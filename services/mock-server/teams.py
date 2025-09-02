"""
Team endpoints for the mock server.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, Team, Organization
from models import TeamCreate, TeamUpdate, TeamResponse
from auth import get_organization_id_from_bearer_token
from typing import List
import uuid
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/", response_model=List[TeamResponse])
def get_teams(
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Get all teams for the authenticated organization."""
    logger.info(f"GET /teams - Organization: {org_id}")
    
    teams = db.query(Team).filter(Team.organization_id == org_id).all()
    
    # Convert to response format with additional fields
    team_responses = []
    for team in teams:
        team_dict = {
            "id": team.id,
            "organization_id": team.organization_id,
            "name": team.name,
            "description": team.description,
            "team_type": team.team_type,
            "color": team.color,
            "status": team.status,
            "settings": json.loads(team.settings) if team.settings else {},
            "created_at": team.created_at,
            "updated_at": team.updated_at,
            "members": [],  # TODO: Implement team members
            "stats": {
                "totalTasks": 0,
                "completedTasks": 0,
                "activeTasks": 0,
                "avgResponseTime": "0s"
            },
            "knowledgeBase": []  # TODO: Implement knowledge base
        }
        team_responses.append(team_dict)
    
    logger.info(f"Returning {len(team_responses)} teams for organization {org_id}")
    return team_responses

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Create a new team for the authenticated organization."""
    logger.info(f"POST /teams - Organization: {org_id}, Team: {team_data.name}")
    
    # Create new team
    team_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    team = Team(
        id=team_id,
        organization_id=org_id,
        name=team_data.name,
        description=team_data.description,
        team_type=team_data.team_type,
        color=team_data.settings.get("color", "#2563eb") if team_data.settings else "#2563eb",
        status="active",
        settings=json.dumps(team_data.settings) if team_data.settings else "{}",
        created_at=now,
        updated_at=now
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Update organization team count
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if organization:
        organization.team_count += 1
        db.commit()
    
    # Convert to response format
    team_response = {
        "id": team.id,
        "organization_id": team.organization_id,
        "name": team.name,
        "description": team.description,
        "team_type": team.team_type,
        "color": team.color,
        "status": team.status,
        "settings": json.loads(team.settings) if team.settings else {},
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": [],
        "stats": {
            "totalTasks": 0,
            "completedTasks": 0,
            "activeTasks": 0,
            "avgResponseTime": "0s"
        },
        "knowledgeBase": []
    }
    
    logger.info(f"Created team: {team.name} ({team_id}) for organization {org_id}")
    return team_response

@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: str,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Get a specific team by ID (must belong to authenticated organization)."""
    logger.info(f"GET /teams/{team_id} - Organization: {org_id}")
    
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.organization_id == org_id
    ).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Convert to response format
    team_response = {
        "id": team.id,
        "organization_id": team.organization_id,
        "name": team.name,
        "description": team.description,
        "team_type": team.team_type,
        "color": team.color,
        "status": team.status,
        "settings": json.loads(team.settings) if team.settings else {},
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": [],
        "stats": {
            "totalTasks": 0,
            "completedTasks": 0,
            "activeTasks": 0,
            "avgResponseTime": "0s"
        },
        "knowledgeBase": []
    }
    
    return team_response

@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: str,
    team_data: TeamUpdate,
    org_id: str = Depends(get_organization_id_from_bearer_token),
    db: Session = Depends(get_db)
):
    """Update a team (must belong to authenticated organization)."""
    logger.info(f"PUT /teams/{team_id} - Organization: {org_id}")
    
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.organization_id == org_id
    ).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Update fields
    update_data = team_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)
    
    team.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(team)
    
    # Convert to response format
    team_response = {
        "id": team.id,
        "organization_id": team.organization_id,
        "name": team.name,
        "description": team.description,
        "team_type": team.team_type,
        "color": team.color,
        "status": team.status,
        "settings": json.loads(team.settings) if team.settings else {},
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "members": [],
        "stats": {
            "totalTasks": 0,
            "completedTasks": 0,
            "activeTasks": 0,
            "avgResponseTime": "0s"
        },
        "knowledgeBase": []
    }
    
    logger.info(f"Updated team: {team.name} ({team_id})")
    return team_response
