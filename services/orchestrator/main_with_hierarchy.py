from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

from database import DatabaseManager
from migration_manager import MigrationManager
from rag_manager import RAGManager
from a2a_protocol import A2AProtocolManager, TaskStatus, MessageType
from models import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    Team,
    TeamCreate,
    TeamUpdate,
    Agent,
    AgentCreate,
    AgentUpdate,
    Task,
    TaskCreate,
    TaskUpdate,
    OrganizationWithTeams,
    TeamWithAgents,
    AgentWithTeam,
    CreateAgentFromTemplate,
    CreateCustomAgent,
)
from agent_templates import template_manager, AgentCategory
from hierarchy_endpoints import router as hierarchy_router

# Default IDs for initial setup
DEFAULT_ORG_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_TEAM_ID = "550e8400-e29b-41d4-a716-446655440001"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Run database migrations and initialize RAG
    try:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
        )
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not anthropic_api_key:
            print("⚠️ ANTHROPIC_API_KEY not found - RAG features will be limited")

        migration_manager = MigrationManager(database_url)

        print("🔄 Running database migrations...")
        migration_result = await migration_manager.migrate_up()
        applied_migrations = migration_result.get("applied_versions", [])

        if applied_migrations:
            print(f"✅ Applied {len(applied_migrations)} migrations:")
            for version in applied_migrations:
                print(f"   - {version}")
        else:
            print("✅ Database is up to date - no migrations needed")

        # Get migration status
        status = await migration_manager.get_migration_status()
        print(
            f"📊 Migration Status: {status['applied_count']}/{status['total_migrations']} applied"
        )

        # Initialize RAG Manager
        print("🧠 Initializing RAG system...")
        rag_manager = RAGManager(database_url, anthropic_api_key)
        await rag_manager.initialize()
        app.state.rag_manager = rag_manager
        print("✅ RAG system initialized")

        # Initialize A2A Protocol Manager
        print("🤝 Initializing A2A protocol...")
        a2a_manager = A2AProtocolManager(database_url)
        await a2a_manager.initialize()
        app.state.a2a_manager = a2a_manager
        print("✅ A2A protocol initialized")

        # Check if default organization exists
        try:
            org = await DatabaseManager.get_organization(DEFAULT_ORG_ID)
            if org:
                print(f"✅ Default organization ready: {org['name']}")
            else:
                print("⚠️ Default organization not found - check migrations")
        except Exception as e:
            print(f"⚠️ Database connection issue: {e}")

    except Exception as e:
        print(f"❌ Startup failed: {e}")
        raise e

    yield

    # Shutdown
    print("🛑 Shutting down orchestrator...")
    if hasattr(app.state, "rag_manager"):
        await app.state.rag_manager.close()
        print("✅ RAG system closed")
    if hasattr(app.state, "a2a_manager"):
        await app.state.a2a_manager.close()
        print("✅ A2A protocol closed")


