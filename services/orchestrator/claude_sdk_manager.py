"""
Claude SDK Manager for FuzeAgent

Manages Claude Code SDK processes, handles interactive states, and integrates
with the File Operations Engine to apply code changes safely.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from .conversation_manager import ConversationManager, MessageType
from .file_operations_engine import FileOperationsEngine, OperationBatch

logger = logging.getLogger(__name__)


class ClaudeSDKState(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PROCESSING = "processing"
    ERROR = "error"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class InteractionType(str, Enum):
    USER_INPUT = "user_input"
    FILE_APPROVAL = "file_approval"
    CONFIRMATION = "confirmation"
    SELECTION = "selection"


@dataclass
class ClaudeInteraction:
    """Represents an interaction request from Claude SDK"""

    interaction_id: str
    interaction_type: InteractionType
    prompt: str
    options: Optional[List[str]] = None
    default_response: Optional[str] = None
    timeout_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ClaudeSDKSession:
    """Represents a Claude SDK session"""

    session_id: str
    task_id: str
    agent_id: str
    workspace_path: str
    process: Optional[asyncio.subprocess.Process] = None
    state: ClaudeSDKState = ClaudeSDKState.IDLE
    current_interaction: Optional[ClaudeInteraction] = None
    output_buffer: str = ""
    error_buffer: str = ""
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class ClaudeSDKManager:
    """
    Manages Claude Code SDK processes and handles all interactions.

    Features:
    - Interactive process management
    - Real-time output streaming
    - Human-in-the-loop handling
    - File operations integration
    - State management and recovery
    """

    def __init__(
        self,
        file_operations_engine: FileOperationsEngine,
        conversation_manager: ConversationManager,
    ):
        self.file_ops_engine = file_operations_engine
        self.conversation_manager = conversation_manager
        self.sessions: Dict[str, ClaudeSDKSession] = {}
        self.interaction_callbacks: Dict[str, Callable] = {}

        # Configuration
        self.claude_cli_path = "claude"  # Assume in PATH
        self.interaction_timeout = 300  # 5 minutes
        self.process_timeout = 3600  # 1 hour

        # Pattern matching for interactive states
        self.interaction_patterns = {
            InteractionType.USER_INPUT: [
                r"Please provide.*?:",
                r"Enter your.*?:",
                r"What would you like.*?:",
                r"\?\s*$",
            ],
            InteractionType.FILE_APPROVAL: [
                r"Apply these changes.*?\?",
                r"Proceed with.*?file.*?changes.*?\?",
                r"Create.*?files.*?\?",
                r"Modify.*?files.*?\?",
            ],
            InteractionType.CONFIRMATION: [
                r"Are you sure.*?\?",
                r"Continue.*?\?",
                r"Proceed.*?\?",
                r"\(y/n\)",
            ],
            InteractionType.SELECTION: [
                r"Choose.*?:",
                r"Select.*?:",
                r"\[1\].*?\[2\]",
                r"Options.*?:",
            ],
        }

    async def start_session(
        self,
        task_id: str,
        agent_id: str,
        workspace_path: str,
        task_description: str,
        additional_context: Optional[str] = None,
    ) -> str:
        """Start a new Claude SDK session"""

        session_id = f"claude-{task_id}-{int(time.time())}"

        session = ClaudeSDKSession(
            session_id=session_id,
            task_id=task_id,
            agent_id=agent_id,
            workspace_path=workspace_path,
            started_at=datetime.now(),
            last_activity=datetime.now(),
        )

        self.sessions[session_id] = session

        try:
            # Start Claude Code process
            await self._start_claude_process(
                session, task_description, additional_context
            )

            # Start output monitoring
            asyncio.create_task(self._monitor_session(session))

            logger.info(f"Started Claude SDK session {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error starting Claude SDK session: {e}")
            session.state = ClaudeSDKState.ERROR
            raise

    async def send_input(self, session_id: str, user_input: str) -> bool:
        """Send input to a Claude SDK session"""

        session = self.sessions.get(session_id)
        if not session or not session.process:
            return False

        try:
            # Send input to process
            session.process.stdin.write((user_input + "\n").encode())
            await session.process.stdin.drain()

            # Update session state
            session.state = ClaudeSDKState.PROCESSING
            session.current_interaction = None
            session.last_activity = datetime.now()

            # Store interaction in conversation manager
            await self.conversation_manager.store_message(
                session_id=session_id,
                message={
                    "task_id": session.task_id,
                    "iteration_number": 1,  # Would be dynamic in real implementation
                    "message_type": MessageType.USER_PROMPT,
                    "content": user_input,
                    "metadata": {"interaction_type": "human_response"},
                },
            )

            logger.info(f"Sent input to Claude SDK session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending input to session {session_id}: {e}")
            return False

    async def approve_file_operations(
        self, session_id: str, batch_id: str, approved: bool
    ) -> bool:
        """Approve or reject file operations from Claude SDK"""

        # Apply file operations
        success = await self.file_ops_engine.approve_operations(batch_id, approved)

        if success and approved:
            # Send approval to Claude SDK
            await self.send_input(session_id, "y")
            return True
        elif success and not approved:
            # Send rejection to Claude SDK
            await self.send_input(session_id, "n")
            return True

        return False

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a Claude SDK session"""

        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "task_id": session.task_id,
            "agent_id": session.agent_id,
            "state": session.state.value,
            "current_interaction": (
                {
                    "id": session.current_interaction.interaction_id,
                    "type": session.current_interaction.interaction_type.value,
                    "prompt": session.current_interaction.prompt,
                    "options": session.current_interaction.options,
                }
                if session.current_interaction
                else None
            ),
            "started_at": (
                session.started_at.isoformat() if session.started_at else None
            ),
            "last_activity": (
                session.last_activity.isoformat() if session.last_activity else None
            ),
            "workspace_path": session.workspace_path,
        }

    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a Claude SDK session"""

        session = self.sessions.get(session_id)
        if not session:
            return False

        try:
            if session.process:
                session.process.terminate()
                try:
                    await asyncio.wait_for(session.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    session.process.kill()
                    await session.process.wait()

            session.state = ClaudeSDKState.TERMINATED
            logger.info(f"Terminated Claude SDK session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            return False

    def register_interaction_callback(self, session_id: str, callback: Callable):
        """Register callback for interaction events"""
        self.interaction_callbacks[session_id] = callback

    async def stream_output(self, session_id: str) -> AsyncGenerator[str, None]:
        """Stream real-time output from Claude SDK session"""

        session = self.sessions.get(session_id)
        if not session:
            return

        last_position = 0

        while session.state not in [
            ClaudeSDKState.COMPLETED,
            ClaudeSDKState.TERMINATED,
            ClaudeSDKState.ERROR,
        ]:
            # Check for new output
            if len(session.output_buffer) > last_position:
                new_output = session.output_buffer[last_position:]
                last_position = len(session.output_buffer)
                yield new_output

            await asyncio.sleep(0.1)  # Small delay to prevent excessive CPU usage

    # Private methods

    async def _start_claude_process(
        self,
        session: ClaudeSDKSession,
        task_description: str,
        additional_context: Optional[str] = None,
    ):
        """Start the Claude Code CLI process"""

        # Build Claude command
        cmd = [
            self.claude_cli_path,
            "code",
            "--workspace",
            session.workspace_path,
            "--task",
            task_description,
        ]

        if additional_context:
            cmd.extend(["--context", additional_context])

        # Set environment
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")

        # Start process
        session.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=session.workspace_path,
            env=env,
        )

        session.state = ClaudeSDKState.RUNNING
        logger.info(f"Started Claude CLI process for session {session.session_id}")

    async def _monitor_session(self, session: ClaudeSDKSession):
        """Monitor a Claude SDK session for output and interactions"""

        logger.info(f"Monitoring Claude SDK session {session.session_id}")

        try:
            while session.process and session.process.returncode is None:
                # Read output with timeout
                try:
                    output_data = await asyncio.wait_for(
                        session.process.stdout.read(1024), timeout=0.1
                    )

                    if output_data:
                        output_text = output_data.decode("utf-8", errors="replace")
                        session.output_buffer += output_text
                        session.last_activity = datetime.now()

                        # Process output for interactions
                        await self._process_output(session, output_text)

                except asyncio.TimeoutError:
                    # Check for session timeout
                    if self._is_session_timed_out(session):
                        logger.warning(f"Session {session.session_id} timed out")
                        session.state = ClaudeSDKState.ERROR
                        await self.terminate_session(session.session_id)
                        break

                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.01)

            # Process completed
            if session.process and session.process.returncode == 0:
                session.state = ClaudeSDKState.COMPLETED
                logger.info(
                    f"Claude SDK session {session.session_id} completed successfully"
                )
            else:
                session.state = ClaudeSDKState.ERROR
                logger.error(f"Claude SDK session {session.session_id} failed")

        except Exception as e:
            logger.error(f"Error monitoring session {session.session_id}: {e}")
            session.state = ClaudeSDKState.ERROR

    async def _process_output(self, session: ClaudeSDKSession, output_text: str):
        """Process output from Claude SDK to detect interactions"""

        # Store output in conversation manager
        await self.conversation_manager.store_message(
            session_id=session.session_id,
            message={
                "task_id": session.task_id,
                "iteration_number": 1,  # Would be dynamic
                "message_type": MessageType.CLAUDE_RESPONSE,
                "content": output_text,
                "metadata": {"stream_chunk": True},
            },
        )

        # Check for interaction patterns
        interaction = self._detect_interaction(output_text)
        if interaction:
            session.current_interaction = interaction
            session.state = ClaudeSDKState.WAITING_FOR_INPUT

            # Notify callback if registered
            callback = self.interaction_callbacks.get(session.session_id)
            if callback:
                asyncio.create_task(callback(session, interaction))

            logger.info(
                f"Detected interaction in session {session.session_id}: {interaction.interaction_type}"
            )

        # Check for file operations
        await self._check_for_file_operations(session, output_text)

    def _detect_interaction(self, output_text: str) -> Optional[ClaudeInteraction]:
        """Detect if output contains an interaction request"""

        # Check each interaction type
        for interaction_type, patterns in self.interaction_patterns.items():
            for pattern in patterns:
                if re.search(pattern, output_text, re.IGNORECASE | re.MULTILINE):
                    # Extract the prompt (last few lines)
                    lines = output_text.strip().split("\n")
                    prompt = "\n".join(lines[-3:])  # Last 3 lines as prompt

                    interaction_id = f"interaction-{int(time.time())}"

                    return ClaudeInteraction(
                        interaction_id=interaction_id,
                        interaction_type=interaction_type,
                        prompt=prompt,
                        timeout_seconds=self.interaction_timeout,
                    )

        return None

    async def _check_for_file_operations(
        self, session: ClaudeSDKSession, output_text: str
    ):
        """Check if output contains file operation requests"""

        # Look for structured file operations (JSON format)
        try:
            # Try to find JSON blocks in output
            json_blocks = re.findall(r"```json\n(.*?)\n```", output_text, re.DOTALL)
            for json_block in json_blocks:
                try:
                    operations_data = json.loads(json_block)
                    if "operations" in operations_data:
                        # Process file operations
                        batch = await self.file_ops_engine.process_claude_response(
                            operations_data, session.task_id, session.agent_id
                        )

                        if batch.requires_approval:
                            session.state = ClaudeSDKState.WAITING_FOR_APPROVAL
                            session.current_interaction = ClaudeInteraction(
                                interaction_id=f"approval-{batch.batch_id}",
                                interaction_type=InteractionType.FILE_APPROVAL,
                                prompt=f"Approve file operations: {batch.description}",
                                metadata={"batch_id": batch.batch_id},
                            )
                        else:
                            # Auto-approved operations
                            await self.file_ops_engine.apply_operations_if_approved(
                                batch.batch_id
                            )

                        logger.info(
                            f"Detected file operations in session {session.session_id}"
                        )

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Error processing file operations: {e}")

    def _is_session_timed_out(self, session: ClaudeSDKSession) -> bool:
        """Check if session has timed out"""

        if not session.last_activity:
            return False

        timeout_seconds = self.process_timeout
        if session.current_interaction:
            timeout_seconds = (
                session.current_interaction.timeout_seconds or self.interaction_timeout
            )

        time_since_activity = (datetime.now() - session.last_activity).total_seconds()
        return time_since_activity > timeout_seconds
