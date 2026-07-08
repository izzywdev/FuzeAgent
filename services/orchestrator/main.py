import asyncio
import json
import logging
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import jwt
from fastapi import (Body, Depends, FastAPI, File, Form, HTTPException, Path,
                     Query, UploadFile, WebSocket, WebSocketDisconnect, status)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from hierarchy_endpoints import router as hierarchy_router
from pydantic import BaseModel, Field

from .agent_manager import AgentManager
from .container_manager import (ContainerConfig, ContainerStatus,
                                container_manager)
from .context_service import ContextService
from .database import get_db_connection
from .knowledge_manager import DocumentMetadata, knowledge_manager
from .rag_integration import RAGContext, rag_system
from .sandbox_manager import AgentSandboxManager
from .task_execution_engine import TaskExecutionEngine
from .task_queue import TaskQueue
from .websocket_manager import (UpdateType, WebSocketUpdate,
                                notify_agent_status_change,
                                notify_container_status_change,
                                notify_knowledge_update, notify_task_progress,
                                websocket_manager)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth helpers (Track 3)
# ---------------------------------------------------------------------------
_security = HTTPBearer(auto_error=False)
_jwt_secret = os.environ.get("FUZEFRONT_JWT_SECRET", "")


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Verify FuzeFront JWT on mutating endpoints. Disabled when secret not set (dev)."""
    if not _jwt_secret:
        return None  # Auth disabled when secret not configured (dev mode)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


# ---------------------------------------------------------------------------
# Agent relay state (Track 4)
# ---------------------------------------------------------------------------
# agent_id -> list of subscriber WebSockets watching that agent's session
agent_relay_subscribers: Dict[str, List[WebSocket]] = defaultdict(list)


# Pydantic models for API documentation
class AgentCreateRequest(BaseModel):
    name: str = Field(..., description="Agent name")
    role: str = Field(..., description="Agent role (e.g., 'Senior React Developer')")
    type: str = Field(..., description="Agent type (e.g., 'developer', 'executive')")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Agent configuration"
    )
    repository_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Repository settings"
    )
    sandbox_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Sandbox settings"
    )


class TaskCreateRequest(BaseModel):
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: str = Field(
        default="medium", description="Task priority (low, medium, high)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional task metadata"
    )


class HumanResponseRequest(BaseModel):
    response: str = Field(..., description="Human response to agent question")


class FileOperationApprovalRequest(BaseModel):
    approved: bool = Field(..., description="Whether to approve the file operations")
    reason: Optional[str] = Field(
        None, description="Optional reason for approval/rejection"
    )


class ClaudeSessionInputRequest(BaseModel):
    input: str = Field(..., description="Input to send to Claude SDK session")


class CoordinationRequest(BaseModel):
    coordination_mode: str = Field(
        default="collaborative",
        description="Coordination mode (sequential, parallel, hierarchical, collaborative)",
    )
    required_agents: Optional[List[str]] = Field(
        None, description="Specific agents to include"
    )
    required_skills: Optional[List[str]] = Field(
        None, description="Required skills for the task"
    )


class AgentCommunicationRequest(BaseModel):
    message_type: str = Field(
        default="notification",
        description="Message type (request, response, notification, question)",
    )
    content: str = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MCPToolRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP tool to call")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class AgentMCPSetupRequest(BaseModel):
    task_id: str = Field(..., description="Task ID for MCP setup")
    session_id: Optional[str] = Field(None, description="Optional session ID")


class ConversationCreateRequest(BaseModel):
    title: str = "New Conversation"
    initial_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ConversationMessage(BaseModel):
    role: str  # 'user' or 'agent'
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


# Model Configuration Models
class ProviderCredentialsRequest(BaseModel):
    provider: str = Field(
        ..., description="Model provider (anthropic, openai, google, etc.)"
    )
    api_key: str = Field(..., description="API key for the provider")
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL")
    additional_config: Dict[str, Any] = Field(
        default_factory=dict, description="Additional provider configuration"
    )


class AgentModelConfigRequest(BaseModel):
    primary_model: str = Field(..., description="Primary model ID")
    fallback_models: List[str] = Field(
        default_factory=list, description="Fallback model IDs"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: int = Field(
        default=4096, ge=1, le=200000, description="Maximum output tokens"
    )
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    custom_instructions: str = Field(
        default="", description="Custom instructions for the agent"
    )
    use_function_calling: bool = Field(
        default=True, description="Enable function calling"
    )
    streaming_enabled: bool = Field(
        default=True, description="Enable response streaming"
    )
    cost_limit_per_task: Optional[float] = Field(
        None, ge=0.0, description="Cost limit per task in USD"
    )


class TaskCostEstimateRequest(BaseModel):
    task_description: str = Field(..., description="Description of the task")
    estimated_complexity: str = Field(
        default="medium",
        description="Estimated complexity (low, medium, high, very_high)",
    )


# Response models
class AgentResponse(BaseModel):
    agent_id: str
    status: str
    agent: Dict[str, Any]


class TaskResponse(BaseModel):
    task_id: str
    status: str


class CoordinationResponse(BaseModel):
    task_id: str
    coordination_session_id: Optional[str] = None
    status: str
    coordination_mode: Optional[str] = None
    message: Optional[str] = None


# Goals Management API Models
class GoalCreateRequest(BaseModel):
    title: str = Field(..., description="Goal title")
    description: str = Field(..., description="Goal description")
    goal_type: str = Field(
        default="business",
        description="Goal type (business, technical, growth, operational)",
    )
    target_value: Optional[Decimal] = Field(
        None, description="Target value (e.g., 100000 for $100K)"
    )
    target_unit: Optional[str] = Field(
        None, description="Target unit (e.g., 'USD', 'users', '%')"
    )
    target_deadline: Optional[date] = Field(None, description="Target completion date")
    priority_level: int = Field(
        default=5, ge=1, le=10, description="Priority level (1-10)"
    )
    success_criteria: Optional[Dict[str, Any]] = Field(
        default=None, description="Success criteria"
    )
    assigned_teams: Optional[List[str]] = Field(
        default=None, description="Assigned team IDs"
    )
    goal_owner_agent_id: Optional[str] = Field(None, description="Goal owner agent ID")
    stakeholder_agents: Optional[List[str]] = Field(
        default=None, description="Stakeholder agent IDs"
    )
    tags: Optional[List[str]] = Field(default=None, description="Goal tags")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class GoalUpdateRequest(BaseModel):
    progress_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    current_value: Optional[Decimal] = Field(None, description="Current value")
    completion_confidence: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Completion confidence"
    )
    notes: Optional[str] = Field(None, description="Progress notes")


class MilestoneCreateRequest(BaseModel):
    title: str = Field(..., description="Milestone title")
    description: str = Field(..., description="Milestone description")
    target_date: date = Field(..., description="Target completion date")
    milestone_type: str = Field(default="deliverable", description="Milestone type")
    success_criteria: Optional[Dict[str, Any]] = Field(
        default=None, description="Success criteria"
    )
    deliverables: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Expected deliverables"
    )
    dependencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Dependencies"
    )
    assigned_teams: Optional[List[str]] = Field(
        default=None, description="Assigned teams"
    )
    responsible_agent_id: Optional[str] = Field(None, description="Responsible agent")
    priority_level: int = Field(default=5, ge=1, le=10, description="Priority level")
    weight_in_goal: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Weight in goal (%)"
    )


class TaskFromMilestoneRequest(BaseModel):
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    task_type: str = Field(default="development", description="Task type")
    complexity_level: str = Field(default="medium", description="Complexity level")
    estimated_hours: Optional[Decimal] = Field(None, description="Estimated hours")
    due_date: Optional[date] = Field(None, description="Due date")
    assigned_team_id: Optional[str] = Field(None, description="Assigned team ID")
    assigned_agent_id: Optional[str] = Field(None, description="Assigned agent ID")
    priority: int = Field(default=5, ge=1, le=10, description="Priority")
    requirements: Optional[Dict[str, Any]] = Field(
        default=None, description="Requirements"
    )
    acceptance_criteria: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Acceptance criteria"
    )
    dependencies: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Dependencies"
    )


class GoalConversationCreateRequest(BaseModel):
    conversation_type: str = Field(default="planning", description="Conversation type")
    conversation_title: str = Field(..., description="Conversation title")
    initial_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Initial context"
    )
    participants: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Participants"
    )


class ConversationMessageRequest(BaseModel):
    message_type: str = Field(default="human", description="Message type")
    sender_name: str = Field(..., description="Sender name")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Message metadata"
    )
    references: Optional[List[str]] = Field(
        default=None, description="Referenced message IDs"
    )


class ProgressUpdateRequest(BaseModel):
    progress_percentage: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    current_value: Optional[Decimal] = Field(None, description="Current value")
    milestone_id: Optional[str] = Field(None, description="Associated milestone ID")
    notes: Optional[str] = Field(None, description="Progress notes")
    confidence_score: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Confidence score"
    )
    trigger_alerts: bool = Field(default=True, description="Whether to trigger alerts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
    )

    app.state.agent_manager = AgentManager(database_url)
    app.state.task_queue = TaskQueue()
    app.state.context_service = ContextService()

    # Initialize sandbox manager
    app.state.sandbox_manager = AgentSandboxManager(database_url)
    await app.state.sandbox_manager.start()

    # Start WebSocket manager background cleanup task
    await websocket_manager.start()

    # Initialize task execution engine
    app.state.task_execution_engine = TaskExecutionEngine(app.state.sandbox_manager)
    await app.state.task_execution_engine.start()

    # Initialize multi-agent coordinator
    from .multi_agent_coordinator import integrate_multi_agent_coordination

    app.state.multi_agent_coordinator = integrate_multi_agent_coordination(
        app.state.task_execution_engine
    )
    await app.state.multi_agent_coordinator.start()

    # Initialize knowledge management system
    try:
        from .context_enhancement_service import ContextEnhancementService
        from .knowledge_notification_service import \
            KnowledgeNotificationService
        from .knowledge_propagation_engine import KnowledgePropagationEngine
        from .organization_rag_manager import OrganizationRAGManager
        from .task_knowledge_extractor import TaskKnowledgeExtractor
        from .team_knowledge_manager import TeamKnowledgeManager

        app.state.org_rag_manager = OrganizationRAGManager(database_url)
        await app.state.org_rag_manager.initialize()

        app.state.team_knowledge_manager = TeamKnowledgeManager(database_url)
        await app.state.team_knowledge_manager.initialize()

        app.state.knowledge_propagation_engine = KnowledgePropagationEngine(
            database_url, app.state.org_rag_manager, app.state.team_knowledge_manager
        )
        await app.state.knowledge_propagation_engine.initialize()

        app.state.notification_service = KnowledgeNotificationService(database_url)
        await app.state.notification_service.initialize()

        app.state.task_knowledge_extractor = TaskKnowledgeExtractor(
            database_url,
            app.state.org_rag_manager,
            app.state.team_knowledge_manager,
            app.state.knowledge_propagation_engine,
        )
        await app.state.task_knowledge_extractor.initialize()

        app.state.context_enhancement_service = ContextEnhancementService(
            database_url, app.state.org_rag_manager, app.state.team_knowledge_manager
        )
        await app.state.context_enhancement_service.initialize()

        # Initialize knowledge analytics service
        from .knowledge_analytics_service import KnowledgeAnalyticsService

        app.state.knowledge_analytics_service = KnowledgeAnalyticsService(database_url)
        await app.state.knowledge_analytics_service.initialize()

        logger.info("Knowledge management system initialized successfully")

    except Exception as e:
        logger.warning(f"Failed to initialize knowledge management system: {e}")

    # Initialize goals management system
    try:
        from .goal_conversation_service import GoalConversationService
        from .goal_tracking_service import GoalTrackingService
        from .goals_management_service import GoalsManagementService
        from .milestone_task_engine import MilestoneTaskEngine

        app.state.goals_service = GoalsManagementService(database_url)
        await app.state.goals_service.initialize()

        app.state.milestone_task_engine = MilestoneTaskEngine(database_url)
        await app.state.milestone_task_engine.initialize()

        app.state.goal_conversation_service = GoalConversationService(database_url)
        await app.state.goal_conversation_service.initialize()

        app.state.goal_tracking_service = GoalTrackingService(database_url)
        await app.state.goal_tracking_service.initialize()

        logger.info("Goals management system initialized successfully")

    except Exception as e:
        logger.warning(f"Failed to initialize goals management system: {e}")

    # Connect components
    app.state.task_queue.set_task_execution_engine(app.state.task_execution_engine)
    await app.state.agent_manager.set_sandbox_manager(app.state.sandbox_manager)

    # Initialize IzzyAI CEO on startup
    try:
        await app.state.agent_manager.create_agent(
            name="IzzyAI",
            role="Digital CEO",
            type="executive",
            config={
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7,
                "tools": [
                    "strategic_planning",
                    "resource_allocation",
                    "team_management",
                ],
            },
        )
    except Exception as e:
        print(f"Warning: Could not create IzzyAI CEO: {e}")

    yield

    # Shutdown
    await app.state.multi_agent_coordinator.stop()
    await app.state.task_execution_engine.stop()
    await app.state.sandbox_manager.stop()
    await app.state.agent_manager.shutdown_all()
    await app.state.task_queue.close()

    # Shutdown knowledge management services
    try:
        if hasattr(app.state, "knowledge_analytics_service"):
            await app.state.knowledge_analytics_service.close()
        if hasattr(app.state, "context_enhancement_service"):
            await app.state.context_enhancement_service.close()
        if hasattr(app.state, "task_knowledge_extractor"):
            await app.state.task_knowledge_extractor.close()
        if hasattr(app.state, "notification_service"):
            await app.state.notification_service.close()
        if hasattr(app.state, "knowledge_propagation_engine"):
            await app.state.knowledge_propagation_engine.close()
        if hasattr(app.state, "team_knowledge_manager"):
            await app.state.team_knowledge_manager.close()
        if hasattr(app.state, "org_rag_manager"):
            await app.state.org_rag_manager.close()
        logger.info("Knowledge management system shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down knowledge management system: {e}")

    # Shutdown goals management services
    try:
        if hasattr(app.state, "goal_tracking_service"):
            await app.state.goal_tracking_service.close()
        if hasattr(app.state, "goal_conversation_service"):
            await app.state.goal_conversation_service.close()
        if hasattr(app.state, "milestone_task_engine"):
            await app.state.milestone_task_engine.close()
        if hasattr(app.state, "goals_service"):
            await app.state.goals_service.close()
        logger.info("Goals management system shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down goals management system: {e}")


app = FastAPI(
    title="FuzeAgent Orchestrator API",
    description="""
    ## FuzeAgent AI Team Orchestration Platform

    A comprehensive platform for autonomous AI development teams that enables:
    
    ### 🤖 Autonomous Agent Execution
    - **Claude SDK Integration**: Interactive AI development with real-time conversation streaming
    - **File Operations Engine**: Safe code changes with human approval workflows
    - **Multi-Agent Coordination**: Complex task decomposition and agent collaboration
    
    ### 🏗️ Core Features
    - **Agent Management**: Create, configure, and manage AI development agents
    - **Task Orchestration**: Assign and monitor complex development tasks
    - **Real-time Monitoring**: WebSocket streaming for live progress updates
    - **Human-in-the-Loop**: Seamless approval workflows for critical decisions
    
    ### 🔗 Integration Capabilities
    - **MCP (Model Context Protocol)**: Organizational context for AI agents
    - **Git Workflow Management**: Automated repository operations
    - **Sandbox Environments**: Isolated development containers
    - **Database Integration**: PostgreSQL for persistent storage
    
    ### 📡 API Categories
    - **Agent Management**: Create and manage AI agents
    - **Task Execution**: Autonomous task processing
    - **File Operations**: Code change management
    - **Multi-Agent Coordination**: Team collaboration
    - **Real-time Communication**: WebSocket endpoints
    - **MCP Integration**: Organizational context tools
    - **Goals Management**: Organizational goals, milestones, and task planning
    - **Knowledge Management**: RAG system and organizational memory
    
    **Version**: 2.0.0 (Autonomous Execution)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "health", "description": "Health check and system status endpoints"},
        {
            "name": "agents",
            "description": "AI agent creation, management, and status monitoring",
        },
        {"name": "tasks", "description": "Task assignment, execution, and monitoring"},
        {
            "name": "autonomous-execution",
            "description": "Autonomous task execution with Claude SDK integration",
        },
        {
            "name": "file-operations",
            "description": "File system operations and code change management",
        },
        {
            "name": "multi-agent-coordination",
            "description": "Multi-agent collaboration and task coordination",
        },
        {
            "name": "real-time",
            "description": "WebSocket endpoints for real-time updates",
        },
        {
            "name": "human-in-loop",
            "description": "Human approval workflows and interaction handling",
        },
        {
            "name": "mcp-integration",
            "description": "Model Context Protocol tools and resources",
        },
        {"name": "sandboxes", "description": "Sandbox environment management"},
        {"name": "context", "description": "Agent memory and context management"},
        {
            "name": "model-configuration",
            "description": "AI model configuration and API key management",
        },
        {
            "name": "knowledge-management",
            "description": "Hierarchical knowledge management, RAG, and intelligent notifications",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3031",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include hierarchy router for organizational visualization
app.include_router(hierarchy_router)


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check the health status of the FuzeAgent orchestrator service",
    response_description="Service health status",
)
async def health_check():
    """
    Health check endpoint that returns the current status of the orchestrator service.

    Returns:
        dict: Service health status and basic information
    """
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "2.0.0",
        "features": {
            "autonomous_execution": True,
            "multi_agent_coordination": True,
            "file_operations": True,
            "mcp_integration": True,
            "real_time_streaming": True,
        },
    }


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send agent updates to UI
            updates = await app.state.agent_manager.get_updates()
            await websocket.send_json(updates)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# WebSocket for task execution updates
