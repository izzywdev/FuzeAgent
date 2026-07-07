from crewai import Crew, Agent, Task
from typing import Dict, List, Optional, Any
import asyncio
import docker
import os
import uuid
import logging
from .claude_code_wrapper import ClaudeCodeWrapper
from .database import get_db_connection, DatabaseManager
from .sandbox_manager import AgentSandboxManager
from .git_workflow_manager import GitWorkflowManager
from .agent_expertise_tracker import AgentExpertiseTracker

logger = logging.getLogger(__name__)

try:
    from kubernetes import client as k8s_client, config as k8s_config
    from kubernetes.client.rest import ApiException
    _K8S_AVAILABLE = True
except ImportError:
    _K8S_AVAILABLE = False

class AgentManager:
    def __init__(self, database_url: str):
        self.agents: Dict[str, Agent] = {}
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except Exception as e:
            logger.warning(f"Docker not available, container features disabled: {e}")
            self.docker_client = None

        self.k8s_batch_v1 = None
        self.k8s_namespace = os.environ.get('POD_NAMESPACE', 'fuzeagent')
        if _K8S_AVAILABLE:
            try:
                k8s_config.load_incluster_config()
                self.k8s_batch_v1 = k8s_client.BatchV1Api()
                logger.info("Kubernetes in-cluster config loaded")
            except Exception:
                try:
                    k8s_config.load_kube_config()
                    self.k8s_batch_v1 = k8s_client.BatchV1Api()
                    logger.info("Kubernetes kubeconfig loaded (dev mode)")
                except Exception as e:
                    logger.warning(f"Kubernetes not available: {e}")

        self.crews: Dict[str, Crew] = {}
        self.sandbox_manager: Optional[AgentSandboxManager] = None
        self.expertise_tracker = AgentExpertiseTracker(database_url)
        self.database_url = database_url
        
        # Track active memory-enabled agent containers
        self.memory_enabled_agents: Dict[str, Dict[str, Any]] = {}
        
        # Agent templates configuration
        self.agent_templates = {
            "python_developer": {
                "role": "Python Developer",
                "type": "developer",
                "config": {
                    "goal": "Develop high-quality Python applications with FastAPI, SQLAlchemy, and testing",
                    "backstory": "Expert Python developer with deep knowledge of backend development, APIs, and testing frameworks",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.3,
                    "tools": ["code_generation", "code_review", "testing", "debugging"]
                },
                "resource_limits": {
                    "memory": "2Gi",
                    "cpu": "1.0",
                    "disk": "10Gi"
                }
            },
            "typescript_developer": {
                "role": "TypeScript Developer", 
                "type": "developer",
                "config": {
                    "goal": "Build modern TypeScript applications with Node.js, Express, and comprehensive testing",
                    "backstory": "Senior TypeScript developer specializing in full-stack development and API design",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.3,
                    "tools": ["code_generation", "code_review", "testing", "api_design"]
                },
                "resource_limits": {
                    "memory": "2Gi",
                    "cpu": "1.0", 
                    "disk": "10Gi"
                }
            },
            "react_developer": {
                "role": "React Developer",
                "type": "developer",
                "config": {
                    "goal": "Create responsive React applications with modern UI/UX and accessibility",
                    "backstory": "Frontend specialist with expertise in React, TypeScript, and modern web technologies",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.4,
                    "tools": ["ui_development", "component_design", "testing", "accessibility"]
                },
                "resource_limits": {
                    "memory": "3Gi",
                    "cpu": "1.5",
                    "disk": "15Gi"
                }
            },
            "security_developer": {
                "role": "Security Developer",
                "type": "developer",
                "config": {
                    "goal": "Implement secure coding practices and identify security vulnerabilities",
                    "backstory": "Cybersecurity expert specializing in secure application development and vulnerability assessment",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.2,
                    "tools": ["security_audit", "code_review", "vulnerability_scanning", "secure_coding"]
                },
                "resource_limits": {
                    "memory": "2Gi",
                    "cpu": "1.0",
                    "disk": "10Gi"
                }
            },
            "devops_engineer": {
                "role": "DevOps Engineer",
                "type": "infrastructure",
                "config": {
                    "goal": "Manage CI/CD pipelines, infrastructure, and deployment automation",
                    "backstory": "DevOps specialist with expertise in Docker, Kubernetes, and cloud infrastructure",
                    "model": "claude-3-5-sonnet-20241022",
                    "temperature": 0.3,
                    "tools": ["infrastructure", "deployment", "monitoring", "automation"]
                },
                "resource_limits": {
                    "memory": "4Gi",
                    "cpu": "2.0",
                    "disk": "20Gi"
                }
            }
        }
        
    async def create_agent(
        self, 
        name: str, 
        role: str, 
        type: str,
        config: dict,
        team_id: Optional[str] = None,
        template_id: Optional[str] = None,
        repository_settings: Optional[Dict[str, Any]] = None,
        sandbox_settings: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Create a new agent with repository and sandbox settings"""
        
        # Generate agent ID
        agent_id = str(uuid.uuid4())
        
        # Create CrewAI agent
        agent = Agent(
            role=role,
            goal=config.get('goal', f"Perform {role} tasks efficiently"),
            backstory=config.get('backstory', f"Expert {role} with deep knowledge"),
            tools=self._get_tools_for_role(type, config.get('tools', [])),
            llm_config={
                "model": config.get('model', 'claude-sonnet-4-20250514'),
                "temperature": config.get('temperature', 0.7)
            },
            verbose=True
        )
        
        # Set agent ID for reference
        agent.id = agent_id
        agent.created_at = asyncio.get_event_loop().time()
        
        # For developer agents, create enhanced Claude Code wrapper
        if type == 'developer':
            workspace_path = None
            git_manager = None
            
            # Set up Git workflow if repository settings provided
            if repository_settings and repository_settings.get('repository_url'):
                git_manager = GitWorkflowManager(
                    agent_id=agent_id,
                    task_id="default",  # Will be updated when tasks are assigned
                    repo_settings=repository_settings
                )
                workspace_path = git_manager.workspace_path
            
            # Create enhanced Claude Code wrapper
            claude_wrapper = ClaudeCodeWrapper(
                workspace_path=workspace_path,
                git_manager=git_manager,
                agent_id=agent_id,
                task_id="default"
            )
            agent.tools.append(claude_wrapper)
        
        # Store agent
        self.agents[agent_id] = agent
        
        # Register in database
        if team_id:
            await DatabaseManager.insert_agent(
                team_id=team_id,
                name=name,
                role=role,
                type=type,
                config={
                    **config,
                    "repository_settings": repository_settings or {},
                    "sandbox_settings": sandbox_settings or {}
                },
                template_id=template_id
            )
        else:
            await self._register_agent_in_db(name, role, type, {
                **config,
                "repository_settings": repository_settings or {},
                "sandbox_settings": sandbox_settings or {}
            })
        
        return agent
    
    async def _spawn_agent_container(
        self,
        name: str,
        role: str,
        agent_type: str,
        config: dict
    ) -> Optional[str]:
        """Spawn a k8s Job for an agent. Falls back to Docker in dev."""
        agent_id = config.get('agent_id', name)
        image_map = {
            'python_developer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest',
            'typescript_developer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest',
            'react_developer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest',
            'security_developer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest',
            'devops_engineer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest',
            'qa_engineer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-qa:latest',
            'marketer': 'ghcr.io/izzywdev/fuzeagent/claude-runner-marketer:latest',
        }
        image = image_map.get(agent_type, 'ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest')

        # Prefer k8s Jobs
        if self.k8s_batch_v1:
            return await self._spawn_k8s_job(agent_id, image, config)
        # Dev fallback: Docker
        if self.docker_client:
            return await self._spawn_docker_container_legacy(agent_id, image, config)
        logger.warning(f"No container runtime available for agent {agent_id}")
        return None

    async def _spawn_k8s_job(self, agent_id: str, image: str, config: dict) -> Optional[str]:
        """Create a Kubernetes Job for an agent pod."""
        loop = asyncio.get_event_loop()

        # Job name must be DNS-safe, max 63 chars
        job_name = f"agent-{agent_id[:50].lower().replace('_', '-').replace(' ', '-')}"

        orchestrator_svc = os.environ.get('ORCHESTRATOR_SERVICE_NAME', 'fuzeagent-orchestrator')
        ws_relay_url = f"ws://{orchestrator_svc}/agent-relay/{agent_id}"

        job = k8s_client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=k8s_client.V1ObjectMeta(
                name=job_name,
                namespace=self.k8s_namespace,
                labels={'fuzeagent/agent-id': agent_id, 'fuzeagent/managed': 'true'},
            ),
            spec=k8s_client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=3600,
                template=k8s_client.V1PodTemplateSpec(
                    spec=k8s_client.V1PodSpec(
                        restart_policy='Never',
                        containers=[
                            k8s_client.V1Container(
                                name='agent',
                                image=image,
                                env=[
                                    k8s_client.V1EnvVar(name='AGENT_ID', value=agent_id),
                                    k8s_client.V1EnvVar(name='WS_RELAY_URL', value=ws_relay_url),
                                    k8s_client.V1EnvVar(
                                        name='ANTHROPIC_API_KEY',
                                        value_from=k8s_client.V1EnvVarSource(
                                            secret_key_ref=k8s_client.V1SecretKeySelector(
                                                name='fuzeagent-secrets',
                                                key='ANTHROPIC_API_KEY',
                                                optional=False,
                                            )
                                        ),
                                    ),
                                ],
                                image_pull_policy='Always',
                            )
                        ],
                    )
                ),
            ),
        )

        try:
            await loop.run_in_executor(
                None,
                lambda: self.k8s_batch_v1.create_namespaced_job(namespace=self.k8s_namespace, body=job),
            )
            logger.info(f"Created k8s Job {job_name} for agent {agent_id}")
            return job_name
        except ApiException as e:
            logger.error(f"Failed to create k8s Job for {agent_id}: {e}")
            return None

    async def _spawn_docker_container_legacy(self, agent_id: str, image: str, config: dict) -> Optional[str]:
        """Dev fallback: run agent as a Docker container."""
        container_config = {
            'image': image,
            'name': f'agent-{agent_id[:50].lower().replace("_", "-").replace(" ", "-")}',
            'environment': {
                'AGENT_ID': agent_id,
                'RABBITMQ_URL': 'amqp://admin:password@rabbitmq:5672/',
                'CONTEXT_API_URL': 'http://orchestrator:8000',
                'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
            },
            'network': 'ai-team-network',
            'restart_policy': {'Name': 'unless-stopped'},
        }
        try:
            container = self.docker_client.containers.run(detach=True, **container_config)
            logger.info(f"Spawned Docker container for agent {agent_id}: {container.id}")
            return container.id
        except Exception as e:
            logger.error(f"Error spawning Docker container for agent {agent_id}: {e}")
            return None

    async def _terminate_agent_container(self, agent_id: str):
        """Delete the k8s Job for an agent (cascades to pod)."""
        if self.k8s_batch_v1:
            job_name = f"agent-{agent_id[:50].lower().replace('_', '-').replace(' ', '-')}"
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_batch_v1.delete_namespaced_job(
                        name=job_name,
                        namespace=self.k8s_namespace,
                        body=k8s_client.V1DeleteOptions(propagation_policy='Foreground'),
                    ),
                )
                logger.info(f"Deleted k8s Job {job_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.error(f"Failed to delete k8s Job {job_name}: {e}")
            return
        # Docker fallback
        if self.docker_client and agent_id in self.agents:
            agent = self.agents[agent_id]
            if container_id := agent.config.get('container_id'):
                try:
                    container = self.docker_client.containers.get(container_id)
                    container.stop()
                    container.remove()
                except Exception as e:
                    logger.warning(f"Docker container cleanup failed: {e}")
    
    def _get_tools_for_role(self, type: str, custom_tools: List[str]) -> List:
        """Get appropriate tools based on agent type"""
        
        base_tools = {
            'executive': ['strategic_planning', 'resource_allocation', 'team_management'],
            'developer': ['code_generation', 'code_review', 'debugging'],
            'qa': ['test_generation', 'test_execution', 'bug_reporting'],
            'designer': ['mockup_generation', 'design_review', 'accessibility_check'],
            'support': ['ticket_handling', 'knowledge_search', 'customer_response']
        }
        
        tools = base_tools.get(type, [])
        tools.extend(custom_tools)
        
        # Convert to actual tool instances
        return [self._create_tool(tool_name) for tool_name in tools]
    
    def _create_tool(self, tool_name: str):
        """Create a tool instance based on name"""
        # This would create actual tool instances
        # For now, return a placeholder
        return {"name": tool_name, "description": f"Tool for {tool_name}"}
    
    async def _register_agent_in_db(self, name: str, role: str, type: str, config: dict):
        """Register agent in database (legacy method)"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agents (name, role, type, status, config, repository_settings, sandbox_settings)
                VALUES ($1, $2, $3, 'active', $4, $5, $6)
                """,
                name, role, type, 
                {k: v for k, v in config.items() if k not in ['repository_settings', 'sandbox_settings']},
                config.get('repository_settings', {}),
                config.get('sandbox_settings', {})
            )
    
    async def list_agents(self) -> List[Dict]:
        """List all agents"""
        async with get_db_connection() as conn:
            rows = await conn.fetch("SELECT * FROM agents")
            return [dict(row) for row in rows]
    
    async def get_agent_status(self, agent_id: str) -> Dict:
        """Get detailed agent status"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            if row:
                return dict(row)
            raise ValueError(f"Agent not found: {agent_id}")
    
    async def get_updates(self) -> Dict:
        """Get real-time updates for WebSocket"""
        agents = await self.list_agents()
        return {
            "agents": agents,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def get_template_config(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get agent template configuration"""
        return self.agent_templates.get(template_id)
    
    async def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all available agent templates"""
        return self.agent_templates
    
    async def get_agent_sandbox(self, agent_id: str) -> Dict[str, Any]:
        """Get agent sandbox information"""
        if not self.sandbox_manager:
            return {"error": "Sandbox manager not initialized"}
        
        sandboxes = await self.sandbox_manager.list_sandboxes(agent_id=agent_id)
        return {
            "agent_id": agent_id,
            "sandboxes": [{
                "sandbox_id": s.sandbox_id,
                "status": s.status.value,
                "workspace_path": s.workspace_path,
                "created_at": s.created_at.isoformat(),
                "resource_limits": s.resource_limits
            } for s in sandboxes]
        }
    
    async def set_sandbox_manager(self, sandbox_manager: AgentSandboxManager):
        """Set the sandbox manager reference"""
        self.sandbox_manager = sandbox_manager
    
    async def deploy_memory_enabled_agent(
        self,
        agent_id: str,
        template_id: str,
        task_id: Optional[str] = None,
        repository_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy a memory-enabled autonomous agent container"""
        
        if not self.sandbox_manager:
            raise RuntimeError("Sandbox manager not initialized")
        
        try:
            # Create sandbox for memory-enabled agent
            sandbox = await self.sandbox_manager.create_sandbox(
                agent_id=agent_id,
                task_id=task_id or "autonomous",
                agent_template=template_id,
                repository_settings=repository_settings or {},
                custom_settings={
                    "environment_vars": {
                        "AGENT_ID": agent_id,
                        "DATABASE_URL": self.database_url,
                        "ORCHESTRATOR_URL": "http://orchestrator:8000",
                        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
                        "MAX_CONCURRENT_TASKS": "3",
                        "TASK_POLL_INTERVAL": "10",
                        "MEMORY_SYNC_INTERVAL": "60"
                    }
                }
            )
            
            # Track the memory-enabled agent
            self.memory_enabled_agents[agent_id] = {
                "sandbox_id": sandbox.sandbox_id,
                "container_id": sandbox.container_id,
                "template_id": template_id,
                "status": "initializing",
                "deployed_at": asyncio.get_event_loop().time(),
                "task_id": task_id
            }
            
            # Update agent status in database
            await self._update_agent_memory_status(agent_id, "memory_enabled", {
                "sandbox_id": sandbox.sandbox_id,
                "container_id": sandbox.container_id,
                "memory_enabled": True
            })
            
            return {
                "success": True,
                "agent_id": agent_id,
                "sandbox_id": sandbox.sandbox_id,
                "container_id": sandbox.container_id,
                "status": "deployed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e)
            }
    
    async def get_agent_memory_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent memory status and expertise summary"""
        
        try:
            # Get basic agent info
            agent_info = await self.get_agent_status(agent_id)
            
            # Get memory-enabled container status
            container_status = self.memory_enabled_agents.get(agent_id, {})
            
            # Get expertise metrics
            performance_metrics = await self.expertise_tracker.get_agent_performance_metrics(agent_id)
            
            # Get recent insights
            insights = await self.expertise_tracker.generate_expertise_insights(agent_id)
            
            return {
                "agent_id": agent_id,
                "basic_info": agent_info,
                "memory_container": container_status,
                "performance_metrics": performance_metrics.__dict__ if performance_metrics else None,
                "recent_insights": [insight.__dict__ for insight in insights[:5]],
                "memory_enabled": bool(container_status),
                "status": container_status.get("status", "unknown")
            }
            
        except Exception as e:
            return {
                "agent_id": agent_id,
                "error": str(e),
                "memory_enabled": False
            }
    
    async def assign_task_to_memory_agent(
        self,
        agent_id: str,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assign a task to a memory-enabled agent"""
        
        if agent_id not in self.memory_enabled_agents:
            return {
                "success": False,
                "error": f"Agent {agent_id} is not memory-enabled or not deployed"
            }
        
        try:
            # Store task in database with memory-enabled flag
            async with get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO tasks (
                        id, agent_id, title, description, type, complexity,
                        language, framework, requirements, status, 
                        assigned_to_memory_agent, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending', true, NOW())
                """, 
                    task_id, agent_id, 
                    task_data.get('title', 'Untitled'),
                    task_data.get('description', ''),
                    task_data.get('type', 'development'),
                    task_data.get('complexity', 'medium'),
                    task_data.get('language'),
                    task_data.get('framework'),
                    task_data.get('requirements', [])
                )
            
            # The memory-enabled agent will automatically pick up the task
            # through its polling mechanism
            
            return {
                "success": True,
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "assigned_to_memory_agent",
                "message": "Task assigned to memory-enabled agent - agent will pick it up automatically"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task_id,
                "agent_id": agent_id,
                "error": str(e)
            }
    
    async def get_system_expertise_dashboard(self) -> Dict[str, Any]:
        """Get system-wide expertise and memory analytics dashboard"""
        
        try:
            # Get system-wide expertise summary
            expertise_summary = await self.expertise_tracker.get_system_wide_expertise_summary()
            
            # Get memory-enabled agents status
            memory_agents_status = []
            for agent_id, container_info in self.memory_enabled_agents.items():
                agent_memory_status = await self.get_agent_memory_status(agent_id)
                memory_agents_status.append(agent_memory_status)
            
            # Get recent activity across all agents
            async with get_db_connection() as conn:
                recent_tasks = await conn.fetch("""
                    SELECT 
                        t.id, t.agent_id, t.title, t.status, t.assigned_to_memory_agent,
                        t.created_at, t.updated_at,
                        a.name as agent_name, a.role as agent_role
                    FROM tasks t
                    JOIN agents a ON t.agent_id = a.id
                    WHERE t.created_at > NOW() - INTERVAL '24 hours'
                    ORDER BY t.created_at DESC
                    LIMIT 20
                """)
            
            return {
                "system_expertise": expertise_summary,
                "memory_enabled_agents": {
                    "count": len(self.memory_enabled_agents),
                    "agents": memory_agents_status
                },
                "recent_activity": [dict(task) for task in recent_tasks],
                "dashboard_generated_at": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "dashboard_generated_at": asyncio.get_event_loop().time()
            }
    
    async def stop_memory_enabled_agent(self, agent_id: str) -> Dict[str, Any]:
        """Stop a memory-enabled agent container"""
        
        if agent_id not in self.memory_enabled_agents:
            return {
                "success": False,
                "error": f"Agent {agent_id} is not memory-enabled or not deployed"
            }
        
        try:
            container_info = self.memory_enabled_agents[agent_id]
            sandbox_id = container_info["sandbox_id"]
            
            # Destroy the sandbox (this will stop and clean up the container)
            if self.sandbox_manager:
                await self.sandbox_manager.destroy_sandbox(sandbox_id)
            
            # Update agent status
            await self._update_agent_memory_status(agent_id, "stopped", {
                "memory_enabled": False,
                "stopped_at": asyncio.get_event_loop().time()
            })
            
            # Remove from tracking
            del self.memory_enabled_agents[agent_id]
            
            return {
                "success": True,
                "agent_id": agent_id,
                "message": "Memory-enabled agent stopped successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e)
            }
    
    async def _update_agent_memory_status(self, agent_id: str, status: str, additional_data: Dict[str, Any]):
        """Update agent memory-related status in database"""
        
        try:
            async with get_db_connection() as conn:
                # Update agent config with memory status
                await conn.execute("""
                    UPDATE agents 
                    SET status = $2, 
                        config = config || $3,
                        updated_at = NOW()
                    WHERE id = $1
                """, agent_id, status, additional_data)
                
        except Exception as e:
            print(f"Error updating agent memory status: {e}")
    
    async def shutdown_all(self):
        """Shutdown all agents including memory-enabled ones"""
        
        # Stop all memory-enabled agents
        memory_agent_ids = list(self.memory_enabled_agents.keys())
        for agent_id in memory_agent_ids:
            try:
                await self.stop_memory_enabled_agent(agent_id)
            except Exception as e:
                print(f"Error stopping memory-enabled agent {agent_id}: {e}")
        
        # Shutdown regular agents
        for agent_id, agent in self.agents.items():
            print(f"Shutting down agent: {agent_id}")
        self.agents.clear()