"""
Agents API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for agents with:
- Organization and team scoping
- Template-based agent creation
- Agent configuration management
- Performance tracking and statistics
- Tool settings inheritance and overrides
- Pagination, search, and filtering
- Status and type management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging

from database import get_db, Agent, Organization, Team, Task
from pydantic import BaseModel, Field

# Pydantic models for request/response
class AgentCreate(BaseModel):
    team_id: str = Field(..., description="ID of the team this agent belongs to")
    name: str = Field(..., description="Name of the agent")
    role: Optional[str] = Field(None, description="Role of the agent")
    type: Optional[str] = Field("developer", description="Type of agent: developer, analyst, manager, specialist")
    template_id: Optional[str] = Field(None, description="Template ID used to create this agent")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name")
    role: Optional[str] = Field(None, description="Updated role")
    type: Optional[str] = Field(None, description="Updated type")
    status: Optional[str] = Field(None, description="Updated status")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated configuration")
    team_id: Optional[str] = Field(None, description="Updated team assignment")

class AgentResponse(BaseModel):
    id: str
    team_id: str
    name: str
    role: str
    type: str
    status: str
    config: Dict[str, Any]
    template_id: str
    created_at: str
    updated_at: str
    team_name: str = ""
    task_count: int = 0
    completed_task_count: int = 0
    active_task_count: int = 0
    efficiency_rate: float = 0.0
    last_activity: str

class AgentFilters(BaseModel):
    status: Optional[List[str]] = Field(None, description="Filter by status")
    type: Optional[List[str]] = Field(None, description="Filter by type")
    team_id: Optional[str] = Field(None, description="Filter by team")
    template_id: Optional[str] = Field(None, description="Filter by template")
    search: Optional[str] = Field(None, description="Search in name and role")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")

class PaginatedAgentsResponse(BaseModel):
    agents: List[AgentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: Optional[AgentFilters]

# Create router
router = APIRouter(prefix="/organizations/{org_id}/agents", tags=["agents"])

logger = logging.getLogger(__name__)

def agent_to_response(db: Session, agent: Agent) -> AgentResponse:
    """Convert database agent to API response format with related data."""
    # Get team name
    team_name = ""
    if agent.team_id:
        team = db.query(Team).filter(Team.id == agent.team_id).first()
        if team:
            team_name = team.name

    # Calculate task statistics
    total_tasks = db.query(Task).filter(Task.agent_id == agent.id).count()
    completed_tasks = db.query(Task).filter(
        and_(Task.agent_id == agent.id, Task.status == "completed")
    ).count()
    active_tasks = db.query(Task).filter(
        and_(Task.agent_id == agent.id, Task.status == "in_progress")
    ).count()

    # Calculate efficiency rate
    efficiency_rate = 0.0
    if total_tasks > 0:
        efficiency_rate = round((completed_tasks / total_tasks) * 100, 2)

    return AgentResponse(
        id=agent.id,
        team_id=agent.team_id or "",
        name=agent.name,
        role=agent.role or "",
        type=agent.type,
        status=agent.status,
        config=json.loads(agent.config) if agent.config else {},
        template_id=agent.template_id or "",
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat(),
        team_name=team_name,
        task_count=total_tasks,
        completed_task_count=completed_tasks,
        active_task_count=active_tasks,
        efficiency_rate=efficiency_rate,
        last_activity=agent.updated_at.isoformat()
    )

@router.post("/", response_model=AgentResponse)
async def create_agent(
    org_id: str,
    agent: AgentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new agent for an organization.

    Validates organization and team relationships.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == agent.team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Create agent
    db_agent = Agent(
        id=str(uuid.uuid4()),
        team_id=agent.team_id,
        name=agent.name,
        role=agent.role,
        type=agent.type or "developer",
        status="active",
        config=json.dumps(agent.config) if agent.config else "{}",
        template_id=agent.template_id
    )

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)

    return agent_to_response(db, db_agent)

@router.get("/", response_model=PaginatedAgentsResponse)
async def list_agents(
    org_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    type: Optional[List[str]] = Query(None, description="Filter by type"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    template_id: Optional[str] = Query(None, description="Filter by template"),
    search: Optional[str] = Query(None, description="Search in name and role"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    List agents for an organization with filtering, search, and pagination.

    Supports comprehensive filtering by status, type, team, and template.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Build query
    query = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(Team.organization_id == org_id)

    # Apply filters
    if status:
        query = query.filter(Agent.status.in_(status))

    if type:
        query = query.filter(Agent.type.in_(type))

    if team_id:
        query = query.filter(Agent.team_id == team_id)

    if template_id:
        query = query.filter(Agent.template_id == template_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Agent.name.ilike(search_filter),
                Agent.role.ilike(search_filter)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Agent, sort_by, Agent.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    agents = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    agent_responses = [agent_to_response(db, a) for a in agents]

    return PaginatedAgentsResponse(
        agents=agent_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        filters=AgentFilters(
            status=status,
            type=type,
            team_id=team_id,
            template_id=template_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        ) if any([status, type, team_id, template_id, search]) else None
    )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    org_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific agent by ID.

    Includes related team and performance data.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent with team relationship for organization validation
    agent = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(
        and_(
            Agent.id == agent_id,
            Team.organization_id == org_id
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_to_response(db, agent)

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    org_id: str,
    agent_id: str,
    agent_update: AgentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing agent.

    Handles team reassignment and configuration updates.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent
    agent = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(
        and_(
            Agent.id == agent_id,
            Team.organization_id == org_id
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate team if provided
    if agent_update.team_id:
        team = db.query(Team).filter(
            and_(Team.id == agent_update.team_id, Team.organization_id == org_id)
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    # Update fields
    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "config":
            setattr(agent, field, json.dumps(value) if value else "{}")
        else:
            setattr(agent, field, value)

    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    return agent_to_response(db, agent)

@router.delete("/{agent_id}")
async def delete_agent(
    org_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an agent.

    Removes the agent from the database.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent
    agent = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(
        and_(
            Agent.id == agent_id,
            Team.organization_id == org_id
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()

    return {"message": "Agent deleted successfully"}

@router.post("/{agent_id}/start")
async def start_agent(
    org_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Start an agent.

    Updates agent status to active.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent
    agent = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(
        and_(
            Agent.id == agent_id,
            Team.organization_id == org_id
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update status to active
    agent.status = "active"
    agent.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Agent started successfully", "agent_id": agent_id}

@router.post("/{agent_id}/stop")
async def stop_agent(
    org_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Stop an agent.

    Updates agent status to inactive.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get agent
    agent = db.query(Agent).join(Team, Agent.team_id == Team.id).filter(
        and_(
            Agent.id == agent_id,
            Team.organization_id == org_id
        )
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update status to inactive
    agent.status = "inactive"
    agent.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Agent stopped successfully", "agent_id": agent_id}

@router.get("/teams/{team_id}", response_model=List[AgentResponse])
async def get_team_agents(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all agents for a specific team.
    """
    # Validate organization and team
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    agents = db.query(Agent).filter(Agent.team_id == team_id).all()
    return [agent_to_response(db, a) for a in agents]

