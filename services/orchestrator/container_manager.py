"""
Container Management System for FuzeAgent
Handles Docker container lifecycle for AI agents
"""
import docker
import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import aiofiles
import threading
import time
from docker.errors import DockerException, NotFound, APIError

logger = logging.getLogger(__name__)

class ContainerStatus(BaseModel):
    """Container status information"""
    id: str
    name: str
    status: str  # 'created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead'
    image: str
    created: datetime
    started: Optional[datetime] = None
    finished: Optional[datetime] = None
    restart_count: int = 0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[int] = None
    memory_limit: Optional[int] = None
    network_rx: Optional[int] = None
    network_tx: Optional[int] = None
    ports: Dict[str, str] = Field(default_factory=dict)
    environment: Dict[str, str] = Field(default_factory=dict)
    mounts: List[str] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    health: Optional[str] = None  # 'healthy', 'unhealthy', 'starting'

class ContainerConfig(BaseModel):
    """Container configuration"""
    image: str
    name: str
    environment: Dict[str, str] = Field(default_factory=dict)
    ports: Dict[str, int] = Field(default_factory=dict)  # container_port -> host_port
    volumes: Dict[str, str] = Field(default_factory=dict)  # host_path -> container_path
    memory_limit: str = "1g"
    cpu_limit: float = 1.0
    restart_policy: str = "unless-stopped"
    command: Optional[str] = None
    working_dir: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    network: Optional[str] = None
    healthcheck: Optional[Dict[str, Any]] = None

class LogEntry(BaseModel):
    """Container log entry"""
    timestamp: datetime
    stream: str  # 'stdout' or 'stderr'
    message: str