@app.websocket("/ws/tasks/{task_id}")
async def task_websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task execution updates"""
    await websocket.accept()
    try:
        while True:
            # Get task execution status
            try:
                status = await app.state.task_queue.get_execution_status(task_id)
                await websocket.send_json(
                    {"type": "status_update", "task_id": task_id, "data": status}
                )

                # If task is completed or failed, send final update and close
                if status.get("status") in ["completed", "failed", "cancelled"]:
                    await websocket.send_json(
                        {
                            "type": "task_finished",
                            "task_id": task_id,
                            "final_status": status.get("status"),
                        }
                    )
                    break

            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "task_id": task_id, "error": str(e)}
                )

            await asyncio.sleep(2)  # Update every 2 seconds

    except Exception as e:
        print(f"Task WebSocket error for {task_id}: {e}")
    finally:
        await websocket.close()


# WebSocket for real-time Claude SDK conversation streaming
@app.websocket("/ws/tasks/{task_id}/conversation")
async def conversation_websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time Claude SDK conversation streaming"""
    await websocket.accept()
    try:
        # Get execution context
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution:
            await websocket.send_json(
                {"type": "error", "message": f"Task {task_id} not found or not active"}
            )
            await websocket.close()
            return

        # Wait for Claude SDK session to be available
        while not execution.claude_session_id and execution.status not in [
            "completed",
            "failed",
            "cancelled",
        ]:
            await asyncio.sleep(1)

        if not execution.claude_session_id:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "No active Claude SDK session for this task",
                }
            )
            await websocket.close()
            return

        # Stream Claude SDK output
        claude_sdk_manager = execution.claude_sdk_manager
        if claude_sdk_manager:
            try:
                async for output_chunk in claude_sdk_manager.stream_output(
                    execution.claude_session_id
                ):
                    await websocket.send_json(
                        {
                            "type": "claude_output",
                            "task_id": task_id,
                            "content": output_chunk,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                # Session ended
                await websocket.send_json(
                    {
                        "type": "conversation_ended",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error streaming conversation: {str(e)}",
                    }
                )

    except Exception as e:
        print(f"Conversation WebSocket error for {task_id}: {e}")
    finally:
        await websocket.close()


# WebSocket for file operations streaming
@app.websocket("/ws/tasks/{task_id}/file-operations")
async def file_operations_websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time file operations updates"""
    await websocket.accept()
    try:
        # Get execution context
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution:
            await websocket.send_json(
                {"type": "error", "message": f"Task {task_id} not found or not active"}
            )
            await websocket.close()
            return

        file_ops_engine = execution.file_operations_engine
        if not file_ops_engine:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "No file operations engine available for this task",
                }
            )
            await websocket.close()
            return

        last_batch_count = 0

        while execution.status not in ["completed", "failed", "cancelled"]:
            try:
                # Get pending operations
                pending_operations = file_ops_engine.get_pending_operations()
                applied_operations = file_ops_engine.get_applied_operations()

                current_batch_count = len(pending_operations) + len(applied_operations)

                # Send updates if there are new operations
                if current_batch_count > last_batch_count:
                    # Send pending operations
                    for batch in pending_operations:
                        # Get diff preview
                        diffs = await file_ops_engine.get_file_diff_preview(
                            batch.batch_id
                        )

                        await websocket.send_json(
                            {
                                "type": "pending_operations",
                                "task_id": task_id,
                                "batch_id": batch.batch_id,
                                "description": batch.description,
                                "requires_approval": batch.requires_approval,
                                "operations_count": len(batch.operations),
                                "file_diffs": diffs,
                                "timestamp": batch.created_at.isoformat(),
                            }
                        )

                    # Send applied operations
                    for batch in applied_operations:
                        await websocket.send_json(
                            {
                                "type": "applied_operations",
                                "task_id": task_id,
                                "batch_id": batch.batch_id,
                                "description": batch.description,
                                "operations_count": len(batch.operations),
                                "applied_at": (
                                    batch.applied_at.isoformat()
                                    if batch.applied_at
                                    else None
                                ),
                                "timestamp": batch.created_at.isoformat(),
                            }
                        )

                    last_batch_count = current_batch_count

                await asyncio.sleep(1)  # Check every second

            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error getting file operations: {str(e)}",
                    }
                )

        # Task completed
        await websocket.send_json(
            {
                "type": "task_completed",
                "task_id": task_id,
                "final_status": execution.status.value,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        print(f"File operations WebSocket error for {task_id}: {e}")
    finally:
        await websocket.close()


# Agent Management Endpoints
@app.post(
    "/agents",
    tags=["agents"],
    summary="Create AI Agent",
    description="Create a new AI agent with repository and sandbox settings",
    response_model=AgentResponse,
)
async def create_agent(agent_config: AgentCreateRequest, _auth=Depends(require_auth)):
    """Create a new AI agent with repository and sandbox settings"""
    try:
        agent = await app.state.agent_manager.create_agent(**agent_config)
        return {
            "agent_id": agent.id,
            "status": "created",
            "agent": {
                "id": agent.id,
                "name": agent_config.get("name"),
                "role": agent_config.get("role"),
                "type": agent_config.get("type"),
                "repository_settings": agent_config.get("repository_settings", {}),
                "sandbox_settings": agent_config.get("sandbox_settings", {}),
                "created_at": (
                    agent.created_at if hasattr(agent, "created_at") else None
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create agent: {str(e)}")


@app.get(
    "/agents",
    tags=["agents"],
    summary="List All Agents",
    description="Get a list of all AI agents and their current status",
)
async def list_agents():
    """List all agents and their status"""
    return await app.state.agent_manager.list_agents()


@app.post(
    "/agents/{agent_id}/tasks",
    tags=["tasks"],
    summary="Assign Task to Agent",
    description="Assign a specific task to an AI agent",
    response_model=TaskResponse,
)
async def assign_task(
    agent_id: str = Path(..., description="Agent ID"),
    task: TaskCreateRequest = Body(...),
    _auth=Depends(require_auth),
):
    """Assign a task to an agent"""
    task_id = await app.state.task_queue.assign_task(agent_id, task)
    return {"task_id": task_id, "status": "assigned"}


@app.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get detailed agent status"""
    return await app.state.agent_manager.get_agent_status(agent_id)


@app.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str):
    """Get tasks assigned to an agent"""
    try:
        # This would normally query the database for tasks assigned to the agent
        # For now, return mock data
        return [
            {
                "id": "1",
                "title": "Strategic Planning Q4 2025",
                "description": "Develop comprehensive strategic plan for Q4 2025 expansion",
                "status": "completed",
                "priority": "high",
                "created_at": "2025-08-05T09:00:00Z",
                "completed_at": "2025-08-05T17:30:00Z",
            },
            {
                "id": "2",
                "title": "Team Performance Review",
                "description": "Conduct quarterly performance review for all team leads",
                "status": "in_progress",
                "priority": "medium",
                "created_at": "2025-08-06T08:00:00Z",
            },
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent tasks: {str(e)}"
        )


@app.get("/teams")
async def list_teams():
    """List all teams"""
    try:
        # This would normally query the database for teams
        # For now, return mock data
        return [
            {
                "id": "1",
                "name": "Executive Team",
                "description": "Strategic leadership and decision making",
            },
            {
                "id": "2",
                "name": "Development Team",
                "description": "Frontend, backend, and full-stack development",
            },
            {
                "id": "3",
                "name": "Quality Assurance",
                "description": "Testing, quality control, and bug detection",
            },
            {
                "id": "4",
                "name": "DevOps Team",
                "description": "Infrastructure, deployment, and system operations",
            },
            {
                "id": "5",
                "name": "Business Team",
                "description": "Marketing, sales, and customer relations",
            },
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {str(e)}")


@app.get("/agent-templates")
async def list_agent_templates():
    """List available agent templates"""
    try:
        return [
            {
                "id": "react_developer",
                "name": "React Developer",
                "description": "Frontend developer specialized in React and TypeScript",
                "type": "developer",
                "defaultConfig": {
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "tools": ["code_generation", "code_review", "debugging", "testing"],
                    "goal": "Build responsive and performant React applications",
                    "backstory": "Experienced frontend developer with deep knowledge of React ecosystem",
                },
            },
            {
                "id": "python_developer",
                "name": "Python Developer",
                "description": "Backend developer specialized in Python and FastAPI",
                "type": "developer",
                "defaultConfig": {
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "tools": [
                        "code_generation",
                        "api_development",
                        "database_design",
                        "testing",
                    ],
                    "goal": "Develop robust and scalable backend systems",
                    "backstory": "Senior Python developer with expertise in FastAPI and databases",
                },
            },
            {
                "id": "qa_engineer",
                "name": "QA Engineer",
                "description": "Quality assurance engineer focused on testing and automation",
                "type": "qa",
                "defaultConfig": {
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.6,
                    "tools": [
                        "test_automation",
                        "bug_reporting",
                        "quality_analysis",
                        "performance_testing",
                    ],
                    "goal": "Ensure high quality and reliability of software products",
                    "backstory": "Experienced QA engineer with expertise in automated testing frameworks",
                },
            },
            {
                "id": "devops_engineer",
                "name": "DevOps Engineer",
                "description": "Infrastructure and deployment specialist",
                "type": "devops",
                "defaultConfig": {
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.5,
                    "tools": [
                        "infrastructure_management",
                        "deployment",
                        "monitoring",
                        "security",
                    ],
                    "goal": "Maintain reliable and scalable infrastructure",
                    "backstory": "DevOps engineer with expertise in cloud platforms and CI/CD",
                },
            },
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list agent templates: {str(e)}"
        )


@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return await app.state.task_queue.list_tasks()


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    return await app.state.task_queue.get_task(task_id)


# Autonomous Execution Endpoints
@app.post("/agents/from-template")
async def create_agent_from_template(request: dict):
    """Create agent from template with repository settings"""
    try:
        # Extract template data
        template_id = request.get("template_id")
        name = request.get("name")
        team_id = request.get("team_id")
        overrides = request.get("overrides", {})

        # Get template configuration
        template_config = await app.state.agent_manager.get_template_config(template_id)
        if not template_config:
            raise HTTPException(
                status_code=404, detail=f"Template {template_id} not found"
            )

        # Build agent configuration
        agent_config = {
            "name": name,
            "role": template_config.get("role", template_id.replace("_", " ").title()),
            "type": template_config.get("type", "specialized"),
            "template_id": template_id,
            "team_id": team_id,
            "config": {**template_config.get("config", {}), **overrides},
            "repository_settings": request.get("repository_settings", {}),
            "sandbox_settings": {
                "base_image": f"fuzeagent/dev-{template_id.split('_')[0]}:latest",
                "resource_limits": template_config.get(
                    "resource_limits", {"memory": "2Gi", "cpu": "1.0", "disk": "10Gi"}
                ),
                "auto_cleanup": "24h",
            },
        }

        # Create agent
        agent = await app.state.agent_manager.create_agent(**agent_config)

        return {
            "agent_id": agent.id,
            "status": "created",
            "agent": agent_config,
            "template_id": template_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create agent from template: {str(e)}"
        )


@app.get("/templates")
async def get_agent_templates():
    """Get available agent templates"""
    return await app.state.agent_manager.get_available_templates()


@app.post(
    "/tasks/{task_id}/execute",
    tags=["autonomous-execution"],
    summary="Start Autonomous Task Execution",
    description="Begin autonomous execution of a task using Claude SDK integration",
    response_model=TaskResponse,
)
async def start_task_execution(
    task_id: str = Path(..., description="Task ID to execute")
):
    """Start autonomous execution of a task"""
    try:
        # This will be handled by the TaskExecutionEngine
        result = await app.state.task_queue.start_autonomous_execution(task_id)
        return {"task_id": task_id, "status": "execution_started", "result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start task execution: {str(e)}"
        )


@app.get("/tasks/{task_id}/status")
async def get_task_execution_status(task_id: str):
    """Get detailed task execution status"""
    try:
        status = await app.state.task_queue.get_execution_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@app.get("/tasks/{task_id}/iterations")
async def get_task_iterations(task_id: str):
    """Get task iteration history"""
    try:
        iterations = await app.state.task_queue.get_task_iterations(task_id)
        return {"task_id": task_id, "iterations": iterations}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task iterations: {str(e)}"
        )


@app.get("/agents/{agent_id}/sandbox")
async def get_agent_sandbox(agent_id: str):
    """Get agent sandbox information"""
    try:
        sandbox_info = await app.state.agent_manager.get_agent_sandbox(agent_id)
        return sandbox_info
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent sandbox: {str(e)}"
        )


# Additional endpoints for UI support
@app.put("/tasks/{task_id}")
async def update_task(task_id: str, update_data: dict):
    """Update task status and result"""
    await app.state.task_queue.update_task_status(
        task_id=task_id,
        status=update_data.get("status"),
        result=update_data.get("result"),
    )
    return {"status": "updated"}


@app.post("/context/interactions")
async def store_interaction(interaction_data: dict):
    """Store agent interaction"""
    interaction_id = await app.state.context_service.store_interaction(
        agent_id=interaction_data.get("agent_id"),
        content=interaction_data.get("content"),
        metadata=interaction_data.get("metadata", {}),
    )
    return {"interaction_id": interaction_id}


@app.get("/context")
async def get_context(query: str, agent_id: str = None):
    """Get relevant context for a query"""
    context = await app.state.context_service.get_context(query, agent_id)
    return context


