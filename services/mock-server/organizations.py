"""
Organization endpoints for the mock server.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, Organization
from models import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from typing import List
import uuid
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])

def _parse_json_field(json_str: str) -> dict:
    """Parse JSON string field, return empty dict if invalid."""
    try:
        return json.loads(json_str) if json_str else {}
    except (json.JSONDecodeError, TypeError):
        return {}

def _serialize_organization(org: Organization) -> dict:
    """Convert Organization model to dict with proper JSON parsing."""
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "industry": org.industry,
        "size": org.size,
        "founded": org.founded,
        "website": org.website,
        "settings": _parse_json_field(org.settings),
        "created_at": org.created_at,
        "updated_at": org.updated_at,
        "team_count": org.team_count,
        "agent_count": org.agent_count
    }

@router.get("/", response_model=List[OrganizationResponse])
def get_organizations(db: Session = Depends(get_db)):
    """Get all organizations (no authentication required for listing)."""
    logger.info("GET /organizations - Listing all organizations")
    organizations = db.query(Organization).all()
    return [_serialize_organization(org) for org in organizations]

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization."""
    logger.info(f"POST /organizations - Creating organization: {org_data.name}")
    
    # Create new organization
    org_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    organization = Organization(
        id=org_id,
        name=org_data.name,
        description=org_data.description,
        industry=org_data.industry,
        size=org_data.size,
        founded=org_data.founded,
        website=org_data.website,
        settings="{}",
        created_at=now,
        updated_at=now,
        team_count=0,
        agent_count=0
    )
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    logger.info(f"Created organization: {organization.name} ({org_id})")
    return _serialize_organization(organization)

@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: str, db: Session = Depends(get_db)):
    """Get a specific organization by ID."""
    logger.info(f"GET /organizations/{org_id}")
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return _serialize_organization(organization)

@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db)
):
    """Update an organization."""
    logger.info(f"PUT /organizations/{org_id}")
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    update_data = org_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(organization)
    
    logger.info(f"Updated organization: {organization.name} ({org_id})")
    return _serialize_organization(organization)