class ContainerManager:
    """Docker container management for AI agents"""
    
    def __init__(self):
        """Initialize the container manager"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
        
        # Storage for active log streams
        self._log_streams = {}
        
        # Default agent container configuration
        self.default_agent_config = ContainerConfig(
            image="fuzeagent/claude-agent:latest",
            name="",
            environment={
                "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
                "FUZEAGENT_API_URL": "http://host.docker.internal:8000",
                "PYTHONUNBUFFERED": "1"
            },
            ports={"8080": 0},  # Auto-assign host port
            memory_limit="2g",
            cpu_limit=2.0,
            restart_policy="unless-stopped",
            labels={
                "fuzeagent.type": "ai-agent",
                "fuzeagent.version": "1.0"
            },
            network="fuzeagent_default",
            healthcheck={
                "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                "interval": 30,
                "timeout": 10,
                "retries": 3,
                "start_period": 60
            }
        )

    def _check_docker_available(self):
        """Check if Docker is available"""
        if not self.docker_client:
            raise RuntimeError("Docker client not available")

    async def create_agent_container(self, agent_id: str, config: ContainerConfig = None) -> ContainerStatus:
        """Create a new agent container"""
        self._check_docker_available()
        
        # Use provided config or default
        if config is None:
            config = self.default_agent_config.model_copy()
            config.name = f"fuzeagent-{agent_id}"
            config.labels["fuzeagent.agent_id"] = agent_id
        
        try:
            # Check if container already exists
            try:
                existing = self.docker_client.containers.get(config.name)
                if existing.status in ['running', 'restarting']:
                    logger.warning(f"Container {config.name} already exists and is running")
                    return await self._get_container_status(existing)
                else:
                    # Remove stopped container
                    existing.remove()
                    logger.info(f"Removed existing stopped container {config.name}")
            except NotFound:
                pass
            
            # Prepare container arguments
            container_args = {
                'image': config.image,
                'name': config.name,
                'environment': config.environment,
                'labels': config.labels,
                'restart_policy': {"Name": config.restart_policy},
                'detach': True,
                'mem_limit': config.memory_limit,
                'cpu_quota': int(config.cpu_limit * 100000),
                'cpu_period': 100000
            }
            
            # Add ports
            if config.ports:
                container_args['ports'] = {}
                for container_port, host_port in config.ports.items():
                    container_args['ports'][container_port] = host_port if host_port > 0 else None
            
            # Add volumes
            if config.volumes:
                container_args['volumes'] = {}
                for host_path, container_path in config.volumes.items():
                    container_args['volumes'][host_path] = {'bind': container_path, 'mode': 'rw'}
            
            # Add command
            if config.command:
                container_args['command'] = config.command
            
            # Add working directory
            if config.working_dir:
                container_args['working_dir'] = config.working_dir
            
            # Add network
            if config.network:
                container_args['network'] = config.network
            
            # Add healthcheck
            if config.healthcheck:
                container_args['healthcheck'] = config.healthcheck
            
            # Create container
            container = self.docker_client.containers.create(**container_args)
            
            logger.info(f"Created container {config.name} with ID {container.short_id}")
            
            # Send WebSocket notification
            try:
                from websocket_manager import notify_container_status_change
                await notify_container_status_change(
                    agent_id=agent_id,
                    container_status="created",
                    additional_data={"container_id": container.short_id}
                )
            except Exception as e:
                logger.error(f"Error sending container notification: {e}")
            
            return await self._get_container_status(container)
            
        except Exception as e:
            logger.error(f"Error creating container {config.name}: {e}")
            raise

    async def start_container(self, agent_id: str) -> ContainerStatus:
        """Start an agent container"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            if container.status == 'running':
                logger.info(f"Container {container_name} is already running")
            else:
                container.start()
                logger.info(f"Started container {container_name}")
                
                # Send WebSocket notification
                try:
                    from websocket_manager import notify_container_status_change
                    await notify_container_status_change(
                        agent_id=agent_id,
                        container_status="started"
                    )
                except Exception as e:
                    logger.error(f"Error sending container notification: {e}")
            
            return await self._get_container_status(container)
            
        except NotFound:
            # Container doesn't exist, create it first
            logger.info(f"Container {container_name} not found, creating it")
            status = await self.create_agent_container(agent_id)
            
            # Now start it
            container = self.docker_client.containers.get(container_name)
            container.start()
            logger.info(f"Created and started container {container_name}")
            
            return await self._get_container_status(container)
            
        except Exception as e:
            logger.error(f"Error starting container {container_name}: {e}")
            raise

    async def stop_container(self, agent_id: str, timeout: int = 30) -> ContainerStatus:
        """Stop an agent container"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            if container.status in ['stopped', 'exited']:
                logger.info(f"Container {container_name} is already stopped")
            else:
                container.stop(timeout=timeout)
                logger.info(f"Stopped container {container_name}")
            
            return await self._get_container_status(container)
            
        except NotFound:
            raise RuntimeError(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error stopping container {container_name}: {e}")
            raise

    async def restart_container(self, agent_id: str, timeout: int = 30) -> ContainerStatus:
        """Restart an agent container"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart(timeout=timeout)
            
            logger.info(f"Restarted container {container_name}")
            
            return await self._get_container_status(container)
            
        except NotFound:
            raise RuntimeError(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error restarting container {container_name}: {e}")
            raise

    async def remove_container(self, agent_id: str, force: bool = False) -> bool:
        """Remove an agent container"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Stop container first if running
            if container.status == 'running':
                container.stop(timeout=10)
            
            # Remove container
            container.remove(force=force)
            
            logger.info(f"Removed container {container_name}")
            return True
            
        except NotFound:
            logger.warning(f"Container {container_name} not found for removal")
            return True  # Consider it successful if it doesn't exist
        except Exception as e:
            logger.error(f"Error removing container {container_name}: {e}")
            return False

    async def get_container_status(self, agent_id: str) -> Optional[ContainerStatus]:
        """Get container status for an agent"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            return await self._get_container_status(container)
            
        except NotFound:
            return None
        except Exception as e:
            logger.error(f"Error getting container status {container_name}: {e}")
            return None

    async def list_agent_containers(self) -> List[ContainerStatus]:
        """List all agent containers"""
        self._check_docker_available()
        
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": "fuzeagent.type=ai-agent"}
            )
            
            statuses = []
            for container in containers:
                status = await self._get_container_status(container)
                statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"Error listing agent containers: {e}")
            return []

    async def get_container_logs(self, agent_id: str, 
                               tail: int = 100, 
                               since: Optional[datetime] = None,
                               until: Optional[datetime] = None) -> List[LogEntry]:
        """Get container logs"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Prepare log arguments
            log_args = {
                'timestamps': True,
                'tail': tail,
                'stdout': True,
                'stderr': True
            }
            
            if since:
                log_args['since'] = since
            if until:
                log_args['until'] = until
            
            # Get logs
            logs = container.logs(**log_args).decode('utf-8')
            
            # Parse logs into entries
            entries = []
            for line in logs.split('\n'):
                if not line.strip():
                    continue
                
                try:
                    # Docker log format: TIMESTAMP STREAM MESSAGE
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        stream = 'stdout'  # Docker doesn't always include stream info
                        message = ' '.join(parts[1:])
                        
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        entries.append(LogEntry(
                            timestamp=timestamp,
                            stream=stream,
                            message=message
                        ))
                except Exception as parse_error:
                    # If parsing fails, create a simple entry
                    entries.append(LogEntry(
                        timestamp=datetime.now(),
                        stream='stdout',
                        message=line
                    ))
            
            return entries
            
        except NotFound:
            raise RuntimeError(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error getting container logs {container_name}: {e}")
            raise

    async def stream_container_logs(self, agent_id: str) -> AsyncGenerator[LogEntry, None]:
        """Stream container logs in real-time"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Create log stream
            log_stream = container.logs(
                stream=True,
                follow=True,
                timestamps=True,
                stdout=True,
                stderr=True
            )
            
            for log_line in log_stream:
                try:
                    line = log_line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    # Parse log line
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        stream = 'stdout'
                        message = ' '.join(parts[1:])
                        
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        yield LogEntry(
                            timestamp=timestamp,
                            stream=stream,
                            message=message
                        )
                except Exception as parse_error:
                    logger.warning(f"Error parsing log line: {parse_error}")
                    yield LogEntry(
                        timestamp=datetime.now(),
                        stream='stdout',
                        message=line
                    )
                    
        except NotFound:
            raise RuntimeError(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error streaming container logs {container_name}: {e}")
            raise

    async def execute_command(self, agent_id: str, command: str, 
                            working_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute a command in the container"""
        self._check_docker_available()
        
        container_name = f"fuzeagent-{agent_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            if container.status != 'running':
                raise RuntimeError(f"Container {container_name} is not running")
            
            # Execute command
            exec_result = container.exec_run(
                command,
                workdir=working_dir,
                detach=False,
                stdout=True,
                stderr=True
            )
            
            return {
                "exit_code": exec_result.exit_code,
                "output": exec_result.output.decode('utf-8')
            }
            
        except NotFound:
            raise RuntimeError(f"Container {container_name} not found")
        except Exception as e:
            logger.error(f"Error executing command in container {container_name}: {e}")
            raise

    async def _get_container_status(self, container) -> ContainerStatus:
        """Get detailed container status"""
        try:
            # Reload container info
            container.reload()
            
            # Get basic info
            attrs = container.attrs
            config = attrs.get('Config', {})
            state = attrs.get('State', {})
            network_settings = attrs.get('NetworkSettings', {})
            
            # Parse timestamps
            created = datetime.fromisoformat(attrs.get('Created', '').replace('Z', '+00:00'))
            started = None
            finished = None
            
            if state.get('StartedAt'):
                try:
                    started = datetime.fromisoformat(state['StartedAt'].replace('Z', '+00:00'))
                except:
                    pass
            
            if state.get('FinishedAt'):
                try:
                    finished = datetime.fromisoformat(state['FinishedAt'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Get resource usage (if available)
            cpu_usage = None
            memory_usage = None
            memory_limit = None
            
            try:
                stats = container.stats(stream=False)
                
                # Calculate CPU usage percentage
                if 'cpu_stats' in stats and 'precpu_stats' in stats:
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                    
                    if system_delta > 0:
                        cpu_usage = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
                
                # Get memory usage
                if 'memory_stats' in stats:
                    memory_usage = stats['memory_stats'].get('usage', 0)
                    memory_limit = stats['memory_stats'].get('limit', 0)
                    
            except Exception as stats_error:
                logger.debug(f"Could not get container stats: {stats_error}")
            
            # Get port mappings
            ports = {}
            if network_settings.get('Ports'):
                for container_port, host_bindings in network_settings['Ports'].items():
                    if host_bindings:
                        for binding in host_bindings:
                            ports[container_port] = f"{binding.get('HostIp', '0.0.0.0')}:{binding.get('HostPort')}"
            
            # Get health status
            health = None
            if state.get('Health'):
                health = state['Health'].get('Status')
            
            return ContainerStatus(
                id=container.short_id,
                name=container.name,
                status=container.status,
                image=config.get('Image', ''),
                created=created,
                started=started,
                finished=finished,
                restart_count=state.get('RestartCount', 0),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                ports=ports,
                environment=dict(config.get('Env', [])) if config.get('Env') else {},
                labels=config.get('Labels', {}),
                health=health
            )
            
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            raise

# Global container manager instance
container_manager = ContainerManager()