@app.get("/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, limit: int = 10):
    """Get agent memory"""
    memory = await app.state.context_service.get_agent_memory(agent_id, limit)
    return memory


# Agent Conversation Endpoints
@app.get(
    "/agents/{agent_id}/conversations",
    tags=["conversations"],
    summary="Get Agent Conversations",
    description="Get all conversations for a specific agent",
)
async def get_agent_conversations(agent_id: str):
    """Get all conversations for a specific agent"""
    try:
        async with get_db_connection() as conn:
            conversations = await conn.fetch(
                """
                SELECT cs.*, COUNT(ac.id) as message_count,
                       (SELECT content FROM agent_conversations 
                        WHERE session_id = cs.id 
                        ORDER BY created_at DESC LIMIT 1) as last_message
                FROM chat_sessions cs
                LEFT JOIN agent_conversations ac ON cs.id = ac.session_id
                WHERE cs.agent_id = $1
                GROUP BY cs.id
                ORDER BY cs.last_activity DESC
            """,
                agent_id,
            )

            return [dict(row) for row in conversations]

    except Exception as e:
        logger.error(f"Error getting agent conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/conversations",
    tags=["conversations"],
    summary="Create New Agent Conversation",
    description="Create a new conversation with an agent",
)
async def create_agent_conversation(agent_id: str, request: ConversationCreateRequest):
    """Create a new conversation with an agent"""
    try:
        async with get_db_connection() as conn:
            # Create new chat session
            session_id = await conn.fetchval(
                """
                INSERT INTO chat_sessions (agent_id, session_name, context, status)
                VALUES ($1, $2, $3, 'active')
                RETURNING id
            """,
                agent_id,
                request.title,
                request.context or {},
            )

            # Add initial message if provided
            if request.initial_message:
                await conn.execute(
                    """
                    INSERT INTO agent_conversations (session_id, agent_id, message_type, content)
                    VALUES ($1, $2, 'system', $3)
                """,
                    session_id,
                    agent_id,
                    request.initial_message,
                )

            # Get the created conversation
            conversation = await conn.fetchrow(
                """
                SELECT * FROM chat_sessions WHERE id = $1
            """,
                session_id,
            )

            return dict(conversation)

    except Exception as e:
        logger.error(f"Error creating agent conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/agents/{agent_id}/conversations/{conversation_id}/messages",
    tags=["conversations"],
    summary="Get Conversation Messages",
    description="Get all messages in a conversation",
)
async def get_conversation_messages(agent_id: str, conversation_id: str):
    """Get all messages in a conversation"""
    try:
        async with get_db_connection() as conn:
            messages = await conn.fetch(
                """
                SELECT * FROM agent_conversations 
                WHERE session_id = $1 AND agent_id = $2
                ORDER BY created_at ASC
            """,
                conversation_id,
                agent_id,
            )

            return [dict(row) for row in messages]

    except Exception as e:
        logger.error(f"Error getting conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/conversations/{conversation_id}/messages",
    tags=["conversations"],
    summary="Send Message to Agent",
    description="Send a message to an agent in a conversation",
)
async def send_message_to_agent(
    agent_id: str, conversation_id: str, request: ChatMessageRequest
):
    """Send a message to an agent in a conversation"""
    try:
        async with get_db_connection() as conn:
            # Insert user message
            user_message_id = await conn.fetchval(
                """
                INSERT INTO agent_conversations (session_id, agent_id, message_type, content, metadata)
                VALUES ($1, $2, 'user', $3, $4)
                RETURNING id
            """,
                conversation_id,
                agent_id,
                request.content,
                request.metadata or {},
            )

            # Update session last activity
            await conn.execute(
                """
                UPDATE chat_sessions 
                SET last_activity = CURRENT_TIMESTAMP, message_count = message_count + 1
                WHERE id = $1
            """,
                conversation_id,
            )

            # TODO: Here we would integrate with the actual agent to generate a response
            # For now, return a simple acknowledgment

            return {
                "id": str(user_message_id),
                "status": "sent",
                "message": "Message sent to agent",
            }

    except Exception as e:
        logger.error(f"Error sending message to agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Search knowledge base"""
    results = await app.state.context_service.search_knowledge(query, limit)
    return results


# Human-in-the-loop endpoints
@app.post(
    "/tasks/{task_id}/human-response",
    tags=["human-in-loop"],
    summary="Submit Human Response",
    description="Submit human response to a task question or approval request",
)
async def submit_human_response(
    task_id: str = Path(..., description="Task ID"),
    response_data: HumanResponseRequest = Body(...),
):
    """Submit human response to a task question"""
    try:
        response = response_data.get("response", "")
        if not response:
            raise HTTPException(status_code=400, detail="Response cannot be empty")

        success = await app.state.task_queue.handle_human_response(task_id, response)

        if success:
            return {"status": "success", "message": "Human response submitted"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Task not found or not waiting for human response",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit human response: {str(e)}"
        )


@app.post("/tasks/{task_id}/cancel")
async def cancel_task_execution(task_id: str):
    """Cancel autonomous execution of a task"""
    try:
        success = await app.state.task_queue.cancel_task_execution(task_id)

        if success:
            return {"status": "cancelled", "message": "Task execution cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Task not found or not running")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@app.get("/tasks/{task_id}/messages")
async def get_task_messages(task_id: str):
    """Get task messages and chat history"""
    try:
        # This would integrate with the HumanInTheLoopHandler when implemented
        # For now, return iteration history which includes human interactions
        iterations = await app.state.task_queue.get_task_iterations(task_id)

        messages = []
        for iteration in iterations:
            if iteration.get("human_question"):
                messages.append(
                    {
                        "type": "agent_question",
                        "content": iteration["human_question"],
                        "timestamp": iteration["started_at"],
                        "iteration": iteration["iteration_number"],
                    }
                )

            if iteration.get("human_response"):
                messages.append(
                    {
                        "type": "human_response",
                        "content": iteration["human_response"],
                        "timestamp": iteration["completed_at"]
                        or iteration["started_at"],
                        "iteration": iteration["iteration_number"],
                    }
                )

        return {"task_id": task_id, "messages": messages}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task messages: {str(e)}"
        )


# Sandbox management endpoints
@app.get("/sandboxes")
async def list_sandboxes(agent_id: str = None, status: str = None):
    """List active sandboxes"""
    try:
        from .sandbox_manager import SandboxStatus

        sandbox_status = None
        if status:
            try:
                sandbox_status = SandboxStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        sandboxes = await app.state.sandbox_manager.list_sandboxes(
            agent_id=agent_id, status=sandbox_status
        )

        return {
            "sandboxes": [
                {
                    "sandbox_id": s.sandbox_id,
                    "agent_id": s.agent_id,
                    "task_id": s.task_id,
                    "status": s.status.value,
                    "workspace_path": s.workspace_path,
                    "created_at": s.created_at.isoformat(),
                    "resource_limits": s.resource_limits,
                }
                for s in sandboxes
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list sandboxes: {str(e)}"
        )


@app.post("/sandboxes/{sandbox_id}/execute")
async def execute_command_in_sandbox(sandbox_id: str, command_data: dict):
    """Execute a command in a sandbox"""
    try:
        command = command_data.get("command")
        working_dir = command_data.get("working_dir")

        if not command:
            raise HTTPException(status_code=400, detail="Command is required")

        result = await app.state.sandbox_manager.execute_command(
            sandbox_id=sandbox_id, command=command, working_dir=working_dir
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to execute command: {str(e)}"
        )


@app.delete("/sandboxes/{sandbox_id}")
async def destroy_sandbox(sandbox_id: str):
    """Destroy a sandbox"""
    try:
        await app.state.sandbox_manager.destroy_sandbox(sandbox_id)
        return {"status": "destroyed", "sandbox_id": sandbox_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to destroy sandbox: {str(e)}"
        )


# Agent registration and communication endpoints
@app.post("/agents/{agent_id}/register")
async def register_agent(agent_id: str, registration_data: dict):
    """Register an agent running in a sandbox container"""
    try:
        # Store agent registration info
        # This would typically update the agent's status and capabilities
        return {
            "status": "registered",
            "agent_id": agent_id,
            "registered_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to register agent: {str(e)}"
        )


@app.get("/agents/{agent_id}/next-task")
async def get_next_task_for_agent(agent_id: str):
    """Get the next task for an agent to execute"""
    try:
        # Find pending tasks assigned to this agent
        tasks = await app.state.task_queue.get_agent_tasks(agent_id)
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]

        if pending_tasks:
            # Return the first pending task
            task = pending_tasks[0]
            # Update status to 'assigned' to prevent double assignment
            await app.state.task_queue.update_task_status(task["id"], "assigned")
            return task
        else:
            # No tasks available
            return None, 204

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get next task: {str(e)}"
        )


@app.post("/agents/{agent_id}/error")
async def report_agent_error(agent_id: str, error_data: dict):
    """Report an error from an agent"""
    try:
        # Log the error and update agent status
        logger.error(f"Agent {agent_id} reported error: {error_data.get('error')}")

        # You might want to store this in a database or alerting system
        return {"status": "error_logged", "agent_id": agent_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to log agent error: {str(e)}"
        )


# Conversation management endpoints
@app.get("/tasks/{task_id}/conversation")
async def get_task_conversation(task_id: str, iteration: int = None, limit: int = 100):
    """Get conversation history for a task"""
    try:
        conversation_history = await app.state.task_execution_engine.conversation_manager.get_conversation_history(
            task_id=task_id, iteration_number=iteration, limit=limit
        )

        return {"task_id": task_id, "conversation": conversation_history}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation: {str(e)}"
        )


@app.get("/tasks/{task_id}/conversation/summary")
async def get_conversation_summary(task_id: str):
    """Get conversation summary with statistics"""
    try:
        summary = await app.state.task_execution_engine.conversation_manager.get_conversation_summary(
            task_id
        )
        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation summary: {str(e)}"
        )


@app.get("/tasks/{task_id}/code-generations")
async def get_task_code_generations(
    task_id: str, iteration: int = None, file_type: str = None
):
    """Get code generations for a task"""
    try:
        code_generations = await app.state.task_execution_engine.conversation_manager.get_code_generations(
            task_id=task_id, iteration_number=iteration, file_type=file_type
        )

        return {"task_id": task_id, "code_generations": code_generations}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get code generations: {str(e)}"
        )


@app.get("/agents/{agent_id}/performance")
async def get_agent_performance(agent_id: str, hours: int = 24):
    """Get agent performance metrics"""
    try:
        metrics = await app.state.task_execution_engine.conversation_manager.get_agent_performance_metrics(
            agent_id=agent_id, time_range_hours=hours
        )

        return {"agent_id": agent_id, "time_range_hours": hours, "metrics": metrics}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent performance: {str(e)}"
        )


# File Operations Endpoints
@app.get(
    "/tasks/{task_id}/file-operations",
    tags=["file-operations"],
    summary="Get File Operations",
    description="Get file operations for a task with optional status filtering",
)
async def get_task_file_operations(
    task_id: str = Path(..., description="Task ID"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending, applied)"
    ),
):
    """Get file operations for a task"""
    try:
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution or not execution.file_operations_engine:
            raise HTTPException(
                status_code=404, detail="Task not found or no file operations available"
            )

        file_ops_engine = execution.file_operations_engine

        if status == "pending":
            operations = file_ops_engine.get_pending_operations()
        elif status == "applied":
            operations = file_ops_engine.get_applied_operations()
        else:
            # Get all operations
            pending = file_ops_engine.get_pending_operations()
            applied = file_ops_engine.get_applied_operations()
            operations = pending + applied

        # Convert to dict format
        operations_data = []
        for batch in operations:
            operations_data.append(
                {
                    "batch_id": batch.batch_id,
                    "task_id": batch.task_id,
                    "agent_id": batch.agent_id,
                    "description": batch.description,
                    "requires_approval": batch.requires_approval,
                    "approval_status": batch.approval_status.value,
                    "operations_count": len(batch.operations),
                    "created_at": batch.created_at.isoformat(),
                    "applied_at": (
                        batch.applied_at.isoformat() if batch.applied_at else None
                    ),
                }
            )

        return {"task_id": task_id, "operations": operations_data}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get file operations: {str(e)}"
        )


@app.get("/tasks/{task_id}/file-operations/{batch_id}/preview")
async def get_file_operations_preview(task_id: str, batch_id: str):
    """Get preview of file changes for a batch"""
    try:
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution or not execution.file_operations_engine:
            raise HTTPException(
                status_code=404, detail="Task not found or no file operations available"
            )

        file_ops_engine = execution.file_operations_engine
        diffs = await file_ops_engine.get_file_diff_preview(batch_id)

        return {"task_id": task_id, "batch_id": batch_id, "file_diffs": diffs}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get file preview: {str(e)}"
        )


@app.post(
    "/tasks/{task_id}/file-operations/{batch_id}/approve",
    tags=["file-operations", "human-in-loop"],
    summary="Approve File Operations",
    description="Approve or reject file operations from Claude SDK",
)
async def approve_file_operations(
    task_id: str = Path(..., description="Task ID"),
    batch_id: str = Path(..., description="Batch ID"),
    approval_data: FileOperationApprovalRequest = Body(...),
):
    """Approve or reject file operations"""
    try:
        approved = approval_data.get("approved", False)

        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution or not execution.file_operations_engine:
            raise HTTPException(
                status_code=404, detail="Task not found or no file operations available"
            )

        file_ops_engine = execution.file_operations_engine
        success = await file_ops_engine.approve_operations(batch_id, approved)

        if success:
            # Also notify Claude SDK if there's an active session
            if execution.claude_sdk_manager and execution.claude_session_id:
                await execution.claude_sdk_manager.approve_file_operations(
                    execution.claude_session_id, batch_id, approved
                )

            return {
                "task_id": task_id,
                "batch_id": batch_id,
                "approved": approved,
                "status": "success",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to process approval")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to approve file operations: {str(e)}"
        )


@app.post("/tasks/{task_id}/file-operations/{batch_id}/rollback")
async def rollback_file_operations(task_id: str, batch_id: str):
    """Rollback applied file operations"""
    try:
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution or not execution.file_operations_engine:
            raise HTTPException(
                status_code=404, detail="Task not found or no file operations available"
            )

        file_ops_engine = execution.file_operations_engine
        success = await file_ops_engine.rollback_operations(batch_id)

        if success:
            return {"task_id": task_id, "batch_id": batch_id, "status": "rolled_back"}
        else:
            raise HTTPException(status_code=400, detail="Failed to rollback operations")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to rollback file operations: {str(e)}"
        )


# Claude SDK Session Management Endpoints
@app.get("/tasks/{task_id}/claude-session")
async def get_claude_session_status(task_id: str):
    """Get Claude SDK session status for a task"""
    try:
        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if (
            not execution
            or not execution.claude_sdk_manager
            or not execution.claude_session_id
        ):
            raise HTTPException(
                status_code=404, detail="No active Claude SDK session for this task"
            )

        status = await execution.claude_sdk_manager.get_session_status(
            execution.claude_session_id
        )
        return status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Claude session status: {str(e)}"
        )


@app.post("/tasks/{task_id}/claude-session/input")
async def send_claude_session_input(task_id: str, input_data: dict):
    """Send input to Claude SDK session"""
    try:
        user_input = input_data.get("input", "")
        if not user_input:
            raise HTTPException(status_code=400, detail="Input cannot be empty")

        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if (
            not execution
            or not execution.claude_sdk_manager
            or not execution.claude_session_id
        ):
            raise HTTPException(
                status_code=404, detail="No active Claude SDK session for this task"
            )

        success = await execution.claude_sdk_manager.send_input(
            execution.claude_session_id, user_input
        )

        if success:
            return {"task_id": task_id, "status": "input_sent", "input": user_input}
        else:
            raise HTTPException(
                status_code=400, detail="Failed to send input to Claude session"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send Claude session input: {str(e)}"
        )


# MCP Integration Endpoints
@app.get("/mcp/tools")
async def get_mcp_tools():
    """Get available MCP tools"""
    try:
        from .mcp_integration import FuzeAgentMCPServer

        mcp_server = FuzeAgentMCPServer()
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in mcp_server.tools
        ]

        return {"tools": tools}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP tools: {str(e)}"
        )


@app.post(
    "/mcp/call-tool",
    tags=["mcp-integration"],
    summary="Call MCP Tool",
    description="Execute an MCP tool to access organizational context",
)
async def call_mcp_tool(tool_request: MCPToolRequest = Body(...)):
    """Call an MCP tool"""
    try:
        from .mcp_integration import FuzeAgentMCPServer

        tool_name = tool_request.get("tool_name")
        arguments = tool_request.get("arguments", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")

        mcp_server = FuzeAgentMCPServer()
        result = await mcp_server.handle_tool_call(tool_name, arguments)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to call MCP tool: {str(e)}"
        )


@app.get("/mcp/resources")
async def get_mcp_resources():
    """Get available MCP resources"""
    try:
        from .mcp_integration import FuzeAgentMCPServer

        mcp_server = FuzeAgentMCPServer()
        resources = [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mime_type,
            }
            for resource in mcp_server.resources
        ]

        return {"resources": resources}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP resources: {str(e)}"
        )


@app.get("/mcp/resource")
async def get_mcp_resource(uri: str):
    """Get an MCP resource by URI"""
    try:
        from .mcp_integration import FuzeAgentMCPServer

        if not uri:
            raise HTTPException(status_code=400, detail="uri parameter is required")

        mcp_server = FuzeAgentMCPServer()
        resource = await mcp_server.handle_resource_request(uri)

        return resource

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP resource: {str(e)}"
        )


@app.get("/tasks/{task_id}/mcp-context")
async def get_task_mcp_context(task_id: str):
    """Get MCP context for a task"""
    try:
        from .mcp_integration import FuzeAgentMCPServer, MCPClaudeIntegration

        execution = app.state.task_execution_engine.active_executions.get(task_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Task not found or not active")

        mcp_server = FuzeAgentMCPServer()
        mcp_integration = MCPClaudeIntegration(mcp_server)

        session_id = execution.claude_session_id or f"session-{task_id}"
        context = await mcp_integration.get_session_context(
            session_id=session_id, agent_id=execution.agent_id, task_id=task_id
        )

        return context

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get MCP context: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/mcp-setup",
    tags=["mcp-integration"],
    summary="Setup Agent MCP Integration",
    description="Configure MCP integration for an AI agent",
)
async def setup_agent_mcp(
    agent_id: str = Path(..., description="Agent ID"),
    setup_data: AgentMCPSetupRequest = Body(...),
):
    """Set up MCP integration for an agent"""
    try:
        from .mcp_integration import FuzeAgentMCPServer, MCPClaudeIntegration

        task_id = setup_data.get("task_id")
        session_id = setup_data.get("session_id")

        if not task_id:
            raise HTTPException(status_code=400, detail="task_id is required")

        mcp_server = FuzeAgentMCPServer()
        mcp_integration = MCPClaudeIntegration(mcp_server)

        # Set up MCP for Claude session
        mcp_config = await mcp_integration.setup_claude_session_mcp(
            session_id=session_id or f"session-{task_id}",
            agent_id=agent_id,
            task_id=task_id,
        )

        return {
            "agent_id": agent_id,
            "task_id": task_id,
            "mcp_config": mcp_config,
            "status": "mcp_configured",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup MCP: {str(e)}")


# Multi-Agent Coordination Endpoints
@app.post(
    "/tasks/{task_id}/coordinate",
    tags=["multi-agent-coordination"],
    summary="Initiate Multi-Agent Coordination",
    description="Initiate multi-agent coordination for complex tasks",
    response_model=CoordinationResponse,
)
async def initiate_task_coordination(
    task_id: str = Path(..., description="Task ID to coordinate"),
    coordination_request: CoordinationRequest = Body(...),
):
    """Initiate multi-agent coordination for a complex task"""
    try:
        from .multi_agent_coordinator import CoordinationMode

        coordination_mode = coordination_request.get(
            "coordination_mode", "collaborative"
        )
        required_agents = coordination_request.get("required_agents")
        required_skills = coordination_request.get("required_skills")

        # Validate coordination mode
        try:
            coord_mode = CoordinationMode(coordination_mode)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid coordination mode: {coordination_mode}",
            )

        # Get multi-agent coordinator
        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            raise HTTPException(
                status_code=503, detail="Multi-agent coordination not available"
            )

        # Initiate coordination
        session_id = await coordinator.initiate_coordination(
            task_id=task_id,
            coordination_mode=coord_mode,
            required_agents=required_agents,
            required_skills=required_skills,
        )

        if session_id:
            return {
                "task_id": task_id,
                "coordination_session_id": session_id,
                "status": "coordination_initiated",
                "coordination_mode": coordination_mode,
            }
        else:
            return {
                "task_id": task_id,
                "status": "coordination_not_needed",
                "message": "Task does not require multi-agent coordination",
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate coordination: {str(e)}"
        )


