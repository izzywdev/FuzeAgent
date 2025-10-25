"""
FastAPI application for FuzeAgent Backend Service
Provides CRUD operations with pagination, search, and filtering for all tables
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import math

from database import SessionLocal, get_db, engine
import models

app = FastAPI(
    title="FuzeAgent Backend API",
    description="Complete CRUD API for FuzeAgent database",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int

class MessageResponse(BaseModel):
    message: str

# Utility functions
def paginate(query, page: int, page_size: int):
    """Apply pagination to a query"""
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return {
        "items": [item.__dict__ for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def to_dict(item):
    """Convert SQLAlchemy model to dictionary"""
    if item is None:
        return None
    result = {}
    for key, value in item.__dict__.items():
        if not key.startswith('_'):
            if hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            else:
                result[key] = value
    return result

# Generic CRUD endpoint creator
def create_crud_endpoints(
    model_class: type,
    prefix: str,
    search_fields: list,
    filter_fields: list
):
    """Create CRUD endpoints for a model"""
    
    @app.get(f"/api/{prefix}", response_model=PaginatedResponse, tags=[prefix])
    def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        search: Optional[str] = None,
        db: Session = Depends(get_db)
    ):
        """List all items with pagination and search"""
        query = db.query(model_class)
        
        # Apply search
        if search and search_fields:
            search_filters = [
                getattr(model_class, field).ilike(f"%{search}%")
                for field in search_fields
                if hasattr(model_class, field)
            ]
            if search_filters:
                query = query.filter(or_(*search_filters))
        
        return paginate(query, page, page_size)
    
    @app.get(f"/api/{prefix}/{{item_id}}", tags=[prefix])
    def get_item(item_id: str, db: Session = Depends(get_db)):
        """Get a single item by ID"""
        item = db.query(model_class).get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return to_dict(item)
    
    @app.post(f"/api/{prefix}", tags=[prefix])
    def create_item(data: dict, db: Session = Depends(get_db)):
        """Create a new item"""
        try:
            # Filter out None values and convert to model
            clean_data = {k: v for k, v in data.items() if v is not None}
            item = model_class(**clean_data)
            db.add(item)
            db.commit()
            db.refresh(item)
            return to_dict(item)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.put(f"/api/{prefix}/{{item_id}}", tags=[prefix])
    def update_item(item_id: str, data: dict, db: Session = Depends(get_db)):
        """Update an item"""
        item = db.query(model_class).get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        
        try:
            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            db.commit()
            db.refresh(item)
            return to_dict(item)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.delete(f"/api/{prefix}/{{item_id}}", response_model=MessageResponse, tags=[prefix])
    def delete_item(item_id: str, db: Session = Depends(get_db)):
        """Delete an item"""
        item = db.query(model_class).get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")
        
        try:
            db.delete(item)
            db.commit()
            return {"message": "Item deleted successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

# Create endpoints for each model
create_crud_endpoints(
    models.Entity,
    "entities",
    search_fields=["kind"],
    filter_fields=["kind"]
)

create_crud_endpoints(
    models.Organization,
    "organizations",
    search_fields=["name", "description"],
    filter_fields=["name"]
)

create_crud_endpoints(
    models.Team,
    "teams",
    search_fields=["name", "description", "team_type"],
    filter_fields=["organization_id", "status", "team_lead"]
)

create_crud_endpoints(
    models.TeamLeadHistory,
    "team-lead-history",
    search_fields=["reason"],
    filter_fields=["team_id", "prev_lead_id", "new_lead_id"]
)

create_crud_endpoints(
    models.AgentTemplate,
    "agent-templates",
    search_fields=["template_name", "category", "description"],
    filter_fields=["category", "model"]
)

create_crud_endpoints(
    models.AgentTemplateEnvVar,
    "agent-template-env-vars",
    search_fields=["name", "value"],
    filter_fields=["template_id", "is_secret"]
)

create_crud_endpoints(
    models.Agent,
    "agents",
    search_fields=["name", "role", "type"],
    filter_fields=["team_id", "status", "template_id"]
)

create_crud_endpoints(
    models.AgentEnvVar,
    "agent-env-vars",
    search_fields=["name", "value"],
    filter_fields=["agent_id", "is_secret"]
)

create_crud_endpoints(
    models.Container,
    "containers",
    search_fields=["external_id", "provider", "docker_image"],
    filter_fields=["agent_id", "provider"]
)

create_crud_endpoints(
    models.OrgTool,
    "org-tools",
    search_fields=["key", "name", "description"],
    filter_fields=["org_id", "is_active"]
)

create_crud_endpoints(
    models.OrgToolParam,
    "org-tool-params",
    search_fields=["name", "param_type"],
    filter_fields=["tool_id", "required"]
)

create_crud_endpoints(
    models.TeamToolSetting,
    "team-tool-settings",
    search_fields=[],
    filter_fields=["team_id", "tool_id", "enabled"]
)

create_crud_endpoints(
    models.AgentToolSetting,
    "agent-tool-settings",
    search_fields=[],
    filter_fields=["agent_id", "tool_id", "enabled"]
)

create_crud_endpoints(
    models.Goal,
    "goals",
    search_fields=["title", "description"],
    filter_fields=["organization_id", "priority", "status"]
)

create_crud_endpoints(
    models.GoalAssignedTeam,
    "goal-assigned-teams",
    search_fields=[],
    filter_fields=["goal_id", "team_id"]
)

create_crud_endpoints(
    models.Milestone,
    "milestones",
    search_fields=["title", "status"],
    filter_fields=["goal_id", "status"]
)

create_crud_endpoints(
    models.Task,
    "tasks",
    search_fields=["title", "description", "progress_notes"],
    filter_fields=["team_id", "agent_id", "milestone_id", "status", "priority"]
)

create_crud_endpoints(
    models.TaskAssignment,
    "task-assignments",
    search_fields=[],
    filter_fields=["task_id", "agent_id", "inherited"]
)

create_crud_endpoints(
    models.Conversation,
    "conversations",
    search_fields=["title"],
    filter_fields=["owner_id", "status"]
)

create_crud_endpoints(
    models.ConversationMessage,
    "conversation-messages",
    search_fields=["content", "role"],
    filter_fields=["conversation_id", "role", "status"]
)

create_crud_endpoints(
    models.Knowledge,
    "knowledge",
    search_fields=["title", "filename", "content_preview", "extracted_text"],
    filter_fields=["owner_id", "type", "status"]
)

# Health check endpoint
@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Initialize database on startup
@app.on_event("startup")
def init_database():
    """Initialize database tables on startup"""
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
