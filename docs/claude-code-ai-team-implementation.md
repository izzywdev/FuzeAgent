# Claude Code AI Team Implementation Plan

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Management UI                            │
│                    (React + WebSocket + D3.js)                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                    API Gateway (Kong/Traefik)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                 Orchestration Service (FastAPI)                  │
│                        + CrewAI Core                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Message Queue (RabbitMQ)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                        Agent Containers                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  IzzyAI CEO │  │   CTO Agent │  │  CPO Agent  │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │Frontend Dev1│  │Frontend Dev2│  │Backend Dev1 │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     Shared Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │Context Store │  │  MCP Servers │  │  Code Storage  │       │
│  │  (Postgres)  │  │   (Node.js)  │  │   (GitLab)    │       │
│  └──────────────┘  └──────────────┘  └────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

## 📋 Phase 1: Core Infrastructure (Week 1)

### 1.1 Docker Compose Base Configuration

```yaml
# docker-compose.yml
version: '3.9'

services:
  # Message Queue
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  # Database for Context Storage
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ai_context
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init_db.sql:/docker-entrypoint-initdb.d/init.sql

  # Redis for Caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Orchestration Service
  orchestrator:
    build: ./services/orchestrator
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_context
      REDIS_URL: redis://redis:6379
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD}@rabbitmq:5672/
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
      - rabbitmq

  # Management UI
  ui:
    build: ./services/ui
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_WS_URL: ws://localhost:8000/ws
    depends_on:
      - orchestrator

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
```

### 1.2 Database Schema

```sql
-- init_db.sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Agent Registry
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'executive', 'developer', 'qa', etc.
    status VARCHAR(50) DEFAULT 'inactive',
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Interactions
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assigned_to UUID REFERENCES agents(id),
    created_by UUID REFERENCES agents(id),
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent Relationships
CREATE TABLE agent_hierarchy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES agents(id),
    child_id UUID REFERENCES agents(id),
    relationship_type VARCHAR(50), -- 'manages', 'collaborates', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_embedding ON interactions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_agents_status ON agents(status);
```

## 📋 Phase 2: Orchestration Service (Week 1-2)

### 2.1 Orchestration Service Structure

```python
# services/orchestrator/main.py
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
            "model": "claude-opus-4-20250514",
            "temperature": 0.7,
            "tools": ["strategic_planning", "resource_allocation", "team_management"]
        }
    )
    
    yield
    
    # Shutdown
    await app.state.agent_manager.shutdown_all()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
```

### 2.2 Agent Manager with CrewAI Integration

