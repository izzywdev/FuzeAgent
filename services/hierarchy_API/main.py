#!/usr/bin/env python3
"""
FuzeAgent Hierarchy API

This API handles organizations, teams, and agents hierarchical structure for the FuzeAgent UI.
It works directly with the database and provides endpoints for the React UI.
"""

from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ai_context")

# FastAPI app
app = FastAPI(
    title="FuzeAgent Hierarchy API",
    description="API for managing organizations, teams, and agents hierarchical structure",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models

# Organizations
class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Organization(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    team_count: Optional[int] = None
    agent_count: Optional[int] = None

# Teams
class TeamCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None
    team_type: Optional[str] = "general"
    settings: Optional[Dict[str, Any]] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_type: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Team(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    team_type: str = "general"
    settings: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    organization_name: Optional[str] = None
    agent_count: Optional[int] = None
    members: List[str] = []
    status: str = 'active'
    color: Optional[str] = None

# Agents
class AgentConfig(BaseModel):
    goal: Optional[str] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: List[str] = []
    skills: List[str] = []
    model: Optional[str] = None
    temperature: Optional[float] = None

class Agent(BaseModel):
    id: str
    team_id: str
    name: str
    role: str
    type: str
    template_id: Optional[str] = None
    status: str = 'active'
    config: AgentConfig = AgentConfig()
    created_at: datetime
    updated_at: datetime
    team_name: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None

# Goals models
class Milestone(BaseModel):
    id: Optional[str] = None
    title: str
    status: str = 'planning'
    target_date: Optional[datetime] = None

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'medium'
    status: str = 'planning'
    target_completion_date: Optional[datetime] = None
    assigned_teams: List[str] = []
    milestones: List[Milestone] = []

class Goal(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    target_completion_date: Optional[datetime] = None
    progress_percentage: int = 0
    assigned_teams: List[str] = []
    milestones: List[Milestone] = []
    created_at: datetime
    updated_at: datetime

# Database helper functions
async def get_db_connection():
    """Get database connection"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

async def close_db_connection(conn):
    """Close database connection"""
    if conn:
        await conn.close()

# Organizations endpoints

@app.get("/organizations", response_model=List[Organization])
async def get_organizations():
    """Get all organizations with team and agent counts"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            o.id,
            o.name,
            o.description,
            o.settings,
            o.created_at,
            o.updated_at,
            COUNT(DISTINCT t.id) as team_count,
            COUNT(DISTINCT a.id) as agent_count
        FROM organizations o
        LEFT JOIN teams t ON o.id = t.organization_id
        LEFT JOIN agents a ON t.id = a.team_id
        GROUP BY o.id, o.name, o.description, o.settings, o.created_at, o.updated_at
        ORDER BY o.created_at DESC
        """
        
        rows = await conn.fetch(query)
        organizations = []
        
        for row in rows:
            # PostgreSQL returns JSONB as string, parse it
            settings = row['settings'] if isinstance(row['settings'], dict) else {}
            
            org = Organization(
                id=str(row['id']),
                name=row['name'],
                description=row['description'],
                settings=settings,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                team_count=row['team_count'],
                agent_count=row['agent_count']
            )
            organizations.append(org)
        
        return organizations
        
    except Exception as e:
        logger.error(f"Error fetching organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(org_id: str):
    """Get a specific organization by ID"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            o.id,
            o.name,
            o.description,
            o.settings,
            o.created_at,
            o.updated_at,
            COUNT(DISTINCT t.id) as team_count,
            COUNT(DISTINCT a.id) as agent_count
        FROM organizations o
        LEFT JOIN teams t ON o.id = t.organization_id
        LEFT JOIN agents a ON t.id = a.team_id
        WHERE o.id = $1
        GROUP BY o.id, o.name, o.description, o.settings, o.created_at, o.updated_at
        """
        
        row = await conn.fetchrow(query, uuid.UUID(org_id))
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        settings = row['settings'] if isinstance(row['settings'], dict) else {}
        
        return Organization(
            id=str(row['id']),
            name=row['name'],
            description=row['description'],
            settings=settings,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            team_count=row['team_count'],
            agent_count=row['agent_count']
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    except Exception as e:
        logger.error(f"Error fetching organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate):
    """Create a new organization"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = """
        INSERT INTO organizations (name, description, settings)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, settings, created_at, updated_at
        """
        
        # Use default empty dict if no settings provided
        settings = org_data.settings if org_data.settings is not None else {}
        
        row = await conn.fetchrow(query, org_data.name, org_data.description, settings)
        
        return Organization(
            id=str(row['id']),
            name=row['name'],
            description=row['description'],
            settings=row['settings'] if isinstance(row['settings'], dict) else {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            team_count=0,
            agent_count=0
        )
        
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.put("/organizations/{org_id}", response_model=Organization)
async def update_organization(org_id: str, org_data: OrganizationUpdate):
    """Update an existing organization"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        if org_data.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(org_data.name)
            param_count += 1
            
        if org_data.description is not None:
            update_fields.append(f"description = ${param_count}")
            values.append(org_data.description)
            param_count += 1
            
        if org_data.settings is not None:
            update_fields.append(f"settings = ${param_count}")
            values.append(org_data.settings)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append(f"updated_at = NOW()")
        values.append(uuid.UUID(org_id))
        
        query = f"""
        UPDATE organizations 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, name, description, settings, created_at, updated_at
        """
        
        row = await conn.fetchrow(query, *values)
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return Organization(
            id=str(row['id']),
            name=row['name'],
            description=row['description'],
            settings=row['settings'] if isinstance(row['settings'], dict) else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.delete("/organizations/{org_id}")
async def delete_organization(org_id: str):
    """Delete an organization"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = "DELETE FROM organizations WHERE id = $1 RETURNING id"
        row = await conn.fetchrow(query, uuid.UUID(org_id))
        
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return {"success": True}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    except Exception as e:
        logger.error(f"Error deleting organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Teams endpoints

@app.get("/teams", response_model=List[Team])
async def get_teams(organization_id: Optional[str] = Query(None)):
    """Get all teams, optionally filtered by organization"""
    conn = None
    try:
        conn = await get_db_connection()
        
        if organization_id:
            query = """
            SELECT 
                t.id,
                t.organization_id,
                t.name,
                t.description,
                t.team_type,
                t.settings,
                t.created_at,
                t.updated_at,
                o.name as organization_name,
                COUNT(a.id) as agent_count,
                COALESCE(array_remove(array_agg(a.name), NULL), '{}') as member_names
            FROM teams t
            LEFT JOIN organizations o ON t.organization_id = o.id
            LEFT JOIN agents a ON t.id = a.team_id
            WHERE t.organization_id = $1
            GROUP BY t.id, t.organization_id, t.name, t.description, t.team_type, t.settings, t.created_at, t.updated_at, o.name
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query, uuid.UUID(organization_id))
        else:
            query = """
            SELECT 
                t.id,
                t.organization_id,
                t.name,
                t.description,
                t.team_type,
                t.settings,
                t.created_at,
                t.updated_at,
                o.name as organization_name,
                COUNT(a.id) as agent_count,
                COALESCE(array_remove(array_agg(a.name), NULL), '{}') as member_names
            FROM teams t
            LEFT JOIN organizations o ON t.organization_id = o.id
            LEFT JOIN agents a ON t.id = a.team_id
            GROUP BY t.id, t.organization_id, t.name, t.description, t.team_type, t.settings, t.created_at, t.updated_at, o.name
            ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query)
        
        teams = []
        for row in rows:
            settings = row['settings'] if isinstance(row['settings'], dict) else {}

            member_names = row['member_names'] if 'member_names' in row else []
            if member_names is None:
                member_names = []
            
            team = Team(
                id=str(row['id']),
                organization_id=str(row['organization_id']),
                name=row['name'],
                description=row['description'],
                team_type=row['team_type'],
                settings=settings,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                organization_name=row['organization_name'],
                agent_count=row['agent_count'],
                members=[m for m in (member_names or []) if isinstance(m, str)],
                status='active',
                color=(settings.get('color') if isinstance(settings, dict) and isinstance(settings.get('color'), str) else '#6b7280')
            )
            teams.append(team)
        
        return teams
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    """Get a specific team by ID"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = """
        SELECT 
            t.id,
            t.organization_id,
            t.name,
            t.description,
            t.team_type,
            t.settings,
            t.created_at,
            t.updated_at,
            o.name as organization_name,
            COUNT(a.id) as agent_count,
            COALESCE(array_remove(array_agg(a.name), NULL), '{}') as member_names
        FROM teams t
        LEFT JOIN organizations o ON t.organization_id = o.id
        LEFT JOIN agents a ON t.id = a.team_id
        WHERE t.id = $1
        GROUP BY t.id, t.organization_id, t.name, t.description, t.team_type, t.settings, t.created_at, t.updated_at, o.name
        """
        
        row = await conn.fetchrow(query, uuid.UUID(team_id))
        if not row:
            raise HTTPException(status_code=404, detail="Team not found")
        
        settings = row['settings'] if isinstance(row['settings'], dict) else {}
        
        member_names = row['member_names'] if 'member_names' in row else []
        if member_names is None:
            member_names = []

        return Team(
            id=str(row['id']),
            organization_id=str(row['organization_id']),
            name=row['name'],
            description=row['description'],
            team_type=row['team_type'],
            settings=settings,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            organization_name=row['organization_name'],
            agent_count=row['agent_count'],
            members=[m for m in (member_names or []) if isinstance(m, str)],
            status='active',
            color=(settings.get('color') if isinstance(settings, dict) and isinstance(settings.get('color'), str) else '#6b7280')
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error fetching team: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.post("/teams", response_model=Team)
async def create_team(team_data: TeamCreate):
    """Create a new team"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Check if organization exists
        org_check = await conn.fetchrow(
            "SELECT id FROM organizations WHERE id = $1",
            uuid.UUID(team_data.organization_id)
        )
        if not org_check:
            raise HTTPException(status_code=400, detail="Organization not found")
        
        query = """
        INSERT INTO teams (organization_id, name, description, team_type, settings)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id, organization_id, name, description, team_type, settings, created_at, updated_at
        """
        
        settings = team_data.settings if team_data.settings is not None else {}
        
        import json
        row = await conn.fetchrow(
            query,
            uuid.UUID(team_data.organization_id),
            team_data.name,
            team_data.description,
            team_data.team_type,
            json.dumps(settings)
        )
        
        color = settings.get('color') if isinstance(settings, dict) and isinstance(settings.get('color'), str) else '#6b7280'
        return Team(
            id=str(row['id']),
            organization_id=str(row['organization_id']),
            name=row['name'],
            description=row['description'],
            team_type=row['team_type'],
            settings=row['settings'] if isinstance(row['settings'], dict) else {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            agent_count=0,
            members=[],
            status='active',
            color=color
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format")
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.put("/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, team_data: TeamUpdate):
    """Update an existing team"""
    conn = None
    try:
        conn = await get_db_connection()
        
        # Build dynamic update query
        update_fields = []
        values = []
        param_count = 1
        
        if team_data.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(team_data.name)
            param_count += 1
            
        if team_data.description is not None:
            update_fields.append(f"description = ${param_count}")
            values.append(team_data.description)
            param_count += 1
            
        if team_data.team_type is not None:
            update_fields.append(f"team_type = ${param_count}")
            values.append(team_data.team_type)
            param_count += 1
            
        if team_data.settings is not None:
            update_fields.append(f"settings = ${param_count}")
            values.append(team_data.settings)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append(f"updated_at = NOW()")
        values.append(uuid.UUID(team_id))
        
        query = f"""
        UPDATE teams 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, organization_id, name, description, team_type, settings, created_at, updated_at
        """
        
        row = await conn.fetchrow(query, *values)
        if not row:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return Team(
            id=str(row['id']),
            organization_id=str(row['organization_id']),
            name=row['name'],
            description=row['description'],
            team_type=row['team_type'],
            settings=row['settings'] if isinstance(row['settings'], dict) else {},
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error updating team: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete a team"""
    conn = None
    try:
        conn = await get_db_connection()
        
        query = "DELETE FROM teams WHERE id = $1 RETURNING id"
        row = await conn.fetchrow(query, uuid.UUID(team_id))
        
        if not row:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {"success": True}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Agents endpoints

@app.get("/agents", response_model=List[Agent])
async def get_agents(team_id: Optional[str] = Query(None)):
    """Get all agents, optionally filtered by team"""
    conn = None
    try:
        conn = await get_db_connection()
        
        if team_id:
            query = """
            SELECT 
                a.id,
                a.team_id,
                a.name,
                a.role,
                a.type,
                a.status,
                a.config,
                a.template_id,
                a.created_at,
                a.updated_at,
                t.name as team_name,
                t.organization_id,
                o.name as organization_name
            FROM agents a
            LEFT JOIN teams t ON a.team_id = t.id
            LEFT JOIN organizations o ON t.organization_id = o.id
            WHERE a.team_id = $1
            ORDER BY a.created_at DESC
            """
            rows = await conn.fetch(query, uuid.UUID(team_id))
        else:
            query = """
            SELECT 
                a.id,
                a.team_id,
                a.name,
                a.role,
                a.type,
                a.status,
                a.config,
                a.template_id,
                a.created_at,
                a.updated_at,
                t.name as team_name,
                t.organization_id,
                o.name as organization_name
            FROM agents a
            LEFT JOIN teams t ON a.team_id = t.id
            LEFT JOIN organizations o ON t.organization_id = o.id
            ORDER BY a.created_at DESC
            """
            rows = await conn.fetch(query)
        
        agents = []
        for row in rows:
            config_data = row['config'] if isinstance(row['config'], dict) else {}
            
            config = AgentConfig(
                goal=config_data.get('goal'),
                backstory=config_data.get('backstory'),
                system_prompt=config_data.get('system_prompt'),
                tools=config_data.get('tools', []),
                skills=config_data.get('skills', []),
                model=config_data.get('model'),
                temperature=config_data.get('temperature')
            )
            
            agent = Agent(
                id=str(row['id']),
                team_id=str(row['team_id']),
                name=row['name'],
                role=row['role'],
                type=row['type'],
                status=row['status'],
                config=config,
                template_id=str(row['template_id']) if row['template_id'] else None,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                team_name=row['team_name'],
                organization_id=str(row['organization_id']) if row['organization_id'] else None,
                organization_name=row['organization_name']
            )
            agents.append(agent)
        
        return agents
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Agent detail endpoints required by UI
@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    conn = None
    try:
        conn = await get_db_connection()
        row = await conn.fetchrow(
            """
            SELECT a.id, a.team_id, a.name, a.role, a.type, a.status, a.config, a.template_id,
                   a.created_at, a.updated_at,
                   t.name as team_name, t.organization_id,
                   o.name as organization_name
            FROM agents a
            LEFT JOIN teams t ON a.team_id = t.id
            LEFT JOIN organizations o ON t.organization_id = o.id
            WHERE a.id = $1
            """,
            uuid.UUID(agent_id)
        )
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        config_data = row['config'] if isinstance(row['config'], dict) else {}
        return Agent(
            id=str(row['id']),
            team_id=str(row['team_id']),
            name=row['name'],
            role=row['role'],
            type=row['type'],
            status=row['status'],
            config=AgentConfig(
                goal=config_data.get('goal'),
                backstory=config_data.get('backstory'),
                system_prompt=config_data.get('system_prompt'),
                tools=config_data.get('tools', []),
                skills=config_data.get('skills', []),
                model=config_data.get('model'),
                temperature=config_data.get('temperature')
            ),
            template_id=str(row['template_id']) if row['template_id'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            team_name=row['team_name'],
            organization_id=str(row['organization_id']) if row['organization_id'] else None,
            organization_name=row['organization_name']
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error(f"Error fetching agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, title, description, status, assigned_to, created_at, updated_at
            FROM tasks
            WHERE assigned_to = $1
            ORDER BY created_at DESC
            """,
            uuid.UUID(agent_id)
        )
        return [
            {
                'id': str(r['id']),
                'title': r['title'],
                'description': r['description'],
                'status': r['status'],
                'assigned_to': str(r['assigned_to']) if r['assigned_to'] else None,
                'created_at': r['created_at'].isoformat(),
                'updated_at': r['updated_at'].isoformat(),
            }
            for r in rows
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error(f"Error fetching agent tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.get("/agents/{agent_id}/conversations")
async def get_agent_conversations(agent_id: str):
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch(
            """
            SELECT id, agent_id, session_id, metadata, created_at, updated_at
            FROM agent_conversations
            WHERE agent_id = $1
            ORDER BY created_at DESC
            """,
            uuid.UUID(agent_id)
        )
        # UI expects an array; we return minimal structure
        return [
            {
                'id': str(r['id']),
                'agent_id': str(r['agent_id']),
                'session_id': str(r['session_id']),
                'messages': [],
                'created_at': r['created_at'].isoformat(),
                'updated_at': r['updated_at'].isoformat(),
            }
            for r in rows
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        logger.error(f"Error fetching agent conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.post("/agents/{agent_id}/conversations")
async def create_agent_conversation(agent_id: str, conversation_data: Dict[str, Any]):
    # Mock endpoint for UI compatibility - create new conversation for agent
    try:
        # Create mock conversation
        conversation = {
            "id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()),
            "title": conversation_data.get('title', 'New Conversation'),
            "status": "active",
            "metadata": conversation_data.get('metadata', {}),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        return {
            "success": True,
            "message": "Conversation created successfully",
            "conversation": conversation
        }
        
    except Exception as e:
        logger.error(f"Error creating agent conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}/container/status")
async def get_agent_container_status(agent_id: str):
    # Mock container status for UI compatibility
    return {
        'status': 'not_deployed',
        'container_id': None,
        'image': None,
        'created_at': None,
        'last_health_check': None
    }

@app.post("/agents/{agent_id}/container/start")
async def start_agent_container(agent_id: str):
    # Mock container start endpoint for UI compatibility
    return {
        "success": True,
        "message": "Container start initiated",
        "container_id": f"container-{agent_id[:8]}",
        "status": "starting"
    }

@app.post("/agents/{agent_id}/container/stop")
async def stop_agent_container(agent_id: str):
    # Mock container stop endpoint for UI compatibility
    return {
        "success": True,
        "message": "Container stop initiated",
        "container_id": f"container-{agent_id[:8]}",
        "status": "stopping"
    }

@app.post("/agents/{agent_id}/container/restart")
async def restart_agent_container(agent_id: str):
    # Mock container restart endpoint for UI compatibility
    return {
        "success": True,
        "message": "Container restart initiated",
        "container_id": f"container-{agent_id[:8]}",
        "status": "restarting"
    }

@app.get("/agents/{agent_id}/container/logs")
async def get_agent_container_logs(agent_id: str):
    # Mock endpoint for UI compatibility - get agent container logs
    try:
        # Return sample log entries
        sample_logs = [
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO",
                "message": f"Agent {agent_id} container started successfully",
                "source": "container"
            },
            {
                "timestamp": datetime.utcnow().isoformat() + "Z", 
                "level": "INFO",
                "message": "Initializing agent capabilities...",
                "source": "agent"
            },
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "INFO", 
                "message": "Agent ready to receive tasks",
                "source": "agent"
            }
        ]
        
        return {
            "success": True,
            "logs": sample_logs,
            "total_lines": len(sample_logs)
        }
    except Exception as e:
        logger.error(f"Error fetching agent container logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/container/create")
async def create_agent_container(agent_id: str, container_config: Dict[str, Any] = None):
    # Mock container creation endpoint for UI compatibility
    return {
        "success": True,
        "message": "Container created successfully",
        "container": {
            "id": f"container-{agent_id[:8]}",
            "name": f"agent-{agent_id[:8]}",
            "image": "fuzeagent/agent:latest",
            "status": "created",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    }

@app.get("/knowledge/agents/{agent_id}/documents")
async def get_agent_knowledge_documents(agent_id: str):
    # Mock documents list for UI compatibility
    return []

@app.post("/knowledge/agents/{agent_id}/url")
async def add_agent_knowledge_url(agent_id: str, url_data: Dict[str, Any]):
    # Mock endpoint for UI compatibility - add URL to agent knowledge base
    try:
        # Basic URL validation
        url = url_data.get('url', '')
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Mock successful response
        return {
            "success": True,
            "message": "URL added to agent knowledge base",
            "document": {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "url": url,
                "title": url_data.get('title', url),
                "description": url_data.get('description', ''),
                "type": "url",
                "status": "processing",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        logger.error(f"Error adding URL to agent knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/agents/{agent_id}/documents")
async def upload_agent_knowledge_documents(
    agent_id: str,
    files: List[UploadFile] = File(...),
):
    # Mock endpoint for UI compatibility - upload documents to agent knowledge base
    try:
        uploaded_documents = []
        
        for file in files:
            # Basic file validation
            if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(status_code=413, detail=f"File {file.filename} is too large")
            
            # Create mock document entry
            document = {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "filename": file.filename,
                "title": file.filename.rsplit('.', 1)[0] if file.filename else "Untitled",
                "type": "document",
                "status": "processing",
                "size": file.size or 0,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            uploaded_documents.append(document)
        
        return {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_documents)} document(s)",
            "documents": uploaded_documents
        }
        
    except Exception as e:
        logger.error(f"Error uploading agent knowledge documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/agents/{agent_id}/documents/{doc_id}/content")
async def get_agent_knowledge_document_content(agent_id: str, doc_id: str):
    # Mock endpoint for UI compatibility - get document content
    return {
        "content": "Mock document content for demonstration purposes.",
        "title": "Document Title",
        "type": "text/plain"
    }

@app.delete("/knowledge/agents/{agent_id}/documents/{doc_id}")
async def delete_agent_knowledge_document(agent_id: str, doc_id: str):
    # Mock endpoint for UI compatibility - delete knowledge document
    return {
        "success": True,
        "message": "Document deleted from knowledge base"
    }

# Organization Knowledge Endpoints
@app.get("/knowledge/organizations/{org_id}/documents")
async def get_organization_knowledge_documents(org_id: str):
    # Mock documents list for UI compatibility
    return []

@app.post("/knowledge/organizations/{org_id}/documents")
async def upload_organization_knowledge_documents(org_id: str):
    # Mock endpoint for UI compatibility - upload documents to organization knowledge base
    return {
        "success": True,
        "message": "Documents uploaded to organization knowledge base",
        "documents": [{
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "filename": "org_document.pdf",
            "title": "Organization Document",
            "type": "document",
            "status": "processing",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }]
    }

@app.post("/knowledge/organizations/{org_id}/url")
async def add_organization_knowledge_url(org_id: str, url_data: Dict[str, Any]):
    # Mock endpoint for UI compatibility - add URL to organization knowledge base
    try:
        # Basic URL validation
        url = url_data.get('url', '')
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Mock successful response
        return {
            "success": True,
            "message": "URL added to organization knowledge base",
            "document": {
                "id": str(uuid.uuid4()),
                "organization_id": org_id,
                "url": url,
                "title": url_data.get('title', url),
                "description": url_data.get('description', ''),
                "type": "url",
                "status": "processing",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        logger.error(f"Error adding URL to organization knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge/organizations/{org_id}/documents/{doc_id}/content")
async def get_organization_knowledge_document_content(org_id: str, doc_id: str):
    # Mock endpoint for UI compatibility - get organization document content
    return {
        "content": "Mock organization document content for demonstration purposes.",
        "title": "Organization Document Title",
        "type": "text/plain"
    }

@app.delete("/knowledge/organizations/{org_id}/documents/{doc_id}")
async def delete_organization_knowledge_document(org_id: str, doc_id: str):
    # Mock endpoint for UI compatibility - delete organization knowledge document
    return {
        "success": True,
        "message": "Document deleted from organization knowledge base"
    }

# General Knowledge Stats Endpoint
@app.get("/knowledge/stats")
async def get_knowledge_stats():
    # Mock endpoint for knowledge statistics
    return {
        "totalDocuments": 0,
        "recentDocuments": []
    }

# Lightweight templates endpoint for UI (if orchestrator isn't present)
@app.get("/agent-templates")
async def get_agent_templates():
    return {
        "templates": [
            {
                "template_id": "react_developer",
                "name": "React Developer",
                "category": "developer",
                "description": "Frontend developer specialized in React and TypeScript",
                "system_prompt": "",
                "default_goal": "Build responsive and performant React applications",
                "default_backstory": "Experienced frontend developer",
                "tools": ["code_generation", "code_review", "debugging", "testing"],
                "skills": ["react", "typescript"],
                "default_model": "claude-sonnet-4-20250514",
                "default_temperature": 0.7,
                "customizable_fields": ["name", "goal", "backstory", "temperature"]
            }
        ]
    }

# Create agent (fallback to insert into agents table if orchestrator isn't used)
@app.post("/agents", response_model=Agent)
async def create_agent(agent_data: Dict[str, Any]):
    conn = None
    try:
        conn = await get_db_connection()
        # minimal required fields
        team_id = agent_data.get("team_id")
        name = agent_data.get("name")
        role = agent_data.get("role", "Agent")
        type_ = agent_data.get("type", "general")
        status = "active"
        config = agent_data.get("config", {})
        if not team_id or not name:
            raise HTTPException(status_code=400, detail="team_id and name are required")
        import json
        row = await conn.fetchrow(
            """
            INSERT INTO agents (team_id, name, role, type, status, config)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING id, team_id, name, role, type, status, config, template_id, created_at, updated_at
            """,
            uuid.UUID(team_id), name, role, type_, status, json.dumps(config)
        )
        # join info
        team_row = await conn.fetchrow("SELECT name, organization_id FROM teams WHERE id = $1", row["team_id"])
        org_name = None
        if team_row and team_row["organization_id"]:
            org_name = await conn.fetchval("SELECT name FROM organizations WHERE id = $1", team_row["organization_id"]) 
        config_data = row['config'] if isinstance(row['config'], dict) else {}
        return Agent(
            id=str(row['id']),
            team_id=str(row['team_id']),
            name=row['name'],
            role=row['role'],
            type=row['type'],
            status=row['status'],
            config=AgentConfig(
                goal=config_data.get('goal'),
                backstory=config_data.get('backstory'),
                system_prompt=config_data.get('system_prompt'),
                tools=config_data.get('tools', []),
                skills=config_data.get('skills', []),
                model=config_data.get('model'),
                temperature=config_data.get('temperature')
            ),
            template_id=str(row['template_id']) if row['template_id'] else None,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            team_name=team_row['name'] if team_row else None,
            organization_id=str(team_row['organization_id']) if team_row and team_row['organization_id'] else None,
            organization_name=org_name
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IDs format")
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Goals endpoints
async def _resolve_org_uuid(conn, org_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(org_id)
    except Exception:
        # Fallback: if numeric '1' is used by UI, take the first organization
        row = await conn.fetchrow("SELECT id FROM organizations ORDER BY created_at LIMIT 1")
        if not row:
            raise HTTPException(status_code=404, detail="No organizations found")
        return row['id']

@app.get("/organizations/{org_id}/goals", response_model=List[Goal])
async def get_goals(org_id: str):
    conn = None
    try:
        conn = await get_db_connection()
        org_uuid = await _resolve_org_uuid(conn, org_id)
        rows = await conn.fetch(
            """
            SELECT g.id, g.title, g.description, g.priority, g.status, g.target_completion_date,
                   g.progress_percentage, g.assigned_teams, g.created_at, g.updated_at
            FROM goals g
            WHERE g.organization_id = $1
            ORDER BY g.created_at DESC
            """,
            org_uuid
        )
        goals: List[Goal] = []
        for row in rows:
            milestone_rows = await conn.fetch(
                "SELECT id, title, status, target_date FROM goal_milestones WHERE goal_id = $1 ORDER BY created_at",
                row['id']
            )
            milestones = [Milestone(id=str(m['id']), title=m['title'], status=m['status'], target_date=m['target_date']) for m in milestone_rows]
            assigned_teams = list(row['assigned_teams']) if isinstance(row['assigned_teams'], list) else []
            goals.append(Goal(
                id=str(row['id']),
                title=row['title'],
                description=row['description'],
                priority=row['priority'],
                status=row['status'],
                target_completion_date=row['target_completion_date'],
                progress_percentage=row['progress_percentage'],
                assigned_teams=assigned_teams,
                milestones=milestones,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        return goals
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.post("/organizations/{org_id}/goals", response_model=Goal)
async def create_goal(org_id: str, goal: GoalCreate):
    conn = None
    try:
        conn = await get_db_connection()
        org_uuid = await _resolve_org_uuid(conn, org_id)
        row = await conn.fetchrow(
            """
            INSERT INTO goals (organization_id, title, description, priority, status, target_completion_date,
                               progress_percentage, assigned_teams)
            VALUES ($1, $2, $3, $4, $5, $6, 0, $7)
            RETURNING id, title, description, priority, status, target_completion_date, progress_percentage, assigned_teams, created_at, updated_at
            """,
            org_uuid,
            goal.title,
            goal.description,
            goal.priority,
            goal.status,
            goal.target_completion_date,
            goal.assigned_teams if goal.assigned_teams else []
        )
        goal_id = row['id']
        # insert milestones
        milestones: List[Milestone] = []
        for ms in goal.milestones:
            ms_row = await conn.fetchrow(
                """
                INSERT INTO goal_milestones (goal_id, title, status, target_date)
                VALUES ($1, $2, $3, $4)
                RETURNING id, title, status, target_date
                """,
                goal_id, ms.title, ms.status, ms.target_date
            )
            milestones.append(Milestone(id=str(ms_row['id']), title=ms_row['title'], status=ms_row['status'], target_date=ms_row['target_date']))
        assigned_teams = list(row['assigned_teams']) if isinstance(row['assigned_teams'], list) else []
        return Goal(
            id=str(row['id']),
            title=row['title'],
            description=row['description'],
            priority=row['priority'],
            status=row['status'],
            target_completion_date=row['target_completion_date'],
            progress_percentage=row['progress_percentage'],
            assigned_teams=assigned_teams,
            milestones=milestones,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = await get_db_connection()
        await conn.fetchrow("SELECT 1")
        await close_db_connection(conn)
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# Hierarchy visualization for UI
@app.get("/hierarchy/visualization")
async def hierarchy_visualization():
    conn = None
    try:
        conn = await get_db_connection()
        org_rows = await conn.fetch("SELECT id, name, description, settings FROM organizations ORDER BY created_at")
        team_rows = await conn.fetch("""
            SELECT t.id, t.organization_id, t.name, t.description, t.team_type, t.settings
            FROM teams t ORDER BY t.created_at
        """)
        agent_rows = await conn.fetch("""
            SELECT a.id, a.team_id, a.name, a.role, a.type, a.status
            FROM agents a ORDER BY a.created_at
        """)

        nodes = []
        edges = []
        # organizations
        for o in org_rows:
            nodes.append({
                "id": f"org-{o['id']}",
                "type": "organization",
                "position": {"x": 0, "y": 0},  # UI will fitView
                "data": {
                    "label": o['name'],
                    "description": o['description'],
                    "settings": o['settings'] if isinstance(o['settings'], dict) else {}
                }
            })
        # teams
        for t in team_rows:
            nodes.append({
                "id": f"team-{t['id']}",
                "type": "team",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": t['name'],
                    "description": t['description'],
                    "type": t['team_type']
                }
            })
            edges.append({
                "id": f"org-{t['organization_id']}-team-{t['id']}",
                "source": f"org-{t['organization_id']}",
                "target": f"team-{t['id']}",
                "type": "smoothstep"
            })
        # agents
        for a in agent_rows:
            nodes.append({
                "id": f"agent-{a['id']}",
                "type": "agent",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": a['name'],
                    "role": a['role'],
                    "type": a['type'],
                    "status": a['status'],
                    "style": {}
                }
            })
            edges.append({
                "id": f"team-{a['team_id']}-agent-{a['id']}",
                "source": f"team-{a['team_id']}",
                "target": f"agent-{a['id']}",
                "type": "smoothstep"
            })

        metadata = {
            "total_organizations": len(org_rows),
            "total_teams": len(team_rows),
            "total_agents": len(agent_rows),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        return {"nodes": nodes, "edges": edges, "metadata": metadata}
    except Exception as e:
        logger.error(f"Error building hierarchy visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

@app.get("/hierarchy/stats")
async def hierarchy_stats():
    conn = None
    try:
        conn = await get_db_connection()
        org_rows = await conn.fetch("SELECT id, name FROM organizations")
        team_rows = await conn.fetch("SELECT id, organization_id, team_type FROM teams")
        agent_rows = await conn.fetch("SELECT id, type, team_id FROM agents")
        org_id_to_name = {str(o['id']): o['name'] for o in org_rows}

        by_org = {}
        for o in org_rows:
            by_org[str(o['id'])] = {
                "id": str(o['id']),
                "name": o['name'],
                "teams": 0,
                "agents": 0,
                "teams_by_type": {},
                "agents_by_type": {}
            }
        for t in team_rows:
            oid = str(t['organization_id'])
            rec = by_org.get(oid)
            if rec:
                rec['teams'] += 1
                rec['teams_by_type'][t['team_type']] = rec['teams_by_type'].get(t['team_type'], 0) + 1
        for a in agent_rows:
            # map agent to its org by team
            team = next((tr for tr in team_rows if tr['id'] == a['team_id']), None)
            if team:
                oid = str(team['organization_id'])
                rec = by_org.get(oid)
                if rec:
                    rec['agents'] += 1
                    rec['agents_by_type'][a['type']] = rec['agents_by_type'].get(a['type'], 0) + 1

        agent_types = {}
        for a in agent_rows:
            agent_types[a['type']] = agent_types.get(a['type'], 0) + 1
        team_types = {}
        for t in team_rows:
            team_types[t['team_type']] = team_types.get(t['team_type'], 0) + 1

        return {
            "organizations": len(org_rows),
            "teams": len(team_rows),
            "agents": len(agent_rows),
            "by_organization": list(by_org.values()),
            "agent_types": agent_types,
            "team_types": team_types
        }
    except Exception as e:
        logger.error(f"Error building hierarchy stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await close_db_connection(conn)

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)