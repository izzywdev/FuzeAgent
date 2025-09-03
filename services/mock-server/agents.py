"""
Agents API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for agents with:
- Organization scoping and validation
- Agent management and statistics
- Tool configuration inheritance and overrides
- Performance tracking and analytics
- Pagination, search, and filtering
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging

from database import get_db, Agent, Organization, Team, Task
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Function to get organization from token header
def get_organization_from_token(request: Request, db: Session = Depends(get_db)) -> Organization:
    """Extract organization from X-Organization-Token header"""
    token = request.headers.get("X-Organization-Token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization token required"
        )

    # For demo purposes, we'll use a simple token-to-org mapping
    # In production, this would validate the token against your auth system
    org_id = "a50af4d0-27f1-40ae-aea0-e847dc5c4ba9"  # Default org for demo

    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return organization

# Pydantic models for request/response
class AgentCreate(BaseModel):
    name: str = Field(..., description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    type: str = Field("assistant", description="Type of agent")
    team_id: Optional[str] = Field(None, description="Team ID if agent belongs to a team")
    model: str = Field("claude-sonnet-4-20250514", description="AI model to use")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Agent settings")
    status: str = Field("active", description="Agent status")

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    team_id: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    type: str
    team_id: Optional[str]
    model: str
    tools: List[str]
    settings: Dict[str, Any]
    status: str
    organization_id: str
    created_at: str
    updated_at: str
    # Computed fields
    team_name: Optional[str] = None
    task_count: int = 0
    completed_tasks: int = 0
    active_tasks: int = 0

# Create router
router = APIRouter(prefix="/agents", tags=["agents"])

def agent_to_response(db: Session, agent: Agent) -> AgentResponse:
    """Convert database agent to API response format with related data."""
    # Get team name if agent belongs to a team
    team_name = None
    if agent.team_id:
        team = db.query(Team).filter(Team.id == agent.team_id).first()
        team_name = team.name if team else None

    # Calculate task statistics
    task_count = db.query(Task).filter(Task.agent_id == agent.id).count()
    completed_tasks = db.query(Task).filter(
        Task.agent_id == agent.id,
        Task.status == "completed"
    ).count()
    active_tasks = db.query(Task).filter(
        Task.agent_id == agent.id,
        Task.status.in_(["pending", "running"])
    ).count()

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        type=agent.type,
        team_id=agent.team_id,
        model=agent.model,
        tools=json.loads(agent.tools) if agent.tools else [],
        settings=json.loads(agent.settings) if agent.settings else {},
        status=agent.status,
        organization_id=agent.organization_id,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat(),
        team_name=team_name,
        task_count=task_count,
        completed_tasks=completed_tasks,
        active_tasks=active_tasks
    )

@router.get("/", response_model=List[AgentResponse])
async def get_agents(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    type: Optional[List[str]] = Query(None, description="Filter by agent type"),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order")
):
    """
    Get all agents for the current organization with pagination, search, and filtering.
    """
    # Get organization from token
    org = get_organization_from_token(request, db)

    # Build query
    query = db.query(Agent).filter(Agent.organization_id == org.id)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%")
            )
        )

    if status:
        query = query.filter(Agent.status.in_(status))

    if type:
        query = query.filter(Agent.type.in_(type))

    if team_id:
        query = query.filter(Agent.team_id == team_id)

    # Apply sorting
    if sort_by == "name":
        order_by = Agent.name.asc() if sort_order == "asc" else Agent.name.desc()
    elif sort_by == "type":
        order_by = Agent.type.asc() if sort_order == "asc" else Agent.type.desc()
    elif sort_by == "status":
        order_by = Agent.status.asc() if sort_order == "asc" else Agent.status.desc()
    else:
        order_by = Agent.created_at.asc() if sort_order == "asc" else Agent.created_at.desc()

    query = query.order_by(order_by)

    # Apply pagination
    total_count = query.count()
    agents = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    response_agents = [agent_to_response(db, agent) for agent in agents]

    return response_agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get a specific agent by ID.
    """
    # Get organization from token
    org = get_organization_from_token(request, db)

    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_to_response(db, agent)

@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent: AgentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a new agent for the organization.
    """
    # Get organization from token
    org = get_organization_from_token(request, db)

    # Validate team if provided
    if agent.team_id:
        team = db.query(Team).filter(
            Team.id == agent.team_id,
            Team.organization_id == org.id
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    # Create agent
    db_agent = Agent(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        name=agent.name,
        description=agent.description,
        type=agent.type,
        team_id=agent.team_id,
        model=agent.model,
        tools=json.dumps(agent.tools),
        settings=json.dumps(agent.settings),
        status=agent.status
    )

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)

    return agent_to_response(db, db_agent)

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update an agent.
    """
    # Get organization from token
    org = get_organization_from_token(request, db)

    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate team if being updated
    if agent_update.team_id is not None:
        if agent_update.team_id:  # Not empty string
            team = db.query(Team).filter(
                Team.id == agent_update.team_id,
                Team.organization_id == org.id
            ).first()
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
        agent.team_id = agent_update.team_id

    # Update fields
    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tools" and value is not None:
            setattr(agent, field, json.dumps(value))
        elif field == "settings" and value is not None:
            setattr(agent, field, json.dumps(value))
        elif value is not None:
            setattr(agent, field, value)

    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    return agent_to_response(db, agent)

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Delete an agent.
    """
    # Get organization from token
    org = get_organization_from_token(request, db)

    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == org.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()

    return {"message": "Agent deleted successfully"}