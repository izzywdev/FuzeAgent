# FuzeAgent Autonomous Agent Execution System - Comprehensive Implementation Plan

## Executive Summary

Transform FuzeAgent from a task assignment system to a fully autonomous AI development platform where agents independently execute code development tasks using Claude Code SDK, manage Git workflows, handle dependencies, and interact with humans when needed - all within secure, isolated environments.

## Current State Analysis

### ✅ What We Have
- **Task assignment system working** (tasks show as "pending")
- **Claude Code wrapper exists** but is basic (`claude_code_wrapper.py`)
- **Agent containers framework** exists (`developer-agent/agent.py`, `base-agent/`)
- **Task queue system** with RabbitMQ
- **Sophisticated A2A protocol** implemented (`a2a_protocol.py`) with:
  - Agent discovery and capability matching
  - Task delegation between agents
  - Inter-agent communication and status updates
  - Message routing and conversation threading
- **Docker-based agent containers** with security (non-root users)
- **Claude Code CLI pre-installed** in base agent images

### ❌ What's Missing
- **Actual background execution processes** - tasks remain "pending"
- **Git workflow integration** - no repository cloning, branching, or PR creation
- **Repository settings** in agent configuration
- **Chat interaction database schema** - no conversation history
- **Human-in-the-loop workflow** - no mechanism for agent questions
- **Task dependency management** - no sequential/parallel task orchestration
- **Agent sandboxing** for secure code execution
- **Context transfer between agents** and tasks
- **Dev container templates** for different agent types

## Technical Architecture Overview

### System Components
```
FuzeAgent Autonomous Execution Platform
├── Task Orchestration Layer
│   ├── TaskExecutionEngine (main daemon)
│   ├── DependencyGraphManager (task relationships)
│   └── TaskProcessor instances (one per active task)
│
├── Agent Sandboxing Layer  
│   ├── AgentSandboxManager (Docker dev containers)
│   ├── DevContainerTemplate (per agent type)
│   └── ResourceManager (limits, cleanup, security)
│
├── Communication Layer
│   ├── A2AProtocolManager (inter-agent communication)
│   ├── ContextTransferService (artifacts, knowledge)
│   └── HumanInTheLoopHandler (questions, responses)
│
├── Git Integration Layer
│   ├── GitWorkflowManager (clone, branch, PR)
│   ├── ClaudeCodeExecutor (enhanced wrapper)
│   └── ProgressReporter (commits, status)
│
└── Monitoring & UI Layer
    ├── WebSocket real-time updates
    ├── Chat interface for human interaction
    └── Dependency graph visualization
```

## Implementation Plan

### Phase 1: Agent Sandboxing & Repository Integration

#### 1.1 Enhanced Agent Configuration
```json
{
  "agent_id": "uuid",
  "repository_settings": {
    "repository_url": "https://github.com/org/fuzeagent.git",
    "github_token": "encrypted_token",
    "default_branch": "main",
    "workspace_path": "/workspaces/agent-{agent_id}",
    "auto_create_pr": true,
    "require_review": true
  },
  "sandbox_settings": {
    "container_type": "dev_container",
    "base_image": "fuzeagent/dev-base:latest", 
    "resource_limits": {
      "memory": "2Gi",
      "cpu": "1000m", 
      "disk": "10Gi"
    },
    "network_policy": "restricted",
    "allowed_commands": ["git", "npm", "python", "docker"],
    "forbidden_paths": ["/etc", "/root", "/home/host"],
    "auto_cleanup": "24h"
  }
}
```

#### 1.2 Database Schema Enhancements
```sql
-- Add to agents table
ALTER TABLE agents ADD COLUMN repository_settings JSONB;
ALTER TABLE agents ADD COLUMN sandbox_settings JSONB;
ALTER TABLE agents ADD COLUMN workspace_path TEXT;
ALTER TABLE agents ADD COLUMN git_credentials_encrypted TEXT;

-- Task dependency management
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dependent_task_id UUID REFERENCES tasks(id),
    prerequisite_task_id UUID REFERENCES tasks(id), 
    dependency_type VARCHAR(20) CHECK (dependency_type IN ('blocking', 'soft', 'data')),
    status VARCHAR(20) DEFAULT 'waiting',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Task execution tracking
CREATE TABLE task_iterations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    iteration_number INTEGER NOT NULL,
    git_commit_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT 'in_progress',
    agent_message TEXT,
    human_question TEXT,
    human_response TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Chat interactions
CREATE TABLE task_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    sender_type VARCHAR(20) CHECK (sender_type IN ('agent', 'human', 'system')),
    sender_id VARCHAR(255),
    message TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Human-in-the-loop questions
CREATE TABLE task_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(20) DEFAULT 'pending',
    human_response TEXT,
    context_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    answered_at TIMESTAMP
);
```

