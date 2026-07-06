"""
WebSocket Manager for FuzeAgent
Handles real-time updates for agents, tasks, containers, and system notifications
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import WebSocket, WebSocketDisconnect
import weakref

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    """Types of real-time updates"""

    AGENT_STATUS = "agent_status"
    AGENT_CREATED = "agent_created"
    AGENT_UPDATED = "agent_updated"
    AGENT_DELETED = "agent_deleted"

    TASK_STATUS = "task_status"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"

    CONTAINER_STATUS = "container_status"
    CONTAINER_CREATED = "container_created"
    CONTAINER_STARTED = "container_started"
    CONTAINER_STOPPED = "container_stopped"
    CONTAINER_LOG = "container_log"

    KNOWLEDGE_UPDATED = "knowledge_updated"
    KNOWLEDGE_INDEXED = "knowledge_indexed"

    SYSTEM_NOTIFICATION = "system_notification"
    SYSTEM_ERROR = "system_error"

    CHAT_MESSAGE = "chat_message"
    CHAT_TYPING = "chat_typing"


class WebSocketUpdate(BaseModel):
    """WebSocket update message"""

    type: UpdateType
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)
    target_id: Optional[str] = None  # Agent ID, Task ID, etc.
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None


class ConnectionScope(BaseModel):
    """WebSocket connection scope"""

    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    subscriptions: Set[UpdateType] = Field(default_factory=set)


class WebSocketConnection:
    """Individual WebSocket connection"""

    def __init__(
        self, websocket: WebSocket, connection_id: str, scope: ConnectionScope
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.scope = scope
        self.connected = True
        self.last_ping = datetime.now()

    async def send_update(self, update: WebSocketUpdate) -> bool:
        """Send an update to this connection"""
        if not self.connected:
            return False

        try:
            await self.websocket.send_json(
                {
                    "id": self.connection_id,
                    "type": update.type.value,
                    "timestamp": update.timestamp.isoformat(),
                    "data": update.data,
                    "target_id": update.target_id,
                    "organization_id": update.organization_id,
                    "team_id": update.team_id,
                    "agent_id": update.agent_id,
                }
            )
            return True
        except Exception as e:
            logger.warning(
                f"Failed to send update to connection {self.connection_id}: {e}"
            )
            self.connected = False
            return False

    def should_receive_update(self, update: WebSocketUpdate) -> bool:
        """Check if this connection should receive the update"""
        # Check subscription to update type
        if update.type not in self.scope.subscriptions:
            return False

        # Check scope filtering
        if (
            self.scope.agent_id
            and update.agent_id
            and self.scope.agent_id != update.agent_id
        ):
            return False

        if (
            self.scope.team_id
            and update.team_id
            and self.scope.team_id != update.team_id
        ):
            return False

        if (
            self.scope.organization_id
            and update.organization_id
            and self.scope.organization_id != update.organization_id
        ):
            return False

        return True


class WebSocketManager:
    """Manages WebSocket connections and real-time updates"""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.agent_connections: Dict[str, Set[str]] = {}  # agent_id -> connection_ids
        self.team_connections: Dict[str, Set[str]] = {}  # team_id -> connection_ids
        self.org_connections: Dict[str, Set[str]] = {}  # org_id -> connection_ids
        self.update_handlers: Dict[UpdateType, List[Callable]] = {}

        self._cleanup_task_handle = None

    async def start(self):
        """Start the background cleanup task. Call from FastAPI startup after event loop is running."""
        self._cleanup_task_handle = asyncio.create_task(self._cleanup_task())

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        organization_id: str = None,
        team_id: str = None,
        agent_id: str = None,
        user_id: str = None,
        subscriptions: List[str] = None,
    ) -> WebSocketConnection:
        """Accept a new WebSocket connection"""

        await websocket.accept()

        # Parse subscriptions
        subscription_types = set()
        if subscriptions:
            for sub in subscriptions:
                try:
                    subscription_types.add(UpdateType(sub))
                except ValueError:
                    logger.warning(f"Invalid subscription type: {sub}")
        else:
            # Default subscriptions
            subscription_types = {
                UpdateType.AGENT_STATUS,
                UpdateType.TASK_STATUS,
                UpdateType.CONTAINER_STATUS,
                UpdateType.SYSTEM_NOTIFICATION,
            }

        scope = ConnectionScope(
            organization_id=organization_id,
            team_id=team_id,
            agent_id=agent_id,
            user_id=user_id,
            subscriptions=subscription_types,
        )

        connection = WebSocketConnection(websocket, connection_id, scope)
        self.connections[connection_id] = connection

        # Index by scope
        if agent_id:
            if agent_id not in self.agent_connections:
                self.agent_connections[agent_id] = set()
            self.agent_connections[agent_id].add(connection_id)

        if team_id:
            if team_id not in self.team_connections:
                self.team_connections[team_id] = set()
            self.team_connections[team_id].add(connection_id)

        if organization_id:
            if organization_id not in self.org_connections:
                self.org_connections[organization_id] = set()
            self.org_connections[organization_id].add(connection_id)

        logger.info(
            f"WebSocket connected: {connection_id} (scope: org={organization_id}, team={team_id}, agent={agent_id})"
        )

        # Send connection confirmation
        await connection.send_update(
            WebSocketUpdate(
                type=UpdateType.SYSTEM_NOTIFICATION,
                data={
                    "message": "WebSocket connected successfully",
                    "subscriptions": [sub.value for sub in subscription_types],
                },
            )
        )

        return connection

    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""

        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]
        connection.connected = False

        # Remove from indices
        if (
            connection.scope.agent_id
            and connection.scope.agent_id in self.agent_connections
        ):
            self.agent_connections[connection.scope.agent_id].discard(connection_id)
            if not self.agent_connections[connection.scope.agent_id]:
                del self.agent_connections[connection.scope.agent_id]

        if (
            connection.scope.team_id
            and connection.scope.team_id in self.team_connections
        ):
            self.team_connections[connection.scope.team_id].discard(connection_id)
            if not self.team_connections[connection.scope.team_id]:
                del self.team_connections[connection.scope.team_id]

        if (
            connection.scope.organization_id
            and connection.scope.organization_id in self.org_connections
        ):
            self.org_connections[connection.scope.organization_id].discard(
                connection_id
            )
            if not self.org_connections[connection.scope.organization_id]:
                del self.org_connections[connection.scope.organization_id]

        del self.connections[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast_update(self, update: WebSocketUpdate):
        """Broadcast an update to relevant connections"""

        sent_count = 0
        failed_connections = []

        for connection_id, connection in self.connections.items():
            if not connection.connected:
                failed_connections.append(connection_id)
                continue

            if connection.should_receive_update(update):
                success = await connection.send_update(update)
                if success:
                    sent_count += 1
                else:
                    failed_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)

        logger.debug(f"Broadcast {update.type.value} to {sent_count} connections")

        # Call registered handlers
        if update.type in self.update_handlers:
            for handler in self.update_handlers[update.type]:
                try:
                    await handler(update)
                except Exception as e:
                    logger.error(f"Error in update handler: {e}")

    async def send_to_agent(self, agent_id: str, update: WebSocketUpdate):
        """Send update to connections watching a specific agent"""
        update.agent_id = agent_id

        if agent_id in self.agent_connections:
            for connection_id in list(self.agent_connections[agent_id]):
                connection = self.connections.get(connection_id)
                if connection and connection.should_receive_update(update):
                    await connection.send_update(update)

    async def send_to_team(self, team_id: str, update: WebSocketUpdate):
        """Send update to connections watching a specific team"""
        update.team_id = team_id

        if team_id in self.team_connections:
            for connection_id in list(self.team_connections[team_id]):
                connection = self.connections.get(connection_id)
                if connection and connection.should_receive_update(update):
                    await connection.send_update(update)

    async def send_to_organization(self, organization_id: str, update: WebSocketUpdate):
        """Send update to connections watching a specific organization"""
        update.organization_id = organization_id

        if organization_id in self.org_connections:
            for connection_id in list(self.org_connections[organization_id]):
                connection = self.connections.get(connection_id)
                if connection and connection.should_receive_update(update):
                    await connection.send_update(update)

    def register_update_handler(self, update_type: UpdateType, handler: Callable):
        """Register a handler for specific update types"""
        if update_type not in self.update_handlers:
            self.update_handlers[update_type] = []
        self.update_handlers[update_type].append(handler)

    async def _cleanup_task(self):
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = datetime.now()
                stale_connections = []

                for connection_id, connection in self.connections.items():
                    # Check if connection is stale (no activity for 5 minutes)
                    if (current_time - connection.last_ping).total_seconds() > 300:
                        stale_connections.append(connection_id)

                for connection_id in stale_connections:
                    await self.disconnect(connection_id)

                if stale_connections:
                    logger.info(
                        f"Cleaned up {len(stale_connections)} stale WebSocket connections"
                    )

            except Exception as e:
                logger.error(f"Error in WebSocket cleanup task: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": len(self.connections),
            "agent_connections": len(self.agent_connections),
            "team_connections": len(self.team_connections),
            "organization_connections": len(self.org_connections),
            "connections_by_type": {
                update_type.value: len(
                    [
                        conn
                        for conn in self.connections.values()
                        if update_type in conn.scope.subscriptions
                    ]
                )
                for update_type in UpdateType
            },
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Convenience functions for common update types
async def notify_agent_status_change(
    agent_id: str, status: str, additional_data: Dict = None
):
    """Notify about agent status changes"""
    data = {"status": status}
    if additional_data:
        data.update(additional_data)

    await websocket_manager.send_to_agent(
        agent_id,
        WebSocketUpdate(
            type=UpdateType.AGENT_STATUS,
            target_id=agent_id,
            agent_id=agent_id,
            data=data,
        ),
    )


async def notify_task_progress(
    task_id: str, agent_id: str, progress: int, message: str = None
):
    """Notify about task progress updates"""
    await websocket_manager.send_to_agent(
        agent_id,
        WebSocketUpdate(
            type=UpdateType.TASK_PROGRESS,
            target_id=task_id,
            agent_id=agent_id,
            data={"task_id": task_id, "progress": progress, "message": message},
        ),
    )


async def notify_container_status_change(
    agent_id: str, container_status: str, additional_data: Dict = None
):
    """Notify about container status changes"""
    data = {"container_status": container_status}
    if additional_data:
        data.update(additional_data)

    await websocket_manager.send_to_agent(
        agent_id,
        WebSocketUpdate(
            type=UpdateType.CONTAINER_STATUS,
            target_id=agent_id,
            agent_id=agent_id,
            data=data,
        ),
    )


async def notify_knowledge_update(
    organization_id: str,
    team_id: str = None,
    agent_id: str = None,
    document_title: str = None,
):
    """Notify about knowledge base updates"""
    update = WebSocketUpdate(
        type=UpdateType.KNOWLEDGE_UPDATED,
        organization_id=organization_id,
        team_id=team_id,
        agent_id=agent_id,
        data={
            "document_title": document_title,
            "message": f"Knowledge base updated: {document_title}"
            if document_title
            else "Knowledge base updated",
        },
    )

    if agent_id:
        await websocket_manager.send_to_agent(agent_id, update)
    elif team_id:
        await websocket_manager.send_to_team(team_id, update)
    elif organization_id:
        await websocket_manager.send_to_organization(organization_id, update)


async def notify_system_error(
    error_message: str,
    organization_id: str = None,
    team_id: str = None,
    agent_id: str = None,
):
    """Notify about system errors"""
    update = WebSocketUpdate(
        type=UpdateType.SYSTEM_ERROR,
        organization_id=organization_id,
        team_id=team_id,
        agent_id=agent_id,
        data={"error": error_message, "severity": "error"},
    )

    await websocket_manager.broadcast_update(update)
