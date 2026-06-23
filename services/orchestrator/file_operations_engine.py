"""
File Operations Engine for FuzeAgent Claude Code Integration

Handles all file system operations requested by Claude Code SDK including:
- File creation, modification, and deletion
- Diff application and conflict resolution
- Human verification workflows
- Rollback and backup management
- Safe file operations with validation
"""

import asyncio
import difflib
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    MOVE_FILE = "move_file"
    APPLY_DIFF = "apply_diff"


class ChangeType(str, Enum):
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    APPEND = "append"
    PREPEND = "prepend"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


@dataclass
class FileChange:
    """Represents a single change within a file"""

    type: ChangeType
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    content: Optional[str] = None
    original_content: Optional[str] = None


@dataclass
class FileOperation:
    """Represents a complete file operation"""

    operation_id: str
    operation: OperationType
    path: str
    content: Optional[str] = None
    changes: Optional[List[FileChange]] = None
    backup_path: Optional[str] = None
    requires_approval: bool = True
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = None
    applied_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OperationBatch:
    """Represents a batch of related file operations"""

    batch_id: str
    task_id: str
    agent_id: str
    operations: List[FileOperation]
    description: str
    requires_approval: bool = True
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = None
    applied_at: Optional[datetime] = None
    rollback_info: Optional[Dict[str, Any]] = None