```python
# services/orchestrator/agent_manager.py
from crewai import Crew, Agent, Task
from typing import Dict, List, Optional
import asyncio
import docker
from .claude_code_wrapper import ClaudeCodeWrapper

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.docker_client = docker.from_env()
        self.crews: Dict[str, Crew] = {}
        
    async def create_agent(
        self, 
        name: str, 
        role: str, 
        type: str,
        config: dict
    ) -> Agent:
        """Create a new agent and optionally spawn a container"""
        
        # Create CrewAI agent
        agent = Agent(
            role=role,
            goal=config.get('goal', f"Perform {role} tasks efficiently"),
            backstory=config.get('backstory', f"Expert {role} with deep knowledge"),
            tools=self._get_tools_for_role(type, config.get('tools', [])),
            llm_config={
                "model": config.get('model', 'claude-opus-4-20250514'),
                "temperature": config.get('temperature', 0.7)
            },
            verbose=True
        )
        
        # For developer agents, wrap Claude Code
        if type == 'developer':
            agent.tools.append(ClaudeCodeWrapper())
        
        # Store agent
        self.agents[name] = agent
        
        # For complex agents, spawn dedicated container
        if type in ['executive', 'developer']:
            await self._spawn_agent_container(name, role, type, config)
        
        # Update database
        await self._register_agent_in_db(name, role, type, config)
        
        return agent
    
    async def _spawn_agent_container(
        self, 
        name: str, 
        role: str, 
        type: str,
        config: dict
    ):
        """Spawn a dedicated container for an agent"""
        
        container_config = {
            'image': f'ai-agent-{type}:latest',
            'name': f'agent-{name.lower().replace(" ", "-")}',
            'environment': {
                'AGENT_NAME': name,
                'AGENT_ROLE': role,
                'AGENT_TYPE': type,
                'RABBITMQ_URL': 'amqp://admin:password@rabbitmq:5672/',
                'CONTEXT_API_URL': 'http://orchestrator:8000',
                'ANTHROPIC_API_KEY': os.environ['ANTHROPIC_API_KEY']
            },
            'network': 'ai-team-network',
            'restart_policy': {'Name': 'unless-stopped'}
        }
        
        try:
            container = self.docker_client.containers.run(
                detach=True,
                **container_config
            )
            print(f"Spawned container for {name}: {container.id}")
        except Exception as e:
            print(f"Error spawning container for {name}: {e}")
    
    def _get_tools_for_role(self, type: str, custom_tools: List[str]) -> List:
        """Get appropriate tools based on agent type"""
        
        base_tools = {
            'executive': ['strategic_planning', 'resource_allocation', 'team_management'],
            'developer': ['code_generation', 'code_review', 'debugging'],
            'qa': ['test_generation', 'test_execution', 'bug_reporting'],
            'designer': ['mockup_generation', 'design_review', 'accessibility_check'],
            'support': ['ticket_handling', 'knowledge_search', 'customer_response']
        }
        
        tools = base_tools.get(type, [])
        tools.extend(custom_tools)
        
        # Convert to actual tool instances
        return [self._create_tool(tool_name) for tool_name in tools]
```

### 2.3 Claude Code Wrapper

```python
# services/orchestrator/claude_code_wrapper.py
from crewai.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import subprocess
import tempfile
import os

class ClaudeCodeInput(BaseModel):
    """Input schema for Claude Code tool"""
    task: str = Field(description="Coding task to complete")
    language: str = Field(default="python", description="Programming language")
    context: str = Field(default="", description="Additional context or requirements")

class ClaudeCodeWrapper(BaseTool):
    name: str = "claude_code"
    description: str = "Execute coding tasks using Claude Code SDK"
    args_schema: Type[BaseModel] = ClaudeCodeInput
    
    def _run(self, task: str, language: str = "python", context: str = "") -> str:
        """Execute Claude Code for a specific task"""
        
        # Prepare the prompt
        prompt = f"""
        Task: {task}
        Language: {language}
        Context: {context}
        
        Please complete this coding task following best practices.
        """
        
        # Create temporary directory for code execution
        with tempfile.TemporaryDirectory() as tmpdir:
            # Call Claude Code CLI (assuming it's installed in container)
            cmd = [
                "claude-code",
                "execute",
                "--prompt", prompt,
                "--output-dir", tmpdir,
                "--language", language
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    # Read generated files
                    generated_files = []
                    for filename in os.listdir(tmpdir):
                        filepath = os.path.join(tmpdir, filename)
                        with open(filepath, 'r') as f:
                            generated_files.append({
                                'filename': filename,
                                'content': f.read()
                            })
                    
                    return {
                        'status': 'success',
                        'files': generated_files,
                        'output': result.stdout
                    }
                else:
                    return {
                        'status': 'error',
                        'error': result.stderr
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    'status': 'error',
                    'error': 'Task execution timed out'
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'error': str(e)
                }
```

## 📋 Phase 3: Agent Container Templates (Week 2)

### 3.1 Base Agent Container

```dockerfile
# containers/base-agent/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN curl -fsSL https://claude-code-install.anthropic.com | bash

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .
COPY tools/ ./tools/

# Run agent
CMD ["python", "agent.py"]
```

### 3.2 Developer Agent Implementation

