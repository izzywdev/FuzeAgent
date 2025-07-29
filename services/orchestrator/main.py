from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from .agent_manager import AgentManager
from .task_queue import TaskQueue
from .context_service import ContextService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.agent_manager = AgentManager()
    app.state.task_queue = TaskQueue()
    app.state.context_service = ContextService()
    
    # Initialize IzzyAI CEO on startup
    await app.state.agent_manager.create_agent(
        name="IzzyAI",
        role="Digital CEO",
        type="executive",
        config={
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "tools": ["strategic_planning", "resource_allocation", "team_management"]
        }
    )
    
    yield
    
    # Shutdown
    await app.state.agent_manager.shutdown_all()

app = FastAPI(
    title="FuzeAgent Orchestrator",
    description="AI Team Orchestration Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "orchestrator"}

# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send agent updates to UI
            updates = await app.state.agent_manager.get_updates()
            await websocket.send_json(updates)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# Agent Management Endpoints
@app.post("/agents")
async def create_agent(agent_config: dict):
    """Create a new AI agent"""
    agent = await app.state.agent_manager.create_agent(**agent_config)
    return {"agent_id": agent.id, "status": "created"}

@app.get("/agents")
async def list_agents():
    """List all agents and their status"""
    return await app.state.agent_manager.list_agents()

@app.post("/agents/{agent_id}/tasks")
async def assign_task(agent_id: str, task: dict):
    """Assign a task to an agent"""
    task_id = await app.state.task_queue.assign_task(agent_id, task)
    return {"task_id": task_id, "status": "assigned"}

@app.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get detailed agent status"""
    return await app.state.agent_manager.get_agent_status(agent_id)

@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return await app.state.task_queue.list_tasks()

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    return await app.state.task_queue.get_task(task_id)

# Additional endpoints for UI support
@app.put("/tasks/{task_id}")
async def update_task(task_id: str, update_data: dict):
    """Update task status and result"""
    await app.state.task_queue.update_task_status(
        task_id=task_id,
        status=update_data.get('status'),
        result=update_data.get('result')
    )
    return {"status": "updated"}

@app.post("/context/interactions")
async def store_interaction(interaction_data: dict):
    """Store agent interaction"""
    interaction_id = await app.state.context_service.store_interaction(
        agent_id=interaction_data.get('agent_id'),
        content=interaction_data.get('content'),
        metadata=interaction_data.get('metadata', {})
    )
    return {"interaction_id": interaction_id}

@app.get("/context")
async def get_context(query: str, agent_id: str = None):
    """Get relevant context for a query"""
    context = await app.state.context_service.get_context(query, agent_id)
    return context

@app.get("/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, limit: int = 10):
    """Get agent memory"""
    memory = await app.state.context_service.get_agent_memory(agent_id, limit)
    return memory

@app.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Search knowledge base"""
    results = await app.state.context_service.search_knowledge(query, limit)
    return results