app = FastAPI(
    title="FuzeAgent Orchestrator",
    description="""
    **FuzeAgent Orchestrator API**
    
    A comprehensive AI team orchestration platform that provides hierarchical organization management,
    intelligent agent templates, and advanced task distribution capabilities.
    
    ## Features
    
    - **Hierarchical Management**: Organizations → Teams → Agents structure
    - **Agent Templates**: 11+ specialized agent templates for different roles
    - **Database Migrations**: Comprehensive migration system with rollback support
    - **Task Management**: Intelligent task assignment and tracking
    - **Real-time Updates**: WebSocket support for live monitoring
    
    ## Architecture
    
    ```
    Organizations (Top-level entities)
    └── Teams (Grouped by department/project)
        └── Agents (Specialized AI workers)
            └── Tasks (Assigned work items)
    ```
    
    ## Agent Template Categories
    
    - **Development**: Python, TypeScript, React developers
    - **Quality Assurance**: QA engineers and testers  
    - **DevOps**: Infrastructure and deployment specialists
    - **Business**: Marketing, sales, customer service
    - **Management**: Team leads and coordinators
    - **Hybrid**: AI-human collaborative roles
    
    ## Getting Started
    
    1. Create or select an organization
    2. Set up teams within the organization
    3. Create agents from templates or custom configurations
    4. Assign tasks and monitor progress
    
    ## Authentication
    
    Currently supports basic API key authentication. Enterprise features coming soon.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "FuzeAgent Support",
        "email": "support@fuzeagent.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.fuzeagent.dev", "description": "Production server"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include hierarchy router for organizational visualization
app.include_router(hierarchy_router)

# ============================================================================
# ORGANIZATION ENDPOINTS
# ============================================================================


@app.get(
    "/organizations",
    response_model=List[Organization],
    tags=["Organizations"],
    summary="List all organizations",
    description="""
    Retrieve a list of all organizations in the system.
    
    Organizations are the top-level entities in the FuzeAgent hierarchy,
    typically representing companies, departments, or major project groups.
    """,
    responses={
        200: {"description": "List of organizations retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def get_organizations():
    """Get all organizations"""
    try:
        orgs = await DatabaseManager.get_organizations()
        return orgs
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get organizations: {str(e)}"
        )


@app.post(
    "/organizations",
    response_model=Organization,
    tags=["Organizations"],
    summary="Create a new organization",
    description="""
    Create a new organization in the system.
    
    This endpoint creates a new top-level organization entity that can contain
    multiple teams and agents. Each organization has its own settings and metadata.
    
    **Required Fields:**
    - `name`: Unique organization name
    - `description`: Brief description of the organization's purpose
    
    **Optional Fields:**
    - `settings`: JSON object containing organization-specific configuration
    """,
    responses={
        201: {"description": "Organization created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Organization with this name already exists"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_organization(org_data: OrganizationCreate):
    """Create a new organization"""
    try:
        org_id = await DatabaseManager.create_organization(
            name=org_data.name,
            description=org_data.description,
            settings=org_data.settings,
        )

        org = await DatabaseManager.get_organization(org_id)
        if not org:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created organization"
            )

        return org
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create organization: {str(e)}"
        )


@app.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(org_id: str):
    """Get organization by ID"""
    try:
        org = await DatabaseManager.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get organization: {str(e)}"
        )


@app.put("/organizations/{org_id}", response_model=Organization)
async def update_organization(org_id: str, org_data: OrganizationUpdate):
    """Update organization"""
    try:
        # Convert to dict and remove None values
        update_data = {k: v for k, v in org_data.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        success = await DatabaseManager.update_organization(org_id, **update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")

        org = await DatabaseManager.get_organization(org_id)
        return org
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update organization: {str(e)}"
        )


@app.delete("/organizations/{org_id}")
async def delete_organization(org_id: str):
    """Delete organization"""
    try:
        success = await DatabaseManager.delete_organization(org_id)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")

        return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete organization: {str(e)}"
        )


# ============================================================================
# TEAM ENDPOINTS
# ============================================================================


@app.get(
    "/teams",
    response_model=List[Team],
    tags=["Teams"],
    summary="List teams",
    description="""
    Retrieve teams, optionally filtered by organization.
    
    Teams are the second level in the FuzeAgent hierarchy, representing
    departments, project groups, or specialized units within an organization.
    
    **Query Parameters:**
    - `organization_id` (optional): Filter teams by organization ID
    """,
    responses={
        200: {"description": "List of teams retrieved successfully"},
        404: {"description": "Organization not found (if organization_id provided)"},
        500: {"description": "Internal server error"},
    },
)
async def get_teams(organization_id: Optional[str] = None):
    """Get teams, optionally filtered by organization"""
    try:
        teams = await DatabaseManager.get_teams(organization_id)
        return teams
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")


@app.post("/teams", response_model=Team)
async def create_team(team_data: TeamCreate):
    """Create a new team"""
    try:
        # Verify organization exists
        org = await DatabaseManager.get_organization(team_data.organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        team_id = await DatabaseManager.create_team(
            organization_id=team_data.organization_id,
            name=team_data.name,
            description=team_data.description,
            team_type=team_data.team_type,
            settings=team_data.settings,
        )

        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created team"
            )

        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")


@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    """Get team by ID"""
    try:
        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@app.put("/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, team_data: TeamUpdate):
    """Update team"""
    try:
        update_data = {k: v for k, v in team_data.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        success = await DatabaseManager.update_team(team_id, **update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")

        team = await DatabaseManager.get_team(team_id)
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update team: {str(e)}")


@app.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete team"""
    try:
        success = await DatabaseManager.delete_team(team_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")

        return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete team: {str(e)}")


# ============================================================================
# AGENT ENDPOINTS (Updated for Teams)
# ============================================================================


@app.get("/agents")
async def get_agents(team_id: Optional[str] = None):
    """Get all agents, optionally filtered by team"""
    try:
        agents = await DatabaseManager.get_agents(team_id)
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents: {str(e)}")


@app.post("/agents")
async def create_agent(agent_data: AgentCreate):
    """Create a custom agent"""
    try:
        # Verify team exists
        team = await DatabaseManager.get_team(agent_data.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        agent_id = await DatabaseManager.insert_agent(
            team_id=agent_data.team_id,
            name=agent_data.name,
            role=agent_data.role,
            type=agent_data.type,
            config=agent_data.config,
            template_id=agent_data.template_id,
        )

        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created agent"
            )

        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@app.post("/agents/from-template")
async def create_agent_from_template(template_data: CreateAgentFromTemplate):
    """Create agent from template"""
    try:
        template = template_manager.get_template(template_data.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Get team_id from overrides or use default
        if "team_id" not in template_data.overrides:
            raise HTTPException(
                status_code=400, detail="team_id is required in overrides"
            )

        team_id = template_data.overrides["team_id"]

        # Verify team exists
        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Create agent config from template with overrides
        config = {
            "goal": template_data.overrides.get("goal", template.default_goal),
            "backstory": template_data.overrides.get(
                "backstory", template.default_backstory
            ),
            "model": template.model,
            "temperature": template_data.overrides.get(
                "temperature", template.default_temperature
            ),
            "tools": template.tools,
            "skills": template.skills,
        }

        agent_id = await DatabaseManager.insert_agent(
            team_id=team_id,
            name=template_data.overrides.get("name", f"{template.name} Agent"),
            role=template.role,
            type=template.type,
            config=config,
            template_id=template.template_id,
        )

        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created agent"
            )

        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create agent from template: {str(e)}"
        )


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent by ID"""
    try:
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


# ============================================================================
# AGENT TEMPLATE ENDPOINTS
# ============================================================================


@app.get(
    "/templates",
    tags=["Agent Templates"],
    summary="List all agent templates",
    description="""
    Retrieve all available agent templates with their categories.
    
    Agent templates provide pre-configured setups for different specialized roles:
    
    **Categories:**
    - **Development**: Python, TypeScript, React developers
    - **Quality Assurance**: QA engineers and testing specialists
    - **DevOps**: Infrastructure and deployment engineers
    - **Business**: Marketing, sales, customer service agents
    - **Management**: Team leads and project coordinators
    - **Hybrid**: AI-human collaborative roles
    
    Each template includes:
    - Specialized prompts and backstories
    - Recommended tools and capabilities
    - Default model configurations
    - Customizable parameters
    """,
    responses={
        200: {
            "description": "Templates and categories retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "templates": [
                            {
                                "template_id": "python_developer",
                                "name": "Python Developer",
                                "category": "development",
                                "description": "Expert Python developer specializing in backend development",
                                "tools": ["code_generation", "debugging", "testing"],
                                "skills": ["python", "fastapi", "pytest"],
                            }
                        ],
                        "categories": [
                            "development",
                            "quality_assurance",
                            "devops",
                            "business",
                            "management",
                            "hybrid",
                        ],
                    }
                }
            },
        }
    },
)
async def get_templates():
    """Get all agent templates"""
    templates = template_manager.get_all_templates()
    return {
        "templates": templates,
        "categories": [category.value for category in AgentCategory],
    }


@app.get("/templates/categories")
async def get_template_categories():
    """Get template categories"""
    return {"categories": [category.value for category in AgentCategory]}


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get specific template"""
    template = template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# ============================================================================
# TASK ENDPOINTS (Updated for Team Context)
# ============================================================================


@app.get("/tasks")
async def get_tasks():
    """Get all tasks"""
    try:
        tasks = await DatabaseManager.get_tasks()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@app.post("/agents/{agent_id}/tasks")
async def assign_task_to_agent(agent_id: str, task_data: TaskCreate):
    """Assign a task to an agent"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        task_id = await DatabaseManager.insert_task(
            title=task_data.title,
            description=task_data.description,
            assigned_to=agent_id,
            created_by=task_data.created_by,
        )

        return {"task_id": task_id, "message": "Task assigned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


# ============================================================================
# DATABASE MIGRATION ENDPOINTS
# ============================================================================


@app.get(
    "/migrations/status",
    tags=["Database Migrations"],
    summary="Get migration status",
    description="""
    Retrieve the current status of database migrations.
    
    This endpoint provides information about:
    - Total number of available migrations
    - Number of applied migrations  
    - Number of pending migrations
    - Last applied migration details
    - Database schema version
    
    Useful for monitoring deployment status and troubleshooting database issues.
    """,
    responses={
        200: {
            "description": "Migration status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "total_migrations": 4,
                        "applied_count": 4,
                        "pending_count": 0,
                        "last_applied": {
                            "version": "20250129_120004",
                            "name": "add_audit_logs",
                            "applied_at": "2025-01-29T12:05:23Z",
                        },
                        "status": "up_to_date",
                    }
                }
            },
        },
        500: {"description": "Failed to retrieve migration status"},
    },
)
async def get_migration_status():
    """Get current migration status"""
    try:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
        )
        migration_manager = MigrationManager(database_url)
        return await migration_manager.get_migration_status()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get migration status: {str(e)}"
        )


@app.post("/migrations/apply")
async def apply_migrations(target_version: Optional[str] = None):
    """Apply pending migrations"""
    try:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
        )
        migration_manager = MigrationManager(database_url)
        result = await migration_manager.migrate_up(target_version)
        applied = result.get("applied_versions", [])

        return {
            "applied_migrations": applied,
            "count": len(applied),
            "message": f"Applied {len(applied)} migrations successfully"
            if applied
            else "No migrations to apply",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to apply migrations: {str(e)}"
        )


@app.post("/migrations/rollback/{target_version}")
async def rollback_migrations(target_version: str):
    """Rollback migrations to target version"""
    try:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
        )
        migration_manager = MigrationManager(database_url)
        rolled_back = await migration_manager.migrate_down(target_version)

        return {
            "rolled_back_migrations": rolled_back,
            "count": len(rolled_back),
            "message": f"Rolled back {len(rolled_back)} migrations successfully"
            if rolled_back
            else "No migrations to rollback",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to rollback migrations: {str(e)}"
        )


# ============================================================================
# RAG CHAT HISTORY ENDPOINTS
# ============================================================================


@app.post(
    "/agents/{agent_id}/chat/sessions",
    tags=["RAG Chat History"],
    summary="Create a new chat session",
    description="""
    Create a new chat session for an agent. Chat sessions group related
    conversations and enable context management and summarization.
    """,
    responses={
        201: {"description": "Chat session created successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to create chat session"},
    },
)
async def create_chat_session(
    agent_id: str,
    session_data: Dict[str, Any] = {
        "session_name": "New Session",
        "session_type": "conversation",
        "participants": [],
        "context": {},
    },
):
    """Create a new chat session for an agent"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        session_id = await app.state.rag_manager.create_chat_session(
            agent_id=agent_id,
            session_name=session_data.get("session_name"),
            session_type=session_data.get("session_type", "conversation"),
            participants=session_data.get("participants"),
            context=session_data.get("context"),
        )

        return {"session_id": session_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create chat session: {str(e)}"
        )


