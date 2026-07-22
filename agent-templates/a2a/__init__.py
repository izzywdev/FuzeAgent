"""Shared A2A server + Agent Card generator for the Fuze family.

This package implements the CALLEE side of the frozen A2A contract v1
(``agent-templates/contracts/a2a/v1``). It is a thin ADAPTER over the existing
Managed-Agents runtime (``agent-templates/providers`` + ``orchestration``): A2A wire
objects in, provider calls out, provider results mapped back to A2A objects. There is
no new task engine here — see ``contracts/a2a/v1/state-mapping.md``.

Modules:
    card_generator  -- projects .fuze/manifest.json + roles/*/role.json -> AgentCard
    task_mapper     -- run_until_block result -> A2A Task/TaskStatus (the core table)
    authz           -- callee-enforced allowlist decision (providesTo, fail-closed)
    adapter         -- wire method dispatch onto an AgentProvider
    server          -- Starlette JSON-RPC 2.0 + SSE transport
"""
from __future__ import annotations

__version__ = "1.0.0"