```python
# containers/developer-agent/agent.py
import asyncio
import aio_pika
import json
from typing import Dict, Any
import os
from claude_code_sdk import ClaudeCode
from context_client import ContextClient

class DeveloperAgent:
    def __init__(self):
        self.name = os.environ['AGENT_NAME']
        self.role = os.environ['AGENT_ROLE']
        self.claude_code = ClaudeCode(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.context_client = ContextClient(os.environ['CONTEXT_API_URL'])
        
    async def start(self):
        """Start listening for tasks"""
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            os.environ['RABBITMQ_URL']
        )
        
        async with connection:
            channel = await connection.channel()
            
            # Declare queue for this agent
            queue = await channel.declare_queue(
                f"agent_{self.name.lower().replace(' ', '_')}",
                durable=True
            )
            
            # Start consuming tasks
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await self.process_task(json.loads(message.body))
    
    async def process_task(self, task: Dict[str, Any]):
        """Process a development task"""
        task_id = task['id']
        task_type = task['type']
        
        try:
            # Get relevant context
            context = await self.context_client.get_context(
                query=task['description'],
                agent_id=self.name
            )
            
            # Execute task based on type
            if task_type == 'implement_feature':
                result = await self.implement_feature(task, context)
            elif task_type == 'fix_bug':
                result = await self.fix_bug(task, context)
            elif task_type == 'code_review':
                result = await self.review_code(task, context)
            else:
                result = {'error': f'Unknown task type: {task_type}'}
            
            # Update task status
            await self.context_client.update_task(
                task_id=task_id,
                status='completed',
                result=result
            )
            
            # Store interaction in context
            await self.context_client.store_interaction(
                agent_id=self.name,
                content=f"Completed task: {task['title']}",
                metadata={
                    'task_id': task_id,
                    'result': result
                }
            )
            
        except Exception as e:
            await self.context_client.update_task(
                task_id=task_id,
                status='failed',
                error=str(e)
            )
    
    async def implement_feature(self, task: Dict, context: Dict) -> Dict:
        """Implement a new feature"""
        
        # Prepare Claude Code prompt
        prompt = f"""
        Feature Request: {task['description']}
        
        Technical Requirements:
        {json.dumps(task.get('requirements', {}), indent=2)}
        
        Relevant Context:
        {context.get('relevant_code', '')}
        
        Previous Similar Implementations:
        {context.get('similar_features', '')}
        
        Please implement this feature following our coding standards.
        """
        
        # Execute with Claude Code
        result = self.claude_code.execute(
            prompt=prompt,
            mode='implement',
            test_coverage=True
        )
        
        return {
            'files': result.files,
            'tests': result.tests,
            'documentation': result.documentation,
            'commit_message': result.suggested_commit_message
        }

if __name__ == "__main__":
    agent = DeveloperAgent()
    asyncio.run(agent.start())
```

## 📋 Phase 4: Management UI (Week 2-3)

### 4.1 React UI Structure

```tsx
// services/ui/src/App.tsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import AgentDetails from './pages/AgentDetails';
import TaskManager from './pages/TaskManager';
import TeamHierarchy from './components/TeamHierarchy';
import { WebSocketProvider } from './contexts/WebSocketContext';

function App() {
  return (
    <WebSocketProvider url={process.env.REACT_APP_WS_URL}>
      <Router>
        <div className="min-h-screen bg-gray-100">
          <nav className="bg-white shadow-lg">
            <div className="max-w-7xl mx-auto px-4">
              <div className="flex justify-between h-16">
                <div className="flex items-center">
                  <h1 className="text-xl font-semibold">AI Team Manager</h1>
                </div>
                <div className="flex space-x-4 items-center">
                  <a href="/" className="hover:text-blue-600">Dashboard</a>
                  <a href="/agents" className="hover:text-blue-600">Agents</a>
                  <a href="/tasks" className="hover:text-blue-600">Tasks</a>
                  <a href="/hierarchy" className="hover:text-blue-600">Team</a>
                </div>
              </div>
            </div>
          </nav>
          
          <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/agents/:id" element={<AgentDetails />} />
              <Route path="/tasks" element={<TaskManager />} />
              <Route path="/hierarchy" element={<TeamHierarchy />} />
            </Routes>
          </main>
        </div>
      </Router>
    </WebSocketProvider>
  );
}

export default App;
```

