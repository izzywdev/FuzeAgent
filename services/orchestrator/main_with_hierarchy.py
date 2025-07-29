from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

from database import DatabaseManager
from models import (
    Organization, OrganizationCreate, OrganizationUpdate,
    Team, TeamCreate, TeamUpdate,
    Agent, AgentCreate, AgentUpdate,
    Task, TaskCreate, TaskUpdate,
    OrganizationWithTeams, TeamWithAgents, AgentWithTeam,
    CreateAgentFromTemplate, CreateCustomAgent
)
from agent_templates import template_manager, AgentCategory

# Default IDs for initial setup
DEFAULT_ORG_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_TEAM_ID = "550e8400-e29b-41d4-a716-446655440001"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize database
    await DatabaseManager.create_tables()
    print("🗄️ Database initialized")
    
    # Check if default organization exists
    try:
        org = await DatabaseManager.get_organization(DEFAULT_ORG_ID)
        if org:
            print(f"✅ Default organization exists: {org['name']}")
        else:
            print("⚠️ Default organization not found in database")
    except Exception as e:
        print(f"⚠️ Database connection issue: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down orchestrator")

app = FastAPI(
    title="FuzeAgent Orchestrator",
    description="AI Team Orchestration Platform with Organizations and Teams",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ORGANIZATION ENDPOINTS
# ============================================================================

@app.get("/organizations", response_model=List[Organization])
async def get_organizations():
    """Get all organizations"""
    try:
        orgs = await DatabaseManager.get_organizations()
        return orgs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organizations: {str(e)}")

@app.post("/organizations", response_model=Organization)
async def create_organization(org_data: OrganizationCreate):
    """Create a new organization"""
    try:
        org_id = await DatabaseManager.create_organization(
            name=org_data.name,
            description=org_data.description,
            settings=org_data.settings
        )
        
        org = await DatabaseManager.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=500, detail="Failed to retrieve created organization")
        
        return org
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")

