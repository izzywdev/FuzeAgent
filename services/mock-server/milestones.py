"""
Milestones API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for milestones with:
- Many-to-one relationship with goals
- One-to-many relationship with tasks
- Search and filtering capabilities
- Pagination support
- Full relationship management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

from database import get_db, Milestone, Goal, Task
from pydantic import BaseModel, Field

# Pydantic models for request/response
class MilestoneCreate(BaseModel):
    goal_id: str = Field(..., description="ID of the goal this milestone belongs to")
    title: str = Field(..., description="Title of the milestone")
    description: str = Field(..., description="Detailed description of the milestone")
    priority: Optional[str] = Field("medium", description="Priority level: low, medium, high, critical")
    target_date: str = Field(..., description="Target completion date in ISO format")

class MilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the milestone")
    description: Optional[str] = Field(None, description="Updated description")
    status: Optional[str] = Field(None, description="Status: not_started, in_progress, completed, blocked, cancelled")
    priority: Optional[str] = Field(None, description="Priority level")
    progress_percentage: Optional[int] = Field(None, description="Progress percentage (0-100)")
    target_date: Optional[str] = Field(None, description="Updated target date")

class MilestoneResponse(BaseModel):
    id: str
    goal_id: str
    title: str
    description: str
    status: str
    priority: str
    progress_percentage: int
    target_date: str
    completed_at: Optional[str]
    created_at: str
    updated_at: str
    task_count: int = 0
    completed_task_count: int = 0

class MilestoneFilters(BaseModel):
    status: Optional[List[str]] = Field(None, description="Filter by milestone status")
    priority: Optional[List[str]] = Field(None, description="Filter by priority level")
    goal_id: Optional[str] = Field(None, description="Filter by specific goal")
    search: Optional[str] = Field(None, description="Search in title and description")
    sort_by: Optional[str] = Field("created_at", description="Sort field: created_at, target_date, priority, progress_percentage, title")
    sort_order: Optional[str] = Field("desc", description="Sort order: asc, desc")

class PaginatedMilestonesResponse(BaseModel):
    milestones: List[MilestoneResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: Optional[MilestoneFilters]

# Create router
router = APIRouter(prefix="/milestones", tags=["milestones"])

def calculate_milestone_progress(db: Session, milestone_id: str) -> tuple[int, int]:
    """Calculate task count and completed task count for a milestone."""
    tasks = db.query(Task).filter(Task.milestone_id == milestone_id).all()
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "completed"])
    return total_tasks, completed_tasks

def milestone_to_response(db: Session, milestone: Milestone) -> MilestoneResponse:
    """Convert database milestone to API response format."""
    task_count, completed_task_count = calculate_milestone_progress(db, milestone.id)

    return MilestoneResponse(
        id=milestone.id,
        goal_id=milestone.goal_id,
        title=milestone.title,
        description=milestone.description or "",
        status=milestone.status,
        priority=milestone.priority,
        progress_percentage=milestone.progress_percentage,
        target_date=milestone.target_date.isoformat() if milestone.target_date else "",
        completed_at=milestone.completed_at.isoformat() if milestone.completed_at else None,
        created_at=milestone.created_at.isoformat(),
        updated_at=milestone.updated_at.isoformat(),
        task_count=task_count,
        completed_task_count=completed_task_count
    )

@router.post("/", response_model=MilestoneResponse)
async def create_milestone(
    milestone: MilestoneCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new milestone.

    - Validates that the goal exists
    - Sets default values for optional fields
    - Calculates initial progress based on existing tasks
    """
    # Validate goal exists
    goal = db.query(Goal).filter(Goal.id == milestone.goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Create milestone
    db_milestone = Milestone(
        id=str(uuid.uuid4()),
        goal_id=milestone.goal_id,
        title=milestone.title,
        description=milestone.description,
        priority=milestone.priority or "medium",
        target_date=datetime.fromisoformat(milestone.target_date.replace('Z', '+00:00'))
    )

    db.add(db_milestone)
    db.commit()
    db.refresh(db_milestone)

    return milestone_to_response(db, db_milestone)

@router.get("/", response_model=PaginatedMilestonesResponse)
async def list_milestones(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    goal_id: Optional[str] = Query(None, description="Filter by goal ID"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    priority: Optional[List[str]] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    List milestones with filtering, search, and pagination.

    Supports:
    - Filtering by goal, status, priority
    - Text search in title and description
    - Sorting by multiple fields
    - Pagination with configurable page size
    """
    # Build query
    query = db.query(Milestone)

    # Apply filters
    if goal_id:
        query = query.filter(Milestone.goal_id == goal_id)

    if status:
        query = query.filter(Milestone.status.in_(status))

    if priority:
        query = query.filter(Milestone.priority.in_(priority))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Milestone.title.ilike(search_filter),
                Milestone.description.ilike(search_filter)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Milestone, sort_by, Milestone.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    milestones = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    milestone_responses = [milestone_to_response(db, m) for m in milestones]

    return PaginatedMilestonesResponse(
        milestones=milestone_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        filters=MilestoneFilters(
            status=status,
            priority=priority,
            goal_id=goal_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        ) if any([status, priority, goal_id, search]) else None
    )

@router.get("/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific milestone by ID.

    Includes calculated task counts and progress information.
    """
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    return milestone_to_response(db, milestone)

@router.put("/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: str,
    milestone_update: MilestoneUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing milestone.

    Supports partial updates and automatically updates progress
    when status changes to completed.
    """
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Update fields
    update_data = milestone_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "target_date" and value:
            setattr(milestone, field, datetime.fromisoformat(value.replace('Z', '+00:00')))
        elif field == "status" and value == "completed" and not milestone.completed_at:
            setattr(milestone, "completed_at", datetime.utcnow())
        else:
            setattr(milestone, field, value)

    milestone.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(milestone)

    return milestone_to_response(db, milestone)

@router.delete("/{milestone_id}")
async def delete_milestone(
    milestone_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a milestone.

    This will also delete all associated tasks due to cascade delete.
    """
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.delete(milestone)
    db.commit()

    return {"message": "Milestone deleted successfully"}

@router.get("/{milestone_id}/tasks")
async def get_milestone_tasks(
    milestone_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by task status"),
    db: Session = Depends(get_db)
):
    """
    Get all tasks associated with a milestone.

    Supports pagination and status filtering.
    """
    # Verify milestone exists
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Build tasks query
    query = db.query(Task).filter(Task.milestone_id == milestone_id)

    if status:
        query = query.filter(Task.status.in_(status))

    # Get total count
    total = query.count()

    # Apply pagination and sorting
    tasks = query.order_by(desc(Task.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    # Convert to dict format
    task_list = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "team_id": task.team_id,
            "agent_id": task.agent_id,
            "milestone_id": task.milestone_id,
            "result": task.result,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
        task_list.append(task_dict)

    return {
        "tasks": task_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.post("/{milestone_id}/tasks/{task_id}")
async def assign_task_to_milestone(
    milestone_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Assign an existing task to a milestone.

    This creates a relationship between the task and milestone.
    """
    # Verify both exist
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Assign task to milestone
    task.milestone_id = milestone_id
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Task assigned to milestone successfully"}

@router.delete("/{milestone_id}/tasks/{task_id}")
async def remove_task_from_milestone(
    milestone_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove a task from a milestone.

    This breaks the relationship between the task and milestone.
    """
    # Verify both exist and are related
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.milestone_id == milestone_id)
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in milestone")

    # Remove task from milestone
    task.milestone_id = None
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Task removed from milestone successfully"}
