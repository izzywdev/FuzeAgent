"""
Image Template Registry, Sandboxes, Brains & Escalations API Router for FuzeAgent.
Provides REST and WebSocket-backed interfaces for:
1. Agent Image Templates (Dockerfiles, FuzeKeys secrets, timeouts, eventBus)
2. Live Sandboxes monitoring and lifecycle (spawn, list, stop)
3. 5-Tier Brains & Memory hierarchy management and RAG retrieval
4. Human-in-the-loop decision escalation approval
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent-platform"])

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class SecretBinding(BaseModel):
    keyName: str
    secretRef: str
    description: Optional[str] = ""

class SandboxSettings(BaseModel):
    defaultTimeoutSeconds: int = 1800
    cpuLimit: str = "2.0"
    memoryLimit: str = "4Gi"
    networkIsolation: str = "outbound-only"
    autoShutdownOnIdle: bool = True

class EventBusSettings(BaseModel):
    enabled: bool = True
    channel: str
    streamLlmChunks: bool = True
    wsRelayUrl: str

class EscalationSettings(BaseModel):
    requiresApprovalForDestructive: bool = True
    costThresholdUsd: float = 5.0
    escalateTo: str = "human"

class ImageTemplateModel(BaseModel):
    id: str
    name: str
    category: str
    role: str
    image: str
    description: str
    dockerfile: str
    envVars: Dict[str, str] = Field(default_factory=dict)
    fuzeKeysSecrets: List[SecretBinding] = Field(default_factory=list)
    setupScript: str
    sandboxing: SandboxSettings
    eventBus: EventBusSettings
    escalation: EscalationSettings
    status: str = "ready"

class SandboxLaunchRequest(BaseModel):
    templateId: str
    agentName: Optional[str] = None
    timeoutSeconds: Optional[int] = None
    envOverrides: Optional[Dict[str, str]] = None

class EscalationResolutionRequest(BaseModel):
    decision: str = Field(..., description="'approved' or 'rejected'")
    notes: Optional[str] = None
    approverId: Optional[str] = "admin"

class BrainQueryRequest(BaseModel):
    query: str
    agentId: Optional[str] = None
    teamId: Optional[str] = None
    orgId: Optional[str] = None
    userId: Optional[str] = None
    tiers: Optional[List[str]] = None

# ---------------------------------------------------------------------------
# In-Memory Platform Registry State
# ---------------------------------------------------------------------------

TEMPLATES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "python-dev-v2": {
        "id": "python-dev-v2",
        "name": "Python FastAPI & ML Specialist",
        "category": "development",
        "role": "Backend & AI Engineer",
        "image": "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
        "description": "Hardened container with Python 3.12, PyTorch, FastAPI, asyncpg, and pre-warmed toolchains.",
        "dockerfile": """# syntax=docker/dockerfile:1\nFROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest\nUSER root\nRUN apt-get update && apt-get install -y python3.12 python3.12-venv python3-pip libpq-dev git\nRUN pip install --no-cache-dir fastapi uvicorn asyncpg pydantic anthropic\nCOPY session-relay.sh /usr/local/bin/session-relay\nRUN chmod +x /usr/local/bin/session-relay\nUSER agent\nWORKDIR /home/agent/workspace\nCMD [\"/usr/local/bin/session-relay\"]""",
        "envVars": {
            "PYTHONUNBUFFERED": "1",
            "LOG_LEVEL": "INFO",
            "FUZE_STREAM_FORMAT": "sse-jsonl",
            "MAX_CONCURRENT_TASKS": "4"
        },
        "fuzeKeysSecrets": [
            {"keyName": "ANTHROPIC_API_KEY", "secretRef": "fk_sec_anthropic_prod", "description": "Anthropic LLM Token via FuzeKeys API"},
            {"keyName": "DATABASE_URL", "secretRef": "fk_sec_postgres_context", "description": "PostgreSQL Vector DB Connection URI"}
        ],
        "setupScript": "#!/bin/bash\necho '⚡ Initializing Python Developer Environment...'\nexec /usr/local/bin/session-relay \"$@\"",
        "sandboxing": {
            "defaultTimeoutSeconds": 1800,
            "cpuLimit": "2.0",
            "memoryLimit": "4Gi",
            "networkIsolation": "outbound-only",
            "autoShutdownOnIdle": True
        },
        "eventBus": {
            "enabled": True,
            "channel": "agent.stream.python-dev-v2",
            "streamLlmChunks": True,
            "wsRelayUrl": "wss://fuzeagent.prod.fuzefront.com/ws/stream"
        },
        "escalation": {
            "requiresApprovalForDestructive": True,
            "costThresholdUsd": 5.0,
            "escalateTo": "human"
        },
        "status": "ready"
    },
    "react-dev-v2": {
        "id": "react-dev-v2",
        "name": "React & Frontend UI Specialist",
        "category": "development",
        "role": "Frontend Architect",
        "image": "ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest",
        "description": "Pre-configured Node.js 24 environment with Vite, Tailwind CSS, TypeScript, and Playwright browser sandbox.",
        "dockerfile": """# syntax=docker/dockerfile:1\nFROM ghcr.io/izzywdev/fuzeagent/claude-runner-base:latest\nUSER root\nRUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && apt-get install -y nodejs git\nRUN npm install -g typescript vite @playwright/test\nCOPY session-relay.sh /usr/local/bin/session-relay\nRUN chmod +x /usr/local/bin/session-relay\nUSER agent\nWORKDIR /home/agent/workspace\nCMD [\"/usr/local/bin/session-relay\"]""",
        "envVars": {
            "NODE_ENV": "development",
            "VITE_HOST": "0.0.0.0",
            "PORT": "3000"
        },
        "fuzeKeysSecrets": [
            {"keyName": "GITHUB_ACCESS_TOKEN", "secretRef": "fk_sec_github_repo_bot", "description": "GitHub Deployment & PR Access Token"}
        ],
        "setupScript": "#!/bin/bash\necho '⚛️ Booting React UI Engineering Workspace...'\nexec /usr/local/bin/session-relay \"$@\"",
        "sandboxing": {
            "defaultTimeoutSeconds": 2400,
            "cpuLimit": "2.0",
            "memoryLimit": "4Gi",
            "networkIsolation": "outbound-only",
            "autoShutdownOnIdle": True
        },
        "eventBus": {
            "enabled": True,
            "channel": "agent.stream.react-dev-v2",
            "streamLlmChunks": True,
            "wsRelayUrl": "wss://fuzeagent.prod.fuzefront.com/ws/stream"
        },
        "escalation": {
            "requiresApprovalForDestructive": True,
            "costThresholdUsd": 5.0,
            "escalateTo": "human"
        },
        "status": "ready"
    }
}