@app.post(
    "/agents/{agent_id}/chat/sessions/{session_id}/messages",
    tags=["RAG Chat History"],
    summary="Store a conversation message",
    description="""
    Store a message in an agent's chat session with automatic vector embedding
    generation for semantic search capabilities.
    """,
    responses={
        201: {"description": "Message stored successfully"},
        404: {"description": "Agent or session not found"},
        500: {"description": "Failed to store message"},
    },
)
async def store_message(agent_id: str, session_id: str, message_data: Dict[str, Any]):
    """Store a conversation message with vector embedding"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        message_id = await app.state.rag_manager.store_conversation_message(
            agent_id=agent_id,
            session_id=session_id,
            message_type=message_data.get("message_type", "user"),
            content=message_data["content"],
            metadata=message_data.get("metadata"),
            parent_message_id=message_data.get("parent_message_id"),
        )

        return {"message_id": message_id, "status": "stored"}
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to store message: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/chat/search",
    tags=["RAG Chat History"],
    summary="Search conversation history",
    description="""
    Search an agent's conversation history using semantic similarity.
    Returns relevant messages and summaries based on the query.
    """,
    responses={
        200: {"description": "Search results retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Search failed"},
    },
)
async def search_conversation_history(
    agent_id: str,
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    session_id: Optional[str] = None,
    include_summaries: bool = True,
):
    """Search conversation history using semantic similarity"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        results = await app.state.rag_manager.search_conversation_history(
            agent_id=agent_id,
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold,
            session_id=session_id,
            include_summaries=include_summaries,
        )

        return {"query": query, "results_count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get(
    "/agents/{agent_id}/chat/sessions/{session_id}/context",
    tags=["RAG Chat History"],
    summary="Get conversation context",
    description="""
    Get recent conversation context for an agent session, including
    recent messages, summaries, and session metadata.
    """,
    responses={
        200: {"description": "Context retrieved successfully"},
        404: {"description": "Agent or session not found"},
        500: {"description": "Failed to get context"},
    },
)
async def get_conversation_context(
    agent_id: str, session_id: str, context_window: int = 20
):
    """Get recent conversation context for an agent session"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        context = await app.state.rag_manager.get_conversation_context(
            agent_id=agent_id, session_id=session_id, context_window=context_window
        )

        if "error" in context:
            raise HTTPException(status_code=404, detail=context["error"])

        return context
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@app.post(
    "/agents/{agent_id}/knowledge",
    tags=["RAG Knowledge Base"],
    summary="Add to knowledge base",
    description="""
    Add content to an agent's knowledge base for retrieval-augmented generation.
    Content is automatically embedded for semantic search.
    """,
    responses={
        201: {"description": "Knowledge item added successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to add knowledge"},
    },
)
async def add_to_knowledge_base(agent_id: str, knowledge_data: Dict[str, Any]):
    """Add content to agent's knowledge base"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        knowledge_id = await app.state.rag_manager.add_to_knowledge_base(
            agent_id=agent_id,
            content=knowledge_data["content"],
            content_type=knowledge_data.get("content_type", "text"),
            source_type=knowledge_data.get("source_type", "manual"),
            source_reference=knowledge_data.get("source_reference"),
            metadata=knowledge_data.get("metadata"),
            tags=knowledge_data.get("tags"),
        )

        return {"knowledge_id": knowledge_id, "status": "added"}
    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add knowledge: {str(e)}"
        )