#### 1.3 Dev Container Templates
Create specialized dev containers for each agent type:

**Base Template (`containers/dev-base/Dockerfile`):**
```dockerfile
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Install development tools
RUN apt-get update && apt-get install -y \
    git curl wget \
    python3 python3-pip \
    nodejs npm \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Security: non-root user
RUN useradd -m -u 1000 agent && \
    usermod -aG docker agent

# Resource limits via systemd
COPY limits.conf /etc/security/limits.d/agent.conf

USER agent
WORKDIR /workspaces
```

**Python Developer Template (`containers/dev-python/Dockerfile`):**
```dockerfile 
FROM fuzeagent/dev-base:latest

# Python-specific tools
RUN pip3 install --user \
    fastapi uvicorn \
    pytest black isort mypy \
    sqlalchemy asyncpg \
    pandas numpy

# VS Code extensions for Python
RUN code --install-extension ms-python.python
```

### Phase 2: Git Workflow Integration System

#### 2.1 GitWorkflowManager Implementation
```python
class GitWorkflowManager:
    def __init__(self, agent_id: str, repo_settings: dict):
        self.agent_id = agent_id
        self.repo_url = repo_settings['repository_url']
        self.workspace_path = repo_settings['workspace_path']
        self.github_token = self.decrypt_token(repo_settings['github_token'])
        
    async def setup_workspace(self, task_id: str) -> str:
        """Clone repo and create feature branch"""
        branch_name = f"feature/agent-{self.agent_id}-task-{task_id}"
        
        # Clone repository
        await self.run_git_command([
            'git', 'clone', 
            f'https://{self.github_token}@{self.repo_url}',
            self.workspace_path
        ])
        
        # Create and checkout feature branch
        await self.run_git_command(['git', 'checkout', '-b', branch_name])
        
        return branch_name
        
    async def commit_changes(self, message: str, files: List[str] = None) -> str:
        """Commit changes with descriptive message"""
        if files:
            for file in files:
                await self.run_git_command(['git', 'add', file])
        else:
            await self.run_git_command(['git', 'add', '.'])
            
        commit_hash = await self.run_git_command([
            'git', 'commit', '-m', 
            f"🤖 {message}\n\nGenerated by FuzeAgent {self.agent_id}"
        ])
        
        return commit_hash.strip()
        
    async def create_pull_request(self, task_title: str, description: str) -> str:
        """Create PR using GitHub CLI"""
        pr_url = await self.run_git_command([
            'gh', 'pr', 'create',
            '--title', f"🤖 {task_title}",
            '--body', f"{description}\n\n---\n*Automated PR by FuzeAgent {self.agent_id}*"
        ])
        
        return pr_url.strip()
```

#### 2.2 Enhanced Claude Code Wrapper
```python
class EnhancedClaudeCodeWrapper(ClaudeCodeWrapper):
    def __init__(self, workspace_path: str, git_manager: GitWorkflowManager):
        super().__init__()
        self.workspace_path = workspace_path
        self.git_manager = git_manager
        
    async def execute_with_git_tracking(
        self,
        task: str,
        iteration_number: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute Claude Code with git integration"""
        
        # Change to workspace directory
        original_cwd = os.getcwd()
        os.chdir(self.workspace_path)
        
        try:
            # Execute Claude Code
            result = await self.execute_claude_code(task, **kwargs)
            
            # Commit changes
            commit_message = f"Iteration {iteration_number}: {task[:100]}..."
            commit_hash = await self.git_manager.commit_changes(
                commit_message, 
                result.get('modified_files', [])
            )
            
            result['git_commit_hash'] = commit_hash
            result['iteration_number'] = iteration_number
            
            return result
            
        finally:
            os.chdir(original_cwd)
```

### Phase 3: Task Dependency Management