ACTIVE_SANDBOXES: List[Dict[str, Any]] = [
    {
        "id": "sbx-py-7721",
        "name": "Python Dev (FastAPI Migration)",
        "templateId": "python-dev-v2",
        "status": "running",
        "podName": "fuzeagent-sbx-python-dev-v2-7721",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "timeoutSeconds": 1800,
        "secondsRemaining": 1420,
        "cpuUsage": "0.35 / 2.0",
        "memUsage": "1.1Gi / 4Gi",
        "currentTask": "Refactoring PostgreSQL connection pool for asyncpg",
        "logs": [
            "[INIT] Container spun up from ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
            "[FUZEKEYS] Injected 2 secrets via zero-trust API (ANTHROPIC_API_KEY, DATABASE_URL)",
            "[STREAM] Linked session to agent.stream.python-dev-v2",
            "[EXEC] Analyzing models/database.py syntax..."
        ]
    }
]

PENDING_ESCALATIONS: List[Dict[str, Any]] = [
    {
        "id": "esc-101",
        "agentId": "python-dev-v2",
        "agentName": "Python Dev (FastAPI Migration)",
        "category": "destructive_operation",
        "title": "Drop and recreate table 'billing_ledger'",
        "detail": "Agent attempted to run 'DROP TABLE billing_ledger CASCADE;' during migration script execution.",
        "costUsd": 0.12,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
]

# ---------------------------------------------------------------------------
# Router Endpoints
# ---------------------------------------------------------------------------

@router.get("/templates", summary="List Agent Container Image Templates")
async def list_templates():
    return list(TEMPLATES_REGISTRY.values())

@router.get("/templates/{template_id}", summary="Get Image Template Details")
async def get_template(template_id: str):
    if template_id not in TEMPLATES_REGISTRY:
        raise HTTPException(status_code=404, detail="Template not found")
    return TEMPLATES_REGISTRY[template_id]

@router.post("/templates", summary="Register or Update Image Template")
async def save_template(template: ImageTemplateModel):
    TEMPLATES_REGISTRY[template.id] = template.model_dump()
    return {"status": "saved", "template": TEMPLATES_REGISTRY[template.id]}

@router.post("/templates/{template_id}/build", summary="Trigger In-Cluster Kaniko Build")
async def trigger_kaniko_build(template_id: str):
    if template_id not in TEMPLATES_REGISTRY:
        raise HTTPException(status_code=404, detail="Template not found")
    
    tmpl = TEMPLATES_REGISTRY[template_id]
    try:
        from .kaniko_builder import kaniko_builder
    except ImportError:
        from kaniko_builder import kaniko_builder
        
    return await kaniko_builder.build_image(
        template_id=template_id,
        dockerfile=tmpl.get("dockerfile", ""),
        destination_image=tmpl["image"]
    )

@router.get("/sandboxes", summary="List Active Sandboxed Containers")
async def list_sandboxes():
    return ACTIVE_SANDBOXES

@router.post("/sandboxes/launch", summary="Launch Ephemeral Agent Sandbox Pod")
async def launch_sandbox(req: SandboxLaunchRequest):
    template = TEMPLATES_REGISTRY.get(req.templateId)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    sbx_id = f"sbx-{req.templateId[:4]}-{uuid.uuid4().hex[:4]}"
    timeout = req.timeoutSeconds or template["sandboxing"]["defaultTimeoutSeconds"]
    
    new_sbx = {
        "id": sbx_id,
        "name": req.agentName or f"{template['name']} ({sbx_id})",
        "templateId": template["id"],
        "status": "running",
        "podName": f"fuzeagent-{sbx_id}",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "timeoutSeconds": timeout,
        "secondsRemaining": timeout,
        "cpuUsage": f"0.1 / {template['sandboxing']['cpuLimit']}",
        "memUsage": f"512Mi / {template['sandboxing']['memoryLimit']}",
        "currentTask": "Container initialized. Waiting for task assignment.",
        "logs": [
            f"[INIT] Booting container {template['image']}",
            f"[SANDBOX] Configured {timeout}s auto-shutdown countdown timer",
            "[FUZEKEYS] Resolving bound secrets...",
            f"[EVENTBUS] Connected to {template['eventBus']['channel']}"
        ]
    }
    ACTIVE_SANDBOXES.insert(0, new_sbx)
    return {"status": "launched", "sandbox": new_sbx}

@router.post("/sandboxes/{sandbox_id}/terminate", summary="Terminate Active Sandbox")
async def terminate_sandbox(sandbox_id: str):
    global ACTIVE_SANDBOXES
    target = next((s for s in ACTIVE_SANDBOXES if s["id"] == sandbox_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    target["status"] = "terminated"
    target["secondsRemaining"] = 0
    target["logs"].append(f"[SHUTDOWN] Sandbox terminated by supervisor.")
    return {"status": "terminated", "sandboxId": sandbox_id}

@router.get("/brains/hierarchy", summary="Get 5-Tier Memory & Brains Hierarchy")
async def get_brains_hierarchy():
    return {
        "tiers": [
            {
                "tier": 1,
                "name": "User Personal Profile Brain",
                "scope": "user",
                "persistence": "permanent",
                "permissions": "read-write",
                "description": "User preferences, communication tone, and individual project context.",
                "vectorCount": 1420
            },
            {
                "tier": 2,
                "name": "Organization Global Brain",
                "scope": "organization",
                "persistence": "permanent",
                "permissions": "consult-only",
                "description": "Company-wide policies, architectural guidelines, compliance rules, and standards.",
                "vectorCount": 18450
            },
            {
                "tier": 3,
                "name": "Team-Level Brain",
                "scope": "team",
                "persistence": "permanent",
                "permissions": "team-read-write",
                "description": "Squad domain knowledge, microservice schemas, and active sprint documentation.",
                "vectorCount": 5920
            },
            {
                "tier": 4,
                "name": "Agent Persona Long-Term Memory",
                "scope": "agent_persona",
                "persistence": "persistent",
                "permissions": "agent-scoped",
                "description": "Archetype-specific historical execution patterns, successful code resolutions, and tool calibrations.",
                "vectorCount": 3810
            },
            {
                "tier": 5,
                "name": "Ephemeral Session Memory",
                "scope": "session",
                "persistence": "ephemeral",
                "permissions": "runtime-isolated",
                "description": "Active conversation scratchpad and CLI buffers. Purged automatically on container shutdown.",
                "vectorCount": 85
            }
        ]
    }

@router.post("/brains/query", summary="Multi-Tier Cascading RAG Retrieval")
async def query_brains(req: BrainQueryRequest):
    return {
        "query": req.query,
        "results": [
            {
                "sourceTier": "Tier 3: Team-Level Brain",
                "docTitle": "FastAPI AsyncPG Database Architecture",
                "relevanceScore": 0.94,
                "excerpt": "Always use asyncpg pool with max_size=20 and acquire connections within async with pool.acquire() context blocks."
            },
            {
                "sourceTier": "Tier 2: Org Global Brain",
                "docTitle": "Enterprise Security & Secret Management",
                "relevanceScore": 0.88,
                "excerpt": "Hardcoding API keys or database credentials is strictly prohibited. Fetch all credentials via FuzeKeys secretRef tokens."
            },
            {
                "sourceTier": "Tier 1: User Personal Profile",
                "docTitle": "User Style Guide",
                "relevanceScore": 0.82,
                "excerpt": "User prefers concise explanations, typed Python code, and GitHub-style markdown tables."
            }
        ]
    }

@router.get("/escalations", summary="List Pending Human Escalations")
async def list_escalations():
    return PENDING_ESCALATIONS

@router.post("/escalations/{escalation_id}/resolve", summary="Resolve Human Escalation")
async def resolve_escalation(escalation_id: str, req: EscalationResolutionRequest):
    global PENDING_ESCALATIONS
    target = next((e for e in PENDING_ESCALATIONS if e["id"] == escalation_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    target["status"] = req.decision
    target["resolvedAt"] = datetime.now(timezone.utc).isoformat()
    target["approverId"] = req.approverId
    target["notes"] = req.notes
    
    return {"status": "resolved", "escalation": target}
