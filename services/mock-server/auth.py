"""
Authentication utilities for Bearer token validation.
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, Organization
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_organization_from_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Organization:
    """
    Extract and validate organization ID from Bearer token.
    Returns the organization if valid, raises HTTPException if invalid.
    """
    if not credentials or not credentials.credentials:
        logger.warning("No Bearer token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid organization Bearer token required"
        )
    
    org_id = credentials.credentials
    
    # Validate that the organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        logger.warning(f"Invalid organization ID in Bearer token: {org_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid organization Bearer token"
        )
    
    logger.info(f"Valid Bearer token for organization: {organization.name} ({org_id})")
    return organization

def get_organization_id_from_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    Extract and validate organization ID from Bearer token.
    Returns the organization ID if valid, raises HTTPException if invalid.
    """
    organization = get_organization_from_bearer_token(credentials, db)
    return organization.id
