"""
Git Workflow Manager for FuzeAgent Autonomous Execution

Manages Git operations for agent development tasks including:
- Repository cloning and setup
- Feature branch creation and management
- Commit tracking and history
- Pull request creation
- Merge conflict handling
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Represents a git commit"""

    hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: List[str]


@dataclass
class GitBranch:
    """Represents a git branch"""

    name: str
    is_current: bool
    commit_hash: str
    upstream: Optional[str] = None


@dataclass
class PullRequest:
    """Represents a pull request"""

    number: int
    title: str
    url: str
    branch: str
    status: str
    created_at: datetime


class GitWorkflowManager:
    """
    Manages Git workflows for agent development tasks.

    Features:
    - Secure credential handling
    - Repository cloning and branching
    - Atomic commits with descriptive messages
    - Pull request automation
    - Conflict detection and resolution
    """

    def __init__(self, agent_id: str, task_id: str, repo_settings: Dict[str, Any]):
        self.agent_id = agent_id
        self.task_id = task_id
        self.repo_url = repo_settings.get("repository_url")
        self.default_branch = repo_settings.get("default_branch", "main")
        self.workspace_path = repo_settings.get(
            "workspace_path", f"/workspaces/{task_id}"
        )
        self.auto_create_pr = repo_settings.get("auto_create_pr", True)
        self.require_review = repo_settings.get("require_review", True)

        # Git configuration
        self.git_user_name = f"FuzeAgent-{agent_id[:8]}"
        self.git_user_email = f"agent-{agent_id}@fuzeagent.ai"

        # Encrypted token handling
        self.encryption_key = os.environ.get(
            "FUZE_ENCRYPTION_KEY", Fernet.generate_key()
        )
        if isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()
        self.fernet = Fernet(self.encryption_key)

        # Decrypt GitHub token
        encrypted_token = repo_settings.get("github_token")
        if encrypted_token:
            try:
                self.github_token = self._decrypt_token(encrypted_token)
            except Exception as e:
                logger.error(f"Failed to decrypt GitHub token: {e}")
                self.github_token = encrypted_token  # Fallback to plaintext (dev only)
        else:
            self.github_token = os.environ.get("GITHUB_TOKEN")

        # Current branch tracking
        self.current_branch: Optional[str] = None
        self.feature_branch: Optional[str] = None

    async def setup_workspace(self) -> str:
        """
        Set up Git workspace for the task.
        Returns the feature branch name.
        """
        logger.info(f"Setting up Git workspace for task {self.task_id}")

        try:
            # Create workspace directory
            workspace = Path(self.workspace_path)
            workspace.mkdir(parents=True, exist_ok=True)

            # Clone repository if it doesn't exist
            git_dir = workspace / ".git"
            if not git_dir.exists():
                await self._clone_repository()
            else:
                # Update existing repository
                await self._update_repository()

            # Configure Git
            await self._configure_git()

            # Create feature branch
            branch_name = await self._create_feature_branch()
            self.feature_branch = branch_name

            logger.info(f"✅ Git workspace ready on branch: {branch_name}")
            return branch_name

        except Exception as e:
            logger.error(f"❌ Failed to setup Git workspace: {e}")
            raise

    async def commit_changes(
        self,
        message: str,
        files: Optional[List[str]] = None,
        iteration_number: Optional[int] = None,
    ) -> str:
        """
        Commit changes with descriptive message.
        Returns the commit hash.
        """
        try:
            # Stage files
            if files:
                for file_path in files:
                    await self._run_git_command(["add", file_path])
            else:
                await self._run_git_command(["add", "."])

            # Check if there are changes to commit
            result = await self._run_git_command(["diff", "--staged", "--name-only"])
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return ""

            # Create commit message
            full_message = self._build_commit_message(message, iteration_number)

            # Commit changes
            await self._run_git_command(["commit", "-m", full_message])

            # Get commit hash
            result = await self._run_git_command(["rev-parse", "HEAD"])
            commit_hash = result.stdout.strip()

            logger.info(f"✅ Committed changes: {commit_hash[:8]} - {message}")
            return commit_hash

        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stderr:
                logger.info("No changes to commit")
                return ""
            else:
                logger.error(f"❌ Failed to commit changes: {e.stderr}")
                raise

    async def push_branch(self) -> bool:
        """Push the current feature branch to remote"""
        if not self.feature_branch:
            raise ValueError("No feature branch to push")

        try:
            # Push to remote
            await self._run_git_command(
                ["push", "--set-upstream", "origin", self.feature_branch]
            )

            logger.info(f"✅ Pushed branch {self.feature_branch} to remote")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to push branch: {e.stderr}")
            return False

    async def create_pull_request(
        self, title: str, description: str, target_branch: Optional[str] = None
    ) -> Optional[PullRequest]:
        """Create a pull request using GitHub CLI"""
        if not self.feature_branch:
            raise ValueError("No feature branch for pull request")

        target_branch = target_branch or self.default_branch

        try:
            # Push branch first
            await self.push_branch()

            # Create PR using GitHub CLI
            pr_title = f"🤖 {title}"
            pr_body = self._build_pr_description(description)

            result = await self._run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    pr_title,
                    "--body",
                    pr_body,
                    "--base",
                    target_branch,
                    "--head",
                    self.feature_branch,
                ]
            )

            # Parse PR URL from output
            pr_url = result.stdout.strip()

            # Get PR details
            pr_info = await self._get_pr_info(pr_url)

            logger.info(f"✅ Created pull request: {pr_url}")
            return pr_info

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to create pull request: {e.stderr}")
            return None

    async def get_commit_history(self, limit: int = 10) -> List[GitCommit]:
        """Get commit history for the current branch"""
        try:
            # Get commit information
            result = await self._run_git_command(
                [
                    "log",
                    f"--max-count={limit}",
                    "--pretty=format:%H|%s|%an|%ai",
                    self.feature_branch or "HEAD",
                ]
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commit_hash, message, author, timestamp = parts

                    # Get files changed in this commit
                    files_result = await self._run_git_command(
                        [
                            "diff-tree",
                            "--no-commit-id",
                            "--name-only",
                            "-r",
                            commit_hash,
                        ]
                    )
                    files_changed = [
                        f.strip() for f in files_result.stdout.split("\n") if f.strip()
                    ]

                    commits.append(
                        GitCommit(
                            hash=commit_hash,
                            message=message,
                            author=author,
                            timestamp=datetime.fromisoformat(
                                timestamp.replace(" ", "T")
                            ),
                            files_changed=files_changed,
                        )
                    )

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to get commit history: {e.stderr}")
            return []

    async def get_branch_status(self) -> Dict[str, Any]:
        """Get current branch status and information"""
        try:
            # Get current branch
            result = await self._run_git_command(["branch", "--show-current"])
            current_branch = result.stdout.strip()

            # Get branch list
            result = await self._run_git_command(["branch", "-v"])
            branches = []
            for line in result.stdout.split("\n"):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        is_current = line.startswith("*")
                        branch_name = parts[1] if is_current else parts[0]
                        commit_hash = parts[2] if is_current else parts[1]

                        branches.append(
                            GitBranch(
                                name=branch_name,
                                is_current=is_current,
                                commit_hash=commit_hash,
                            )
                        )

            # Check for uncommitted changes
            result = await self._run_git_command(["status", "--porcelain"])
            has_changes = bool(result.stdout.strip())

            # Get remote status
            try:
                await self._run_git_command(["fetch", "origin", "--dry-run"])
                result = await self._run_git_command(["status", "-uno"])
                remote_status = "up-to-date"
                if "ahead" in result.stdout:
                    remote_status = "ahead"
                elif "behind" in result.stdout:
                    remote_status = "behind"
                elif "diverged" in result.stdout:
                    remote_status = "diverged"
            except:
                remote_status = "unknown"

            return {
                "current_branch": current_branch,
                "feature_branch": self.feature_branch,
                "branches": branches,
                "has_uncommitted_changes": has_changes,
                "remote_status": remote_status,
                "workspace_path": self.workspace_path,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to get branch status: {e.stderr}")
            return {}

    async def cleanup_workspace(self):
        """Clean up the workspace and remove feature branch"""
        try:
            # Switch to default branch
            await self._run_git_command(["checkout", self.default_branch])

            # Delete feature branch locally
            if self.feature_branch:
                await self._run_git_command(["branch", "-D", self.feature_branch])

                # Delete remote branch (optional)
                try:
                    await self._run_git_command(
                        ["push", "origin", "--delete", self.feature_branch]
                    )
                except subprocess.CalledProcessError:
                    # Remote branch might not exist or already deleted
                    pass

            logger.info(f"✅ Cleaned up Git workspace")

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to cleanup workspace: {e.stderr}")

    # Private methods

    async def _clone_repository(self):
        """Clone the repository to workspace"""
        # Prepare authenticated URL
        if self.github_token and "github.com" in self.repo_url:
            auth_url = self.repo_url.replace(
                "https://github.com/", f"https://{self.github_token}@github.com/"
            )
        else:
            auth_url = self.repo_url

        await self._run_command(["git", "clone", auth_url, self.workspace_path])

    async def _update_repository(self):
        """Update existing repository"""
        await self._run_git_command(["fetch", "origin"])
        await self._run_git_command(["checkout", self.default_branch])
        await self._run_git_command(["pull", "origin", self.default_branch])

    async def _configure_git(self):
        """Configure Git user settings"""
        await self._run_git_command(["config", "user.name", self.git_user_name])
        await self._run_git_command(["config", "user.email", self.git_user_email])

        # Configure GitHub token for authenticated operations
        if self.github_token:
            await self._run_git_command(
                [
                    "config",
                    "credential.helper",
                    f"!echo username={self.github_token}; echo password=",
                ]
            )

    async def _create_feature_branch(self) -> str:
        """Create and checkout feature branch"""
        branch_name = f"feature/agent-{self.agent_id[:8]}-task-{self.task_id[:8]}"

        try:
            # Check if branch already exists
            result = await self._run_git_command(["branch", "--list", branch_name])
            if result.stdout.strip():
                # Branch exists, checkout and update
                await self._run_git_command(["checkout", branch_name])
                await self._run_git_command(["rebase", self.default_branch])
            else:
                # Create new branch
                await self._run_git_command(["checkout", "-b", branch_name])

        except subprocess.CalledProcessError:
            # If rebase fails, create a new branch with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = (
                f"feature/agent-{self.agent_id[:8]}-task-{self.task_id[:8]}-{timestamp}"
            )
            await self._run_git_command(["checkout", "-b", branch_name])

        return branch_name

    def _build_commit_message(
        self, message: str, iteration: Optional[int] = None
    ) -> str:
        """Build a descriptive commit message"""
        prefix = "🤖"
        if iteration:
            prefix += f" Iteration {iteration}:"

        full_message = f"""{prefix} {message}

Agent: {self.agent_id[:8]}
Task: {self.task_id[:8]}
Timestamp: {datetime.now().isoformat()}

Generated by FuzeAgent autonomous development system.
"""
        return full_message

    def _build_pr_description(self, description: str) -> str:
        """Build pull request description"""
        return f"""{description}

## 🤖 Autonomous Development Details

- **Agent ID**: `{self.agent_id}`
- **Task ID**: `{self.task_id}`  
- **Branch**: `{self.feature_branch}`
- **Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

## 🔍 Review Checklist

- [ ] Code follows project conventions
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No sensitive information exposed
- [ ] Performance impact considered

---
*This pull request was generated automatically by FuzeAgent.*
"""

    async def _get_pr_info(self, pr_url: str) -> PullRequest:
        """Get pull request information"""
        try:
            # Extract PR number from URL
            pr_number = int(pr_url.split("/")[-1])

            # Get PR details using GitHub CLI
            result = await self._run_command(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "title,url,headRefName,state,createdAt",
                ]
            )

            pr_data = json.loads(result.stdout)

            return PullRequest(
                number=pr_number,
                title=pr_data["title"],
                url=pr_data["url"],
                branch=pr_data["headRefName"],
                status=pr_data["state"],
                created_at=datetime.fromisoformat(
                    pr_data["createdAt"].replace("Z", "+00:00")
                ),
            )

        except Exception as e:
            logger.error(f"Failed to get PR info: {e}")
            # Return basic info
            return PullRequest(
                number=0,
                title="Unknown",
                url=pr_url,
                branch=self.feature_branch or "unknown",
                status="unknown",
                created_at=datetime.now(),
            )

    async def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run git command in workspace directory"""
        return await self._run_command(["git"] + args, cwd=self.workspace_path)

    async def _run_command(
        self, args: List[str], cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Run shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd or self.workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "GITHUB_TOKEN": self.github_token or ""},
        )

        stdout, stderr = await process.communicate()

        result = subprocess.CompletedProcess(
            args=args,
            returncode=process.returncode,
            stdout=stdout.decode("utf-8"),
            stderr=stderr.decode("utf-8"),
        )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, args, result.stdout, result.stderr
            )

        return result

    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return base64.b64encode(self.fernet.encrypt(token.encode())).decode()

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a stored token"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_token.encode())
            return self.fernet.decrypt(encrypted_bytes).decode()
        except Exception:
            # If decryption fails, assume it's already plaintext (dev mode)
            return encrypted_token
