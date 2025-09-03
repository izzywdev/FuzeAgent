"""
Teams API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for teams with:
- Organization scoping and validation
- Team member management and statistics
- Tool configuration inheritance and overrides
- Performance tracking and analytics
- Pagination, search, and filtering
- Knowledge base integration
- Agent assignment and tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging

from database import get_db, Team, Organization, Agent, Task, Milestone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class TeamCreate(BaseModel):
    name: str = Field(..., description="Name of the team")
    description: Optional[str] = Field(None, description="Description of the team")
    team_type: Optional[str] = Field("development", description="Type of team: development, operations, management, research")
    color: Optional[str] = Field("#2563eb", description="Color for team UI representation")
    settings: Optional[Dict[str, Any]] = Field(None, description="Team settings and configuration")

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    team_type: Optional[str] = Field(None, description="Updated team type")
    color: Optional[str] = Field(None, description="Updated color")
    status: Optional[str] = Field(None, description="Updated status")
    settings: Optional[Dict[str, Any]] = Field(None, description="Updated settings")

class TeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str
    team_type: str
    color: str
    status: str
    settings: Dict[str, Any]
    created_at: str
    updated_at: str
    member_count: int = 0
    agent_count: int = 0
    task_count: int = 0
    completed_task_count: int = 0
    active_task_count: int = 0
    goal_count: int = 0
    milestone_count: int = 0
    efficiency_rate: float = 0.0
    avg_response_time: str = "0s"

class TeamFilters(BaseModel):
    status: Optional[List[str]] = Field(None, description="Filter by status")
    team_type: Optional[List[str]] = Field(None, description="Filter by team type")
    search: Optional[str] = Field(None, description="Search in name and description")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")

class PaginatedTeamsResponse(BaseModel):
    teams: List[TeamResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: Optional[TeamFilters]

class AddTeamMemberRequest(BaseModel):
    agent_id: str = Field(..., description="ID of the agent to add to the team")

# Create router
router = APIRouter(prefix="/teams", tags=["teams"])

def team_to_response(db: Session, team: Team) -> TeamResponse:
    """Convert database team to API response format with related data."""
    # Calculate team statistics
    agent_count = db.query(Agent).filter(Agent.team_id == team.id).count()

    # Task statistics
    total_tasks = db.query(Task).filter(Task.team_id == team.id).count()
    completed_tasks = db.query(Task).filter(
        and_(Task.team_id == team.id, Task.status == "completed")
    ).count()
    active_tasks = db.query(Task).filter(
        and_(Task.team_id == team.id, Task.status == "in_progress")
    ).count()

    # Efficiency rate calculation
    efficiency_rate = 0.0
    if total_tasks > 0:
        efficiency_rate = round((completed_tasks / total_tasks) * 100, 2)

    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id or "",
        name=team.name,
        description=team.description or "",
        team_type=team.team_type or "development",
        color=team.color or "#2563eb",
        status=team.status,
        settings=json.loads(team.settings) if team.settings else {},
        created_at=team.created_at.isoformat(),
        updated_at=team.updated_at.isoformat(),
        member_count=agent_count,  # Alias for backward compatibility
        agent_count=agent_count,
        task_count=total_tasks,
        completed_task_count=completed_tasks,
        active_task_count=active_tasks,
        goal_count=0,  # TODO: Implement when goals are available
        milestone_count=0,  # TODO: Implement when milestones are available
        efficiency_rate=efficiency_rate,
        avg_response_time="0s"  # TODO: Implement response time tracking
    )

@router.post("/", response_model=TeamResponse)
async def create_team(
    org_id: str,
    team: TeamCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new team for an organization.

    Validates organization exists and handles team creation.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Create team
    db_team = Team(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        name=team.name,
        description=team.description,
        team_type=team.team_type or "development",
        color=team.color or "#2563eb",
        status="active",
        settings=json.dumps(team.settings) if team.settings else "{}"
    )

    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    return team_to_response(db, db_team)

@router.get("/", response_model=PaginatedTeamsResponse)
async def list_teams(
    org_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    team_type: Optional[List[str]] = Query(None, description="Filter by team type"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    List teams for an organization with filtering, search, and pagination.

    Supports comprehensive filtering by status, type, and search.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Build query
    query = db.query(Team).filter(Team.organization_id == org_id)

    # Apply filters
    if status:
        query = query.filter(Team.status.in_(status))

    if team_type:
        query = query.filter(Team.team_type.in_(team_type))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Team.name.ilike(search_filter),
                Team.description.ilike(search_filter)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Team, sort_by, Team.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    teams = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    team_responses = [team_to_response(db, t) for t in teams]

    return PaginatedTeamsResponse(
        teams=team_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        filters=TeamFilters(
            status=status,
            team_type=team_type,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        ) if any([status, team_type, search]) else None
    )

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific team by ID.

    Includes related agents and performance data.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get team with organization validation
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team_to_response(db, team)

@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    org_id: str,
    team_id: str,
    team_update: TeamUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing team.

    Handles team configuration updates and settings.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get team
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Update fields
    update_data = team_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "settings":
            setattr(team, field, json.dumps(value) if value else "{}")
        else:
            setattr(team, field, value)

    team.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(team)

    return team_to_response(db, team)

@router.delete("/{team_id}")
async def delete_team(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a team.

    Removes the team and handles related cleanup.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get team
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if team has agents
    agent_count = db.query(Agent).filter(Agent.team_id == team_id).count()
    if agent_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete team with {agent_count} agents. Please reassign agents first."
        )

    db.delete(team)
    db.commit()

    return {"message": "Team deleted successfully"}

@router.post("/{team_id}/members", response_model=dict)
async def add_team_member(
    org_id: str,
    team_id: str,
    member_request: AddTeamMemberRequest,
    db: Session = Depends(get_db)
):
    """
    Add an agent to a team.

    Validates team and agent relationships.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Validate agent exists
    agent = db.query(Agent).filter(Agent.id == member_request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if agent is already in a team
    if agent.team_id:
        raise HTTPException(
            status_code=400,
            detail="Agent is already assigned to a team. Please remove from current team first."
        )

    # Add agent to team
    agent.team_id = team_id
    agent.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Agent added to team successfully", "agent_id": agent.id, "team_id": team_id}

@router.delete("/{team_id}/members/{agent_id}")
async def remove_team_member(
    org_id: str,
    team_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove an agent from a team.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Validate agent exists and is in the team
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.team_id == team_id)
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found in this team")

    # Remove agent from team
    agent.team_id = None
    agent.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Agent removed from team successfully", "agent_id": agent_id, "team_id": team_id}

@router.get("/{team_id}/members", response_model=List[dict])
async def get_team_members(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all members of a team with their details.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get team agents
    agents = db.query(Agent).filter(Agent.team_id == team_id).all()

    # Convert to response format
    members = []
    for agent in agents:
        # Calculate task statistics
        total_tasks = db.query(Task).filter(Task.agent_id == agent.id).count()
        completed_tasks = db.query(Task).filter(
            and_(Task.agent_id == agent.id, Task.status == "completed")
        ).count()
        active_tasks = db.query(Task).filter(
            and_(Task.agent_id == agent.id, Task.status == "in_progress")
        ).count()

        efficiency_rate = 0.0
        if total_tasks > 0:
            efficiency_rate = round((completed_tasks / total_tasks) * 100, 2)

        members.append({
            "id": agent.id,
            "name": agent.name,
            "role": agent.role or "",
            "type": agent.type,
            "status": agent.status,
            "task_count": total_tasks,
            "completed_task_count": completed_tasks,
            "active_task_count": active_tasks,
            "efficiency_rate": efficiency_rate,
            "joined_date": agent.created_at.isoformat(),
            "performance": {
                "tasksCompleted": completed_tasks,
                "tasksActive": active_tasks,
                "efficiency": f"{efficiency_rate}%"
            }
        })

    return members

@router.get("/{team_id}/stats", response_model=dict)
async def get_team_stats(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive statistics for a team.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Calculate statistics
    agent_count = db.query(Agent).filter(Agent.team_id == team_id).count()

    # Task statistics
    total_tasks = db.query(Task).filter(Task.team_id == team_id).count()
    completed_tasks = db.query(Task).filter(
        and_(Task.team_id == team_id, Task.status == "completed")
    ).count()
    active_tasks = db.query(Task).filter(
        and_(Task.team_id == team_id, Task.status == "in_progress")
    ).count()
    pending_tasks = db.query(Task).filter(
        and_(Task.team_id == team_id, Task.status == "pending")
    ).count()

    # Agent performance
    agents = db.query(Agent).filter(Agent.team_id == team_id).all()
    total_agent_tasks = 0
    total_completed_agent_tasks = 0

    for agent in agents:
        agent_tasks = db.query(Task).filter(Task.agent_id == agent.id).count()
        agent_completed_tasks = db.query(Task).filter(
            and_(Task.agent_id == agent.id, Task.status == "completed")
        ).count()
        total_agent_tasks += agent_tasks
        total_completed_agent_tasks += agent_completed_tasks

    team_efficiency = 0.0
    if total_agent_tasks > 0:
        team_efficiency = round((total_completed_agent_tasks / total_agent_tasks) * 100, 2)

    return {
        "team_id": team_id,
        "team_name": team.name,
        "agent_count": agent_count,
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "active": active_tasks,
            "pending": pending_tasks,
            "completion_rate": round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
        },
        "performance": {
            "efficiency_rate": team_efficiency,
            "avg_tasks_per_agent": round(total_tasks / agent_count, 2) if agent_count > 0 else 0,
            "avg_completed_per_agent": round(total_completed_agent_tasks / agent_count, 2) if agent_count > 0 else 0
        },
        "created_at": team.created_at.isoformat(),
        "last_updated": team.updated_at.isoformat()
    }

# Legacy endpoints for backward compatibility
@router.get("/legacy/all", response_model=List[TeamResponse])
def get_all_teams_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint for getting all teams (no auth required)."""
    teams = db.query(Team).all()
    return [team_to_response(db, t) for t in teams]

# Knowledge/Document endpoints for teams
@router.get("/{team_id}/knowledge", response_model=List[dict])
async def get_team_knowledge(org_id: str, team_id: str, db: Session = Depends(get_db)):
    """
    Get knowledge documents for a team.

    Validates organization and team access.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    logger.info(f"GET /organizations/{org_id}/teams/{team_id}/knowledge")

    # For now, return mock data since we don't have a knowledge table
    mock_docs = [
        {
            "id": "doc1",
            "title": "Team Guidelines",
            "filename": "guidelines.pdf",
            "type": "document",
            "mime_type": "application/pdf",
            "size": 1024000,
            "status": "active",
            "upload_date": "2024-01-15T10:00:00Z",
            "last_modified": "2024-01-15T10:00:00Z",
            "content_preview": "This document contains team guidelines...",
            "tags": ["guidelines", "team"],
            "team_id": team_id,
            "word_count": 1200,
            "extracted_text": "This document contains team guidelines and best practices..."
        },
        {
            "id": "doc2",
            "title": "Project Documentation",
            "filename": "project-docs.md",
            "type": "document",
            "mime_type": "text/markdown",
            "size": 512000,
            "status": "active",
            "upload_date": "2024-01-20T14:30:00Z",
            "last_modified": "2024-01-20T14:30:00Z",
            "content_preview": "# Project Documentation\n\nThis is the main project documentation...",
            "tags": ["documentation", "project"],
            "team_id": team_id,
            "word_count": 800,
            "extracted_text": "# Project Documentation\n\nThis is the main project documentation..."
        }
    ]

    return mock_docs

@router.get("/{team_id}/knowledge/{doc_id}/content", response_model=dict)
async def get_team_knowledge_content(org_id: str, team_id: str, doc_id: str, db: Session = Depends(get_db)):
    """
    Get content of a specific knowledge document.

    Validates organization and team access.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team exists and belongs to organization
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    logger.info(f"GET /organizations/{org_id}/teams/{team_id}/knowledge/{doc_id}/content")

    # Mock content based on document ID
    mock_content = {
        "doc1": {
            "content": "This document contains team guidelines and best practices for working together effectively. Please review these guidelines regularly to ensure smooth collaboration.",
            "type": "document",
            "filename": "guidelines.pdf"
        },
        "doc2": {
            "content": "# Project Documentation\n\nThis is the main project documentation for the team. It contains all the important information about the project structure, requirements, and procedures.",
            "type": "document",
            "filename": "project-docs.md"
        }
    }

    if doc_id not in mock_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return mock_content[doc_id]