#### 3.1 TaskDependencyManager
```python
class TaskDependencyManager:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    async def create_dependency_graph(self, tasks: List[Task]) -> ExecutionGraph:
        """Analyze task dependencies and create execution plan"""
        
        # Build dependency graph
        graph = {}
        for task in tasks:
            dependencies = await self.extract_dependencies(task)
            graph[task.id] = {
                'task': task,
                'dependencies': dependencies,
                'dependents': []
            }
        
        # Find dependent tasks
        for task_id, node in graph.items():
            for dep_id in node['dependencies']:
                if dep_id in graph:
                    graph[dep_id]['dependents'].append(task_id)
        
        # Create execution plan
        execution_plan = await self.create_execution_plan(graph)
        
        return ExecutionGraph(
            graph_id=str(uuid.uuid4()),
            tasks=graph,
            execution_plan=execution_plan
        )
    
    async def resolve_dependencies(self, completed_task_id: str) -> List[str]:
        """Get tasks that are now ready to execute"""
        
        async with self.db_pool.acquire() as conn:
            # Find tasks waiting on this completed task
            ready_tasks = await conn.fetch("""
                UPDATE task_dependencies 
                SET status = 'satisfied'
                WHERE prerequisite_task_id = $1 AND status = 'waiting'
                RETURNING dependent_task_id
            """, completed_task_id)
            
            ready_task_ids = []
            for task_row in ready_tasks:
                task_id = task_row['dependent_task_id']
                
                # Check if all dependencies are satisfied
                remaining_deps = await conn.fetchval("""
                    SELECT COUNT(*) FROM task_dependencies
                    WHERE dependent_task_id = $1 AND status != 'satisfied'
                """, task_id)
                
                if remaining_deps == 0:
                    ready_task_ids.append(task_id)
            
            return ready_task_ids
```

#### 3.2 A2A Integration for Dependencies
```python
class EnhancedA2AProtocolManager(A2AProtocolManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependency_manager = TaskDependencyManager(self.pool)
        
    async def delegate_task_with_dependencies(
        self,
        requesting_agent_id: str,
        task_data: dict,
        dependencies: List[str] = None
    ) -> str:
        """Enhanced task delegation with dependency tracking"""
        
        # Create the task
        task_id = await self.delegate_task(
            requesting_agent_id=requesting_agent_id,
            **task_data
        )
        
        # Register dependencies
        if dependencies:
            await self.dependency_manager.register_dependencies(
                task_id, dependencies
            )
        
        # Check if task can start immediately
        ready_tasks = await self.dependency_manager.get_ready_tasks([task_id])
        if task_id not in ready_tasks:
            # Task must wait for dependencies
            await self.update_task_status(task_id, TaskStatus.WAITING_DEPENDENCIES)
        
        return task_id
        
    async def handle_task_completion(self, task_id: str, result: dict):
        """Handle task completion and trigger dependent tasks"""
        
        # Mark task as completed
        await self.update_task_status(task_id, TaskStatus.COMPLETED, output_data=result)
        
        # Find and trigger dependent tasks
        ready_tasks = await self.dependency_manager.resolve_dependencies(task_id)
        
        for ready_task_id in ready_tasks:
            # Transfer context from completed task to ready task
            await self.transfer_task_context(task_id, ready_task_id, result)
            
            # Update task status to ready
            await self.update_task_status(ready_task_id, TaskStatus.PENDING)
            
            # Notify the assigned agent
            task_data = await self.get_task(ready_task_id)
            await self.send_message(
                sender_agent_id="system",
                recipient_agent_id=task_data.assigned_agent_id,
                message_type=MessageType.STATUS_UPDATE,
                content=f"Task {ready_task_id} is now ready to execute",
                task_id=ready_task_id
            )
```

### Phase 4: Background Task Execution Engine

