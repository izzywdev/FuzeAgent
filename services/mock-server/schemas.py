"""
Pydantic schemas for FuzeAgent Mock Server API
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums
class EntityKind(str, Enum):
    ORGANIZATION = "organization"
    TEAM = "team"
    AGENT = "agent"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"
    CLOSED_APPROVED = "closed_approved"

class TeamStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class ConversationStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

# Pagination
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Page size")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

class PaginatedOrganizationsResponse(BaseModel):
    items: List[OrganizationResponse]
    total: int
    page: int
    size: int
    pages: int

# Search and Filter
class SearchParams(BaseModel):
    q: Optional[str] = Field(None, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter parameters")

# Entity schemas
class EntityBase(BaseSchema):
    kind: EntityKind

class EntityResponse(EntityBase, TimestampMixin):
    id: UUID

# Organization schemas
class OrganizationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class OrganizationResponse(OrganizationBase, TimestampMixin):
    id: UUID

# Team schemas
class TeamBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    team_type: Optional[str] = None
    color: Optional[str] = None
    status: TeamStatus = TeamStatus.ACTIVE
    settings: Dict[str, Any] = Field(default_factory=dict)

class TeamCreate(TeamBase):
    organization_id: UUID

class TeamUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    team_type: Optional[str] = None
    color: Optional[str] = None
    status: Optional[TeamStatus] = None
    settings: Optional[Dict[str, Any]] = None
    team_lead: Optional[UUID] = None

class TeamResponse(TeamBase, TimestampMixin):
    id: UUID
    organization_id: UUID
    team_lead: Optional[UUID] = None

# Agent Template schemas
class AgentTemplateBase(BaseSchema):
    template_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    model: str = Field(..., min_length=1)
    temperature: float = Field(0.70, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    docker_image: Optional[str] = None
    concurrency_limit: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    locale: Optional[str] = None
    log_level: Optional[str] = None
    tags: Optional[List[str]] = None
    template_metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentTemplateCreate(AgentTemplateBase):
    id: str = Field(..., min_length=1, max_length=255)

class AgentTemplateUpdate(BaseSchema):
    template_name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = Field(None, min_length=1)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    docker_image: Optional[str] = None
    concurrency_limit: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    locale: Optional[str] = None
    log_level: Optional[str] = None
    tags: Optional[List[str]] = None
    template_metadata: Optional[Dict[str, Any]] = None

class AgentTemplateResponse(AgentTemplateBase, TimestampMixin):
    id: str

# Agent schemas
class AgentBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = None
    type: Optional[str] = None
    status: str = Field("active", pattern="^(active|idle|inactive)$")
    model: str = Field(..., min_length=1)
    temperature: float = Field(0.70, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    docker_image: Optional[str] = None
    concurrency_limit: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    locale: Optional[str] = None
    log_level: Optional[str] = None
    tags: Optional[List[str]] = None
    template_metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentCreate(AgentBase):
    team_id: UUID
    template_id: Optional[str] = None

class AgentUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|idle|inactive)$")
    model: Optional[str] = Field(None, min_length=1)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    stop_sequences: Optional[List[str]] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    docker_image: Optional[str] = None
    concurrency_limit: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    locale: Optional[str] = None
    log_level: Optional[str] = None
    tags: Optional[List[str]] = None
    template_metadata: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None

class AgentResponse(AgentBase, TimestampMixin):
    id: UUID
    team_id: UUID
    template_id: Optional[str] = None
    last_activity: Optional[datetime] = None
    joined_date: Optional[datetime] = None

# Goal schemas
class GoalBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    status: str = Field("planning", pattern="^(planning|active|completed|on_hold)$")
    target_completion_date: Optional[datetime] = None
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)

class GoalCreate(GoalBase):
    organization_id: UUID

class GoalUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, pattern="^(planning|active|completed|on_hold)$")
    target_completion_date: Optional[datetime] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)

class GoalResponse(GoalBase, TimestampMixin):
    id: UUID
    organization_id: UUID

# Milestone schemas
class MilestoneBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    status: str = Field("planned", pattern="^(planned|in_progress|completed|cancelled)$")
    due_date: Optional[datetime] = None

class MilestoneCreate(MilestoneBase):
    goal_id: UUID

class MilestoneUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern="^(planned|in_progress|completed|cancelled)$")
    due_date: Optional[datetime] = None

class MilestoneResponse(MilestoneBase, TimestampMixin):
    id: UUID
    goal_id: UUID

# Task schemas
class TaskBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)
    progress_notes: Optional[str] = None

class TaskCreate(TaskBase):
    team_id: UUID
    agent_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None

class TaskUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    progress_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    progress_notes: Optional[str] = None
    agent_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    completed_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None

class TaskResponse(TaskBase, TimestampMixin):
    id: UUID
    team_id: UUID
    agent_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    completed_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    completed_at: Optional[datetime] = None

# Knowledge schemas
class KnowledgeBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=255)
    filename: Optional[str] = None
    type: str = Field(..., pattern="^(document|link|text)$")
    mime_type: Optional[str] = None
    size: Optional[int] = Field(None, ge=0)
    status: str = Field("active", pattern="^(active|processing|error)$")
    content_preview: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    word_count: Optional[int] = Field(None, ge=0)
    extracted_text: Optional[str] = None

class KnowledgeCreate(KnowledgeBase):
    owner_id: UUID

class KnowledgeUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    filename: Optional[str] = None
    type: Optional[str] = Field(None, pattern="^(document|link|text)$")
    mime_type: Optional[str] = None
    size: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|processing|error)$")
    content_preview: Optional[str] = None
    tags: Optional[List[str]] = None
    source_url: Optional[str] = None
    word_count: Optional[int] = Field(None, ge=0)
    extracted_text: Optional[str] = None

class KnowledgeResponse(KnowledgeBase, TimestampMixin):
    id: UUID
    owner_id: UUID
    upload_date: datetime
    last_modified: datetime

# Conversation schemas
class ConversationBase(BaseSchema):
    title: Optional[str] = None
    status: ConversationStatus = ConversationStatus.RUNNING

class ConversationCreate(ConversationBase):
    owner_id: UUID

class ConversationUpdate(BaseSchema):
    title: Optional[str] = None
    status: Optional[ConversationStatus] = None

class ConversationResponse(ConversationBase, TimestampMixin):
    owner_id: UUID

# Message schemas
class MessageBase(BaseSchema):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: Optional[str] = None
    status: str = Field("sent", pattern="^(sending|sent)$")
    template_metadata: Optional[Dict[str, Any]] = None

class MessageCreate(MessageBase):
    conversation_id: UUID

class MessageUpdate(BaseSchema):
    content: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(sending|sent)$")
    template_metadata: Optional[Dict[str, Any]] = None

class MessageResponse(MessageBase, TimestampMixin):
    id: UUID
    conversation_id: UUID
    timestamp: datetime

# Error schemas
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