@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_agent_templates(
    org_id: str,
    db: Session = Depends(get_db)
):
    """
    Get available agent templates.

    Returns a list of predefined agent templates.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Return mock templates
    templates = [
        {
            "id": "developer",
            "name": "Developer Agent",
            "category": "development",
            "description": "Specialized in software development and coding tasks",
            "config": {
                "model": "gpt-4",
                "temperature": 0.7,
                "tools": ["code_analysis", "git", "testing"]
            }
        },
        {
            "id": "analyst",
            "name": "Data Analyst",
            "category": "analysis",
            "description": "Expert in data analysis and reporting",
            "config": {
                "model": "gpt-4",
                "temperature": 0.5,
                "tools": ["data_analysis", "visualization", "reporting"]
            }
        },
        {
            "id": "manager",
            "name": "Project Manager",
            "category": "management",
            "description": "Handles project coordination and team management",
            "config": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.3,
                "tools": ["scheduling", "communication", "reporting"]
            }
        },
        {
            "id": "specialist",
            "name": "Domain Specialist",
            "category": "specialized",
            "description": "Expert in specific business domains",
            "config": {
                "model": "gpt-4",
                "temperature": 0.6,
                "tools": ["domain_knowledge", "research", "consulting"]
            }
        }
    ]

    return templates
