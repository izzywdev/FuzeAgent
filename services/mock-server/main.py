"""
FuzeAgent Mock Server - FastAPI Application
Complete CRUD API with PostgreSQL, SQLAlchemy, and Alembic
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import uvicorn

import crud, models, schemas, database
from database import get_db

# Create FastAPI app
app = FastAPI(
    title="FuzeAgent Mock Server",
    description="Complete CRUD API for FuzeAgent with PostgreSQL and SQLAlchemy",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "FuzeAgent Mock Server API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Organizations endpoints
@app.get("/organizations", response_model=schemas.PaginatedResponse)
async def get_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db)
):
    """Get all organizations with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    items, total = crud.organization.get_multi_with_teams(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/organizations/{organization_id}", response_model=schemas.OrganizationResponse)
async def get_organization(
    organization_id: UUID = Path(..., description="Organization ID"),
    db: Session = Depends(get_db)
):
    """Get a specific organization by ID"""
    organization = crud.organization.get(db=db, id=organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization

@app.post("/organizations", response_model=schemas.OrganizationResponse)
async def create_organization(
    organization: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    # Check if organization with same name already exists
    existing = crud.organization.get_by_name(db=db, name=organization.name)
    if existing:
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    
    return crud.organization.create(db=db, obj_in=organization)

@app.put("/organizations/{organization_id}", response_model=schemas.OrganizationResponse)
async def update_organization(
    organization_id: UUID = Path(..., description="Organization ID"),
    organization_update: schemas.OrganizationUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update an organization"""
    organization = crud.organization.get(db=db, id=organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return crud.organization.update(db=db, db_obj=organization, obj_in=organization_update)

@app.delete("/organizations/{organization_id}")
async def delete_organization(
    organization_id: UUID = Path(..., description="Organization ID"),
    db: Session = Depends(get_db)
):
    """Delete an organization"""
    organization = crud.organization.get(db=db, id=organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    crud.organization.remove(db=db, id=organization_id)
    return {"message": "Organization deleted successfully"}

# Teams endpoints
@app.get("/teams", response_model=schemas.PaginatedResponse)
async def get_teams(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db)
):
    """Get all teams with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if organization_id:
        filters["organization_id"] = organization_id
    
    items, total = crud.team.get_multi_with_agents(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/teams/{team_id}", response_model=schemas.TeamResponse)
async def get_team(
    team_id: UUID = Path(..., description="Team ID"),
    db: Session = Depends(get_db)
):
    """Get a specific team by ID"""
    team = crud.team.get(db=db, id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@app.post("/teams", response_model=schemas.TeamResponse)
async def create_team(
    team: schemas.TeamCreate,
    db: Session = Depends(get_db)
):
    """Create a new team"""
    # Verify organization exists
    organization = crud.organization.get(db=db, id=team.organization_id)
    if not organization:
        raise HTTPException(status_code=400, detail="Organization not found")
    
    return crud.team.create(db=db, obj_in=team)

@app.put("/teams/{team_id}", response_model=schemas.TeamResponse)
async def update_team(
    team_id: UUID = Path(..., description="Team ID"),
    team_update: schemas.TeamUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a team"""
    team = crud.team.get(db=db, id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return crud.team.update(db=db, db_obj=team, obj_in=team_update)

@app.delete("/teams/{team_id}")
async def delete_team(
    team_id: UUID = Path(..., description="Team ID"),
    db: Session = Depends(get_db)
):
    """Delete a team"""
    team = crud.team.get(db=db, id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    crud.team.remove(db=db, id=team_id)
    return {"message": "Team deleted successfully"}

# Agent Templates endpoints
@app.get("/agent-templates", response_model=schemas.PaginatedResponse)
async def get_agent_templates(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get all agent templates with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if category:
        filters["category"] = category
    
    items, total = crud.agent_template.get_multi_with_search(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/agent-templates/{template_id}", response_model=schemas.AgentTemplateResponse)
async def get_agent_template(
    template_id: str = Path(..., description="Template ID"),
    db: Session = Depends(get_db)
):
    """Get a specific agent template by ID"""
    template = crud.agent_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent template not found")
    return template

@app.post("/agent-templates", response_model=schemas.AgentTemplateResponse)
async def create_agent_template(
    template: schemas.AgentTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new agent template"""
    return crud.agent_template.create(db=db, obj_in=template)

@app.put("/agent-templates/{template_id}", response_model=schemas.AgentTemplateResponse)
async def update_agent_template(
    template_id: str = Path(..., description="Template ID"),
    template_update: schemas.AgentTemplateUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update an agent template"""
    template = crud.agent_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent template not found")
    
    return crud.agent_template.update(db=db, db_obj=template, obj_in=template_update)

@app.delete("/agent-templates/{template_id}")
async def delete_agent_template(
    template_id: str = Path(..., description="Template ID"),
    db: Session = Depends(get_db)
):
    """Delete an agent template"""
    template = crud.agent_template.get(db=db, id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Agent template not found")
    
    crud.agent_template.remove(db=db, id=template_id)
    return {"message": "Agent template deleted successfully"}

# Agents endpoints
@app.get("/agents", response_model=schemas.PaginatedResponse)
async def get_agents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all agents with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if team_id:
        filters["team_id"] = team_id
    if status:
        filters["status"] = status
    
    items, total = crud.agent.get_multi_with_search(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/agents/{agent_id}", response_model=schemas.AgentResponse)
async def get_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    db: Session = Depends(get_db)
):
    """Get a specific agent by ID"""
    agent = crud.agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.post("/agents", response_model=schemas.AgentResponse)
async def create_agent(
    agent: schemas.AgentCreate,
    db: Session = Depends(get_db)
):
    """Create a new agent"""
    # Verify team exists
    team = crud.team.get(db=db, id=agent.team_id)
    if not team:
        raise HTTPException(status_code=400, detail="Team not found")
    
    return crud.agent.create(db=db, obj_in=agent)

@app.put("/agents/{agent_id}", response_model=schemas.AgentResponse)
async def update_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    agent_update: schemas.AgentUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update an agent"""
    agent = crud.agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return crud.agent.update(db=db, db_obj=agent, obj_in=agent_update)

@app.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    db: Session = Depends(get_db)
):
    """Delete an agent"""
    agent = crud.agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    crud.agent.remove(db=db, id=agent_id)
    return {"message": "Agent deleted successfully"}

# Goals endpoints
@app.get("/goals", response_model=schemas.PaginatedResponse)
async def get_goals(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all goals with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if organization_id:
        filters["organization_id"] = organization_id
    if status:
        filters["status"] = status
    
    items, total = crud.goal.get_multi_with_search(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/goals/{goal_id}", response_model=schemas.GoalResponse)
async def get_goal(
    goal_id: UUID = Path(..., description="Goal ID"),
    db: Session = Depends(get_db)
):
    """Get a specific goal by ID"""
    goal = crud.goal.get(db=db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@app.post("/goals", response_model=schemas.GoalResponse)
async def create_goal(
    goal: schemas.GoalCreate,
    db: Session = Depends(get_db)
):
    """Create a new goal"""
    # Verify organization exists
    organization = crud.organization.get(db=db, id=goal.organization_id)
    if not organization:
        raise HTTPException(status_code=400, detail="Organization not found")
    
    return crud.goal.create(db=db, obj_in=goal)

@app.put("/goals/{goal_id}", response_model=schemas.GoalResponse)
async def update_goal(
    goal_id: UUID = Path(..., description="Goal ID"),
    goal_update: schemas.GoalUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a goal"""
    goal = crud.goal.get(db=db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return crud.goal.update(db=db, db_obj=goal, obj_in=goal_update)

@app.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: UUID = Path(..., description="Goal ID"),
    db: Session = Depends(get_db)
):
    """Delete a goal"""
    goal = crud.goal.get(db=db, id=goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    crud.goal.remove(db=db, id=goal_id)
    return {"message": "Goal deleted successfully"}

# Tasks endpoints
@app.get("/tasks", response_model=schemas.PaginatedResponse)
async def get_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all tasks with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if team_id:
        filters["team_id"] = team_id
    if agent_id:
        filters["agent_id"] = agent_id
    if status:
        filters["status"] = status
    
    items, total = crud.task.get_multi_with_search(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID"""
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/tasks", response_model=schemas.TaskResponse)
async def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db)
):
    """Create a new task"""
    # Verify team exists
    team = crud.team.get(db=db, id=task.team_id)
    if not team:
        raise HTTPException(status_code=400, detail="Team not found")
    
    return crud.task.create(db=db, obj_in=task)

@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse)
async def update_task(
    task_id: UUID = Path(..., description="Task ID"),
    task_update: schemas.TaskUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a task"""
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return crud.task.update(db=db, db_obj=task, obj_in=task_update)

@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID = Path(..., description="Task ID"),
    db: Session = Depends(get_db)
):
    """Delete a task"""
    task = crud.task.get(db=db, id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    crud.task.remove(db=db, id=task_id)
    return {"message": "Task deleted successfully"}

# Knowledge endpoints
@app.get("/knowledge", response_model=schemas.PaginatedResponse)
async def get_knowledge(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    q: Optional[str] = Query(None, description="Search query"),
    owner_id: Optional[UUID] = Query(None, description="Filter by owner ID"),
    type: Optional[str] = Query(None, description="Filter by type"),
    db: Session = Depends(get_db)
):
    """Get all knowledge items with pagination, sorting, and search"""
    skip = (page - 1) * size
    filters = {}
    
    if owner_id:
        filters["owner_id"] = owner_id
    if type:
        filters["type"] = type
    
    items, total = crud.knowledge.get_multi_with_search(
        db=db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=q
    )
    
    return crud.paginate_results(items, total, page, size)

@app.get("/knowledge/{knowledge_id}", response_model=schemas.KnowledgeResponse)
async def get_knowledge_item(
    knowledge_id: UUID = Path(..., description="Knowledge ID"),
    db: Session = Depends(get_db)
):
    """Get a specific knowledge item by ID"""
    knowledge = crud.knowledge.get(db=db, id=knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return knowledge

@app.post("/knowledge", response_model=schemas.KnowledgeResponse)
async def create_knowledge(
    knowledge: schemas.KnowledgeCreate,
    db: Session = Depends(get_db)
):
    """Create a new knowledge item"""
    return crud.knowledge.create(db=db, obj_in=knowledge)

@app.put("/knowledge/{knowledge_id}", response_model=schemas.KnowledgeResponse)
async def update_knowledge(
    knowledge_id: UUID = Path(..., description="Knowledge ID"),
    knowledge_update: schemas.KnowledgeUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a knowledge item"""
    knowledge = crud.knowledge.get(db=db, id=knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    return crud.knowledge.update(db=db, db_obj=knowledge, obj_in=knowledge_update)

@app.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: UUID = Path(..., description="Knowledge ID"),
    db: Session = Depends(get_db)
):
    """Delete a knowledge item"""
    knowledge = crud.knowledge.get(db=db, id=knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    
    crud.knowledge.remove(db=db, id=knowledge_id)
    return {"message": "Knowledge item deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
