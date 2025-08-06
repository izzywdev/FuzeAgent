"""
Agent Memory Manager for Persistent Agent Memory

Manages agent's life-long memory stored in centralized database but accessed
from within agent containers. Provides semantic search, learning capabilities,
and expertise tracking across container instances.
"""

import asyncio
import asyncpg
import json
import logging
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

# For embeddings - in production you'd want a proper embedding service
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    LEARNING = "learning"
    PATTERN = "pattern"
    ERROR = "error"
    SUCCESS = "success"
    TASK_OUTCOME = "task_outcome"
    CODE_PATTERN = "code_pattern"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"

class PerformanceTrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"

@dataclass
class AgentMemory:
    """Represents a single memory entry"""
    id: str
    agent_id: str
    container_instance_id: str
    task_id: Optional[str]
    session_id: Optional[str]
    memory_type: MemoryType
    content: str
    embedding: Optional[List[float]]
    code_context: Dict[str, Any]
    task_context: Dict[str, Any]
    outcome_context: Dict[str, Any]
    confidence_score: float
    success_correlation: float
    usage_count: int
    last_accessed: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class AgentExpertise:
    """Represents expertise in a skill area"""
    id: str
    agent_id: str
    skill_area: str
    expertise_level: float
    task_count: int
    success_rate: float
    learning_velocity: float
    last_task_performance: Optional[float]
    performance_trend: PerformanceTrend
    key_learnings: Dict[str, Any]
    common_mistakes: Dict[str, Any]
    successful_approaches: Dict[str, Any]
    updated_at: datetime

@dataclass
class MemoryQueryResult:
    """Result of a memory query"""
    memory: AgentMemory
    relevance_score: float

class LRUCache:
    """Simple LRU cache for memory entries"""
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.cache = {}
        self.access_order = []
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.maxsize:
            # Remove least recently used
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def __contains__(self, key: str) -> bool:
        return key in self.cache
    
    def __getitem__(self, key: str):
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        self.set(key, value)