@app.get(
    "/agents/{agent_id}/knowledge/search",
    tags=["RAG Knowledge Base"],
    summary="Search knowledge base",
    description="""
    Search an agent's knowledge base using semantic similarity.
    Returns relevant knowledge items based on the query.
    """,
    responses={
        200: {"description": "Knowledge search results retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Knowledge search failed"},
    },
)
async def search_knowledge_base(
    agent_id: str,
    query: str,
    limit: int = 10,
    similarity_threshold: float = 0.7,
    content_types: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
):
    """Search agent's knowledge base using semantic similarity"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        results = await app.state.rag_manager.search_knowledge_base(
            agent_id=agent_id,
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold,
            content_types=content_types,
            tags=tags,
        )

        return {"query": query, "results_count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Knowledge search failed: {str(e)}"
        )


# ============================================================================
# A2A PROTOCOL ENDPOINTS
# ============================================================================


@app.get(
    "/a2a/agents/discover",
    tags=["A2A Protocol"],
    summary="Discover agents",
    description="""
    Discover available agents based on capabilities, skills, and availability.
    Returns agent cards that can be used for task delegation and collaboration.
    """,
    responses={
        200: {"description": "Agent discovery results"},
        500: {"description": "Discovery failed"},
    },
)
async def discover_agents(
    capabilities: Optional[List[str]] = None,
    skills: Optional[List[str]] = None,
    availability_only: bool = True,
    team_id: Optional[str] = None,
    organization_id: Optional[str] = None,
):
    """Discover agents based on capabilities and availability"""
    try:
        agents = await app.state.a2a_manager.discover_agents(
            capabilities=capabilities,
            skills=skills,
            availability_only=availability_only,
            team_id=team_id,
            organization_id=organization_id,
        )

        return {
            "agents_found": len(agents),
            "agents": [agent.dict() for agent in agents],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent discovery failed: {str(e)}")


@app.post(
    "/a2a/agents/{requesting_agent_id}/delegate",
    tags=["A2A Protocol"],
    summary="Delegate task to agent",
    description="""
    Delegate a task to another agent using the A2A protocol.
    Automatically finds suitable agents if no target is specified.
    """,
    responses={
        201: {"description": "Task delegated successfully"},
        404: {"description": "Agent not found"},
        400: {"description": "No suitable agents found"},
        500: {"description": "Task delegation failed"},
    },
)
async def delegate_task(requesting_agent_id: str, task_data: Dict[str, Any]):
    """Delegate a task to another agent"""
    try:
        # Verify requesting agent exists
        agent = await DatabaseManager.get_agent(requesting_agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Requesting agent not found")

        task_id = await app.state.a2a_manager.delegate_task(
            requesting_agent_id=requesting_agent_id,
            task_title=task_data["title"],
            task_description=task_data["description"],
            task_type=task_data.get("task_type", "general"),
            target_agent_id=task_data.get("target_agent_id"),
            required_capabilities=task_data.get("required_capabilities"),
            required_skills=task_data.get("required_skills"),
            priority=task_data.get("priority", 5),
            deadline=task_data.get("deadline"),
            input_data=task_data.get("input_data"),
        )

        return {"task_id": task_id, "status": "delegated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task delegation failed: {str(e)}")


@app.get(
    "/a2a/agents/{agent_id}/card",
    tags=["A2A Protocol"],
    summary="Get agent card",
    description="""
    Get the A2A agent card containing capabilities, availability, and endpoints.
    """,
    responses={
        200: {"description": "Agent card retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to get agent card"},
    },
)
async def get_agent_card(agent_id: str):
    """Get agent card for A2A protocol"""
    try:
        # Check if agent exists in local registry
        if agent_id in app.state.a2a_manager.local_agents:
            agent_card = app.state.a2a_manager.local_agents[agent_id]
            return agent_card.dict()

        # If not in local registry, check if it's a valid agent
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Create agent card on-the-fly
        agent_card = await app.state.a2a_manager._create_agent_card_from_agent(agent)
        return agent_card.dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent card: {str(e)}"
        )


@app.post(
    "/a2a/agents/{sender_agent_id}/message",
    tags=["A2A Protocol"],
    summary="Send inter-agent message",
    description="""
    Send a message between agents using the A2A protocol.
    Supports various message types including task updates, collaboration, and handoffs.
    """,
    responses={
        201: {"description": "Message sent successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to send message"},
    },
)
async def send_a2a_message(sender_agent_id: str, message_data: Dict[str, Any]):
    """Send a message between agents"""
    try:
        # Verify sender agent exists
        agent = await DatabaseManager.get_agent(sender_agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Sender agent not found")

        # Verify recipient agent exists
        recipient_agent = await DatabaseManager.get_agent(
            message_data["recipient_agent_id"]
        )
        if not recipient_agent:
            raise HTTPException(status_code=404, detail="Recipient agent not found")

        message_id = await app.state.a2a_manager.send_message(
            sender_agent_id=sender_agent_id,
            recipient_agent_id=message_data["recipient_agent_id"],
            message_type=MessageType(message_data.get("message_type", "collaboration")),
            content=message_data["content"],
            data=message_data.get("data"),
            task_id=message_data.get("task_id"),
            conversation_id=message_data.get("conversation_id"),
            priority=message_data.get("priority", 5),
        )

        return {"message_id": message_id, "status": "sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@app.get(
    "/a2a/agents/{agent_id}/tasks",
    tags=["A2A Protocol"],
    summary="Get agent tasks",
    description="""
    Get tasks for an agent in the A2A protocol context.
    Includes both requested and assigned tasks.
    """,
    responses={
        200: {"description": "Tasks retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to get tasks"},
    },
)
async def get_agent_a2a_tasks(
    agent_id: str, status_filter: Optional[List[str]] = None, limit: int = 50
):
    """Get A2A tasks for an agent"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Convert string status to TaskStatus enum
        status_enum_filter = None
        if status_filter:
            try:
                status_enum_filter = [TaskStatus(status) for status in status_filter]
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid status value: {e}"
                )

        tasks = await app.state.a2a_manager.get_agent_tasks(
            agent_id=agent_id, status_filter=status_enum_filter, limit=limit
        )

        return {
            "agent_id": agent_id,
            "tasks_count": len(tasks),
            "tasks": [task.dict() for task in tasks],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent tasks: {str(e)}"
        )


