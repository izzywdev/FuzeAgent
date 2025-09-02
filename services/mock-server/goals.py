"""
Goals API router for FuzeAgent mock server.

Provides comprehensive CRUD operations for goals with:
- Organization-scoped goals
- Pagination, search, and filtering
- Status and priority management
- Progress tracking
- Team assignments
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

from database import get_db, Goal, Organization, Team
from pydantic import BaseModel, Field

# Pydantic models for request/response
class GoalCreate(BaseModel):
    title: str = Field(..., description="Title of the goal")
    description: str = Field(..., description="Detailed description of the goal")
    priority: Optional[str] = Field("medium", description="Priority: low, medium, high, critical")
    status: Optional[str] = Field("planning", description="Status: planning, active, completed, on_hold")
    target_completion_date: Optional[str] = Field(None, description="Target completion date")
    assigned_teams: Optional[List[str]] = Field([], description="List of assigned team IDs")

class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title")
    description: Optional[str] = Field(None, description="Updated description")
    priority: Optional[str] = Field(None, description="Updated priority")
    status: Optional[str] = Field(None, description="Updated status")
    target_completion_date: Optional[str] = Field(None, description="Updated target date")
    assigned_teams: Optional[List[str]] = Field(None, description="Updated team assignments")
    progress_percentage: Optional[int] = Field(None, description="Updated progress percentage")

class GoalResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    priority: str
    status: str
    target_completion_date: str
    progress_percentage: int
    assigned_teams: List[str]
    created_at: str
    updated_at: str
    team_count: int = 0
    milestone_count: int = 0
    completed_milestone_count: int = 0

class GoalFilters(BaseModel):
    status: Optional[List[str]] = Field(None, description="Filter by status")
    priority: Optional[List[str]] = Field(None, description="Filter by priority")
    assigned_team: Optional[str] = Field(None, description="Filter by assigned team")
    date_range: Optional[Dict[str, str]] = Field(None, description="Filter by date range")
    search: Optional[str] = Field(None, description="Search in title and description")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")

class PaginatedGoalsResponse(BaseModel):
    goals: List[GoalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: Optional[GoalFilters]

# Create router
router = APIRouter(prefix="/organizations/{org_id}/goals", tags=["goals"])

def calculate_goal_progress(db: Session, goal_id: str) -> tuple[int, int, int]:
    """Calculate milestone counts and progress for a goal."""
    from database import Milestone

    milestones = db.query(Milestone).filter(Milestone.goal_id == goal_id).all()
    total_milestones = len(milestones)
    completed_milestones = len([m for m in milestones if m.status == "completed"])

    # Calculate progress based on milestone completion
    if total_milestones == 0:
        progress = 0
    else:
        progress = int((completed_milestones / total_milestones) * 100)

    return total_milestones, completed_milestones, progress

def goal_to_response(db: Session, goal: Goal) -> GoalResponse:
    """Convert database goal to API response format."""
    milestone_count, completed_milestone_count, calculated_progress = calculate_goal_progress(db, goal.id)

    # Use calculated progress or stored progress (whichever is higher)
    progress_percentage = max(goal.progress_percentage or 0, calculated_progress)

    return GoalResponse(
        id=goal.id,
        organization_id=goal.organization_id,
        title=goal.title,
        description=goal.description or "",
        priority=goal.priority,
        status=goal.status,
        target_completion_date=goal.target_date.isoformat() if goal.target_date else "",
        progress_percentage=progress_percentage,
        assigned_teams=[],  # Would need a teams relationship table
        created_at=goal.created_at.isoformat(),
        updated_at=goal.updated_at.isoformat(),
        team_count=0,  # Would need team assignment tracking
        milestone_count=milestone_count,
        completed_milestone_count=completed_milestone_count
    )

@router.post("/", response_model=GoalResponse)
async def create_goal(
    org_id: str,
    goal: GoalCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new goal for an organization.

    - Validates organization exists
    - Sets default values for optional fields
    - Initializes progress tracking
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Create goal
    db_goal = Goal(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        title=goal.title,
        description=goal.description,
        priority=goal.priority or "medium",
        status=goal.status or "planning",
        target_date=datetime.fromisoformat(goal.target_completion_date.replace('Z', '+00:00')) if goal.target_completion_date else None,
        progress_percentage=0
    )

    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)

    return goal_to_response(db, db_goal)

@router.get("/", response_model=PaginatedGoalsResponse)
async def list_goals(
    org_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    priority: Optional[List[str]] = Query(None, description="Filter by priority"),
    assigned_team: Optional[str] = Query(None, description="Filter by assigned team"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    date_from: Optional[str] = Query(None, description="Filter by target date from"),
    date_to: Optional[str] = Query(None, description="Filter by target date to"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    List goals for an organization with filtering, search, and pagination.

    Supports:
    - Filtering by status, priority, assigned teams
    - Text search in title and description
    - Date range filtering
    - Sorting by multiple fields
    - Pagination with configurable page size
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Build query
    query = db.query(Goal).filter(Goal.organization_id == org_id)

    # Apply filters
    if status:
        query = query.filter(Goal.status.in_(status))

    if priority:
        query = query.filter(Goal.priority.in_(priority))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Goal.title.ilike(search_filter),
                Goal.description.ilike(search_filter)
            )
        )

    if date_from or date_to:
        if date_from:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Goal.target_date >= from_date)
        if date_to:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Goal.target_date <= to_date)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Goal, sort_by, Goal.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    goals = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to response format
    goal_responses = [goal_to_response(db, g) for g in goals]

    return PaginatedGoalsResponse(
        goals=goal_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        filters=GoalFilters(
            status=status,
            priority=priority,
            assigned_team=assigned_team,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            date_range={
                "from": date_from,
                "to": date_to
            } if date_from or date_to else None
        ) if any([status, priority, assigned_team, search, date_from, date_to]) else None
    )

@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    org_id: str,
    goal_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific goal by ID.

    Includes calculated progress and milestone statistics.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    goal = db.query(Goal).filter(
        and_(Goal.id == goal_id, Goal.organization_id == org_id)
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return goal_to_response(db, goal)

@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    org_id: str,
    goal_id: str,
    goal_update: GoalUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing goal.

    Supports partial updates and automatic progress recalculation.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    goal = db.query(Goal).filter(
        and_(Goal.id == goal_id, Goal.organization_id == org_id)
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Update fields
    update_data = goal_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "target_completion_date" and value:
            setattr(goal, "target_date", datetime.fromisoformat(value.replace('Z', '+00:00')))
        else:
            setattr(goal, field, value)

    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)

    return goal_to_response(db, goal)

@router.delete("/{goal_id}")
async def delete_goal(
    org_id: str,
    goal_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a goal.

    This will also delete all associated milestones due to cascade delete.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    goal = db.query(Goal).filter(
        and_(Goal.id == goal_id, Goal.organization_id == org_id)
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(goal)
    db.commit()

    return {"message": "Goal deleted successfully"}

@router.get("/{goal_id}/statistics")
async def get_goal_statistics(
    org_id: str,
    goal_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a goal.

    Includes milestone progress, task completion rates, and timeline information.
    """
    # Validate organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    goal = db.query(Goal).filter(
        and_(Goal.id == goal_id, Goal.organization_id == org_id)
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Calculate statistics
    from database import Milestone, Task

    milestones = db.query(Milestone).filter(Milestone.goal_id == goal_id).all()
    milestone_count = len(milestones)
    completed_milestones = len([m for m in milestones if m.status == "completed"])
    in_progress_milestones = len([m for m in milestones if m.status == "in_progress"])

    # Task statistics
    milestone_ids = [m.id for m in milestones]
    tasks = db.query(Task).filter(Task.milestone_id.in_(milestone_ids)).all() if milestone_ids else []
    task_count = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "completed"])

    return {
        "goal_id": goal_id,
        "milestones": {
            "total": milestone_count,
            "completed": completed_milestones,
            "in_progress": in_progress_milestones,
            "completion_rate": (completed_milestones / milestone_count * 100) if milestone_count > 0 else 0
        },
        "tasks": {
            "total": task_count,
            "completed": completed_tasks,
            "completion_rate": (completed_tasks / task_count * 100) if task_count > 0 else 0
        },
        "progress_percentage": goal.progress_percentage or 0,
        "days_remaining": None,  # Would calculate based on target_date
        "created_at": goal.created_at.isoformat(),
        "last_updated": goal.updated_at.isoformat()
    }
