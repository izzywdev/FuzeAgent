from crewai import Crew, Agent, Task
from typing import Dict, List, Optional
import asyncio
import docker
import os
from .claude_code_wrapper import ClaudeCodeWrapper
from .database import get_db_connection

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.docker_client = docker.from_env()
        self.crews: Dict[str, Crew] = {}
        
    async def create_agent(
        self, 
        name: str, 
        role: str, 
        type: str,
        config: dict
    ) -> Agent:
        """Create a new agent and optionally spawn a container"""
        
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
        
        # For developer agents, wrap Claude Code
        if type == 'developer':
            agent.tools.append(ClaudeCodeWrapper())
        
        # Store agent
        self.agents[name] = agent
        
        # For complex agents, spawn dedicated container
        if type in ['executive', 'developer']:
            await self._spawn_agent_container(name, role, type, config)
        
        # Update database
        await self._register_agent_in_db(name, role, type, config)
        
        return agent
    
    async def _spawn_agent_container(
        self, 
        name: str, 
        role: str, 
        type: str,
        config: dict
    ):
        """Spawn a dedicated container for an agent"""
        
        container_config = {
            'image': f'ai-agent-{type}:latest',
            'name': f'agent-{name.lower().replace(" ", "-")}',
            'environment': {
                'AGENT_NAME': name,
                'AGENT_ROLE': role,
                'AGENT_TYPE': type,
                'RABBITMQ_URL': 'amqp://admin:password@rabbitmq:5672/',
                'CONTEXT_API_URL': 'http://orchestrator:8000',
                'ANTHROPIC_API_KEY': os.environ['ANTHROPIC_API_KEY']
            },
            'network': 'ai-team-network',
            'restart_policy': {'Name': 'unless-stopped'}
        }
        
        try:
            container = self.docker_client.containers.run(
                detach=True,
                **container_config
            )
            print(f"Spawned container for {name}: {container.id}")
        except Exception as e:
            print(f"Error spawning container for {name}: {e}")
    
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
        """Register agent in database"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agents (name, role, type, status, config)
                VALUES ($1, $2, $3, 'active', $4)
                """,
                name, role, type, config
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
            raise HTTPException(status_code=404, detail="Agent not found")
    
    async def get_updates(self) -> Dict:
        """Get real-time updates for WebSocket"""
        agents = await self.list_agents()
        return {
            "agents": agents,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def shutdown_all(self):
        """Shutdown all agents"""
        for name, agent in self.agents.items():
            print(f"Shutting down agent: {name}")
        self.agents.clear()