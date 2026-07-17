# fmt: off
"""
Knowledge Notification Service for FuzeAgent

This service manages notifications about knowledge updates, new insights,
knowledge conflicts, and cross-team learning opportunities. It provides
intelligent filtering, prioritization, and delivery of knowledge-related
notifications across the organization.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import asyncpg
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    NEW_KNOWLEDGE = "new_knowledge"
    KNOWLEDGE_UPDATE = "knowledge_update"
    KNOWLEDGE_CONFLICT = "knowledge_conflict"
    KNOWLEDGE_EXPIRY = "knowledge_expiry"
    RELEVANT_KNOWLEDGE = "relevant_knowledge"
    KNOWLEDGE_REQUEST = "knowledge_request"
    KNOWLEDGE_FEEDBACK = "knowledge_feedback"
    CROSS_TEAM_SHARING = "cross_team_sharing"
    KNOWLEDGE_GAP_IDENTIFIED = "knowledge_gap_identified"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    ACTED_UPON = "acted_upon"
    DISMISSED = "dismissed"


@dataclass
class NotificationRule:
    """Defines rules for when to send notifications"""

    recipient_type: str  # 'agent', 'team', 'organization'
    notification_types: List[NotificationType]
    conditions: Dict[str, Any]
    priority_threshold: Priority
    frequency_limit: Dict[str, int]  # e.g., {'daily': 5, 'weekly': 20}
    auto_dismiss_after_days: int


@dataclass
class KnowledgeNotification:
    """Represents a knowledge notification"""

    id: str
    recipient_type: str
    recipient_id: str
    notification_type: NotificationType
    title: str
    message: str
    knowledge_id: Optional[str]
    knowledge_type: Optional[str]
    priority: Priority
    requires_action: bool
    status: NotificationStatus
    suggested_actions: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]


class KnowledgeNotificationService:
    """
    Manages knowledge-related notifications with intelligent filtering,
    prioritization, and delivery across the organization hierarchy.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

        # Notification rules and configuration
        self.notification_rules = self._create_default_notification_rules()
        self.recipient_preferences: Dict[str, Dict[str, Any]] = {}

        # Rate limiting and batching
        self.rate_limits: Dict[str, Dict[str, int]] = {}
        self.batch_notifications: Dict[str, List[KnowledgeNotification]] = {}

        # Configuration
        self.batch_size = 10
        self.batch_interval_seconds = 300  # 5 minutes
        self.max_notifications_per_day = 20
        self.notification_retention_days = 30

        # Background task management
        self._notification_processor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.notifications_sent = 0
        self.notifications_batched = 0
        self.notifications_dismissed = 0

    async def initialize(self):
        """Initialize the notification service"""
        logger.info("Initializing KnowledgeNotificationService")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=8, command_timeout=60
            )

            # Load recipient preferences
            await self._load_recipient_preferences()

            # Start background tasks
            self._running = True
            self._notification_processor_task = asyncio.create_task(
                self._notification_processor()
            )
            self._cleanup_task = asyncio.create_task(self._cleanup_processor())

            logger.info("KnowledgeNotificationService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeNotificationService: {e}")
            raise

    async def close(self):
        """Close the notification service"""
        self._running = False

        if self._notification_processor_task:
            self._notification_processor_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        try:
            if self._notification_processor_task:
                await self._notification_processor_task
            if self._cleanup_task:
                await self._cleanup_task
        except asyncio.CancelledError:
            pass

        if self.pool:
            await self.pool.close()

        logger.info("KnowledgeNotificationService closed")

    async def notify_new_knowledge(
        self,
        knowledge_id: str,
        knowledge_type: str,
        organization_id: str,
        source_team_id: Optional[str] = None,
        source_agent_id: Optional[str] = None,
        knowledge_category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Create notifications for new knowledge"""

        notification_ids = []

        try:
            # Determine relevant recipients
            recipients = await self._identify_knowledge_recipients(
                knowledge_type,
                organization_id,
                source_team_id,
                source_agent_id,
                knowledge_category,
            )

            for recipient_type, recipient_id in recipients:
                # Check if recipient wants this type of notification
                if not self._should_notify_recipient(
                    recipient_type, recipient_id, NotificationType.NEW_KNOWLEDGE
                ):
                    continue

                # Create notification
                title = f"New {knowledge_category or 'Knowledge'} Available"
                message = await self._create_new_knowledge_message(
                    knowledge_id, knowledge_type, source_team_id, source_agent_id
                )

                priority = self._calculate_knowledge_priority(
                    knowledge_type, knowledge_category, metadata or {}
                )

                notification_id = await self._create_notification(
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    notification_type=NotificationType.NEW_KNOWLEDGE,
                    title=title,
                    message=message,
                    knowledge_id=knowledge_id,
                    knowledge_type=knowledge_type,
                    priority=priority,
                    suggested_actions=[
                        {"action": "review_knowledge", "label": "Review Knowledge"},
                        {"action": "apply_knowledge", "label": "Consider Application"},
                        {"action": "share_feedback", "label": "Provide Feedback"},
                    ],
                    metadata={
                        "knowledge_category": knowledge_category,
                        "source_team": source_team_id,
                        "source_agent": source_agent_id,
                        **(metadata or {}),
                    },
                )

                notification_ids.append(notification_id)

        except Exception as e:
            logger.error(f"Error creating new knowledge notifications: {e}")

        return notification_ids

    async def notify_knowledge_conflict(
        self,
        conflicting_knowledge_ids: List[str],
        organization_id: str,
        conflict_description: str,
        affected_teams: Optional[List[str]] = None,
    ) -> List[str]:
        """Create notifications for knowledge conflicts"""

        notification_ids = []

        try:
            # Determine who should be notified about conflicts
            if affected_teams:
                recipients = [
                    (otype, oid)
                    for otype, oid in [("team", team_id) for team_id in affected_teams]
                ]
            else:
                # Notify organization-level if no specific teams
                recipients = [("organization", organization_id)]

            for recipient_type, recipient_id in recipients:
                title = "Knowledge Conflict Detected"
                message = (
                    f"Conflicting knowledge items detected: {conflict_description}"
                )

                notification_id = await self._create_notification(
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                    notification_type=NotificationType.KNOWLEDGE_CONFLICT,
                    title=title,
                    message=message,
                    knowledge_id=conflicting_knowledge_ids[0]
                    if conflicting_knowledge_ids
                    else None,
                    knowledge_type="conflict",
                    priority=Priority.HIGH,
                    requires_action=True,
                    suggested_actions=[
                        {
                            "action": "review_conflict",
                            "label": "Review Conflicting Knowledge",
                        },
                        {"action": "resolve_conflict", "label": "Resolve Conflict"},
                        {"action": "escalate", "label": "Escalate to Management"},
                    ],
                    metadata={
                        "conflicting_knowledge_ids": conflicting_knowledge_ids,
                        "conflict_description": conflict_description,
                    },
                )

                notification_ids.append(notification_id)

        except Exception as e:
            logger.error(f"Error creating conflict notifications: {e}")

        return notification_ids

    async def notify_relevant_knowledge_for_task(
        self, agent_id: str, task_id: str, relevant_knowledge: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Notify agent about relevant knowledge for their current task"""

        if not relevant_knowledge or not self._should_notify_recipient(
            "agent", agent_id, NotificationType.RELEVANT_KNOWLEDGE
        ):
            return None

        try:
            # Create summary of relevant knowledge
            knowledge_summary = []
            for knowledge in relevant_knowledge[:3]:  # Top 3 items
                knowledge_summary.append(f"• {knowledge.get('title', 'Unknown')}")

            title = f"Relevant Knowledge for Current Task"
            message = (
                f"Found {len(relevant_knowledge)} knowledge items that might help with your current task:\n\n"
                + "\n".join(knowledge_summary)
            )

            if len(relevant_knowledge) > 3:
                message += f"\n\n... and {len(relevant_knowledge) - 3} more items."

            notification_id = await self._create_notification(
                recipient_type="agent",
                recipient_id=agent_id,
                notification_type=NotificationType.RELEVANT_KNOWLEDGE,
                title=title,
                message=message,
                knowledge_id=relevant_knowledge[0].get("id"),
                knowledge_type="task_relevant",
                priority=Priority.MEDIUM,
                suggested_actions=[
                    {"action": "review_knowledge", "label": "Review Knowledge"},
                    {"action": "apply_to_task", "label": "Apply to Current Task"},
                    {"action": "mark_helpful", "label": "Mark as Helpful"},
                ],
                metadata={
                    "task_id": task_id,
                    "relevant_knowledge_count": len(relevant_knowledge),
                    "knowledge_items": [k.get("id") for k in relevant_knowledge],
                },
                expires_at=datetime.now()
                + timedelta(hours=24),  # Task-specific, expires quickly
            )

            return notification_id

        except Exception as e:
            logger.error(f"Error creating relevant knowledge notification: {e}")
            return None

    async def notify_cross_team_opportunity(
        self,
        source_team_id: str,
        target_team_ids: List[str],
        knowledge_id: str,
        opportunity_description: str,
    ) -> List[str]:
        """Notify teams about cross-team knowledge sharing opportunities"""

        notification_ids = []

        try:
            for target_team_id in target_team_ids:
                if not self._should_notify_recipient(
                    "team", target_team_id, NotificationType.CROSS_TEAM_SHARING
                ):
                    continue

                title = "Cross-Team Knowledge Sharing Opportunity"
                message = f"Team has knowledge that could benefit your team: {opportunity_description}"

                notification_id = await self._create_notification(
                    recipient_type="team",
                    recipient_id=target_team_id,
                    notification_type=NotificationType.CROSS_TEAM_SHARING,
                    title=title,
                    message=message,
                    knowledge_id=knowledge_id,
                    knowledge_type="cross_team",
                    priority=Priority.MEDIUM,
                    suggested_actions=[
                        {"action": "review_knowledge", "label": "Review Knowledge"},
                        {
                            "action": "request_sharing",
                            "label": "Request Knowledge Sharing",
                        },
                        {
                            "action": "schedule_meeting",
                            "label": "Schedule Knowledge Transfer",
                        },
                    ],
                    metadata={
                        "source_team_id": source_team_id,
                        "opportunity_type": "knowledge_sharing",
                    },
                )

                notification_ids.append(notification_id)

        except Exception as e:
            logger.error(f"Error creating cross-team opportunity notifications: {e}")

        return notification_ids

    async def get_notifications_for_recipient(
        self,
        recipient_type: str,
        recipient_id: str,
        limit: int = 20,
        status_filter: Optional[List[NotificationStatus]] = None,
        notification_type_filter: Optional[List[NotificationType]] = None,
    ) -> List[KnowledgeNotification]:
        """Get notifications for a specific recipient"""

        try:
            async with self.pool.acquire() as conn:
                where_conditions = ["recipient_type = $1", "recipient_id = $2"]
                params = [recipient_type, recipient_id]
                param_idx = 3

                if status_filter:
                    where_conditions.append(f"status = ANY(${param_idx})")
                    params.append([status.value for status in status_filter])
                    param_idx += 1

                if notification_type_filter:
                    where_conditions.append(f"notification_type = ANY(${param_idx})")
                    params.append([ntype.value for ntype in notification_type_filter])
                    param_idx += 1

                # Don't show expired notifications
                where_conditions.append("(expires_at IS NULL OR expires_at > NOW())")

                where_clause = "WHERE " + " AND ".join(where_conditions)

                notifications = await conn.fetch(
                    f"""
                    SELECT * FROM knowledge_notifications
                    {where_clause}
                    ORDER BY 
                        CASE priority 
                            WHEN 'urgent' THEN 4
                            WHEN 'high' THEN 3
                            WHEN 'medium' THEN 2
                            ELSE 1
                        END DESC,
                        created_at DESC
                    LIMIT ${param_idx}
                """,
                    *params,
                    limit,
                )

                return [self._row_to_notification(row) for row in notifications]

        except Exception as e:
            logger.error(
                f"Error getting notifications for {recipient_type} {recipient_id}: {e}"
            )
            return []

    async def mark_notification_status(
        self,
        notification_id: str,
        status: NotificationStatus,
        action_taken: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark notification status and optional action taken"""

        try:
            async with self.pool.acquire() as conn:
                update_fields = ["status = $2"]
                params = [notification_id, status.value]
                param_idx = 3

                if status == NotificationStatus.READ:
                    update_fields.append(f"read_at = NOW()")
                elif status == NotificationStatus.ACKNOWLEDGED:
                    update_fields.append(f"acknowledged_at = NOW()")

                if action_taken:
                    update_fields.append(f"action_taken = ${param_idx}")
                    params.append(json.dumps(action_taken))
                    param_idx += 1

                result = await conn.execute(
                    f"""
                    UPDATE knowledge_notifications 
                    SET {', '.join(update_fields)}
                    WHERE id = $1
                """,
                    *params,
                )

                return result == "UPDATE 1"

        except Exception as e:
            logger.error(f"Error marking notification status: {e}")
            return False

    async def get_notification_statistics(
        self, organization_id: Optional[str] = None, days_back: int = 30
    ) -> Dict[str, Any]:
        """Get notification statistics"""

        try:
            async with self.pool.acquire() as conn:
                # Basic notification statistics
                where_conditions = [
                    "created_at >= NOW() - INTERVAL '%s days'" % days_back
                ]
                params = []

                if organization_id:
                    where_conditions.append(
                        """
                        recipient_id IN (
                            SELECT id FROM organizations WHERE id = $1
                            UNION ALL
                            SELECT id FROM teams WHERE organization_id = $1
                            UNION ALL
                            SELECT a.id FROM agents a 
                            JOIN teams t ON a.team_id = t.id 
                            WHERE t.organization_id = $1
                        )
                    """
                    )
                    params.append(organization_id)

                where_clause = "WHERE " + " AND ".join(where_conditions)

                basic_stats = await conn.fetchrow(
                    f"""
                    SELECT 
                        COUNT(*) as total_notifications,
                        COUNT(CASE WHEN status = 'unread' THEN 1 END) as unread,
                        COUNT(CASE WHEN status = 'read' THEN 1 END) as read,
                        COUNT(CASE WHEN status = 'acknowledged' THEN 1 END) as acknowledged,
                        COUNT(CASE WHEN status = 'acted_upon' THEN 1 END) as acted_upon,
                        COUNT(CASE WHEN status = 'dismissed' THEN 1 END) as dismissed,
                        COUNT(CASE WHEN requires_action = true THEN 1 END) as requiring_action
                    FROM knowledge_notifications
                    {where_clause}
                """,
                    *params,
                )

                # Notification type breakdown
                type_stats = await conn.fetch(
                    f"""
                    SELECT 
                        notification_type,
                        COUNT(*) as count,
                        COUNT(CASE WHEN status = 'acted_upon' THEN 1 END) as acted_upon_count,
                        COUNT(CASE WHEN status IN ('read', 'acknowledged', 'acted_upon') THEN 1 END) as engaged_count
                    FROM knowledge_notifications
                    {where_clause}
                    GROUP BY notification_type
                    ORDER BY count DESC
                """,
                    *params,
                )

                # Priority distribution
                priority_stats = await conn.fetch(
                    f"""
                    SELECT 
                        priority,
                        COUNT(*) as count,
                        AVG(CASE WHEN read_at IS NOT NULL THEN EXTRACT(EPOCH FROM read_at - created_at) END) / 3600 as avg_time_to_read_hours
                    FROM knowledge_notifications
                    {where_clause}
                    GROUP BY priority
                    ORDER BY 
                        CASE priority 
                            WHEN 'urgent' THEN 4
                            WHEN 'high' THEN 3
                            WHEN 'medium' THEN 2
                            ELSE 1
                        END DESC
                """,
                    *params,
                )

                return {
                    "time_period_days": days_back,
                    "basic_stats": dict(basic_stats) if basic_stats else {},
                    "type_breakdown": [dict(ts) for ts in type_stats],
                    "priority_distribution": [dict(ps) for ps in priority_stats],
                    "service_stats": {
                        "notifications_sent": self.notifications_sent,
                        "notifications_batched": self.notifications_batched,
                        "notifications_dismissed": self.notifications_dismissed,
                    },
                    "generated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return {}

    async def _create_notification(
        self,
        recipient_type: str,
        recipient_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        knowledge_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        priority: Priority = Priority.MEDIUM,
        requires_action: bool = False,
        suggested_actions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """Create a new notification"""

        notification_id = str(uuid.uuid4())

        # Check rate limits
        if not self._check_rate_limits(recipient_type, recipient_id, notification_type):
            logger.debug(
                f"Rate limit exceeded for {recipient_type} {recipient_id}, skipping notification"
            )
            return notification_id  # Return ID but don't create notification

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO knowledge_notifications (
                        id, recipient_type, recipient_id, notification_type,
                        title, message, knowledge_id, knowledge_type, priority,
                        requires_action, suggested_actions, metadata, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    notification_id,
                    recipient_type,
                    recipient_id,
                    notification_type.value,
                    title,
                    message,
                    knowledge_id,
                    knowledge_type,
                    priority.value,
                    requires_action,
                    json.dumps(suggested_actions or []),
                    json.dumps(metadata or {}),
                    expires_at,
                )

            # Update rate limiting
            self._update_rate_limits(recipient_type, recipient_id, notification_type)

            self.notifications_sent += 1

            logger.info(
                f"Created {notification_type.value} notification for {recipient_type} {recipient_id}"
            )

        except Exception as e:
            logger.error(f"Error creating notification: {e}")

        return notification_id

    async def _identify_knowledge_recipients(
        self,
        knowledge_type: str,
        organization_id: str,
        source_team_id: Optional[str],
        source_agent_id: Optional[str],
        knowledge_category: Optional[str],
    ) -> List[Tuple[str, str]]:
        """Identify who should be notified about new knowledge"""

        recipients = []

        try:
            async with self.pool.acquire() as conn:
                # Always notify the organization level
                recipients.append(("organization", organization_id))

                # Notify relevant teams based on category
                if knowledge_category:
                    # Find teams that work with this category
                    relevant_teams = await conn.fetch(
                        """
                        SELECT DISTINCT t.id 
                        FROM teams t
                        JOIN agents a ON t.id = a.team_id
                        JOIN tasks ta ON a.id = ta.agent_id
                        WHERE t.organization_id = $1
                          AND ta.metadata->>'category' = $2
                          AND ta.completed_at >= NOW() - INTERVAL '90 days'
                        LIMIT 10
                    """,
                        organization_id,
                        knowledge_category,
                    )

                    for team in relevant_teams:
                        recipients.append(("team", str(team["id"])))

                # Don't notify the source team/agent about their own contribution
                recipients = [
                    (rtype, rid)
                    for rtype, rid in recipients
                    if not (rtype == "team" and rid == source_team_id)
                    and not (rtype == "agent" and rid == source_agent_id)
                ]

        except Exception as e:
            logger.error(f"Error identifying knowledge recipients: {e}")

        return recipients

    def _should_notify_recipient(
        self,
        recipient_type: str,
        recipient_id: str,
        notification_type: NotificationType,
    ) -> bool:
        """Check if recipient should receive this type of notification"""

        # Check recipient preferences
        prefs = self.recipient_preferences.get(f"{recipient_type}:{recipient_id}", {})

        # Default to allowing notifications unless explicitly disabled
        type_prefs = prefs.get("notification_types", {})
        return type_prefs.get(notification_type.value, True)

    def _check_rate_limits(
        self,
        recipient_type: str,
        recipient_id: str,
        notification_type: NotificationType,
    ) -> bool:
        """Check if notification would exceed rate limits"""

        recipient_key = f"{recipient_type}:{recipient_id}"

        if recipient_key not in self.rate_limits:
            self.rate_limits[recipient_key] = {}

        limits = self.rate_limits[recipient_key]
        today = datetime.now().date()

        daily_count = limits.get(f"daily:{today}", 0)
        return daily_count < self.max_notifications_per_day

    def _update_rate_limits(
        self,
        recipient_type: str,
        recipient_id: str,
        notification_type: NotificationType,
    ):
        """Update rate limiting counters"""

        recipient_key = f"{recipient_type}:{recipient_id}"

        if recipient_key not in self.rate_limits:
            self.rate_limits[recipient_key] = {}

        limits = self.rate_limits[recipient_key]
        today = datetime.now().date()

        daily_key = f"daily:{today}"
        limits[daily_key] = limits.get(daily_key, 0) + 1

    def _calculate_knowledge_priority(
        self,
        knowledge_type: str,
        knowledge_category: Optional[str],
        metadata: Dict[str, Any],
    ) -> Priority:
        """Calculate notification priority based on knowledge characteristics"""

        # High priority for security and critical issues
        if knowledge_category in ["security", "troubleshooting"]:
            return Priority.HIGH

        # High priority for high-confidence, high-usage knowledge
        confidence = metadata.get("confidence_score", 0.5)
        usage_count = metadata.get("usage_count", 0)

        if confidence > 0.8 and usage_count > 5:
            return Priority.HIGH
        elif confidence > 0.6 or usage_count > 2:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    async def _create_new_knowledge_message(
        self,
        knowledge_id: str,
        knowledge_type: str,
        source_team_id: Optional[str],
        source_agent_id: Optional[str],
    ) -> str:
        """Create a message for new knowledge notification"""

        message_parts = []

        message_parts.append(
            f"New {knowledge_type} knowledge has been added to the organization knowledge base."
        )

        if source_team_id:
            # Get team name
            try:
                async with self.pool.acquire() as conn:
                    team_name = await conn.fetchval(
                        """
                        SELECT name FROM teams WHERE id = $1
                    """,
                        source_team_id,
                    )

                    if team_name:
                        message_parts.append(f"Source: {team_name} team")
            except Exception as e:
                logger.error(f"Error getting team name: {e}")

        message_parts.append(
            "This knowledge may be relevant to your current and future work."
        )

        return " ".join(message_parts)

    def _create_default_notification_rules(self) -> List[NotificationRule]:
        """Create default notification rules"""
        return [
            # Agent rules
            NotificationRule(
                recipient_type="agent",
                notification_types=[
                    NotificationType.RELEVANT_KNOWLEDGE,
                    NotificationType.KNOWLEDGE_REQUEST,
                ],
                conditions={"active_task": True},
                priority_threshold=Priority.MEDIUM,
                frequency_limit={"daily": 5, "weekly": 20},
                auto_dismiss_after_days=7,
            ),
            # Team rules
            NotificationRule(
                recipient_type="team",
                notification_types=[
                    NotificationType.NEW_KNOWLEDGE,
                    NotificationType.KNOWLEDGE_CONFLICT,
                    NotificationType.CROSS_TEAM_SHARING,
                ],
                conditions={},
                priority_threshold=Priority.MEDIUM,
                frequency_limit={"daily": 10, "weekly": 40},
                auto_dismiss_after_days=14,
            ),
            # Organization rules
            NotificationRule(
                recipient_type="organization",
                notification_types=[
                    NotificationType.KNOWLEDGE_CONFLICT,
                    NotificationType.KNOWLEDGE_GAP_IDENTIFIED,
                ],
                conditions={},
                priority_threshold=Priority.HIGH,
                frequency_limit={"daily": 3, "weekly": 15},
                auto_dismiss_after_days=30,
            ),
        ]

    def _row_to_notification(self, row) -> KnowledgeNotification:
        """Convert database row to KnowledgeNotification object"""
        return KnowledgeNotification(
            id=str(row["id"]),
            recipient_type=row["recipient_type"],
            recipient_id=str(row["recipient_id"]),
            notification_type=NotificationType(row["notification_type"]),
            title=row["title"],
            message=row["message"],
            knowledge_id=str(row["knowledge_id"]) if row["knowledge_id"] else None,
            knowledge_type=row["knowledge_type"],
            priority=Priority(row["priority"]),
            requires_action=row["requires_action"],
            status=NotificationStatus(row["status"]),
            suggested_actions=json.loads(row["suggested_actions"])
            if row["suggested_actions"]
            else [],
            metadata=json.loads(row["metadata"])
            if isinstance(row["metadata"], str)
            else row["metadata"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    async def _load_recipient_preferences(self):
        """Load notification preferences for recipients"""
        # This would load from database in a full implementation
        # For now, using defaults
        pass

    async def _notification_processor(self):
        """Background task to process notification batches"""

        while self._running:
            try:
                # Process any batched notifications
                if self.batch_notifications:
                    for (
                        recipient_key,
                        notifications,
                    ) in self.batch_notifications.items():
                        if len(notifications) >= self.batch_size:
                            # Process batch
                            await self._process_notification_batch(
                                recipient_key, notifications
                            )
                            self.batch_notifications[recipient_key] = []

                await asyncio.sleep(self.batch_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification processor: {e}")
                await asyncio.sleep(60)

    async def _cleanup_processor(self):
        """Background task to clean up old notifications"""

        while self._running:
            try:
                async with self.pool.acquire() as conn:
                    # Delete expired notifications
                    deleted_expired = (
                        await conn.fetchval(
                            """
                        DELETE FROM knowledge_notifications 
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                        RETURNING COUNT(*)
                    """
                        )
                        or 0
                    )

                    # Delete old dismissed notifications
                    cutoff_date = datetime.now() - timedelta(
                        days=self.notification_retention_days
                    )
                    deleted_old = (
                        await conn.fetchval(
                            """
                        DELETE FROM knowledge_notifications 
                        WHERE status = 'dismissed' AND created_at < $1
                        RETURNING COUNT(*)
                    """,
                            cutoff_date,
                        )
                        or 0
                    )

                    if deleted_expired > 0 or deleted_old > 0:
                        logger.info(
                            f"Cleaned up {deleted_expired} expired and {deleted_old} old notifications"
                        )

                # Clean up rate limiting data
                self._cleanup_rate_limits()

                await asyncio.sleep(3600)  # Run every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup processor: {e}")
                await asyncio.sleep(3600)

    async def _process_notification_batch(
        self, recipient_key: str, notifications: List[KnowledgeNotification]
    ):
        """Process a batch of notifications"""
        # This would implement batching logic, e.g., email digests
        self.notifications_batched += len(notifications)
        logger.info(
            f"Processed batch of {len(notifications)} notifications for {recipient_key}"
        )

    def _cleanup_rate_limits(self):
        """Clean up old rate limiting data"""
        current_date = datetime.now().date()

        for recipient_key in list(self.rate_limits.keys()):
            limits = self.rate_limits[recipient_key]

            # Remove old daily counts
            old_keys = [
                key
                for key in limits.keys()
                if key.startswith("daily:") and key != f"daily:{current_date}"
            ]

            for old_key in old_keys:
                del limits[old_key]

            # Remove empty entries
            if not limits:
                del self.rate_limits[recipient_key]