class AgentMemoryManager:
    """
    Manages agent's persistent memory stored in centralized database
    but accessed from within the agent container.
    
    Features:
    - Semantic memory search using vector embeddings
    - Expertise tracking and learning analytics
    - Memory caching for performance
    - Batch operations for efficiency
    - Container instance tracking
    """
    
    def __init__(self, agent_id: str, container_instance_id: str):
        self.agent_id = agent_id
        self.container_instance_id = container_instance_id
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # Local caching
        self.local_cache = LRUCache(maxsize=1000)
        self.memory_buffer: List[Dict[str, Any]] = []
        self.buffer_max_size = 10
        
        # Embedding model for semantic search
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384
        
        # Statistics
        self.session_memories_created = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.queries_processed = 0
        
        # Configuration
        self.batch_flush_interval = 30  # seconds
        self.max_memory_age_days = 365  # Keep memories for 1 year
        self.min_confidence_threshold = 0.3
        
        # Background tasks
        self._flush_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self, database_url: str):
        """Initialize the memory manager with database connection"""
        logger.info(f"Initializing AgentMemoryManager for agent {self.agent_id}")
        
        try:
            # Create database connection pool
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Register this container instance
            await self._register_container_instance()
            
            # Load recent high-value memories into cache
            await self._load_recent_memories()
            
            # Start background tasks
            self._flush_task = asyncio.create_task(self._periodic_flush())
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            logger.info(f"AgentMemoryManager initialized for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentMemoryManager: {e}")
            raise
    
    async def close(self):
        """Clean up resources"""
        logger.info(f"Closing AgentMemoryManager for agent {self.agent_id}")
        
        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Flush any remaining memories
        await self._flush_memory_buffer()
        
        # Update container instance end time
        await self._update_container_instance_end()
        
        # Close database pool
        if self.db_pool:
            await self.db_pool.close()
    
    async def store_memory(
        self,
        task_id: Optional[str],
        memory_type: MemoryType,
        content: str,
        session_id: Optional[str] = None,
        code_context: Optional[Dict[str, Any]] = None,
        task_context: Optional[Dict[str, Any]] = None,
        outcome_context: Optional[Dict[str, Any]] = None,
        confidence_score: float = 1.0
    ) -> str:
        """Store a new memory entry"""
        
        memory_id = str(uuid.uuid4())
        
        # Generate embedding for semantic search
        embedding = self._generate_embedding(content)
        
        memory_entry = {
            'id': memory_id,
            'agent_id': self.agent_id,
            'container_instance_id': self.container_instance_id,
            'task_id': task_id,
            'session_id': session_id,
            'memory_type': memory_type.value,
            'content': content,
            'embedding': embedding,
            'code_context': json.dumps(code_context or {}),
            'task_context': json.dumps(task_context or {}),
            'outcome_context': json.dumps(outcome_context or {}),
            'confidence_score': max(0.0, min(1.0, confidence_score)),
            'success_correlation': 0.0,  # Will be calculated later
            'usage_count': 0,
            'created_at': datetime.now(),
            'created_by_container': self.container_instance_id
        }
        
        # Add to buffer for batch processing
        self.memory_buffer.append(memory_entry)
        self.session_memories_created += 1
        
        # Cache locally for immediate access
        self.local_cache[memory_id] = memory_entry
        
        # Flush buffer if it's getting full
        if len(self.memory_buffer) >= self.buffer_max_size:
            await self._flush_memory_buffer()
        
        logger.debug(f"Stored memory {memory_id} ({memory_type.value}) for agent {self.agent_id}")
        return memory_id
    
    async def query_memories(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        task_context: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_confidence: float = 0.5,
        include_similar_tasks: bool = True
    ) -> List[MemoryQueryResult]:
        """Query agent's memories using semantic search"""
        
        self.queries_processed += 1
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Build query parameters
        memory_type_list = [mt.value for mt in memory_types] if memory_types else None
        
        try:
            async with self.db_pool.acquire() as conn:
                # Use the database function for efficient vector search
                memories = await conn.fetch("""
                    SELECT * FROM get_agent_relevant_memories($1, $2, $3, $4, $5)
                """, 
                    self.agent_id,
                    query_embedding,
                    memory_type_list,
                    min_confidence,
                    limit
                )
                
                # Convert to MemoryQueryResult objects
                results = []
                memory_ids = []
                
                for memory_row in memories:
                    # Get full memory details
                    full_memory = await conn.fetchrow("""
                        SELECT * FROM agent_memory WHERE id = $1
                    """, memory_row['memory_id'])
                    
                    if full_memory:
                        agent_memory = self._row_to_memory(full_memory)
                        result = MemoryQueryResult(
                            memory=agent_memory,
                            relevance_score=memory_row['relevance_score']
                        )
                        results.append(result)
                        memory_ids.append(memory_row['memory_id'])
                
                # Update memory usage statistics
                if memory_ids:
                    await conn.execute("""
                        SELECT update_memory_usage($1, $2, $3)
                    """, 
                        memory_ids, 
                        self.agent_id,
                        json.dumps({
                            'query': query[:200],  # Truncate long queries
                            'context': task_context or {},
                            'timestamp': datetime.now().isoformat()
                        })
                    )
                
                logger.debug(f"Found {len(results)} relevant memories for query: {query[:50]}...")
                return results
                
        except Exception as e:
            logger.error(f"Error querying memories: {e}")
            return []
    
    async def learn_from_task_outcome(
        self,
        task_id: str,
        task_result: Dict[str, Any]
    ):
        """Learn from task completion and update expertise"""
        
        success = task_result.get('success', False)
        task_type = task_result.get('task_type', 'unknown')
        complexity = task_result.get('complexity', 'medium')
        duration_minutes = task_result.get('duration_minutes', 0)
        error_message = task_result.get('error_message')
        
        # Store outcome memory
        outcome_content = f"Task {'completed successfully' if success else 'failed'}: {task_result.get('description', '')}"
        if error_message:
            outcome_content += f"\nError: {error_message}"
        
        await self.store_memory(
            task_id=task_id,
            memory_type=MemoryType.TASK_OUTCOME,
            content=outcome_content,
            task_context={
                'task_type': task_type,
                'complexity': complexity,
                'duration_minutes': duration_minutes
            },
            outcome_context={
                'success': success,
                'error_message': error_message,
                'files_modified': task_result.get('files_modified', []),
                'test_results': task_result.get('test_results', {}),
                'performance_metrics': task_result.get('performance_metrics', {})
            },
            confidence_score=1.0 if success else 0.3
        )
        
        # Update expertise tracking
        await self._update_expertise(task_type, success, task_result)
        
        # If task failed, store error patterns for learning
        if not success and error_message:
            await self.store_memory(
                task_id=task_id,
                memory_type=MemoryType.ERROR,
                content=f"Error in {task_type}: {error_message}",
                code_context=task_result.get('code_context', {}),
                task_context={'task_type': task_type, 'complexity': complexity},
                outcome_context={'error_details': task_result.get('error_details', {})},
                confidence_score=0.8
            )
    
    async def get_agent_expertise_summary(self) -> Dict[str, Any]:
        """Get comprehensive agent expertise and memory statistics"""
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get expertise areas
                expertise_areas = await conn.fetch("""
                    SELECT * FROM agent_expertise 
                    WHERE agent_id = $1 
                    ORDER BY expertise_level DESC
                """, self.agent_id)
                
                # Get memory statistics
                memory_stats = await conn.fetchrow("""
                    SELECT * FROM agent_memory_summary WHERE agent_id = $1
                """, self.agent_id)
                
                # Get recent performance trends
                recent_performance = await conn.fetch("""
                    SELECT 
                        memory_type,
                        COUNT(*) as count,
                        AVG(confidence_score) as avg_confidence,
                        MAX(created_at) as last_created
                    FROM agent_memory 
                    WHERE agent_id = $1 AND created_at > NOW() - INTERVAL '7 days'
                    GROUP BY memory_type
                    ORDER BY count DESC
                """, self.agent_id)
                
                # Get container instance history
                container_history = await conn.fetch("""
                    SELECT container_instance_id, started_at, ended_at, 
                           tasks_completed, memory_entries_created
                    FROM agent_container_instances 
                    WHERE agent_id = $1 
                    ORDER BY started_at DESC
                    LIMIT 10
                """, self.agent_id)
                
                return {
                    'agent_id': self.agent_id,
                    'current_container_instance': self.container_instance_id,
                    'memory_statistics': dict(memory_stats) if memory_stats else {},
                    'expertise_areas': [dict(area) for area in expertise_areas],
                    'recent_performance': [dict(perf) for perf in recent_performance],
                    'container_history': [dict(container) for container in container_history],
                    'session_stats': {
                        'memories_created': self.session_memories_created,
                        'queries_processed': self.queries_processed,
                        'cache_hit_rate': self.cache_hits / max(1, self.cache_hits + self.cache_misses),
                        'buffer_size': len(self.memory_buffer)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting expertise summary: {e}")
            return {
                'agent_id': self.agent_id,
                'error': str(e)
            }
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformers"""
        try:
            # In production, you might want to use a dedicated embedding service
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.embedding_dim
    
    async def _register_container_instance(self):
        """Register this container instance in the database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO agent_container_instances (
                        agent_id, container_id, container_instance_id, started_at
                    ) VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (container_instance_id) DO NOTHING
                """, 
                    self.agent_id,
                    f"container-{self.agent_id}-{int(time.time())}",
                    self.container_instance_id
                )
                
                logger.info(f"Registered container instance {self.container_instance_id}")
                
        except Exception as e:
            logger.error(f"Error registering container instance: {e}")
    
    async def _update_container_instance_end(self):
        """Update container instance end time"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE agent_container_instances 
                    SET ended_at = NOW(), 
                        tasks_completed = $2,
                        memory_entries_created = $3,
                        status = 'stopped'
                    WHERE container_instance_id = $1
                """, 
                    self.container_instance_id,
                    0,  # Would track tasks completed in practice
                    self.session_memories_created
                )
                
        except Exception as e:
            logger.error(f"Error updating container instance end: {e}")
    
    async def _load_recent_memories(self):
        """Load recent high-value memories into cache"""
        try:
            async with self.db_pool.acquire() as conn:
                recent_memories = await conn.fetch("""
                    SELECT * FROM agent_memory 
                    WHERE agent_id = $1 
                        AND confidence_score > 0.7
                        AND created_at > NOW() - INTERVAL '7 days'
                    ORDER BY confidence_score DESC, usage_count DESC
                    LIMIT 100
                """, self.agent_id)
                
                for memory_row in recent_memories:
                    memory = self._row_to_memory(memory_row)
                    self.local_cache[memory.id] = memory
                
                logger.info(f"Loaded {len(recent_memories)} recent memories into cache")
                
        except Exception as e:
            logger.error(f"Error loading recent memories: {e}")
    
    async def _flush_memory_buffer(self):
        """Flush buffered memories to database"""
        if not self.memory_buffer:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Batch insert memories
                await conn.executemany("""
                    INSERT INTO agent_memory (
                        id, agent_id, container_instance_id, task_id, session_id,
                        memory_type, content, embedding, code_context, task_context,
                        outcome_context, confidence_score, success_correlation,
                        usage_count, created_at, created_by_container
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """, [
                    (
                        mem['id'], mem['agent_id'], mem['container_instance_id'],
                        mem['task_id'], mem['session_id'], mem['memory_type'],
                        mem['content'], mem['embedding'], mem['code_context'],
                        mem['task_context'], mem['outcome_context'],
                        mem['confidence_score'], mem['success_correlation'],
                        mem['usage_count'], mem['created_at'], mem['created_by_container']
                    ) for mem in self.memory_buffer
                ])
                
                logger.debug(f"Flushed {len(self.memory_buffer)} memories to database")
                self.memory_buffer.clear()
                
        except Exception as e:
            logger.error(f"Error flushing memory buffer: {e}")
    
    async def _update_expertise(self, task_type: str, success: bool, task_result: Dict[str, Any]):
        """Update agent expertise based on task outcome"""
        
        # Map task type to skill area
        skill_area = self._map_task_to_skill(task_type)
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get existing expertise
                expertise = await conn.fetchrow("""
                    SELECT * FROM agent_expertise 
                    WHERE agent_id = $1 AND skill_area = $2
                """, self.agent_id, skill_area)
                
                current_performance = 1.0 if success else 0.0
                
                if expertise:
                    # Update existing expertise
                    new_task_count = expertise['task_count'] + 1
                    new_success_rate = (
                        (expertise['success_rate'] * expertise['task_count'] + current_performance)
                        / new_task_count
                    )
                    
                    # Calculate learning velocity
                    if expertise['last_task_performance'] is not None:
                        performance_delta = current_performance - expertise['last_task_performance']
                        learning_velocity = performance_delta * 0.1 + expertise['learning_velocity'] * 0.9
                    else:
                        learning_velocity = 0.0
                    
                    # Determine trend
                    if learning_velocity > 0.05:
                        trend = PerformanceTrend.IMPROVING
                    elif learning_velocity < -0.05:
                        trend = PerformanceTrend.DECLINING
                    else:
                        trend = PerformanceTrend.STABLE
                    
                    # Calculate new expertise level
                    expertise_delta = 0.1 if success else -0.05
                    new_expertise_level = max(0.0, min(1.0, 
                        expertise['expertise_level'] + expertise_delta * (1.0 / new_task_count)
                    ))
                    
                    await conn.execute("""
                        UPDATE agent_expertise 
                        SET task_count = $3, success_rate = $4, expertise_level = $5,
                            last_task_performance = $6, learning_velocity = $7,
                            performance_trend = $8, updated_at = NOW()
                        WHERE agent_id = $1 AND skill_area = $2
                    """, 
                        self.agent_id, skill_area, new_task_count, new_success_rate,
                        new_expertise_level, current_performance, learning_velocity, trend.value
                    )
                else:
                    # Create new expertise entry
                    initial_expertise = 0.1 if success else 0.05
                    
                    await conn.execute("""
                        INSERT INTO agent_expertise (
                            agent_id, skill_area, expertise_level, task_count,
                            success_rate, last_task_performance, learning_velocity,
                            performance_trend, key_learnings, common_mistakes,
                            successful_approaches
                        ) VALUES ($1, $2, $3, 1, $4, $5, 0.0, 'stable', '{}', '{}', '{}')
                    """, 
                        self.agent_id, skill_area, initial_expertise, 
                        current_performance, current_performance
                    )
                
        except Exception as e:
            logger.error(f"Error updating expertise: {e}")
    
    def _map_task_to_skill(self, task_type: str) -> str:
        """Map task type to skill area"""
        skill_mapping = {
            'python_development': 'python_backend',
            'javascript_development': 'javascript_frontend',
            'react_development': 'react_frontend',
            'api_development': 'api_design',
            'database_design': 'database_design',
            'testing': 'software_testing',
            'debugging': 'debugging',
            'code_review': 'code_review',
            'deployment': 'devops_deployment'
        }
        
        return skill_mapping.get(task_type.lower(), task_type.lower().replace(' ', '_'))
    
    def _row_to_memory(self, row) -> AgentMemory:
        """Convert database row to AgentMemory object"""
        return AgentMemory(
            id=str(row['id']),
            agent_id=str(row['agent_id']),
            container_instance_id=row['container_instance_id'],
            task_id=str(row['task_id']) if row['task_id'] else None,
            session_id=str(row['session_id']) if row['session_id'] else None,
            memory_type=MemoryType(row['memory_type']),
            content=row['content'],
            embedding=row['embedding'] if row['embedding'] else None,
            code_context=json.loads(row['code_context']) if row['code_context'] else {},
            task_context=json.loads(row['task_context']) if row['task_context'] else {},
            outcome_context=json.loads(row['outcome_context']) if row['outcome_context'] else {},
            confidence_score=row['confidence_score'],
            success_correlation=row['success_correlation'],
            usage_count=row['usage_count'],
            last_accessed=row['last_accessed'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    async def _periodic_flush(self):
        """Periodically flush memory buffer"""
        while True:
            try:
                await asyncio.sleep(self.batch_flush_interval)
                await self._flush_memory_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up old memories"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_memories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_old_memories(self):
        """Clean up very old, low-value memories"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_memory_age_days)
            
            async with self.db_pool.acquire() as conn:
                # Delete old, low-confidence, unused memories
                deleted = await conn.fetchval("""
                    DELETE FROM agent_memory 
                    WHERE agent_id = $1 
                        AND created_at < $2 
                        AND confidence_score < 0.3 
                        AND usage_count = 0
                    RETURNING COUNT(*)
                """, self.agent_id, cutoff_date)
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old memories for agent {self.agent_id}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old memories: {e}")