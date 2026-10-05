"""
Image Template Registry, Sandboxes, Brains & Escalations API Router for FuzeAgent.
Provides REST and WebSocket-backed interfaces for:
1. Agent Image Templates (Dockerfiles, FuzeKeys secrets, timeouts, eventBus)
2. Live Sandboxes monitoring and lifecycle (Track #1: Kubernetes Sandbox Driver)
3. FuzeKeys Vault Secret Resolution (Track #2: Live cluster secret injection)
4. 5-Tier Brains & Memory hierarchy management, Wiki & RAG retrieval (Track #4)
5. Real-Time Human-in-the-loop decision escalation approval (Track #3: RabbitMQ + WebSocket)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# Track #1: Kubernetes Pod Sandbox Driver
try:
    from .kubernetes_sandbox_driver import k8s_sandbox_driver
except ImportError:
    from kubernetes_sandbox_driver import k8s_sandbox_driver

# Track #2: FuzeKeys Vault Secret Resolution
try:
    from .fuzekeys_resolver import fuzekeys_resolver
except ImportError:
    from fuzekeys_resolver import fuzekeys_resolver

# Track #3: Real-Time Human Escalation Engine (RabbitMQ + WS)
try:
    from .escalation_engine import escalation_engine
except ImportError:
    from escalation_engine import escalation_engine

# Track #4: pgvector-backed Brains document store
try:
    from . import brain_store
except ImportError:
    import brain_store

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
    orgId: Optional[str] = None


class EscalationCreateRequest(BaseModel):
    agentId: str
    agentName: str
    category: str
    title: str
    detail: str
    costUsd: Optional[float] = 0.0
    metadata: Optional[Dict[str, Any]] = None


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


class BrainDocumentCreateRequest(BaseModel):
    title: str
    category: Optional[str] = "General"
    content: str
    author: Optional[str] = "Platform Architect"
    tags: Optional[List[str]] = Field(default_factory=list)


class BrainChatRequest(BaseModel):
    message: str
    sessionHistory: Optional[List[Dict[str, str]]] = Field(default_factory=list)


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
            "MAX_CONCURRENT_TASKS": "4",
        },
        "fuzeKeysSecrets": [
            {
                "keyName": "ANTHROPIC_API_KEY",
                "secretRef": "fk_sec_anthropic_prod",
                "description": "Anthropic LLM Token via FuzeKeys API",
            },
            {
                "keyName": "DATABASE_URL",
                "secretRef": "fk_sec_postgres_context",
                "description": "PostgreSQL Vector DB Connection URI",
            },
        ],
        "setupScript": "#!/bin/bash\necho '⚡ Initializing Python Developer Environment...'\nexec /usr/local/bin/session-relay \"$@\"",
        "sandboxing": {
            "defaultTimeoutSeconds": 1800,
            "cpuLimit": "2.0",
            "memoryLimit": "4Gi",
            "networkIsolation": "outbound-only",
            "autoShutdownOnIdle": True,
        },
        "eventBus": {
            "enabled": True,
            "channel": "agent.stream.python-dev-v2",
            "streamLlmChunks": True,
            "wsRelayUrl": "wss://fuzeagent.prod.fuzefront.com/ws/stream",
        },
        "escalation": {
            "requiresApprovalForDestructive": True,
            "costThresholdUsd": 5.0,
            "escalateTo": "human",
        },
        "status": "ready",
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
            "PORT": "3000",
        },  # nosec B104 -- sandbox dev server must listen on all interfaces inside its pod
        "fuzeKeysSecrets": [
            {
                "keyName": "GITHUB_ACCESS_TOKEN",
                "secretRef": "fk_sec_github_repo_bot",
                "description": "GitHub Deployment & PR Access Token",
            }
        ],
        "setupScript": "#!/bin/bash\necho '⚛️ Booting React UI Engineering Workspace...'\nexec /usr/local/bin/session-relay \"$@\"",
        "sandboxing": {
            "defaultTimeoutSeconds": 2400,
            "cpuLimit": "2.0",
            "memoryLimit": "4Gi",
            "networkIsolation": "outbound-only",
            "autoShutdownOnIdle": True,
        },
        "eventBus": {
            "enabled": True,
            "channel": "agent.stream.react-dev-v2",
            "streamLlmChunks": True,
            "wsRelayUrl": "wss://fuzeagent.prod.fuzefront.com/ws/stream",
        },
        "escalation": {
            "requiresApprovalForDestructive": True,
            "costThresholdUsd": 5.0,
            "escalateTo": "human",
        },
        "status": "ready",
    },
}

ACTIVE_SANDBOXES: List[Dict[str, Any]] = [
    {
        "id": "sbx-py-7721",
        "name": "Python Dev (FastAPI Migration)",
        "templateId": "python-dev-v2",
        "status": "running",
        "podName": "agent-sbx-python-dev-7721",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "timeoutSeconds": 1800,
        "secondsRemaining": 1420,
        "cpuUsage": "0.35 / 2.0",
        "memUsage": "1.1Gi / 4Gi",
        "currentTask": "Refactoring PostgreSQL connection pool for asyncpg",
        "logs": [
            "[INIT] Kubernetes Pod spawned from ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
            "[FUZEKEYS] Injected 2 secrets via zero-trust API (ANTHROPIC_API_KEY, DATABASE_URL)",
            "[STREAM] Linked session to agent.stream.python-dev-v2",
            "[EXEC] Analyzing models/database.py syntax...",
        ],
    }
]

# Track #4: In-Memory / pgvector backed documents store
BRAIN_DOCUMENTS: Dict[str, List[Dict[str, Any]]] = {
    "default": [
        {
            "id": "doc_arch_01",
            "title": "Module Federation & Multi-Tenant MFE Architecture",
            "category": "Architecture",
            "content": "FuzeFront uses Webpack & Vite Module Federation to stitch autonomous microfrontends into a cohesive portal shell. React 19 is shared singleton across all remotes.",
            "author": "Platform Architect",
            "updatedAt": "2 hours ago",
            "tags": ["mfe", "vite", "federation", "architecture"],
            "chunksCount": 8,
        },
        {
            "id": "doc_agents_02",
            "title": "Autonomous Agent Sandboxing & TTL Policies",
            "category": "Agent Ops",
            "content": "All agent pods (Python, React, DevOps, Marketing) run with strict rootless execution, default 30m auto-shutdown TTL, and FuzeKeys zero-exposure secrets injection.",
            "author": "DevOps Lead",
            "updatedAt": "Yesterday",
            "tags": ["security", "sandboxes", "agents", "ttl"],
            "chunksCount": 5,
        },
        {
            "id": "doc_fuzekeys_03",
            "title": "FuzeKeys Zero-Exposure Vault Protocol",
            "category": "Security",
            "content": "Credentials never touch disk or git repos. They are dynamically resolved over internal cluster HTTP API via opaque tokenized references.",
            "author": "Security Architect",
            "updatedAt": "3 days ago",
            "tags": ["fuzekeys", "security", "zero-exposure", "vault"],
            "chunksCount": 6,
        },
    ]
}

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


@router.post(
    "/templates/{template_id}/build", summary="Trigger In-Cluster Kaniko Build"
)
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
        destination_image=tmpl["image"],
    )


# ---------------------------------------------------------------------------
# Track #1 & #2: Sandboxes Lifecycle & Live FuzeKeys Secret Resolution
# ---------------------------------------------------------------------------


@router.get("/sandboxes", summary="List Active Sandboxed Containers")
async def list_sandboxes():
    # Sync with live Kubernetes pods if available
    try:
        k8s_pods = await k8s_sandbox_driver.list_sandbox_pods()
        live_names = {p["podName"] for p in k8s_pods}
        for sbx in ACTIVE_SANDBOXES:
            if sbx.get("podName") and sbx["podName"] in live_names:
                sbx["status"] = "running"
    except Exception as e:
        logger.debug(f"K8s pod list sync: {e}")
    return ACTIVE_SANDBOXES


@router.post("/sandboxes/launch", summary="Launch Ephemeral Agent Sandbox Pod")
async def launch_sandbox(req: SandboxLaunchRequest):
    template = TEMPLATES_REGISTRY.get(req.templateId)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    timeout = req.timeoutSeconds or template["sandboxing"]["defaultTimeoutSeconds"]

    # 1. Track #2: Live FuzeKeys Secret Resolution
    secret_bindings = template.get("fuzeKeysSecrets", [])
    resolved_secrets = await fuzekeys_resolver.resolve_secrets(
        secret_bindings=secret_bindings,
        org_id=req.orgId,
    )

    # Combine environment variables
    env_vars = {
        **template.get("envVars", {}),
        **resolved_secrets,
        **(req.envOverrides or {}),
    }

    # 2. Track #1: Kubernetes Sandbox Driver Pod Creation
    k8s_res = await k8s_sandbox_driver.spawn_sandbox_pod(
        template_id=template["id"],
        image=template["image"],
        env_vars=env_vars,
        timeout_seconds=timeout,
        cpu_limit=template["sandboxing"]["cpuLimit"],
        memory_limit=template["sandboxing"]["memoryLimit"],
    )

    sbx_id = k8s_res["id"]
    pod_name = k8s_res["podName"]

    new_sbx = {
        "id": sbx_id,
        "name": req.agentName or f"{template['name']} ({sbx_id})",
        "templateId": template["id"],
        "status": "running",
        "podName": pod_name,
        "startedAt": k8s_res["startedAt"],
        "timeoutSeconds": timeout,
        "secondsRemaining": timeout,
        "cpuUsage": f"0.1 / {template['sandboxing']['cpuLimit']}",
        "memUsage": f"512Mi / {template['sandboxing']['memoryLimit']}",
        "currentTask": "Container initialized via K8s driver. Waiting for task assignment.",
        "logs": [
            f"[K8S] Pod {pod_name} scheduled in namespace {k8s_res.get('namespace', 'fuzeagent')}",
            f"[INIT] Booting image {template['image']}",
            f"[SANDBOX] Configured {timeout}s auto-shutdown countdown timer (activeDeadlineSeconds)",
            f"[FUZEKEYS] Injected {len(resolved_secrets)} resolved vault secrets into Pod spec",
            f"[EVENTBUS] Connected to {template['eventBus']['channel']}",
        ],
    }
    ACTIVE_SANDBOXES.insert(0, new_sbx)
    return {"status": "launched", "sandbox": new_sbx}


@router.post("/sandboxes/{sandbox_id}/terminate", summary="Terminate Active Sandbox")
async def terminate_sandbox(sandbox_id: str):
    target = next((s for s in ACTIVE_SANDBOXES if s["id"] == sandbox_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # Track #1: Terminate K8s Pod
    if target.get("podName"):
        await k8s_sandbox_driver.terminate_sandbox_pod(target["podName"])

    target["status"] = "terminated"
    target["secondsRemaining"] = 0
    target["logs"].append("[SHUTDOWN] Sandbox Pod terminated by supervisor.")
    return {"status": "terminated", "sandboxId": sandbox_id}


# ---------------------------------------------------------------------------
# Track #4: 5-Tier Brains, Wiki Documents & RAG Chat Retrieval
# ---------------------------------------------------------------------------


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
                "vectorCount": 1420,
            },
            {
                "tier": 2,
                "name": "Organization Global Brain",
                "scope": "organization",
                "persistence": "permanent",
                "permissions": "consult-only",
                "description": "Company-wide policies, architectural guidelines, compliance rules, and standards.",
                "vectorCount": 18450,
            },
            {
                "tier": 3,
                "name": "Team-Level Brain",
                "scope": "team",
                "persistence": "permanent",
                "permissions": "team-read-write",
                "description": "Squad domain knowledge, microservice schemas, and active sprint documentation.",
                "vectorCount": 5920,
            },
            {
                "tier": 4,
                "name": "Agent Persona Long-Term Memory",
                "scope": "agent_persona",
                "persistence": "persistent",
                "permissions": "agent-scoped",
                "description": "Archetype-specific historical execution patterns, successful code resolutions, and tool calibrations.",
                "vectorCount": 3810,
            },
            {
                "tier": 5,
                "name": "Ephemeral Session Memory",
                "scope": "session",
                "persistence": "ephemeral",
                "permissions": "runtime-isolated",
                "description": "Active conversation scratchpad and CLI buffers. Purged automatically on container shutdown.",
                "vectorCount": 85,
            },
        ]
    }


@router.get("/brains/{brain_id}/documents", summary="List Documents in Brain Wiki")
async def list_brain_documents(brain_id: str):
    stored = await brain_store.list_documents(brain_id)
    seed = BRAIN_DOCUMENTS.get(brain_id) or BRAIN_DOCUMENTS.get("default", [])
    # Persisted (pgvector) docs first, then the built-in seed docs.
    return (stored or []) + seed


@router.post(
    "/brains/{brain_id}/documents", summary="Ingest Document into Brain Knowledge Base"
)
async def ingest_brain_document(brain_id: str, doc: BrainDocumentCreateRequest):
    persisted = await brain_store.add_document(
        brain_id=brain_id,
        title=doc.title,
        content=doc.content,
        category=doc.category or "General",
        author=doc.author or "Human Architect",
        tags=doc.tags or [],
    )
    if persisted:
        logger.info(
            f"📚 Brain Document embedded into pgvector: '{doc.title}' ({brain_id})"
        )
        return {"status": "ingested", "persisted": True, "document": persisted}

    # Fallback: in-memory only (lost on restart)
    new_doc = {
        "id": f"doc_{uuid.uuid4().hex[:8]}",
        "title": doc.title,
        "category": doc.category or "General",
        "content": doc.content,
        "author": doc.author or "Human Architect",
        "updatedAt": "Just now",
        "tags": doc.tags or [],
        "chunksCount": max(1, len(doc.content) // 250),
    }
    if brain_id not in BRAIN_DOCUMENTS:
        BRAIN_DOCUMENTS[brain_id] = list(BRAIN_DOCUMENTS["default"])
    BRAIN_DOCUMENTS[brain_id].insert(0, new_doc)
    logger.warning(
        f"Brain Document stored in memory only (pgvector unavailable): '{doc.title}'"
    )
    return {"status": "ingested", "persisted": False, "document": new_doc}


@router.post("/brains/{brain_id}/chat", summary="Chat with Brain Knowledge Base")
async def chat_with_brain(brain_id: str, req: BrainChatRequest):
    # 1) Real vector similarity search over pgvector-stored documents
    hits = await brain_store.search(brain_id, req.message, limit=3)
    hits = [h for h in (hits or []) if h.get("score", 0) >= 0.25]

    # 2) Keyword fallback over the built-in seed docs
    seed = BRAIN_DOCUMENTS.get(brain_id) or BRAIN_DOCUMENTS.get("default", [])
    words = req.message.lower().split()
    kw = []
    for d in seed:
        score = 0.0
        if any(w in d["title"].lower() for w in words):
            score += 0.5
        if any(w in d["content"].lower() for w in words):
            score += 0.4
        if score > 0:
            kw.append({**d, "score": score})
    kw.sort(key=lambda x: x["score"], reverse=True)

    top = (hits + kw)[:3]
    citations = [
        {
            "title": d["title"],
            "excerpt": d["content"][:180] + ("..." if len(d["content"]) > 180 else ""),
            "score": round(d.get("score", 0), 3),
        }
        for d in top
    ]

    if citations:
        answer = (
            f"Based on indexed documents in '{brain_id}': {citations[0]['excerpt']}"
        )
    else:
        answer = f"I searched the '{brain_id}' knowledge store for '{req.message}' but found no relevant documents."

    return {
        "reply": answer,
        "citations": citations,
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
                "excerpt": "Always use asyncpg pool with max_size=20 and acquire connections within async with pool.acquire() context blocks.",
            },
            {
                "sourceTier": "Tier 2: Org Global Brain",
                "docTitle": "Enterprise Security & Secret Management",
                "relevanceScore": 0.88,
                "excerpt": "Hardcoding API keys or database credentials is strictly prohibited. Fetch all credentials via FuzeKeys secretRef tokens.",
            },
            {
                "sourceTier": "Tier 1: User Personal Profile",
                "docTitle": "User Style Guide",
                "relevanceScore": 0.82,
                "excerpt": "User prefers concise explanations, typed Python code, and GitHub-style markdown tables.",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Track #3: Real-Time Human Decision Escalation Engine (RabbitMQ + WS)
# ---------------------------------------------------------------------------


@router.get("/escalations", summary="List Pending Human Escalations")
async def list_escalations():
    return escalation_engine.list_escalations()


@router.post("/escalations", summary="Create Escalation from Agent Sandbox")
async def create_escalation(req: EscalationCreateRequest):
    return await escalation_engine.create_escalation(
        agent_id=req.agentId,
        agent_name=req.agentName,
        category=req.category,
        title=req.title,
        detail=req.detail,
        cost_usd=req.costUsd or 0.0,
        metadata=req.metadata,
    )


@router.post("/escalations/{escalation_id}/resolve", summary="Resolve Human Escalation")
async def resolve_escalation(escalation_id: str, req: EscalationResolutionRequest):
    res = await escalation_engine.resolve_escalation(
        escalation_id=escalation_id,
        decision=req.decision,
        approver_id=req.approverId or "admin",
        notes=req.notes,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return {"status": "resolved", "escalation": res}
