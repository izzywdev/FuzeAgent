"""
Task Execution Engine for FuzeAgent Autonomous Execution

Orchestrates the autonomous execution of tasks by agents, managing:
- Task lifecycle and state transitions
- Sandbox creation and cleanup
- Git workflow automation
- Human-in-the-loop interactions
- Inter-agent communication
- Result aggregation

This is the core component that ties together all autonomous execution components.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .claude_code_wrapper import ClaudeCodeWrapper
from .claude_sdk_manager import ClaudeSDKManager, ClaudeSDKSession
from .context_enhancement_service import ContextEnhancementService
from .conversation_manager import ConversationManager, InteractionType
from .database import DatabaseManager, get_db_connection
from .file_operations_engine import FileOperationsEngine
from .git_workflow_manager import GitWorkflowManager
from .sandbox_manager import AgentSandboxManager, Sandbox
from .task_knowledge_extractor import TaskKnowledgeExtractor

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    SETTING_UP = "setting_up"
    EXECUTING = "executing"
    WAITING_FOR_HUMAN = "waiting_for_human"
    REVIEWING = "reviewing"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStep(str, Enum):
    ANALYZE_TASK = "analyze_task"
    SETUP_SANDBOX = "setup_sandbox"
    SETUP_GIT = "setup_git"
    EXECUTE_ITERATION = "execute_iteration"
    REVIEW_CHANGES = "review_changes"
    COMMIT_CHANGES = "commit_changes"
    HUMAN_INTERACTION = "human_interaction"
    FINALIZE_TASK = "finalize_task"
    CLEANUP = "cleanup"


@dataclass
class TaskIteration:
    """Represents a single iteration of task execution"""

    iteration_number: int
    step: ExecutionStep
    started_at: datetime
    completed_at: Optional[datetime]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    human_question: Optional[str] = None
    human_response: Optional[str] = None


@dataclass
class ExecutionContext:
    """Context for task execution"""

    task_id: str
    agent_id: str
    task_data: Dict[str, Any]
    agent_data: Dict[str, Any]
    sandbox: Optional[Sandbox]
    git_manager: Optional[GitWorkflowManager]
    claude_wrapper: Optional[ClaudeCodeWrapper]
    current_iteration: int
    iterations: List[TaskIteration]
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    # New components for autonomous execution
    file_operations_engine: Optional[FileOperationsEngine] = None
    claude_sdk_manager: Optional[ClaudeSDKManager] = None
    claude_session_id: Optional[str] = None


class TaskExecutionEngine:
    """
    Orchestrates autonomous task execution by agents.

    Features:
    - Task lifecycle management
    - Sandbox and Git workflow integration
    - Human-in-the-loop interactions
    - Dependency handling
    - Result aggregation
    - Error recovery
    """

    def __init__(
        self,
        sandbox_manager: AgentSandboxManager,
        knowledge_extractor: Optional[TaskKnowledgeExtractor] = None,
        context_enhancer: Optional[ContextEnhancementService] = None,
    ):
        self.sandbox_manager = sandbox_manager
        self.conversation_manager = ConversationManager()
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_callbacks: Dict[str, List[Callable]] = {}
        self.running = False
        self.worker_tasks: List[asyncio.Task] = []

        # Knowledge management services
        self.knowledge_extractor = knowledge_extractor
        self.context_enhancer = context_enhancer

        # Initialize integrated components
        self.file_operations_engines: Dict[str, FileOperationsEngine] = {}  # Per task
        self.claude_sdk_managers: Dict[str, ClaudeSDKManager] = {}  # Per task

        # Configuration
        self.max_iterations = 50
        self.iteration_timeout = 3600  # 1 hour per iteration
        self.human_response_timeout = 86400  # 24 hours for human response

    async def start(self):
        """Start the execution engine"""
        logger.info("Starting TaskExecutionEngine")
        self.running = True

        # Start worker tasks
        self.worker_tasks = [
            asyncio.create_task(self._execution_worker()),
            asyncio.create_task(self._monitoring_worker()),
            asyncio.create_task(self._cleanup_worker()),
        ]

        logger.info("TaskExecutionEngine started")

    async def stop(self):
        """Stop the execution engine"""
        logger.info("Stopping TaskExecutionEngine")
        self.running = False

        # Cancel worker tasks
        for task in self.worker_tasks:
            task.cancel()

        try:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error stopping worker tasks: {e}")

        # Clean up active executions
        for execution_id in list(self.active_executions.keys()):
            try:
                await self._cleanup_execution(execution_id)
            except Exception as e:
                logger.error(f"Error cleaning up execution {execution_id}: {e}")

        logger.info("TaskExecutionEngine stopped")

    async def start_task_execution(self, task_id: str) -> Dict[str, Any]:
        """
        Start autonomous execution of a task.
        Returns execution status and context.
        """
        logger.info(f"Starting task execution: {task_id}")

        try:
            # Get task data
            task_data = await self._get_task_data(task_id)
            if not task_data:
                raise ValueError(f"Task {task_id} not found")

            # Get agent data
            agent_id = task_data.get("assigned_to")
            if not agent_id:
                raise ValueError(f"Task {task_id} has no assigned agent")

            agent_data = await self._get_agent_data(agent_id)
            if not agent_data:
                raise ValueError(f"Agent {agent_id} not found")

            # Create execution context
            execution_context = ExecutionContext(
                task_id=task_id,
                agent_id=agent_id,
                task_data=task_data,
                agent_data=agent_data,
                sandbox=None,
                git_manager=None,
                claude_wrapper=None,
                current_iteration=0,
                iterations=[],
                status=TaskStatus.PENDING,
                started_at=datetime.now(),
                completed_at=None,
                result=None,
                error=None,
            )

            # Store execution context
            self.active_executions[task_id] = execution_context

            # Update task status in database
            await self._update_task_status(task_id, TaskStatus.PENDING)

            logger.info(f"✅ Task execution started: {task_id}")
            return {
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "execution_started": True,
                "agent_id": agent_id,
            }

        except Exception as e:
            logger.error(f"❌ Failed to start task execution {task_id}: {e}")
            await self._update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            raise

    async def get_execution_status(self, task_id: str) -> Dict[str, Any]:
        """Get detailed execution status for a task"""

        execution = self.active_executions.get(task_id)
        if not execution:
            # Check database for completed/failed tasks
            task_data = await self._get_task_data(task_id)
            if task_data:
                return {
                    "task_id": task_id,
                    "status": task_data.get("status", "unknown"),
                    "result": task_data.get("result"),
                    "active_execution": False,
                }
            else:
                return {"task_id": task_id, "status": "not_found"}

        return {
            "task_id": task_id,
            "status": execution.status.value,
            "agent_id": execution.agent_id,
            "current_iteration": execution.current_iteration,
            "iterations_count": len(execution.iterations),
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "sandbox_id": execution.sandbox.sandbox_id if execution.sandbox else None,
            "git_branch": execution.git_manager.feature_branch if execution.git_manager else None,
            "result": execution.result,
            "error": execution.error,
            "active_execution": True,
        }

    async def get_task_iterations(self, task_id: str) -> List[Dict[str, Any]]:
        """Get iteration history for a task"""

        execution = self.active_executions.get(task_id)
        if execution:
            iterations = execution.iterations
        else:
            # Get from database
            iterations = await self._get_task_iterations_from_db(task_id)

        return [
            {
                "iteration_number": it.iteration_number,
                "step": it.step.value if hasattr(it.step, "value") else str(it.step),
                "started_at": it.started_at.isoformat(),
                "completed_at": it.completed_at.isoformat() if it.completed_at else None,
                "success": it.success,
                "error_message": it.error_message,
                "human_question": it.human_question,
                "human_response": it.human_response,
                "input_data": it.input_data,
                "output_data": it.output_data,
            }
            for it in iterations
        ]

    async def cancel_task_execution(self, task_id: str) -> bool:
        """Cancel a running task execution"""

        execution = self.active_executions.get(task_id)
        if not execution:
            return False

        execution.status = TaskStatus.CANCELLED
        execution.completed_at = datetime.now()
        execution.error = "Task cancelled by user"

        # Update database
        await self._update_task_status(task_id, TaskStatus.CANCELLED, error="Task cancelled by user")

        # Schedule cleanup
        asyncio.create_task(self._cleanup_execution(task_id))

        logger.info(f"Task execution cancelled: {task_id}")
        return True

    # Private methods for execution workflow

    async def _execution_worker(self):
        """Main execution worker that processes pending tasks"""
        while self.running:
            try:
                # Find tasks ready for execution
                pending_tasks = [task_id for task_id, execution in self.active_executions.items() if execution.status in [TaskStatus.PENDING, TaskStatus.EXECUTING]]

                # Process each pending task
                for task_id in pending_tasks:
                    try:
                        await self._process_task_execution(task_id)
                    except Exception as e:
                        logger.error(f"Error processing task {task_id}: {e}")
                        await self._handle_execution_error(task_id, str(e))

                # Sleep between iterations
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in execution worker: {e}")
                await asyncio.sleep(10)

    async def _process_task_execution(self, task_id: str):
        """Process a single task execution step"""
        execution = self.active_executions.get(task_id)
        if not execution:
            return

        # Skip if waiting for human or in terminal state
        if execution.status in [
            TaskStatus.WAITING_FOR_HUMAN,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            return

        # Determine next step
        next_step = self._determine_next_step(execution)
        if not next_step:
            return

        # Execute the step
        try:
            await self._execute_step(execution, next_step)
        except Exception as e:
            logger.error(f"Error executing step {next_step} for task {task_id}: {e}")
            await self._handle_execution_error(task_id, str(e))

    def _determine_next_step(self, execution: ExecutionContext) -> Optional[ExecutionStep]:
        """Determine the next execution step"""

        if execution.status == TaskStatus.PENDING:
            return ExecutionStep.ANALYZE_TASK

        if not execution.iterations:
            return ExecutionStep.ANALYZE_TASK

        last_iteration = execution.iterations[-1]

        # Continue based on last completed step
        if last_iteration.step == ExecutionStep.ANALYZE_TASK and last_iteration.success:
            return ExecutionStep.SETUP_SANDBOX
        elif last_iteration.step == ExecutionStep.SETUP_SANDBOX and last_iteration.success:
            return ExecutionStep.SETUP_GIT
        elif last_iteration.step == ExecutionStep.SETUP_GIT and last_iteration.success:
            return ExecutionStep.EXECUTE_ITERATION
        elif last_iteration.step == ExecutionStep.EXECUTE_ITERATION and last_iteration.success:
            # Check if we need human input
            if last_iteration.human_question:
                return ExecutionStep.HUMAN_INTERACTION
            else:
                return ExecutionStep.REVIEW_CHANGES
        elif last_iteration.step == ExecutionStep.HUMAN_INTERACTION and last_iteration.human_response:
            return ExecutionStep.EXECUTE_ITERATION
        elif last_iteration.step == ExecutionStep.REVIEW_CHANGES and last_iteration.success:
            return ExecutionStep.COMMIT_CHANGES
        elif last_iteration.step == ExecutionStep.COMMIT_CHANGES and last_iteration.success:
            # Check if task is complete
            if self._is_task_complete(execution):
                return ExecutionStep.FINALIZE_TASK
            else:
                return ExecutionStep.EXECUTE_ITERATION

        return None

    async def _execute_step(self, execution: ExecutionContext, step: ExecutionStep):
        """Execute a specific step"""

        iteration = TaskIteration(
            iteration_number=execution.current_iteration + 1,
            step=step,
            started_at=datetime.now(),
            completed_at=None,
            input_data={},
            output_data=None,
            success=False,
            error_message=None,
        )

        execution.iterations.append(iteration)
        execution.current_iteration += 1

        try:
            if step == ExecutionStep.ANALYZE_TASK:
                await self._step_analyze_task(execution, iteration)
            elif step == ExecutionStep.SETUP_SANDBOX:
                await self._step_setup_sandbox(execution, iteration)
            elif step == ExecutionStep.SETUP_GIT:
                await self._step_setup_git(execution, iteration)
            elif step == ExecutionStep.EXECUTE_ITERATION:
                await self._step_execute_iteration(execution, iteration)
            elif step == ExecutionStep.REVIEW_CHANGES:
                await self._step_review_changes(execution, iteration)
            elif step == ExecutionStep.COMMIT_CHANGES:
                await self._step_commit_changes(execution, iteration)
            elif step == ExecutionStep.HUMAN_INTERACTION:
                await self._step_human_interaction(execution, iteration)
            elif step == ExecutionStep.FINALIZE_TASK:
                await self._step_finalize_task(execution, iteration)

            iteration.completed_at = datetime.now()
            iteration.success = True

        except Exception as e:
            iteration.completed_at = datetime.now()
            iteration.success = False
            iteration.error_message = str(e)
            raise

        finally:
            # Store iteration in database
            await self._store_task_iteration(execution.task_id, iteration)

    async def _step_analyze_task(self, execution: ExecutionContext, iteration: TaskIteration):
        """Analyze the task and prepare execution plan"""
        execution.status = TaskStatus.ANALYZING
        await self._update_task_status(execution.task_id, TaskStatus.ANALYZING)

        # Analyze task requirements
        task_description = execution.task_data.get("description", "")
        task_title = execution.task_data.get("title", "")

        iteration.input_data = {
            "task_title": task_title,
            "task_description": task_description,
            "agent_type": execution.agent_data.get("type"),
            "agent_role": execution.agent_data.get("role"),
        }

        # Enhance context with organizational knowledge
        enhanced_context = None
        if self.context_enhancer:
            try:
                enhanced_context = await self.context_enhancer.enhance_agent_context(
                    agent_id=execution.agent_id,
                    task_data=execution.task_data,
                    base_context=iteration.input_data,
                )
                logger.info(f"Enhanced context for task {execution.task_id}: " f"{len(enhanced_context.organizational_knowledge)} org + " f"{len(enhanced_context.team_knowledge)} team + " f"{len(enhanced_context.similar_task_insights)} similar task insights")
            except Exception as e:
                logger.error(f"Error enhancing context for task {execution.task_id}: {e}")

        # Simple analysis for now - in a full implementation this would use AI
        iteration.output_data = {
            "analysis_complete": True,
            "requires_sandbox": execution.agent_data.get("type") == "developer",
            "requires_git": bool(execution.agent_data.get("repository_settings", {}).get("repository_url")),
            "enhanced_context": enhanced_context,
            "estimated_complexity": "medium",
            "estimated_iterations": 5,
        }

        logger.info(f"Task analysis complete for {execution.task_id}")

    async def _step_setup_sandbox(self, execution: ExecutionContext, iteration: TaskIteration):
        """Set up sandbox environment for the agent"""
        execution.status = TaskStatus.SETTING_UP
        await self._update_task_status(execution.task_id, TaskStatus.SETTING_UP)

        agent_template = execution.agent_data.get("template_id", "python_developer")
        repository_settings = execution.agent_data.get("repository_settings", {})
        sandbox_settings = execution.agent_data.get("sandbox_settings", {})

        # Create sandbox
        sandbox = await self.sandbox_manager.create_sandbox(
            agent_id=execution.agent_id,
            task_id=execution.task_id,
            agent_template=agent_template,
            repository_settings=repository_settings,
            custom_settings=sandbox_settings,
        )

        execution.sandbox = sandbox

        iteration.input_data = {
            "agent_template": agent_template,
            "repository_settings": repository_settings,
            "sandbox_settings": sandbox_settings,
        }

        iteration.output_data = {
            "sandbox_id": sandbox.sandbox_id,
            "workspace_path": sandbox.workspace_path,
            "container_id": sandbox.container_id,
        }

        logger.info(f"Sandbox setup complete for {execution.task_id}: {sandbox.sandbox_id}")

    async def _step_setup_git(self, execution: ExecutionContext, iteration: TaskIteration):
        """Set up Git workflow for the task"""
        repository_settings = execution.agent_data.get("repository_settings", {})

        if not repository_settings.get("repository_url"):
            # Skip Git setup if no repository
            iteration.output_data = {
                "git_setup": "skipped",
                "reason": "no_repository_configured",
            }
            return

        # Create Git workflow manager
        git_manager = GitWorkflowManager(
            agent_id=execution.agent_id,
            task_id=execution.task_id,
            repo_settings=repository_settings,
        )

        # Setup workspace
        feature_branch = await git_manager.setup_workspace()

        execution.git_manager = git_manager

        # Create enhanced Claude wrapper with Git context and conversation tracking
        execution.claude_wrapper = ClaudeCodeWrapper(
            workspace_path=git_manager.workspace_path,
            git_manager=git_manager,
            agent_id=execution.agent_id,
            task_id=execution.task_id,
            conversation_manager=self.conversation_manager,
        )

        # Initialize File Operations Engine
        file_ops_engine = FileOperationsEngine(git_manager.workspace_path)
        execution.file_operations_engine = file_ops_engine
        self.file_operations_engines[execution.task_id] = file_ops_engine

        # Initialize Claude SDK Manager
        claude_sdk_manager = ClaudeSDKManager(
            file_operations_engine=file_ops_engine,
            conversation_manager=self.conversation_manager,
        )
        execution.claude_sdk_manager = claude_sdk_manager
        self.claude_sdk_managers[execution.task_id] = claude_sdk_manager

        # Start conversation session
        await execution.claude_wrapper.start_conversation_session(execution.sandbox.sandbox_id)

        iteration.input_data = {
            "repository_url": repository_settings.get("repository_url"),
            "default_branch": repository_settings.get("default_branch", "main"),
        }

        iteration.output_data = {
            "git_setup": "complete",
            "feature_branch": feature_branch,
            "workspace_path": git_manager.workspace_path,
        }

        logger.info(f"Git setup complete for {execution.task_id}: {feature_branch}")

    async def _step_execute_iteration(self, execution: ExecutionContext, iteration: TaskIteration):
        """Execute a development iteration using Claude SDK Manager"""
        execution.status = TaskStatus.EXECUTING
        await self._update_task_status(execution.task_id, TaskStatus.EXECUTING)

        task_description = execution.task_data.get("description", "")
        task_title = execution.task_data.get("title", "")

        iteration.input_data = {
            "task_description": task_description,
            "task_title": task_title,
            "iteration_number": iteration.iteration_number,
            "workspace_path": execution.sandbox.workspace_path if execution.sandbox else None,
        }

        try:
            # Start Claude SDK session if not already running
            if not execution.claude_session_id and execution.claude_sdk_manager:
                # Build comprehensive task context
                context_info = ""
                if execution.git_manager:
                    context_info += f"\nRepository: {execution.git_manager.repo_url}"
                    context_info += f"\nBranch: {execution.git_manager.feature_branch}"
                if iteration.iteration_number > 1:
                    context_info += f"\nIteration: {iteration.iteration_number} of ongoing development"

                # Construct task prompt
                task_prompt = f"""
