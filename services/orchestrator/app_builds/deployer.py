"""The ``AppDeployer`` adapter: the seam where an app is actually built and deployed.

FuzeAgent has NO general "develop an app from a brief and deploy it" primitive today:
``kaniko_builder.py`` builds an image from a ready Dockerfile and nothing deploys it, and
agent task execution does not produce a deployable, registry-ready service. Rather than fake
a deploy, the default adapter is :class:`NotConfiguredDeployer`, which fails closed — the
session reports ``failed`` with ``errorCode=deployer_unavailable``.

An implementation must be **idempotent on ``ctx.build_session_id``**: after a pod restart the
runtime re-invokes any step whose result was not yet persisted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DeployContext:
    build_session_id: str
    agent_session_ref: str
    organization_id: (
        str  # prefixed TypeID; the ONLY org the app may be deployed/registered into
    )
    requested_by_user_id: str
    context: str
    name: str
    brief: str


@dataclass(frozen=True)
class DeployResult:
    #: FuzeFront manifest ``integration`` block for the deployed app.
    integration: Dict[str, Any]
    description: Optional[str] = None


class DeployError(Exception):
    """A build/deploy failure with a stable, machine-readable ``code``."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class DeployerUnavailable(DeployError):
    def __init__(
        self, message: str = "No app deployer is configured on this FuzeAgent"
    ):
        super().__init__("deployer_unavailable", message)


class AppDeployer(ABC):
    @abstractmethod
    async def build(self, ctx: DeployContext) -> Dict[str, Any]:
        """Develop the app from ``ctx.brief`` and build its artifact (JSON-serialisable)."""

    @abstractmethod
    async def deploy(
        self, ctx: DeployContext, artifact: Dict[str, Any]
    ) -> DeployResult:
        """Deploy the artifact; return the integration the registry manifest needs."""

    async def cancel(self, ctx: DeployContext) -> None:  # best effort, optional
        return None


class NotConfiguredDeployer(AppDeployer):
    async def build(self, ctx: DeployContext) -> Dict[str, Any]:
        raise DeployerUnavailable()

    async def deploy(
        self, ctx: DeployContext, artifact: Dict[str, Any]
    ) -> DeployResult:
        raise DeployerUnavailable()
