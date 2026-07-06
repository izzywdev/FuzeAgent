"""
Agent Sandbox Manager for FuzeAgent Autonomous Execution

Manages Docker containers for secure, isolated agent execution environments.
Each agent gets its own sandboxed container with resource limits and security constraints.
"""

import asyncio
import docker
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .database import get_db_connection

logger = logging.getLogger(__name__)


class SandboxStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


@dataclass
class Sandbox:
    """Represents an agent sandbox container"""

    id: str
    sandbox_id: str
    agent_id: str
    task_id: str
    container_id: Optional[str]
    status: SandboxStatus
    workspace_path: str
    resource_limits: Dict[str, Any]
    created_at: datetime
    destroyed_at: Optional[datetime] = None
    container: Optional[Any] = None  # Docker container object


@dataclass
class SandboxConfig:
    """Configuration for creating a sandbox"""

    base_image: str
    resource_limits: Dict[str, Any]
    environment_vars: Dict[str, str]
    volumes: Dict[str, Dict[str, str]]
    network_mode: str = "bridge"
    security_opts: List[str] = None
    capabilities: Dict[str, List[str]] = None
    auto_cleanup_hours: int = 24


class AgentSandboxManager:
    """
    Manages Docker containers for agent execution environments.

    Features:
    - Secure container isolation
    - Resource limits (CPU, memory, disk)
    - Automatic cleanup
    - Workspace management
    - Network isolation
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker not available, sandbox features disabled: {e}")
            self.docker_client = None
        self.active_sandboxes: Dict[str, Sandbox] = {}
        self.cleanup_task: Optional[asyncio.Task] = None

        # Default template configurations
        self.template_configs = {
            "python_developer": {
                "base_image": "fuzeagent/dev-python:latest",
                "resource_limits": {"memory": "2Gi", "cpu": "1.0", "disk": "10Gi"},
            },
            "typescript_developer": {
                "base_image": "fuzeagent/dev-typescript:latest",
                "resource_limits": {"memory": "2Gi", "cpu": "1.0", "disk": "10Gi"},
            },
            "react_developer": {
                "base_image": "fuzeagent/dev-react:latest",
                "resource_limits": {"memory": "3Gi", "cpu": "1.5", "disk": "15Gi"},
            },
            "devops_engineer": {
                "base_image": "fuzeagent/dev-base:latest",
                "resource_limits": {"memory": "4Gi", "cpu": "2.0", "disk": "20Gi"},
            },
        }

    async def start(self):
        """Start the sandbox manager"""
        logger.info("Starting AgentSandboxManager")

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Load existing sandboxes from database
        await self._load_existing_sandboxes()

        logger.info(
            f"AgentSandboxManager started with {len(self.active_sandboxes)} active sandboxes"
        )

    async def stop(self):
        """Stop the sandbox manager"""
        logger.info("Stopping AgentSandboxManager")

        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Destroy all active sandboxes
        sandbox_ids = list(self.active_sandboxes.keys())
        for sandbox_id in sandbox_ids:
            try:
                await self.destroy_sandbox(sandbox_id)
            except Exception as e:
                logger.error(f"Error destroying sandbox {sandbox_id}: {e}")

        logger.info("AgentSandboxManager stopped")

    async def create_sandbox(
        self,
        agent_id: str,
        task_id: str,
        agent_template: str,
        repository_settings: Dict[str, Any],
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> Sandbox:
        """Create a new sandbox for an agent"""

        sandbox_id = f"agent-{agent_id[:8]}-task-{task_id[:8]}-{uuid.uuid4().hex[:8]}"

        logger.info(f"Creating sandbox {sandbox_id} for agent {agent_id}")

        try:
            # Get template configuration
            template_config = self.template_configs.get(
                agent_template,
                self.template_configs["python_developer"],  # Default fallback
            )

            # Merge with custom settings
            if custom_settings:
                template_config = {**template_config, **custom_settings}

            # Create sandbox configuration
            config = await self._build_sandbox_config(
                agent_id, task_id, template_config, repository_settings
            )

            # Create sandbox record
            sandbox = Sandbox(
                id=str(uuid.uuid4()),
                sandbox_id=sandbox_id,
                agent_id=agent_id,
                task_id=task_id,
                container_id=None,
                status=SandboxStatus.CREATING,
                workspace_path=f"/workspaces/{task_id}",
                resource_limits=config.resource_limits,
                created_at=datetime.now(),
            )

            # Store in database
            await self._store_sandbox(sandbox)

            # Create Docker container
            container = await self._create_container(sandbox, config)
            sandbox.container = container
            sandbox.container_id = container.id
            sandbox.status = SandboxStatus.RUNNING

            # Update database
            await self._update_sandbox_status(
                sandbox.id, SandboxStatus.RUNNING, container.id
            )

            # Store in memory
            self.active_sandboxes[sandbox_id] = sandbox

            logger.info(f"✅ Sandbox {sandbox_id} created successfully")
            return sandbox

        except Exception as e:
            logger.error(f"❌ Failed to create sandbox {sandbox_id}: {e}")
            # Update status to ERROR
            if "sandbox" in locals():
                sandbox.status = SandboxStatus.ERROR
                await self._update_sandbox_status(sandbox.id, SandboxStatus.ERROR)
            raise

    async def destroy_sandbox(self, sandbox_id: str):
        """Destroy a sandbox and cleanup resources"""

        if sandbox_id not in self.active_sandboxes:
            logger.warning(f"Sandbox {sandbox_id} not found in active sandboxes")
            return

        sandbox = self.active_sandboxes[sandbox_id]
        logger.info(f"Destroying sandbox {sandbox_id}")

        try:
            sandbox.status = SandboxStatus.DESTROYING
            await self._update_sandbox_status(sandbox.id, SandboxStatus.DESTROYING)

            # Stop and remove container
            if sandbox.container:
                try:
                    sandbox.container.stop(timeout=30)
                    sandbox.container.remove(force=True)
                    logger.info(f"Container {sandbox.container_id} stopped and removed")
                except docker.errors.NotFound:
                    logger.warning(f"Container {sandbox.container_id} not found")
                except Exception as e:
                    logger.error(
                        f"Error removing container {sandbox.container_id}: {e}"
                    )

            # Remove workspace volume
            try:
                volume_name = f"agent-workspace-{sandbox.agent_id}-{sandbox.task_id}"
                volume = self.docker_client.volumes.get(volume_name)
                volume.remove()
                logger.info(f"Volume {volume_name} removed")
            except docker.errors.NotFound:
                logger.warning(f"Volume {volume_name} not found")
            except Exception as e:
                logger.error(f"Error removing volume: {e}")

            # Update database
            sandbox.status = SandboxStatus.DESTROYED
            sandbox.destroyed_at = datetime.now()
            await self._update_sandbox_status(
                sandbox.id, SandboxStatus.DESTROYED, destroyed_at=sandbox.destroyed_at
            )

            # Remove from active sandboxes
            del self.active_sandboxes[sandbox_id]

            logger.info(f"✅ Sandbox {sandbox_id} destroyed successfully")

        except Exception as e:
            logger.error(f"❌ Error destroying sandbox {sandbox_id}: {e}")
            sandbox.status = SandboxStatus.ERROR
            await self._update_sandbox_status(sandbox.id, SandboxStatus.ERROR)

    async def get_sandbox(self, sandbox_id: str) -> Optional[Sandbox]:
        """Get sandbox by ID"""
        return self.active_sandboxes.get(sandbox_id)

    async def list_sandboxes(
        self, agent_id: Optional[str] = None, status: Optional[SandboxStatus] = None
    ) -> List[Sandbox]:
        """List sandboxes with optional filtering"""

        sandboxes = list(self.active_sandboxes.values())

        if agent_id:
            sandboxes = [s for s in sandboxes if s.agent_id == agent_id]

        if status:
            sandboxes = [s for s in sandboxes if s.status == status]

        return sandboxes

    async def execute_command(
        self, sandbox_id: str, command: str, working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command in a sandbox"""

        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox or not sandbox.container:
            raise ValueError(f"Sandbox {sandbox_id} not found or not running")

        try:
            # Execute command
            exec_result = sandbox.container.exec_run(
                command,
                workdir=working_dir or sandbox.workspace_path,
                user="agent",
                environment={"HOME": "/home/agent", "USER": "agent"},
            )

            return {
                "exit_code": exec_result.exit_code,
                "output": exec_result.output.decode("utf-8"),
                "success": exec_result.exit_code == 0,
            }

        except Exception as e:
            logger.error(f"Error executing command in sandbox {sandbox_id}: {e}")
            return {"exit_code": -1, "output": str(e), "success": False}

    async def _build_sandbox_config(
        self,
        agent_id: str,
        task_id: str,
        template_config: Dict[str, Any],
        repository_settings: Dict[str, Any],
    ) -> SandboxConfig:
        """Build sandbox configuration"""

        # Parse resource limits
        resource_limits = template_config["resource_limits"]
        memory_limit = self._parse_memory_limit(resource_limits["memory"])
        cpu_limit = float(resource_limits["cpu"])

        # Create workspace volume
        volume_name = f"agent-workspace-{agent_id}-{task_id}"

        # Environment variables
        env_vars = {
            "AGENT_ID": agent_id,
            "TASK_ID": task_id,
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
            "FUZE_AGENT_WORKSPACE": f"/workspaces/{task_id}",
            "HOME": "/home/agent",
            "USER": "agent",
        }

        # Add repository settings to environment
        if repository_settings:
            if "github_token" in repository_settings:
                env_vars["GITHUB_TOKEN"] = repository_settings["github_token"]
            if "repository_url" in repository_settings:
                env_vars["REPOSITORY_URL"] = repository_settings["repository_url"]

        return SandboxConfig(
            base_image=template_config["base_image"],
            resource_limits={
                "memory": memory_limit,
                "cpu_count": max(1, int(cpu_limit)),
                "cpu_shares": int(cpu_limit * 1024),  # Docker CPU shares
            },
            environment_vars=env_vars,
            volumes={volume_name: {"bind": f"/workspaces/{task_id}", "mode": "rw"}},
            security_opts=[
                "no-new-privileges:true",
                "seccomp:unconfined",  # Needed for some development tools
            ],
            capabilities={
                "drop": ["ALL"],
                "add": ["DAC_OVERRIDE", "SETGID", "SETUID"],  # Minimal capabilities
            },
            auto_cleanup_hours=24,
        )

    async def _create_container(self, sandbox: Sandbox, config: SandboxConfig):
        """Create Docker container"""

        # Create workspace volume
        volume_name = f"agent-workspace-{sandbox.agent_id}-{sandbox.task_id}"
        try:
            self.docker_client.volumes.create(name=volume_name, driver="local")
        except docker.errors.APIError as e:
            if "already exists" not in str(e):
                raise

        # Container configuration
        container_config = {
            "image": config.base_image,
            "name": sandbox.sandbox_id,
            "detach": True,
            "user": "agent",
            "working_dir": sandbox.workspace_path,
            "environment": config.environment_vars,
            "volumes": config.volumes,
            "mem_limit": config.resource_limits["memory"],
            "cpu_count": config.resource_limits["cpu_count"],
            "cpu_shares": config.resource_limits["cpu_shares"],
            "network_mode": config.network_mode,
            "security_opt": config.security_opts,
            "cap_drop": config.capabilities["drop"],
            "cap_add": config.capabilities["add"],
            "read_only": False,  # Need write access for development
            "tmpfs": {"/tmp": "rw,noexec,nosuid,size=1g"},
            "labels": {
                "fuzeagent.sandbox": "true",
                "fuzeagent.agent_id": sandbox.agent_id,
                "fuzeagent.task_id": sandbox.task_id,
                "fuzeagent.created_at": sandbox.created_at.isoformat(),
            },
        }

        # Create and start container
        container = self.docker_client.containers.run(**container_config)

        logger.info(
            f"Container {container.id} created for sandbox {sandbox.sandbox_id}"
        )
        return container

    def _parse_memory_limit(self, memory_str: str) -> str:
        """Parse memory limit string (e.g., '2Gi' -> '2g')"""
        memory_str = memory_str.lower()
        if memory_str.endswith("gi"):
            return memory_str.replace("gi", "g")
        elif memory_str.endswith("mi"):
            return memory_str.replace("mi", "m")
        return memory_str

    async def _store_sandbox(self, sandbox: Sandbox):
        """Store sandbox in database"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_sandboxes (
                    id, sandbox_id, agent_id, task_id, container_id,
                    status, workspace_path, resource_limits, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                sandbox.id,
                sandbox.sandbox_id,
                sandbox.agent_id,
                sandbox.task_id,
                sandbox.container_id,
                sandbox.status.value,
                sandbox.workspace_path,
                json.dumps(sandbox.resource_limits),
                sandbox.created_at,
            )

    async def _update_sandbox_status(
        self,
        sandbox_id: str,
        status: SandboxStatus,
        container_id: Optional[str] = None,
        destroyed_at: Optional[datetime] = None,
    ):
        """Update sandbox status in database"""
        async with get_db_connection() as conn:
            if destroyed_at:
                await conn.execute(
                    """
                    UPDATE agent_sandboxes 
                    SET status = $2, container_id = $3, destroyed_at = $4
                    WHERE id = $1
                """,
                    sandbox_id,
                    status.value,
                    container_id,
                    destroyed_at,
                )
            else:
                await conn.execute(
                    """
                    UPDATE agent_sandboxes 
                    SET status = $2, container_id = $3
                    WHERE id = $1
                """,
                    sandbox_id,
                    status.value,
                    container_id,
                )

    async def _load_existing_sandboxes(self):
        """Load existing sandboxes from database on startup"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM agent_sandboxes 
                WHERE status IN ('running', 'paused') 
                AND destroyed_at IS NULL
            """
            )

            for row in rows:
                try:
                    # Try to get the container
                    container = None
                    if row["container_id"]:
                        try:
                            container = self.docker_client.containers.get(
                                row["container_id"]
                            )
                        except docker.errors.NotFound:
                            # Container no longer exists, mark as destroyed
                            await self._update_sandbox_status(
                                row["id"],
                                SandboxStatus.DESTROYED,
                                destroyed_at=datetime.now(),
                            )
                            continue

                    sandbox = Sandbox(
                        id=row["id"],
                        sandbox_id=row["sandbox_id"],
                        agent_id=row["agent_id"],
                        task_id=row["task_id"],
                        container_id=row["container_id"],
                        status=SandboxStatus(row["status"]),
                        workspace_path=row["workspace_path"],
                        resource_limits=json.loads(row["resource_limits"]),
                        created_at=row["created_at"],
                        destroyed_at=row["destroyed_at"],
                        container=container,
                    )

                    self.active_sandboxes[sandbox.sandbox_id] = sandbox

                except Exception as e:
                    logger.error(f"Error loading sandbox {row['sandbox_id']}: {e}")

        logger.info(f"Loaded {len(self.active_sandboxes)} existing sandboxes")

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_expired_sandboxes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired_sandboxes(self):
        """Clean up expired sandboxes"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        expired_sandboxes = [
            sandbox
            for sandbox in self.active_sandboxes.values()
            if sandbox.created_at < cutoff_time
        ]

        for sandbox in expired_sandboxes:
            try:
                logger.info(f"Cleaning up expired sandbox {sandbox.sandbox_id}")
                await self.destroy_sandbox(sandbox.sandbox_id)
            except Exception as e:
                logger.error(f"Error cleaning up sandbox {sandbox.sandbox_id}: {e}")

        if expired_sandboxes:
            logger.info(f"Cleaned up {len(expired_sandboxes)} expired sandboxes")