### 4.2 Team Hierarchy Visualization

```tsx
// services/ui/src/components/TeamHierarchy.tsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useWebSocket } from '../contexts/WebSocketContext';

interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: string;
  children?: Agent[];
}

const TeamHierarchy: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { agents } = useWebSocket();
  
  useEffect(() => {
    if (!agents || agents.length === 0) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    const width = 1200;
    const height = 800;
    const margin = { top: 20, right: 120, bottom: 20, left: 120 };
    
    // Build hierarchy
    const hierarchy = d3.hierarchy(buildHierarchy(agents));
    
    const treeLayout = d3.tree()
      .size([height - margin.top - margin.bottom, width - margin.left - margin.right]);
    
    const treeData = treeLayout(hierarchy);
    
    const g = svg
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);
    
    // Links
    g.selectAll(".link")
      .data(treeData.links())
      .enter()
      .append("path")
      .attr("class", "link")
      .attr("d", d3.linkHorizontal()
        .x(d => d.y)
        .y(d => d.x)
      )
      .style("fill", "none")
      .style("stroke", "#ccc")
      .style("stroke-width", 2);
    
    // Nodes
    const node = g.selectAll(".node")
      .data(treeData.descendants())
      .enter()
      .append("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.y},${d.x})`);
    
    // Node circles
    node.append("circle")
      .attr("r", 25)
      .style("fill", d => getNodeColor(d.data))
      .style("stroke", "#333")
      .style("stroke-width", 2);
    
    // Node labels
    node.append("text")
      .attr("dy", ".31em")
      .attr("x", d => d.children ? -30 : 30)
      .style("text-anchor", d => d.children ? "end" : "start")
      .text(d => d.data.name)
      .style("font-size", "12px");
    
    // Status indicators
    node.append("circle")
      .attr("r", 5)
      .attr("cx", 20)
      .attr("cy", -20)
      .style("fill", d => d.data.status === 'active' ? '#10b981' : '#ef4444');
    
  }, [agents]);
  
  const buildHierarchy = (agents: Agent[]): Agent => {
    // Find IzzyAI (root)
    const izzy = agents.find(a => a.name === 'IzzyAI');
    if (!izzy) return { id: 'root', name: 'No CEO', role: '', type: '', status: 'inactive' };
    
    // Build tree structure
    const executives = agents.filter(a => a.type === 'executive' && a.name !== 'IzzyAI');
    const developers = agents.filter(a => a.type === 'developer');
    const qa = agents.filter(a => a.type === 'qa');
    const designers = agents.filter(a => a.type === 'designer');
    
    // Organize by department
    const cto = executives.find(a => a.role.includes('CTO'));
    const cpo = executives.find(a => a.role.includes('CPO'));
    
    if (cto) cto.children = developers;
    if (cpo) cpo.children = [...designers, ...qa];
    
    izzy.children = executives;
    
    return izzy;
  };
  
  const getNodeColor = (agent: Agent): string => {
    const colors = {
      executive: '#3b82f6',
      developer: '#10b981',
      qa: '#f59e0b',
      designer: '#8b5cf6',
      support: '#ec4899'
    };
    return colors[agent.type] || '#6b7280';
  };
  
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-4">Team Hierarchy</h2>
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default TeamHierarchy;
```

### 4.3 Agent Creation Form

```tsx
// services/ui/src/components/CreateAgentForm.tsx
import React, { useState } from 'react';
import { createAgent } from '../api/agents';