@app.get("/coordination/{session_id}")
async def get_coordination_status(session_id: str):
    """Get status of a coordination session"""
    try:
        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            raise HTTPException(
                status_code=503, detail="Multi-agent coordination not available"
            )

        status = await coordinator.get_coordination_status(session_id)

        if status:
            return status
        else:
            raise HTTPException(
                status_code=404, detail="Coordination session not found"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get coordination status: {str(e)}"
        )


@app.post("/coordination/{session_id}/cancel")
async def cancel_coordination(session_id: str):
    """Cancel a coordination session"""
    try:
        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            raise HTTPException(
                status_code=503, detail="Multi-agent coordination not available"
            )

        success = await coordinator.cancel_coordination(session_id)

        if success:
            return {"coordination_session_id": session_id, "status": "cancelled"}
        else:
            raise HTTPException(
                status_code=404, detail="Coordination session not found"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel coordination: {str(e)}"
        )


@app.post("/agents/{from_agent_id}/communicate/{to_agent_id}")
async def send_agent_communication(
    from_agent_id: str, to_agent_id: str, communication_data: dict
):
    """Send communication between agents"""
    try:
        message_type = communication_data.get("message_type", "notification")
        content = communication_data.get("content", "")
        metadata = communication_data.get("metadata", {})

        if not content:
            raise HTTPException(status_code=400, detail="Content cannot be empty")

        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            raise HTTPException(
                status_code=503, detail="Multi-agent coordination not available"
            )

        communication_id = await coordinator.send_agent_communication(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message_type=message_type,
            content=content,
            metadata=metadata,
        )

        return {
            "communication_id": communication_id,
            "from_agent_id": from_agent_id,
            "to_agent_id": to_agent_id,
            "status": "sent",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send agent communication: {str(e)}"
        )


@app.get("/coordination/active")
async def get_active_coordinations():
    """Get all active coordination sessions"""
    try:
        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            raise HTTPException(
                status_code=503, detail="Multi-agent coordination not available"
            )

        active_sessions = []
        for session_id in coordinator.active_sessions.keys():
            status = await coordinator.get_coordination_status(session_id)
            if status:
                active_sessions.append(status)

        return {"active_coordinations": active_sessions, "count": len(active_sessions)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get active coordinations: {str(e)}"
        )


# WebSocket for coordination updates
@app.websocket("/ws/coordination/{session_id}")
async def coordination_websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time coordination updates"""
    await websocket.accept()
    try:
        coordinator = getattr(
            app.state.task_execution_engine, "multi_agent_coordinator", None
        )
        if not coordinator:
            await websocket.send_json(
                {"type": "error", "message": "Multi-agent coordination not available"}
            )
            await websocket.close()
            return

        # Monitor coordination session
        while True:
            try:
                status = await coordinator.get_coordination_status(session_id)
                if status:
                    await websocket.send_json(
                        {
                            "type": "coordination_update",
                            "session_id": session_id,
                            "data": status,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    # If coordination is completed or failed, send final update
                    if status.get("status") in ["completed", "failed", "cancelled"]:
                        await websocket.send_json(
                            {
                                "type": "coordination_finished",
                                "session_id": session_id,
                                "final_status": status.get("status"),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        break
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Coordination session {session_id} not found",
                        }
                    )
                    break

                await asyncio.sleep(3)  # Update every 3 seconds

            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Error monitoring coordination: {str(e)}",
                    }
                )

    except Exception as e:
        print(f"Coordination WebSocket error for {session_id}: {e}")
    finally:
        await websocket.close()


# ---------------------------------------------------------------------------
# Agent relay WebSocket (Track 4)
# ---------------------------------------------------------------------------
@app.websocket("/agent-relay/{agent_id}")
async def agent_relay_endpoint(websocket: WebSocket, agent_id: str):
    """
    Agent pods connect here to stream their session output.
    Dashboard clients connect here to watch a specific agent's session.
    Both use the same endpoint — first JSON message determines role:
      {"role": "agent"}      -> agent pod streaming output
      {"role": "subscriber"} -> human dashboard watcher (default)
    """
    await websocket.accept()
    role = None
    try:
        init_msg = await websocket.receive_json()
        role = init_msg.get("role", "subscriber")

        if role == "agent":
            # Stream from agent pod to all subscribers
            async for data in websocket.iter_json():
                msg = {"agentId": agent_id, **data}
                dead = []
                for sub in list(agent_relay_subscribers[agent_id]):
                    try:
                        await sub.send_json(msg)
                    except Exception:
                        dead.append(sub)
                for d in dead:
                    agent_relay_subscribers[agent_id].remove(d)
        else:
            # Human dashboard subscriber — wait for messages from agent
            agent_relay_subscribers[agent_id].append(websocket)
            await websocket.receive_text()  # keep alive until disconnect
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"agent-relay {agent_id}: {e}")
    finally:
        subs = agent_relay_subscribers.get(agent_id, [])
        if role != "agent" and websocket in subs:
            subs.remove(websocket)


# Model Configuration and API Key Management Endpoints
@app.post(
    "/organizations/{organization_id}/providers/{provider}/credentials",
    tags=["model-configuration"],
    summary="Store Provider API Credentials",
    description="Store encrypted API credentials for a model provider",
)
async def store_provider_credentials(
    organization_id: str = Path(..., description="Organization ID"),
    provider: str = Path(..., description="Provider name"),
    credentials: ProviderCredentialsRequest = Body(...),
):
    """Store encrypted API credentials for a model provider at organization level"""
    try:
        from .model_configuration import ModelProvider, model_config_manager

        # Validate provider
        try:
            provider_enum = ModelProvider(provider)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Unsupported provider: {provider}"
            )

        success = await model_config_manager.store_provider_credentials(
            organization_id=organization_id,
            provider=provider_enum,
            api_key=credentials.api_key,
            endpoint_url=credentials.endpoint_url,
            additional_config=credentials.additional_config,
        )

        if success:
            return {
                "organization_id": organization_id,
                "provider": provider,
                "status": "credentials_stored",
                "message": "API credentials stored successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store credentials")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to store provider credentials: {str(e)}"
        )


@app.get(
    "/organizations/{organization_id}/models",
    tags=["model-configuration"],
    summary="Get Available Models",
    description="Get available AI models for an organization",
)
async def get_available_models(
    organization_id: str = Path(..., description="Organization ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    capabilities: Optional[str] = Query(
        None, description="Filter by capabilities (comma-separated)"
    ),
):
    """Get available AI models with provider credential validation"""
    try:
        from .model_configuration import (ModelCapability, ModelProvider,
                                          model_config_manager)

        provider_filter = None
        if provider:
            try:
                provider_filter = ModelProvider(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid provider: {provider}"
                )

        capabilities_filter = None
        if capabilities:
            try:
                capabilities_filter = [
                    ModelCapability(cap.strip()) for cap in capabilities.split(",")
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid capability: {str(e)}"
                )

        models = await model_config_manager.get_available_models(
            organization_id=organization_id,
            provider=provider_filter,
            capabilities=capabilities_filter,
        )

        return {
            "organization_id": organization_id,
            "models": models,
            "count": len(models),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get available models: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/model-configuration",
    tags=["model-configuration"],
    summary="Configure Agent Model Settings",
    description="Configure model settings and preferences for an agent",
)
async def configure_agent_model(
    agent_id: str = Path(..., description="Agent ID"),
    config: AgentModelConfigRequest = Body(...),
):
    """Configure model settings for an AI agent"""
    try:
        from .model_configuration import AgentModelConfig, model_config_manager

        agent_config = AgentModelConfig(
            agent_id=agent_id,
            primary_model=config.primary_model,
            fallback_models=config.fallback_models,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
            custom_instructions=config.custom_instructions,
            use_function_calling=config.use_function_calling,
            streaming_enabled=config.streaming_enabled,
            cost_limit_per_task=config.cost_limit_per_task,
        )

        success = await model_config_manager.configure_agent_model(
            agent_id, agent_config
        )

        if success:
            return {
                "agent_id": agent_id,
                "status": "configured",
                "primary_model": config.primary_model,
                "fallback_models": config.fallback_models,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to configure agent model"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to configure agent model: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/model-configuration",
    tags=["model-configuration"],
    summary="Get Agent Model Configuration",
    description="Get current model configuration for an agent",
)
async def get_agent_model_configuration(
    agent_id: str = Path(..., description="Agent ID")
):
    """Get model configuration for an AI agent"""
    try:
        from .model_configuration import model_config_manager

        config = await model_config_manager.get_agent_model_config(agent_id)

        if config:
            return {
                "agent_id": agent_id,
                "configuration": {
                    "primary_model": config.primary_model,
                    "fallback_models": config.fallback_models,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "top_p": config.top_p,
                    "frequency_penalty": config.frequency_penalty,
                    "presence_penalty": config.presence_penalty,
                    "custom_instructions": config.custom_instructions,
                    "use_function_calling": config.use_function_calling,
                    "streaming_enabled": config.streaming_enabled,
                    "cost_limit_per_task": config.cost_limit_per_task,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                },
            }
        else:
            raise HTTPException(
                status_code=404, detail="Agent model configuration not found"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent model configuration: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/tasks/cost-estimate",
    tags=["model-configuration"],
    summary="Estimate Task Cost",
    description="Estimate the cost of executing a task with the agent's model configuration",
)
async def estimate_task_cost(
    agent_id: str = Path(..., description="Agent ID"),
    request: TaskCostEstimateRequest = Body(...),
):
    """Estimate cost for task execution based on agent's model configuration"""
    try:
        from .model_configuration import model_config_manager

        estimate = await model_config_manager.estimate_task_cost(
            agent_id=agent_id,
            task_description=request.task_description,
            estimated_complexity=request.estimated_complexity,
        )

        return estimate

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to estimate task cost: {str(e)}"
        )


@app.get(
    "/organizations/{organization_id}/model-usage",
    tags=["model-configuration"],
    summary="Get Model Usage Statistics",
    description="Get model usage statistics and costs for an organization",
)
async def get_organization_model_usage(
    organization_id: str = Path(..., description="Organization ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
):
    """Get model usage statistics and costs for an organization"""
    try:
        from .model_configuration import model_config_manager

        usage = await model_config_manager.get_organization_model_usage(
            organization_id=organization_id, days=days
        )

        return usage

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get model usage: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/model-recommendations",
    tags=["model-configuration"],
    summary="Get Model Recommendations",
    description="Get model recommendations for an agent based on task capabilities",
)
async def get_model_recommendations(
    agent_id: str = Path(..., description="Agent ID"),
    capabilities: str = Query(
        ..., description="Required capabilities (comma-separated)"
    ),
    cost_limit: Optional[float] = Query(
        None, ge=0.0, description="Maximum cost limit in USD"
    ),
):
    """Get model recommendations based on task capabilities and cost constraints"""
    try:
        from .model_configuration import ModelCapability, model_config_manager

        # Parse capabilities
        try:
            capability_list = [
                ModelCapability(cap.strip()) for cap in capabilities.split(",")
            ]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid capability: {str(e)}")

        recommended_model = await model_config_manager.get_model_for_task(
            agent_id=agent_id, task_capabilities=capability_list, cost_limit=cost_limit
        )

        if recommended_model:
            return {
                "agent_id": agent_id,
                "recommended_model": recommended_model,
                "capabilities": capabilities,
                "cost_limit": cost_limit,
            }
        else:
            return {
                "agent_id": agent_id,
                "recommended_model": None,
                "message": "No suitable model found for the specified requirements",
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get model recommendations: {str(e)}"
        )


# Knowledge Management and Notification Endpoints


@app.get(
    "/knowledge/notifications/{recipient_type}/{recipient_id}",
    tags=["knowledge-management"],
    summary="Get Knowledge Notifications",
    description="Get notifications about knowledge updates, conflicts, and opportunities",
)
async def get_knowledge_notifications(
    recipient_type: str = Path(
        ..., description="Recipient type (agent, team, organization)"
    ),
    recipient_id: str = Path(..., description="Recipient ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum notifications to return"),
    status_filter: Optional[str] = Query(
        None, description="Filter by status (unread, read, acknowledged)"
    ),
    notification_type_filter: Optional[str] = Query(
        None, description="Filter by type (comma-separated)"
    ),
):
    """Get knowledge notifications for a recipient"""
    try:
        from .knowledge_notification_service import (
            KnowledgeNotificationService, NotificationStatus, NotificationType)

        # Initialize notification service if not already done
        if not hasattr(app.state, "notification_service"):
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:password@postgres:5432/ai_context",
            )
            app.state.notification_service = KnowledgeNotificationService(database_url)
            await app.state.notification_service.initialize()

        # Parse filters
        status_filters = None
        if status_filter:
            try:
                status_filters = [
                    NotificationStatus(s.strip()) for s in status_filter.split(",")
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid status filter: {str(e)}"
                )

        type_filters = None
        if notification_type_filter:
            try:
                type_filters = [
                    NotificationType(t.strip())
                    for t in notification_type_filter.split(",")
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid notification type filter: {str(e)}",
                )

        notifications = (
            await app.state.notification_service.get_notifications_for_recipient(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                limit=limit,
                status_filter=status_filters,
                notification_type_filter=type_filters,
            )
        )

        return {
            "recipient_type": recipient_type,
            "recipient_id": recipient_id,
            "notifications": [
                {
                    "id": n.id,
                    "notification_type": n.notification_type.value,
                    "title": n.title,
                    "message": n.message,
                    "knowledge_id": n.knowledge_id,
                    "knowledge_type": n.knowledge_type,
                    "priority": n.priority.value,
                    "requires_action": n.requires_action,
                    "status": n.status.value,
                    "suggested_actions": n.suggested_actions,
                    "metadata": n.metadata,
                    "created_at": n.created_at.isoformat(),
                    "expires_at": n.expires_at.isoformat() if n.expires_at else None,
                }
                for n in notifications
            ],
            "count": len(notifications),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge notifications: {str(e)}"
        )


@app.put(
    "/knowledge/notifications/{notification_id}/status",
    tags=["knowledge-management"],
    summary="Update Notification Status",
    description="Mark notification as read, acknowledged, or acted upon",
)
async def update_notification_status(
    notification_id: str = Path(..., description="Notification ID"),
    status: str = Body(..., description="New notification status"),
    action_taken: Optional[Dict[str, Any]] = Body(
        None, description="Optional action taken metadata"
    ),
):
    """Update notification status and optional action taken"""
    try:
        from .knowledge_notification_service import NotificationStatus

        # Validate status
        try:
            notification_status = NotificationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        success = await app.state.notification_service.mark_notification_status(
            notification_id=notification_id,
            status=notification_status,
            action_taken=action_taken,
        )

        if success:
            return {
                "notification_id": notification_id,
                "status": status,
                "updated": True,
            }
        else:
            raise HTTPException(status_code=404, detail="Notification not found")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update notification status: {str(e)}"
        )


@app.get(
    "/knowledge/notifications/statistics",
    tags=["knowledge-management"],
    summary="Get Notification Statistics",
    description="Get comprehensive notification statistics and analytics",
)
async def get_notification_statistics(
    organization_id: Optional[str] = Query(
        None, description="Filter by organization ID"
    ),
    days_back: int = Query(30, ge=1, le=365, description="Days of history to analyze"),
):
    """Get notification statistics and analytics"""
    try:
        stats = await app.state.notification_service.get_notification_statistics(
            organization_id=organization_id, days_back=days_back
        )

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get notification statistics: {str(e)}"
        )


