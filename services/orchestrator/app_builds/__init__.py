"""FuzeFront "build your application" API (see docs/app-builds.md)."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from .config import Settings
from .deployer import (
    AppDeployer,
    DeployContext,
    DeployError,
    DeployerUnavailable,
    DeployResult,
    NotConfiguredDeployer,
)
from .router import get_runtime, router, set_runtime
from .runtime import BuildRuntime
from .store import BuildStore, InMemoryBuildStore, PostgresBuildStore

logger = logging.getLogger(__name__)

__all__ = [
    "router",
    "BuildRuntime",
    "AppDeployer",
    "DeployContext",
    "DeployResult",
    "DeployError",
    "DeployerUnavailable",
    "NotConfiguredDeployer",
    "Settings",
    "BuildStore",
    "InMemoryBuildStore",
    "PostgresBuildStore",
    "start_app_builds",
    "stop_app_builds",
    "get_runtime",
    "set_runtime",
]


from .sandbox_deployer import KubernetesSandboxDeployer


async def start_app_builds(
    connect: Callable[[], Any], deployer: Optional[AppDeployer] = None
) -> BuildRuntime:
    """Wire the Postgres-backed runtime into the process and resume unfinished sessions.

    ``connect`` is ``database.get_db_connection``. Safe to call with the feature flag OFF: the
    router answers 503 and the loops only touch an (empty) table."""
    active_deployer = deployer or KubernetesSandboxDeployer()
    runtime = BuildRuntime(
        PostgresBuildStore(connect),
        active_deployer,
        settings=Settings.from_env(),
    )
    set_runtime(runtime)
    await runtime.start()
    logger.info(
        "app_builds runtime started deployer=%s", type(runtime.deployer).__name__
    )
    return runtime


async def stop_app_builds() -> None:
    runtime = get_runtime()
    if runtime is not None:
        await runtime.stop()
        set_runtime(None)
