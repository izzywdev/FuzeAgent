"""
WebSocket handler for mock server to support chat functionality.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class MockWebSocketManager:
    """Simple WebSocket manager for mock server"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_conversations: Dict[str, Set[str]] = {}  # agent_id -> conversation_ids
        self.conversation_connections: Dict[str, Set[str]] = {}  # conversation_id -> connection_ids
    
    async def connect(self, websocket: WebSocket, agent_id: str, conversation_id: str):
        """Accept a new WebSocket connection for agent conversation"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        
        # Track conversation connections
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(connection_id)
        
        # Track agent conversations
        if agent_id not in self.agent_conversations:
            self.agent_conversations[agent_id] = set()
        self.agent_conversations[agent_id].add(conversation_id)
        
        logger.info(f"WebSocket connected: {connection_id} for agent {agent_id}, conversation {conversation_id}")
        
        # Send connection confirmation
        await self.send_message(websocket, {
            "type": "connection_established",
            "message": "WebSocket connected successfully",
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            del self.active_connections[connection_id]
            
            # Remove from conversation tracking
            for conversation_id, connections in self.conversation_connections.items():
                connections.discard(connection_id)
                if not connections:
                    del self.conversation_connections[conversation_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
    
    async def broadcast_to_conversation(self, conversation_id: str, message: dict):
        """Broadcast a message to all connections in a conversation"""
        if conversation_id in self.conversation_connections:
            for connection_id in self.conversation_connections[conversation_id]:
                if connection_id in self.active_connections:
                    await self.send_message(self.active_connections[connection_id], message)
    
    async def handle_message(self, websocket: WebSocket, message: str, agent_id: str, conversation_id: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self.send_message(websocket, {"type": "pong"})
            elif message_type == "new_message":
                # Simulate agent response
                user_message = data.get("content", "")
                
                # Echo back a mock agent response
                agent_response = {
                    "type": "new_message",
                    "message": {
                        "id": str(uuid.uuid4()),
                        "conversation_id": conversation_id,
                        "role": "agent",
                        "content": f"Mock agent response to: {user_message}",
                        "timestamp": datetime.now().isoformat(),
                        "status": "sent",
                        "metadata": {
                            "model": "mock-model",
                            "response_time": 0.5
                        }
                    }
                }
                
                # Broadcast to all connections in this conversation
                await self.broadcast_to_conversation(conversation_id, agent_response)
                
            elif message_type == "typing":
                # Broadcast typing indicator
                typing_message = {
                    "type": "typing",
                    "typing": data.get("typing", False),
                    "agent_id": agent_id
                }
                await self.broadcast_to_conversation(conversation_id, typing_message)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

# Global WebSocket manager instance
websocket_manager = MockWebSocketManager()
