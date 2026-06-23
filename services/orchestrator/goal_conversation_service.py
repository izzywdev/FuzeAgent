"""
Goal Conversation Management Service for FuzeAgent

This service manages AI-powered conversations about organizational goals,
enabling collaborative planning, progress reviews, problem-solving, and
strategic adjustments through intelligent dialogue.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import asyncpg

logger = logging.getLogger(__name__)

class ConversationType(str, Enum):
    PLANNING = "planning"
    REVIEW = "review"
    ADJUSTMENT = "adjustment"
    PROBLEM_SOLVING = "problem_solving"
    BRAINSTORMING = "brainstorming"
    RETROSPECTIVE = "retrospective"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"

class MessageType(str, Enum):
    SYSTEM = "system"
    AGENT = "agent"
    HUMAN = "human"
    AI_ANALYSIS = "ai_analysis"
    ACTION_ITEM = "action_item"

@dataclass
class ConversationMessage:
    """Represents a message in a goal conversation"""
    id: str
    message_type: MessageType
    sender_id: Optional[str]
    sender_name: Optional[str]
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    references: List[str]  # Referenced message IDs
    reactions: List[Dict[str, Any]]  # Message reactions/acknowledgments

@dataclass
class ConversationInsight:
    """Represents an AI-generated insight from conversation analysis"""
    id: str
    insight_type: str  # pattern, risk, opportunity, recommendation
    title: str
    description: str
    confidence_score: float
    supporting_messages: List[str]
    suggested_actions: List[Dict[str, Any]]
    generated_at: datetime

@dataclass
class ActionItem:
    """Represents an action item derived from conversation"""
    id: str
    title: str
    description: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    status: str  # pending, in_progress, completed, cancelled
    priority: int
    source_messages: List[str]
    created_at: datetime
    completed_at: Optional[datetime]

class GoalConversationService:
    """
    Manages AI-powered conversations for organizational goal planning,
    tracking, and optimization with intelligent insights and action generation.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        
        # Configuration
        self.max_conversation_messages = 1000
        self.insight_confidence_threshold = 0.6
        self.auto_action_item_threshold = 0.8
        
        # AI conversation templates and prompts
        self.conversation_starters = self._initialize_conversation_starters()
        self.analysis_prompts = self._initialize_analysis_prompts()
        
        # Statistics
        self.conversations_created = 0
        self.messages_processed = 0
        self.insights_generated = 0
        self.action_items_created = 0
    
    async def initialize(self):
        """Initialize the goal conversation service"""
        logger.info("Initializing GoalConversationService")
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
            
            logger.info("GoalConversationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GoalConversationService: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("GoalConversationService closed")
    
    async def create_goal_conversation(
        self,
        goal_id: str,
        conversation_type: ConversationType,
        conversation_title: str,
        initial_context: Optional[Dict[str, Any]] = None,
        participants: Optional[List[Dict[str, Any]]] = None,
        created_by: Optional[str] = None
    ) -> str:
        """Create a new conversation for a goal"""
        
        conversation_id = str(uuid.uuid4())
        
        if initial_context is None:
            initial_context = {}
        if participants is None:
            participants = []
        
        try:
            async with self.pool.acquire() as conn:
                # Get goal context
                goal = await conn.fetchrow("""
                    SELECT title, description, goal_type, target_deadline, 
                           progress_percentage, current_value, target_value
                    FROM organization_goals WHERE id = $1
                """, goal_id)
                
                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")
                
                # Enhanced context with goal information
                enhanced_context = {
                    **initial_context,
                    'goal_title': goal['title'],
                    'goal_type': goal['goal_type'],
                    'goal_progress': float(goal['progress_percentage']),
                    'days_to_deadline': (goal['target_deadline'] - datetime.now().date()).days,
                    'conversation_created_at': datetime.now().isoformat()
                }
                
                # Create conversation
                await conn.execute("""
                    INSERT INTO goal_conversations (
                        id, goal_id, conversation_type, conversation_title,
                        conversation_context, participants, status, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    conversation_id, goal_id, conversation_type.value, conversation_title,
                    json.dumps(enhanced_context), json.dumps(participants), 
                    ConversationStatus.ACTIVE.value, created_by
                )
                
                # Add initial system message with conversation starter
                starter_message = self._generate_conversation_starter(
                    conversation_type, goal, enhanced_context
                )
                
                await self._add_message(
                    conversation_id, MessageType.SYSTEM, None, "System",
                    starter_message, {'conversation_starter': True}
                )
            
            self.conversations_created += 1
            logger.info(f"Created conversation {conversation_id} for goal {goal_id}")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def add_message_to_conversation(
        self,
        conversation_id: str,
        message_type: MessageType,
        sender_id: Optional[str],
        sender_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        references: Optional[List[str]] = None
    ) -> str:
        """Add a message to a conversation"""
        
        if metadata is None:
            metadata = {}
        if references is None:
            references = []
        
        try:
            # Add the message
            message_id = await self._add_message(
                conversation_id, message_type, sender_id, sender_name,
                content, metadata, references
            )
            
            # Trigger conversation analysis for insights
            await self._analyze_conversation_for_insights(conversation_id)
            
            # Update conversation activity timestamp
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE goal_conversations 
                    SET last_activity_at = NOW(), updated_at = NOW()
                    WHERE id = $1
                """, conversation_id)
            
            self.messages_processed += 1
            
            return message_id
            
        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get full conversation with messages, insights, and action items"""
        
        try:
            async with self.pool.acquire() as conn:
                # Get conversation details
                conversation = await conn.fetchrow("""
                    SELECT gc.*, og.title as goal_title, og.goal_type
                    FROM goal_conversations gc
                    JOIN organization_goals og ON gc.goal_id = og.id
                    WHERE gc.id = $1
                """, conversation_id)
                
                if not conversation:
                    return None
                
                # Get messages
                messages = json.loads(conversation['messages']) if conversation['messages'] else []
                
                # Get insights
                insights = json.loads(conversation['insights_generated']) if conversation['insights_generated'] else []
                
                # Get action items
                action_items = json.loads(conversation['action_items']) if conversation['action_items'] else []
                
                return {
                    'id': str(conversation['id']),
                    'goal_id': str(conversation['goal_id']),
                    'goal_title': conversation['goal_title'],
                    'conversation_type': conversation['conversation_type'],
                    'conversation_title': conversation['conversation_title'],
                    'conversation_summary': conversation['conversation_summary'],
                    'conversation_context': json.loads(conversation['conversation_context']) if conversation['conversation_context'] else {},
                    'participants': json.loads(conversation['participants']) if conversation['participants'] else [],
                    'messages': messages,
                    'insights_generated': insights,
                    'action_items': action_items,
                    'status': conversation['status'],
                    'last_activity_at': conversation['last_activity_at'].isoformat() if conversation['last_activity_at'] else None,
                    'created_at': conversation['created_at'].isoformat(),
                    'updated_at': conversation['updated_at'].isoformat(),
                    'message_count': len(messages),
                    'insight_count': len(insights),
                    'action_item_count': len(action_items)
                }
                
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None
    
    async def generate_planning_milestones(
        self,
        conversation_id: str,
        planning_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate milestone suggestions based on conversation analysis"""
        
        try:
            async with self.pool.acquire() as conn:
                # Get conversation and goal context
                conversation = await conn.fetchrow("""
                    SELECT gc.*, og.title, og.description, og.goal_type, 
                           og.target_deadline, og.target_value, og.target_unit
                    FROM goal_conversations gc
                    JOIN organization_goals og ON gc.goal_id = og.id
                    WHERE gc.id = $1
                """, conversation_id)
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
                
                # Analyze conversation content for milestone ideas
                messages = json.loads(conversation['messages']) if conversation['messages'] else []
                milestone_suggestions = self._extract_milestone_ideas_from_conversation(
                    messages, conversation, planning_context
                )
                
                # Generate AI-powered milestone recommendations
                ai_milestones = await self._generate_ai_milestone_recommendations(
                    conversation, milestone_suggestions, planning_context
                )
                
                # Add milestones as insights to the conversation
                milestone_insight = {
                    'id': str(uuid.uuid4()),
                    'insight_type': 'milestone_recommendations',
                    'title': 'AI-Generated Milestone Recommendations',
                    'description': f'Based on conversation analysis, here are {len(ai_milestones)} recommended milestones',
                    'confidence_score': 0.85,
                    'supporting_messages': [msg['id'] for msg in messages[-5:] if 'id' in msg],  # Last 5 messages
                    'suggested_actions': [
                        {
                            'action': 'create_milestones',
                            'description': 'Create these milestones for the goal',
                            'milestones': ai_milestones
                        }
                    ],
                    'generated_at': datetime.now().isoformat()
                }
                
                # Update conversation with milestone insight
                await self._add_insight_to_conversation(conversation_id, milestone_insight)
                
                return ai_milestones
                
        except Exception as e:
            logger.error(f"Error generating planning milestones: {e}")
            return []
    
    async def conduct_progress_review(
        self,
        conversation_id: str,
        review_period_days: int = 30
    ) -> Dict[str, Any]:
        """Conduct AI-powered progress review for a goal conversation"""
        
        try:
            async with self.pool.acquire() as conn:
                # Get conversation and goal data
                conversation = await conn.fetchrow("""
                    SELECT gc.*, og.*
                    FROM goal_conversations gc
                    JOIN organization_goals og ON gc.goal_id = og.id
                    WHERE gc.id = $1
                """, conversation_id)
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
                
                # Get recent progress data
                progress_data = await conn.fetch("""
                    SELECT * FROM goal_progress_tracking
                    WHERE goal_id = $1 
                      AND recorded_at >= NOW() - INTERVAL '%s days'
                    ORDER BY recorded_at DESC
                """, str(conversation['goal_id']), review_period_days)
                
                # Get milestones and tasks status
                milestone_status = await conn.fetch("""
                    SELECT status, COUNT(*) as count
                    FROM goal_milestones
                    WHERE goal_id = $1
                    GROUP BY status
                """, str(conversation['goal_id']))
                
                task_status = await conn.fetch("""
                    SELECT status, COUNT(*) as count
                    FROM goal_tasks
                    WHERE goal_id = $1
                    GROUP BY status
                """, str(conversation['goal_id']))
                
                # Generate review analysis
                review_analysis = {
                    'review_period_days': review_period_days,
                    'goal_progress': {
                        'current_progress': float(conversation['progress_percentage']),
                        'target_value': float(conversation['target_value']) if conversation['target_value'] else None,
                        'current_value': float(conversation['current_value']) if conversation['current_value'] else None,
                        'completion_confidence': float(conversation['completion_confidence'])
                    },
                    'milestone_summary': {row['status']: row['count'] for row in milestone_status},
                    'task_summary': {row['status']: row['count'] for row in task_status},
                    'progress_trend': self._calculate_progress_trend([dict(p) for p in progress_data]),
                    'risk_assessment': self._assess_goal_risks(conversation, progress_data),
                    'recommendations': self._generate_progress_recommendations(conversation, progress_data)
                }
                
                # Add review as a structured message
                review_message = self._format_progress_review_message(review_analysis)
                await self._add_message(
                    conversation_id, MessageType.AI_ANALYSIS, None, "Progress Analyzer",
                    review_message, {'review_analysis': review_analysis}
                )
                
                return review_analysis
                
        except Exception as e:
            logger.error(f"Error conducting progress review: {e}")
            return {'error': str(e)}
    
    async def extract_action_items_from_conversation(
        self,
        conversation_id: str,
        auto_assign: bool = True
    ) -> List[Dict[str, Any]]:
        """Extract and create action items from conversation analysis"""
        
        try:
            async with self.pool.acquire() as conn:
                conversation = await conn.fetchrow("""
                    SELECT * FROM goal_conversations WHERE id = $1
                """, conversation_id)
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
                
                messages = json.loads(conversation['messages']) if conversation['messages'] else []
                
                # Analyze messages for actionable items
                potential_actions = self._identify_action_items_in_messages(messages)
                
                # Convert to action item format
                action_items = []
                for action in potential_actions:
                    if action['confidence'] >= self.auto_action_item_threshold:
                        action_item = {
                            'id': str(uuid.uuid4()),
                            'title': action['title'],
                            'description': action['description'],
                            'assigned_to': action.get('assigned_to') if auto_assign else None,
                            'due_date': action.get('due_date'),
                            'status': 'pending',
                            'priority': action.get('priority', 5),
                            'source_messages': action['source_messages'],
                            'created_at': datetime.now().isoformat(),
                            'confidence_score': action['confidence']
                        }
                        action_items.append(action_item)
                
                # Update conversation with action items
                if action_items:
                    existing_actions = json.loads(conversation['action_items']) if conversation['action_items'] else []
                    all_actions = existing_actions + action_items
                    
                    await conn.execute("""
                        UPDATE goal_conversations 
                        SET action_items = $2, updated_at = NOW()
                        WHERE id = $1
                    """, conversation_id, json.dumps(all_actions))
                
                self.action_items_created += len(action_items)
                
                return action_items
                
        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return []
    
    async def get_goal_conversations(
        self,
        goal_id: str,
        conversation_type: Optional[ConversationType] = None,
        status: Optional[ConversationStatus] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversations for a goal with optional filtering"""
        
        try:
            async with self.pool.acquire() as conn:
                where_conditions = ["goal_id = $1"]
                params = [goal_id]
                param_idx = 2
                
                if conversation_type:
                    where_conditions.append(f"conversation_type = ${param_idx}")
                    params.append(conversation_type.value)
                    param_idx += 1
                
                if status:
                    where_conditions.append(f"status = ${param_idx}")
                    params.append(status.value)
                    param_idx += 1
                
                where_clause = " AND ".join(where_conditions)
                
                conversations = await conn.fetch(f"""
                    SELECT id, conversation_type, conversation_title, conversation_summary,
                           status, last_activity_at, created_at,
                           COALESCE(array_length(string_to_array(messages::text, '}}'), 1), 0) as message_count,
                           COALESCE(array_length(string_to_array(action_items::text, '}}'), 1), 0) as action_count
                    FROM goal_conversations
                    WHERE {where_clause}
                    ORDER BY last_activity_at DESC, created_at DESC
                    LIMIT ${param_idx}
                """, *params, limit)
                
                return [dict(conv) for conv in conversations]
                
        except Exception as e:
            logger.error(f"Error getting conversations for goal {goal_id}: {e}")
            return []
    
    # Helper methods for conversation management
    
    async def _add_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        sender_id: Optional[str],
        sender_name: str,
        content: str,
        metadata: Dict[str, Any],
        references: Optional[List[str]] = None
    ) -> str:
        """Add a message to conversation"""
        
        message_id = str(uuid.uuid4())
        message = {
            'id': message_id,
            'message_type': message_type.value,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'content': content,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat(),
            'references': references or [],
            'reactions': []
        }
        
        async with self.pool.acquire() as conn:
            # Get current messages
            current_messages = await conn.fetchval("""
                SELECT messages FROM goal_conversations WHERE id = $1
            """, conversation_id)
            
            messages = json.loads(current_messages) if current_messages else []
            messages.append(message)
            
            # Limit message history
            if len(messages) > self.max_conversation_messages:
                messages = messages[-self.max_conversation_messages:]
            
            # Update conversation
            await conn.execute("""
                UPDATE goal_conversations 
                SET messages = $2, updated_at = NOW()
                WHERE id = $1
            """, conversation_id, json.dumps(messages))
        
        return message_id
    
    async def _add_insight_to_conversation(
        self,
        conversation_id: str,
        insight: Dict[str, Any]
    ):
        """Add an insight to conversation"""
        
        async with self.pool.acquire() as conn:
            # Get current insights
            current_insights = await conn.fetchval("""
                SELECT insights_generated FROM goal_conversations WHERE id = $1
            """, conversation_id)
            
            insights = json.loads(current_insights) if current_insights else []
            insights.append(insight)
            
            # Update conversation
            await conn.execute("""
                UPDATE goal_conversations 
                SET insights_generated = $2, updated_at = NOW()
                WHERE id = $1
            """, conversation_id, json.dumps(insights))
        
        self.insights_generated += 1
    
    def _generate_conversation_starter(
        self,
        conversation_type: ConversationType,
        goal: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate an appropriate conversation starter"""
        
        starters = self.conversation_starters.get(conversation_type, {})
        
        if conversation_type == ConversationType.PLANNING:
            return starters['default'].format(
                goal_title=goal['title'],
                goal_type=goal['goal_type'],
                deadline=goal['target_deadline'].strftime('%B %d, %Y'),
                target_value=goal['target_value'] if goal['target_value'] else 'defined objectives'
            )
        elif conversation_type == ConversationType.REVIEW:
            return starters['default'].format(
                goal_title=goal['title'],
                current_progress=f"{goal['progress_percentage']:.1f}%"
            )
        else:
            return starters.get('default', f"Let's discuss the {goal['title']} goal.")
    
    def _initialize_conversation_starters(self) -> Dict[str, Dict[str, str]]:
        """Initialize conversation starter templates"""
        
        return {
            ConversationType.PLANNING: {
                'default': """Welcome to the strategic planning session for "{goal_title}"!

🎯 **Goal**: {goal_title}
📊 **Type**: {goal_type}
📅 **Deadline**: {deadline}
🎌 **Target**: {target_value}

Let's break this goal down into actionable milestones and tasks. Here are some questions to get us started:

1. **What are the major milestones we need to achieve?**
2. **What dependencies and blockers should we consider?**
3. **Which teams and resources will be involved?**
4. **How should we measure progress along the way?**

What aspect would you like to focus on first?"""
            },
            ConversationType.REVIEW: {
                'default': """Time for a progress review of "{goal_title}"!

📈 **Current Progress**: {current_progress}

Let's evaluate our progress, identify what's working well, and address any challenges. 

Key areas to discuss:
- Recent achievements and wins
- Current blockers or risks  
- Resource allocation and team performance
- Timeline adjustments if needed
- Next steps and priorities

What would you like to review first?"""
            },
            ConversationType.PROBLEM_SOLVING: {
                'default': """Problem-solving session for "{goal_title}".

Let's identify the specific challenges we're facing and work together to find solutions. Please share:
- What specific problems or blockers have emerged?
- What have we tried so far?  
- What constraints or requirements should we consider?

What's the main challenge you'd like to tackle?"""
            }
        }
    
    def _initialize_analysis_prompts(self) -> Dict[str, str]:
        """Initialize AI analysis prompts for conversation processing"""
        
        return {
            'extract_milestones': """Analyze this goal conversation and extract potential milestones mentioned or implied. Look for:
- Time-based deliverables or checkpoints
- Measurable objectives or targets
- Dependencies between activities
- Key decision points or reviews

Return milestones with titles, descriptions, and target dates.""",
            
            'identify_risks': """Analyze this conversation for potential risks, blockers, or concerns mentioned. Look for:
- Resource constraints or availability issues
- Technical challenges or unknowns
- Timeline concerns or dependencies
- Team capacity or skill gaps
- External dependencies or market factors

Assess the probability and impact of each risk.""",
            
            'extract_actions': """Extract specific action items from this conversation. Look for:
- Tasks or activities that someone needs to do
- Decisions that need to be made
- Information that needs to be gathered
- People who need to be contacted
- Deadlines or time-sensitive items

Include who should be responsible and when it should be done."""
        }
    
    # Placeholder implementations for AI analysis methods
    
    async def _analyze_conversation_for_insights(self, conversation_id: str):
        """Analyze conversation for insights (placeholder for AI integration)"""
        # This would integrate with an AI service for conversation analysis
        pass
    
    def _extract_milestone_ideas_from_conversation(
        self,
        messages: List[Dict[str, Any]],
        conversation: Dict[str, Any],
        planning_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract milestone ideas from conversation messages"""
        # Simplified implementation - would use NLP/AI for real extraction
        milestone_keywords = ['milestone', 'phase', 'deliverable', 'target', 'deadline', 'complete']
        
        milestones = []
        for message in messages:
            content = message.get('content', '').lower()
            if any(keyword in content for keyword in milestone_keywords):
                # Extract potential milestone (simplified)
                milestones.append({
                    'title': f"Milestone from conversation",
                    'description': message.get('content', '')[:200],
                    'source_message': message.get('id'),
                    'confidence': 0.7
                })
        
        return milestones[:5]  # Return top 5 candidates
    
    async def _generate_ai_milestone_recommendations(
        self,
        conversation: Dict[str, Any],
        milestone_suggestions: List[Dict[str, Any]],
        planning_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered milestone recommendations"""
        # Placeholder implementation - would use AI for intelligent milestone generation
        
        goal_type = conversation['goal_type']
        timeline_days = (conversation['target_deadline'] - datetime.now().date()).days
        
        # Generate sample milestones based on goal type
        if goal_type == 'business' and 'revenue' in conversation['title'].lower():
            return [
                {
                    'title': 'Foundation Setup',
                    'description': 'Establish initial infrastructure, team structure, and processes',
                    'target_date': (datetime.now() + timedelta(days=timeline_days//4)).date().isoformat(),
                    'milestone_type': 'checkpoint'
                },
                {
                    'title': 'Growth Phase Launch',
                    'description': 'Execute marketing campaigns and sales initiatives',
                    'target_date': (datetime.now() + timedelta(days=timeline_days//2)).date().isoformat(),
                    'milestone_type': 'deliverable'
                },
                {
                    'title': 'Scale and Optimize',
                    'description': 'Optimize processes and scale operations for target achievement',
                    'target_date': (datetime.now() + timedelta(days=timeline_days*3//4)).date().isoformat(),
                    'milestone_type': 'metric'
                }
            ]
        
        return []
    
    # Additional helper methods for conversation analysis
    def _calculate_progress_trend(self, progress_data: List[Dict[str, Any]]) -> str:
        """Calculate progress trend from historical data"""
        if len(progress_data) < 2:
            return 'insufficient_data'
        
        # Simple trend calculation
        recent_progress = progress_data[0]['progress_percentage']
        older_progress = progress_data[-1]['progress_percentage']
        
        if recent_progress > older_progress * 1.1:
            return 'accelerating'
        elif recent_progress < older_progress * 0.9:
            return 'declining'
        else:
            return 'steady'
    
    def _assess_goal_risks(self, goal: Dict[str, Any], progress_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assess risks based on goal and progress data"""
        risks = []
        
        # Timeline risk
        days_remaining = (goal['target_deadline'] - datetime.now().date()).days
        progress = float(goal['progress_percentage'])
        
        if days_remaining < 30 and progress < 70:
            risks.append({
                'type': 'timeline_risk',
                'severity': 'high',
                'description': 'Goal progress is behind schedule with limited time remaining'
            })
        
        return risks
    
    def _generate_progress_recommendations(self, goal: Dict[str, Any], progress_data: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on progress analysis"""
        recommendations = []
        
        progress = float(goal['progress_percentage'])
        
        if progress < 25:
            recommendations.append("Consider breaking down remaining work into smaller, more manageable tasks")
        
        if progress > 75:
            recommendations.append("Focus on final quality checks and prepare for goal completion")
        
        return recommendations
    
    def _identify_action_items_in_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify potential action items from messages"""
        # Simplified implementation - would use NLP for real extraction
        action_keywords = ['need to', 'should', 'must', 'will', 'action', 'task', 'todo']
        
        actions = []
        for message in messages:
            content = message.get('content', '').lower()
            if any(keyword in content for keyword in action_keywords):
                actions.append({
                    'title': f"Action item from conversation",
                    'description': message.get('content', '')[:200],
                    'source_messages': [message.get('id')],
                    'confidence': 0.8,
                    'priority': 5
                })
        
        return actions[:10]  # Return top 10 candidates
    
    def _format_progress_review_message(self, review_analysis: Dict[str, Any]) -> str:
        """Format progress review analysis as a readable message"""
        
        progress = review_analysis['goal_progress']['current_progress']
        trend = review_analysis['progress_trend']
        
        message = f"""## Progress Review Summary

**Current Progress**: {progress:.1f}%
**Trend**: {trend.replace('_', ' ').title()}

### Key Metrics
"""
        
        if review_analysis['milestone_summary']:
            message += "\n**Milestones:**\n"
            for status, count in review_analysis['milestone_summary'].items():
                message += f"- {status.replace('_', ' ').title()}: {count}\n"
        
        if review_analysis['recommendations']:
            message += "\n### Recommendations\n"
            for i, rec in enumerate(review_analysis['recommendations'], 1):
                message += f"{i}. {rec}\n"
        
        return message