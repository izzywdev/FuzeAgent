import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_templates import AgentCategory, template_manager

# Simple in-memory storage for demonstration
agents_db = {}
tasks_db = {}
teams_db = {}
conversations_db = {}


# Initialize some mock data
def initialize_mock_data():
    # Create a default team
    default_team_id = str(uuid.uuid4())
    teams_db[default_team_id] = {
        "id": default_team_id,
        "name": "Default Team",
        "description": "Default team for agents",
        "organization_id": "1",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize mock data
    initialize_mock_data()

    # Startup - create IzzyAI CEO
    izzy_id = str(uuid.uuid4())
    agents_db[izzy_id] = {
        "id": izzy_id,
        "name": "IzzyAI",
        "role": "Digital CEO",
        "type": "executive",
        "status": "active",
        "config": {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "tools": ["strategic_planning", "resource_allocation", "team_management"],
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    print(f"✅ Created IzzyAI CEO with ID: {izzy_id}")

    yield

    # Shutdown
    print("🛑 Shutting down orchestrator")


app = FastAPI(
    title="FuzeAgent Orchestrator",
    description="AI Team Orchestration Platform - Simple Version",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "agents_count": len(agents_db),
        "tasks_count": len(tasks_db),
    }


# Agent Management Endpoints
@app.post("/agents")
async def create_agent(agent_config: dict):
    """Create a new AI agent"""
    agent_id = str(uuid.uuid4())

    agent = {
        "id": agent_id,
        "name": agent_config.get("name"),
        "role": agent_config.get("role"),
        "type": agent_config.get("type"),
        "status": "active",
        "config": agent_config.get("config", {}),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    agents_db[agent_id] = agent
    print(f"✅ Created agent: {agent['name']} ({agent['type']})")

    return {"agent_id": agent_id, "status": "created", "agent": agent}


@app.get("/agents")
async def list_agents():
    """List all agents and their status"""
    return list(agents_db.values())


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get specific agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_db[agent_id]


@app.post("/agents/{agent_id}/tasks")
async def assign_task(agent_id: str, task: dict):
    """Assign a task to an agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    task_id = str(uuid.uuid4())

    new_task = {
        "id": task_id,
        "title": task.get("title", "Untitled Task"),
        "description": task.get("description", ""),
        "type": task.get("type", "general"),
        "assigned_to": agent_id,
        "assigned_agent_name": agents_db[agent_id]["name"],
        "status": "pending",
        "priority": task.get("priority", 5),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
    }

    tasks_db[task_id] = new_task
    print(f"✅ Assigned task '{new_task['title']}' to {agents_db[agent_id]['name']}")

    return {"task_id": task_id, "status": "assigned", "task": new_task}


@app.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get detailed agent status"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agents_db[agent_id]
    agent_tasks = [
        task for task in tasks_db.values() if task["assigned_to"] == agent_id
    ]

    return {
        **agent,
        "tasks_count": len(agent_tasks),
        "pending_tasks": len([t for t in agent_tasks if t["status"] == "pending"]),
        "completed_tasks": len([t for t in agent_tasks if t["status"] == "completed"]),
    }


# Task Management
@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return list(tasks_db.values())


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]


@app.put("/tasks/{task_id}")
async def update_task(task_id: str, update_data: dict):
    """Update task status and result"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_db[task_id]

    if "status" in update_data:
        task["status"] = update_data["status"]
        if update_data["status"] == "completed":
            task["completed_at"] = datetime.now().isoformat()

    if "result" in update_data:
        task["result"] = update_data["result"]

    task["updated_at"] = datetime.now().isoformat()

    return {"status": "updated", "task": task}


# Context endpoints (simplified)
@app.post("/context/interactions")
async def store_interaction(interaction_data: dict):
    """Store agent interaction (simplified)"""
    interaction_id = str(uuid.uuid4())
    print(
        f"📝 Stored interaction for {interaction_data.get('agent_id')}: {interaction_data.get('content', '')[:50]}..."
    )
    return {"interaction_id": interaction_id}


@app.get("/context")
async def get_context(query: str, agent_id: str = None):
    """Get relevant context for a query (simplified)"""
    return {
        "similar_interactions": [],
        "recent_interactions": [],
        "relevant_code": "",
        "similar_features": "",
    }


@app.get("/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, limit: int = 10):
    """Get agent memory (simplified)"""
    return []


@app.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Search knowledge base (simplified)"""
    return []


# Agent Template Endpoints
@app.get("/templates")
async def list_templates(category: Optional[str] = None):
    """List all agent templates, optionally filtered by category"""
    try:
        if category:
            category_enum = AgentCategory(category)
            templates = template_manager.list_templates(category_enum)
        else:
            templates = template_manager.list_templates()
        return {"templates": templates}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/templates/categories")
async def list_template_categories():
    """List all available template categories"""
    return {"categories": template_manager.get_categories()}


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get specific template details"""
    try:
        template = template_manager.get_template(template_id)
        return template.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/agents/from-template")
async def create_agent_from_template(request: dict):
    """Create agent from template with optional customizations"""
    template_id = request.get("template_id")
    overrides = request.get("overrides", {})

    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required")

    try:
        # Validate overrides
        validation_errors = template_manager.validate_template_overrides(
            template_id, overrides
        )
        if validation_errors:
            raise HTTPException(
                status_code=400, detail={"validation_errors": validation_errors}
            )

        # Create agent configuration from template
        agent_config = template_manager.create_agent_from_template(
            template_id, overrides
        )

        # Create the agent using existing create_agent logic
        agent_id = str(uuid.uuid4())

        agent = {
            "id": agent_id,
            "name": agent_config.get("name"),
            "role": agent_config.get("role"),
            "type": agent_config.get("type"),
            "template_id": template_id,
            "status": "active",
            "config": agent_config.get("config", {}),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        agents_db[agent_id] = agent
        print(f"✅ Created agent from template: {agent['name']} ({template_id})")

        return {
            "agent_id": agent_id,
            "status": "created",
            "agent": agent,
            "template_id": template_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating agent from template: {str(e)}"
        )


# Demo endpoint to create sample agents
@app.post("/demo/create-sample-agents")
async def create_sample_agents():
    """Create sample agents for demonstration using templates"""
    sample_configs = [
        {"template_id": "react_developer", "overrides": {"name": "Frontend Dev 1"}},
        {"template_id": "python_developer", "overrides": {"name": "Backend Dev 1"}},
        {"template_id": "qa_engineer", "overrides": {"name": "QA Engineer 1"}},
    ]

    created_agents = []
    for config in sample_configs:
        try:
            result = await create_agent_from_template(config)
            created_agents.append(result)
        except Exception as e:
            print(f"Failed to create agent from template {config['template_id']}: {e}")
            # Fallback to manual creation for this demo
            fallback_agent = {
                "name": config["overrides"].get("name", "Demo Agent"),
                "role": "Demo Role",
                "type": "developer",
                "config": {
                    "goal": "Demo agent",
                    "tools": ["code_generation"],
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                },
            }
            result = await create_agent(fallback_agent)
            created_agents.append(result)

    return {"created_agents": created_agents}


# Missing endpoints that the UI expects
@app.get("/teams")
async def list_teams():
    """List all teams"""
    return list(teams_db.values())


@app.get("/agent-templates")
async def list_agent_templates():
    """Alternative endpoint for templates (UI compatibility)"""
    try:
        templates = template_manager.list_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_id}/conversations")
async def get_agent_conversations(agent_id: str):
    """Get agent conversations"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Return mock conversations for now
    agent_conversations = conversations_db.get(agent_id, [])
    return agent_conversations


@app.post("/agents/{agent_id}/conversations")
async def create_agent_conversation(agent_id: str, conversation_data: dict):
    """Create a new conversation for agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    conversation_id = str(uuid.uuid4())
    conversation = {
        "id": conversation_id,
        "agent_id": agent_id,
        "title": conversation_data.get("title", "New Conversation"),
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    if agent_id not in conversations_db:
        conversations_db[agent_id] = []

    conversations_db[agent_id].append(conversation)
    return conversation


@app.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str):
    """Get tasks for a specific agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_tasks = [
        task for task in tasks_db.values() if task["assigned_to"] == agent_id
    ]
    return agent_tasks


@app.get("/agents/{agent_id}/container/status")
async def get_agent_container_status(agent_id: str):
    """Get agent container status"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Mock container status
    return {
        "status": "running",
        "container_id": f"container_{agent_id[:8]}",
        "health": "healthy",
        "uptime": "5m30s",
        "memory_usage": "256MB",
        "cpu_usage": "15%",
    }


@app.get("/knowledge/agents/{agent_id}/documents")
async def get_agent_documents(agent_id: str):
    """Get agent knowledge documents"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Mock documents
    return {"documents": [], "total_count": 0, "agent_id": agent_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