@app.post(
    "/knowledge/organizations/{organization_id}/add",
    tags=["knowledge-management"],
    summary="Add Organizational Knowledge",
    description="Add knowledge to organization-level knowledge base",
)
async def add_organizational_knowledge(
    organization_id: str = Path(..., description="Organization ID"),
    title: str = Body(..., description="Knowledge title"),
    content: str = Body(..., description="Knowledge content"),
    content_type: str = Body("documentation", description="Content type"),
    knowledge_category: str = Body("development", description="Knowledge category"),
    source_agent_id: Optional[str] = Body(None, description="Source agent ID"),
    source_team_id: Optional[str] = Body(None, description="Source team ID"),
    tags: List[str] = Body(default_factory=list, description="Knowledge tags"),
    metadata: Dict[str, Any] = Body(
        default_factory=dict, description="Additional metadata"
    ),
):
    """Add knowledge to organization-level knowledge base"""
    try:
        from .organization_rag_manager import (ContentType, KnowledgeCategory,
                                               OrganizationRAGManager,
                                               SourceType)

        # Initialize services if not already done
        if not hasattr(app.state, "org_rag_manager"):
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:password@postgres:5432/ai_context",
            )
            app.state.org_rag_manager = OrganizationRAGManager(database_url)
            await app.state.org_rag_manager.initialize()

        # Validate enums
        try:
            content_type_enum = ContentType(content_type)
            category_enum = KnowledgeCategory(knowledge_category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")

        knowledge_id = await app.state.org_rag_manager.add_knowledge(
            organization_id=organization_id,
            title=title,
            content=content,
            content_type=content_type_enum,
            knowledge_category=category_enum,
            source_type=SourceType.MANUAL_INPUT,
            source_agent_id=source_agent_id,
            source_team_id=source_team_id,
            tags=tags,
            metadata=metadata,
        )

        return {
            "knowledge_id": knowledge_id,
            "organization_id": organization_id,
            "title": title,
            "status": "added",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add organizational knowledge: {str(e)}"
        )


@app.get(
    "/knowledge/organizations/{organization_id}/search",
    tags=["knowledge-management"],
    summary="Search Organizational Knowledge",
    description="Search organization-level knowledge base",
)
async def search_organizational_knowledge(
    organization_id: str = Path(..., description="Organization ID"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    min_similarity: float = Query(
        0.3, ge=0.0, le=1.0, description="Minimum similarity threshold"
    ),
    categories: Optional[str] = Query(
        None, description="Filter by categories (comma-separated)"
    ),
):
    """Search organization-level knowledge base"""
    try:
        from .organization_rag_manager import KnowledgeCategory

        # Parse categories
        category_filters = None
        if categories:
            try:
                category_filters = [
                    KnowledgeCategory(cat.strip()) for cat in categories.split(",")
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid category: {str(e)}"
                )

        search_results = await app.state.org_rag_manager.search_knowledge(
            organization_id=organization_id,
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            categories=category_filters,
        )

        results = []
        for result in search_results:
            results.append(
                {
                    "knowledge_id": result.knowledge.id,
                    "title": result.knowledge.title,
                    "content_preview": (
                        result.knowledge.content[:200] + "..."
                        if len(result.knowledge.content) > 200
                        else result.knowledge.content
                    ),
                    "category": result.knowledge.knowledge_category.value,
                    "content_type": result.knowledge.content_type.value,
                    "similarity_score": result.similarity_score,
                    "combined_score": result.combined_score,
                    "quality_score": result.knowledge.quality_score,
                    "usage_count": result.knowledge.usage_count,
                    "created_at": result.knowledge.created_at.isoformat(),
                    "tags": result.knowledge.tags,
                    "metadata": result.knowledge.metadata,
                }
            )

        return {
            "organization_id": organization_id,
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search organizational knowledge: {str(e)}",
        )


@app.get(
    "/knowledge/context-enhancement/{agent_id}",
    tags=["knowledge-management"],
    summary="Get Enhanced Context for Agent",
    description="Get enhanced context with relevant organizational knowledge for task execution",
)
async def get_enhanced_context_for_agent(
    agent_id: str = Path(..., description="Agent ID"),
    task_description: str = Query(
        ..., description="Task description for context enhancement"
    ),
    task_type: Optional[str] = Query(None, description="Task type"),
    technologies: Optional[str] = Query(
        None, description="Technologies involved (comma-separated)"
    ),
):
    """Get enhanced context with relevant knowledge for agent task execution"""
    try:
        from .context_enhancement_service import ContextEnhancementService

        # Initialize context enhancement service if needed
        if not hasattr(app.state, "context_enhancement_service"):
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:password@postgres:5432/ai_context",
            )
            # These would be initialized in the lifespan
            if hasattr(app.state, "org_rag_manager") and hasattr(
                app.state, "team_knowledge_manager"
            ):
                app.state.context_enhancement_service = ContextEnhancementService(
                    database_url=database_url,
                    org_rag_manager=app.state.org_rag_manager,
                    team_knowledge_manager=app.state.team_knowledge_manager,
                )
                await app.state.context_enhancement_service.initialize()
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Knowledge management services not initialized",
                )

        # Build task data
        task_data = {
            "description": task_description,
            "task_type": task_type,
            "technologies": technologies.split(",") if technologies else [],
        }

        enhanced_context = (
            await app.state.context_enhancement_service.enhance_agent_context(
                agent_id=agent_id, task_data=task_data
            )
        )

        return {
            "agent_id": agent_id,
            "task_description": task_description,
            "enhanced_context": {
                "organizational_knowledge_count": len(
                    enhanced_context.organizational_knowledge
                ),
                "team_knowledge_count": len(enhanced_context.team_knowledge),
                "similar_task_insights_count": len(
                    enhanced_context.similar_task_insights
                ),
                "success_patterns": enhanced_context.success_patterns,
                "common_pitfalls": enhanced_context.common_pitfalls,
                "recommended_approaches": enhanced_context.recommended_approaches,
                "context_summary": enhanced_context.context_summary,
                "enhancement_metadata": enhanced_context.enhancement_metadata,
            },
            "organizational_knowledge": [
                {
                    "knowledge_id": item.knowledge_id,
                    "title": item.title,
                    "category": item.category,
                    "relevance_score": item.relevance_score,
                    "confidence_score": item.confidence_score,
                    "content_preview": (
                        item.content[:200] + "..."
                        if len(item.content) > 200
                        else item.content
                    ),
                }
                for item in enhanced_context.organizational_knowledge
            ],
            "team_knowledge": [
                {
                    "knowledge_id": item.knowledge_id,
                    "title": item.title,
                    "category": item.category,
                    "relevance_score": item.relevance_score,
                    "confidence_score": item.confidence_score,
                    "content_preview": (
                        item.content[:200] + "..."
                        if len(item.content) > 200
                        else item.content
                    ),
                }
                for item in enhanced_context.team_knowledge
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get enhanced context: {str(e)}"
        )


@app.get(
    "/knowledge/analytics/organizations/{organization_id}/insights",
    tags=["knowledge-management"],
    summary="Get Organizational Knowledge Insights",
    description="Get comprehensive analytics and insights about organizational knowledge",
)
async def get_organizational_knowledge_insights(
    organization_id: str = Path(..., description="Organization ID"),
    analysis_period_days: int = Query(
        30, ge=7, le=365, description="Analysis period in days"
    ),
):
    """Get comprehensive organizational knowledge insights and analytics"""
    try:
        insights = (
            await app.state.knowledge_analytics_service.get_organizational_insights(
                organization_id=organization_id,
                analysis_period_days=analysis_period_days,
            )
        )

        return {
            "organization_id": organization_id,
            "analysis_period_days": analysis_period_days,
            "insights": {
                "total_knowledge_items": insights.total_knowledge_items,
                "knowledge_growth_rate": insights.knowledge_growth_rate,
                "knowledge_utilization_rate": insights.knowledge_utilization_rate,
                "knowledge_freshness_score": insights.knowledge_freshness_score,
                "cross_team_sharing_rate": insights.cross_team_sharing_rate,
                "propagation_efficiency": insights.propagation_efficiency,
                "top_performing_categories": insights.top_performing_categories,
                "knowledge_gaps": insights.knowledge_gaps,
                "agent_knowledge_engagement": insights.agent_knowledge_engagement,
                "team_knowledge_contribution": insights.team_knowledge_contribution,
                "recommendations": insights.recommendations,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get organizational insights: {str(e)}"
        )


@app.get(
    "/knowledge/analytics/organizations/{organization_id}/effectiveness",
    tags=["knowledge-management"],
    summary="Analyze Knowledge Effectiveness",
    description="Analyze effectiveness and performance of knowledge items",
)
async def analyze_knowledge_effectiveness(
    organization_id: str = Path(..., description="Organization ID"),
    knowledge_category: Optional[str] = Query(
        None, description="Filter by knowledge category"
    ),
    min_usage_count: int = Query(
        3, ge=1, description="Minimum usage count for analysis"
    ),
):
    """Analyze effectiveness of knowledge items in the organization"""
    try:
        effectiveness_metrics = (
            await app.state.knowledge_analytics_service.analyze_knowledge_effectiveness(
                organization_id=organization_id,
                knowledge_category=knowledge_category,
                min_usage_count=min_usage_count,
            )
        )

        results = []
        for metric in effectiveness_metrics:
            results.append(
                {
                    "knowledge_id": metric.knowledge_id,
                    "title": metric.title,
                    "category": metric.category,
                    "usage_count": metric.usage_count,
                    "success_correlation": metric.success_correlation,
                    "average_relevance": metric.average_relevance,
                    "agent_adoption_rate": metric.agent_adoption_rate,
                    "team_adoption_rate": metric.team_adoption_rate,
                    "quality_score": metric.quality_score,
                    "recency_score": metric.recency_score,
                    "overall_effectiveness": metric.overall_effectiveness,
                    "trend_direction": metric.trend_direction,
                    "optimization_suggestions": metric.optimization_suggestions,
                }
            )

        return {
            "organization_id": organization_id,
            "effectiveness_analysis": results,
            "total_analyzed": len(results),
            "summary": {
                "avg_effectiveness": sum(r["overall_effectiveness"] for r in results)
                / max(len(results), 1),
                "top_performers": sorted(
                    results, key=lambda x: x["overall_effectiveness"], reverse=True
                )[:5],
                "needs_attention": [
                    r for r in results if r["overall_effectiveness"] < 0.5
                ],
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze knowledge effectiveness: {str(e)}",
        )


@app.get(
    "/knowledge/analytics/agents/{agent_id}/profile",
    tags=["knowledge-management"],
    summary="Get Agent Knowledge Profile",
    description="Get detailed knowledge profile and analytics for an agent",
)
async def get_agent_knowledge_profile(
    agent_id: str = Path(..., description="Agent ID"),
    analysis_period_days: int = Query(
        60, ge=7, le=365, description="Analysis period in days"
    ),
):
    """Get detailed knowledge profile for an agent"""
    try:
        profile = (
            await app.state.knowledge_analytics_service.get_agent_knowledge_profile(
                agent_id=agent_id, analysis_period_days=analysis_period_days
            )
        )

        if not profile:
            raise HTTPException(
                status_code=404, detail="Agent not found or no knowledge data available"
            )

        return {
            "agent_id": agent_id,
            "analysis_period_days": analysis_period_days,
            "profile": {
                "agent_name": profile.agent_name,
                "team_id": profile.team_id,
                "knowledge_consumption_rate": profile.knowledge_consumption_rate,
                "knowledge_creation_rate": profile.knowledge_creation_rate,
                "expertise_areas": profile.expertise_areas,
                "knowledge_application_success": profile.knowledge_application_success,
                "learning_velocity": profile.learning_velocity,
                "knowledge_sharing_activity": profile.knowledge_sharing_activity,
                "preferred_knowledge_types": profile.preferred_knowledge_types,
                "knowledge_gaps": profile.knowledge_gaps,
                "optimization_recommendations": profile.optimization_recommendations,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent knowledge profile: {str(e)}"
        )


@app.get(
    "/knowledge/analytics/organizations/{organization_id}/optimization",
    tags=["knowledge-management"],
    summary="Get Knowledge Optimization Recommendations",
    description="Get comprehensive recommendations for knowledge system optimization",
)
async def get_knowledge_optimization_recommendations(
    organization_id: str = Path(..., description="Organization ID"),
    focus_area: Optional[str] = Query(
        None,
        description="Focus area (utilization, quality, gaps, propagation, collaboration)",
    ),
):
    """Generate comprehensive knowledge optimization recommendations"""
    try:
        recommendations = await app.state.knowledge_analytics_service.generate_knowledge_optimization_recommendations(
            organization_id=organization_id, focus_area=focus_area
        )

        return {
            "organization_id": organization_id,
            "focus_area": focus_area,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get optimization recommendations: {str(e)}",
        )


@app.get(
    "/knowledge/analytics/organizations/{organization_id}/trends",
    tags=["knowledge-management"],
    summary="Get Knowledge Trends Analysis",
    description="Analyze knowledge trends and patterns over time",
)
async def get_knowledge_trends_analysis(
    organization_id: str = Path(..., description="Organization ID"),
    trend_period_days: int = Query(
        90, ge=30, le=365, description="Trend analysis period in days"
    ),
):
    """Get comprehensive knowledge trends analysis"""
    try:
        trends = (
            await app.state.knowledge_analytics_service.get_knowledge_trends_analysis(
                organization_id=organization_id, trend_period_days=trend_period_days
            )
        )

        return {
            "organization_id": organization_id,
            "trend_period_days": trend_period_days,
            "trends": trends,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge trends: {str(e)}"
        )


# Memory-Enhanced Agents Endpoints


@app.post(
    "/agents/{agent_id}/deploy-memory",
    tags=["memory-agents"],
    summary="Deploy Memory-Enabled Agent",
    description="Deploy an agent with persistent memory capabilities",
)
async def deploy_memory_enabled_agent(
    agent_id: str = Path(..., description="Agent ID"),
    template_id: str = Body(..., description="Agent template ID"),
    task_id: Optional[str] = Body(None, description="Optional specific task ID"),
    repository_settings: Optional[Dict[str, Any]] = Body(
        None, description="Repository settings"
    ),
):
    """Deploy a memory-enabled autonomous agent container"""
    try:
        result = await app.state.agent_manager.deploy_memory_enabled_agent(
            agent_id=agent_id,
            template_id=template_id,
            task_id=task_id,
            repository_settings=repository_settings,
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to deploy memory-enabled agent: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/memory-status",
    tags=["memory-agents"],
    summary="Get Agent Memory Status",
    description="Get agent memory status and expertise summary",
)
async def get_agent_memory_status(agent_id: str = Path(..., description="Agent ID")):
    """Get agent memory status, expertise metrics, and insights"""
    try:
        status = await app.state.agent_manager.get_agent_memory_status(agent_id)
        return status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent memory status: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/memory-tasks",
    tags=["memory-agents"],
    summary="Assign Task to Memory Agent",
    description="Assign a task to a memory-enabled agent",
)
async def assign_task_to_memory_agent(
    agent_id: str = Path(..., description="Agent ID"),
    task_id: str = Body(..., description="Task ID"),
    task_data: Dict[str, Any] = Body(..., description="Task data"),
):
    """Assign a task to a memory-enabled agent for autonomous execution"""
    try:
        result = await app.state.agent_manager.assign_task_to_memory_agent(
            agent_id=agent_id, task_id=task_id, task_data=task_data
        )

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to assign task to memory agent: {str(e)}"
        )


@app.delete(
    "/agents/{agent_id}/memory",
    tags=["memory-agents"],
    summary="Stop Memory-Enabled Agent",
    description="Stop a memory-enabled agent container",
)
async def stop_memory_enabled_agent(agent_id: str = Path(..., description="Agent ID")):
    """Stop and clean up a memory-enabled agent container"""
    try:
        result = await app.state.agent_manager.stop_memory_enabled_agent(agent_id)

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop memory-enabled agent: {str(e)}"
        )


@app.get(
    "/system/expertise-dashboard",
    tags=["memory-agents"],
    summary="Get System Expertise Dashboard",
    description="Get system-wide expertise and memory analytics",
)
async def get_system_expertise_dashboard():
    """Get comprehensive dashboard of system expertise and memory analytics"""
    try:
        dashboard = await app.state.agent_manager.get_system_expertise_dashboard()
        return dashboard

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get expertise dashboard: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/tasks/pending",
    tags=["memory-agents"],
    summary="Get Pending Tasks for Agent",
    description="Get pending tasks for a memory-enabled agent",
)
async def get_pending_tasks_for_agent(
    agent_id: str = Path(..., description="Agent ID"),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of tasks to return"
    ),
):
    """Get pending tasks that a memory-enabled agent can pick up"""
    try:
        async with get_db_connection() as conn:
            tasks = await conn.fetch(
                """
                SELECT id, title, description, type, complexity, language, 
                       framework, requirements, created_at
                FROM tasks
                WHERE agent_id = $1 
                    AND status = 'pending'
                    AND assigned_to_memory_agent = true
                ORDER BY created_at ASC
                LIMIT $2
            """,
                agent_id,
                limit,
            )

            return {
                "agent_id": agent_id,
                "tasks": [dict(task) for task in tasks],
                "count": len(tasks),
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get pending tasks: {str(e)}"
        )


