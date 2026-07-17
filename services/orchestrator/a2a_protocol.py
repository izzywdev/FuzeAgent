# fmt: off
"""
Agent-to-Agent (A2A) Protocol Implementation for FuzeAgent

This module implements Google's Agent2Agent protocol for enabling
AI agents to communicate, collaborate, and coordinate tasks.

Based on the A2A Protocol Specification:
- Agent Discovery via Agent Cards
- Task Management and Delegation
- Secure Communication
- Multi-modal Support
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import asyncpg
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status values for A2A protocol"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Message types for A2A communication"""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ARTIFACT = "artifact"
    COLLABORATION = "collaboration"
    HANDOFF = "handoff"


class AgentCard(BaseModel):
    """Agent Card for agent discovery and capability advertisement"""

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent display name")
    description: str = Field(..., description="Agent description and purpose")
    version: str = Field(default="1.0.0", description="Agent version")

    # Capabilities
    capabilities: List[str] = Field(..., description="List of agent capabilities")
    skills: List[str] = Field(..., description="Agent skills and expertise")
    tools: List[str] = Field(..., description="Available tools and integrations")

    # Communication
    protocols: List[str] = Field(default=["A2A"], description="Supported protocols")
    endpoints: Dict[str, str] = Field(..., description="Communication endpoints")

    # Availability and limits
    availability_status: str = Field(
        default="available", description="Current availability"
    )
    max_concurrent_tasks: int = Field(default=5, description="Maximum concurrent tasks")
    current_task_count: int = Field(default=0, description="Current active tasks")

    # Metadata
    tags: List[str] = Field(default=[], description="Agent tags for filtering")
    team_id: Optional[str] = Field(None, description="Associated team ID")
    organization_id: Optional[str] = Field(
        None, description="Associated organization ID"
    )

    # Authentication and security
    authentication_type: str = Field(
        default="bearer_token", description="Authentication method"
    )
    security_level: str = Field(
        default="standard", description="Security level requirement"
    )

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class A2ATask(BaseModel):
    """A2A Task representation"""

    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    task_type: str = Field(..., description="Type of task")

    # Agent assignment
    requesting_agent_id: str = Field(..., description="Agent requesting the task")
    assigned_agent_id: Optional[str] = Field(None, description="Agent assigned to task")

    # Task details
    priority: int = Field(default=5, description="Task priority (1-10)")
    estimated_duration: Optional[int] = Field(
        None, description="Estimated duration in minutes"
    )
    deadline: Optional[datetime] = Field(None, description="Task deadline")

    # Status and progress
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    progress_percentage: int = Field(
        default=0, description="Task completion percentage"
    )

    # Data and context
    input_data: Dict[str, Any] = Field(default={}, description="Task input data")
    output_data: Dict[str, Any] = Field(default={}, description="Task output data")
    context: Dict[str, Any] = Field(default={}, description="Additional context")

    # Communication
    artifacts: List[Dict[str, Any]] = Field(default=[], description="Task artifacts")
    messages: List[Dict[str, Any]] = Field(
        default=[], description="Task communication log"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    updated_at: datetime = Field(default_factory=datetime.now)


class A2AMessage(BaseModel):
    """A2A Communication Message"""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = Field(..., description="Type of message")

    # Participants
    sender_agent_id: str = Field(..., description="Sending agent ID")
    recipient_agent_id: str = Field(..., description="Receiving agent ID")

    # Content
    content: str = Field(..., description="Message content")
    data: Dict[str, Any] = Field(default={}, description="Structured data")

    # Context
    task_id: Optional[str] = Field(None, description="Related task ID")
    conversation_id: Optional[str] = Field(None, description="Conversation thread ID")
    parent_message_id: Optional[str] = Field(None, description="Parent message ID")

    # Metadata
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")
    priority: int = Field(default=5, description="Message priority")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = Field(None)
    read_at: Optional[datetime] = Field(None)


class A2AProtocolManager:
    """
    Agent-to-Agent Protocol Manager

    Handles agent discovery, task delegation, and inter-agent communication
    following the A2A protocol specification.
    """

    def __init__(self, database_url: str, agent_registry_url: Optional[str] = None):
        self.database_url = database_url
        self.agent_registry_url = agent_registry_url
        self.pool = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Local agent registry
        self.local_agents: Dict[str, AgentCard] = {}

        # Message routing
        self.message_handlers: Dict[MessageType, callable] = {
            MessageType.TASK_REQUEST: self._handle_task_request,
            MessageType.TASK_RESPONSE: self._handle_task_response,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ARTIFACT: self._handle_artifact,
            MessageType.COLLABORATION: self._handle_collaboration,
            MessageType.HANDOFF: self._handle_handoff,
        }

    async def initialize(self):
        """Initialize the A2A protocol manager"""
        self.pool = await asyncpg.create_pool(
            self.database_url, min_size=2, max_size=10, command_timeout=60
        )

        # Create A2A tables if they don't exist
        await self._create_a2a_tables()

        # Load local agent registry
        await self._load_local_agents()

        logger.info("A2A Protocol Manager initialized")

    async def close(self):
        """Close the A2A protocol manager"""
        if self.http_client:
            await self.http_client.aclose()
        if self.pool:
            await self.pool.close()

    async def _create_a2a_tables(self):
        """Create A2A protocol tables"""
        async with self.pool.acquire() as conn:
            # Agent cards table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS a2a_agent_cards (
                    agent_id VARCHAR(255) PRIMARY KEY,
                    card_data JSONB NOT NULL,
                    capabilities TEXT[] DEFAULT ARRAY[]::TEXT[],
                    skills TEXT[] DEFAULT ARRAY[]::TEXT[],
                    availability_status VARCHAR(50) DEFAULT 'available',
                    current_task_count INTEGER DEFAULT 0,
                    max_concurrent_tasks INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            )

            # A2A tasks table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS a2a_tasks (
                    task_id VARCHAR(255) PRIMARY KEY,
                    task_data JSONB NOT NULL,
                    requesting_agent_id VARCHAR(255) NOT NULL,
                    assigned_agent_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
            """
            )

            # A2A messages table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS a2a_messages (
                    message_id VARCHAR(255) PRIMARY KEY,
                    message_data JSONB NOT NULL,
                    sender_agent_id VARCHAR(255) NOT NULL,
                    recipient_agent_id VARCHAR(255) NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    task_id VARCHAR(255),
                    conversation_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered_at TIMESTAMP,
                    read_at TIMESTAMP
                );
            """
            )

            # Create indexes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_a2a_agent_cards_capabilities 
                ON a2a_agent_cards USING GIN(capabilities);
                
                CREATE INDEX IF NOT EXISTS idx_a2a_agent_cards_skills 
                ON a2a_agent_cards USING GIN(skills);
                
                CREATE INDEX IF NOT EXISTS idx_a2a_tasks_status 
                ON a2a_tasks(status, created_at DESC);
                
                CREATE INDEX IF NOT EXISTS idx_a2a_tasks_agent 
                ON a2a_tasks(assigned_agent_id, status);
                
                CREATE INDEX IF NOT EXISTS idx_a2a_messages_conversation 
                ON a2a_messages(conversation_id, created_at DESC);
            """
            )

    async def _load_local_agents(self):
        """Load local agents into the registry"""
        async with self.pool.acquire() as conn:
            # Get all agents from the main agent table
            agents = await conn.fetch(
                """
                SELECT a.id, a.name, a.role, a.type, a.config, a.team_id,
                       t.organization_id
                FROM agents a
                LEFT JOIN teams t ON a.team_id = t.id
                WHERE a.status = 'active'
            """
            )

            for agent in agents:
                agent_card = await self._create_agent_card_from_agent(dict(agent))
                self.local_agents[agent["id"]] = agent_card

                # Store in database
                await self._store_agent_card(agent_card)

        logger.info(f"Loaded {len(self.local_agents)} local agents into A2A registry")

    async def _create_agent_card_from_agent(
        self, agent_data: Dict[str, Any]
    ) -> AgentCard:
        """Create an A2A agent card from agent data"""

        config = agent_data.get("config", {})

        # Extract capabilities and skills from config
        capabilities = []
        skills = config.get("skills", [])
        tools = config.get("tools", [])

        # Map agent type to capabilities
        type_capabilities = {
            "python_developer": [
                "code_generation",
                "debugging",
                "testing",
                "code_review",
            ],
            "typescript_developer": [
                "frontend_development",
                "api_development",
                "testing",
            ],
            "react_developer": [
                "ui_development",
                "component_design",
                "frontend_testing",
            ],
            "devops_engineer": [
                "infrastructure",
                "deployment",
                "monitoring",
                "security",
            ],
            "qa_engineer": ["testing", "quality_assurance", "bug_reporting"],
            "claude_ai_developer": [
                "ai_development",
                "intelligent_coding",
                "automated_testing",
            ],
        }

        capabilities = type_capabilities.get(
            agent_data.get("type", ""), ["general_assistance"]
        )

        # Create endpoints
        agent_id = agent_data["id"]
        endpoints = {
            "task_assignment": f"/a2a/agents/{agent_id}/tasks",
            "status": f"/a2a/agents/{agent_id}/status",
            "communication": f"/a2a/agents/{agent_id}/messages",
            "handoff": f"/a2a/agents/{agent_id}/handoff",
        }

        return AgentCard(
            agent_id=agent_id,
            name=agent_data["name"],
            description=f"{agent_data['role']} - {config.get('backstory', 'Specialized AI agent')}",
            capabilities=capabilities,
            skills=skills,
            tools=tools,
            endpoints=endpoints,
            team_id=agent_data.get("team_id"),
            organization_id=agent_data.get("organization_id"),
            tags=[
                agent_data.get("type", "general"),
                agent_data.get("role", "").lower().replace(" ", "_"),
            ],
        )

    async def _store_agent_card(self, agent_card: AgentCard):
        """Store agent card in database"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO a2a_agent_cards (
                    agent_id, card_data, capabilities, skills,
                    availability_status, current_task_count, max_concurrent_tasks
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (agent_id) DO UPDATE SET
                    card_data = EXCLUDED.card_data,
                    capabilities = EXCLUDED.capabilities,
                    skills = EXCLUDED.skills,
                    availability_status = EXCLUDED.availability_status,
                    updated_at = CURRENT_TIMESTAMP
            """,
                agent_card.agent_id,
                agent_card.dict(),
                agent_card.capabilities,
                agent_card.skills,
                agent_card.availability_status,
                agent_card.current_task_count,
                agent_card.max_concurrent_tasks,
            )

    async def discover_agents(
        self,
        capabilities: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        availability_only: bool = True,
        team_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[AgentCard]:
        """Discover agents based on criteria"""

        async with self.pool.acquire() as conn:
            where_conditions = []
            params = []
            param_count = 1

            if availability_only:
                where_conditions.append("availability_status = 'available'")
                where_conditions.append("current_task_count < max_concurrent_tasks")

            if capabilities:
                where_conditions.append(f"capabilities && ${param_count}")
                params.append(capabilities)
                param_count += 1

            if skills:
                where_conditions.append(f"skills && ${param_count}")
                params.append(skills)
                param_count += 1

            if team_id:
                where_conditions.append(f"(card_data->>'team_id') = ${param_count}")
                params.append(team_id)
                param_count += 1

            if organization_id:
                where_conditions.append(
                    f"(card_data->>'organization_id') = ${param_count}"
                )
                params.append(organization_id)
                param_count += 1

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            results = await conn.fetch(
                f"""
                SELECT card_data FROM a2a_agent_cards 
                {where_clause}
                ORDER BY 
                    CASE availability_status 
                        WHEN 'available' THEN 1 
                        WHEN 'busy' THEN 2 
                        ELSE 3 
                    END,
                    current_task_count ASC
            """,
                *params,
            )

            return [AgentCard(**result["card_data"]) for result in results]

    async def delegate_task(
        self,
        requesting_agent_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        target_agent_id: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        required_skills: Optional[List[str]] = None,
        priority: int = 5,
        deadline: Optional[datetime] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Delegate a task to another agent"""

        # Find suitable agent if not specified
        if not target_agent_id:
            suitable_agents = await self.discover_agents(
                capabilities=required_capabilities,
                skills=required_skills,
                availability_only=True,
            )

            if not suitable_agents:
                raise ValueError("No suitable agents found for task delegation")

            # Select the agent with lowest current task count
            target_agent_id = min(
                suitable_agents, key=lambda a: a.current_task_count
            ).agent_id

        # Create task
        task = A2ATask(
            task_id=str(uuid.uuid4()),
            title=task_title,
            description=task_description,
            task_type=task_type,
            requesting_agent_id=requesting_agent_id,
            assigned_agent_id=target_agent_id,
            priority=priority,
            deadline=deadline,
            input_data=input_data or {},
        )

        # Store task
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO a2a_tasks (
                    task_id, task_data, requesting_agent_id, 
                    assigned_agent_id, status, priority
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
                task.task_id,
                task.dict(),
                task.requesting_agent_id,
                task.assigned_agent_id,
                task.status.value,
                task.priority,
            )

            # Update agent task count
            await conn.execute(
                """
                UPDATE a2a_agent_cards 
                SET current_task_count = current_task_count + 1,
                    availability_status = CASE 
                        WHEN current_task_count + 1 >= max_concurrent_tasks THEN 'busy'
                        ELSE 'available'
                    END
                WHERE agent_id = $1
            """,
                target_agent_id,
            )

        # Send task request message
        await self.send_message(
            sender_agent_id=requesting_agent_id,
            recipient_agent_id=target_agent_id,
            message_type=MessageType.TASK_REQUEST,
            content=f"New task assignment: {task_title}",
            data={"task_id": task.task_id, "task_data": task.dict()},
            task_id=task.task_id,
        )

        logger.info(
            f"Task {task.task_id} delegated from {requesting_agent_id} to {target_agent_id}"
        )
        return task.task_id

    async def send_message(
        self,
        sender_agent_id: str,
        recipient_agent_id: str,
        message_type: MessageType,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        priority: int = 5,
    ) -> str:
        """Send a message between agents"""

        message = A2AMessage(
            message_type=message_type,
            sender_agent_id=sender_agent_id,
            recipient_agent_id=recipient_agent_id,
            content=content,
            data=data or {},
            task_id=task_id,
            conversation_id=conversation_id,
            priority=priority,
        )

        # Store message
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO a2a_messages (
                    message_id, message_data, sender_agent_id, 
                    recipient_agent_id, message_type, task_id, conversation_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                message.message_id,
                message.dict(),
                message.sender_agent_id,
                message.recipient_agent_id,
                message.message_type.value,
                message.task_id,
                message.conversation_id,
            )

        # Route message to handler
        handler = self.message_handlers.get(message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error handling message {message.message_id}: {e}")

        logger.debug(
            f"Message {message.message_id} sent from {sender_agent_id} to {recipient_agent_id}"
        )
        return message.message_id

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress_percentage: Optional[int] = None,
        output_data: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ):
        """Update task status and notify relevant agents"""

        async with self.pool.acquire() as conn:
            # Get current task
            task_row = await conn.fetchrow(
                """
                SELECT task_data, requesting_agent_id, assigned_agent_id 
                FROM a2a_tasks 
                WHERE task_id = $1
            """,
                task_id,
            )

            if not task_row:
                raise ValueError(f"Task {task_id} not found")

            task_data = task_row["task_data"]
            task = A2ATask(**task_data)

            # Update task
            task.status = status
            if progress_percentage is not None:
                task.progress_percentage = progress_percentage
            if output_data:
                task.output_data.update(output_data)

            if status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now()
            elif status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                task.completed_at = datetime.now()

                # Update agent task count
                await conn.execute(
                    """
                    UPDATE a2a_agent_cards 
                    SET current_task_count = GREATEST(current_task_count - 1, 0),
                        availability_status = CASE 
                            WHEN current_task_count - 1 < max_concurrent_tasks THEN 'available'
                            ELSE availability_status
                        END
                    WHERE agent_id = $1
                """,
                    task.assigned_agent_id,
                )

            task.updated_at = datetime.now()

            # Update task in database
            await conn.execute(
                """
                UPDATE a2a_tasks 
                SET task_data = $2, status = $3, updated_at = CURRENT_TIMESTAMP,
                    completed_at = $4
                WHERE task_id = $1
            """,
                task_id,
                task.dict(),
                status.value,
                task.completed_at,
            )

        # Send status update to requesting agent
        if agent_id != task.requesting_agent_id:
            await self.send_message(
                sender_agent_id=task.assigned_agent_id or "system",
                recipient_agent_id=task.requesting_agent_id,
                message_type=MessageType.STATUS_UPDATE,
                content=f"Task {task.title} status updated to {status.value}",
                data={
                    "task_id": task_id,
                    "status": status.value,
                    "progress_percentage": task.progress_percentage,
                    "output_data": task.output_data,
                },
                task_id=task_id,
            )

    # Message handlers
    async def _handle_task_request(self, message: A2AMessage):
        """Handle incoming task request"""
        # This would typically trigger agent processing
        logger.info(f"Task request received: {message.task_id}")

    async def _handle_task_response(self, message: A2AMessage):
        """Handle task response"""
        logger.info(f"Task response received: {message.task_id}")

    async def _handle_status_update(self, message: A2AMessage):
        """Handle status update"""
        logger.info(f"Status update received for task: {message.task_id}")

    async def _handle_artifact(self, message: A2AMessage):
        """Handle artifact sharing"""
        logger.info(f"Artifact shared: {message.message_id}")

    async def _handle_collaboration(self, message: A2AMessage):
        """Handle collaboration request"""
        logger.info(f"Collaboration request: {message.message_id}")

    async def _handle_handoff(self, message: A2AMessage):
        """Handle task handoff"""
        logger.info(f"Task handoff: {message.message_id}")

    async def get_agent_tasks(
        self,
        agent_id: str,
        status_filter: Optional[List[TaskStatus]] = None,
        limit: int = 50,
    ) -> List[A2ATask]:
        """Get tasks for an agent"""

        async with self.pool.acquire() as conn:
            where_conditions = ["(requesting_agent_id = $1 OR assigned_agent_id = $1)"]
            params = [agent_id]
            param_count = 2

            if status_filter:
                status_values = [s.value for s in status_filter]
                where_conditions.append(f"status = ANY(${param_count})")
                params.append(status_values)
                param_count += 1

            where_clause = " AND ".join(where_conditions)

            results = await conn.fetch(
                f"""
                SELECT task_data FROM a2a_tasks 
                WHERE {where_clause}
                ORDER BY created_at DESC 
                LIMIT ${param_count}
            """,
                *params,
                limit,
            )

            return [A2ATask(**result["task_data"]) for result in results]

    async def get_agent_messages(
        self, agent_id: str, conversation_id: Optional[str] = None, limit: int = 50
    ) -> List[A2AMessage]:
        """Get messages for an agent"""

        async with self.pool.acquire() as conn:
            where_conditions = ["(sender_agent_id = $1 OR recipient_agent_id = $1)"]
            params = [agent_id]
            param_count = 2

            if conversation_id:
                where_conditions.append(f"conversation_id = ${param_count}")
                params.append(conversation_id)
                param_count += 1

            where_clause = " AND ".join(where_conditions)

            results = await conn.fetch(
                f"""
                SELECT message_data FROM a2a_messages 
                WHERE {where_clause}
                ORDER BY created_at DESC 
                LIMIT ${param_count}
            """,
                *params,
                limit,
            )

            return [A2AMessage(**result["message_data"]) for result in results]