const CreateAgentForm: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    type: 'developer',
    goal: '',
    backstory: '',
    tools: [],
    model: 'claude-opus-4-20250514',
    temperature: 0.7
  });
  
  const agentTypes = [
    { value: 'executive', label: 'Executive' },
    { value: 'developer', label: 'Developer' },
    { value: 'qa', label: 'QA Engineer' },
    { value: 'designer', label: 'Designer' },
    { value: 'support', label: 'Support' }
  ];
  
  const toolOptions = {
    developer: ['code_generation', 'code_review', 'debugging', 'testing'],
    qa: ['test_generation', 'test_execution', 'bug_reporting'],
    designer: ['mockup_generation', 'design_review', 'accessibility_check'],
    executive: ['strategic_planning', 'resource_allocation', 'team_management'],
    support: ['ticket_handling', 'knowledge_search', 'customer_response']
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const agent = await createAgent({
        name: formData.name,
        role: formData.role,
        type: formData.type,
        config: {
          goal: formData.goal,
          backstory: formData.backstory,
          tools: formData.tools,
          model: formData.model,
          temperature: formData.temperature
        }
      });
      
      alert(`Agent ${agent.name} created successfully!`);
      // Reset form or redirect
    } catch (error) {
      alert('Error creating agent: ' + error.message);
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Agent Name
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Role Description
        </label>
        <input
          type="text"
          value={formData.role}
          onChange={(e) => setFormData({...formData, role: e.target.value})}
          placeholder="e.g., Senior Frontend Developer"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Agent Type
        </label>
        <select
          value={formData.type}
          onChange={(e) => setFormData({...formData, type: e.target.value, tools: []})}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          {agentTypes.map(type => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Agent Goal
        </label>
        <textarea
          value={formData.goal}
          onChange={(e) => setFormData({...formData, goal: e.target.value})}
          placeholder="What is this agent's primary objective?"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          rows={3}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Tools & Capabilities
        </label>
        <div className="mt-2 space-y-2">
          {toolOptions[formData.type]?.map(tool => (
            <label key={tool} className="flex items-center">
              <input
                type="checkbox"
                value={tool}
                checked={formData.tools.includes(tool)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData({...formData, tools: [...formData.tools, tool]});
                  } else {
                    setFormData({...formData, tools: formData.tools.filter(t => t !== tool)});
                  }
                }}
                className="mr-2"
              />
              {tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </label>
          ))}
        </div>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Temperature (Creativity)
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={formData.temperature}
          onChange={(e) => setFormData({...formData, temperature: parseFloat(e.target.value)})}
          className="mt-1 block w-full"
        />
        <span className="text-sm text-gray-500">{formData.temperature}</span>
      </div>
      
      <button
        type="submit"
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
      >
        Create Agent
      </button>
    </form>
  );
};

export default CreateAgentForm;
```

## 📋 Phase 5: Task Management System (Week 3)

### 5.1 Task Distribution Algorithm

```python
# services/orchestrator/task_distributor.py
from typing import List, Dict, Optional
import asyncio
from datetime import datetime
import json

