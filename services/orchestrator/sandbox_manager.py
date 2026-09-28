"""
Agent Sandbox Manager for FuzeAgent Autonomous Execution

Manages Docker containers for secure, isolated agent execution environments.
Each agent gets its own sandboxed container with resource limits and security constraints.
"""

import asyncio
import json
import logging
import os
import posixpath
import re
import shlex
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import docker
except ImportError:  # Docker stays optional for the remote provider.
    docker = None

from .database import get_db_connection
from .fuze_sandbox_client import FuzeSandboxClient

logger = logging.getLogger(__name__)


class SandboxStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
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
        self.provider = os.environ.get("FUZE_SANDBOX_PROVIDER", "docker").strip().lower()
        if self.provider not in {"docker", "fuze-sandbox"}:
            raise ValueError("FUZE_SANDBOX_PROVIDER must be 'docker' or 'fuze-sandbox'")
        self.remote_client = None
        self.remote_image = ""
        self.remote_profile = "agent-small"
        if self.provider == "fuze-sandbox":
            base_url = os.environ.get("FUZE_SANDBOX_API_URL", "")
            api_key = os.environ.get("FUZE_SANDBOX_API_KEY", "")
            self.remote_image = os.environ.get("FUZE_SANDBOX_IMAGE", "")
            self.remote_profile = os.environ.get("FUZE_SANDBOX_PROFILE", "agent-small")
            if not self.remote_image:
                raise ValueError("FUZE_SANDBOX_IMAGE must be set for the Fuze Sandbox provider")
            self.remote_client = FuzeSandboxClient(base_url, api_key)
            self.docker_client = None
        else:
            try:
                if docker is None:
                    raise RuntimeError("Docker Python SDK is not installed")
                self.docker_client = docker.from_env()
                self.docker_client.ping()  # force eager connection; lazy SDK won't fail until first API call
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

        if self.provider == "fuze-sandbox":
            if not self.remote_client:
                raise RuntimeError("Fuze Sandbox provider is not configured")
            readiness = await self.remote_client.get_readiness()
            if not (readiness.get("status") == "ready"
                    and readiness.get("execution_enabled") is True
                    and readiness.get("worker") == "ready"
                    and readiness.get("machine_workspace_enabled") is True):
                raise RuntimeError("Fuze Sandbox is not ready for machine workspaces")

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

        # Remote workspaces outlive an orchestrator restart; their server-side
        # TTL and idle cleanup remain authoritative.
        if self.provider == "docker":
            sandbox_ids = list(self.active_sandboxes.keys())
            for sandbox_id in sandbox_ids:
                try:
                    await self.destroy_sandbox(sandbox_id)
                except Exception as e:
                    logger.error(f"Error destroying sandbox {sandbox_id}: {e}")
        elif self.remote_client:
            await self.remote_client.close()

        logger.info("AgentSandboxManager stopped")

    async def create_sandbox(
        self,
        agent_id: str,
        task_id: str,
        agent_template: str,
        repository_settings: Dict[str, Any],
        custom_settings: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Sandbox:
        """Create a new sandbox for an agent"""

        if self.provider == "fuze-sandbox":
            return await self._create_remote_workspace(agent_id, task_id, agent_template, ttl_seconds)

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

    async def _create_remote_workspace(self, agent_id: str, task_id: str,
                                       agent_template: str,
                                       ttl_seconds: Optional[int] = None) -> Sandbox:
        if not self.remote_client:
            raise RuntimeError("Fuze Sandbox provider is not configured")
        remote_id = None
        record = Sandbox(
            id=str(uuid.uuid4()),
            sandbox_id="pending",
            agent_id=agent_id,
            task_id=task_id,
            container_id=None,
            status=SandboxStatus.CREATING,
            workspace_path="/workspace",
            resource_limits={"profile": self.remote_profile},
            created_at=datetime.now(),
        )
        try:
            payload = {
                "name": f"fa-{uuid.uuid4().hex[:20]}",
                "image": self.remote_image,
                "kind": "workspace",
                "profile": self.remote_profile,
                "ttl_seconds": min(86400, max(60, int(
                    ttl_seconds if ttl_seconds is not None else
                    os.getenv("FUZE_SANDBOX_TTL_SECONDS", "86400")
                ))),
                "storage": os.getenv("FUZE_SANDBOX_WORKSPACE_STORAGE", "5Gi"),
                "ports": [int(port.strip()) for port in
                          os.getenv("FUZE_SANDBOX_PREVIEW_PORTS", "").split(",") if port.strip()],
            }
            created = await self.remote_client.create_sandbox(**payload)
            remote_id = created["id"]
            record.sandbox_id = remote_id
            record.container_id = f"fuze-sandbox:{remote_id}"
            await self._store_sandbox(record)
            self.active_sandboxes[remote_id] = record
            timeout = max(10, int(os.getenv("FUZE_SANDBOX_CREATE_TIMEOUT_SECONDS", "180")))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                current = await self.remote_client.get_sandbox(remote_id)
                status = current.get("status")
                if status == "running":
                    record.status = SandboxStatus.RUNNING
                    await self._update_sandbox_status(record.id, record.status, record.container_id)
                    logger.info("Fuze Sandbox workspace %s is ready for agent %s", remote_id, agent_id)
                    return record
                if status in {"failed", "deleted", "succeeded", "cancelled"}:
                    raise RuntimeError(f"Fuze Sandbox workspace entered terminal state: {status}")
                await asyncio.sleep(2)
            raise TimeoutError("Fuze Sandbox workspace did not become ready before the configured timeout")
        except Exception as exc:
            if remote_id:
                try:
                    await self.remote_client.cancel_sandbox(remote_id)
                except Exception:
                    logger.exception("Failed to cancel incomplete Fuze Sandbox workspace %s", remote_id)
                self.active_sandboxes.pop(remote_id, None)
            record.status = SandboxStatus.ERROR
            if remote_id:
                await self._update_sandbox_status(record.id, SandboxStatus.ERROR, record.container_id)
            logger.error("Fuze Sandbox workspace creation failed for agent %s: %s", agent_id, exc)
            raise

    async def create_remote_job(self, agent_id: str, task_id: str,
                                command: list[str], args: list[str] | None = None,
                                ttl_seconds: int = 3600) -> Sandbox:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            raise RuntimeError("Jobs require the Fuze Sandbox provider")
        if not command or len(command) > 32 or any(len(part) > 4096 for part in command):
            raise ValueError("Job command must contain 1-32 arguments of at most 4096 characters")
        if args and (len(args) > 64 or any(len(part) > 4096 for part in args)):
            raise ValueError("Job args must contain at most 64 arguments of at most 4096 characters")
        remote = await self.remote_client.create_sandbox(
            name=f"fa-job-{uuid.uuid4().hex[:20]}", image=self.remote_image,
            kind="job", profile=self.remote_profile,
            ttl_seconds=min(86400, max(60, int(ttl_seconds))),
            command=command, args=args or [],
        )
        remote_id = remote["id"]
        record = Sandbox(
            id=str(uuid.uuid4()), sandbox_id=remote_id, agent_id=agent_id,
            task_id=task_id, container_id=f"fuze-sandbox:{remote_id}",
            status=SandboxStatus.CREATING, workspace_path="",
            resource_limits={"profile": self.remote_profile}, created_at=datetime.now(),
        )
        await self._store_sandbox(record)
        self.active_sandboxes[remote_id] = record
        await self._refresh_remote_record(record)
        return record

    async def _refresh_remote_record(self, sandbox: Sandbox) -> None:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            return
        try:
            remote = await self.remote_client.get_sandbox(sandbox.sandbox_id)
        except Exception:
            logger.warning("Unable to refresh remote sandbox status for %s", sandbox.sandbox_id)
            return
        remote_status = remote.get("status")
        status_map = {
            "pending": SandboxStatus.CREATING,
            "queued": SandboxStatus.CREATING,
            "running": SandboxStatus.RUNNING,
            "succeeded": SandboxStatus.SUCCEEDED,
            "failed": SandboxStatus.ERROR,
            "deleting": SandboxStatus.DESTROYING,
            "deleted": SandboxStatus.DESTROYED,
        }
        mapped = status_map.get(remote_status)
        if mapped and mapped != sandbox.status:
            sandbox.status = mapped
            if mapped in {SandboxStatus.SUCCEEDED, SandboxStatus.ERROR, SandboxStatus.DESTROYED}:
                sandbox.destroyed_at = datetime.now()
            await self._update_sandbox_status(sandbox.id, mapped, sandbox.container_id,
                destroyed_at=sandbox.destroyed_at)

    async def destroy_sandbox(self, sandbox_id: str):
        """Destroy a sandbox and cleanup resources"""

        if sandbox_id not in self.active_sandboxes:
            logger.warning(f"Sandbox {sandbox_id} not found in active sandboxes")
            return

        sandbox = self.active_sandboxes[sandbox_id]
        logger.info(f"Destroying sandbox {sandbox_id}")

        if self.provider == "fuze-sandbox":
            if not self.remote_client:
                raise RuntimeError("Fuze Sandbox provider is not configured")
            sandbox.status = SandboxStatus.DESTROYING
            await self._update_sandbox_status(sandbox.id, sandbox.status, sandbox.container_id)
            await self.remote_client.cancel_sandbox(sandbox.sandbox_id)
            deadline = time.monotonic() + max(10, int(os.getenv("FUZE_SANDBOX_DELETE_TIMEOUT_SECONDS", "120")))
            while time.monotonic() < deadline:
                remote = await self.remote_client.get_sandbox(sandbox.sandbox_id)
                if remote.get("status") == "deleted":
                    sandbox.status = SandboxStatus.DESTROYED
                    sandbox.destroyed_at = datetime.now()
                    await self._update_sandbox_status(sandbox.id, sandbox.status,
                        sandbox.container_id, destroyed_at=sandbox.destroyed_at)
                    self.active_sandboxes.pop(sandbox_id, None)
                    return
                await asyncio.sleep(2)
            raise TimeoutError("Fuze Sandbox workspace deletion is still pending")

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
        sandbox = self.active_sandboxes.get(sandbox_id)
        if sandbox and self.provider == "fuze-sandbox":
            await self._refresh_remote_record(sandbox)
        return sandbox

    async def list_sandboxes(
        self, agent_id: Optional[str] = None, status: Optional[SandboxStatus] = None
    ) -> List[Sandbox]:
        """List sandboxes with optional filtering"""

        sandboxes = list(self.active_sandboxes.values())

        if self.provider == "fuze-sandbox":
            for sandbox in sandboxes:
                await self._refresh_remote_record(sandbox)

        if agent_id:
            sandboxes = [s for s in sandboxes if s.agent_id == agent_id]

        if status:
            sandboxes = [s for s in sandboxes if s.status == status]

        return sandboxes

    async def get_logs(self, sandbox_id: str) -> dict:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            raise RuntimeError("Job logs require the Fuze Sandbox provider")
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox:
            raise ValueError("Sandbox not found")
        return await self.remote_client.get_logs(sandbox.sandbox_id)

    async def execute_command(
        self, sandbox_id: str, command: str, working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command in a sandbox"""

        if self.provider == "fuze-sandbox":
            sandbox = self.active_sandboxes.get(sandbox_id)
            if not sandbox or sandbox.status != SandboxStatus.RUNNING or not self.remote_client:
                raise ValueError(f"Sandbox {sandbox_id} not found or not running")
            if not command or len(command) > 4096:
                raise ValueError("Fuze Sandbox commands must be between 1 and 4096 characters")
            directory = posixpath.normpath(working_dir or "/workspace")
            if directory != "/workspace" and not directory.startswith("/workspace/"):
                raise ValueError("remote working directory must be inside /workspace")
            wrapped = (f"cd -- {shlex.quote(directory)} && {command}; "
                       "_fuze_code=$?; printf '\\n__FUZE_EXIT_CODE__%s\\n' \"$_fuze_code\"")
            if len(wrapped) > 4096:
                raise ValueError("command exceeds the Fuze Sandbox API limit after wrapping")
            try:
                result = await self.remote_client.execute_workspace(sandbox.sandbox_id, wrapped)
                output = str(result.get("output", ""))
                match = re.search(r"(?:^|\n)__FUZE_EXIT_CODE__(\d+)\s*$", output)
                if not match:
                    return {"exit_code": -1, "output": output, "success": False}
                exit_code = int(match.group(1))
                return {"exit_code": exit_code, "output": output[:match.start()].rstrip(),
                        "success": exit_code == 0}
            except Exception as exc:
                logger.error("Fuze Sandbox command failed for %s: %s", sandbox_id, exc)
                return {"exit_code": -1, "output": str(exc), "success": False}

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

    async def write_workspace_file(self, sandbox_id: str, path: str, content: bytes) -> dict:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            raise RuntimeError("workspace file API is only available with the Fuze Sandbox provider")
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox or sandbox.status != SandboxStatus.RUNNING:
            raise ValueError(f"Sandbox {sandbox_id} not found or not running")
        return await self.remote_client.write_workspace_file(sandbox.sandbox_id, path, content)

    async def read_workspace_file(self, sandbox_id: str, path: str) -> bytes:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            raise RuntimeError("workspace file API is only available with the Fuze Sandbox provider")
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox or sandbox.status != SandboxStatus.RUNNING:
            raise ValueError(f"Sandbox {sandbox_id} not found or not running")
        return await self.remote_client.read_workspace_file(sandbox.sandbox_id, path)

    async def create_preview_grant(self, sandbox_id: str, port: int) -> dict:
        if self.provider != "fuze-sandbox" or not self.remote_client:
            raise RuntimeError("preview grants require the Fuze Sandbox provider")
        sandbox = self.active_sandboxes.get(sandbox_id)
        if not sandbox or sandbox.status != SandboxStatus.RUNNING:
            raise ValueError(f"Sandbox {sandbox_id} not found or not running")
        return await self.remote_client.create_preview_grant(sandbox.sandbox_id, port)

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
            "tmpfs": {
                "/tmp": "rw,noexec,nosuid,size=1g"
            },  # nosec B108 -- Docker tmpfs mount point inside the sandbox container, hardened with noexec,nosuid
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
            rows = await conn.fetch("""
                SELECT * FROM agent_sandboxes 
                WHERE destroyed_at IS NULL
                  AND (status IN ('running', 'paused') OR container_id LIKE 'fuze-sandbox:%')
            """)

            for row in rows:
                try:
                    provider_marker = row["container_id"] or ""
                    is_remote = provider_marker.startswith("fuze-sandbox:")
                    if self.provider == "fuze-sandbox" and not is_remote:
                        # Never reinterpret a Docker container row as a remote
                        # workspace after a backend configuration change.
                        continue
                    if self.provider == "docker" and is_remote:
                        # Leave remote records untouched when running locally.
                        continue
                    # Try to get the container
                    container = None
                    if row["container_id"] and self.docker_client and not is_remote:
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