@app.put(
    "/tasks/{task_id}/status",
    tags=["memory-agents"],
    summary="Update Task Status",
    description="Update task status (used by memory-enabled agents)",
)
async def update_task_status(
    task_id: str = Path(..., description="Task ID"),
    status: str = Body(..., description="New task status"),
    result: Optional[Dict[str, Any]] = Body(None, description="Task result data"),
    updated_by: Optional[str] = Body(None, description="ID of agent updating the task"),
    container_instance_id: Optional[str] = Body(
        None, description="Container instance ID"
    ),
    updated_at: Optional[str] = Body(None, description="Update timestamp"),
):
    """Update task status - used by memory-enabled agents to report progress"""
    try:
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE tasks
                SET status = $2, 
                    result = COALESCE($3, result),
                    updated_by = COALESCE($4, updated_by),
                    updated_at = NOW()
                WHERE id = $1
            """,
                task_id,
                status,
                result,
                updated_by,
            )

            # If task is completed, log it for expertise tracking
            if status in ["completed", "failed"]:
                # The agent's memory system will handle learning from the outcome
                pass

            return {"task_id": task_id, "status": status, "updated": True}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update task status: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/register",
    tags=["memory-agents"],
    summary="Agent Registration",
    description="Register agent capabilities and status with orchestrator",
)
async def register_agent_capabilities(
    agent_id: str = Path(..., description="Agent ID"),
    capabilities: Dict[str, Any] = Body(
        ..., description="Agent capabilities and status"
    ),
):
    """Register or update agent capabilities - used by memory-enabled agents on startup"""
    try:
        # Update agent capabilities in database
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE agents
                SET config = config || $2,
                    status = 'active',
                    updated_at = NOW()
                WHERE id = $1
            """,
                agent_id,
                {
                    "capabilities": capabilities,
                    "last_registration": datetime.now().isoformat(),
                },
            )

        # Update in-memory tracking
        if agent_id in app.state.agent_manager.memory_enabled_agents:
            app.state.agent_manager.memory_enabled_agents[agent_id]["status"] = "active"

        return {
            "agent_id": agent_id,
            "agent_recognized": True,
            "capabilities_accepted": True,
            "status": "registered",
        }

    except Exception as e:
        return {
            "agent_id": agent_id,
            "agent_recognized": False,
            "capabilities_accepted": False,
            "error": str(e),
        }


