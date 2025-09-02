"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# Organization models
class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    team_count: int = 0
    agent_count: int = 0

# Team models
class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    team_type: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_type: Optional[str] = None
    color: Optional[str] = None

class TeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    team_type: Optional[str] = None
    color: str = "#2563eb"
    status: str = "active"
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    members: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {}
    knowledgeBase: List[Dict[str, Any]] = []

# Agent models
class AgentCreate(BaseModel):
    team_id: str
    name: str
    role: Optional[str] = None
    type: Optional[str] = "developer"
    config: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class AgentResponse(BaseModel):
    id: str
    team_id: str
    name: str
    role: Optional[str] = None
    type: str = "developer"
    status: str = "active"
    config: Dict[str, Any] = {}
    template_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: Dict[str, int] = {"completed": 0, "running": 0, "pending": 0}
    lastActivity: datetime
    performance: Dict[str, Any] = {}
    joinedDate: datetime
    conversations: List[Dict[str, Any]] = []

# Task models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    priority: Optional[str] = "medium"
    team_id: Optional[str] = None
    agent_id: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# Tool models
class OrgToolCreate(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    default_config: Optional[Dict[str, Any]] = None

class OrgToolResponse(BaseModel):
    id: str
    org_id: str
    key: str
    name: str
    description: Optional[str] = None
    default_config: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

# Error models
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
