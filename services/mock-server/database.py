"""
Database configuration and models for the mock server.
Uses SQLite with SQLAlchemy for persistence.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/mock_data_v2.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    industry = Column(String)
    size = Column(String)
    founded = Column(String)
    website = Column(String)
    settings = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    team_count = Column(Integer, default=0)
    agent_count = Column(Integer, default=0)
    
    # Relationships
    teams = relationship("Team", back_populates="organization")
    tools = relationship("OrgTool", back_populates="organization")

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    team_type = Column(String)
    color = Column(String, default="#2563eb")
    status = Column(String, default="active")
    settings = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="teams")
    agents = relationship("Agent", back_populates="team")
    tool_settings = relationship("TeamToolSetting", back_populates="team")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String)
    type = Column(String, default="developer")
    status = Column(String, default="active")
    config = Column(Text)  # JSON string
    template_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="agents")
    tool_settings = relationship("AgentToolSetting", back_populates="agent")

class OrgTool(Base):
    __tablename__ = "org_tools"
    
    id = Column(String, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    key = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    default_config = Column(Text)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="tools")
    team_settings = relationship("TeamToolSetting", back_populates="tool")
    agent_settings = relationship("AgentToolSetting", back_populates="tool")

class TeamToolSetting(Base):
    __tablename__ = "team_tool_settings"
    
    team_id = Column(String, ForeignKey("teams.id"), primary_key=True)
    tool_id = Column(String, ForeignKey("org_tools.id"), primary_key=True)
    enabled = Column(Boolean, default=False)
    config_override = Column(Text)  # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="tool_settings")
    tool = relationship("OrgTool", back_populates="team_settings")

class AgentToolSetting(Base):
    __tablename__ = "agent_tool_settings"
    
    agent_id = Column(String, ForeignKey("agents.id"), primary_key=True)
    tool_id = Column(String, ForeignKey("org_tools.id"), primary_key=True)
    enabled = Column(Boolean, default=False)
    config_override = Column(Text)  # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="tool_settings")
    tool = relationship("OrgTool", back_populates="agent_settings")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    priority = Column(String, default="medium")  # low, medium, high, critical
    team_id = Column(String, ForeignKey("teams.id"))
    agent_id = Column(String, ForeignKey("agents.id"))
    milestone_id = Column(String, ForeignKey("milestones.id"))
    result = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    milestone = relationship("Milestone", back_populates="tasks")

class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="active")
    priority = Column(String, default="medium")
    target_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    milestones = relationship("Milestone", back_populates="goal", cascade="all, delete-orphan")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(String, primary_key=True, index=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="not_started")  # not_started, in_progress, completed, blocked, cancelled
    priority = Column(String, default="medium")  # low, medium, high, critical
    progress_percentage = Column(Integer, default=0)
    target_date = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    goal = relationship("Goal", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone", cascade="all, delete-orphan")

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