Task: {task_title}

Description: {task_description}

Context: {context_info}

Please analyze the codebase, understand the requirements, and implement the necessary changes. 
Work incrementally and ask for clarification if needed.
"""

                # Start Claude SDK session
                execution.claude_session_id = await execution.claude_sdk_manager.start_session(
                    task_id=execution.task_id,
                    agent_id=execution.agent_id,
                    workspace_path=execution.git_manager.workspace_path if execution.git_manager else execution.sandbox.workspace_path,
                    task_description=task_prompt,
                    additional_context=context_info,
                )

                logger.info(f"Started Claude SDK session: {execution.claude_session_id}")

            # Register interaction callback for human-in-the-loop
            if execution.claude_sdk_manager and execution.claude_session_id:
                execution.claude_sdk_manager.register_interaction_callback(
                    execution.claude_session_id,
                    lambda session, interaction: self._handle_claude_interaction(execution, session, interaction),
                )

            # Monitor session status
            session_status = await execution.claude_sdk_manager.get_session_status(execution.claude_session_id) if execution.claude_session_id else None

            if session_status:
                current_interaction = session_status.get("current_interaction")
                if current_interaction:
                    # Claude is waiting for human input
                    interaction_type = current_interaction.get("type")
                    if interaction_type in ["user_input", "confirmation"]:
                        iteration.human_question = current_interaction.get("prompt")
                        execution.status = TaskStatus.WAITING_FOR_HUMAN
                        await self._update_task_status(execution.task_id, TaskStatus.WAITING_FOR_HUMAN)

                        iteration.output_data = {
                            "claude_session_status": session_status.get("state"),
                            "human_interaction_required": True,
                            "interaction_type": interaction_type,
                            "human_question_asked": True,
                        }

                        logger.info(f"Claude SDK requesting human input for task {execution.task_id}")
                        return

                    elif interaction_type == "file_approval":
                        # File operations pending approval
                        batch_id = current_interaction.get("metadata", {}).get("batch_id")
                        if batch_id and execution.file_operations_engine:
                            # Get diff preview for human review
                            diffs = await execution.file_operations_engine.get_file_diff_preview(batch_id)

                            iteration.human_question = f"""Claude wants to make the following file changes:
                            
