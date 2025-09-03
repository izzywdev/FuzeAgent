"""
Main FastAPI application for the mock server.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from database import create_tables
    logger.info("Database module imported successfully")
except ImportError as e:
    logger.error(f"Failed to import database module: {e}")
    raise

try:
    from organizations import router as organizations_router
    from teams import router as teams_router
    from agents import router as agents_router
    from goals import router as goals_router
    from tasks import router as tasks_router
    from milestones import router as milestones_router
    logger.info("All routers imported successfully")
except ImportError as e:
    logger.error(f"Failed to import routers: {e}")
    raise

# Create FastAPI app
app = FastAPI(
    title="FuzeAgent Mock API",
    description="Mock API server for FuzeAgent with organization-scoped data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
try:
    app.include_router(organizations_router)
    logger.info("Organizations router included")

    app.include_router(teams_router, prefix="/organizations/{org_id}")
    logger.info("Teams router included")

    app.include_router(agents_router, prefix="/organizations/{org_id}")
    logger.info("Agents router included")

    app.include_router(goals_router)
    logger.info("Goals router included")

    app.include_router(tasks_router)
    logger.info("Tasks router included")

    app.include_router(milestones_router)
    logger.info("Milestones router included")

    logger.info("All routers registered successfully")
except Exception as e:
    logger.error(f"Failed to register routers: {e}")
    raise

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    logger.info("Starting up Mock API server...")
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "FuzeAgent Mock API Server",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
