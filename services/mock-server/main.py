"""
Main FastAPI application for the mock server.
"""

import logging
import os

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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
    from agent_templates import router as agent_templates_router
    from websocket_handler import websocket_manager
    logger.info("All routers and WebSocket handler imported successfully")
except ImportError as e:
    logger.error(f"Failed to import routers or WebSocket handler: {e}")
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

    app.include_router(teams_router)
    logger.info("Teams router included")

    app.include_router(agents_router)
    logger.info("Agents router included")

    app.include_router(goals_router)
    logger.info("Goals router included")

    app.include_router(tasks_router)
    logger.info("Tasks router included")

    app.include_router(milestones_router)
    logger.info("Milestones router included")

    app.include_router(agent_templates_router)
    logger.info("Agent templates router included")

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

# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws/agents/{agent_id}/conversations/{conversation_id}")
async def websocket_agent_conversation(websocket: WebSocket, agent_id: str, conversation_id: str):
    """WebSocket endpoint for agent conversation chat"""
    connection_id = None
    
    try:
        connection_id = await websocket_manager.connect(websocket, agent_id, conversation_id)
        
        # Keep connection alive and handle messages
        while True:
            try:
                message = await websocket.receive_text()
                await websocket_manager.handle_message(websocket, message, agent_id, conversation_id)
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}, conversation {conversation_id}: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
