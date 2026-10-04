"""
Real-Time Human Decision Escalation Engine (Track #3).
Integrates RabbitMQ messaging bus and WebSocket relays for instant human intervention.
Allows agents executing in sandboxes to pause destructive, high-cost, or compliance operations
and request approval from human administrators in real-time.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:password@rabbitmq:5672/")

try:
    import aio_pika

    RABBIT_AVAILABLE = True
except ImportError:
    RABBIT_AVAILABLE = False
    logger.warning(
        "aio_pika not installed; RabbitMQ escalation events will run in in-memory relay mode"
    )


class EscalationEngine:
    """Manages real-time agent escalations and human approval workflows."""

    def __init__(self, rabbitmq_url: str = RABBITMQ_URL):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.exchange = None
        self.pending_escalations: Dict[str, Dict[str, Any]] = {}
        self.ws_subscribers: List[Any] = []
        self._seed_default_escalation()

    def _seed_default_escalation(self):
        """Seed initial escalation item matching system demonstration state."""
        self.pending_escalations["esc-101"] = {
            "id": "esc-101",
            "agentId": "python-dev-v2",
            "agentName": "Python Dev (FastAPI Migration)",
            "category": "destructive_operation",
            "title": "Drop and recreate table 'billing_ledger'",
            "detail": "Agent attempted to run 'DROP TABLE billing_ledger CASCADE;' during migration script execution.",
            "costUsd": 0.12,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

    async def _ensure_connection(self):
        if not RABBIT_AVAILABLE:
            return

        if not self.connection or self.connection.is_closed:
            try:
                self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    "agent.escalations",
                    aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )
                logger.info(
                    "📡 EscalationEngine: Connected to RabbitMQ exchange 'agent.escalations'"
                )
            except Exception as e:
                logger.debug(
                    f"EscalationEngine: RabbitMQ unavailable ({e}); using internal relay"
                )
                self.connection = None
                self.channel = None
                self.exchange = None

    async def publish_event(self, routing_key: str, payload: Dict[str, Any]):
        """Publish event to RabbitMQ and broadcast to WebSocket listeners."""
        # 1. RabbitMQ publish
        await self._ensure_connection()
        if self.exchange:
            try:
                message = aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                )
                await self.exchange.publish(message, routing_key=routing_key)
                logger.info(
                    f"📤 Published escalation event to RabbitMQ ({routing_key})"
                )
            except Exception as e:
                logger.warning(f"Failed to publish to RabbitMQ: {e}")

        # 2. WebSocket broadcast
        from .main import websocket_manager

        try:
            ws_msg = {
                "type": f"escalation:{routing_key}",
                "data": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await websocket_manager.broadcast(ws_msg)
        except Exception:
            pass

    async def create_escalation(
        self,
        agent_id: str,
        agent_name: str,
        category: str,
        title: str,
        detail: str,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new pending human escalation and trigger bus alerts."""
        esc_id = f"esc-{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "id": esc_id,
            "agentId": agent_id,
            "agentName": agent_name,
            "category": category,
            "title": title,
            "detail": detail,
            "costUsd": cost_usd,
            "metadata": metadata or {},
            "createdAt": now,
            "status": "pending",
        }
        self.pending_escalations[esc_id] = item
        await self.publish_event("created", item)
        logger.info(
            f"⚠️ Escalation {esc_id} created by agent '{agent_name}' ({category})"
        )
        return item

    async def resolve_escalation(
        self,
        escalation_id: str,
        decision: str,
        approver_id: str = "admin",
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Approve or reject a pending agent escalation."""
        item = self.pending_escalations.get(escalation_id)
        if not item:
            return None

        item["status"] = decision
        item["resolvedAt"] = datetime.now(timezone.utc).isoformat()
        item["approverId"] = approver_id
        item["notes"] = notes or ""

        routing = "approved" if decision == "approved" else "rejected"
        await self.publish_event(f"decision.{routing}", item)
        logger.info(
            f"✅ Escalation {escalation_id} resolved: {decision.upper()} by {approver_id}"
        )
        return item

    def list_escalations(self) -> List[Dict[str, Any]]:
        return list(self.pending_escalations.values())


# Global singleton instance
escalation_engine = EscalationEngine()