@app.post(
    "/agents/{agent_id}/statistics",
    tags=["memory-agents"],
    summary="Agent Statistics Update",
    description="Update agent performance and memory statistics",
)
async def update_agent_statistics(
    agent_id: str = Path(..., description="Agent ID"),
    stats: Dict[str, Any] = Body(..., description="Agent statistics"),
):
    """Update agent statistics - used by memory-enabled agents for performance tracking"""
    try:
        # Store statistics for analytics
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE agents
                SET config = config || $2,
                    updated_at = NOW()
                WHERE id = $1
            """,
                agent_id,
                {
                    "latest_statistics": stats,
                    "statistics_updated_at": datetime.now().isoformat(),
                },
            )

        # Clear expertise cache to force refresh
        await app.state.agent_manager.expertise_tracker.clear_cache(agent_id)

        return {"agent_id": agent_id, "statistics_updated": True}

    except Exception as e:
        return {"agent_id": agent_id, "statistics_updated": False, "error": str(e)}


@app.post(
    "/agents/{agent_id}/error",
    tags=["memory-agents"],
    summary="Agent Error Reporting",
    description="Report agent errors for monitoring",
)
async def report_agent_error(
    agent_id: str = Path(..., description="Agent ID"),
    error_data: Dict[str, Any] = Body(..., description="Error information"),
):
    """Report agent errors - used by memory-enabled agents for error tracking"""
    try:
        # Log error for monitoring
        logger.error(f"Agent {agent_id} reported error: {error_data}")

        # Update agent status if it's a critical error
        if error_data.get("critical", False):
            async with get_db_connection() as conn:
                await conn.execute(
                    """
                    UPDATE agents
                    SET status = 'error',
                        config = config || $2,
                        updated_at = NOW()
                    WHERE id = $1
                """,
                    agent_id,
                    {
                        "last_error": error_data,
                        "error_reported_at": datetime.now().isoformat(),
                    },
                )

        return {"agent_id": agent_id, "error_logged": True}

    except Exception as e:
        logger.error(f"Failed to log agent error: {e}")
        return {"agent_id": agent_id, "error_logged": False}


# ============================================================================
# Goals Management API Endpoints
# ============================================================================


@app.post(
    "/organizations/{organization_id}/goals",
    tags=["goals-management"],
    summary="Create organizational goal",
    description="Create a new goal for an organization with specified targets and deadlines",
)
async def create_goal(
    organization_id: str = Path(..., description="Organization ID"),
    goal_data: GoalCreateRequest = Body(..., description="Goal creation data"),
    created_by: Optional[str] = Query(
        None, description="ID of user/agent creating the goal"
    ),
):
    """Create a new organizational goal"""
    try:
        from .goals_management_service import GoalType

        goal_id = await app.state.goals_service.create_goal(
            organization_id=organization_id,
            title=goal_data.title,
            description=goal_data.description,
            goal_type=GoalType(goal_data.goal_type),
            target_value=goal_data.target_value,
            target_unit=goal_data.target_unit,
            target_deadline=goal_data.target_deadline,
            priority_level=goal_data.priority_level,
            success_criteria=goal_data.success_criteria,
            assigned_teams=goal_data.assigned_teams,
            goal_owner_agent_id=goal_data.goal_owner_agent_id,
            stakeholder_agents=goal_data.stakeholder_agents,
            tags=goal_data.tags,
            metadata=goal_data.metadata,
            created_by=created_by,
        )

        return {"goal_id": goal_id, "status": "created"}

    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/organizations/{organization_id}/goals",
    tags=["goals-management"],
    summary="List organization goals",
    description="Get all goals for an organization with optional filtering",
)
async def list_organization_goals(
    organization_id: str = Path(..., description="Organization ID"),
    status: Optional[List[str]] = Query(None, description="Filter by goal status"),
    goal_type: Optional[List[str]] = Query(None, description="Filter by goal type"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of goals to return"
    ),
):
    """List goals for an organization"""
    try:
        from .goals_management_service import GoalStatus, GoalType

        status_filter = [GoalStatus(s) for s in status] if status else None
        type_filter = [GoalType(gt) for gt in goal_type] if goal_type else None

        goals = await app.state.goals_service.list_organization_goals(
            organization_id=organization_id,
            status_filter=status_filter,
            goal_type_filter=type_filter,
            limit=limit,
        )

        return {
            "organization_id": organization_id,
            "goals": [
                {
                    "id": goal.id,
                    "title": goal.title,
                    "description": goal.description,
                    "goal_type": goal.goal_type.value,
                    "status": goal.status.value,
                    "progress_percentage": float(goal.progress_percentage),
                    "target_value": (
                        float(goal.target_value) if goal.target_value else None
                    ),
                    "target_unit": goal.target_unit,
                    "current_value": (
                        float(goal.current_value) if goal.current_value else None
                    ),
                    "target_deadline": goal.target_deadline.isoformat(),
                    "priority_level": goal.priority_level,
                    "completion_confidence": float(goal.completion_confidence),
                    "created_at": goal.created_at.isoformat(),
                    "updated_at": goal.updated_at.isoformat(),
                }
                for goal in goals
            ],
        }

    except Exception as e:
        logger.error(f"Error listing organization goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/goals/{goal_id}",
    tags=["goals-management"],
    summary="Get goal details",
    description="Get detailed information about a specific goal",
)
async def get_goal(goal_id: str = Path(..., description="Goal ID")):
    """Get goal details"""
    try:
        goal = await app.state.goals_service.get_goal(goal_id)

        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        return {
            "id": goal.id,
            "organization_id": goal.organization_id,
            "title": goal.title,
            "description": goal.description,
            "goal_type": goal.goal_type.value,
            "status": goal.status.value,
            "progress_percentage": float(goal.progress_percentage),
            "target_value": float(goal.target_value) if goal.target_value else None,
            "target_unit": goal.target_unit,
            "current_value": float(goal.current_value) if goal.current_value else None,
            "success_criteria": goal.success_criteria,
            "start_date": goal.start_date.isoformat(),
            "target_deadline": goal.target_deadline.isoformat(),
            "actual_completion_date": (
                goal.actual_completion_date.isoformat()
                if goal.actual_completion_date
                else None
            ),
            "priority_level": goal.priority_level,
            "completion_confidence": float(goal.completion_confidence),
            "assigned_teams": goal.assigned_teams,
            "goal_owner_agent_id": goal.goal_owner_agent_id,
            "stakeholder_agents": goal.stakeholder_agents,
            "tags": goal.tags,
            "metadata": goal.metadata,
            "created_by": goal.created_by,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/goals/{goal_id}/overview",
    tags=["goals-management"],
    summary="Get goal overview",
    description="Get comprehensive overview of goal with milestones, tasks, and progress",
)
async def get_goal_overview(goal_id: str = Path(..., description="Goal ID")):
    """Get comprehensive goal overview"""
    try:
        overview = await app.state.goals_service.get_goal_overview(goal_id)

        if not overview:
            raise HTTPException(status_code=404, detail="Goal not found")

        return overview

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal overview {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/goals/{goal_id}/progress",
    tags=["goals-management"],
    summary="Update goal progress",
    description="Update progress for a specific goal",
)
async def update_goal_progress(
    goal_id: str = Path(..., description="Goal ID"),
    progress_data: GoalUpdateRequest = Body(..., description="Progress update data"),
    recorded_by: Optional[str] = Query(
        None, description="ID of user/agent recording progress"
    ),
):
    """Update goal progress"""
    try:
        success = await app.state.goals_service.update_goal_progress(
            goal_id=goal_id,
            progress_percentage=progress_data.progress_percentage,
            current_value=progress_data.current_value,
            completion_confidence=progress_data.completion_confidence,
            progress_notes=progress_data.notes,
            recorded_by=recorded_by,
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Goal not found or no changes made"
            )

        return {"goal_id": goal_id, "status": "updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating goal progress {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/milestones",
    tags=["goals-management"],
    summary="Create milestone",
    description="Create a new milestone for a goal",
)
async def create_milestone(
    goal_id: str = Path(..., description="Goal ID"),
    milestone_data: MilestoneCreateRequest = Body(
        ..., description="Milestone creation data"
    ),
    created_by: Optional[str] = Query(
        None, description="ID of user/agent creating milestone"
    ),
):
    """Create milestone for goal"""
    try:
        milestone_id = await app.state.goals_service.create_milestone(
            goal_id=goal_id,
            title=milestone_data.title,
            description=milestone_data.description,
            target_date=milestone_data.target_date,
            milestone_type=milestone_data.milestone_type,
            success_criteria=milestone_data.success_criteria,
            deliverables=milestone_data.deliverables,
            dependencies=milestone_data.dependencies,
            assigned_teams=milestone_data.assigned_teams,
            responsible_agent_id=milestone_data.responsible_agent_id,
            priority_level=milestone_data.priority_level,
            weight_in_goal=milestone_data.weight_in_goal,
            created_by=created_by,
        )

        return {"milestone_id": milestone_id, "status": "created"}

    except Exception as e:
        logger.error(f"Error creating milestone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/milestones/{milestone_id}/tasks",
    tags=["goals-management"],
    summary="Create task from milestone",
    description="Create a new task derived from a milestone",
)
async def create_task_from_milestone(
    milestone_id: str = Path(..., description="Milestone ID"),
    task_data: TaskFromMilestoneRequest = Body(..., description="Task creation data"),
    created_by: Optional[str] = Query(
        None, description="ID of user/agent creating task"
    ),
):
    """Create task from milestone"""
    try:
        task_id = await app.state.goals_service.create_task_from_milestone(
            milestone_id=milestone_id,
            title=task_data.title,
            description=task_data.description,
            task_type=task_data.task_type,
            complexity_level=task_data.complexity_level,
            estimated_hours=task_data.estimated_hours,
            due_date=task_data.due_date,
            assigned_team_id=task_data.assigned_team_id,
            assigned_agent_id=task_data.assigned_agent_id,
            priority=task_data.priority,
            requirements=task_data.requirements,
            acceptance_criteria=task_data.acceptance_criteria,
            dependencies=task_data.dependencies,
            created_by_agent_id=created_by,
        )

        return {"task_id": task_id, "status": "created"}

    except Exception as e:
        logger.error(f"Error creating task from milestone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/generate-execution-plan",
    tags=["goals-management"],
    summary="Generate execution plan",
    description="Generate comprehensive milestone and task execution plan for a goal",
)
async def generate_execution_plan(
    goal_id: str = Path(..., description="Goal ID"),
    planning_context: Optional[Dict[str, Any]] = Body(
        None, description="Additional planning context"
    ),
):
    """Generate execution plan with milestones and tasks"""
    try:
        execution_plan = (
            await app.state.milestone_task_engine.generate_goal_execution_plan(
                goal_id=goal_id, planning_context=planning_context
            )
        )

        return execution_plan

    except Exception as e:
        logger.error(f"Error generating execution plan for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/generate-monthly-milestones",
    tags=["goals-management"],
    summary="Generate monthly milestones",
    description="Generate monthly milestone breakdown for a goal",
)
async def generate_monthly_milestones(
    goal_id: str = Path(..., description="Goal ID"),
    start_date: Optional[date] = Query(None, description="Start date for milestones"),
    end_date: Optional[date] = Query(None, description="End date for milestones"),
):
    """Generate monthly milestones for goal"""
    try:
        milestone_ids = (
            await app.state.milestone_task_engine.generate_monthly_milestones(
                goal_id=goal_id, start_date=start_date, end_date=end_date
            )
        )

        return {
            "goal_id": goal_id,
            "milestone_ids": milestone_ids,
            "count": len(milestone_ids),
            "status": "generated",
        }

    except Exception as e:
        logger.error(f"Error generating monthly milestones for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/milestones/{milestone_id}/generate-weekly-tasks",
    tags=["goals-management"],
    summary="Generate weekly tasks",
    description="Generate weekly task breakdown for a milestone",
)
async def generate_weekly_tasks(
    milestone_id: str = Path(..., description="Milestone ID"),
    focus_areas: Optional[List[str]] = Body(
        None, description="Focus areas for task generation"
    ),
):
    """Generate weekly tasks for milestone"""
    try:
        task_ids = (
            await app.state.milestone_task_engine.generate_weekly_tasks_for_milestone(
                milestone_id=milestone_id, focus_areas=focus_areas
            )
        )

        return {
            "milestone_id": milestone_id,
            "task_ids": task_ids,
            "count": len(task_ids),
            "status": "generated",
        }

    except Exception as e:
        logger.error(f"Error generating weekly tasks for milestone {milestone_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/generate-cross-functional-tasks",
    tags=["goals-management"],
    summary="Generate cross-functional tasks",
    description="Generate tasks across different business functions for a goal",
)
async def generate_cross_functional_tasks(
    goal_id: str = Path(..., description="Goal ID"),
    target_functions: Optional[List[str]] = Body(
        None, description="Target business functions"
    ),
):
    """Generate cross-functional tasks for goal"""
    try:
        functional_tasks = (
            await app.state.milestone_task_engine.generate_cross_functional_tasks(
                goal_id=goal_id, target_functions=target_functions
            )
        )

        return {
            "goal_id": goal_id,
            "functional_tasks": functional_tasks,
            "total_tasks": sum(len(tasks) for tasks in functional_tasks.values()),
            "status": "generated",
        }

    except Exception as e:
        logger.error(f"Error generating cross-functional tasks for goal {goal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/conversations",
    tags=["goals-management"],
    summary="Create goal conversation",
    description="Create AI-powered conversation for goal planning and discussion",
)
async def create_goal_conversation(
    goal_id: str = Path(..., description="Goal ID"),
    conversation_data: GoalConversationCreateRequest = Body(
        ..., description="Conversation creation data"
    ),
    created_by: Optional[str] = Query(
        None, description="ID of user/agent creating conversation"
    ),
):
    """Create goal conversation"""
    try:
        from .goal_conversation_service import ConversationType

        conversation_id = (
            await app.state.goal_conversation_service.create_goal_conversation(
                goal_id=goal_id,
                conversation_type=ConversationType(conversation_data.conversation_type),
                conversation_title=conversation_data.conversation_title,
                initial_context=conversation_data.initial_context,
                participants=conversation_data.participants,
                created_by=created_by,
            )
        )

        return {"conversation_id": conversation_id, "status": "created"}

    except Exception as e:
        logger.error(f"Error creating goal conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/conversations/{conversation_id}",
    tags=["goals-management"],
    summary="Get goal conversation",
    description="Get full conversation with messages, insights, and action items",
)
async def get_goal_conversation(
    conversation_id: str = Path(..., description="Conversation ID")
):
    """Get goal conversation"""
    try:
        conversation = await app.state.goal_conversation_service.get_conversation(
            conversation_id
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/conversations/{conversation_id}/messages",
    tags=["goals-management"],
    summary="Add message to conversation",
    description="Add a new message to a goal conversation",
)
async def add_message_to_conversation(
    conversation_id: str = Path(..., description="Conversation ID"),
    message_data: ConversationMessageRequest = Body(..., description="Message data"),
    sender_id: Optional[str] = Query(None, description="ID of message sender"),
):
    """Add message to conversation"""
    try:
        from .goal_conversation_service import MessageType

        message_id = (
            await app.state.goal_conversation_service.add_message_to_conversation(
                conversation_id=conversation_id,
                message_type=MessageType(message_data.message_type),
                sender_id=sender_id,
                sender_name=message_data.sender_name,
                content=message_data.content,
                metadata=message_data.metadata,
                references=message_data.references,
            )
        )

        return {"message_id": message_id, "status": "added"}

    except Exception as e:
        logger.error(f"Error adding message to conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/conversations/{conversation_id}/generate-milestones",
    tags=["goals-management"],
    summary="Generate milestones from conversation",
    description="Generate milestone recommendations based on conversation analysis",
)
async def generate_planning_milestones(
    conversation_id: str = Path(..., description="Conversation ID"),
    planning_context: Optional[Dict[str, Any]] = Body(
        None, description="Additional planning context"
    ),
):
    """Generate planning milestones from conversation"""
    try:
        milestones = (
            await app.state.goal_conversation_service.generate_planning_milestones(
                conversation_id=conversation_id, planning_context=planning_context
            )
        )

        return {
            "conversation_id": conversation_id,
            "milestones": milestones,
            "count": len(milestones),
            "status": "generated",
        }

    except Exception as e:
        logger.error(f"Error generating planning milestones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/conversations/{conversation_id}/conduct-progress-review",
    tags=["goals-management"],
    summary="Conduct progress review",
    description="Conduct AI-powered progress review for a goal conversation",
)
async def conduct_progress_review(
    conversation_id: str = Path(..., description="Conversation ID"),
    review_period_days: int = Query(
        30, ge=1, le=365, description="Review period in days"
    ),
):
    """Conduct progress review"""
    try:
        review_analysis = (
            await app.state.goal_conversation_service.conduct_progress_review(
                conversation_id=conversation_id, review_period_days=review_period_days
            )
        )

        return review_analysis

    except Exception as e:
        logger.error(f"Error conducting progress review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/conversations/{conversation_id}/extract-action-items",
    tags=["goals-management"],
    summary="Extract action items",
    description="Extract and create action items from conversation analysis",
)
async def extract_action_items(
    conversation_id: str = Path(..., description="Conversation ID"),
    auto_assign: bool = Query(
        True, description="Whether to automatically assign action items"
    ),
):
    """Extract action items from conversation"""
    try:
        action_items = await app.state.goal_conversation_service.extract_action_items_from_conversation(
            conversation_id=conversation_id, auto_assign=auto_assign
        )

        return {
            "conversation_id": conversation_id,
            "action_items": action_items,
            "count": len(action_items),
            "status": "extracted",
        }

    except Exception as e:
        logger.error(f"Error extracting action items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/goals/{goal_id}/conversations",
    tags=["goals-management"],
    summary="Get goal conversations",
    description="Get all conversations for a goal with optional filtering",
)
async def get_goal_conversations(
    goal_id: str = Path(..., description="Goal ID"),
    conversation_type: Optional[str] = Query(
        None, description="Filter by conversation type"
    ),
    status: Optional[str] = Query(None, description="Filter by conversation status"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of conversations"),
):
    """Get conversations for a goal"""
    try:
        from .goal_conversation_service import (ConversationStatus,
                                                ConversationType)

        conv_type = ConversationType(conversation_type) if conversation_type else None
        conv_status = ConversationStatus(status) if status else None

        conversations = (
            await app.state.goal_conversation_service.get_goal_conversations(
                goal_id=goal_id,
                conversation_type=conv_type,
                status=conv_status,
                limit=limit,
            )
        )

        return {
            "goal_id": goal_id,
            "conversations": conversations,
            "count": len(conversations),
        }

    except Exception as e:
        logger.error(f"Error getting goal conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/goals/{goal_id}/track-progress",
    tags=["goals-management"],
    summary="Record progress tracking update",
    description="Record detailed progress update with tracking and risk assessment",
)
async def record_progress_tracking(
    goal_id: str = Path(..., description="Goal ID"),
    progress_data: ProgressUpdateRequest = Body(
        ..., description="Progress tracking data"
    ),
    recorded_by: Optional[str] = Query(
        None, description="ID of user/agent recording progress"
    ),
):
    """Record progress tracking update"""
    try:
        snapshot_id = await app.state.goal_tracking_service.record_progress_update(
            goal_id=goal_id,
            progress_percentage=progress_data.progress_percentage,
            current_value=progress_data.current_value,
            milestone_id=progress_data.milestone_id,
            notes=progress_data.notes,
            recorded_by=recorded_by,
            confidence_score=progress_data.confidence_score,
            trigger_alerts=progress_data.trigger_alerts,
        )

        return {"goal_id": goal_id, "snapshot_id": snapshot_id, "status": "recorded"}

    except Exception as e:
        logger.error(f"Error recording progress tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/goals/{goal_id}/deadline-risk",
    tags=["goals-management"],
    summary="Assess deadline risk",
    description="Get comprehensive deadline risk assessment for a goal",
)
async def assess_deadline_risk(goal_id: str = Path(..., description="Goal ID")):
    """Assess deadline risk for goal"""
    try:
        deadline_risk = await app.state.goal_tracking_service.assess_goal_deadline_risk(
            goal_id
        )

        return {
            "goal_id": deadline_risk.goal_id,
            "risk_level": deadline_risk.risk_level.value,
            "probability_of_delay": float(deadline_risk.probability_of_delay),
            "estimated_completion_date": deadline_risk.estimated_completion_date.isoformat(),
            "days_at_risk": deadline_risk.days_at_risk,
            "critical_path_items": deadline_risk.critical_path_items,
            "mitigation_strategies": deadline_risk.mitigation_strategies,
            "updated_at": deadline_risk.updated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error assessing deadline risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/goals/{goal_id}/progress-report",
    tags=["goals-management"],
    summary="Generate progress report",
    description="Generate comprehensive progress report for a goal",
)
async def generate_progress_report(
    goal_id: str = Path(..., description="Goal ID"),
    report_period_days: int = Query(
        30, ge=1, le=365, description="Report period in days"
    ),
):
    """Generate progress report for goal"""
    try:
        report = await app.state.goal_tracking_service.generate_progress_report(
            goal_id=goal_id, report_period_days=report_period_days
        )

        return report

    except Exception as e:
        logger.error(f"Error generating progress report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/organizations/{organization_id}/goals-dashboard",
    tags=["goals-management"],
    summary="Get organization goals dashboard",
    description="Get comprehensive dashboard for all organization goals",
)
async def get_organization_goals_dashboard(
    organization_id: str = Path(..., description="Organization ID")
):
    """Get organization goals dashboard"""
    try:
        dashboard = await app.state.goals_service.get_organization_goals_dashboard(
            organization_id
        )
        return dashboard

    except Exception as e:
        logger.error(f"Error getting organization dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/organizations/{organization_id}/tracking-dashboard",
    tags=["goals-management"],
    summary="Get tracking dashboard",
    description="Get comprehensive tracking dashboard with risk assessments",
)
async def get_tracking_dashboard(
    organization_id: str = Path(..., description="Organization ID")
):
    """Get organization tracking dashboard"""
    try:
        dashboard = (
            await app.state.goal_tracking_service.get_organization_tracking_dashboard(
                organization_id
            )
        )
        return dashboard

    except Exception as e:
        logger.error(f"Error getting tracking dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Knowledge Management API Endpoints
# ================================


@app.post(
    "/knowledge/organizations/{organization_id}/documents",
    tags=["knowledge-management"],
    summary="Upload Organizational Document",
    response_model=DocumentMetadata,
)
async def upload_organization_document(
    organization_id: str = Path(..., description="Organization ID"),
    file: UploadFile = File(..., description="Document file to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """Upload a document to organizational knowledge base"""
    try:
        tags_list = []
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]

        document = await knowledge_manager.upload_document(
            file_content=file.file,
            filename=file.filename,
            title=title,
            organization_id=organization_id,
            tags=tags_list,
        )

        return document

    except Exception as e:
        logger.error(f"Error uploading organizational document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/knowledge/organizations/{organization_id}/url",
    tags=["knowledge-management"],
    summary="Add URL to Organizational Knowledge",
    response_model=DocumentMetadata,
)
async def add_organization_url(
    organization_id: str = Path(..., description="Organization ID"),
    url: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Add URL content to organizational knowledge base"""
    try:
        document = await knowledge_manager.upload_url(
            url=url, title=title, organization_id=organization_id, tags=tags or []
        )

        return document

    except Exception as e:
        logger.error(f"Error adding organizational URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/organizations/{organization_id}/documents",
    tags=["knowledge-management"],
    summary="List Organizational Documents",
    response_model=List[DocumentMetadata],
)
async def list_organization_documents(
    organization_id: str = Path(..., description="Organization ID")
):
    """Get list of organizational documents"""
    try:
        documents = await knowledge_manager.get_documents(
            organization_id=organization_id
        )
        return documents

    except Exception as e:
        logger.error(f"Error listing organizational documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/organizations/{organization_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Get Organizational Document",
    response_model=DocumentMetadata,
)
async def get_organization_document(
    organization_id: str = Path(..., description="Organization ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get organizational document metadata"""
    try:
        document = await knowledge_manager.get_document_metadata(
            doc_id=doc_id, organization_id=organization_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organizational document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/organizations/{organization_id}/documents/{doc_id}/content",
    tags=["knowledge-management"],
    summary="Get Organizational Document Content",
)
async def get_organization_document_content(
    organization_id: str = Path(..., description="Organization ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get full content of organizational document"""
    try:
        content = await knowledge_manager.get_document_content(
            doc_id=doc_id, organization_id=organization_id
        )

        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"content": content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organizational document content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/knowledge/organizations/{organization_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Update Organizational Document",
    response_model=DocumentMetadata,
)
async def update_organization_document(
    organization_id: str = Path(..., description="Organization ID"),
    doc_id: str = Path(..., description="Document ID"),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Update organizational document metadata"""
    try:
        document = await knowledge_manager.update_document(
            doc_id=doc_id, title=title, tags=tags, organization_id=organization_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organizational document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/knowledge/organizations/{organization_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Delete Organizational Document",
)
async def delete_organization_document(
    organization_id: str = Path(..., description="Organization ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Delete organizational document"""
    try:
        success = await knowledge_manager.delete_document(
            doc_id=doc_id, organization_id=organization_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organizational document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Team Knowledge Management Endpoints


@app.post(
    "/knowledge/teams/{team_id}/documents",
    tags=["knowledge-management"],
    summary="Upload Team Document",
    response_model=DocumentMetadata,
)
async def upload_team_document(
    team_id: str = Path(..., description="Team ID"),
    file: UploadFile = File(..., description="Document file to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """Upload a document to team knowledge base"""
    try:
        tags_list = []
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]

        document = await knowledge_manager.upload_document(
            file_content=file.file,
            filename=file.filename,
            title=title,
            team_id=team_id,
            tags=tags_list,
        )

        return document

    except Exception as e:
        logger.error(f"Error uploading team document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/knowledge/teams/{team_id}/url",
    tags=["knowledge-management"],
    summary="Add URL to Team Knowledge",
    response_model=DocumentMetadata,
)
async def add_team_url(
    team_id: str = Path(..., description="Team ID"),
    url: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Add URL content to team knowledge base"""
    try:
        document = await knowledge_manager.upload_url(
            url=url, title=title, team_id=team_id, tags=tags or []
        )

        return document

    except Exception as e:
        logger.error(f"Error adding team URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/teams/{team_id}/documents",
    tags=["knowledge-management"],
    summary="List Team Documents",
    response_model=List[DocumentMetadata],
)
async def list_team_documents(team_id: str = Path(..., description="Team ID")):
    """Get list of team documents"""
    try:
        documents = await knowledge_manager.get_documents(team_id=team_id)
        return documents

    except Exception as e:
        logger.error(f"Error listing team documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/teams/{team_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Get Team Document",
    response_model=DocumentMetadata,
)
async def get_team_document(
    team_id: str = Path(..., description="Team ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get team document metadata"""
    try:
        document = await knowledge_manager.get_document_metadata(
            doc_id=doc_id, team_id=team_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/teams/{team_id}/documents/{doc_id}/content",
    tags=["knowledge-management"],
    summary="Get Team Document Content",
)
async def get_team_document_content(
    team_id: str = Path(..., description="Team ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get full content of team document"""
    try:
        content = await knowledge_manager.get_document_content(
            doc_id=doc_id, team_id=team_id
        )

        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"content": content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team document content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/knowledge/teams/{team_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Update Team Document",
    response_model=DocumentMetadata,
)
async def update_team_document(
    team_id: str = Path(..., description="Team ID"),
    doc_id: str = Path(..., description="Document ID"),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Update team document metadata"""
    try:
        document = await knowledge_manager.update_document(
            doc_id=doc_id, title=title, tags=tags, team_id=team_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/knowledge/teams/{team_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Delete Team Document",
)
async def delete_team_document(
    team_id: str = Path(..., description="Team ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Delete team document"""
    try:
        success = await knowledge_manager.delete_document(
            doc_id=doc_id, team_id=team_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent Knowledge Management Endpoints


@app.post(
    "/knowledge/agents/{agent_id}/documents",
    tags=["knowledge-management"],
    summary="Upload Agent Document",
    response_model=DocumentMetadata,
)
async def upload_agent_document(
    agent_id: str = Path(..., description="Agent ID"),
    file: UploadFile = File(..., description="Document file to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """Upload a document to agent knowledge base"""
    try:
        tags_list = []
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]

        document = await knowledge_manager.upload_document(
            file_content=file.file,
            filename=file.filename,
            title=title,
            agent_id=agent_id,
            tags=tags_list,
        )

        return document

    except Exception as e:
        logger.error(f"Error uploading agent document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/knowledge/agents/{agent_id}/url",
    tags=["knowledge-management"],
    summary="Add URL to Agent Knowledge",
    response_model=DocumentMetadata,
)
async def add_agent_url(
    agent_id: str = Path(..., description="Agent ID"),
    url: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Add URL content to agent knowledge base"""
    try:
        document = await knowledge_manager.upload_url(
            url=url, title=title, agent_id=agent_id, tags=tags or []
        )

        return document

    except Exception as e:
        logger.error(f"Error adding agent URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/agents/{agent_id}/documents",
    tags=["knowledge-management"],
    summary="List Agent Documents",
    response_model=List[DocumentMetadata],
)
async def list_agent_documents(agent_id: str = Path(..., description="Agent ID")):
    """Get list of agent documents"""
    try:
        documents = await knowledge_manager.get_documents(agent_id=agent_id)
        return documents

    except Exception as e:
        logger.error(f"Error listing agent documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/agents/{agent_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Get Agent Document",
    response_model=DocumentMetadata,
)
async def get_agent_document(
    agent_id: str = Path(..., description="Agent ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get agent document metadata"""
    try:
        document = await knowledge_manager.get_document_metadata(
            doc_id=doc_id, agent_id=agent_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/knowledge/agents/{agent_id}/documents/{doc_id}/content",
    tags=["knowledge-management"],
    summary="Get Agent Document Content",
)
async def get_agent_document_content(
    agent_id: str = Path(..., description="Agent ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Get full content of agent document"""
    try:
        content = await knowledge_manager.get_document_content(
            doc_id=doc_id, agent_id=agent_id
        )

        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"content": content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent document content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/knowledge/agents/{agent_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Update Agent Document",
    response_model=DocumentMetadata,
)
async def update_agent_document(
    agent_id: str = Path(..., description="Agent ID"),
    doc_id: str = Path(..., description="Document ID"),
    title: Optional[str] = Body(None, embed=True),
    tags: Optional[List[str]] = Body(None, embed=True),
):
    """Update agent document metadata"""
    try:
        document = await knowledge_manager.update_document(
            doc_id=doc_id, title=title, tags=tags, agent_id=agent_id
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/knowledge/agents/{agent_id}/documents/{doc_id}",
    tags=["knowledge-management"],
    summary="Delete Agent Document",
)
async def delete_agent_document(
    agent_id: str = Path(..., description="Agent ID"),
    doc_id: str = Path(..., description="Document ID"),
):
    """Delete agent document"""
    try:
        success = await knowledge_manager.delete_document(
            doc_id=doc_id, agent_id=agent_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge Search Endpoints


@app.get(
    "/knowledge/search",
    tags=["knowledge-management"],
    summary="Search Knowledge Base",
    response_model=List[DocumentMetadata],
)
async def search_knowledge(
    query: str = Query(..., description="Search query"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
):
    """Search across knowledge base"""
    try:
        documents = await knowledge_manager.search_documents(
            query=query,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            limit=limit,
        )

        return documents

    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# Container Management API Endpoints
# ================================


@app.post(
    "/agents/{agent_id}/container/create",
    tags=["container-management"],
    summary="Create Agent Container",
    response_model=ContainerStatus,
)
async def create_agent_container(
    agent_id: str = Path(..., description="Agent ID"),
    config: Optional[ContainerConfig] = Body(
        None, description="Container configuration"
    ),
):
    """Create a new container for an AI agent"""
    try:
        status = await container_manager.create_agent_container(agent_id, config)
        return status

    except Exception as e:
        logger.error(f"Error creating container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/container/start",
    tags=["container-management"],
    summary="Start Agent Container",
    response_model=ContainerStatus,
)
async def start_agent_container(agent_id: str = Path(..., description="Agent ID")):
    """Start an agent container"""
    try:
        status = await container_manager.start_container(agent_id)
        return status

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/container/stop",
    tags=["container-management"],
    summary="Stop Agent Container",
    response_model=ContainerStatus,
)
async def stop_agent_container(
    agent_id: str = Path(..., description="Agent ID"),
    timeout: int = Body(30, description="Stop timeout in seconds"),
):
    """Stop an agent container"""
    try:
        status = await container_manager.stop_container(agent_id, timeout)
        return status

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/container/restart",
    tags=["container-management"],
    summary="Restart Agent Container",
    response_model=ContainerStatus,
)
async def restart_agent_container(
    agent_id: str = Path(..., description="Agent ID"),
    timeout: int = Body(30, description="Restart timeout in seconds"),
):
    """Restart an agent container"""
    try:
        status = await container_manager.restart_container(agent_id, timeout)
        return status

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error restarting container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/agents/{agent_id}/container",
    tags=["container-management"],
    summary="Remove Agent Container",
)
async def remove_agent_container(
    agent_id: str = Path(..., description="Agent ID"),
    force: bool = Query(False, description="Force removal of running container"),
):
    """Remove an agent container"""
    try:
        success = await container_manager.remove_container(agent_id, force)

        if success:
            return {"message": f"Container for agent {agent_id} removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove container")

    except Exception as e:
        logger.error(f"Error removing container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/agents/{agent_id}/container/status",
    tags=["container-management"],
    summary="Get Agent Container Status",
    response_model=Optional[ContainerStatus],
)
async def get_agent_container_status(agent_id: str = Path(..., description="Agent ID")):
    """Get container status for an agent"""
    try:
        status = await container_manager.get_container_status(agent_id)
        return status

    except Exception as e:
        logger.error(f"Error getting container status for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/containers/agents",
    tags=["container-management"],
    summary="List Agent Containers",
    response_model=List[ContainerStatus],
)
async def list_agent_containers():
    """List all agent containers"""
    try:
        containers = await container_manager.list_agent_containers()
        return containers

    except Exception as e:
        logger.error(f"Error listing agent containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/agents/{agent_id}/container/logs",
    tags=["container-management"],
    summary="Get Agent Container Logs",
)
async def get_agent_container_logs(
    agent_id: str = Path(..., description="Agent ID"),
    tail: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    since: Optional[str] = Query(
        None, description="Show logs since timestamp (ISO format)"
    ),
):
    """Get container logs for an agent"""
    try:
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format")

        logs = await container_manager.get_container_logs(
            agent_id=agent_id, tail=tail, since=since_dt
        )

        return {"logs": logs}

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting container logs for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/agents/{agent_id}/container/execute",
    tags=["container-management"],
    summary="Execute Command in Container",
)
async def execute_container_command(
    agent_id: str = Path(..., description="Agent ID"),
    command: str = Body(..., description="Command to execute"),
    working_dir: Optional[str] = Body(None, description="Working directory"),
):
    """Execute a command in the agent container"""
    try:
        result = await container_manager.execute_command(
            agent_id=agent_id, command=command, working_dir=working_dir
        )

        return result

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing command in container for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time log streaming
@app.websocket("/agents/{agent_id}/container/logs/stream")
async def stream_agent_container_logs(websocket: WebSocket, agent_id: str):
    """Stream container logs in real-time via WebSocket"""
    await websocket.accept()

    try:
        # Check if container exists
        status = await container_manager.get_container_status(agent_id)
        if not status:
            await websocket.send_json({"error": "Container not found"})
            await websocket.close()
            return

        await websocket.send_json({"status": "connected", "agent_id": agent_id})

        # Stream logs
        async for log_entry in container_manager.stream_container_logs(agent_id):
            await websocket.send_json(
                {
                    "timestamp": log_entry.timestamp.isoformat(),
                    "stream": log_entry.stream,
                    "message": log_entry.message,
                }
            )

    except Exception as e:
        logger.error(f"Error in log stream for agent {agent_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
        finally:
            try:
                await websocket.close()
            except:
                pass


# ============================================================================
# RAG (Retrieval-Augmented Generation) Endpoints
# ============================================================================


@app.post("/rag/search")
async def search_knowledge_context(
    query: str = Body(..., embed=True),
    organization_id: Optional[str] = Body(None, embed=True),
    team_id: Optional[str] = Body(None, embed=True),
    agent_id: Optional[str] = Body(None, embed=True),
    max_results: int = Body(5, embed=True),
    similarity_threshold: float = Body(0.7, embed=True),
):
    """Search for relevant knowledge context using RAG"""
    try:
        context = await rag_system.search_relevant_context(
            query=query,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            max_results=max_results,
            similarity_threshold=similarity_threshold,
        )

        return {
            "query": context.query,
            "relevant_chunks": [
                {
                    "document_id": chunk.document_id,
                    "document_title": chunk.metadata.get("document_title", "Unknown"),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.metadata,
                }
                for chunk in context.relevant_chunks
            ],
            "similarity_scores": context.similarity_scores,
            "total_documents": context.total_documents,
            "context_length": context.context_length,
        }

    except Exception as e:
        logger.error(f"Error searching knowledge context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/enhance-prompt")
async def enhance_prompt_with_context(
    message: str = Body(..., embed=True),
    organization_id: Optional[str] = Body(None, embed=True),
    team_id: Optional[str] = Body(None, embed=True),
    agent_id: Optional[str] = Body(None, embed=True),
    max_context_length: int = Body(4000, embed=True),
):
    """Enhance a prompt with relevant context using RAG"""
    try:
        enhanced_prompt = await rag_system.get_contextual_prompt(
            user_message=message,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            max_context_length=max_context_length,
        )

        return {
            "original_message": message,
            "enhanced_prompt": enhanced_prompt,
            "context_added": len(enhanced_prompt) > len(message),
        }

    except Exception as e:
        logger.error(f"Error enhancing prompt with context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/reindex")
async def reindex_knowledge_base(
    organization_id: Optional[str] = Body(None, embed=True),
    team_id: Optional[str] = Body(None, embed=True),
    agent_id: Optional[str] = Body(None, embed=True),
):
    """Reindex all documents in a scope for RAG"""
    try:
        results = await rag_system.index_all_documents(
            organization_id=organization_id, team_id=team_id, agent_id=agent_id
        )

        return {
            "scope": {
                "organization_id": organization_id,
                "team_id": team_id,
                "agent_id": agent_id,
            },
            "results": results,
            "message": f"Indexed {results['indexed']} documents, {results['failed']} failed, {results['skipped']} skipped",
        }

    except Exception as e:
        logger.error(f"Error reindexing knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats")
async def get_rag_index_stats():
    """Get statistics about the RAG index"""
    try:
        stats = await rag_system.get_index_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/documents/{doc_id}/reindex")
async def reindex_document(
    doc_id: str,
    organization_id: Optional[str] = Body(None, embed=True),
    team_id: Optional[str] = Body(None, embed=True),
    agent_id: Optional[str] = Body(None, embed=True),
):
    """Reindex a specific document for RAG"""
    try:
        # Get document metadata
        document = await knowledge_manager.get_document_metadata(
            doc_id=doc_id,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Reindex the document
        success = await rag_system.index_document(document)

        if success:
            return {
                "document_id": doc_id,
                "status": "reindexed",
                "message": f"Document '{document.title}' has been reindexed successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reindex document")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Real-time WebSocket Endpoints
# ============================================================================


@app.websocket("/ws/updates")
async def websocket_real_time_updates(
    websocket: WebSocket,
    organization_id: Optional[str] = None,
    team_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    subscriptions: Optional[str] = None,
):
    """Main WebSocket endpoint for real-time updates"""
    import uuid

    connection_id = str(uuid.uuid4())

    # Parse subscriptions
    subscription_list = []
    if subscriptions:
        subscription_list = subscriptions.split(",")

    try:
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            user_id=user_id,
            subscriptions=subscription_list,
        )

        # Keep connection alive and handle pings
        while True:
            try:
                # Wait for ping messages or disconnection
                message = await websocket.receive_text()

                # Handle ping/pong
                if message == "ping":
                    await websocket.send_text("pong")
                    connection.last_ping = datetime.now()
                else:
                    # Parse other messages (subscription updates, etc.)
                    try:
                        data = json.loads(message)
                        if data.get("type") == "subscribe":
                            # Update subscriptions
                            new_subs = data.get("subscriptions", [])
                            connection.scope.subscriptions.clear()
                            for sub in new_subs:
                                try:
                                    connection.scope.subscriptions.add(UpdateType(sub))
                                except ValueError:
                                    pass

                            await connection.send_update(
                                WebSocketUpdate(
                                    type=UpdateType.SYSTEM_NOTIFICATION,
                                    data={
                                        "message": "Subscriptions updated",
                                        "subscriptions": list(
                                            connection.scope.subscriptions
                                        ),
                                    },
                                )
                            )
                    except json.JSONDecodeError:
                        pass

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@app.websocket("/ws/agent/{agent_id}/updates")
async def websocket_agent_updates(websocket: WebSocket, agent_id: str):
    """WebSocket endpoint for specific agent updates"""
    import uuid

    connection_id = f"agent-{agent_id}-{uuid.uuid4()}"

    try:
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            agent_id=agent_id,
            subscriptions=[
                UpdateType.AGENT_STATUS.value,
                UpdateType.TASK_STATUS.value,
                UpdateType.TASK_PROGRESS.value,
                UpdateType.CONTAINER_STATUS.value,
                UpdateType.CHAT_MESSAGE.value,
                UpdateType.CHAT_TYPING.value,
            ],
        )

        # Keep connection alive
        while True:
            try:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
                    connection.last_ping = datetime.now()
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Agent WebSocket error for {agent_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@app.websocket("/ws/agents/{agent_id}/conversations/{conversation_id}")
async def websocket_agent_conversation(
    websocket: WebSocket, agent_id: str, conversation_id: str
):
    """WebSocket endpoint for real-time agent conversation"""
    import uuid

    connection_id = f"conversation-{conversation_id}-{uuid.uuid4()}"

    await websocket.accept()

    try:
        # Store connection for broadcasting
        active_conversations = getattr(app.state, "active_conversations", {})
        if conversation_id not in active_conversations:
            active_conversations[conversation_id] = []
        active_conversations[conversation_id].append(websocket)
        app.state.active_conversations = active_conversations

        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "message":
                    # Handle new message
                    message_content = data.get("content", "")
                    if message_content:
                        # Store message in database
                        async with get_db_connection() as conn:
                            message_id = await conn.fetchval(
                                """
                                INSERT INTO agent_conversations (session_id, agent_id, message_type, content)
                                VALUES ($1, $2, 'user', $3)
                                RETURNING id
                            """,
                                conversation_id,
                                agent_id,
                                message_content,
                            )

                            # Update session activity
                            await conn.execute(
                                """
                                UPDATE chat_sessions 
                                SET last_activity = CURRENT_TIMESTAMP, message_count = message_count + 1
                                WHERE id = $1
                            """,
                                conversation_id,
                            )

                        # Broadcast to all connected clients for this conversation
                        message_data = {
                            "type": "new_message",
                            "message": {
                                "id": str(message_id),
                                "conversation_id": conversation_id,
                                "role": "user",
                                "content": message_content,
                                "timestamp": datetime.now().isoformat(),
                                "status": "sent",
                            },
                        }

                        for conn in active_conversations.get(conversation_id, []):
                            try:
                                await conn.send_json(message_data)
                            except:
                                pass  # Connection might be closed

                        # TODO: Here we would trigger agent response generation
                        # For now, send a simple acknowledgment after a delay
                        await asyncio.sleep(1)

                        agent_response = {
                            "type": "new_message",
                            "message": {
                                "id": str(uuid.uuid4()),
                                "conversation_id": conversation_id,
                                "role": "agent",
                                "content": f"I received your message: {message_content}",
                                "timestamp": datetime.now().isoformat(),
                                "status": "received",
                            },
                        }

                        for conn in active_conversations.get(conversation_id, []):
                            try:
                                await conn.send_json(agent_response)
                            except:
                                pass

                        # Store agent response in database
                        async with get_db_connection() as conn:
                            await conn.execute(
                                """
                                INSERT INTO agent_conversations (session_id, agent_id, message_type, content)
                                VALUES ($1, $2, 'agent', $3)
                            """,
                                conversation_id,
                                agent_id,
                                agent_response["message"]["content"],
                            )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in conversation WebSocket: {e}")

    except Exception as e:
        logger.error(f"Conversation WebSocket error for {conversation_id}: {e}")
    finally:
        # Clean up connection
        if (
            hasattr(app.state, "active_conversations")
            and conversation_id in app.state.active_conversations
        ):
            if websocket in app.state.active_conversations[conversation_id]:
                app.state.active_conversations[conversation_id].remove(websocket)


@app.websocket("/ws/organization/{organization_id}/updates")
async def websocket_organization_updates(websocket: WebSocket, organization_id: str):
    """WebSocket endpoint for organization-wide updates"""
    import uuid

    connection_id = f"org-{organization_id}-{uuid.uuid4()}"

    try:
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            organization_id=organization_id,
            subscriptions=[
                UpdateType.AGENT_CREATED.value,
                UpdateType.AGENT_UPDATED.value,
                UpdateType.AGENT_DELETED.value,
                UpdateType.KNOWLEDGE_UPDATED.value,
                UpdateType.KNOWLEDGE_INDEXED.value,
                UpdateType.SYSTEM_NOTIFICATION.value,
            ],
        )

        # Keep connection alive
        while True:
            try:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
                    connection.last_ping = datetime.now()
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Organization WebSocket error for {organization_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


# WebSocket Statistics Endpoint
@app.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = websocket_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Manual notification endpoints for testing
@app.post("/ws/test/agent/{agent_id}/status")
async def test_agent_status_notification(
    agent_id: str,
    status: str = Body(..., embed=True),
    message: Optional[str] = Body(None, embed=True),
):
    """Test endpoint to send agent status notifications"""
    try:
        await notify_agent_status_change(
            agent_id=agent_id,
            status=status,
            additional_data={"message": message} if message else None,
        )
        return {"status": "notification_sent", "agent_id": agent_id}
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Missing API Endpoints (Goals, Teams, Organizations)
# ============================================================================


@app.get("/teams")
async def get_teams():
    """Get list of teams"""
    # Mock data for now
    return [
        {
            "id": "1",
            "name": "Development Team",
            "description": "Frontend and backend developers",
            "member_count": 5,
            "organization_id": "1",
        },
        {
            "id": "2",
            "name": "Executive Team",
            "description": "Leadership and strategy",
            "member_count": 3,
            "organization_id": "1",
        },
    ]


@app.get("/organizations/{organization_id}/goals")
async def get_organization_goals(organization_id: str):
    """Get goals for an organization"""
    # Mock data for now
    return [
        {
            "id": "1",
            "title": "Increase Development Velocity",
            "description": "Improve team productivity and code quality",
            "status": "active",
            "progress": 75,
            "organization_id": organization_id,
            "created_at": "2024-01-15T10:00:00Z",
            "due_date": "2024-12-31T23:59:59Z",
        },
        {
            "id": "2",
            "title": "Enhance AI Capabilities",
            "description": "Expand AI agent capabilities and intelligence",
            "status": "active",
            "progress": 50,
            "organization_id": organization_id,
            "created_at": "2024-02-01T10:00:00Z",
            "due_date": "2024-11-30T23:59:59Z",
        },
    ]


@app.get("/goals/{goal_id}")
async def get_goal_details(goal_id: str):
    """Get detailed information about a specific goal"""
    # Mock data for now
    return {
        "id": goal_id,
        "title": "Increase Development Velocity",
        "description": "Improve team productivity and code quality through better tooling, processes, and automation",
        "status": "active",
        "progress": 75,
        "organization_id": "1",
        "team_id": "1",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-08-06T16:30:00Z",
        "due_date": "2024-12-31T23:59:59Z",
        "milestones": [
            {
                "id": "1",
                "title": "Implement CI/CD Pipeline",
                "description": "Set up automated testing and deployment",
                "status": "completed",
                "progress": 100,
                "due_date": "2024-03-15T23:59:59Z",
            },
            {
                "id": "2",
                "title": "Enhance Code Review Process",
                "description": "Streamline code review workflow with automated tools",
                "status": "in_progress",
                "progress": 80,
                "due_date": "2024-09-30T23:59:59Z",
            },
            {
                "id": "3",
                "title": "Deploy AI-Powered Testing",
                "description": "Implement intelligent test generation and execution",
                "status": "planned",
                "progress": 25,
                "due_date": "2024-12-15T23:59:59Z",
            },
        ],
        "metrics": {
            "deployment_frequency": "Daily",
            "lead_time": "2.3 days",
            "mttr": "45 minutes",
            "change_failure_rate": "5%",
        },
        "assigned_agents": [
            {"id": "1", "name": "DevOps Agent", "role": "CI/CD Specialist"},
            {"id": "2", "name": "QA Agent", "role": "Test Automation Engineer"},
        ],
    }


@app.get("/agents/{agent_id}/tasks")
async def get_agent_tasks_list(agent_id: str):
    """Get tasks for a specific agent - GET method"""
    try:
        # Get tasks from task queue
        tasks = await app.state.task_queue.get_agent_tasks(agent_id)
        return {"agent_id": agent_id, "tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