class TaskDistributor:
    def __init__(self, agent_manager, context_service):
        self.agent_manager = agent_manager
        self.context_service = context_service
        
    async def distribute_task(self, task: Dict) -> Dict:
        """Intelligently distribute tasks to appropriate agents"""
        
        # Analyze task requirements
        task_analysis = await self._analyze_task(task)
        
        # Find suitable agents
        suitable_agents = await self._find_suitable_agents(task_analysis)
        
        # If task needs multiple agents, create subtasks
        if task_analysis['complexity'] == 'high' or len(task_analysis['required_skills']) > 1:
            subtasks = await self._decompose_task(task, task_analysis)
            
            # Distribute subtasks
            assignments = []
            for subtask in subtasks:
                agent = await self._select_best_agent(subtask, suitable_agents)
                assignment = await self._assign_to_agent(agent, subtask)
                assignments.append(assignment)
            
            return {
                'task_id': task['id'],
                'type': 'distributed',
                'subtasks': assignments
            }
        else:
            # Simple task - assign to single agent
            agent = await self._select_best_agent(task, suitable_agents)
            return await self._assign_to_agent(agent, task)
    
    async def _analyze_task(self, task: Dict) -> Dict:
        """Use AI to analyze task requirements"""
        
        # Get IzzyAI or a planning agent to analyze
        analysis_prompt = f"""
        Analyze this task and determine:
        1. Required skills/expertise
        2. Complexity level (low/medium/high)
        3. Estimated time
        4. Dependencies
        5. Suggested agent type(s)
        
        Task: {json.dumps(task, indent=2)}
        """
        
        # This would call Claude to analyze
        analysis = await self.agent_manager.agents['IzzyAI'].analyze(analysis_prompt)
        
        return analysis
    
    async def _decompose_task(self, task: Dict, analysis: Dict) -> List[Dict]:
        """Break complex tasks into subtasks"""
        
        decomposition_prompt = f"""
        Break down this complex task into smaller, manageable subtasks.
        Each subtask should be assignable to a single agent.
        
        Task: {task['description']}
        Analysis: {json.dumps(analysis, indent=2)}
        
        Return a list of subtasks with:
        - title
        - description
        - required_skills
        - dependencies
        - estimated_time
        """
        
        # Use executive agent to decompose
        subtasks = await self.agent_manager.agents['IzzyAI'].plan(decomposition_prompt)
        
        return subtasks
```

### 5.2 Real-time Monitoring Dashboard

```tsx
// services/ui/src/pages/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import AgentCard from '../components/AgentCard';
import TaskQueue from '../components/TaskQueue';
import PerformanceMetrics from '../components/PerformanceMetrics';
import ActiveTasks from '../components/ActiveTasks';

const Dashboard: React.FC = () => {
  const { agents, tasks, metrics } = useWebSocket();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  
  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Agent Status Grid */}
      <div className="col-span-8">
        <h2 className="text-xl font-bold mb-4">Active Agents</h2>
        <div className="grid grid-cols-3 gap-4">
          {agents.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onClick={() => setSelectedAgent(agent.id)}
              selected={selectedAgent === agent.id}
            />
          ))}
        </div>
      </div>
      
      {/* Task Queue */}
      <div className="col-span-4">
        <TaskQueue tasks={tasks.filter(t => t.status === 'pending')} />
      </div>
      
      {/* Active Tasks */}
      <div className="col-span-12">
        <ActiveTasks tasks={tasks.filter(t => t.status === 'in_progress')} />
      </div>
      
      {/* Performance Metrics */}
      <div className="col-span-12">
        <PerformanceMetrics metrics={metrics} />
      </div>
    </div>
  );
};

