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
            ) as response:
                if response.status == 200:
                    logger.info("Successfully registered with orchestrator")
                else:
                    logger.warning(f"Registration response: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error connecting to orchestrator: {e}")
            # Continue anyway - we can work offline
            
    async def _setup_workspace(self):
        """Set up the development workspace"""
        logger.info(f"Setting up workspace: {self.workspace_path}")
        
        try:
            # Create workspace directory
            workspace = Path(self.workspace_path)
            workspace.mkdir(parents=True, exist_ok=True)
            
            # Change to workspace directory
            os.chdir(self.workspace_path)
            
            # Clone repository if specified
            if self.repository_url:
                await self._clone_repository()
                
            logger.info("Workspace setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up workspace: {e}")
            raise
            
    async def _clone_repository(self):
        """Clone the repository into workspace"""
        logger.info(f"Cloning repository: {self.repository_url}")
        
        try:
            # Configure git if token provided
            if self.github_token:
                await self._run_command([
                    'git', 'config', '--global', 'credential.helper', 
                    f'!echo username={self.github_token}; echo password='
                ])
                
            # Clone repository
            result = await self._run_command(['git', 'clone', self.repository_url, '.'])
            
            if result['exit_code'] == 0:
                logger.info("Repository cloned successfully")
            else:
                logger.error(f"Failed to clone repository: {result['output']}")
                
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            
    async def _main_loop(self):
        """Main execution loop"""
        logger.info("Starting main execution loop")
        
        while self.running:
            try:
                # Check for new tasks from orchestrator
                task = await self._get_next_task()
                
                if task:
                    logger.info(f"Received task: {task.get('title', 'Untitled')}")
                    await self._execute_task(task)
                else:
                    # No task - wait a bit
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
                
        logger.info("Main execution loop stopped")
        
    async def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from orchestrator"""
        try:
            if not self.session:
                return None
                
            async with self.session.get(
                f"{self.orchestrator_url}/agents/{self.agent_id}/next-task"
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 204:
                    # No tasks available
                    return None
                else:
                    logger.warning(f"Error getting next task: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting next task: {e}")
            return None
            
    async def _execute_task(self, task: Dict[str, Any]):
        """Execute a development task using Claude Code CLI"""
        task_id = task.get('id', 'unknown')
        task_title = task.get('title', 'Untitled Task')
        task_description = task.get('description', '')
        
        logger.info(f"Executing task {task_id}: {task_title}")
        
        try:
            # Update task status
            await self._update_task_status(task_id, 'executing')
            
            # Create feature branch
            branch_name = f"feature/agent-{self.agent_id[:8]}-task-{task_id[:8]}"
            await self._create_git_branch(branch_name)
            
            # Execute task using Claude Code CLI
            result = await self._execute_with_claude(task_description)
            
            if result['success']:
                # Commit changes
                commit_message = f"🤖 {task_title}\n\n{task_description[:200]}...\n\nGenerated by FuzeAgent autonomous development."
                await self._commit_changes(commit_message)
                
                # Update task status
                await self._update_task_status(task_id, 'completed', {
                    'branch': branch_name,
                    'files_modified': result.get('files_modified', []),
                    'execution_time': result.get('execution_time', 0)
                })
                
                logger.info(f"✅ Task {task_id} completed successfully")
                
            else:
                # Task failed
                await self._update_task_status(task_id, 'failed', {
                    'error': result.get('error', 'Unknown error'),
                    'branch': branch_name
                })
                
                logger.error(f"❌ Task {task_id} failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            await self._update_task_status(task_id, 'failed', {'error': str(e)})
            
    async def _execute_with_claude(self, task_description: str) -> Dict[str, Any]:
        """Execute task using Claude Code CLI"""
        logger.info("Executing task with Claude Code CLI")
        
        if not self.claude_cli_initialized:
            return {
                'success': False,
                'error': 'Claude CLI not initialized'
            }
            
        try:
            start_time = time.time()
            
            # Use Claude Code CLI to execute the task
            # This is a simplified approach - in practice you'd want more sophisticated prompting
            claude_prompt = f"""
I need you to help me complete this development task:

{task_description}

Please:
1. Analyze the current codebase and understand the requirements
2. Implement the necessary changes
3. Write appropriate tests
4. Ensure code quality and best practices