#### 4.1 TaskExecutionEngine
```python
class TaskExecutionEngine:
    def __init__(self):
        self.task_processors: Dict[str, TaskProcessor] = {}
        self.sandbox_manager = AgentSandboxManager()
        self.a2a_manager = EnhancedA2AProtocolManager(DATABASE_URL)
        self.dependency_manager = TaskDependencyManager(self.a2a_manager.pool)
        
    async def start(self):
        """Start the execution engine"""
        await self.a2a_manager.initialize()
        
        # Start task monitor
        asyncio.create_task(self.task_monitor_loop())
        
        # Start cleanup process
        asyncio.create_task(self.cleanup_loop())
        
    async def task_monitor_loop(self):
        """Main loop that monitors for pending tasks"""
        while True:
            try:
                # Get ready tasks (no unsatisfied dependencies)
                ready_tasks = await self.get_ready_tasks()
                
                for task in ready_tasks:
                    if task.id not in self.task_processors:
                        # Start new task processor
                        await self.start_task_processor(task)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in task monitor loop: {e}")
                await asyncio.sleep(10)
                
    async def start_task_processor(self, task: A2ATask):
        """Start a new task processor for a task"""
        
        # Get agent information
        agent = await self.get_agent(task.assigned_agent_id)
        
        # Create sandbox for the agent
        sandbox = await self.sandbox_manager.create_sandbox(
            agent_id=task.assigned_agent_id,
            task_id=task.task_id,
            repo_settings=agent.repository_settings,
            sandbox_settings=agent.sandbox_settings
        )
        
        # Create and start task processor
        processor = TaskProcessor(
            task=task,
            agent=agent,
            sandbox=sandbox,
            a2a_manager=self.a2a_manager
        )
        
        self.task_processors[task.task_id] = processor
        
        # Start processing in background
        asyncio.create_task(self.run_task_processor(processor))
        
    async def run_task_processor(self, processor: TaskProcessor):
        """Run a task processor"""
        try:
            await processor.execute()
        except Exception as e:
            logger.error(f"Task processor error: {e}")
            await processor.handle_error(e)
        finally:
            # Cleanup
            await self.sandbox_manager.destroy_sandbox(processor.sandbox.id)
            if processor.task.task_id in self.task_processors:
                del self.task_processors[processor.task.task_id]
```

#### 4.2 TaskProcessor Implementation
```python
class TaskProcessor:
    def __init__(self, task: A2ATask, agent: Agent, sandbox: Sandbox, a2a_manager):
        self.task = task
        self.agent = agent  
        self.sandbox = sandbox
        self.a2a_manager = a2a_manager
        self.git_manager = GitWorkflowManager(agent.id, agent.repository_settings)
        self.claude_wrapper = EnhancedClaudeCodeWrapper(
            sandbox.workspace_path, 
            self.git_manager
        )
        self.human_loop_handler = HumanInTheLoopHandler(task.task_id, a2a_manager)
        
    async def execute(self):
        """Main task execution loop"""
        
        try:
            # Update task status
            await self.a2a_manager.update_task_status(
                self.task.task_id, 
                TaskStatus.IN_PROGRESS
            )
            
            # Setup workspace
            branch_name = await self.git_manager.setup_workspace(self.task.task_id)
            
            iteration = 0
            max_iterations = 10
            
            while iteration < max_iterations:
                iteration += 1
                
                await self.log_message(f"Starting iteration {iteration}")
                
                # Execute development work
                result = await self.claude_wrapper.execute_with_git_tracking(
                    task=self.task.description,
                    iteration_number=iteration,
                    context=self.task.input_data,
                    language=self.detect_language(),
                    include_tests=True
                )
                
                # Store iteration in database
                await self.store_iteration(iteration, result)
                
                # Check if human input is needed
                questions = self.extract_questions(result)
                if questions:
                    await self.handle_human_questions(questions, iteration)
                    continue
                
                # Check if task is complete
                if self.is_task_complete(result):
                    await self.complete_task(result, branch_name)
                    break
                    
                # Wait before next iteration
                await asyncio.sleep(30)
            
        except Exception as e:
            await self.handle_error(e)
            
    async def handle_human_questions(self, questions: List[str], iteration: int):
        """Handle human-in-the-loop questions"""
        
        for question in questions:
            # Store question in database
            question_id = await self.store_question(question, iteration)
            
            # Send notification via A2A
            await self.a2a_manager.send_message(
                sender_agent_id=self.agent.id,
                recipient_agent_id="human",  # Special human recipient
                message_type=MessageType.COLLABORATION,
                content=f"Human input needed: {question}",
                data={
                    "question_id": question_id,
                    "task_id": self.task.task_id,
                    "iteration": iteration
                }
            )
            
            # Wait for human response
            response = await self.human_loop_handler.wait_for_response(question_id)
            
            # Continue with human input
            await self.incorporate_human_response(response, iteration)
            
    async def complete_task(self, result: dict, branch_name: str):
        """Complete the task and create PR"""
        
        # Create pull request
        pr_url = await self.git_manager.create_pull_request(
            task_title=self.task.title,
            description=self.task.description + f"\n\nImplementation details:\n{result.get('explanation', '')}"
        )
        
        # Update task with results
        output_data = {
            "status": "completed",
            "pull_request_url": pr_url,
            "branch_name": branch_name,
            "files_modified": result.get('files', []),
            "commit_hashes": result.get('commits', [])
        }
        
        await self.a2a_manager.update_task_status(
            self.task.task_id,
            TaskStatus.COMPLETED,
            output_data=output_data
        )
        
        await self.log_message(f"Task completed successfully. PR: {pr_url}")
```

