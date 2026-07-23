import asyncio
import json
import os
import subprocess  # nosec B404 -- subprocess used only for running known test runners
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Import Anthropic SDK for real Claude integration
import anthropic
from anthropic import Anthropic
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Import conversation manager for full chat tracking.
# This module is imported both as part of the `services.orchestrator` package
# (relative form, e.g. from main.py/agent_manager.py) and flat with
# services/orchestrator on sys.path (e.g. from tests and main_with_hierarchy.py),
# so support both — mirrors the existing pattern in hierarchy_endpoints.py.
try:
    from .conversation_manager import ConversationManager, MessageType
except ImportError:  # pragma: no cover - flat import (no parent package)
    from conversation_manager import ConversationManager, MessageType


class ClaudeCodeInput(BaseModel):
    """Input schema for Claude Code tool"""

    task: str = Field(description="Coding task to complete")
    language: str = Field(default="python", description="Programming language")
    context: str = Field(default="", description="Additional context or requirements")
    include_tests: bool = Field(
        default=True, description="Whether to include unit tests"
    )
    include_docs: bool = Field(
        default=True, description="Whether to include documentation"
    )
    file_path: Optional[str] = Field(
        default=None, description="Optional file path for code context"
    )


class ClaudeCodeWrapper(BaseTool):
    name: str = "claude_code"
    description: str = """
    Execute advanced coding tasks using Claude AI with real-time code generation, 
    testing, and documentation. Supports multiple programming languages and 
    follows industry best practices. Enhanced for repository context and Git integration.
    """
    args_schema: Type[BaseModel] = ClaudeCodeInput

    # Runtime attributes. ``BaseTool`` is a Pydantic v2 model, which rejects
    # assignment to undeclared attributes ("object has no field ...").  These
    # are declared as model fields (rather than PrivateAttr) so they remain
    # publicly readable on the instance (e.g. ``wrapper.client`` /
    # ``wrapper.model``), preserving the tool's public interface.  Object
    # handles (Anthropic SDK client, git/conversation managers) are typed
    # ``Any`` so Pydantic stores them as-is without schema validation.
    client: Optional[Any] = None
    model: str = "claude-3-5-sonnet-20241022"
    workspace_path: Optional[str] = None
    git_manager: Optional[Any] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_manager: Optional[Any] = None
    conversation_session_id: Optional[str] = None
    current_context: Dict[str, Any] = Field(default_factory=dict)
    repository_context: Dict[str, Any] = Field(default_factory=dict)

    def __init__(
        self,
        workspace_path: Optional[str] = None,
        git_manager: Optional[Any] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        conversation_manager: Optional[ConversationManager] = None,
    ):
        super().__init__()
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        self.model = "claude-3-5-sonnet-20241022"
        self.workspace_path = workspace_path or os.getcwd()
        self.git_manager = git_manager
        self.agent_id = agent_id
        self.task_id = task_id
        self.conversation_manager = conversation_manager or ConversationManager()
        self.conversation_session_id: Optional[str] = None
        self.current_context = {}  # Store context between iterations

        # Repository context
        self.repository_context = {
            "files_changed": [],
            "current_branch": None,
            "last_commit": None,
            "iteration_count": 0,
        }

    def _run(
        self,
        task: str,
        language: str = "python",
        context: str = "",
        include_tests: bool = True,
        include_docs: bool = True,
        file_path: Optional[str] = None,
        iteration_number: Optional[int] = None,
    ) -> str:
        """Execute Claude Code for a specific task with real AI integration"""

        try:
            # Update iteration count
            if iteration_number:
                self.repository_context["iteration_count"] = iteration_number
            else:
                self.repository_context["iteration_count"] += 1

            # Get repository context if Git manager is available
            repo_context = ""
            if self.git_manager:
                try:
                    # Note: In a full implementation, we'd make this method async
                    # For now, we'll skip the Git context in the sync version
                    repo_context = (
                        "Repository context: Available (Git manager configured)"
                    )
                except Exception as e:
                    repo_context = f"Repository context unavailable: {str(e)}"

            # Read existing file context if provided
            existing_code = ""
            if file_path:
                # Use workspace-relative path if available
                full_path = (
                    os.path.join(self.workspace_path, file_path)
                    if not os.path.isabs(file_path)
                    else file_path
                )
                if os.path.exists(full_path):
                    with open(full_path, "r") as f:
                        existing_code = f.read()

            # Prepare the comprehensive prompt with repository context
            prompt = self._build_prompt(
                task=task,
                language=language,
                context=context,
                existing_code=existing_code,
                include_tests=include_tests,
                include_docs=include_docs,
                repo_context=repo_context,
            )

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,  # Lower temperature for more consistent code
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse the response and extract code files
            result = self._parse_response(
                response.content[0].text, language, include_tests, include_docs
            )

            # Save files to workspace if available, otherwise use temp directory
            if self.workspace_path and os.path.exists(self.workspace_path):
                saved_files = self._save_files_to_workspace(result["files"])
            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    saved_files = self._save_files(result["files"], tmpdir)

            # Update repository context with changed files
            self.repository_context["files_changed"].extend(
                [
                    f["filename"]
                    for f in result["files"]
                    if f["type"] == "implementation"
                ]
            )

            # Run tests if generated and in workspace
            test_results = None
            if include_tests and any(f["type"] == "test" for f in result["files"]):
                if self.workspace_path and os.path.exists(self.workspace_path):
                    test_results = self._run_tests(self.workspace_path, language)
                else:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        self._save_files(result["files"], tmpdir)
                        test_results = self._run_tests(tmpdir, language)

            return json.dumps(
                {
                    "status": "success",
                    "files": result["files"],
                    "explanation": result.get("explanation", ""),
                    "test_results": test_results,
                    "commit_message": result.get("commit_message", ""),
                    "execution_summary": f"Generated {len(result['files'])} files for {language} task: {task[:100]}...",
                    "iteration": self.repository_context["iteration_count"],
                    "workspace_path": self.workspace_path,
                    "repository_context": self.repository_context,
                }
            )

        except anthropic.APIError as e:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Claude API error: {str(e)}",
                    "error_type": "api_error",
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Unexpected error: {str(e)}",
                    "error_type": "general_error",
                }
            )

    def _build_prompt(
        self,
        task: str,
        language: str,
        context: str,
        existing_code: str,
        include_tests: bool,
        include_docs: bool,
        repo_context: str = "",
    ) -> str:
        """Build a comprehensive prompt for Claude with repository context"""

        # Build agent context
        agent_info = ""
        if self.agent_id and self.task_id:
            agent_info = f"""
**Agent Context**:
- Agent ID: {self.agent_id}
- Task ID: {self.task_id}
- Iteration: {self.repository_context['iteration_count']}
- Workspace: {self.workspace_path}
"""

        prompt = f"""
You are an expert {language} developer working autonomously as part of FuzeAgent AI team. I need you to complete the following coding task:

{agent_info}

**Task**: {task}

**Programming Language**: {language}

**Additional Context**: {context}

{repo_context}

**Existing Code** (if any):
```{language}
{existing_code}
```

**Requirements**:
1. Write clean, maintainable, and well-documented code
2. Follow {language} best practices and conventions
3. Include proper error handling
4. Use type hints (where applicable)
5. {"Include comprehensive unit tests" if include_tests else "Focus only on implementation"}
6. {"Include docstrings and comments" if include_docs else "Minimal documentation"}
7. Consider the repository context and maintain consistency with existing code
8. Write code that integrates well with the current branch and recent changes

**Output Format**:
Please structure your response as follows:

## Explanation
Brief explanation of your approach and key decisions, considering the repository context.

## Implementation

### Main Code
```{language}
# Your main implementation here
```

{"### Tests" if include_tests else ""}
{f"```{language}" if include_tests else ""}
{"# Your test code here" if include_tests else ""}
{f"```" if include_tests else ""}

{"### Documentation" if include_docs else ""}
{"```markdown" if include_docs else ""}
{"# Your documentation here" if include_docs else ""}
{f"```" if include_docs else ""}

## Commit Message
Suggest a concise git commit message for these changes that follows the repository's commit history style.

Please ensure the code is production-ready and follows industry standards.
"""
        return prompt

    def _parse_response(
        self, response: str, language: str, include_tests: bool, include_docs: bool
    ) -> Dict[str, Any]:
        """Parse Claude's response and extract code files"""

        files = []
        explanation = ""
        commit_message = ""

        # Extract explanation
        if "## Explanation" in response:
            explanation_start = response.find("## Explanation") + len("## Explanation")
            explanation_end = response.find("## Implementation")
            if explanation_end > explanation_start:
                explanation = response[explanation_start:explanation_end].strip()

        # Extract commit message
        if "## Commit Message" in response:
            commit_start = response.find("## Commit Message") + len("## Commit Message")
            commit_message = response[commit_start:].strip()
            # Clean up the commit message
            commit_message = commit_message.split("\n")[0].strip()

        # Extract main code
        main_code = self._extract_code_block(response, "### Main Code", language)
        if main_code:
            file_ext = self._get_file_extension(language)
            files.append(
                {
                    "filename": f"main.{file_ext}",
                    "content": main_code,
                    "type": "implementation",
                    "language": language,
                }
            )

        # Extract tests if requested
        if include_tests:
            test_code = self._extract_code_block(response, "### Tests", language)
            if test_code:
                test_ext = self._get_file_extension(language)
                files.append(
                    {
                        "filename": f"test_main.{test_ext}",
                        "content": test_code,
                        "type": "test",
                        "language": language,
                    }
                )

        # Extract documentation if requested
        if include_docs:
            docs = self._extract_code_block(response, "### Documentation", "markdown")
            if docs:
                files.append(
                    {
                        "filename": "README.md",
                        "content": docs,
                        "type": "documentation",
                        "language": "markdown",
                    }
                )

        return {
            "files": files,
            "explanation": explanation,
            "commit_message": commit_message,
        }

    def _extract_code_block(
        self, text: str, section: str, language: str
    ) -> Optional[str]:
        """Extract code block from a specific section"""

        section_start = text.find(section)
        if section_start == -1:
            return None

        # Find the start of the code block
        code_start = text.find(f"```{language}", section_start)
        if code_start == -1:
            code_start = text.find("```", section_start)
            if code_start == -1:
                return None

        # Find the end of the code block
        code_content_start = text.find("\n", code_start) + 1
        code_end = text.find("```", code_content_start)

        if code_end == -1:
            return None

        return text[code_content_start:code_end].strip()

    def _get_file_extension(self, language: str) -> str:
        """Get appropriate file extension for language"""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "rust": "rs",
            "go": "go",
            "ruby": "rb",
            "php": "php",
            "swift": "swift",
            "kotlin": "kt",
            "scala": "scala",
            "r": "R",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "shell": "sh",
            "bash": "sh",
        }
        return extensions.get(language.lower(), "txt")

    def _save_files(self, files: List[Dict], tmpdir: str) -> List[str]:
        """Save generated files to temporary directory"""
        saved_files = []

        for file_info in files:
            file_path = os.path.join(tmpdir, file_info["filename"])
            with open(file_path, "w") as f:
                f.write(file_info["content"])
            saved_files.append(file_path)

        return saved_files

    def _run_tests(self, tmpdir: str, language: str) -> Optional[Dict[str, Any]]:
        """Run tests for the generated code"""

        try:
            if language == "python":
                # Try to run pytest
                result = subprocess.run(  # nosec B603 B607 -- fixed command list, no shell, no user input
                    ["python", "-m", "pytest", tmpdir, "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )

                return {
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                }
            elif language == "javascript":
                # Try to run with node
                test_files = [f for f in os.listdir(tmpdir) if f.startswith("test_")]
                if test_files:
                    result = subprocess.run(  # nosec B603 B607 -- fixed command list, no shell, no user input
                        ["node", test_files[0]],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=tmpdir,
                    )

                    return {
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "success": result.returncode == 0,
                    }

            return None

        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out",
                "success": False,
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Test execution error: {str(e)}",
                "success": False,
            }

    def _build_repository_context(
        self, branch_status: Dict[str, Any], commit_history: List[Any]
    ) -> str:
        """Build repository context string for the prompt"""
        context_parts = ["**Repository Context**:"]

        if branch_status:
            current_branch = branch_status.get("current_branch", "unknown")
            feature_branch = branch_status.get("feature_branch")
            has_changes = branch_status.get("has_uncommitted_changes", False)
            remote_status = branch_status.get("remote_status", "unknown")

            context_parts.append(f"- Current Branch: `{current_branch}`")
            if feature_branch:
                context_parts.append(f"- Feature Branch: `{feature_branch}`")
            context_parts.append(
                f"- Uncommitted Changes: {'Yes' if has_changes else 'No'}"
            )
            context_parts.append(f"- Remote Status: {remote_status}")

        if commit_history:
            context_parts.append("- Recent Commits:")
            for i, commit in enumerate(commit_history[:3]):
                context_parts.append(f"  {i+1}. `{commit.hash[:8]}` - {commit.message}")
                if commit.files_changed:
                    context_parts.append(
                        f"     Files: {', '.join(commit.files_changed[:5])}"
                    )

        if self.repository_context.get("files_changed"):
            changed_files = list(set(self.repository_context["files_changed"]))
            context_parts.append(
                f"- Files Modified This Session: {', '.join(changed_files)}"
            )

        return "\n".join(context_parts) + "\n"

    def _save_files_to_workspace(self, files: List[Dict]) -> List[str]:
        """Save generated files directly to workspace"""
        saved_files = []

        for file_info in files:
            file_path = os.path.join(self.workspace_path, file_info["filename"])

            # Create directory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w") as f:
                f.write(file_info["content"])
            saved_files.append(file_path)

        return saved_files

    async def commit_and_push_changes(
        self, commit_message: str, files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Commit and push changes using Git manager"""
        if not self.git_manager:
            return {"success": False, "error": "No Git manager available"}

        try:
            # Commit changes
            commit_hash = await self.git_manager.commit_changes(
                message=commit_message,
                files=files,
                iteration_number=self.repository_context["iteration_count"],
            )

            if commit_hash:
                self.repository_context["last_commit"] = commit_message
                return {
                    "success": True,
                    "commit_hash": commit_hash,
                    "message": "Changes committed successfully",
                }
            else:
                return {"success": True, "message": "No changes to commit"}

        except Exception as e:
            return {"success": False, "error": f"Failed to commit changes: {str(e)}"}

    def get_repository_context(self) -> Dict[str, Any]:
        """Get current repository context"""
        return self.repository_context.copy()

    def reset_context(self):
        """Reset the repository context"""
        self.repository_context = {
            "files_changed": [],
            "current_branch": None,
            "last_commit": None,
            "iteration_count": 0,
        }

    async def start_conversation_session(self, sandbox_id: str) -> str:
        """Start a conversation session for tracking all Claude Code interactions"""
        if not self.agent_id or not self.task_id:
            raise ValueError("Agent ID and Task ID required for conversation tracking")

        self.conversation_session_id = (
            await self.conversation_manager.start_conversation_session(
                agent_id=self.agent_id,
                task_id=self.task_id,
                sandbox_id=sandbox_id,
                metadata={
                    "workspace_path": self.workspace_path,
                    "model": self.model,
                    "git_enabled": bool(self.git_manager),
                },
            )
        )
        return self.conversation_session_id

    async def end_conversation_session(self) -> bool:
        """End the current conversation session"""
        if not self.conversation_session_id:
            return False

        success = await self.conversation_manager.end_conversation_session(
            self.conversation_session_id
        )
        self.conversation_session_id = None
        return success

    async def execute_task_async(
        self,
        task: str,
        language: str = "python",
        context: str = "",
        include_tests: bool = True,
        include_docs: bool = True,
        file_path: Optional[str] = None,
        iteration_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Async version of task execution with full conversation tracking"""

        try:
            # Update iteration count
            if iteration_number:
                self.repository_context["iteration_count"] = iteration_number
            else:
                self.repository_context["iteration_count"] += 1

            current_iteration = self.repository_context["iteration_count"]

            # Get repository context if Git manager is available
            repo_context = ""
            if self.git_manager:
                try:
                    branch_status = await self.git_manager.get_branch_status()
                    self.repository_context["current_branch"] = branch_status.get(
                        "current_branch"
                    )

                    commit_history = await self.git_manager.get_commit_history(limit=3)
                    if commit_history:
                        self.repository_context["last_commit"] = commit_history[
                            0
                        ].message

                    repo_context = self._build_repository_context(
                        branch_status, commit_history
                    )
                except Exception as e:
                    repo_context = f"Repository context unavailable: {str(e)}"

            # Read existing file context if provided
            existing_code = ""
            if file_path:
                # Use workspace-relative path if available
                full_path = (
                    os.path.join(self.workspace_path, file_path)
                    if not os.path.isabs(file_path)
                    else file_path
                )
                if os.path.exists(full_path):
                    with open(full_path, "r") as f:
                        existing_code = f.read()

            # Prepare the comprehensive prompt with repository context
            prompt = self._build_prompt(
                task=task,
                language=language,
                context=context,
                existing_code=existing_code,
                include_tests=include_tests,
                include_docs=include_docs,
                repo_context=repo_context,
            )

            # Store user prompt in conversation history
            if self.conversation_session_id and self.task_id:
                await self.conversation_manager.store_user_prompt(
                    session_id=self.conversation_session_id,
                    task_id=self.task_id,
                    iteration_number=current_iteration,
                    prompt=prompt,
                    model=self.model,
                    temperature=0.3,
                    metadata={
                        "task_description": (
                            task[:200] + "..." if len(task) > 200 else task
                        ),
                        "language": language,
                        "include_tests": include_tests,
                        "include_docs": include_docs,
                        "file_path": file_path,
                        "workspace_path": self.workspace_path,
                    },
                )

            # Record start time for response time tracking
            start_time = time.time()

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,  # Lower temperature for more consistent code
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response content and token usage
            response_content = response.content[0].text
            token_count = (
                getattr(response.usage, "output_tokens", None)
                if hasattr(response, "usage")
                else None
            )

            # Store Claude response in conversation history
            if self.conversation_session_id and self.task_id:
                await self.conversation_manager.store_claude_response(
                    session_id=self.conversation_session_id,
                    task_id=self.task_id,
                    iteration_number=current_iteration,
                    response=response_content,
                    token_count=token_count,
                    model=self.model,
                    start_time=start_time,
                    metadata={
                        "prompt_length": len(prompt),
                        "response_length": len(response_content),
                    },
                )

            # Parse the response and extract code files
            result = self._parse_response(
                response_content, language, include_tests, include_docs
            )

            # Save files to workspace if available
            saved_files = []
            if self.workspace_path and os.path.exists(self.workspace_path):
                saved_files = self._save_files_to_workspace(result["files"])

                # Store code generations in database
                if self.task_id:
                    for file_info in result["files"]:
                        await self.conversation_manager.store_code_generation(
                            task_id=self.task_id,
                            iteration_number=current_iteration,
                            file_path=file_info["filename"],
                            file_type=file_info["type"],
                            language=file_info.get("language", language),
                            content=file_info["content"],
                        )

            # Update repository context with changed files
            self.repository_context["files_changed"].extend(
                [
                    f["filename"]
                    for f in result["files"]
                    if f["type"] == "implementation"
                ]
            )

            # Run tests if generated and in workspace
            test_results = None
            if include_tests and any(f["type"] == "test" for f in result["files"]):
                if self.workspace_path and os.path.exists(self.workspace_path):
                    test_results = self._run_tests(self.workspace_path, language)

                    # Store test results
                    if self.conversation_session_id and self.task_id:
                        await self.conversation_manager.store_message(
                            session_id=self.conversation_session_id,
                            message={
                                "task_id": self.task_id,
                                "iteration_number": current_iteration,
                                "message_type": MessageType.TEST_RESULT,
                                "content": json.dumps(test_results),
                                "metadata": {
                                    "test_framework": (
                                        "pytest" if language == "python" else "jest"
                                    ),
                                    "workspace_path": self.workspace_path,
                                },
                            },
                        )

            return {
                "status": "success",
                "files": result["files"],
                "saved_files": saved_files,
                "explanation": result.get("explanation", ""),
                "test_results": test_results,
                "commit_message": result.get("commit_message", ""),
                "execution_summary": f"Generated {len(result['files'])} files for {language} task: {task[:100]}...",
                "iteration": current_iteration,
                "workspace_path": self.workspace_path,
                "repository_context": self.repository_context,
                "conversation_tracked": bool(self.conversation_session_id),
                "token_count": token_count,
            }

        except Exception as e:
            # Store error in conversation history
            if self.conversation_session_id and self.task_id:
                try:
                    await self.conversation_manager.store_message(
                        session_id=self.conversation_session_id,
                        message={
                            "task_id": self.task_id,
                            "iteration_number": self.repository_context[
                                "iteration_count"
                            ],
                            "message_type": MessageType.ERROR_MESSAGE,
                            "content": str(e),
                            "metadata": {
                                "error_type": type(e).__name__,
                                "task_description": (
                                    task[:200] + "..." if len(task) > 200 else task
                                ),
                            },
                        },
                    )
                except Exception as conv_error:
                    # Don't let conversation storage errors break the main flow
                    print(
                        f"Warning: Failed to store error in conversation: {conv_error}"
                    )

            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error",
                "iteration": self.repository_context["iteration_count"],
                "conversation_tracked": bool(self.conversation_session_id),
            }