Work in the current directory: {os.getcwd()}
"""
            
            # Execute Claude Code CLI
            result = await self._run_command([
                'claude', 'code', '--prompt', claude_prompt, 
                '--workspace', self.workspace_path
            ])
            
            execution_time = time.time() - start_time
            
            if result['exit_code'] == 0:
                # Parse output to determine what files were modified
                files_modified = await self._get_modified_files()
                
                return {
                    'success': True,
                    'output': result['output'],
                    'files_modified': files_modified,
                    'execution_time': execution_time
                }
            else:
                return {
                    'success': False,
                    'error': result['output'],
                    'execution_time': execution_time
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _create_git_branch(self, branch_name: str):
        """Create and checkout a new git branch"""
        try:
            # Check if we're in a git repository
            result = await self._run_command(['git', 'status'])
            if result['exit_code'] != 0:
                logger.warning("Not in a git repository - skipping branch creation")
                return
                
            # Create and checkout branch
            result = await self._run_command(['git', 'checkout', '-b', branch_name])
            if result['exit_code'] == 0:
                logger.info(f"Created and checked out branch: {branch_name}")
            else:
                logger.warning(f"Failed to create branch: {result['output']}")
                
        except Exception as e:
            logger.error(f"Error creating git branch: {e}")
            
    async def _commit_changes(self, commit_message: str):
        """Commit changes to git"""
        try:
            # Add all changes
            await self._run_command(['git', 'add', '.'])
            
            # Check if there are changes to commit
            result = await self._run_command(['git', 'diff', '--staged', '--name-only'])
            if not result['output'].strip():
                logger.info("No changes to commit")
                return
                
            # Configure git user
            await self._run_command(['git', 'config', 'user.name', f'FuzeAgent-{self.agent_id[:8]}'])
            await self._run_command(['git', 'config', 'user.email', f'agent-{self.agent_id}@fuzeagent.ai'])
            
            # Commit changes
            result = await self._run_command(['git', 'commit', '-m', commit_message])
            
            if result['exit_code'] == 0:
                logger.info("Changes committed successfully")
            else:
                logger.error(f"Failed to commit changes: {result['output']}")
                
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            
    async def _get_modified_files(self) -> List[str]:
        """Get list of modified files"""
        try:
            result = await self._run_command(['git', 'diff', '--name-only', 'HEAD~1'])
            if result['exit_code'] == 0:
                return [f.strip() for f in result['output'].split('\n') if f.strip()]
            else:
                return []
        except Exception:
            return []
            
    async def _update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Update task status in orchestrator"""
        try:
            if not self.session:
                return
                
            async with self.session.put(
                f"{self.orchestrator_url}/tasks/{task_id}",
                json={
                    'status': status,
                    'result': result or {},
                    'updated_by': self.agent_id,
                    'updated_at': datetime.now().isoformat()
                }
            ) as response:
                if response.status == 200:
                    logger.info(f"Task {task_id} status updated to {status}")
                else:
                    logger.warning(f"Failed to update task status: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            
    async def _report_error(self, error_message: str):
        """Report error to orchestrator"""
        try:
            if not self.session:
                return
                
            async with self.session.post(
                f"{self.orchestrator_url}/agents/{self.agent_id}/error",
                json={
                    'error': error_message,
                    'timestamp': datetime.now().isoformat(),
                    'sandbox_id': self.sandbox_id
                }
            ) as response:
                if response.status == 200:
                    logger.info("Error reported to orchestrator")
                    
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
            
    async def _run_command(self, args: List[str], env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Run a shell command asynchronously"""
        try:
            command_env = os.environ.copy()
            if env:
                command_env.update(env)
                
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=command_env
            )
            
            stdout, _ = await process.communicate()
            
            return {
                'exit_code': process.returncode,
                'output': stdout.decode('utf-8', errors='replace'),
                'success': process.returncode == 0
            }
            
        except Exception as e:
            return {
                'exit_code': -1,
                'output': str(e),
                'success': False
            }
            
    async def _cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up agent resources")
        
        if self.websocket:
            await self.websocket.close()
            
        if self.session:
            await self.session.close()
            
        logger.info("Agent cleanup complete")


async def main():
    """Main entry point"""
    agent = AutonomousAgent()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
    finally:
        await agent.stop()


if __name__ == '__main__':
    asyncio.run(main())