### Phase 5: Human-in-the-Loop System

#### 5.1 HumanInTheLoopHandler
```python
class HumanInTheLoopHandler:
    def __init__(self, task_id: str, a2a_manager):
        self.task_id = task_id
        self.a2a_manager = a2a_manager
        self.pending_questions: Dict[str, asyncio.Event] = {}
        
    async def wait_for_response(self, question_id: str, timeout: int = 3600) -> str:
        """Wait for human response to a question"""
        
        # Create event for this question
        event = asyncio.Event()
        self.pending_questions[question_id] = event
        
        try:
            # Wait for response or timeout
            await asyncio.wait_for(event.wait(), timeout=timeout)
            
            # Get the response from database
            async with self.a2a_manager.pool.acquire() as conn:
                response = await conn.fetchval("""
                    SELECT human_response FROM task_questions
                    WHERE id = $1
                """, question_id)
                
            return response
            
        except asyncio.TimeoutError:
            # Handle timeout - could escalate or use default response
            await self.handle_timeout(question_id)
            return "No response provided within timeout period"
            
        finally:
            if question_id in self.pending_questions:
                del self.pending_questions[question_id]
                
    async def receive_human_response(self, question_id: str, response: str):
        """Receive human response and notify waiting task"""
        
        # Store response in database
        async with self.a2a_manager.pool.acquire() as conn:
            await conn.execute("""
                UPDATE task_questions 
                SET human_response = $2, status = 'answered', answered_at = NOW()
                WHERE id = $1
            """, question_id, response)
        
        # Notify waiting task
        if question_id in self.pending_questions:
            self.pending_questions[question_id].set()
```

#### 5.2 Chat API Endpoints
```python
# Add to hierarchy_endpoints.py

@app.get("/tasks/{task_id}/messages")
async def get_task_messages(task_id: str):
    """Get full conversation history for a task"""
    async with get_db_connection() as conn:
        messages = await conn.fetch("""
            SELECT * FROM task_messages 
            WHERE task_id = $1 
            ORDER BY timestamp ASC
        """, task_id)
        
    return {"messages": [dict(msg) for msg in messages]}

@app.post("/tasks/{task_id}/messages")
async def add_task_message(task_id: str, message_data: dict):
    """Add a human message to task conversation"""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO task_messages (task_id, sender_type, sender_id, message, message_type)
            VALUES ($1, 'human', $2, $3, $4)
        """, task_id, message_data.get('sender_id', 'user'), 
             message_data['message'], message_data.get('type', 'text'))
    
    return {"status": "message_added"}

@app.get("/tasks/{task_id}/questions")
async def get_pending_questions(task_id: str):
    """Get pending human-in-the-loop questions"""
    async with get_db_connection() as conn:
        questions = await conn.fetch("""
            SELECT * FROM task_questions 
            WHERE task_id = $1 AND status = 'pending'
            ORDER BY created_at ASC
        """, task_id)
        
    return {"questions": [dict(q) for q in questions]}

@app.put("/tasks/{task_id}/questions/{question_id}")
async def answer_question(task_id: str, question_id: str, response_data: dict):
    """Answer a human-in-the-loop question"""
    
    # Update database
    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE task_questions 
            SET human_response = $3, status = 'answered', answered_at = NOW()
            WHERE id = $1 AND task_id = $2
        """, question_id, task_id, response_data['response'])
    
    # Notify the waiting agent
    human_handler = HumanInTheLoopHandler(task_id, a2a_manager)
    await human_handler.receive_human_response(question_id, response_data['response'])
    
    return {"status": "question_answered"}
```

