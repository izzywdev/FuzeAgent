"""
Tasks API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for tasks with:
- Organization and team scoping
- Agent assignment and tracking
- Milestone relationship management
- Pagination, search, and filtering
- Status and priority management
- Task execution and result tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from database import get_db, Task, Organization, Team, Agent, Milestone
from pydantic import BaseModel, Field

# Pydantic models for request/response
class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    priority: Optional[str] = Field("medium", description="Priority: low, medium, high, critical")
    status: Optional[str] = Field("pending", description="Status: pending, in_progress, completed, failed")
    team_id: Optional[str] = Field(None, description="ID of assigned team")
    agent_id: Optional[str] = Field(None, description="ID of assigned agent")
    milestone_id: Optional[str] = Field(None, description="ID of related milestone")

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title")
    description: Optional[str] = Field(None, description="Updated description")
    priority: Optional[str] = Field(None, description="Updated priority")
    status: Optional[str] = Field(None, description="Updated status")
    team_id: Optional[str] = Field(None, description="Updated team assignment")
    agent_id: Optional[str] = Field(None, description="Updated agent assignment")
    milestone_id: Optional[str] = Field(None, description="Updated milestone relationship")
    result: Optional[str] = Field(None, description="Task execution result")

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    team_id: str
    agent_id: str
    milestone_id: str
    result: str
    created_at: str
    updated_at: str
    completed_at: str
    team_name: str = ""
    agent_name: str = ""
    milestone_title: str = ""

class TaskFilters(BaseModel):
    status: Optional[List[str]] = Field(None, description="Filter by status")
    priority: Optional[List[str]] = Field(None, description="Filter by priority")
    team_id: Optional[str] = Field(None, description="Filter by team")
    agent_id: Optional[str] = Field(None, description="Filter by agent")
    milestone_id: Optional[str] = Field(None, description="Filter by milestone")
    search: Optional[str] = Field(None, description="Search in title and description")
    date_from: Optional[str] = Field(None, description="Filter by creation date from")
    date_to: Optional[str] = Field(None, description="Filter by creation date to")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")

class PaginatedTasksResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: Optional[TaskFilters]

# Create router
router = APIRouter(prefix="/organizations/{org_id}/tasks", tags=["tasks"])

def task_to_response(db: Session, task: Task) -> TaskResponse:
    """Convert database task to API response format with related data."""
    # Get related entity names
    team_name = ""
    if task.team_id:
        team = db.query(Team).filter(Team.id == task.team_id).first()
        if team:
            team_name = team.name

    agent_name = ""
    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if agent:
            agent_name = agent.name

    milestone_title = ""
    if task.milestone_id:
        milestone = db.query(Milestone).filter(Milestone.id == task.milestone_id).first()
        if milestone:
            milestone_title = milestone.title

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description or "",
        priority=task.priority,
        status=task.status,
        team_id=task.team_id or "",
        agent_id=task.agent_id or "",
        milestone_id=task.milestone_id or "",
        result=task.result or "",
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else "",
        team_name=team_name,
        agent_name=agent_name,
        milestone_title=milestone_title
    )

@router.post("/", response_model=TaskResponse)
async def create_task(
    org_id: str,
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new task for an organization.

    Validates organization exists and handles milestone relationships.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Validate team if provided
    if task.team_id:
        team = db.query(Team).filter(
            and_(Team.id == task.team_id, Team.organization_id == org_id)
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    # Validate agent if provided
    if task.agent_id:
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

    # Validate milestone if provided
    if task.milestone_id:
        milestone = db.query(Milestone).filter(Milestone.id == task.milestone_id).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

    # Create task
    db_task = Task(
        id=str(uuid.uuid4()),
        title=task.title,
        description=task.description,
        priority=task.priority or "medium",
        status=task.status or "pending",
        team_id=task.team_id,
        agent_id=task.agent_id,
        milestone_id=task.milestone_id
    )

    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return task_to_response(db, db_task)

@router.get("/", response_model=PaginatedTasksResponse)
async def list_tasks(
    org_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    priority: Optional[List[str]] = Query(None, description="Filter by priority"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    milestone_id: Optional[str] = Query(None, description="Filter by milestone"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    date_from: Optional[str] = Query(None, description="Filter by creation date from"),
    date_to: Optional[str] = Query(None, description="Filter by creation date to"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    List tasks for an organization with filtering, search, and pagination.

    Supports comprehensive filtering by status, priority, assignments, and dates.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Build query
    query = db.query(Task).filter(Task.team_id.isnot(None))  # Only show tasks with team assignment

    # Join with teams to ensure organization scoping
    query = query.join(Team, Task.team_id == Team.id).filter(Team.organization_id == org_id)

    # Apply filters
    if status:
        query = query.filter(Task.status.in_(status))

    if priority:
        query = query.filter(Task.priority.in_(priority))

    if team_id:
        query = query.filter(Task.team_id == team_id)

    if agent_id:
        query = query.filter(Task.agent_id == agent_id)

    if milestone_id:
        query = query.filter(Task.milestone_id == milestone_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_filter),
                Task.description.ilike(search_filter)
            )
        )

    if date_from or date_to:
        if date_from:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Task.created_at >= from_date)
        if date_to:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Task.created_at <= to_date)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Task, sort_by, Task.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    task_responses = [task_to_response(db, t) for t in tasks]

    return PaginatedTasksResponse(
        tasks=task_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        filters=TaskFilters(
            status=status,
            priority=priority,
            team_id=team_id,
            agent_id=agent_id,
            milestone_id=milestone_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order
        ) if any([status, priority, team_id, agent_id, milestone_id, search, date_from, date_to]) else None
    )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    org_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific task by ID.

    Includes related team, agent, and milestone information.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get task with team relationship for organization validation
    task = db.query(Task).join(Team, Task.team_id == Team.id).filter(
        and_(
            Task.id == task_id,
            Team.organization_id == org_id
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_to_response(db, task)

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    org_id: str,
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing task.

    Handles status changes and completion tracking.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get task
    task = db.query(Task).join(Team, Task.team_id == Team.id).filter(
        and_(
            Task.id == task_id,
            Team.organization_id == org_id
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update fields
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value == "completed" and not task.completed_at:
            # Set completion timestamp when status changes to completed
            setattr(task, "completed_at", datetime.utcnow())
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    return task_to_response(db, task)

@router.delete("/{task_id}")
async def delete_task(
    org_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a task.

    Removes the task from the database.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get task
    task = db.query(Task).join(Team, Task.team_id == Team.id).filter(
        and_(
            Task.id == task_id,
            Team.organization_id == org_id
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/execute")
async def execute_task(
    org_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Execute a task.

    Updates task status to in_progress and simulates execution.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get task
    task = db.query(Task).join(Team, Task.team_id == Team.id).filter(
        and_(
            Task.id == task_id,
            Team.organization_id == org_id
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update status to in_progress
    task.status = "in_progress"
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Task execution started", "task_id": task_id}

@router.get("/teams/{team_id}", response_model=List[TaskResponse])
async def get_team_tasks(
    org_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all tasks for a specific team.
    """
    # Validate organization and team
    team = db.query(Team).filter(
        and_(Team.id == team_id, Team.organization_id == org_id)
    ).first()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    tasks = db.query(Task).filter(Task.team_id == team_id).all()
    return [task_to_response(db, t) for t in tasks]

@router.get("/agents/{agent_id}", response_model=List[TaskResponse])
async def get_agent_tasks(
    org_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all tasks assigned to a specific agent.
    """
    # Validate agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    tasks = db.query(Task).filter(Task.agent_id == agent_id).all()
    return [task_to_response(db, t) for t in tasks]

@router.get("/milestones/{milestone_id}", response_model=List[TaskResponse])
async def get_milestone_tasks(
    org_id: str,
    milestone_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all tasks for a specific milestone.
    """
    # Validate milestone exists
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    tasks = db.query(Task).filter(Task.milestone_id == milestone_id).all()
    return [task_to_response(db, t) for t in tasks]
