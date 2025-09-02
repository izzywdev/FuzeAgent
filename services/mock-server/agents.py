"""
Agent endpoints for the mock server.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, Agent, Team, Organization
from models import AgentCreate, AgentUpdate, AgentResponse
from auth import get_organization_id_from_bearer_token
from typing import List
import uuid
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/", response_model=List[AgentResponse])
def get_agents(
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Get all agents for the authenticated organization."""
    logger.info(f"GET /agents - Organization: {org_id}")
    
    # Get all teams for the organization
    org_teams = db.query(Team).filter(Team.organization_id == org_id).all()
    org_team_ids = [team.id for team in org_teams]
    
    # Get all agents for those teams
    agents = db.query(Agent).filter(Agent.team_id.in_(org_team_ids)).all()
    
    # Convert to response format
    agent_responses = []
    for agent in agents:
        agent_dict = {
            "id": agent.id,
            "team_id": agent.team_id,
            "name": agent.name,
            "role": agent.role,
            "type": agent.type,
            "status": agent.status,
            "config": json.loads(agent.config) if agent.config else {},
            "template_id": agent.template_id,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "tasks": {"completed": 0, "running": 0, "pending": 0},
            "lastActivity": agent.created_at,
            "performance": {
                "tasksCompleted": 0,
                "tasksActive": 0,
                "efficiency": "0%"
            },
            "joinedDate": agent.created_at,
            "conversations": []
        }
        agent_responses.append(agent_dict)
    
    logger.info(f"Returning {len(agent_responses)} agents for organization {org_id}")
    return agent_responses

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: AgentCreate,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Create a new agent for the authenticated organization."""
    logger.info(f"POST /agents - Organization: {org_id}, Agent: {agent_data.name}")
    
    # Verify the team belongs to the organization
    team = db.query(Team).filter(
        Team.id == agent_data.team_id,
        Team.organization_id == org_id
    ).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or does not belong to your organization"
        )
    
    # Create new agent
    agent_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    default_config = {
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
        "tools": [],
        "goal": "",
        "backstory": ""
    }
    
    agent = Agent(
        id=agent_id,
        team_id=agent_data.team_id,
        name=agent_data.name,
        role=agent_data.role or "Agent",
        type=agent_data.type or "developer",
        status="active",
        config=json.dumps(agent_data.config or default_config),
        template_id=agent_data.template_id,
        created_at=now,
        updated_at=now
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    # Update organization agent count
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if organization:
        organization.agent_count += 1
        db.commit()
    
    # Convert to response format
    agent_response = {
        "id": agent.id,
        "team_id": agent.team_id,
        "name": agent.name,
        "role": agent.role,
        "type": agent.type,
        "status": agent.status,
        "config": json.loads(agent.config) if agent.config else {},
        "template_id": agent.template_id,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "tasks": {"completed": 0, "running": 0, "pending": 0},
        "lastActivity": agent.created_at,
        "performance": {
            "tasksCompleted": 0,
            "tasksActive": 0,
            "efficiency": "0%"
        },
        "joinedDate": agent.created_at,
        "conversations": []
    }
    
    logger.info(f"Created agent: {agent.name} ({agent_id}) for organization {org_id}")
    return agent_response

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Get a specific agent by ID (must belong to authenticated organization)."""
    logger.info(f"GET /agents/{agent_id} - Organization: {org_id}")
    
    # Get agent and verify it belongs to the organization
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Verify agent's team belongs to the organization
    team = db.query(Team).filter(
        Team.id == agent.team_id,
        Team.organization_id == org_id
    ).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Convert to response format
    agent_response = {
        "id": agent.id,
        "team_id": agent.team_id,
        "name": agent.name,
        "role": agent.role,
        "type": agent.type,
        "status": agent.status,
        "config": json.loads(agent.config) if agent.config else {},
        "template_id": agent.template_id,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "tasks": {"completed": 0, "running": 0, "pending": 0},
        "lastActivity": agent.created_at,
        "performance": {
            "tasksCompleted": 0,
            "tasksActive": 0,
            "efficiency": "0%"
        },
        "joinedDate": agent.created_at,
        "conversations": []
    }
    
    return agent_response

@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Update an agent (must belong to authenticated organization)."""
    logger.info(f"PUT /agents/{agent_id} - Organization: {org_id}")
    
    # Get agent and verify it belongs to the organization
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Verify agent's team belongs to the organization
    team = db.query(Team).filter(
        Team.id == agent.team_id,
        Team.organization_id == org_id
    ).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    update_data = agent_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "config" and value:
            setattr(agent, field, json.dumps(value))
        else:
            setattr(agent, field, value)
    
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    # Convert to response format
    agent_response = {
        "id": agent.id,
        "team_id": agent.team_id,
        "name": agent.name,
        "role": agent.role,
        "type": agent.type,
        "status": agent.status,
        "config": json.loads(agent.config) if agent.config else {},
        "template_id": agent.template_id,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "tasks": {"completed": 0, "running": 0, "pending": 0},
        "lastActivity": agent.created_at,
        "performance": {
            "tasksCompleted": 0,
            "tasksActive": 0,
            "efficiency": "0%"
        },
        "joinedDate": agent.created_at,
        "conversations": []
    }
    
    logger.info(f"Updated agent: {agent.name} ({agent_id})")
    return agent_response
