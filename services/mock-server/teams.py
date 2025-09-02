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
    db: Session = Depends(get_db)
):
    """Get all teams (no authentication required for listing)."""
    logger.info("GET /teams - Listing all teams")

    teams = db.query(Team).all()
    
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
    db: Session = Depends(get_db)
):
    """Get a specific team by ID."""
    logger.info(f"GET /teams/{team_id}")

    team = db.query(Team).filter(Team.id == team_id).first()

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

# Knowledge/Document endpoints for teams
@router.get("/{team_id}/knowledge", response_model=List[dict])
def get_team_knowledge(team_id: str, db: Session = Depends(get_db)):
    """Get knowledge documents for a team."""
    logger.info(f"GET /teams/{team_id}/knowledge")

    # For now, return mock data since we don't have a knowledge table
    mock_docs = [
        {
            "id": "doc1",
            "title": "Team Guidelines",
            "filename": "guidelines.pdf",
            "type": "document",
            "mime_type": "application/pdf",
            "size": 1024000,
            "status": "active",
            "upload_date": "2024-01-15T10:00:00Z",
            "last_modified": "2024-01-15T10:00:00Z",
            "content_preview": "This document contains team guidelines...",
            "tags": ["guidelines", "team"],
            "team_id": team_id,
            "word_count": 1200,
            "extracted_text": "This document contains team guidelines and best practices..."
        },
        {
            "id": "doc2",
            "title": "Project Documentation",
            "filename": "project-docs.md",
            "type": "document",
            "mime_type": "text/markdown",
            "size": 512000,
            "status": "active",
            "upload_date": "2024-01-20T14:30:00Z",
            "last_modified": "2024-01-20T14:30:00Z",
            "content_preview": "# Project Documentation\n\nThis is the main project documentation...",
            "tags": ["documentation", "project"],
            "team_id": team_id,
            "word_count": 800,
            "extracted_text": "# Project Documentation\n\nThis is the main project documentation..."
        }
    ]

    return mock_docs

@router.get("/{team_id}/knowledge/{doc_id}/content", response_model=dict)
def get_team_knowledge_content(team_id: str, doc_id: str, db: Session = Depends(get_db)):
    """Get content of a specific knowledge document."""
    logger.info(f"GET /teams/{team_id}/knowledge/{doc_id}/content")

    # Mock content based on document ID
    mock_content = {
        "doc1": {
            "content": "This document contains team guidelines and best practices for working together effectively. Please review these guidelines regularly to ensure smooth collaboration.",
            "type": "document",
            "filename": "guidelines.pdf"
        },
        "doc2": {
            "content": "# Project Documentation\n\nThis is the main project documentation for the team. It contains all the important information about the project structure, requirements, and procedures.",
            "type": "document",
            "filename": "project-docs.md"
        }
    }

    if doc_id not in mock_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return mock_content[doc_id]

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
