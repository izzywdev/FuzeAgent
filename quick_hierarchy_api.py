#!/usr/bin/env python3
"""
Quick script to add hierarchy API endpoints to the existing orchestrator
"""

import asyncio
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os

# Database connection
DATABASE_URL = "postgresql://postgres:J7hplO7vKnbUsKDAsxpe4t9C0@localhost:5434/ai_context"

app = FastAPI(title="FuzeAgent Hierarchy API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Database connection pool
db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

@app.on_event("startup")
async def startup_event():
    await get_db_pool()

@app.on_event("shutdown")
async def shutdown_event():
    if db_pool:
        await db_pool.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "hierarchy-api"}

@app.get("/organizations", response_model=List[Organization])
async def get_organizations():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id::text,
                name,
                description,
                settings,
                created_at::text,
                updated_at::text
            FROM organizations 
            ORDER BY created_at DESC
        """)
        return [Organization(**dict(row)) for row in rows]

@app.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        org_id = str(uuid.uuid4())
        row = await conn.fetchrow("""
            INSERT INTO organizations (id, name, description, settings)
            VALUES ($1, $2, $3, $4)
            RETURNING 
                id::text,
                name,
                description,
                settings,
                created_at::text,
                updated_at::text
        """, org_id, org_data.name, org_data.description, org_data.settings)
        
        return Organization(**dict(row))

@app.get("/organizations/{organization_id}", response_model=Organization)
async def get_organization(organization_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id::text,
                name,
                description,
                settings,
                created_at::text,
                updated_at::text
            FROM organizations 
            WHERE id = $1
        """, organization_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return Organization(**dict(row))

@app.get("/teams", response_model=List[Team])
async def get_teams(organization_id: Optional[str] = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if organization_id:
            rows = await conn.fetch("""
                SELECT 
                    id::text,
                    organization_id::text,
                    name,
                    description,
                    team_type,
                    settings,
                    created_at::text,
                    updated_at::text
                FROM teams 
                WHERE organization_id = $1
                ORDER BY created_at DESC
            """, organization_id)
        else:
            rows = await conn.fetch("""
                SELECT 
                    id::text,
                    organization_id::text,
                    name,
                    description,
                    team_type,
                    settings,
                    created_at::text,
                    updated_at::text
                FROM teams 
                ORDER BY created_at DESC
            """)
        
        return [Team(**dict(row)) for row in rows]

@app.post("/teams", response_model=Team)
async def create_team(team_data: TeamCreate):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
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
                id::text,
                organization_id::text,
                name,
                description,
                team_type,
                settings,
                created_at::text,
                updated_at::text
        """, team_id, team_data.organization_id, team_data.name, 
             team_data.description, team_data.team_type, team_data.settings)
        
        return Team(**dict(row))

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id::text,
                organization_id::text,
                name,
                description,
                team_type,
                settings,
                created_at::text,
                updated_at::text
            FROM teams 
            WHERE id = $1
        """, team_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return Team(**dict(row))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)