class FileOperationsEngine:
    """
    Handles file operations from Claude Code SDK responses.

    Features:
    - Safe file operations with backups
    - Human approval workflows
    - Conflict detection and resolution
    - Diff application and validation
    - Rollback capabilities
    - Integration with Git workflows
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.backup_dir = self.workspace_path / ".fuzeagent" / "backups"
        self.pending_operations: Dict[str, OperationBatch] = {}
        self.applied_operations: Dict[str, OperationBatch] = {}

        # Configuration
        self.auto_approve_safe_operations = True  # Small changes, tests, docs
        self.max_file_size_bytes = 1024 * 1024  # 1MB
        self.backup_retention_days = 7

        # Initialize backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def process_claude_response(
        self, claude_response: Dict[str, Any], task_id: str, agent_id: str
    ) -> OperationBatch:
        """
        Process a Claude Code SDK response and create file operations.

        Args:
            claude_response: Raw response from Claude Code SDK
            task_id: Task ID for tracking
            agent_id: Agent ID for tracking

        Returns:
            OperationBatch with all requested operations
        """
        logger.info(f"Processing Claude response for task {task_id}")

        try:
            # Parse Claude response format
            operations_data = self._parse_claude_response(claude_response)

            # Create file operations
            operations = []
            for op_data in operations_data.get("operations", []):
                operation = await self._create_file_operation(op_data)
                operations.append(operation)

            # Create operation batch
            batch = OperationBatch(
                batch_id=str(uuid.uuid4()),
                task_id=task_id,
                agent_id=agent_id,
                operations=operations,
                description=operations_data.get(
                    "explanation", "Claude Code file operations"
                ),
                requires_approval=operations_data.get(
                    "human_verification_required", True
                ),
                created_at=datetime.now(),
                rollback_info={},
            )

            # Determine if auto-approval is possible
            if self._can_auto_approve(batch):
                batch.approval_status = ApprovalStatus.AUTO_APPROVED
                batch.requires_approval = False

            # Store pending batch
            self.pending_operations[batch.batch_id] = batch

            logger.info(
                f"Created operation batch {batch.batch_id} with {len(operations)} operations"
            )
            return batch

        except Exception as e:
            logger.error(f"Error processing Claude response: {e}")
            raise

    async def approve_operations(self, batch_id: str, approved: bool = True) -> bool:
        """Approve or reject a batch of operations"""

        batch = self.pending_operations.get(batch_id)
        if not batch:
            logger.error(f"Operation batch {batch_id} not found")
            return False

        if approved:
            batch.approval_status = ApprovalStatus.APPROVED
            logger.info(f"Operation batch {batch_id} approved")
            return await self._apply_operations(batch)
        else:
            batch.approval_status = ApprovalStatus.REJECTED
            logger.info(f"Operation batch {batch_id} rejected")
            return True

    async def apply_operations_if_approved(self, batch_id: str) -> bool:
        """Apply operations if they're approved or auto-approved"""

        batch = self.pending_operations.get(batch_id)
        if not batch:
            return False

        if batch.approval_status in [
            ApprovalStatus.APPROVED,
            ApprovalStatus.AUTO_APPROVED,
        ]:
            return await self._apply_operations(batch)

        return False

    async def rollback_operations(self, batch_id: str) -> bool:
        """Rollback a previously applied batch of operations"""

        batch = self.applied_operations.get(batch_id)
        if not batch or not batch.rollback_info:
            logger.error(f"Cannot rollback batch {batch_id} - no rollback info")
            return False

        try:
            logger.info(f"Rolling back operation batch {batch_id}")

            # Restore files from backups
            for operation in reversed(batch.operations):  # Reverse order for rollback
                await self._rollback_operation(operation, batch.rollback_info)

            # Move batch back to pending
            del self.applied_operations[batch_id]
            batch.applied_at = None
            batch.approval_status = ApprovalStatus.PENDING
            self.pending_operations[batch_id] = batch

            logger.info(f"Successfully rolled back batch {batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error rolling back batch {batch_id}: {e}")
            return False

    async def get_file_diff_preview(self, batch_id: str) -> Dict[str, str]:
        """Get a preview of file changes as unified diffs"""

        batch = self.pending_operations.get(batch_id)
        if not batch:
            return {}

        diffs = {}

        for operation in batch.operations:
            try:
                if operation.operation == OperationType.CREATE_FILE:
                    # For new files, show the entire content
                    diffs[operation.path] = (
                        f"New file: {operation.path}\n" + operation.content
                    )

                elif operation.operation == OperationType.MODIFY_FILE:
                    # Generate diff for existing file
                    original_path = self.workspace_path / operation.path
                    if original_path.exists():
                        original_content = original_path.read_text()
                        new_content = await self._apply_changes_to_content(
                            original_content, operation.changes
                        )

                        diff = difflib.unified_diff(
                            original_content.splitlines(keepends=True),
                            new_content.splitlines(keepends=True),
                            fromfile=f"a/{operation.path}",
                            tofile=f"b/{operation.path}",
                        )
                        diffs[operation.path] = "".join(diff)
                    else:
                        diffs[operation.path] = f"File not found: {operation.path}"

                elif operation.operation == OperationType.DELETE_FILE:
                    diffs[operation.path] = f"Delete file: {operation.path}"

            except Exception as e:
                diffs[operation.path] = f"Error generating diff: {str(e)}"

        return diffs

    def get_pending_operations(self) -> List[OperationBatch]:
        """Get all pending operation batches"""
        return list(self.pending_operations.values())

    def get_applied_operations(self) -> List[OperationBatch]:
        """Get all applied operation batches"""
        return list(self.applied_operations.values())

    # Private methods

    def _parse_claude_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Claude Code SDK response format"""

        # Handle different response formats
        if "operations" in response:
            # Direct operations format
            return response
        elif "files" in response:
            # Legacy format - convert to operations
            operations = []
            for file_info in response["files"]:
                if file_info.get("type") == "implementation":
                    operations.append(
                        {
                            "operation": "create_file",
                            "path": file_info["filename"],
                            "content": file_info["content"],
                        }
                    )
            return {
                "operations": operations,
                "explanation": response.get("explanation", ""),
                "human_verification_required": True,
            }
        else:
            # Try to extract from text content
            return self._extract_operations_from_text(response)

    def _extract_operations_from_text(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract file operations from text-based Claude response"""
        # This would parse markdown code blocks and extract file operations
        # Simplified implementation - in production this would be more sophisticated

        content = response.get("content", "")
        operations = []

        # Look for code blocks with file paths
        import re

        code_blocks = re.findall(r"```(\w+)?\n(.*?)\n```", content, re.DOTALL)

        for i, (lang, code) in enumerate(code_blocks):
            # Simple heuristic - create files for code blocks
            extension = self._get_extension_for_language(lang) if lang else "txt"
            filename = f"generated_file_{i}.{extension}"

            operations.append(
                {"operation": "create_file", "path": filename, "content": code.strip()}
            )

        return {
            "operations": operations,
            "explanation": "Extracted from Claude response",
            "human_verification_required": True,
        }

    def _get_extension_for_language(self, language: str) -> str:
        """Get file extension for programming language"""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "rust": "rs",
            "go": "go",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "bash": "sh",
            "yaml": "yml",
            "json": "json",
        }
        return extensions.get(language.lower(), "txt")

    async def _create_file_operation(self, op_data: Dict[str, Any]) -> FileOperation:
        """Create a FileOperation from operation data"""

        operation_type = OperationType(op_data["operation"])
        operation_id = str(uuid.uuid4())

        # Parse changes if present
        changes = None
        if "changes" in op_data:
            changes = []
            for change_data in op_data["changes"]:
                change = FileChange(
                    type=ChangeType(change_data["type"]),
                    line_start=change_data.get("line_start") or change_data.get("line"),
                    line_end=change_data.get("line_end"),
                    content=change_data.get("content"),
                    original_content=change_data.get("original_content"),
                )
                changes.append(change)

        return FileOperation(
            operation_id=operation_id,
            operation=operation_type,
            path=op_data["path"],
            content=op_data.get("content"),
            changes=changes,
            requires_approval=op_data.get("requires_approval", True),
            created_at=datetime.now(),
            metadata=op_data.get("metadata", {}),
        )

    def _can_auto_approve(self, batch: OperationBatch) -> bool:
        """Determine if operations can be auto-approved"""

        if not self.auto_approve_safe_operations:
            return False

        # Auto-approve if all operations are "safe"
        for operation in batch.operations:
            if not self._is_safe_operation(operation):
                return False

        return True

    def _is_safe_operation(self, operation: FileOperation) -> bool:
        """Check if an operation is safe for auto-approval"""

        path = Path(operation.path)

        # Auto-approve test files
        if any(test_dir in path.parts for test_dir in ["test", "tests", "__tests__"]):
            return True

        # Auto-approve documentation
        if path.suffix.lower() in [".md", ".txt", ".rst"]:
            return True

        # Auto-approve small files
        if operation.content and len(operation.content) < 1000:  # Less than 1KB
            return True

        # Auto-approve specific safe paths
        safe_paths = [".gitignore", "requirements.txt", "package.json", "README.md"]
        if path.name in safe_paths:
            return True

        return False

    async def _apply_operations(self, batch: OperationBatch) -> bool:
        """Apply all operations in a batch"""

        logger.info(f"Applying operation batch {batch.batch_id}")

        try:
            # Create backups first
            rollback_info = {}

            for operation in batch.operations:
                backup_path = await self._create_backup(operation)
                if backup_path:
                    rollback_info[operation.operation_id] = backup_path
                    operation.backup_path = str(backup_path)

            batch.rollback_info = rollback_info

            # Apply operations
            for operation in batch.operations:
                await self._apply_single_operation(operation)
                operation.applied_at = datetime.now()

            # Move to applied operations
            batch.applied_at = datetime.now()
            self.applied_operations[batch.batch_id] = batch
            del self.pending_operations[batch.batch_id]

            logger.info(f"Successfully applied batch {batch.batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error applying batch {batch.batch_id}: {e}")
            # Attempt rollback
            await self._emergency_rollback(batch)
            return False

    async def _apply_single_operation(self, operation: FileOperation):
        """Apply a single file operation"""

        file_path = self.workspace_path / operation.path

        if operation.operation == OperationType.CREATE_FILE:
            # Create file and directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(operation.content)
            logger.info(f"Created file: {operation.path}")

        elif operation.operation == OperationType.MODIFY_FILE:
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Cannot modify non-existent file: {operation.path}"
                )

            original_content = file_path.read_text()
            new_content = await self._apply_changes_to_content(
                original_content, operation.changes
            )
            file_path.write_text(new_content)
            logger.info(f"Modified file: {operation.path}")

        elif operation.operation == OperationType.DELETE_FILE:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {operation.path}")

        elif operation.operation == OperationType.MOVE_FILE:
            new_path = self.workspace_path / operation.metadata["new_path"]
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(new_path))
            logger.info(
                f"Moved file: {operation.path} -> {operation.metadata['new_path']}"
            )

    async def _apply_changes_to_content(
        self, original: str, changes: List[FileChange]
    ) -> str:
        """Apply a list of changes to file content"""

        lines = original.splitlines(keepends=True)

        # Sort changes by line number in reverse order to avoid offset issues
        sorted_changes = sorted(
            [c for c in changes if c.line_start is not None],
            key=lambda x: x.line_start,
            reverse=True,
        )

        for change in sorted_changes:
            if change.type == ChangeType.INSERT:
                lines.insert(change.line_start, change.content + "\n")

            elif change.type == ChangeType.REPLACE:
                end_line = change.line_end or change.line_start
                # Replace lines (convert to 0-based indexing)
                del lines[change.line_start - 1 : end_line]
                lines.insert(change.line_start - 1, change.content + "\n")

            elif change.type == ChangeType.DELETE:
                end_line = change.line_end or change.line_start
                del lines[change.line_start - 1 : end_line]

        # Handle non-line-based changes
        content = "".join(lines)

        for change in changes:
            if change.line_start is None:  # Content-based changes
                if change.type == ChangeType.APPEND:
                    content += change.content
                elif change.type == ChangeType.PREPEND:
                    content = change.content + content

        return content

    async def _create_backup(self, operation: FileOperation) -> Optional[Path]:
        """Create backup of file before modification"""

        file_path = self.workspace_path / operation.path

        if not file_path.exists():
            return None  # No backup needed for new files

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{operation.operation_id}_{timestamp}_{file_path.name}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(str(file_path), str(backup_path))
        logger.debug(f"Created backup: {backup_path}")

        return backup_path

    async def _rollback_operation(
        self, operation: FileOperation, rollback_info: Dict[str, Any]
    ):
        """Rollback a single operation"""

        backup_path = rollback_info.get(operation.operation_id)
        file_path = self.workspace_path / operation.path

        if operation.operation == OperationType.CREATE_FILE:
            # Delete created file
            if file_path.exists():
                file_path.unlink()

        elif operation.operation in [
            OperationType.MODIFY_FILE,
            OperationType.DELETE_FILE,
        ]:
            # Restore from backup
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, str(file_path))

    async def _emergency_rollback(self, batch: OperationBatch):
        """Emergency rollback when batch application fails"""

        logger.warning(f"Performing emergency rollback for batch {batch.batch_id}")

        try:
            if batch.rollback_info:
                for operation in reversed(batch.operations):
                    if operation.applied_at:  # Only rollback applied operations
                        await self._rollback_operation(operation, batch.rollback_info)
        except Exception as e:
            logger.error(f"Emergency rollback failed: {e}")
            # This is a critical error - operations may be in inconsistent state
