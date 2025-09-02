"""
Main FastAPI application for the mock server.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from organizations import router as organizations_router
from teams import router as teams_router
from agents import router as agents_router
from goals import router as goals_router
from tasks import router as tasks_router
from milestones import router as milestones_router
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
app.include_router(organizations_router)
app.include_router(teams_router)
app.include_router(agents_router)
app.include_router(goals_router)
app.include_router(tasks_router)
app.include_router(milestones_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    logger.info("Starting up Mock API server...")
    create_tables()
    logger.info("Database tables created/verified")

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
