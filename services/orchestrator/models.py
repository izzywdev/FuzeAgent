from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Enums
class TeamType(str, Enum):
    DEVELOPMENT = "development"
    QA = "qa"
    DESIGN = "design"
    MANAGEMENT = "management"
    GENERAL = "general"

class AgentType(str, Enum):
    EXECUTIVE = "executive"
    DEVELOPER = "developer"
    QA = "qa"
    DESIGNER = "designer"
    SPECIALIZED = "specialized"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    ERROR = "error"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Organization Models
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Organization(OrganizationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Team Models
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    team_type: TeamType = TeamType.GENERAL
    settings: Dict[str, Any] = Field(default_factory=dict)

class TeamCreate(TeamBase):
    organization_id: str

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    team_type: Optional[TeamType] = None
    settings: Optional[Dict[str, Any]] = None

class Team(TeamBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Agent Models
class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    type: AgentType
    config: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[str] = None

class AgentCreate(AgentBase):
    team_id: str

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[AgentType] = None
    status: Optional[AgentStatus] = None
    config: Optional[Dict[str, Any]] = None
    team_id: Optional[str] = None
    template_id: Optional[str] = None

class Agent(AgentBase):
    id: str
    team_id: str
    status: AgentStatus = AgentStatus.INACTIVE
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Extended models with relationships
class AgentWithTeam(Agent):
    team_name: str
    organization_id: str
    organization_name: str

class TeamWithAgents(Team):
    agents: List[Agent] = []
    agent_count: int = 0

class OrganizationWithTeams(Organization):
    teams: List[TeamWithAgents] = []
    team_count: int = 0
    agent_count: int = 0

# Task Models
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)

class TaskCreate(TaskBase):
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class Task(TaskBase):
    id: str
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskWithAgent(Task):
    assigned_agent_name: Optional[str] = None
    created_by_agent_name: Optional[str] = None

# Template Models (from existing agent_templates.py)
class CreateAgentFromTemplate(BaseModel):
    template_id: str
    overrides: Dict[str, Any] = Field(default_factory=dict)

class CreateCustomAgent(BaseModel):
    name: str
    role: str
    type: str
    config: Dict[str, Any]

# Response Models
class OrganizationResponse(BaseModel):
    organization: Organization
    message: str = "Organization retrieved successfully"

class TeamResponse(BaseModel):
    team: Team
    message: str = "Team retrieved successfully"

class AgentResponse(BaseModel):
    agent: Agent
    message: str = "Agent retrieved successfully"

class ListResponse(BaseModel):
    items: List[Any]
    total: int
    message: str = "Items retrieved successfully"

# Statistics Models
class OrganizationStats(BaseModel):
    total_teams: int
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int

class TeamStats(BaseModel):
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int