// Agent Card Component
const AgentCard: React.FC<{agent: Agent, onClick: () => void, selected: boolean}> = ({ agent, onClick, selected }) => {
  const statusColors = {
    active: 'bg-green-100 text-green-800',
    busy: 'bg-yellow-100 text-yellow-800',
    idle: 'bg-gray-100 text-gray-800',
    error: 'bg-red-100 text-red-800'
  };
  
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
        selected ? 'border-blue-500 shadow-lg' : 'border-gray-200'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold">{agent.name}</h3>
        <span className={`px-2 py-1 rounded text-xs ${statusColors[agent.status]}`}>
          {agent.status}
        </span>
      </div>
      <p className="text-sm text-gray-600">{agent.role}</p>
      <div className="mt-3 space-y-1">
        <div className="text-xs text-gray-500">
          Current Task: {agent.currentTask || 'None'}
        </div>
        <div className="text-xs text-gray-500">
          Tasks Completed: {agent.tasksCompleted || 0}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
```

## 📋 Phase 6: Deployment & Scaling (Week 4)

### 6.1 Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-team

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: ai-team
spec:
  replicas: 2
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: ai-team/orchestrator:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: ai-team
spec:
  selector:
    app: orchestrator
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
# Agent Auto-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: developer-agents-hpa
  namespace: ai-team
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: developer-agents
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: pending_tasks
      target:
        type: AverageValue
        averageValue: "5"
```

### 6.2 Monitoring Stack

```yaml
# docker-compose.monitoring.yml
version: '3.9'

services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    depends_on:
      - prometheus
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources

  loki:
    image: grafana/loki
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki

  promtail:
    image: grafana/promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

### 6.3 Quick Start Script

```bash
#!/bin/bash
# setup.sh - Quick setup script for AI Team

echo "🚀 Setting up AI Team Infrastructure..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Create necessary directories
mkdir -p services/{orchestrator,ui,context-service}
mkdir -p containers/{base-agent,developer-agent,executive-agent}
mkdir -p k8s
mkdir -p monitoring/{prometheus,grafana}

# Generate .env file
cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
RABBITMQ_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
ANTHROPIC_API_KEY=your-api-key-here
JWT_SECRET=$(openssl rand -base64 32)
EOF

echo "📝 Created .env file - Please add your ANTHROPIC_API_KEY"

# Build base images
echo "🔨 Building base images..."
docker-compose build

# Initialize database
echo "💾 Initializing database..."
docker-compose up -d postgres
sleep 5
docker-compose exec postgres psql -U postgres -d ai_context -f /docker-entrypoint-initdb.d/init.sql

# Start core services
echo "🎯 Starting core services..."
docker-compose up -d rabbitmq redis

# Start orchestrator
echo "🤖 Starting orchestrator..."
docker-compose up -d orchestrator

# Start UI
echo "🎨 Starting management UI..."
docker-compose up -d ui

# Create initial IzzyAI agent
echo "👔 Creating IzzyAI CEO..."
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IzzyAI",
    "role": "Digital CEO",
    "type": "executive",
    "config": {
      "goal": "Lead the AI team to build amazing products",
      "backstory": "Visionary AI leader with deep understanding of technology and business",
      "tools": ["strategic_planning", "resource_allocation", "team_management"],
      "model": "claude-opus-4-20250514",
      "temperature": 0.7
    }
  }'

echo "✅ Setup complete!"
echo "📊 Dashboard available at: http://localhost:3000"
echo "🔌 API available at: http://localhost:8000"
echo "📝 RabbitMQ Management: http://localhost:15672 (admin/password)"

echo ""
echo "Next steps:"
echo "1. Add your ANTHROPIC_API_KEY to .env file"
echo "2. Restart services: docker-compose restart"
echo "3. Create additional agents via the UI"
echo "4. Start assigning tasks!"
```

## 📊 Monitoring & Observability

### Custom Grafana Dashboard Config

```json
{
  "dashboard": {
    "title": "AI Team Performance",
    "panels": [
      {
        "title": "Active Agents",
        "targets": [
          {
            "expr": "sum(agent_status{status='active'})"
          }
        ]
      },
      {
        "title": "Tasks Completed (24h)",
        "targets": [
          {
            "expr": "sum(rate(tasks_completed_total[24h]))"
          }
        ]
      },
      {
        "title": "Agent Utilization",
        "targets": [
          {
            "expr": "avg(agent_utilization_percent) by (agent_name)"
          }
        ]
      },
      {
        "title": "API Token Usage",
        "targets": [
          {
            "expr": "sum(rate(anthropic_tokens_used_total[1h]))"
          }
        ]
      }
    ]
  }
}
```

## 🎯 Key Features Implemented

1. **Containerized Agent Architecture**: Each agent runs in its own container with Claude Code SDK
2. **Visual Team Hierarchy**: D3.js-based visualization of the entire team structure
3. **Real-time Monitoring**: WebSocket-based live updates of agent status and tasks
4. **Intelligent Task Distribution**: AI-powered task analysis and assignment
5. **Shared Context System**: PostgreSQL with pgvector for semantic search across all agent memories
6. **Auto-scaling**: Kubernetes HPA for scaling agents based on workload
7. **Cost Tracking**: Monitor API usage and optimize agent utilization
8. **Human-in-the-loop**: Critical decisions route to Israel (Human CEO)

This implementation provides a production-ready foundation for your AI startup team!