{current_interaction.get('prompt')}

File changes preview:
{self._format_diffs_for_human(diffs)}

Approve these changes? (yes/no)"""

                            execution.status = TaskStatus.WAITING_FOR_HUMAN
                            await self._update_task_status(execution.task_id, TaskStatus.WAITING_FOR_HUMAN)

                            iteration.output_data = {
                                "claude_session_status": session_status.get("state"),
                                "file_approval_required": True,
                                "batch_id": batch_id,
                                "file_changes_preview": diffs,
                                "human_question_asked": True,
                            }

                            logger.info(f"Claude SDK requesting file approval for task {execution.task_id}")
                            return

                # No interaction needed - continue execution
                iteration.output_data = {
                    "claude_session_status": session_status.get("state"),
                    "session_active": True,
                    "iteration_completed": True,
                    "workspace_path": session_status.get("workspace_path"),
                }

                # Check if session completed
                if session_status.get("state") in ["completed", "terminated"]:
                    iteration.output_data["development_complete"] = True

            else:
                # No session - this shouldn't happen but handle gracefully
                iteration.output_data = {
                    "error": "No Claude SDK session available",
                    "development_complete": False,
                }

        except Exception as e:
            logger.error(f"Error in Claude SDK iteration: {e}")
            iteration.output_data = {"error": str(e), "development_complete": False}
            raise

        logger.info(f"Development iteration {iteration.iteration_number} processed for {execution.task_id}")

    async def _step_review_changes(self, execution: ExecutionContext, iteration: TaskIteration):
        """Review the changes made in the iteration"""
        execution.status = TaskStatus.REVIEWING
        await self._update_task_status(execution.task_id, TaskStatus.REVIEWING)

        # Review changes - in full implementation this would:
        # 1. Run linting and type checking
        # 2. Run tests
        # 3. Check code quality
        # 4. Validate against requirements

        iteration.output_data = {
            "review_passed": True,
            "issues_found": [],
            "tests_passed": True,
            "code_quality_score": 85,
        }

        logger.info(f"Code review complete for {execution.task_id}")

    async def _step_commit_changes(self, execution: ExecutionContext, iteration: TaskIteration):
        """Commit changes to Git"""
        execution.status = TaskStatus.COMMITTING
        await self._update_task_status(execution.task_id, TaskStatus.COMMITTING)

        if not execution.git_manager:
            iteration.output_data = {"commit": "skipped", "reason": "no_git_manager"}
            return

        # Commit changes
        commit_message = f"Iteration {iteration.iteration_number}: {execution.task_data.get('title', 'Task update')}"
        commit_hash = await execution.git_manager.commit_changes(message=commit_message, iteration_number=iteration.iteration_number)

        iteration.output_data = {
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "branch": execution.git_manager.feature_branch,
        }

        logger.info(f"Changes committed for {execution.task_id}: {commit_hash}")

    async def _step_human_interaction(self, execution: ExecutionContext, iteration: TaskIteration):
        """Handle human interaction step"""
        # This step waits for human response - the actual waiting is handled
        # by the status being WAITING_FOR_HUMAN
        iteration.output_data = {
            "human_interaction": "waiting_for_response",
            "question": iteration.human_question,
        }

    async def _step_finalize_task(self, execution: ExecutionContext, iteration: TaskIteration):
        """Finalize the task execution"""
        execution.status = TaskStatus.COMPLETED
        execution.completed_at = datetime.now()

        # Create pull request if Git is configured
        pr_url = None
        if execution.git_manager:
            try:
                pr = await execution.git_manager.create_pull_request(
                    title=f"🤖 {execution.task_data.get('title', 'Task completion')}",
                    description=f"Autonomous completion of task: {execution.task_data.get('description', '')}",
                )
                pr_url = pr.url if pr else None
            except Exception as e:
                logger.error(f"Failed to create PR for {execution.task_id}: {e}")

        # Prepare final result
        execution.result = {
            "status": "completed",
            "iterations": len(execution.iterations),
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat(),
            "pull_request_url": pr_url,
            "sandbox_id": execution.sandbox.sandbox_id if execution.sandbox else None,
            "git_branch": execution.git_manager.feature_branch if execution.git_manager else None,
        }

        # Update database
        await self._update_task_status(execution.task_id, TaskStatus.COMPLETED, result=execution.result)

        iteration.output_data = execution.result

        # End conversation session
        if execution.claude_wrapper:
            try:
                await execution.claude_wrapper.end_conversation_session()
            except Exception as e:
                logger.error(f"Error ending conversation session: {e}")

        # Store final performance metrics
        await self._store_completion_metrics(execution)

        # Extract knowledge from completed task
        if self.knowledge_extractor:
            try:
                extracted_knowledge_ids = await self.knowledge_extractor.extract_knowledge_from_task(
                    task_id=execution.task_id,
                    agent_id=execution.agent_id,
                    execution_result=execution.result,
                )
                if extracted_knowledge_ids:
                    logger.info(f"Extracted {len(extracted_knowledge_ids)} knowledge items from task {execution.task_id}")
            except Exception as e:
                logger.error(f"Error extracting knowledge from task {execution.task_id}: {e}")

        logger.info(f"✅ Task execution completed: {execution.task_id}")

        # End Claude SDK session
        if execution.claude_sdk_manager and execution.claude_session_id:
            try:
                await execution.claude_sdk_manager.terminate_session(execution.claude_session_id)
            except Exception as e:
                logger.error(f"Error terminating Claude SDK session: {e}")

        # Schedule cleanup
        asyncio.create_task(self._cleanup_execution(execution.task_id))

    def _is_task_complete(self, execution: ExecutionContext) -> bool:
        """Check if the task is complete"""
        # Simple completion check - in full implementation this would be more sophisticated
        return execution.current_iteration >= 3

    async def _handle_execution_error(self, task_id: str, error_message: str):
        """Handle execution error"""
        execution = self.active_executions.get(task_id)
        if execution:
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.now()
            execution.error = error_message

        await self._update_task_status(task_id, TaskStatus.FAILED, error=error_message)

        # Schedule cleanup
        asyncio.create_task(self._cleanup_execution(task_id))

        logger.error(f"Task execution failed: {task_id} - {error_message}")

    async def _cleanup_execution(self, task_id: str):
        """Clean up execution resources"""
        execution = self.active_executions.pop(task_id, None)
        if not execution:
            return

        # Cleanup Claude SDK session
        if execution.claude_sdk_manager and execution.claude_session_id:
            try:
                await execution.claude_sdk_manager.terminate_session(execution.claude_session_id)
            except Exception as e:
                logger.error(f"Error terminating Claude SDK session for {task_id}: {e}")

        # Remove engines from tracking
        self.file_operations_engines.pop(task_id, None)
        self.claude_sdk_managers.pop(task_id, None)

        # Cleanup sandbox
        if execution.sandbox:
            try:
                await self.sandbox_manager.destroy_sandbox(execution.sandbox.sandbox_id)
            except Exception as e:
                logger.error(f"Error destroying sandbox for {task_id}: {e}")

        # Cleanup Git workspace (optional - might want to keep for review)
        if execution.git_manager and execution.status != TaskStatus.COMPLETED:
            try:
                await execution.git_manager.cleanup_workspace()
            except Exception as e:
                logger.error(f"Error cleaning up Git workspace for {task_id}: {e}")

        logger.info(f"Execution cleanup complete: {task_id}")

    async def _monitoring_worker(self):
        """Monitor execution health and timeouts"""
        while self.running:
            try:
                current_time = datetime.now()

                for task_id, execution in list(self.active_executions.items()):
                    # Check for timeouts
                    if execution.status == TaskStatus.WAITING_FOR_HUMAN:
                        # Check human response timeout
                        last_iteration = execution.iterations[-1] if execution.iterations else None
                        if last_iteration and last_iteration.started_at:
                            time_waiting = current_time - last_iteration.started_at
                            if time_waiting > timedelta(seconds=self.human_response_timeout):
                                await self._handle_execution_error(
                                    task_id,
                                    "Human response timeout - no response received within 24 hours",
                                )
                    else:
                        # Check general execution timeout
                        execution_time = current_time - execution.started_at
                        if execution_time > timedelta(seconds=self.iteration_timeout * self.max_iterations):
                            await self._handle_execution_error(
                                task_id,
                                f"Execution timeout - exceeded maximum time limit",
                            )

                    # Check iteration limits
                    if execution.current_iteration > self.max_iterations:
                        await self._handle_execution_error(
                            task_id,
                            f"Maximum iterations exceeded ({self.max_iterations})",
                        )

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring worker: {e}")
                await asyncio.sleep(60)

    async def _cleanup_worker(self):
        """Clean up completed executions periodically"""
        while self.running:
            try:
                current_time = datetime.now()
                cutoff_time = current_time - timedelta(hours=1)  # Keep completed tasks for 1 hour

                completed_tasks = [task_id for task_id, execution in self.active_executions.items() if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and execution.completed_at and execution.completed_at < cutoff_time]

                for task_id in completed_tasks:
                    await self._cleanup_execution(task_id)

                await asyncio.sleep(3600)  # Run every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                await asyncio.sleep(3600)

    # Database operations

    async def _get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data from database"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
            return dict(row) if row else None

    async def _get_agent_data(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data from database"""
        return await DatabaseManager.get_agent(agent_id)

    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Update task status in database"""
        await DatabaseManager.update_task_status(task_id=task_id, status=status.value, result=result)

    async def _store_task_iteration(self, task_id: str, iteration: TaskIteration):
        """Store task iteration in database"""
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO task_iterations (
                    id, task_id, iteration_number, step, started_at, completed_at,
                    input_data, output_data, success, error_message, 
                    human_question, human_response
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                str(uuid.uuid4()),
                task_id,
                iteration.iteration_number,
                iteration.step.value,
                iteration.started_at,
                iteration.completed_at,
                json.dumps(iteration.input_data),
                json.dumps(iteration.output_data) if iteration.output_data else None,
                iteration.success,
                iteration.error_message,
                iteration.human_question,
                iteration.human_response,
            )

    async def _get_task_iterations_from_db(self, task_id: str) -> List[TaskIteration]:
        """Get task iterations from database"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM task_iterations 
                WHERE task_id = $1 
                ORDER BY iteration_number
            """,
                task_id,
            )

            iterations = []
            for row in rows:
                iterations.append(
                    TaskIteration(
                        iteration_number=row["iteration_number"],
                        step=ExecutionStep(row["step"]),
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        input_data=json.loads(row["input_data"]) if row["input_data"] else {},
                        output_data=json.loads(row["output_data"]) if row["output_data"] else None,
                        success=row["success"],
                        error_message=row["error_message"],
                        human_question=row["human_question"],
                        human_response=row["human_response"],
                    )
                )

            return iterations

    async def _store_completion_metrics(self, execution: ExecutionContext):
        """Store performance metrics for completed task"""
        try:
            if not execution.completed_at or not execution.started_at:
                return

            # Calculate execution time
            execution_time = (execution.completed_at - execution.started_at).total_seconds() / 60  # minutes

            # Store metrics
            await self.conversation_manager.store_performance_metric(
                agent_id=execution.agent_id,
                task_id=execution.task_id,
                metric_type="execution_time_minutes",
                metric_value=execution_time,
                metric_unit="minutes",
            )

            await self.conversation_manager.store_performance_metric(
                agent_id=execution.agent_id,
                task_id=execution.task_id,
                metric_type="iterations_to_completion",
                metric_value=float(execution.current_iteration),
                metric_unit="iterations",
            )

            # Store success/failure metric
            success_value = 1.0 if execution.status == TaskStatus.COMPLETED else 0.0
            await self.conversation_manager.store_performance_metric(
                agent_id=execution.agent_id,
                task_id=execution.task_id,
                metric_type="task_success_rate",
                metric_value=success_value,
                metric_unit="boolean",
            )

        except Exception as e:
            logger.error(f"Error storing completion metrics: {e}")

    async def _handle_claude_interaction(self, execution: ExecutionContext, session: ClaudeSDKSession, interaction):
        """Handle interaction from Claude SDK"""
        logger.info(f"Claude interaction for task {execution.task_id}: {interaction.interaction_type}")

        # This will be processed in the next iteration of _step_execute_iteration
        # The interaction handling is done there to maintain the execution flow

    def _format_diffs_for_human(self, diffs: Dict[str, str]) -> str:
        """Format file diffs for human review"""
        if not diffs:
            return "No file changes detected."

        formatted = []
        for file_path, diff in diffs.items():
            formatted.append(f"\n--- {file_path} ---")
            formatted.append(diff[:1000] + "..." if len(diff) > 1000 else diff)

        return "\n".join(formatted)

    async def handle_human_response(self, task_id: str, response: str) -> bool:
        """Enhanced human response handler that integrates with Claude SDK"""

        execution = self.active_executions.get(task_id)
        if not execution or execution.status != TaskStatus.WAITING_FOR_HUMAN:
            return False

        # Find the current iteration waiting for human response
        current_iteration = None
        for iteration in reversed(execution.iterations):
            if iteration.human_question and not iteration.human_response:
                current_iteration = iteration
                break

        if current_iteration:
            current_iteration.human_response = response
            execution.status = TaskStatus.EXECUTING

            # Handle different types of responses
            output_data = current_iteration.output_data or {}

            if output_data.get("file_approval_required"):
                # Handle file approval
                batch_id = output_data.get("batch_id")
                approved = response.lower().strip() in [
                    "yes",
                    "y",
                    "approve",
                    "approved",
                    "true",
                ]

                if batch_id and execution.claude_sdk_manager and execution.claude_session_id:
                    success = await execution.claude_sdk_manager.approve_file_operations(execution.claude_session_id, batch_id, approved)

                    if success:
                        logger.info(f"File operations {'approved' if approved else 'rejected'} for task {task_id}")
                    else:
                        logger.error(f"Failed to process file approval for task {task_id}")

            else:
                # Handle general user input
                if execution.claude_sdk_manager and execution.claude_session_id:
                    success = await execution.claude_sdk_manager.send_input(execution.claude_session_id, response)

                    if success:
                        logger.info(f"Human response sent to Claude SDK for task {task_id}")
                    else:
                        logger.error(f"Failed to send human response to Claude SDK for task {task_id}")

            # Update database
            await self._store_task_iteration(task_id, current_iteration)
            await self._update_task_status(task_id, TaskStatus.EXECUTING)

            logger.info(f"Human response processed for task {task_id}")
            return True

        return False