@app.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(org_id: str):
    """Get organization by ID"""
    try:
        org = await DatabaseManager.get_organization(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organization: {str(e)}")

@app.put("/organizations/{org_id}", response_model=Organization)
async def update_organization(org_id: str, org_data: OrganizationUpdate):
    """Update organization"""
    try:
        # Convert to dict and remove None values
        update_data = {k: v for k, v in org_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
        success = await DatabaseManager.update_organization(org_id, **update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org = await DatabaseManager.get_organization(org_id)
        return org
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update organization: {str(e)}")

@app.delete("/organizations/{org_id}")
async def delete_organization(org_id: str):
    """Delete organization"""
    try:
        success = await DatabaseManager.delete_organization(org_id)
        if not success:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete organization: {str(e)}")

# ============================================================================
# TEAM ENDPOINTS
# ============================================================================

@app.get("/teams", response_model=List[Team])
async def get_teams(organization_id: Optional[str] = None):
    """Get teams, optionally filtered by organization"""
    try:
        teams = await DatabaseManager.get_teams(organization_id)
        return teams
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")

@app.post("/teams", response_model=Team)
async def create_team(team_data: TeamCreate):
    """Create a new team"""
    try:
        # Verify organization exists
        org = await DatabaseManager.get_organization(team_data.organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        team_id = await DatabaseManager.create_team(
            organization_id=team_data.organization_id,
            name=team_data.name,
            description=team_data.description,
            team_type=team_data.team_type,
            settings=team_data.settings
        )
        
        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=500, detail="Failed to retrieve created team")
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(team_id: str):
    """Get team by ID"""
    try:
        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")

@app.put("/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, team_data: TeamUpdate):
    """Update team"""
    try:
        update_data = {k: v for k, v in team_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")
        
        success = await DatabaseManager.update_team(team_id, **update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team = await DatabaseManager.get_team(team_id)
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update team: {str(e)}")

@app.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete team"""
    try:
        success = await DatabaseManager.delete_team(team_id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete team: {str(e)}")

# ============================================================================
# AGENT ENDPOINTS (Updated for Teams)
# ============================================================================

@app.get("/agents")
async def get_agents(team_id: Optional[str] = None):
    """Get all agents, optionally filtered by team"""
    try:
        agents = await DatabaseManager.get_agents(team_id)
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents: {str(e)}")

@app.post("/agents")
async def create_agent(agent_data: AgentCreate):
    """Create a custom agent"""
    try:
        # Verify team exists
        team = await DatabaseManager.get_team(agent_data.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        agent_id = await DatabaseManager.insert_agent(
            team_id=agent_data.team_id,
            name=agent_data.name,
            role=agent_data.role,
            type=agent_data.type,
            config=agent_data.config,
            template_id=agent_data.template_id
        )
        
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to retrieve created agent")
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

@app.post("/agents/from-template")
async def create_agent_from_template(template_data: CreateAgentFromTemplate):
    """Create agent from template"""
    try:
        template = template_manager.get_template(template_data.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Get team_id from overrides or use default
        if 'team_id' not in template_data.overrides:
            raise HTTPException(status_code=400, detail="team_id is required in overrides")
        
        team_id = template_data.overrides['team_id']
        
        # Verify team exists
        team = await DatabaseManager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Create agent config from template with overrides
        config = {
            "goal": template_data.overrides.get("goal", template.default_goal),
            "backstory": template_data.overrides.get("backstory", template.default_backstory),
            "model": template.model,
            "temperature": template_data.overrides.get("temperature", template.default_temperature),
            "tools": template.tools,
            "skills": template.skills
        }
        
        agent_id = await DatabaseManager.insert_agent(
            team_id=team_id,
            name=template_data.overrides.get("name", f"{template.name} Agent"),
            role=template.role,
            type=template.type,
            config=config,
            template_id=template.template_id
        )
        
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to retrieve created agent")
        
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent from template: {str(e)}")

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent by ID"""
    try:
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")

# ============================================================================
# TEMPLATE ENDPOINTS (Existing)
# ============================================================================

@app.get("/templates")
async def get_templates():
    """Get all agent templates"""
    templates = template_manager.get_all_templates()
    return {
        "templates": templates,
        "categories": [category.value for category in AgentCategory]
    }

@app.get("/templates/categories")
async def get_template_categories():
    """Get template categories"""
    return {"categories": [category.value for category in AgentCategory]}

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get specific template"""
    template = template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

# ============================================================================
# TASK ENDPOINTS (Updated for Team Context)
# ============================================================================

@app.get("/tasks")
async def get_tasks():
    """Get all tasks"""
    try:
        tasks = await DatabaseManager.get_tasks()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@app.post("/agents/{agent_id}/tasks")
async def assign_task_to_agent(agent_id: str, task_data: TaskCreate):
    """Assign a task to an agent"""
    try:
        # Verify agent exists
        agent = await DatabaseManager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        task_id = await DatabaseManager.insert_task(
            title=task_data.title,
            description=task_data.description,
            assigned_to=agent_id,
            created_by=task_data.created_by
        )
        
        return {"task_id": task_id, "message": "Task assigned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")

# ============================================================================
# DEMO/HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "message": "FuzeAgent Orchestrator API",
        "version": "2.0.0",
        "features": ["Organizations", "Teams", "Agents", "Templates", "Tasks"],
        "status": "running"
    }

@app.get("/demo")
async def demo_endpoint():
    """Demo endpoint with sample hierarchy"""
    try:
        # Get organizations with their teams and agents
        orgs = await DatabaseManager.get_organizations()
        
        if not orgs:
            return {"message": "No organizations found. Database may need initialization."}
        
        demo_data = {
            "organizations": len(orgs),
            "sample_org": orgs[0] if orgs else None,
            "message": "FuzeAgent Orchestrator running with hierarchical structure"
        }
        
        return demo_data
    except Exception as e:
        return {"error": f"Demo endpoint failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)