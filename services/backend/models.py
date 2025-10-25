"""
SQLAlchemy models for FuzeAgent Backend Service
Based on the schema provided in New - Schema.pdf
"""
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, 
    DateTime, Numeric, ForeignKey, UniqueConstraint, CheckConstraint,
    Index, ARRAY, JSON, Enum as SQLEnum, PrimaryKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ENUM, BIGINT
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class EntityKind:
    ORGANIZATION = "organization"
    TEAM = "team"
    AGENT = "agent"

class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"
    CLOSED_APPROVED = "closed_approved"

class TeamStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"

class ConversationStatus:
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"

class ToolParamType:
    FREE_TEXT = "free-text"

# ============================================================================
# 1. SHARED INFRASTRUCTURE
# ============================================================================

class Entity(Base):
    """Global identity registry for organizations, teams, agents"""
    __tablename__ = "entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(
        ENUM("organization", "team", "agent", name="entity_kind", create_type=True),
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())

# ============================================================================
# 2. ORGANIZATIONS
# ============================================================================

class Organization(Base):
    """Organizations table"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    settings = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="organization", cascade="all, delete-orphan")
    org_tools = relationship("OrgTool", back_populates="organization", cascade="all, delete-orphan")

# ============================================================================
# 3. TEAMS
# ============================================================================

class Team(Base):
    """Teams table"""
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
    )
    
    id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    team_type = Column(Text)
    color = Column(Text)
    status = Column(
        ENUM("active", "inactive", name="team_status", create_type=True),
        nullable=False,
        default="active"
    )
    settings = Column(JSON, nullable=False, default={})
    team_lead = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    team_lead_agent = relationship("Agent", foreign_keys=[team_lead])
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan", foreign_keys="Agent.team_id")
    tasks = relationship("Task", back_populates="team", cascade="all, delete-orphan")
    goal_assignments = relationship("GoalAssignedTeam", back_populates="team", cascade="all, delete-orphan")
    team_tool_settings = relationship("TeamToolSetting", back_populates="team", cascade="all, delete-orphan")
    team_lead_history = relationship("TeamLeadHistory", back_populates="team", cascade="all, delete-orphan")

class TeamLeadHistory(Base):
    """Team lead change history"""
    __tablename__ = "team_lead_history"
    
    id = Column(BIGINT, primary_key=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    prev_lead_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    new_lead_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    reason = Column(Text, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    
    # Relationships
    team = relationship("Team", back_populates="team_lead_history")
    
    # Indexes
    __table_args__ = (
        Index('ix_team_lead_history_team_changed', 'team_id', 'changed_at'),
    )

# ============================================================================
# 4. AGENTS
# ============================================================================

class AgentTemplate(Base):
    """Agent templates table"""
    __tablename__ = "agent_templates"
    
    id = Column(Text, primary_key=True)
    template_name = Column(Text, nullable=False)
    category = Column(Text)
    description = Column(Text)
    model = Column(Text, nullable=False)
    temperature = Column(Numeric(3, 2), default=0.70)
    top_p = Column(Numeric(3, 2))
    max_tokens = Column(Integer)
    frequency_penalty = Column(Numeric(3, 2))
    presence_penalty = Column(Numeric(3, 2))
    stop_sequences = Column(ARRAY(Text))
    backstory = Column(Text)
    system_prompt = Column(Text)
    docker_image = Column(Text)
    concurrency_limit = Column(Integer)
    timezone = Column(Text)
    locale = Column(Text)
    log_level = Column(Text)
    tags = Column(ARRAY(Text))
    custom_metadata = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="template")

class AgentTemplateEnvVar(Base):
    """Agent template environment variables"""
    __tablename__ = "agent_template_env_vars"
    
    template_id = Column(Text, ForeignKey("agent_templates.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    value = Column(Text)
    is_secret = Column(Boolean, nullable=False, default=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('template_id', 'name'),
    )

class Agent(Base):
    """Agents table"""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    role = Column(Text)
    type = Column(Text)
    status = Column(String(20), CheckConstraint("status IN ('active','idle','inactive')"), default='active')
    model = Column(Text, nullable=False)
    temperature = Column(Numeric(3, 2), CheckConstraint("temperature BETWEEN 0 AND 2"), default=0.70)
    top_p = Column(Numeric(3, 2))
    max_tokens = Column(Integer)
    frequency_penalty = Column(Numeric(3, 2))
    presence_penalty = Column(Numeric(3, 2))
    stop_sequences = Column(ARRAY(Text))
    backstory = Column(Text)
    system_prompt = Column(Text)
    docker_image = Column(Text)
    concurrency_limit = Column(Integer)
    timezone = Column(Text)
    locale = Column(Text)
    log_level = Column(Text)
    tags = Column(ARRAY(Text))
    custom_metadata = Column(JSON, nullable=False, default={})
    template_id = Column(Text, ForeignKey("agent_templates.id"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True))
    joined_date = Column(DateTime(timezone=True))
    
    # Relationships
    team = relationship("Team", back_populates="agents", foreign_keys=[team_id])
    template = relationship("AgentTemplate", back_populates="agents")
    env_vars = relationship("AgentEnvVar", back_populates="agent", cascade="all, delete-orphan")

class AgentEnvVar(Base):
    """Agent environment variables"""
    __tablename__ = "agent_env_vars"
    
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    value = Column(Text)
    is_secret = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="env_vars")
    
    __table_args__ = (
        PrimaryKeyConstraint('agent_id', 'name'),
    )

# ============================================================================
# 5. CONTAINERS
# ============================================================================

class Container(Base):
    """Containers table"""
    __tablename__ = "containers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(Text)
    provider = Column(Text, nullable=False)
    docker_image = Column(Text)
    config = Column(JSON, nullable=False, default={})
    last_run_at = Column(DateTime(timezone=True))
    last_run_duration = Column(Numeric)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")

# ============================================================================
# 6. TOOLS (org-level + overrides)
# ============================================================================

class OrgTool(Base):
    """Organization-level tools"""
    __tablename__ = "org_tools"
    __table_args__ = (
        UniqueConstraint("org_id", "key"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    key = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    default_config = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="org_tools")
    params = relationship("OrgToolParam", back_populates="tool", cascade="all, delete-orphan")

class OrgToolParam(Base):
    """Organization tool parameters"""
    __tablename__ = "org_tool_params"
    
    id = Column(BIGINT, primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("org_tools.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    param_type = Column(Text, nullable=False)
    required = Column(Boolean, nullable=False, default=False)
    default_value = Column(JSON)
    
    # Relationships
    tool = relationship("OrgTool", back_populates="params")
    
    __table_args__ = (
        UniqueConstraint('tool_id', 'name'),
    )

class TeamToolSetting(Base):
    """Team-level tool settings"""
    __tablename__ = "team_tool_settings"
    
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("org_tools.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    config_override = Column(JSON)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    team = relationship("Team", back_populates="team_tool_settings")
    
    __table_args__ = (
        PrimaryKeyConstraint('team_id', 'tool_id'),
    )

class AgentToolSetting(Base):
    """Agent-level tool settings"""
    __tablename__ = "agent_tool_settings"
    
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("org_tools.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    config_override = Column(JSON)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        PrimaryKeyConstraint('agent_id', 'tool_id'),
    )

# ============================================================================
# 7. GOALS & MILESTONES
# ============================================================================

class Goal(Base):
    """Goals table"""
    __tablename__ = "goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    priority = Column(String(20), CheckConstraint("priority IN ('low','medium','high','critical')"), default='medium')
    status = Column(String(20), CheckConstraint("status IN ('planning','active','completed','on_hold')"), default='planning')
    target_completion_date = Column(DateTime(timezone=True))
    progress_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="goals")
    assigned_teams = relationship("GoalAssignedTeam", back_populates="goal", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="goal", cascade="all, delete-orphan")

class GoalAssignedTeam(Base):
    """Many-to-many relationship between goals and teams"""
    __tablename__ = "goal_assigned_teams"
    
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    goal = relationship("Goal", back_populates="assigned_teams")
    team = relationship("Team", back_populates="goal_assignments")
    
    __table_args__ = (
        PrimaryKeyConstraint('goal_id', 'team_id'),
    )

class Milestone(Base):
    """Milestones table"""
    __tablename__ = "milestones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='planned')
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    goal = relationship("Goal", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone", cascade="all, delete-orphan")

# ============================================================================
# 8. TASKS
# ============================================================================

class Task(Base):
    """Tasks table"""
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(ENUM('pending', 'in_progress', 'blocked', 'closed', 'closed_approved', name='task_status', create_type=True), nullable=False, default='pending')
    priority = Column(String(20), CheckConstraint("priority IN ('low','medium','high')"), default='medium')
    progress_pct = Column(Numeric(5, 2), nullable=False, default=0)
    progress_notes = Column(Text)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    team = relationship("Team", back_populates="tasks")
    assignee = relationship("Agent", foreign_keys=[agent_id])
    completed_by_agent = relationship("Agent", foreign_keys=[completed_by])
    approved_by_agent = relationship("Agent", foreign_keys=[approved_by])
    milestone = relationship("Milestone", back_populates="tasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")

class TaskAssignment(Base):
    """Task assignments to agents"""
    __tablename__ = "task_assignments"
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    inherited = Column(Boolean, nullable=False, default=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="assignments")
    
    __table_args__ = (
        PrimaryKeyConstraint('task_id', 'agent_id'),
    )

# ============================================================================
# 9. CONVERSATIONS (1:1 per owner)
# ============================================================================

class Conversation(Base):
    """Conversations table - 1:1 per owner"""
    __tablename__ = "conversations"
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    title = Column(Text)
    status = Column(ENUM('running', 'paused', 'stopped', name='conversation_status', create_type=True), nullable=False, default='running')
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

class ConversationMessage(Base):
    """Conversation messages table"""
    __tablename__ = "conversation_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.owner_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), CheckConstraint("role IN ('user','assistant')"), nullable=False)
    content = Column(Text)
    status = Column(String(20), CheckConstraint("status IN ('sending','sent')"), default='sent')
    message_metadata = Column(JSON)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('ix_conversation_messages_timestamp', 'conversation_id', 'timestamp', 'id'),
    )

# ============================================================================
# 10. KNOWLEDGE (Unified)
# ============================================================================

class Knowledge(Base):
    """Unified knowledge table"""
    __tablename__ = "knowledge"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    filename = Column(Text)
    type = Column(String(20), CheckConstraint("type IN ('document','link','text')"), nullable=False)
    mime_type = Column(Text)
    size = Column(BigInteger)
    status = Column(String(20), CheckConstraint("status IN ('active','processing','error')"), default='active')
    upload_date = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    last_modified = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
    content_preview = Column(Text)
    tags = Column(ARRAY(Text), nullable=False, default=[])
    source_url = Column(Text)
    word_count = Column(Integer)
    extracted_text = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
