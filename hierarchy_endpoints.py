#!/usr/bin/env python3
"""
Simple FastAPI service that adds organization/team endpoints 
and proxies other requests to the orchestrator
"""

import asyncio
import asyncpg
import json
import uuid
import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Set

# Configuration
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:J7hplO7vKnbUsKDAsxpe4t9C0@localhost:5434/ai_context")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

app = FastAPI(title="FuzeAgent Hierarchy API", version="1.0.0")

# CORS middleware - very permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

async def shutdown():
    if db_pool:
        await db_pool.close()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

# Pydantic models
class Organization(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    settings: dict = {}
    created_at: str
    updated_at: str

class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    settings: dict = {}

class Team(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    team_type: str = "general"
    settings: dict = {}
    created_at: str
    updated_at: str

class TeamCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None
    team_type: str = "general"
    settings: dict = {}

# Organization endpoints
@app.get("/organizations", response_model=List[Organization])
async def get_organizations():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id::text, name, description, settings,
                created_at::text, updated_at::text
            FROM organizations 
            ORDER BY created_at DESC
        """)
        
        organizations = []
        for row in rows:
            organizations.append(Organization(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                settings=json.loads(row['settings']) if row['settings'] else {},
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return organizations

@app.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate):
    async with db_pool.acquire() as conn:
        org_id = str(uuid.uuid4())
        row = await conn.fetchrow("""
            INSERT INTO organizations (id, name, description, settings)
            VALUES ($1, $2, $3, $4)
            RETURNING 
                id::text, name, description, settings,
                created_at::text, updated_at::text
        """, org_id, org_data.name, org_data.description, json.dumps(org_data.settings))
        
        organization = Organization(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            settings=json.loads(row['settings']) if row['settings'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Broadcast the change
        await manager.broadcast({
            "type": "organization_created",
            "data": organization.dict()
        })
        
        return organization

@app.get("/organizations/{organization_id}", response_model=Organization)
async def get_organization(organization_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id::text, name, description, settings,
                created_at::text, updated_at::text
            FROM organizations 
            WHERE id = $1
        """, organization_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return Organization(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            settings=json.loads(row['settings']) if row['settings'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

# Team endpoints
@app.get("/teams", response_model=List[Team])
async def get_teams(organization_id: Optional[str] = None):
    async with db_pool.acquire() as conn:
        if organization_id:
            rows = await conn.fetch("""
                SELECT 
                    id::text, organization_id::text, name, description,
                    team_type, settings, created_at::text, updated_at::text
                FROM teams 
                WHERE organization_id = $1
                ORDER BY created_at DESC
            """, organization_id)
        else:
            rows = await conn.fetch("""
                SELECT 
                    id::text, organization_id::text, name, description,
                    team_type, settings, created_at::text, updated_at::text
                FROM teams 
                ORDER BY created_at DESC
            """)
        
        teams = []
        for row in rows:
            teams.append(Team(
                id=row['id'],
                organization_id=row['organization_id'],
                name=row['name'],
                description=row['description'],
                team_type=row['team_type'],
                settings=json.loads(row['settings']) if row['settings'] else {},
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return teams

@app.post("/teams", response_model=Team)
async def create_team(team_data: TeamCreate):
    async with db_pool.acquire() as conn:
        # Verify organization exists
        org_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM organizations WHERE id = $1)",
            team_data.organization_id
        )
        if not org_exists:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        team_id = str(uuid.uuid4())
        row = await conn.fetchrow("""
            INSERT INTO teams (id, organization_id, name, description, team_type, settings)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING 
                id::text, organization_id::text, name, description,
                team_type, settings, created_at::text, updated_at::text
        """, team_id, team_data.organization_id, team_data.name, 
             team_data.description, team_data.team_type, json.dumps(team_data.settings))
        
        team = Team(
            id=row['id'],
            organization_id=row['organization_id'],
            name=row['name'],
            description=row['description'],
            team_type=row['team_type'],
            settings=json.loads(row['settings']) if row['settings'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Broadcast the change
        await manager.broadcast({
            "type": "team_created",
            "data": team.dict()
        })
        
        return team

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id::text, organization_id::text, name, description,
                team_type, settings, created_at::text, updated_at::text
            FROM teams 
            WHERE id = $1
        """, team_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return Team(
            id=row['id'],
            organization_id=row['organization_id'],
            name=row['name'],
            description=row['description'],
            team_type=row['team_type'],
            settings=json.loads(row['settings']) if row['settings'] else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Proxy all other requests to the original orchestrator
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_to_orchestrator(path: str, request: Request):
    url = f"{ORCHESTRATOR_URL}/{path}"
    
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get request body if present
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                # Log the request for debugging
                if path == "agents/from-template":
                    print(f"DEBUG: Proxying agents/from-template request")
                    print(f"DEBUG: URL: {url}")
                    print(f"DEBUG: Body: {body.decode() if body else 'None'}")
                    print(f"DEBUG: Headers: {dict(request.headers)}")
            
            # Forward the request
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                content=body,
                headers={k: v for k, v in request.headers.items() 
                        if k.lower() not in ['host', 'content-length']},
            )
            
            # Check if this was an agent creation and broadcast the change
            if (request.method == "POST" and 
                (path == "agents" or path == "agents/from-template") and 
                response.status_code in [200, 201] and
                response.headers.get("content-type", "").startswith("application/json")):
                try:
                    agent_data = response.json()
                    await manager.broadcast({
                        "type": "agent_created",
                        "data": agent_data
                    })
                except:
                    pass  # Ignore broadcast errors
            
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    **{k: v for k, v in response.headers.items()
                       if k.lower() not in ['content-length', 'transfer-encoding', 'connection']}
                }
            )
    
    except httpx.RequestError as e:
        print(f"ERROR: RequestError in proxy: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to orchestrator: {str(e)}")
    except Exception as e:
        print(f"ERROR: Exception in proxy: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)