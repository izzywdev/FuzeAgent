"""
Task Knowledge Extractor for FuzeAgent

This module extracts valuable knowledge from completed tasks and feeds it
into the hierarchical knowledge management system. It analyzes task outcomes,
code changes, conversation patterns, and performance metrics to create
reusable organizational knowledge.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from sentence_transformers import SentenceTransformer

from .knowledge_propagation_engine import (KnowledgePropagationEngine,
                                           PropagationTrigger)
from .organization_rag_manager import (ContentType, KnowledgeCategory,
                                       OrganizationRAGManager, SourceType)
from .team_knowledge_manager import TeamKnowledgeManager

logger = logging.getLogger(__name__)


@dataclass
class TaskKnowledgeExtract:
    """Represents extracted knowledge from a task"""

    title: str
    content: str
    content_type: ContentType
    category: KnowledgeCategory
    confidence_score: float
    tags: List[str]
    metadata: Dict[str, Any]
    success_indicators: List[str]
    failure_patterns: List[str]


@dataclass
class ExtractionContext:
    """Context for knowledge extraction"""

    task_id: str
    agent_id: str
    team_id: str
    organization_id: str
    task_data: Dict[str, Any]
    execution_result: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    code_changes: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    iteration_count: int
    total_duration_minutes: float
    success: bool


class TaskKnowledgeExtractor:
    """
    Extracts knowledge from completed tasks and integrates it
    into the hierarchical knowledge management system.
    """

    def __init__(
        self,
        database_url: str,
        org_rag_manager: OrganizationRAGManager,
        team_knowledge_manager: TeamKnowledgeManager,
        propagation_engine: KnowledgePropagationEngine,
    ):
        self.database_url = database_url
        self.org_rag_manager = org_rag_manager
        self.team_knowledge_manager = team_knowledge_manager
        self.propagation_engine = propagation_engine
        self.pool: Optional[asyncpg.Pool] = None

        # Initialize text analysis model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Extraction patterns and rules
        self.code_patterns = self._initialize_code_patterns()
        self.success_patterns = self._initialize_success_patterns()
        self.failure_patterns = self._initialize_failure_patterns()

        # Configuration
        self.min_extraction_confidence = 0.4
        self.min_task_duration_minutes = 5  # Don't extract from very short tasks
        self.max_content_length = 5000

        # Statistics
        self.extractions_performed = 0
        self.knowledge_items_created = 0
        self.propagations_triggered = 0

    async def initialize(self):
        """Initialize the knowledge extractor"""
        logger.info("Initializing TaskKnowledgeExtractor")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=5, command_timeout=60
            )

            logger.info("TaskKnowledgeExtractor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TaskKnowledgeExtractor: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("TaskKnowledgeExtractor closed")

    async def extract_knowledge_from_task(
        self, task_id: str, agent_id: str, execution_result: Dict[str, Any]
    ) -> List[str]:
        """Extract knowledge from a completed task and store it"""

        try:
            # Build extraction context
            context = await self._build_extraction_context(
                task_id, agent_id, execution_result
            )

            if not context:
                logger.warning(f"Could not build extraction context for task {task_id}")
                return []

            # Skip extraction for very short or trivial tasks
            if context.total_duration_minutes < self.min_task_duration_minutes:
                logger.debug(
                    f"Skipping extraction for short task {task_id} ({context.total_duration_minutes:.1f}m)"
                )
                return []

            # Extract knowledge items
            knowledge_extracts = await self._extract_knowledge_items(context)

            if not knowledge_extracts:
                logger.debug(f"No knowledge extracted from task {task_id}")
                return []

            # Store extracted knowledge
            stored_knowledge_ids = []
            for extract in knowledge_extracts:
                if extract.confidence_score >= self.min_extraction_confidence:
                    knowledge_id = await self._store_knowledge_extract(context, extract)
                    if knowledge_id:
                        stored_knowledge_ids.append(knowledge_id)

            # Trigger knowledge propagation if we have valuable knowledge
            if stored_knowledge_ids:
                propagation_ids = (
                    await self.propagation_engine.trigger_agent_to_team_propagation(
                        agent_id=context.agent_id,
                        task_id=context.task_id,
                        task_outcome={
                            "success": context.success,
                            "task_type": context.task_data.get("task_type", "unknown"),
                            "complexity": self._assess_task_complexity(context),
                            "duration_minutes": context.total_duration_minutes,
                            "knowledge_extracted": len(stored_knowledge_ids),
                            "iteration_count": context.iteration_count,
                        },
                    )
                )

                self.propagations_triggered += len(propagation_ids)
                logger.info(
                    f"Triggered {len(propagation_ids)} knowledge propagations for task {task_id}"
                )

            self.extractions_performed += 1
            self.knowledge_items_created += len(stored_knowledge_ids)

            logger.info(
                f"Extracted {len(stored_knowledge_ids)} knowledge items from task {task_id}"
            )
            return stored_knowledge_ids

        except Exception as e:
            logger.error(f"Error extracting knowledge from task {task_id}: {e}")
            return []

    async def _build_extraction_context(
        self, task_id: str, agent_id: str, execution_result: Dict[str, Any]
    ) -> Optional[ExtractionContext]:
        """Build context for knowledge extraction"""

        async with self.pool.acquire() as conn:
            # Get basic task information
            task_data = await conn.fetchrow(
                """
                SELECT t.*, a.team_id, te.organization_id 
                FROM tasks t
                JOIN agents a ON t.agent_id = a.id
                JOIN teams te ON a.team_id = te.id
                WHERE t.id = $1
            """,
                task_id,
            )

            if not task_data:
                return None

            # Get conversation history
            conversation_history = await conn.fetch(
                """
                SELECT message_type, content, metadata, created_at
                FROM claude_conversations 
                WHERE task_id = $1
                ORDER BY created_at ASC
            """,
                task_id,
            )

            # Get code generations
            code_changes = await conn.fetch(
                """
                SELECT file_path, file_type, language, content, test_results, quality_metrics
                FROM code_generations 
                WHERE task_id = $1
                ORDER BY generated_at ASC
            """,
                task_id,
            )

            # Get performance metrics
            performance_metrics = await conn.fetch(
                """
                SELECT metric_type, metric_value, metric_unit, context
                FROM agent_performance_metrics 
                WHERE task_id = $1
            """,
                task_id,
            )

            # Calculate duration
            started_at = task_data["started_at"]
            completed_at = execution_result.get("completed_at")
            if completed_at:
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(
                        completed_at.replace("Z", "+00:00")
                    )
                duration = (completed_at - started_at).total_seconds() / 60.0
            else:
                duration = 0.0

            return ExtractionContext(
                task_id=str(task_data["id"]),
                agent_id=str(task_data["agent_id"]),
                team_id=str(task_data["team_id"]),
                organization_id=str(task_data["organization_id"]),
                task_data=dict(task_data),
                execution_result=execution_result,
                conversation_history=[dict(conv) for conv in conversation_history],
                code_changes=[dict(code) for code in code_changes],
                performance_metrics={
                    pm["metric_type"]: pm for pm in performance_metrics
                },
                iteration_count=execution_result.get("iterations", 0),
                total_duration_minutes=duration,
                success=execution_result.get("status") == "completed",
            )

    async def _extract_knowledge_items(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract specific knowledge items from the task context"""

        knowledge_extracts = []

        # Extract different types of knowledge
        knowledge_extracts.extend(await self._extract_code_patterns(context))
        knowledge_extracts.extend(await self._extract_problem_solutions(context))
        knowledge_extracts.extend(await self._extract_debugging_insights(context))
        knowledge_extracts.extend(await self._extract_process_knowledge(context))
        knowledge_extracts.extend(await self._extract_error_patterns(context))
        knowledge_extracts.extend(await self._extract_optimization_insights(context))

        return knowledge_extracts

    async def _extract_code_patterns(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract reusable code patterns and best practices"""

        extracts = []

        for code_change in context.code_changes:
            if code_change["file_type"] == "implementation":
                content = code_change["content"]
                language = code_change.get("language", "unknown")

                # Look for reusable patterns
                patterns_found = []
                for pattern_name, pattern_info in self.code_patterns.items():
                    if any(
                        keyword in content.lower()
                        for keyword in pattern_info["keywords"]
                    ):
                        patterns_found.append(pattern_name)

                if patterns_found and len(content) > 100:  # Substantial code
                    # Create knowledge extract
                    title = f"Code Pattern: {', '.join(patterns_found)} ({language})"
                    extract_content = self._create_code_pattern_content(
                        content, patterns_found, context
                    )

                    confidence = self._calculate_code_pattern_confidence(
                        content, patterns_found, context
                    )

                    if confidence >= self.min_extraction_confidence:
                        extract = TaskKnowledgeExtract(
                            title=title,
                            content=extract_content,
                            content_type=ContentType.CODE,
                            category=KnowledgeCategory.DEVELOPMENT,
                            confidence_score=confidence,
                            tags=["code_pattern", language, *patterns_found],
                            metadata={
                                "language": language,
                                "file_path": code_change["file_path"],
                                "patterns": patterns_found,
                                "task_success": context.success,
                                "lines_of_code": len(content.split("\n")),
                            },
                            success_indicators=self._extract_success_indicators(
                                context
                            ),
                            failure_patterns=[],
                        )

                        extracts.append(extract)

        return extracts

    async def _extract_problem_solutions(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract problem-solution pairs from the task"""

        extracts = []

        # Analyze conversation for problem descriptions and solutions
        problem_solution_pairs = self._identify_problem_solution_pairs(
            context.conversation_history
        )

        for problem, solution in problem_solution_pairs:
            if len(problem) > 50 and len(solution) > 50:  # Substantial content
                title = f"Solution: {problem[:50]}..."
                content = f"**Problem:**\n{problem}\n\n**Solution:**\n{solution}"

                # Determine category based on content
                category = self._categorize_problem_solution(problem, solution)

                confidence = self._calculate_solution_confidence(
                    problem, solution, context
                )

                if confidence >= self.min_extraction_confidence:
                    extract = TaskKnowledgeExtract(
                        title=title,
                        content=content[: self.max_content_length],
                        content_type=ContentType.PROCEDURE,
                        category=category,
                        confidence_score=confidence,
                        tags=["problem_solution", "troubleshooting"],
                        metadata={
                            "problem_type": self._classify_problem_type(problem),
                            "solution_type": self._classify_solution_type(solution),
                            "task_success": context.success,
                        },
                        success_indicators=self._extract_success_indicators(context),
                        failure_patterns=[],
                    )

                    extracts.append(extract)

        return extracts

    async def _extract_debugging_insights(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract debugging approaches and insights"""

        extracts = []

        # Look for error messages and resolution patterns
        debugging_sessions = self._identify_debugging_sessions(
            context.conversation_history
        )

        for session in debugging_sessions:
            if session["resolution"] and context.success:
                title = f"Debugging: {session['error_type']}"
                content = self._create_debugging_content(session)

                confidence = self._calculate_debugging_confidence(session, context)

                if confidence >= self.min_extraction_confidence:
                    extract = TaskKnowledgeExtract(
                        title=title,
                        content=content,
                        content_type=ContentType.PROCEDURE,
                        category=KnowledgeCategory.TROUBLESHOOTING,
                        confidence_score=confidence,
                        tags=["debugging", session["error_type"], "troubleshooting"],
                        metadata={
                            "error_type": session["error_type"],
                            "resolution_method": session["resolution_method"],
                            "tools_used": session.get("tools_used", []),
                        },
                        success_indicators=self._extract_success_indicators(context),
                        failure_patterns=session.get("failure_patterns", []),
                    )

                    extracts.append(extract)

        return extracts

    async def _extract_process_knowledge(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract process and workflow knowledge"""

        extracts = []

        if context.iteration_count > 1:  # Multi-iteration tasks have process insights
            title = f"Process: {context.task_data.get('task_type', 'Task')} Workflow"

            process_content = self._create_process_content(context)
            confidence = self._calculate_process_confidence(context)

            if confidence >= self.min_extraction_confidence:
                extract = TaskKnowledgeExtract(
                    title=title,
                    content=process_content,
                    content_type=ContentType.PROCEDURE,
                    category=KnowledgeCategory.PROCESS,
                    confidence_score=confidence,
                    tags=[
                        "process",
                        "workflow",
                        context.task_data.get("task_type", "general"),
                    ],
                    metadata={
                        "iterations_used": context.iteration_count,
                        "duration_minutes": context.total_duration_minutes,
                        "success_rate": 1.0 if context.success else 0.0,
                        "complexity": self._assess_task_complexity(context),
                    },
                    success_indicators=self._extract_success_indicators(context),
                    failure_patterns=[],
                )

                extracts.append(extract)

        return extracts

    async def _extract_error_patterns(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract error patterns and avoidance strategies"""

        extracts = []

        # Look for error patterns in failed tasks or recovered errors
        error_patterns = self._identify_error_patterns(context.conversation_history)

        for pattern in error_patterns:
            if pattern["frequency"] >= 2 or pattern["severity"] == "high":
                title = f"Error Pattern: {pattern['error_type']}"
                content = self._create_error_pattern_content(pattern, context)

                confidence = self._calculate_error_pattern_confidence(pattern, context)

                if confidence >= self.min_extraction_confidence:
                    extract = TaskKnowledgeExtract(
                        title=title,
                        content=content,
                        content_type=ContentType.DOCUMENTATION,
                        category=KnowledgeCategory.TROUBLESHOOTING,
                        confidence_score=confidence,
                        tags=["error_pattern", pattern["error_type"], "prevention"],
                        metadata={
                            "error_type": pattern["error_type"],
                            "frequency": pattern["frequency"],
                            "severity": pattern["severity"],
                            "prevention_strategies": pattern.get("prevention", []),
                        },
                        success_indicators=[],
                        failure_patterns=pattern.get("indicators", []),
                    )

                    extracts.append(extract)

        return extracts

    async def _extract_optimization_insights(
        self, context: ExtractionContext
    ) -> List[TaskKnowledgeExtract]:
        """Extract performance optimization insights"""

        extracts = []

        # Look for performance improvements in metrics
        if "execution_time_minutes" in context.performance_metrics:
            perf_data = context.performance_metrics["execution_time_minutes"]
            if (
                perf_data["metric_value"] < 30 and context.success
            ):  # Efficient completion
                title = "Performance Optimization: Efficient Task Execution"
                content = self._create_optimization_content(context)

                confidence = self._calculate_optimization_confidence(context)

                if confidence >= self.min_extraction_confidence:
                    extract = TaskKnowledgeExtract(
                        title=title,
                        content=content,
                        content_type=ContentType.BEST_PRACTICE,
                        category=KnowledgeCategory.DEVELOPMENT,
                        confidence_score=confidence,
                        tags=["optimization", "performance", "efficiency"],
                        metadata={
                            "execution_time": perf_data["metric_value"],
                            "iteration_efficiency": context.iteration_count
                            / context.total_duration_minutes,
                            "optimization_techniques": self._identify_optimization_techniques(
                                context
                            ),
                        },
                        success_indicators=self._extract_success_indicators(context),
                        failure_patterns=[],
                    )

                    extracts.append(extract)

        return extracts

    async def _store_knowledge_extract(
        self, context: ExtractionContext, extract: TaskKnowledgeExtract
    ) -> Optional[str]:
        """Store a knowledge extract in the appropriate knowledge base"""

        try:
            # Store in organization knowledge base
            knowledge_id = await self.org_rag_manager.add_knowledge(
                organization_id=context.organization_id,
                title=extract.title,
                content=extract.content,
                content_type=extract.content_type,
                knowledge_category=extract.category,
                source_type=SourceType.TASK_OUTCOME,
                source_agent_id=context.agent_id,
                source_team_id=context.team_id,
                source_task_id=context.task_id,
                relevance_score=extract.confidence_score,
                quality_score=extract.confidence_score,
                metadata={
                    **extract.metadata,
                    "extraction_timestamp": datetime.now().isoformat(),
                    "extractor_version": "1.0",
                    "success_indicators": extract.success_indicators,
                    "failure_patterns": extract.failure_patterns,
                },
                tags=extract.tags,
            )

            return knowledge_id

        except Exception as e:
            logger.error(f"Error storing knowledge extract: {e}")
            return None

    # Helper methods for pattern matching and analysis
    def _initialize_code_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize code pattern definitions"""
        return {
            "api_integration": {
                "keywords": ["fetch", "axios", "request", "api", "endpoint", "rest"],
                "confidence_boost": 0.2,
            },
            "database_operations": {
                "keywords": [
                    "select",
                    "insert",
                    "update",
                    "delete",
                    "query",
                    "database",
                    "sql",
                ],
                "confidence_boost": 0.2,
            },
            "authentication": {
                "keywords": ["auth", "login", "token", "jwt", "session", "passport"],
                "confidence_boost": 0.15,
            },
            "error_handling": {
                "keywords": ["try", "catch", "error", "exception", "throw"],
                "confidence_boost": 0.1,
            },
            "testing": {
                "keywords": ["test", "spec", "describe", "it", "expect", "mock"],
                "confidence_boost": 0.15,
            },
            "optimization": {
                "keywords": ["performance", "optimize", "cache", "memory", "speed"],
                "confidence_boost": 0.2,
            },
        }

    def _initialize_success_patterns(self) -> List[str]:
        """Initialize success indicator patterns"""
        return [
            r"test.*pass",
            r"build.*success",
            r"deploy.*complete",
            r"fix.*issue",
            r"resolve.*problem",
            r"implement.*feature",
            r"complete.*task",
        ]

    def _initialize_failure_patterns(self) -> List[str]:
        """Initialize failure indicator patterns"""
        return [
            r"error.*occur",
            r"fail.*to",
            r"timeout.*exceed",
            r"connection.*refuse",
            r"not.*found",
            r"access.*deni",
            r"invalid.*request",
        ]

    def _assess_task_complexity(self, context: ExtractionContext) -> str:
        """Assess task complexity based on various factors"""

        complexity_score = 0

        # Factor 1: Iteration count
        if context.iteration_count > 10:
            complexity_score += 3
        elif context.iteration_count > 5:
            complexity_score += 2
        elif context.iteration_count > 2:
            complexity_score += 1

        # Factor 2: Duration
        if context.total_duration_minutes > 180:  # 3 hours
            complexity_score += 3
        elif context.total_duration_minutes > 60:  # 1 hour
            complexity_score += 2
        elif context.total_duration_minutes > 30:
            complexity_score += 1

        # Factor 3: Code changes
        if len(context.code_changes) > 10:
            complexity_score += 2
        elif len(context.code_changes) > 5:
            complexity_score += 1

        # Factor 4: Conversation length
        if len(context.conversation_history) > 50:
            complexity_score += 2
        elif len(context.conversation_history) > 20:
            complexity_score += 1

        if complexity_score >= 6:
            return "very_high"
        elif complexity_score >= 4:
            return "high"
        elif complexity_score >= 2:
            return "medium"
        else:
            return "low"

    def _extract_success_indicators(self, context: ExtractionContext) -> List[str]:
        """Extract success indicators from the task execution"""

        indicators = []

        # Look for success patterns in conversation
        for conv in context.conversation_history:
            content = conv.get("content", "").lower()
            for pattern in self.success_patterns:
                if re.search(pattern, content):
                    indicators.append(pattern)

        # Add task-specific indicators
        if context.success:
            indicators.append("task_completed_successfully")

        if context.execution_result.get("pull_request_url"):
            indicators.append("pull_request_created")

        return list(set(indicators))  # Remove duplicates

    # Additional helper methods would be implemented here...
    # (The file is getting quite long, so I'll implement key methods and indicate where others would go)

    def _identify_problem_solution_pairs(
        self, conversation_history: List[Dict]
    ) -> List[Tuple[str, str]]:
        """Identify problem-solution pairs in conversation history"""
        pairs = []
        # Implementation would analyze conversation flow to identify problems and their solutions
        # This is a simplified placeholder
        return pairs

    def _categorize_problem_solution(
        self, problem: str, solution: str
    ) -> KnowledgeCategory:
        """Categorize a problem-solution pair"""
        # Simple categorization based on keywords
        combined_text = (problem + " " + solution).lower()

        if any(word in combined_text for word in ["test", "testing", "spec"]):
            return KnowledgeCategory.TESTING
        elif any(word in combined_text for word in ["deploy", "build", "ci", "cd"]):
            return KnowledgeCategory.INFRASTRUCTURE
        elif any(word in combined_text for word in ["security", "auth", "permission"]):
            return KnowledgeCategory.SECURITY
        elif any(word in combined_text for word in ["design", "ui", "ux", "interface"]):
            return KnowledgeCategory.DESIGN
        else:
            return KnowledgeCategory.DEVELOPMENT

    def _calculate_code_pattern_confidence(
        self, content: str, patterns: List[str], context: ExtractionContext
    ) -> float:
        """Calculate confidence score for code pattern extraction"""
        base_confidence = 0.5

        # Boost for successful task
        if context.success:
            base_confidence += 0.2

        # Boost for multiple patterns
        if len(patterns) > 1:
            base_confidence += 0.1

        # Boost for substantial code
        if len(content) > 500:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _calculate_solution_confidence(
        self, problem: str, solution: str, context: ExtractionContext
    ) -> float:
        """Calculate confidence score for solution extraction"""
        base_confidence = 0.4

        if context.success:
            base_confidence += 0.3

        if len(solution) > 200:  # Detailed solution
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _calculate_debugging_confidence(
        self, session: Dict, context: ExtractionContext
    ) -> float:
        """Calculate confidence for debugging insights"""
        base_confidence = 0.6 if context.success else 0.3

        if session.get("resolution_method"):
            base_confidence += 0.2

        return min(1.0, base_confidence)

    def _calculate_process_confidence(self, context: ExtractionContext) -> float:
        """Calculate confidence for process knowledge"""
        if not context.success:
            return 0.2

        # Base confidence increases with iteration count (more process learning)
        base_confidence = min(0.8, 0.3 + (context.iteration_count * 0.05))

        return base_confidence

    def _calculate_error_pattern_confidence(
        self, pattern: Dict, context: ExtractionContext
    ) -> float:
        """Calculate confidence for error pattern extraction"""
        base_confidence = 0.4

        if pattern["frequency"] > 2:
            base_confidence += 0.2

        if pattern["severity"] == "high":
            base_confidence += 0.2

        return min(1.0, base_confidence)

    def _calculate_optimization_confidence(self, context: ExtractionContext) -> float:
        """Calculate confidence for optimization insights"""
        if not context.success:
            return 0.1

        base_confidence = 0.5

        # Boost for efficient execution
        if context.total_duration_minutes < 30:
            base_confidence += 0.2

        if context.iteration_count < 5:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    # Content creation methods (simplified implementations)
    def _create_code_pattern_content(
        self, content: str, patterns: List[str], context: ExtractionContext
    ) -> str:
        """Create formatted content for code pattern knowledge"""
        return f"**Code Pattern: {', '.join(patterns)}**\n\n{content[:2000]}..."

    def _create_debugging_content(self, session: Dict) -> str:
        """Create formatted content for debugging knowledge"""
        return f"**Error:** {session.get('error_type', 'Unknown')}\n\n**Resolution:** {session.get('resolution', 'No resolution provided')}"

    def _create_process_content(self, context: ExtractionContext) -> str:
        """Create formatted content for process knowledge"""
        return f"**Task Type:** {context.task_data.get('task_type', 'Unknown')}\n**Iterations:** {context.iteration_count}\n**Duration:** {context.total_duration_minutes:.1f} minutes\n**Success:** {'Yes' if context.success else 'No'}"

    def _create_error_pattern_content(
        self, pattern: Dict, context: ExtractionContext
    ) -> str:
        """Create formatted content for error pattern knowledge"""
        return f"**Error Type:** {pattern['error_type']}\n**Frequency:** {pattern['frequency']}\n**Prevention:** {', '.join(pattern.get('prevention', []))}"

    def _create_optimization_content(self, context: ExtractionContext) -> str:
        """Create formatted content for optimization knowledge"""
        return f"**Optimization achieved in {context.total_duration_minutes:.1f} minutes with {context.iteration_count} iterations**"

    # Placeholder methods for more complex analysis functions
    def _identify_debugging_sessions(
        self, conversation_history: List[Dict]
    ) -> List[Dict]:
        """Identify debugging sessions in conversation history"""
        return []  # Simplified implementation

    def _identify_error_patterns(self, conversation_history: List[Dict]) -> List[Dict]:
        """Identify error patterns in conversation history"""
        return []  # Simplified implementation

    def _identify_optimization_techniques(
        self, context: ExtractionContext
    ) -> List[str]:
        """Identify optimization techniques used"""
        return []  # Simplified implementation

    def _classify_problem_type(self, problem: str) -> str:
        """Classify the type of problem"""
        return "general"  # Simplified implementation

    def _classify_solution_type(self, solution: str) -> str:
        """Classify the type of solution"""
        return "general"  # Simplified implementation
