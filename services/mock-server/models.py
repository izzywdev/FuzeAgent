"""
SQLAlchemy models for FuzeAgent Mock Server
These models exactly match the FuzeAgentMock database schema
"""
from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Boolean, 
    DateTime, Numeric, ForeignKey, UniqueConstraint, CheckConstraint,
    Index, ARRAY, JSON, Enum as SQLEnum, PrimaryKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

# Enums are defined in schemas.py

# Core registry table
class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(ENUM("organization", "team", "agent", name="entity_kind", schema="FuzeAgentMock"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

# Organizations
class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    settings = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="organization", cascade="all, delete-orphan")
    org_tools = relationship("OrgTool", back_populates="organization", cascade="all, delete-orphan")

# Teams
class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        {"schema": "FuzeAgentMock"}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    team_type = Column(Text)
    color = Column(Text)
    status = Column(ENUM("active", "inactive", name="team_status", schema="FuzeAgentMock"), nullable=False, default="active")
    settings = Column(JSON, nullable=False, default={})
    team_lead = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan", foreign_keys="Agent.team_id")
    tasks = relationship("Task", back_populates="team", cascade="all, delete-orphan")
    goal_assignments = relationship("GoalAssignedTeam", back_populates="team", cascade="all, delete-orphan")
    team_tool_settings = relationship("TeamToolSetting", back_populates="team", cascade="all, delete-orphan")
    team_lead_history = relationship("TeamLeadHistory", back_populates="team", cascade="all, delete-orphan")

# Agent Templates
class AgentTemplate(Base):
    __tablename__ = "agent_templates"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
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
    template_metadata = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    template_env_vars = relationship("AgentTemplateEnvVar", back_populates="template", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="template")

class AgentTemplateEnvVar(Base):
    __tablename__ = "agent_template_env_vars"
    __table_args__ = (
        PrimaryKeyConstraint("template_id", "name"),
        {"schema": "FuzeAgentMock"}
    )
    
    template_id = Column(Text, ForeignKey("FuzeAgentMock.agent_templates.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    value = Column(Text)
    is_secret = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    template = relationship("AgentTemplate", back_populates="template_env_vars")

# Agents
class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint("status IN ('active','idle','inactive')"),
        CheckConstraint("temperature BETWEEN 0 AND 2"),
        Index("idx_agents_team", "team_id"),
        {"schema": "FuzeAgentMock"}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.entities.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    role = Column(Text)
    type = Column(Text)
    status = Column(Text, nullable=False, default="active")
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
    template_metadata = Column(JSON, nullable=False, default={})
    template_id = Column(Text, ForeignKey("FuzeAgentMock.agent_templates.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_activity = Column(DateTime(timezone=True))
    joined_date = Column(DateTime(timezone=True))
    
    # Relationships
    team = relationship("Team", back_populates="agents", foreign_keys="Agent.team_id")
    template = relationship("AgentTemplate", back_populates="agents")
    agent_env_vars = relationship("AgentEnvVar", back_populates="agent", cascade="all, delete-orphan")
    containers = relationship("Container", back_populates="agent", cascade="all, delete-orphan")
    agent_tool_settings = relationship("AgentToolSetting", back_populates="agent", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="agent")
    task_assignments = relationship("TaskAssignment", back_populates="agent", cascade="all, delete-orphan")

# Team Lead History
class TeamLeadHistory(Base):
    __tablename__ = "team_lead_history"
    __table_args__ = (
        Index("idx_team_lead_history_team", "team_id", "changed_at"),
        {"schema": "FuzeAgentMock"}
    )
    
    id = Column(BigInteger, primary_key=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.teams.id", ondelete="CASCADE"), nullable=False)
    prev_lead_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    new_lead_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    reason = Column(Text, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    team = relationship("Team", back_populates="team_lead_history")

# Agent Environment Variables
class AgentEnvVar(Base):
    __tablename__ = "agent_env_vars"
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", "name"),
        {"schema": "FuzeAgentMock"}
    )
    
    agent_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    value = Column(Text)
    is_secret = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="agent_env_vars")

# Containers
class Container(Base):
    __tablename__ = "containers"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(Text)
    provider = Column(Text, nullable=False)
    docker_image = Column(Text)
    config = Column(JSON, nullable=False, default={})
    last_run_at = Column(DateTime(timezone=True))
    last_run_duration = Column(Text)  # Using Text for interval type
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="containers")

# Organization Tools
class OrgTool(Base):
    __tablename__ = "org_tools"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.organizations.id", ondelete="CASCADE"), nullable=False)
    key = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    default_config = Column(JSON, nullable=False, default={})
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="org_tools")
    tool_params = relationship("OrgToolParam", back_populates="tool", cascade="all, delete-orphan")
    team_tool_settings = relationship("TeamToolSetting", back_populates="tool", cascade="all, delete-orphan")
    agent_tool_settings = relationship("AgentToolSetting", back_populates="tool", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("org_id", "key"),
        {"schema": "FuzeAgentMock"}
    )

class OrgToolParam(Base):
    __tablename__ = "org_tool_params"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(BigInteger, primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.org_tools.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    param_type = Column(Text, nullable=False)
    required = Column(Boolean, nullable=False, default=False)
    default_value = Column(JSON)
    
    # Relationships
    tool = relationship("OrgTool", back_populates="tool_params")
    
    __table_args__ = (
        UniqueConstraint("tool_id", "name"),
        {"schema": "FuzeAgentMock"}
    )

class TeamToolSetting(Base):
    __tablename__ = "team_tool_settings"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    team_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.teams.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.org_tools.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    config_override = Column(JSON)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    team = relationship("Team", back_populates="team_tool_settings")
    tool = relationship("OrgTool", back_populates="team_tool_settings")
    
    __table_args__ = (
        PrimaryKeyConstraint("team_id", "tool_id"),
        {"schema": "FuzeAgentMock"}
    )

class AgentToolSetting(Base):
    __tablename__ = "agent_tool_settings"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    agent_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.org_tools.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    config_override = Column(JSON)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="agent_tool_settings")
    tool = relationship("OrgTool", back_populates="agent_tool_settings")
    
    __table_args__ = (
        PrimaryKeyConstraint("agent_id", "tool_id"),
        {"schema": "FuzeAgentMock"}
    )

# Goals
class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.organizations.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    priority = Column(Text, nullable=False, default="medium")
    status = Column(Text, nullable=False, default="planning")
    target_completion_date = Column(DateTime(timezone=True))
    progress_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="goals")
    assigned_teams = relationship("GoalAssignedTeam", back_populates="goal", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="goal", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("priority IN ('low','medium','high','critical')"),
        CheckConstraint("status IN ('planning','active','completed','on_hold')"),
        {"schema": "FuzeAgentMock"}
    )

class GoalAssignedTeam(Base):
    __tablename__ = "goal_assigned_teams"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    goal_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.goals.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.teams.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    goal = relationship("Goal", back_populates="assigned_teams")
    team = relationship("Team", back_populates="goal_assignments")
    
    __table_args__ = (
        PrimaryKeyConstraint("goal_id", "team_id"),
        {"schema": "FuzeAgentMock"}
    )

# Milestones
class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.goals.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="planned")
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    goal = relationship("Goal", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone", cascade="all, delete-orphan")

# Tasks
class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.teams.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.milestones.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(ENUM("pending", "in_progress", "blocked", "closed", "closed_approved", name="task_status", schema="FuzeAgentMock"), nullable=False, default="pending")
    priority = Column(Text, nullable=False, default="medium")
    progress_pct = Column(Numeric(5, 2), nullable=False, default=0)
    progress_notes = Column(Text)
    completed_by = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    team = relationship("Team", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks", foreign_keys=[agent_id])
    milestone = relationship("Milestone", back_populates="tasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("priority IN ('low','medium','high')"),
        Index("idx_tasks_team", "team_id"),
        Index("idx_tasks_agent", "agent_id"),
        Index("idx_tasks_milestone", "milestone_id"),
        {"schema": "FuzeAgentMock"}
    )

class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    task_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.tasks.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.agents.id", ondelete="CASCADE"), nullable=False)
    inherited = Column(Boolean, nullable=False, default=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="assignments")
    agent = relationship("Agent", back_populates="task_assignments")
    
    __table_args__ = (
        PrimaryKeyConstraint("task_id", "agent_id"),
        {"schema": "FuzeAgentMock"}
    )

# Conversations
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.entities.id", ondelete="CASCADE"), primary_key=True)
    title = Column(Text)
    status = Column(ENUM("running", "paused", "stopped", name="conversation_status", schema="FuzeAgentMock"), nullable=False, default="running")
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.conversations.owner_id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text)
    status = Column(Text, nullable=False, default="sent")
    template_metadata = Column(JSON)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')"),
        CheckConstraint("status IN ('sending','sent')"),
        Index("idx_messages_convo_time", "conversation_id", "timestamp", "id"),
        {"schema": "FuzeAgentMock"}
    )

# Knowledge
class Knowledge(Base):
    __tablename__ = "knowledge"
    __table_args__ = {"schema": "FuzeAgentMock"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("FuzeAgentMock.entities.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    filename = Column(Text)
    type = Column(Text, nullable=False)
    mime_type = Column(Text)
    size = Column(BigInteger)
    status = Column(Text, nullable=False, default="active")
    upload_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_modified = Column(DateTime(timezone=True), nullable=False, default=func.now())
    content_preview = Column(Text)
    tags = Column(ARRAY(Text), nullable=False, default=[])
    source_url = Column(Text)
    word_count = Column(Integer)
    extracted_text = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    __table_args__ = (
        CheckConstraint("type IN ('document','link','text')"),
        CheckConstraint("status IN ('active','processing','error')"),
        {"schema": "FuzeAgentMock"}
    )
