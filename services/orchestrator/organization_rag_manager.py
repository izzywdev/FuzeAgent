"""
Organization RAG Manager for FuzeAgent

This module provides centralized knowledge management at the organization level,
with semantic search, knowledge aggregation, and cross-team knowledge sharing.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

import asyncpg
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class KnowledgeCategory(str, Enum):
    DEVELOPMENT = "development"
    INFRASTRUCTURE = "infrastructure" 
    BUSINESS = "business"
    SECURITY = "security"
    DESIGN = "design"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PROCESS = "process"
    TROUBLESHOOTING = "troubleshooting"

class ContentType(str, Enum):
    TEXT = "text"
    CODE = "code"
    DOCUMENTATION = "documentation"
    PROCEDURE = "procedure"
    BEST_PRACTICE = "best_practice"

class SourceType(str, Enum):
    AGENT_CONTRIBUTION = "agent_contribution"
    TEAM_AGGREGATION = "team_aggregation"
    MANUAL_ENTRY = "manual_entry"
    TASK_OUTCOME = "task_outcome"
    EXTERNAL_IMPORT = "external_import"

class VisibilityLevel(str, Enum):
    ORGANIZATION = "organization"
    TEAM = "team"
    AGENT = "agent"
    PUBLIC = "public"

@dataclass
class OrganizationKnowledge:
    """Represents a piece of organization-level knowledge"""
    id: str
    organization_id: str
    title: str
    content: str
    content_type: ContentType
    knowledge_category: KnowledgeCategory
    embedding: Optional[List[float]]
    source_type: SourceType
    source_agent_id: Optional[str]
    source_team_id: Optional[str]
    source_task_id: Optional[str]
    source_reference: Optional[str]
    relevance_score: float
    quality_score: float
    usage_count: int
    success_correlation: float
    visibility_level: VisibilityLevel
    access_teams: List[str]
    access_agents: List[str]
    metadata: Dict[str, Any]
    tags: List[str]
    related_knowledge_ids: List[str]
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]

@dataclass
class KnowledgeSearchResult:
    """Result of a knowledge search query"""
    knowledge: OrganizationKnowledge
    similarity_score: float
    relevance_score: float
    combined_score: float

class OrganizationRAGManager:
    """
    Manages organization-level knowledge base with semantic search,
    knowledge aggregation, and intelligent knowledge distribution.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384
        
        # Configuration
        self.default_relevance_score = 0.5
        self.min_similarity_threshold = 0.3
        self.max_knowledge_per_query = 50
        self.knowledge_freshness_days = 90
        
        # Statistics
        self.queries_processed = 0
        self.knowledge_added = 0
        self.propagations_processed = 0
    
    async def initialize(self):
        """Initialize the organization RAG manager"""
        logger.info("Initializing OrganizationRAGManager")
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=15,
                command_timeout=60
            )
            
            # Verify database schema
            await self._verify_schema()
            
            logger.info("OrganizationRAGManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OrganizationRAGManager: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("OrganizationRAGManager closed")
    
    async def add_knowledge(
        self,
        organization_id: str,
        title: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        knowledge_category: KnowledgeCategory = KnowledgeCategory.DEVELOPMENT,
        source_type: SourceType = SourceType.MANUAL_ENTRY,
        source_agent_id: Optional[str] = None,
        source_team_id: Optional[str] = None,
        source_task_id: Optional[str] = None,
        source_reference: Optional[str] = None,
        relevance_score: float = 0.5,
        quality_score: float = 0.5,
        visibility_level: VisibilityLevel = VisibilityLevel.ORGANIZATION,
        access_teams: Optional[List[str]] = None,
        access_agents: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Add knowledge to organization knowledge base"""
        
        knowledge_id = str(uuid.uuid4())
        embedding = self._generate_embedding(content)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO organization_knowledge_base (
                    id, organization_id, title, content, content_type, knowledge_category,
                    embedding, source_type, source_agent_id, source_team_id, source_task_id,
                    source_reference, relevance_score, quality_score, visibility_level,
                    access_teams, access_agents, metadata, tags, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """, 
                knowledge_id, organization_id, title, content, content_type.value, 
                knowledge_category.value, embedding, source_type.value, source_agent_id,
                source_team_id, source_task_id, source_reference, relevance_score,
                quality_score, visibility_level.value, access_teams or [], 
                access_agents or [], json.dumps(metadata or {}), tags or [], expires_at
            )
        
        self.knowledge_added += 1
        
        # Log the knowledge creation
        await self._log_knowledge_activity(
            organization_id, knowledge_id, 'knowledge_created',
            {'source_type': source_type.value, 'category': knowledge_category.value}
        )
        
        logger.info(f"Added knowledge {knowledge_id} to organization {organization_id}")
        return knowledge_id
    
    async def search_knowledge(
        self,
        organization_id: str,
        query: str,
        categories: Optional[List[KnowledgeCategory]] = None,
        content_types: Optional[List[ContentType]] = None,
        limit: int = 10,
        min_similarity: float = 0.3,
        include_team_knowledge: bool = True,
        requester_agent_id: Optional[str] = None,
        requester_team_id: Optional[str] = None
    ) -> List[KnowledgeSearchResult]:
        """Search organization knowledge using semantic similarity"""
        
        self.queries_processed += 1
        query_embedding = self._generate_embedding(query)
        
        async with self.pool.acquire() as conn:
            # Build filter conditions
            where_conditions = ["organization_id = $2"]
            params = [query_embedding, organization_id]
            param_idx = 3
            
            if categories:
                where_conditions.append(f"knowledge_category = ANY(${param_idx})")
                params.append([cat.value for cat in categories])
                param_idx += 1
            
            if content_types:
                where_conditions.append(f"content_type = ANY(${param_idx})")
                params.append([ct.value for ct in content_types])
                param_idx += 1
            
            # Add access control
            if requester_team_id or requester_agent_id:
                access_condition = f"""
                (visibility_level = 'organization' OR 
                 (visibility_level = 'team' AND ${param_idx} = ANY(access_teams)) OR
                 (visibility_level = 'agent' AND ${param_idx + 1} = ANY(access_agents)))
                """
                where_conditions.append(access_condition)
                params.extend([requester_team_id or '', requester_agent_id or ''])
                param_idx += 2
            
            # Add similarity threshold
            where_conditions.append(f"(1 - (embedding <=> $1)) >= ${param_idx}")
            params.append(min_similarity)
            param_idx += 1
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Execute search
            knowledge_results = await conn.fetch(f"""
                SELECT * FROM search_organization_knowledge(
                    $2, $1, null, ${param_idx}, ${param_idx}
                )
            """, *params, limit, min_similarity)
            
            # Convert to result objects
            results = []
            for row in knowledge_results:
                # Get full knowledge record
                full_knowledge = await conn.fetchrow("""
                    SELECT * FROM organization_knowledge_base WHERE id = $1
                """, row['knowledge_id'])
                
                if full_knowledge:
                    knowledge = self._row_to_knowledge(full_knowledge)
                    combined_score = (row['similarity_score'] * 0.7 + 
                                    row['relevance_score'] * 0.3)
                    
                    results.append(KnowledgeSearchResult(
                        knowledge=knowledge,
                        similarity_score=float(row['similarity_score']),
                        relevance_score=float(row['relevance_score']),
                        combined_score=combined_score
                    ))
            
            # Update usage statistics
            if results:
                knowledge_ids = [r.knowledge.id for r in results]
                await conn.execute("""
                    UPDATE organization_knowledge_base 
                    SET usage_count = usage_count + 1, last_accessed = NOW()
                    WHERE id = ANY($1)
                """, knowledge_ids)
        
        # Sort by combined score
        results.sort(key=lambda x: x.combined_score, reverse=True)
        
        logger.debug(f"Found {len(results)} knowledge items for query: {query[:50]}...")
        return results
    
    async def get_knowledge_by_id(
        self,
        knowledge_id: str,
        requester_agent_id: Optional[str] = None,
        requester_team_id: Optional[str] = None
    ) -> Optional[OrganizationKnowledge]:
        """Get specific knowledge by ID with access control"""
        
        async with self.pool.acquire() as conn:
            knowledge_row = await conn.fetchrow("""
                SELECT * FROM organization_knowledge_base WHERE id = $1
            """, knowledge_id)
            
            if not knowledge_row:
                return None
            
            knowledge = self._row_to_knowledge(knowledge_row)
            
            # Check access permissions
            if not self._check_access_permissions(knowledge, requester_agent_id, requester_team_id):
                return None
            
            # Update access statistics
            await conn.execute("""
                UPDATE organization_knowledge_base 
                SET usage_count = usage_count + 1, last_accessed = NOW()
                WHERE id = $1
            """, knowledge_id)
            
            return knowledge
    
    async def update_knowledge_quality(
        self,
        knowledge_id: str,
        quality_score: Optional[float] = None,
        relevance_score: Optional[float] = None,
        success_correlation: Optional[float] = None,
        feedback_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update knowledge quality metrics based on usage feedback"""
        
        updates = []
        params = []
        param_idx = 1
        
        if quality_score is not None:
            updates.append(f"quality_score = ${param_idx}")
            params.append(max(0.0, min(1.0, quality_score)))
            param_idx += 1
        
        if relevance_score is not None:
            updates.append(f"relevance_score = ${param_idx}")
            params.append(max(0.0, min(1.0, relevance_score)))
            param_idx += 1
        
        if success_correlation is not None:
            updates.append(f"success_correlation = ${param_idx}")
            params.append(max(-1.0, min(1.0, success_correlation)))
            param_idx += 1
        
        if feedback_metadata:
            updates.append(f"metadata = metadata || ${param_idx}")
            params.append(json.dumps(feedback_metadata))
            param_idx += 1
        
        if not updates:
            return False
        
        updates.append("updated_at = NOW()")
        params.append(knowledge_id)
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(f"""
                UPDATE organization_knowledge_base 
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
            """, *params)
            
            return result == "UPDATE 1"
    
    async def get_organization_knowledge_stats(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive knowledge statistics for an organization"""
        
        async with self.pool.acquire() as conn:
            # Basic counts
            basic_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_knowledge,
                    COUNT(DISTINCT knowledge_category) as categories,
                    COUNT(DISTINCT source_agent_id) as contributing_agents,
                    COUNT(DISTINCT source_team_id) as contributing_teams,
                    AVG(relevance_score) as avg_relevance,
                    AVG(quality_score) as avg_quality,
                    SUM(usage_count) as total_usage
                FROM organization_knowledge_base 
                WHERE organization_id = $1
            """, organization_id)
            
            # Category breakdown
            category_stats = await conn.fetch("""
                SELECT 
                    knowledge_category,
                    COUNT(*) as count,
                    AVG(relevance_score) as avg_relevance,
                    SUM(usage_count) as usage_count
                FROM organization_knowledge_base 
                WHERE organization_id = $1
                GROUP BY knowledge_category
                ORDER BY count DESC
            """, organization_id)
            
            # Recent activity
            recent_activity = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as knowledge_added
                FROM organization_knowledge_base 
                WHERE organization_id = $1 
                  AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, organization_id)
            
            # Top contributors
            top_contributors = await conn.fetch("""
                SELECT 
                    COALESCE(a.name, 'Unknown') as agent_name,
                    COUNT(*) as contributions,
                    AVG(okb.quality_score) as avg_quality
                FROM organization_knowledge_base okb
                LEFT JOIN agents a ON okb.source_agent_id = a.id
                WHERE okb.organization_id = $1 
                  AND okb.source_agent_id IS NOT NULL
                GROUP BY okb.source_agent_id, a.name
                ORDER BY contributions DESC
                LIMIT 10
            """, organization_id)
            
            return {
                'organization_id': organization_id,
                'basic_stats': dict(basic_stats) if basic_stats else {},
                'category_breakdown': [dict(cat) for cat in category_stats],
                'recent_activity': [dict(activity) for activity in recent_activity],
                'top_contributors': [dict(contrib) for contrib in top_contributors],
                'generated_at': datetime.now().isoformat()
            }
    
    async def cleanup_expired_knowledge(self, organization_id: str) -> int:
        """Clean up expired knowledge items"""
        
        async with self.pool.acquire() as conn:
            deleted_count = await conn.fetchval("""
                DELETE FROM organization_knowledge_base 
                WHERE organization_id = $1 
                  AND expires_at IS NOT NULL 
                  AND expires_at < NOW()
                RETURNING COUNT(*)
            """, organization_id)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired knowledge items for org {organization_id}")
                
                # Log cleanup activity
                await self._log_knowledge_activity(
                    organization_id, None, 'knowledge_cleanup',
                    {'expired_count': deleted_count}
                )
            
            return deleted_count or 0
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformers"""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.embedding_dim
    
    def _row_to_knowledge(self, row) -> OrganizationKnowledge:
        """Convert database row to OrganizationKnowledge object"""
        return OrganizationKnowledge(
            id=str(row['id']),
            organization_id=str(row['organization_id']),
            title=row['title'],
            content=row['content'],
            content_type=ContentType(row['content_type']),
            knowledge_category=KnowledgeCategory(row['knowledge_category']),
            embedding=row['embedding'] if row['embedding'] else None,
            source_type=SourceType(row['source_type']),
            source_agent_id=str(row['source_agent_id']) if row['source_agent_id'] else None,
            source_team_id=str(row['source_team_id']) if row['source_team_id'] else None,
            source_task_id=str(row['source_task_id']) if row['source_task_id'] else None,
            source_reference=row['source_reference'],
            relevance_score=row['relevance_score'],
            quality_score=row['quality_score'],
            usage_count=row['usage_count'],
            success_correlation=row['success_correlation'],
            visibility_level=VisibilityLevel(row['visibility_level']),
            access_teams=row['access_teams'] or [],
            access_agents=row['access_agents'] or [],
            metadata=json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata'],
            tags=row['tags'] or [],
            related_knowledge_ids=row['related_knowledge_ids'] or [],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_accessed=row['last_accessed'],
            expires_at=row['expires_at']
        )
    
    def _check_access_permissions(
        self, 
        knowledge: OrganizationKnowledge,
        requester_agent_id: Optional[str],
        requester_team_id: Optional[str]
    ) -> bool:
        """Check if requester has access to knowledge"""
        
        if knowledge.visibility_level == VisibilityLevel.ORGANIZATION:
            return True
        elif knowledge.visibility_level == VisibilityLevel.PUBLIC:
            return True
        elif knowledge.visibility_level == VisibilityLevel.TEAM:
            return requester_team_id in knowledge.access_teams if requester_team_id else False
        elif knowledge.visibility_level == VisibilityLevel.AGENT:
            return requester_agent_id in knowledge.access_agents if requester_agent_id else False
        
        return False
    
    async def _verify_schema(self):
        """Verify that required database schema exists"""
        async with self.pool.acquire() as conn:
            tables = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'organization_knowledge_base'
            """)
            
            if tables == 0:
                raise Exception("organization_knowledge_base table not found. Run migrations first.")
    
    async def _log_knowledge_activity(
        self,
        organization_id: str,
        knowledge_id: Optional[str],
        activity_type: str,
        metadata: Dict[str, Any]
    ):
        """Log knowledge-related activities for analytics"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO knowledge_analytics (
                        organization_id, metric_type, metric_name, metric_value,
                        metadata, measured_at
                    ) VALUES ($1, 'activity', $2, 1, $3, NOW())
                """, 
                    organization_id, activity_type, 
                    json.dumps({**metadata, 'knowledge_id': knowledge_id})
                )
        except Exception as e:
            logger.error(f"Failed to log knowledge activity: {e}")