### Phase 6: Agent Sandboxing Implementation

#### 6.1 AgentSandboxManager
```python
class AgentSandboxManager:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_sandboxes: Dict[str, Sandbox] = {}
        
    async def create_sandbox(
        self, 
        agent_id: str, 
        task_id: str,
        repo_settings: dict,
        sandbox_settings: dict
    ) -> Sandbox:
        """Create isolated sandbox for agent task execution"""
        
        sandbox_id = f"agent-{agent_id}-task-{task_id}"
        
        # Prepare container configuration
        container_config = {
            'image': sandbox_settings['base_image'],
            'name': sandbox_id,
            'detach': True,
            'working_dir': '/workspaces',
            'environment': {
                'AGENT_ID': agent_id,
                'TASK_ID': task_id,
                'ANTHROPIC_API_KEY': os.environ['ANTHROPIC_API_KEY'],
                'GITHUB_TOKEN': self.decrypt_token(repo_settings['github_token'])
            },
            'volumes': {
                f'agent-workspace-{agent_id}': {
                    'bind': '/workspaces',
                    'mode': 'rw'
                }
            },
            'mem_limit': sandbox_settings['resource_limits']['memory'],
            'cpu_count': self.parse_cpu_limit(sandbox_settings['resource_limits']['cpu']),
            'network_mode': 'bridge',  # Isolated network
            'security_opt': ['no-new-privileges:true'],
            'cap_drop': ['ALL'],
            'cap_add': ['DAC_OVERRIDE'],  # Minimal capabilities
            'read_only': False,  # Need write access for code generation
            'tmpfs': {'/tmp': 'rw,noexec,nosuid,size=1g'}
        }
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        # Create sandbox object
        sandbox = Sandbox(
            id=sandbox_id,
            agent_id=agent_id,
            task_id=task_id,
            container=container,
            workspace_path=f"/workspaces/{task_id}",
            created_at=datetime.now()
        )
        
        self.active_sandboxes[sandbox_id] = sandbox
        
        # Setup auto-cleanup
        cleanup_time = self.parse_cleanup_time(sandbox_settings['auto_cleanup'])
        asyncio.create_task(self.schedule_cleanup(sandbox_id, cleanup_time))
        
        return sandbox
        
    async def destroy_sandbox(self, sandbox_id: str):
        """Destroy sandbox and cleanup resources"""
        if sandbox_id in self.active_sandboxes:
            sandbox = self.active_sandboxes[sandbox_id]
            
            try:
                # Stop and remove container
                sandbox.container.stop(timeout=30)
                sandbox.container.remove()
                
                # Remove volume
                try:
                    volume = self.docker_client.volumes.get(f'agent-workspace-{sandbox.agent_id}')
                    volume.remove()
                except docker.errors.NotFound:
                    pass
                    
            except Exception as e:
                logger.error(f"Error destroying sandbox {sandbox_id}: {e}")
            
            del self.active_sandboxes[sandbox_id]
```

### Phase 7: Context Transfer & A2A Enhancement

#### 7.1 Enhanced Context Transfer
```python
class ContextTransferService:
    def __init__(self, a2a_manager):
        self.a2a_manager = a2a_manager
        
    async def transfer_task_context(
        self,
        from_task_id: str,
        to_task_id: str,
        context_data: dict,
        context_type: str = "task_results"
    ):
        """Transfer context between tasks"""
        
        # Get task information
        from_task = await self.a2a_manager.get_task(from_task_id)
        to_task = await self.a2a_manager.get_task(to_task_id)
        
        # Create context transfer message
        await self.a2a_manager.send_message(
            sender_agent_id=from_task.assigned_agent_id,
            recipient_agent_id=to_task.assigned_agent_id,
            message_type=MessageType.ARTIFACT,
            content=f"Context transfer from task {from_task.title}",
            data={
                "context_type": context_type,
                "context_data": context_data,
                "source_task_id": from_task_id,
                "transfer_timestamp": datetime.now().isoformat()
            },
            task_id=to_task_id
        )
        
        # Store context in target task
        async with self.a2a_manager.pool.acquire() as conn:
            await conn.execute("""
                UPDATE a2a_tasks 
                SET task_data = jsonb_set(
                    task_data, 
                    '{context,transferred_data}', 
                    $2::jsonb
                )
                WHERE task_id = $1
            """, to_task_id, json.dumps(context_data))
```

