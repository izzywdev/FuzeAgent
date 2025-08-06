#!/usr/bin/env python3
"""
Autonomous Agent Process for FuzeAgent Sandbox Containers

This script runs inside each sandbox container and provides the autonomous
development capabilities using Claude Code CLI. It communicates with the
orchestrator and executes development tasks independently.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/agent.log')
    ]
)
logger = logging.getLogger(__name__)

class AutonomousAgent:
    """
    Autonomous agent that runs inside sandbox containers.
    
    Features:
    - Claude Code CLI integration for development tasks
    - WebSocket communication with orchestrator
    - Git workflow management
    - Human-in-the-loop interactions
    - Progress reporting and error handling
    """
    
    def __init__(self):
        # Agent configuration from environment
        self.agent_id = os.environ.get('AGENT_ID', str(uuid.uuid4()))
        self.task_id = os.environ.get('TASK_ID', 'unknown')
        self.sandbox_id = os.environ.get('SANDBOX_ID', 'unknown')
        self.orchestrator_url = os.environ.get('ORCHESTRATOR_URL', 'http://orchestrator:8000')
        self.workspace_path = os.environ.get('FUZE_AGENT_WORKSPACE', '/workspaces')
        
        # Repository settings
        self.repository_url = os.environ.get('REPOSITORY_URL')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        # Agent state
        self.running = False
        self.current_task: Optional[Dict[str, Any]] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Claude Code CLI configuration
        self.claude_cli_initialized = False
        
    async def start(self):
        """Start the autonomous agent"""
        logger.info(f"Starting autonomous agent {self.agent_id} for task {self.task_id}")
        
        try:
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            
            # Initialize Claude Code CLI
            await self._initialize_claude_cli()
            
            # Connect to orchestrator
            await self._connect_to_orchestrator()
            
            # Set up workspace
            await self._setup_workspace()
            
            # Start main execution loop
            self.running = True
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Error starting agent: {e}")
            await self._report_error(str(e))
            
        finally:
            await self._cleanup()
            
    async def stop(self):
        """Stop the autonomous agent"""
        logger.info("Stopping autonomous agent")
        self.running = False
        
    async def _initialize_claude_cli(self):
        """Initialize Claude Code CLI"""
        logger.info("Initializing Claude Code CLI")
        
        try:
            # Check if Claude CLI is installed
            result = await self._run_command(['claude', '--version'])
            if result['exit_code'] != 0:
                raise RuntimeError("Claude CLI not found in container")
                
            logger.info(f"Claude CLI version: {result['output'].strip()}")
            
            # Configure Claude CLI with API key
            if self.anthropic_api_key:
                # Set the API key
                env = os.environ.copy()
                env['ANTHROPIC_API_KEY'] = self.anthropic_api_key
                
                # Initialize Claude configuration
                result = await self._run_command(['claude', 'auth', 'login'], env=env)
                if result['exit_code'] == 0:
                    logger.info("Claude CLI authentication successful")
                    self.claude_cli_initialized = True
                else:
                    logger.warning(f"Claude CLI auth warning: {result['output']}")
                    # Continue anyway - might already be authenticated
                    self.claude_cli_initialized = True
            else:
                logger.warning("No ANTHROPIC_API_KEY provided")
                
        except Exception as e:
            logger.error(f"Error initializing Claude CLI: {e}")
            raise
            
    async def _connect_to_orchestrator(self):
        """Connect to orchestrator via WebSocket"""
        logger.info(f"Connecting to orchestrator: {self.orchestrator_url}")
        
        try:
            # Register with orchestrator
            async with self.session.post(
                f"{self.orchestrator_url}/agents/{self.agent_id}/register",
                json={
                    'sandbox_id': self.sandbox_id,
                    'task_id': self.task_id,
                    'status': 'initializing',
                    'capabilities': {
                        'claude_cli': self.claude_cli_initialized,
                        'git': True,
                        'workspace_path': self.workspace_path
                    }
                }
            ) as response:\n                if response.status == 200:\n                    logger.info(\"Successfully registered with orchestrator\")\n                else:\n                    logger.warning(f\"Registration response: {response.status}\")\n                    \n        except Exception as e:\n            logger.error(f\"Error connecting to orchestrator: {e}\")\n            # Continue anyway - we can work offline\n            \n    async def _setup_workspace(self):\n        \"\"\"Set up the development workspace\"\"\"\n        logger.info(f\"Setting up workspace: {self.workspace_path}\")\n        \n        try:\n            # Create workspace directory\n            workspace = Path(self.workspace_path)\n            workspace.mkdir(parents=True, exist_ok=True)\n            \n            # Change to workspace directory\n            os.chdir(self.workspace_path)\n            \n            # Clone repository if specified\n            if self.repository_url:\n                await self._clone_repository()\n                \n            logger.info(\"Workspace setup complete\")\n            \n        except Exception as e:\n            logger.error(f\"Error setting up workspace: {e}\")\n            raise\n            \n    async def _clone_repository(self):\n        \"\"\"Clone the repository into workspace\"\"\"\n        logger.info(f\"Cloning repository: {self.repository_url}\")\n        \n        try:\n            # Configure git if token provided\n            if self.github_token:\n                await self._run_command([\n                    'git', 'config', '--global', 'credential.helper', \n                    f'!echo username={self.github_token}; echo password='\n                ])\n                \n            # Clone repository\n            result = await self._run_command(['git', 'clone', self.repository_url, '.'])\n            \n            if result['exit_code'] == 0:\n                logger.info(\"Repository cloned successfully\")\n            else:\n                logger.error(f\"Failed to clone repository: {result['output']}\")\n                \n        except Exception as e:\n            logger.error(f\"Error cloning repository: {e}\")\n            \n    async def _main_loop(self):\n        \"\"\"Main execution loop\"\"\"\n        logger.info(\"Starting main execution loop\")\n        \n        while self.running:\n            try:\n                # Check for new tasks from orchestrator\n                task = await self._get_next_task()\n                \n                if task:\n                    logger.info(f\"Received task: {task.get('title', 'Untitled')}\")\n                    await self._execute_task(task)\n                else:\n                    # No task - wait a bit\n                    await asyncio.sleep(5)\n                    \n            except Exception as e:\n                logger.error(f\"Error in main loop: {e}\")\n                await asyncio.sleep(10)\n                \n        logger.info(\"Main execution loop stopped\")\n        \n    async def _get_next_task(self) -> Optional[Dict[str, Any]]:\n        \"\"\"Get next task from orchestrator\"\"\"\n        try:\n            if not self.session:\n                return None\n                \n            async with self.session.get(\n                f\"{self.orchestrator_url}/agents/{self.agent_id}/next-task\"\n            ) as response:\n                if response.status == 200:\n                    return await response.json()\n                elif response.status == 204:\n                    # No tasks available\n                    return None\n                else:\n                    logger.warning(f\"Error getting next task: {response.status}\")\n                    return None\n                    \n        except Exception as e:\n            logger.error(f\"Error getting next task: {e}\")\n            return None\n            \n    async def _execute_task(self, task: Dict[str, Any]):\n        \"\"\"Execute a development task using Claude Code CLI\"\"\"\n        task_id = task.get('id', 'unknown')\n        task_title = task.get('title', 'Untitled Task')\n        task_description = task.get('description', '')\n        \n        logger.info(f\"Executing task {task_id}: {task_title}\")\n        \n        try:\n            # Update task status\n            await self._update_task_status(task_id, 'executing')\n            \n            # Create feature branch\n            branch_name = f\"feature/agent-{self.agent_id[:8]}-task-{task_id[:8]}\"\n            await self._create_git_branch(branch_name)\n            \n            # Execute task using Claude Code CLI\n            result = await self._execute_with_claude(task_description)\n            \n            if result['success']:\n                # Commit changes\n                commit_message = f\"🤖 {task_title}\\n\\n{task_description[:200]}...\\n\\nGenerated by FuzeAgent autonomous development.\"\n                await self._commit_changes(commit_message)\n                \n                # Update task status\n                await self._update_task_status(task_id, 'completed', {\n                    'branch': branch_name,\n                    'files_modified': result.get('files_modified', []),\n                    'execution_time': result.get('execution_time', 0)\n                })\n                \n                logger.info(f\"✅ Task {task_id} completed successfully\")\n                \n            else:\n                # Task failed\n                await self._update_task_status(task_id, 'failed', {\n                    'error': result.get('error', 'Unknown error'),\n                    'branch': branch_name\n                })\n                \n                logger.error(f\"❌ Task {task_id} failed: {result.get('error')}\")\n                \n        except Exception as e:\n            logger.error(f\"Error executing task {task_id}: {e}\")\n            await self._update_task_status(task_id, 'failed', {'error': str(e)})\n            \n    async def _execute_with_claude(self, task_description: str) -> Dict[str, Any]:\n        \"\"\"Execute task using Claude Code CLI\"\"\"\n        logger.info(\"Executing task with Claude Code CLI\")\n        \n        if not self.claude_cli_initialized:\n            return {\n                'success': False,\n                'error': 'Claude CLI not initialized'\n            }\n            \n        try:\n            start_time = time.time()\n            \n            # Use Claude Code CLI to execute the task\n            # This is a simplified approach - in practice you'd want more sophisticated prompting\n            claude_prompt = f\"\"\"\nI need you to help me complete this development task:\n\n{task_description}\n\nPlease:\n1. Analyze the current codebase and understand the requirements\n2. Implement the necessary changes\n3. Write appropriate tests\n4. Ensure code quality and best practices\n\nWork in the current directory: {os.getcwd()}\n\"\"\"\n            \n            # Execute Claude Code CLI\n            result = await self._run_command([\n                'claude', 'code', '--prompt', claude_prompt, \n                '--workspace', self.workspace_path\n            ])\n            \n            execution_time = time.time() - start_time\n            \n            if result['exit_code'] == 0:\n                # Parse output to determine what files were modified\n                files_modified = await self._get_modified_files()\n                \n                return {\n                    'success': True,\n                    'output': result['output'],\n                    'files_modified': files_modified,\n                    'execution_time': execution_time\n                }\n            else:\n                return {\n                    'success': False,\n                    'error': result['output'],\n                    'execution_time': execution_time\n                }\n                \n        except Exception as e:\n            return {\n                'success': False,\n                'error': str(e)\n            }\n            \n    async def _create_git_branch(self, branch_name: str):\n        \"\"\"Create and checkout a new git branch\"\"\"\n        try:\n            # Check if we're in a git repository\n            result = await self._run_command(['git', 'status'])\n            if result['exit_code'] != 0:\n                logger.warning(\"Not in a git repository - skipping branch creation\")\n                return\n                \n            # Create and checkout branch\n            result = await self._run_command(['git', 'checkout', '-b', branch_name])\n            if result['exit_code'] == 0:\n                logger.info(f\"Created and checked out branch: {branch_name}\")\n            else:\n                logger.warning(f\"Failed to create branch: {result['output']}\")\n                \n        except Exception as e:\n            logger.error(f\"Error creating git branch: {e}\")\n            \n    async def _commit_changes(self, commit_message: str):\n        \"\"\"Commit changes to git\"\"\"\n        try:\n            # Add all changes\n            await self._run_command(['git', 'add', '.'])\n            \n            # Check if there are changes to commit\n            result = await self._run_command(['git', 'diff', '--staged', '--name-only'])\n            if not result['output'].strip():\n                logger.info(\"No changes to commit\")\n                return\n                \n            # Configure git user\n            await self._run_command(['git', 'config', 'user.name', f'FuzeAgent-{self.agent_id[:8]}'])\n            await self._run_command(['git', 'config', 'user.email', f'agent-{self.agent_id}@fuzeagent.ai'])\n            \n            # Commit changes\n            result = await self._run_command(['git', 'commit', '-m', commit_message])\n            \n            if result['exit_code'] == 0:\n                logger.info(\"Changes committed successfully\")\n            else:\n                logger.error(f\"Failed to commit changes: {result['output']}\")\n                \n        except Exception as e:\n            logger.error(f\"Error committing changes: {e}\")\n            \n    async def _get_modified_files(self) -> List[str]:\n        \"\"\"Get list of modified files\"\"\"\n        try:\n            result = await self._run_command(['git', 'diff', '--name-only', 'HEAD~1'])\n            if result['exit_code'] == 0:\n                return [f.strip() for f in result['output'].split('\\n') if f.strip()]\n            else:\n                return []\n        except Exception:\n            return []\n            \n    async def _update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):\n        \"\"\"Update task status in orchestrator\"\"\"\n        try:\n            if not self.session:\n                return\n                \n            async with self.session.put(\n                f\"{self.orchestrator_url}/tasks/{task_id}\",\n                json={\n                    'status': status,\n                    'result': result or {},\n                    'updated_by': self.agent_id,\n                    'updated_at': datetime.now().isoformat()\n                }\n            ) as response:\n                if response.status == 200:\n                    logger.info(f\"Task {task_id} status updated to {status}\")\n                else:\n                    logger.warning(f\"Failed to update task status: {response.status}\")\n                    \n        except Exception as e:\n            logger.error(f\"Error updating task status: {e}\")\n            \n    async def _report_error(self, error_message: str):\n        \"\"\"Report error to orchestrator\"\"\"\n        try:\n            if not self.session:\n                return\n                \n            async with self.session.post(\n                f\"{self.orchestrator_url}/agents/{self.agent_id}/error\",\n                json={\n                    'error': error_message,\n                    'timestamp': datetime.now().isoformat(),\n                    'sandbox_id': self.sandbox_id\n                }\n            ) as response:\n                if response.status == 200:\n                    logger.info(\"Error reported to orchestrator\")\n                    \n        except Exception as e:\n            logger.error(f\"Failed to report error: {e}\")\n            \n    async def _run_command(self, args: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:\n        \"\"\"Run a shell command asynchronously\"\"\"\n        try:\n            command_env = os.environ.copy()\n            if env:\n                command_env.update(env)\n                \n            process = await asyncio.create_subprocess_exec(\n                *args,\n                stdout=asyncio.subprocess.PIPE,\n                stderr=asyncio.subprocess.STDOUT,\n                env=command_env\n            )\n            \n            stdout, _ = await process.communicate()\n            \n            return {\n                'exit_code': process.returncode,\n                'output': stdout.decode('utf-8', errors='replace'),\n                'success': process.returncode == 0\n            }\n            \n        except Exception as e:\n            return {\n                'exit_code': -1,\n                'output': str(e),\n                'success': False\n            }\n            \n    async def _cleanup(self):\n        \"\"\"Clean up resources\"\"\"\n        logger.info(\"Cleaning up agent resources\")\n        \n        if self.websocket:\n            await self.websocket.close()\n            \n        if self.session:\n            await self.session.close()\n            \n        logger.info(\"Agent cleanup complete\")\n\n\nasync def main():\n    \"\"\"Main entry point\"\"\"\n    agent = AutonomousAgent()\n    \n    try:\n        await agent.start()\n    except KeyboardInterrupt:\n        logger.info(\"Received interrupt signal\")\n    except Exception as e:\n        logger.error(f\"Unhandled error: {e}\")\n    finally:\n        await agent.stop()\n\n\nif __name__ == '__main__':\n    asyncio.run(main())"