@app.put(
    "/a2a/tasks/{task_id}/status",
    tags=["A2A Protocol"],
    summary="Update task status",
    description="""
    Update the status of an A2A task and notify relevant agents.
    """,
    responses={
        200: {"description": "Task status updated successfully"},
        404: {"description": "Task not found"},
        500: {"description": "Failed to update task status"},
    },
)
async def update_a2a_task_status(task_id: str, status_data: Dict[str, Any]):
    """Update A2A task status"""
    try:
        await app.state.a2a_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus(status_data["status"]),
            progress_percentage=status_data.get("progress_percentage"),
            output_data=status_data.get("output_data"),
            agent_id=status_data.get("agent_id"),
        )

        return {"task_id": task_id, "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update task status: {str(e)}"
        )


@app.get(
    "/a2a/agents/{agent_id}/messages",
    tags=["A2A Protocol"],
    summary="Get agent messages",
    description="""
    Get A2A messages for an agent, optionally filtered by conversation.
    """,
    responses={
        200: {"description": "Messages retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "Failed to get messages"},
    },
)
async def get_agent_a2a_messages(
    agent_id: str, conversation_id: Optional[str] = None, limit: int = 50
):
    """Get A2A messages for an agent"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        messages = await app.state.a2a_manager.get_agent_messages(
            agent_id=agent_id, conversation_id=conversation_id, limit=limit
        )

        return {
            "agent_id": agent_id,
            "messages_count": len(messages),
            "messages": [message.dict() for message in messages],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent messages: {str(e)}"
        )


# ============================================================================
# DEMO/HEALTH ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "message": "FuzeAgent Orchestrator API",
        "version": "2.0.0",
        "features": ["Organizations", "Teams", "Agents", "Templates", "Tasks"],
        "status": "running",
    }


@app.get("/demo")
async def demo_endpoint():
    """Demo endpoint with sample hierarchy"""
    try:
        # Get organizations with their teams and agents
        orgs = await DatabaseManager.get_organizations()

        if not orgs:
            return {
                "message": "No organizations found. Database may need initialization."
            }

        demo_data = {
            "organizations": len(orgs),
            "sample_org": orgs[0] if orgs else None,
            "message": "FuzeAgent Orchestrator running with hierarchical structure",
        }

        return demo_data
    except Exception as e:
        return {"error": f"Demo endpoint failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