## Integration Points & Data Flow

### Task Lifecycle with Dependencies
```
1. Task Creation → Dependency Analysis → Execution Planning
2. Ready Tasks → Agent Assignment → Sandbox Creation  
3. Repository Setup → Feature Branch Creation
4. Development Loop:
   - Claude Code execution
   - Git commits
   - Human-in-the-loop questions
   - Context updates via A2A
5. Task Completion → PR Creation → Dependency Resolution
6. Trigger Dependent Tasks → Context Transfer → Repeat
```

### Inter-Agent Communication Flow
```
Agent A completes Task 1
    ↓
A2A Protocol notifies completion
    ↓  
DependencyManager resolves dependent tasks
    ↓
Context transferred to Agent B for Task 2
    ↓
Agent B receives task with context
    ↓
Agent B starts execution in new sandbox
```

## Files to Create/Modify

### New Files
- `services/orchestrator/task_execution_engine.py`
- `services/orchestrator/task_processor.py`
- `services/orchestrator/git_workflow_manager.py`
- `services/orchestrator/sandbox_manager.py`
- `services/orchestrator/dependency_manager.py`
- `services/orchestrator/context_transfer_service.py`
- `services/orchestrator/human_in_the_loop.py`
- `services/orchestrator/migrations/add_autonomous_execution_schema.sql`
- `containers/dev-base/Dockerfile`
- `containers/dev-python/Dockerfile`
- `containers/dev-typescript/Dockerfile`
- `containers/dev-react/Dockerfile`

### Modified Files
- `services/orchestrator/agent_manager.py` (add repository & sandbox settings)
- `services/orchestrator/claude_code_wrapper.py` (enhance for repository context)
- `services/orchestrator/task_queue.py` (trigger background execution)
- `services/orchestrator/a2a_protocol.py` (add dependency management)
- `hierarchy_endpoints.py` (add chat and question APIs)
- `services/ui-react/src/components/TaskDetailsPage.tsx` (chat interface)
- `services/ui-react/src/components/HumanResponseInput.tsx`
- `services/ui-react/src/components/DependencyGraph.tsx`

## Success Criteria

### Functional Requirements
1. ✅ **Tasks automatically progress**: "pending" → "in_progress" → "completed"
2. ✅ **Autonomous Git workflow**: Feature branches, commits, PRs created automatically
3. ✅ **Human-in-the-loop integration**: Agent questions appear in UI, humans can respond
4. ✅ **Real-time chat interface**: Live development progress visible to humans
5. ✅ **Dependency management**: Sequential and parallel task execution
6. ✅ **Context transfer**: Information flows between dependent tasks and agents
7. ✅ **Secure sandboxing**: Agents work in isolated environments
8. ✅ **Multi-agent coordination**: Multiple agents work simultaneously on different tasks
9. ✅ **Error recovery**: Failed tasks can be retried or reassigned

### Technical Requirements  
1. ✅ **Resource management**: CPU/memory limits per sandbox
2. ✅ **Security isolation**: No cross-sandbox access
3. ✅ **Scalability**: Support 10+ concurrent agent executions
4. ✅ **Monitoring**: Real-time task progress and agent status
5. ✅ **Audit trail**: Complete history of task execution and decisions

### Business Requirements
1. ✅ **Code quality**: All generated code includes tests and documentation
2. ✅ **Review process**: PRs created for human review before merge
3. ✅ **Compliance**: Git history maintains proper attribution
4. ✅ **Productivity**: Reduce human development time by 60%+
5. ✅ **Reliability**: 95%+ task completion rate without human intervention

## Next Steps

1. **Create comprehensive documentation** (this document) ✅
2. **Implement Phase 1**: Agent sandboxing and repository integration
3. **Implement Phase 2**: Git workflow and enhanced Claude Code wrapper
4. **Implement Phase 3**: Task dependency management and A2A enhancements
5. **Implement Phase 4**: Background execution engine
6. **Implement Phase 5**: Human-in-the-loop system
7. **Integration testing** with real development tasks
8. **Performance optimization** and scaling
9. **UI enhancements** for monitoring and interaction
10. **Production deployment** and monitoring setup

This comprehensive plan transforms FuzeAgent into a truly autonomous AI development platform while maintaining human oversight and quality control.