#!/usr/bin/env python3
"""
Enhanced Autonomous Agent with Persistent Memory

This agent maintains life-long memory across container instances, learns from
experience, and provides increasingly intelligent responses based on accumulated
expertise. Each agent has its own persistent memory stored in the centralized
database but accessed locally for performance.
"""

import asyncio
import aiohttp
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from agent_memory_manager import AgentMemoryManager, MemoryType
from claude_client_with_memory import ClaudeClientWithMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/agent.log')
    ]
)
logger = logging.getLogger(__name__)

class TaskStatus:
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AutonomousAgentWithMemory:
    """
    Enhanced autonomous agent with persistent memory and learning capabilities.
    
    Features:
    - Persistent memory across container instances
    - Learning from task outcomes and experiences
    - Memory-enhanced Claude interactions
    - Expertise development over time
    - Context continuity across tasks
    - Performance analytics and optimization
    """
    
    def __init__(self):
        # Agent configuration from environment
        self.agent_id = os.environ.get('AGENT_ID', str(uuid.uuid4()))
        self.container_instance_id = f"{self.agent_id}-{uuid.uuid4().hex[:8]}"
        self.orchestrator_url = os.environ.get('ORCHESTRATOR_URL', 'http://orchestrator:8000')
        self.workspace_root = os.environ.get('FUZE_AGENT_WORKSPACE', '/workspaces')
        
        # Database configuration
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # API keys
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        # Repository settings
        self.repository_url = os.environ.get('REPOSITORY_URL')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        
        # Agent state
        self.running = False
        self.current_tasks: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Memory and AI components
        self.memory_manager: Optional[AgentMemoryManager] = None
        self.claude_client: Optional[ClaudeClientWithMemory] = None
        
        # Performance tracking
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_execution_time = 0.0
        self.startup_time = datetime.now()
        
        # Configuration
        self.max_concurrent_tasks = int(os.environ.get('MAX_CONCURRENT_TASKS', '3'))
        self.task_poll_interval = int(os.environ.get('TASK_POLL_INTERVAL', '10'))
        self.memory_sync_interval = int(os.environ.get('MEMORY_SYNC_INTERVAL', '60'))
        
    async def start(self):
        """Start the autonomous agent with memory initialization"""
        logger.info(f"🚀 Starting Enhanced Autonomous Agent {self.agent_id}")
        logger.info(f"Container Instance: {self.container_instance_id}")
        
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=300)
            )
            
            # Initialize memory system
            await self._initialize_memory_system()
            
            # Initialize Claude client with memory
            await self._initialize_claude_client()
            
            # Connect to orchestrator and announce capabilities
            await self._connect_to_orchestrator()
            
            # Set up workspace
            await self._setup_workspace()
            
            # Load agent's historical context
            await self._load_agent_context()
            
            # Start main execution loop
            self.running = True
            await self._main_execution_loop()
            
        except Exception as e:
            logger.error(f"❌ Error starting agent: {e}")
            await self._report_error(f"Agent startup failed: {str(e)}")
            raise
        finally:
            await self._cleanup()
    
    async def stop(self):
        """Stop the autonomous agent gracefully"""
        logger.info("🛑 Stopping Enhanced Autonomous Agent")
        self.running = False
        
        # Complete any running tasks
        if self.current_tasks:
            logger.info(f"Waiting for {len(self.current_tasks)} tasks to complete...")
            await asyncio.sleep(5)  # Give tasks time to finish
    
    async def _initialize_memory_system(self):
        """Initialize the persistent memory system"""
        logger.info("🧠 Initializing persistent memory system...")
        
        self.memory_manager = AgentMemoryManager(
            agent_id=self.agent_id,
            container_instance_id=self.container_instance_id
        )
        
        await self.memory_manager.initialize(self.database_url)
        
        # Get agent expertise summary
        expertise = await self.memory_manager.get_agent_expertise_summary()
        total_memories = expertise.get('memory_statistics', {}).get('total_memories', 0)
        skill_areas = len(expertise.get('expertise_areas', []))
        
        logger.info(f"✅ Memory system initialized:")
        logger.info(f"   - Total memories: {total_memories}")
        logger.info(f"   - Skill areas: {skill_areas}")
        logger.info(f"   - Container instances: {len(expertise.get('container_history', []))}")
    
    async def _initialize_claude_client(self):
        """Initialize Claude client with memory integration"""
        logger.info("🤖 Initializing Claude client with memory...")
        
        self.claude_client = ClaudeClientWithMemory(
            memory_manager=self.memory_manager,
            agent_id=self.agent_id,
            anthropic_api_key=self.anthropic_api_key,
            model=os.environ.get('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
        )
        
        logger.info("✅ Claude client with memory initialized")
    
    async def _connect_to_orchestrator(self):
        """Connect to orchestrator and announce agent capabilities"""
        logger.info(f"🔗 Connecting to orchestrator: {self.orchestrator_url}")
        
        try:
            # Get agent expertise for capability announcement
            expertise = await self.memory_manager.get_agent_expertise_summary()
            
            # Announce agent capabilities
            capabilities = {
                'agent_id': self.agent_id,
                'container_instance_id': self.container_instance_id,
                'status': 'initializing',
                'features': {
                    'persistent_memory': True,
                    'learning_enabled': True,
                    'expertise_tracking': True,
                    'memory_enhanced_claude': True,
                    'multi_task_support': True
                },
                'expertise': {
                    'total_memories': expertise.get('memory_statistics', {}).get('total_memories', 0),
                    'skill_areas': [area['skill_area'] for area in expertise.get('expertise_areas', [])],
                    'avg_expertise_level': sum(area['expertise_level'] for area in expertise.get('expertise_areas', [])) / max(1, len(expertise.get('expertise_areas', []))),
                    'container_instances': len(expertise.get('container_history', []))
                },
                'capabilities': {
                    'max_concurrent_tasks': self.max_concurrent_tasks,
                    'supported_languages': ['python', 'javascript', 'typescript', 'react', 'html', 'css'],
                    'task_types': ['development', 'debugging', 'testing', 'code_review', 'optimization'],
                    'workspace_path': self.workspace_root
                }
            }
            
            async with self.session.post(
                f"{self.orchestrator_url}/agents/{self.agent_id}/register",
                json=capabilities
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("✅ Successfully registered with orchestrator")
                    logger.info(f"   - Agent recognized: {result.get('agent_recognized', False)}")
                    logger.info(f"   - Capabilities accepted: {result.get('capabilities_accepted', False)}")
                else:
                    logger.warning(f"⚠️ Registration response: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Error connecting to orchestrator: {e}")
            # Continue anyway - agent can work in standalone mode
    
    async def _setup_workspace(self):
        """Set up the agent's workspace"""
        logger.info(f"📁 Setting up workspace: {self.workspace_root}")
        
        try:
            # Create workspace directory structure
            workspace = Path(self.workspace_root)
            workspace.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (workspace / "shared").mkdir(exist_ok=True)
            (workspace / "templates").mkdir(exist_ok=True)
            (workspace / "cache").mkdir(exist_ok=True)
            
            # Change to workspace directory
            os.chdir(self.workspace_root)
            
            logger.info("✅ Workspace setup complete")
            
        except Exception as e:
            logger.error(f"❌ Error setting up workspace: {e}")
            raise
    
    async def _load_agent_context(self):
        """Load agent's historical context and recent learnings"""
        logger.info("📚 Loading agent historical context...")
        
        try:
            # Query recent high-value memories for context
            recent_memories = await self.memory_manager.query_memories(
                query="recent successful patterns and learnings",
                memory_types=[MemoryType.SUCCESS, MemoryType.LEARNING, MemoryType.PATTERN],
                limit=10,
                min_confidence=0.7
            )
            
            if recent_memories:
                logger.info(f"✅ Loaded {len(recent_memories)} recent high-value memories")
                
                # Store context summary as a memory
                context_summary = f"Agent context loaded with {len(recent_memories)} recent memories. "
                context_summary += f"Key patterns: {[m.memory.memory_type.value for m in recent_memories[:3]]}"
                
                await self.memory_manager.store_memory(
                    task_id=None,
                    memory_type=MemoryType.LEARNING,
                    content=context_summary,
                    confidence_score=0.8
                )
            else:
                logger.info("No recent high-value memories found - fresh start")
                
        except Exception as e:
            logger.error(f"Error loading agent context: {e}")
    
    async def _main_execution_loop(self):
        """Main execution loop with multi-task support"""
        logger.info("🎯 Starting main execution loop with multi-task support")
        
        while self.running:
            try:
                # Check for new tasks if we have capacity
                if len(self.current_tasks) < self.max_concurrent_tasks:
                    new_tasks = await self._get_pending_tasks()
                    
                    for task in new_tasks:
                        if len(self.current_tasks) >= self.max_concurrent_tasks:
                            break
                        
                        task_id = task['id']
                        logger.info(f"📋 Starting task {task_id}: {task.get('title', 'Untitled')}")
                        
                        # Start task execution as background coroutine
                        task_coroutine = asyncio.create_task(
                            self._execute_task_with_memory(task)
                        )
                        
                        self.current_tasks[task_id] = {
                            'task': task,
                            'coroutine': task_coroutine,
                            'started_at': datetime.now()
                        }
                
                # Check for completed tasks
                completed_task_ids = []
                for task_id, task_info in self.current_tasks.items():
                    if task_info['coroutine'].done():
                        completed_task_ids.append(task_id)
                        
                        try:
                            result = await task_info['coroutine']
                            if result.get('success', False):
                                self.tasks_completed += 1
                                logger.info(f"✅ Task {task_id} completed successfully")
                            else:
                                self.tasks_failed += 1
                                logger.warning(f"❌ Task {task_id} failed: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            self.tasks_failed += 1
                            logger.error(f"❌ Task {task_id} exception: {e}")
                
                # Remove completed tasks
                for task_id in completed_task_ids:
                    del self.current_tasks[task_id]
                
                # Periodic memory sync and cleanup
                if int(time.time()) % self.memory_sync_interval == 0:
                    await self._sync_memory_statistics()
                
                # Wait before next iteration
                await asyncio.sleep(self.task_poll_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in main execution loop: {e}")
                await asyncio.sleep(self.task_poll_interval)
        
        logger.info("🛑 Main execution loop stopped")
    
    async def _get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks from orchestrator"""
        try:
            if not self.session:
                return []
            
            async with self.session.get(
                f"{self.orchestrator_url}/agents/{self.agent_id}/tasks/pending",
                params={'limit': self.max_concurrent_tasks - len(self.current_tasks)}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('tasks', [])
                elif response.status == 204:
                    # No tasks available
                    return []
                else:
                    logger.warning(f"⚠️ Error getting pending tasks: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error getting pending tasks: {e}")
            return []
    
    async def _execute_task_with_memory(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using memory-enhanced Claude interaction"""
        
        task_id = task['id']
        task_title = task.get('title', 'Untitled Task')
        task_description = task.get('description', '')
        task_type = task.get('type', 'development')
        
        start_time = time.time()
        
        try:
            # Update task status to executing
            await self._update_task_status(task_id, TaskStatus.EXECUTING, {
                'started_at': datetime.now().isoformat(),
                'agent_container_instance': self.container_instance_id
            })
            
            # Create task-specific workspace
            task_workspace = await self._setup_task_workspace(task_id, task)
            
            # Build comprehensive task context
            task_context = {
                'task_id': task_id,
                'task_type': task_type,
                'complexity': task.get('complexity', 'medium'),
                'estimated_duration': task.get('estimated_duration'),
                'language': task.get('language'),
                'framework': task.get('framework'),
                'requirements': task.get('requirements', [])
            }
            
            # Build code context from repository if available
            code_context = await self._build_code_context(task_workspace, task)
            
            # Execute task with memory-enhanced Claude
            logger.info(f"🤖 Executing task {task_id} with memory-enhanced Claude")
            
            claude_result = await self.claude_client.execute_with_memory_context(
                task_description=task_description,
                task_id=task_id,
                task_context=task_context,
                code_context=code_context,
                enable_learning=True
            )
            
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            if claude_result.get('success', False):
                # Apply code changes if any
                await self._apply_code_changes(task_workspace, claude_result)
                
                # Create git commit if in repository
                commit_hash = await self._create_git_commit(
                    task_workspace, task_title, task_description, claude_result
                )
                
                # Build success result
                result = {
                    'success': True,
                    'task_id': task_id,
                    'execution_time': execution_time,
                    'claude_response': claude_result.get('response', ''),
                    'code_blocks': claude_result.get('code_blocks', []),
                    'file_operations': claude_result.get('file_operations', []),
                    'commit_hash': commit_hash,
                    'workspace_path': task_workspace,
                    'confidence_score': claude_result.get('confidence_score', 0.8)
                }
                
                # Learn from successful outcome
                await self.memory_manager.learn_from_task_outcome(task_id, {
                    'success': True,
                    'task_type': task_type,
                    'complexity': task_context['complexity'],
                    'duration_minutes': execution_time / 60,
                    'description': task_description,
                    'files_modified': result.get('file_operations', []),
                    'performance_metrics': {
                        'execution_time': execution_time,
                        'confidence_score': result['confidence_score'],
                        'code_blocks_generated': len(result.get('code_blocks', []))
                    }
                })
                
                # Update task status to completed
                await self._update_task_status(task_id, TaskStatus.COMPLETED, result)
                
                logger.info(f"✅ Task {task_id} completed successfully in {execution_time:.2f}s")
                return result
                
            else:
                # Handle task failure
                error_message = claude_result.get('error', 'Task execution failed')
                
                result = {
                    'success': False,
                    'task_id': task_id,
                    'error': error_message,
                    'execution_time': execution_time,
                    'claude_response': claude_result.get('response', ''),
                    'confidence_score': claude_result.get('confidence_score', 0.1)
                }
                
                # Learn from failure
                await self.memory_manager.learn_from_task_outcome(task_id, {
                    'success': False,
                    'task_type': task_type,
                    'complexity': task_context['complexity'],
                    'duration_minutes': execution_time / 60,
                    'description': task_description,
                    'error_message': error_message,
                    'error_details': claude_result
                })
                
                # Update task status to failed
                await self._update_task_status(task_id, TaskStatus.FAILED, result)
                
                logger.error(f"❌ Task {task_id} failed: {error_message}")
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            logger.error(f"❌ Exception in task {task_id}: {e}")
            
            # Store error memory
            await self.memory_manager.store_memory(
                task_id=task_id,
                memory_type=MemoryType.ERROR,
                content=f"Task execution exception: {error_message}",
                task_context=task_context or {},
                outcome_context={'error': error_message, 'exception_type': type(e).__name__},
                confidence_score=0.9
            )
            
            result = {
                'success': False,
                'task_id': task_id,
                'error': error_message,
                'execution_time': execution_time,
                'exception_type': type(e).__name__
            }
            
            # Update task status to failed
            await self._update_task_status(task_id, TaskStatus.FAILED, result)
            
            return result
        
        finally:
            # Cleanup task workspace if needed
            await self._cleanup_task_workspace(task_workspace)
    
    async def _setup_task_workspace(self, task_id: str, task: Dict[str, Any]) -> str:
        """Set up isolated workspace for task execution"""
        
        task_workspace = os.path.join(self.workspace_root, f"task-{task_id}")
        
        try:
            # Create task workspace
            Path(task_workspace).mkdir(parents=True, exist_ok=True)
            
            # Clone repository if specified
            if self.repository_url:
                await self._clone_repository_to_workspace(task_workspace)
            
            logger.debug(f"Created task workspace: {task_workspace}")
            return task_workspace
            
        except Exception as e:
            logger.error(f"Error setting up task workspace: {e}")
            return task_workspace
    
    async def _clone_repository_to_workspace(self, workspace_path: str):
        """Clone repository to task workspace"""
        try:
            # Configure git credentials if token available
            if self.github_token:
                await self._run_command([
                    'git', 'config', '--global', 'credential.helper', 
                    f'!echo "username={self.github_token}"; echo "password="'
                ])
            
            # Clone repository
            result = await self._run_command([
                'git', 'clone', self.repository_url, workspace_path
            ])
            
            if result['exit_code'] == 0:
                logger.debug(f"Repository cloned to {workspace_path}")
            else:
                logger.error(f"Failed to clone repository: {result['output']}")
                
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
    
    async def _build_code_context(self, workspace_path: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Build code context from workspace"""
        
        context = {
            'workspace_path': workspace_path,
            'has_git': False,
            'files_present': [],
            'languages_detected': [],
            'frameworks_detected': []
        }
        
        try:
            workspace = Path(workspace_path)
            
            # Check if it's a git repository
            if (workspace / '.git').exists():
                context['has_git'] = True
                
                # Get current branch
                result = await self._run_command(['git', 'branch', '--show-current'], cwd=workspace_path)
                if result['exit_code'] == 0:
                    context['current_branch'] = result['output'].strip()
            
            # Scan for relevant files (limit to avoid overwhelming context)
            relevant_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.md', '.yml', '.yaml', '.toml'}
            
            for file_path in workspace.rglob('*'):
                if file_path.is_file() and file_path.suffix in relevant_extensions:
                    relative_path = file_path.relative_to(workspace)
                    context['files_present'].append(str(relative_path))
                    
                    # Detect language
                    if file_path.suffix == '.py':
                        context['languages_detected'].append('python')
                    elif file_path.suffix in {'.js', '.jsx'}:
                        context['languages_detected'].append('javascript')
                    elif file_path.suffix in {'.ts', '.tsx'}:
                        context['languages_detected'].append('typescript')
                    
                    # Stop after reasonable number of files
                    if len(context['files_present']) > 50:
                        break
            
            # Remove duplicates
            context['languages_detected'] = list(set(context['languages_detected']))
            
            # Detect frameworks
            if 'package.json' in [f.name for f in workspace.iterdir() if f.is_file()]:
                try:
                    with open(workspace / 'package.json', 'r') as f:
                        package_data = json.load(f)
                        dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                        
                        if 'react' in dependencies:
                            context['frameworks_detected'].append('react')
                        if 'next' in dependencies:
                            context['frameworks_detected'].append('nextjs')
                        if 'vue' in dependencies:
                            context['frameworks_detected'].append('vue')
                        if 'express' in dependencies:
                            context['frameworks_detected'].append('express')
                            
                except Exception:
                    pass
            
            if 'requirements.txt' in [f.name for f in workspace.iterdir() if f.is_file()]:
                context['frameworks_detected'].append('python')
                try:
                    with open(workspace / 'requirements.txt', 'r') as f:
                        requirements = f.read().lower()
                        if 'fastapi' in requirements:
                            context['frameworks_detected'].append('fastapi')
                        if 'django' in requirements:
                            context['frameworks_detected'].append('django')
                        if 'flask' in requirements:
                            context['frameworks_detected'].append('flask')
                except Exception:
                    pass
            
            logger.debug(f"Built code context: {len(context['files_present'])} files, "
                        f"{len(context['languages_detected'])} languages, "
                        f"{len(context['frameworks_detected'])} frameworks")
            
        except Exception as e:
            logger.error(f"Error building code context: {e}")
        
        return context
    
    async def _apply_code_changes(self, workspace_path: str, claude_result: Dict[str, Any]):
        """Apply code changes from Claude's response"""
        
        try:
            code_blocks = claude_result.get('code_blocks', [])
            file_operations = claude_result.get('file_operations', [])
            
            for code_block in code_blocks:
                # Simple heuristic: if code block mentions a filename, try to save it
                code = code_block.get('code', '')
                language = code_block.get('language', '')
                
                # Look for filename comments in code
                import re
                filename_match = re.search(r'#\s*filename?[:=]\s*([^\n\r]+)', code) or \
                                re.search(r'//\s*filename?[:=]\s*([^\n\r]+)', code) or \
                                re.search(r'<!--\s*filename?[:=]\s*([^\n\r]+)\s*-->', code)
                
                if filename_match:
                    filename = filename_match.group(1).strip()
                    file_path = Path(workspace_path) / filename
                    
                    # Create directory if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write code to file
                    with open(file_path, 'w') as f:
                        f.write(code)
                    
                    logger.debug(f"Applied code changes to {filename}")
            
            # Apply explicit file operations
            for file_op in file_operations:
                file_path = Path(workspace_path) / file_op
                if file_path.exists():
                    logger.debug(f"File operation applied: {file_op}")
            
        except Exception as e:
            logger.error(f"Error applying code changes: {e}")
    
    async def _create_git_commit(
        self, 
        workspace_path: str, 
        task_title: str, 
        task_description: str, 
        claude_result: Dict[str, Any]
    ) -> Optional[str]:
        """Create git commit for task changes"""
        
        try:
            workspace = Path(workspace_path)
            
            if not (workspace / '.git').exists():
                return None
            
            # Configure git user
            await self._run_command([
                'git', 'config', 'user.name', f'FuzeAgent-{self.agent_id[:8]}'
            ], cwd=workspace_path)
            await self._run_command([
                'git', 'config', 'user.email', f'agent-{self.agent_id}@fuzeagent.ai'
            ], cwd=workspace_path)
            
            # Add all changes
            await self._run_command(['git', 'add', '.'], cwd=workspace_path)
            
            # Check if there are changes to commit
            result = await self._run_command(['git', 'diff', '--staged', '--name-only'], cwd=workspace_path)
            if not result['output'].strip():
                logger.debug("No changes to commit")
                return None
            
            # Create commit message
            commit_message = f"🤖 {task_title}\n\n{task_description[:200]}...\n\n"
            commit_message += f"Generated by FuzeAgent {self.agent_id[:8]} with persistent memory.\n"
            commit_message += f"Container instance: {self.container_instance_id}\n"
            commit_message += f"Confidence score: {claude_result.get('confidence_score', 0):.1%}"
            
            # Create commit
            result = await self._run_command(['git', 'commit', '-m', commit_message], cwd=workspace_path)
            
            if result['exit_code'] == 0:
                # Get commit hash
                hash_result = await self._run_command(['git', 'rev-parse', 'HEAD'], cwd=workspace_path)
                if hash_result['exit_code'] == 0:
                    commit_hash = hash_result['output'].strip()
                    logger.info(f"Created git commit: {commit_hash[:8]}")
                    return commit_hash
            
        except Exception as e:
            logger.error(f"Error creating git commit: {e}")
        
        return None
    
    async def _cleanup_task_workspace(self, workspace_path: str):
        """Clean up task workspace"""
        try:
            # For now, keep workspaces for debugging
            # In production, you might want to clean up after successful tasks
            logger.debug(f"Task workspace preserved: {workspace_path}")
        except Exception as e:
            logger.error(f"Error cleaning up task workspace: {e}")
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None
    ):
        """Update task status in orchestrator"""
        try:
            if not self.session:
                return
            
            payload = {
                'status': status,
                'result': result or {},
                'updated_by': self.agent_id,
                'container_instance_id': self.container_instance_id,
                'updated_at': datetime.now().isoformat()
            }
            
            async with self.session.put(
                f"{self.orchestrator_url}/tasks/{task_id}/status",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.debug(f"Task {task_id} status updated to {status}")
                else:
                    logger.warning(f"Failed to update task status: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
    
    async def _sync_memory_statistics(self):
        """Sync memory and performance statistics with orchestrator"""
        try:
            # Get current statistics
            expertise = await self.memory_manager.get_agent_expertise_summary()
            claude_stats = await self.claude_client.get_interaction_statistics()
            
            uptime_hours = (datetime.now() - self.startup_time).total_seconds() / 3600
            
            stats = {
                'agent_id': self.agent_id,
                'container_instance_id': self.container_instance_id,
                'uptime_hours': uptime_hours,
                'tasks_completed': self.tasks_completed,
                'tasks_failed': self.tasks_failed,
                'success_rate': self.tasks_completed / max(1, self.tasks_completed + self.tasks_failed),
                'total_execution_time': self.total_execution_time,
                'current_active_tasks': len(self.current_tasks),
                'memory_statistics': expertise.get('memory_statistics', {}),
                'claude_statistics': claude_stats,
                'expertise_summary': {
                    'skill_areas': len(expertise.get('expertise_areas', [])),
                    'avg_expertise_level': sum(area['expertise_level'] for area in expertise.get('expertise_areas', [])) / max(1, len(expertise.get('expertise_areas', []))),
                    'improving_skills': len([area for area in expertise.get('expertise_areas', []) if area['performance_trend'] == 'improving'])
                }
            }
            
            async with self.session.post(
                f"{self.orchestrator_url}/agents/{self.agent_id}/statistics",
                json=stats
            ) as response:
                if response.status == 200:
                    logger.debug("Memory statistics synced with orchestrator")
                    
        except Exception as e:
            logger.error(f"Error syncing memory statistics: {e}")
    
    async def _report_error(self, error_message: str):
        """Report error to orchestrator"""
        try:
            if not self.session:
                return
            
            await self.session.post(
                f"{self.orchestrator_url}/agents/{self.agent_id}/error",
                json={
                    'error': error_message,
                    'timestamp': datetime.now().isoformat(),
                    'container_instance_id': self.container_instance_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    async def _run_command(
        self, 
        args: List[str], 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run a shell command asynchronously"""
        try:
            command_env = os.environ.copy()
            if env:
                command_env.update(env)
            
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=command_env,
                cwd=cwd
            )
            
            stdout, _ = await process.communicate()
            
            return {
                'exit_code': process.returncode,
                'output': stdout.decode('utf-8', errors='replace'),
                'success': process.returncode == 0
            }
            
        except Exception as e:
            return {
                'exit_code': -1,
                'output': str(e),
                'success': False
            }
    
    async def _cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up agent resources")
        
        # Close memory manager
        if self.memory_manager:
            await self.memory_manager.close()
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        logger.info("✅ Agent cleanup complete")

async def main():
    """Main entry point"""
    agent = AutonomousAgentWithMemory()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}")
    finally:
        await agent.stop()

if __name__ == '__main__':
    asyncio.run(main())