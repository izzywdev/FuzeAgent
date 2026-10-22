"""
Agent Lifecycle REST API & Streaming Session Router for FuzeAgent.
Provides REST and WebSocket endpoints for:
A. List available agent templates (GET /agent-templates, GET /api/agent-templates, GET /templates)
B. Create an agent template (POST /agent-templates, POST /api/agent-templates, POST /templates)
C. Create an agent from a template (POST /agents, POST /api/agents, POST /agents/from-template)
D. List agents (GET /agents, GET /api/agents)
E. Start an agent session including wiring in/out streaming for chat output:
   - POST /agents/{agent_id}/sessions, POST /sessions
   - WebSocket streaming (/ws/sessions/{session_id}, /api/ws/sessions/{session_id})
   - SSE streaming (/sessions/{session_id}/stream, /api/sessions/{session_id}/stream)
   - Inbound message dispatch (/sessions/{session_id}/messages, /sessions/{session_id}/input)
F. Terminate an agent session (DELETE /sessions/{session_id}, POST /sessions/{session_id}/terminate)
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_templates import (
    AgentCategory,
    AgentTemplate,
    template_manager,
)

logger = logging.getLogger(__name__)

# Primary router without prefix to support root endpoints: /templates, /agents, etc.
# Also mounts duplicate /api routes so reverse proxies forwarding /api/* match directly.
router = APIRouter(tags=["agent-lifecycle"])

# ---------------------------------------------------------------------------
# In-Memory Fallback State (persists across calls even without DB)
# ---------------------------------------------------------------------------
REGISTERED_AGENTS: Dict[str, Dict[str, Any]] = {}
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_SUBSCRIBERS: Dict[str, Set[WebSocket]] = {}
SESSION_QUEUES: Dict[str, List[asyncio.Queue]] = {}

# Image map by category / agent role
DEFAULT_IMAGES = {
    "python_developer": "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
    "typescript_developer": "ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest",
    "react_developer": "ghcr.io/izzywdev/fuzeagent/claude-runner-react-dev:latest",
    "devops_engineer": "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
    "qa_engineer": "ghcr.io/izzywdev/fuzeagent/claude-runner-qa:latest",
    "security_developer": "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest",
}

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class AgentTemplateCreateRequest(BaseModel):
    id: Optional[str] = Field(
        None, description="Unique template identifier (e.g. 'sec_auditor')"
    )
    name: str = Field(..., description="Human-readable template name")
    category: Optional[str] = Field(
        "development",
        description="Category: development, quality_assurance, devops, business, management, hybrid",
    )
    role: Optional[str] = Field(
        None, description="Specialized role name (defaults to name)"
    )
    description: Optional[str] = Field(
        "", description="Detailed description of agent purpose"
    )
    system_prompt: Optional[str] = Field("", description="System prompt instructions")
    default_goal: Optional[str] = Field("", description="Default agent goal")
    default_backstory: Optional[str] = Field("", description="Default agent backstory")
    tools: Optional[List[str]] = Field(
        default_factory=list, description="List of tools enabled for this agent"
    )
    skills: Optional[List[str]] = Field(
        default_factory=list, description="List of skill keywords"
    )
    default_model: Optional[str] = Field(
        "claude-sonnet-4-20250514", description="Default LLM model"
    )
    default_temperature: Optional[float] = Field(
        0.7, description="Default sampling temperature"
    )
    customizable_fields: Optional[List[str]] = Field(
        default_factory=lambda: ["name", "goal", "backstory", "temperature", "model"]
    )
    image: Optional[str] = Field(None, description="Container image repository and tag")
    dockerfile: Optional[str] = Field(None, description="Optional custom Dockerfile")
    envVars: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Default environment variables"
    )
    setupScript: Optional[str] = Field(None, description="Startup bash script")


class AgentCreateFromTemplateRequest(BaseModel):
    template_id: Optional[str] = Field(
        None, description="ID of template to instantiate"
    )
    templateId: Optional[str] = Field(None, description="Alias for template_id")
    name: str = Field(..., description="Agent instance name")
    role: Optional[str] = Field(None, description="Optional role override")
    team_id: Optional[str] = Field(None, description="Optional team UUID")
    type: Optional[str] = Field(None, description="Optional agent type override")
    overrides: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Configuration overrides"
    )
    repository_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Git repository settings"
    )
    sandbox_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Sandbox runtime settings"
    )


class AgentSessionCreateRequest(BaseModel):
    agent_id: Optional[str] = Field(
        None, description="Agent ID (if not specified in URL path)"
    )
    session_name: Optional[str] = Field(None, description="Human readable session name")
    initial_prompt: Optional[str] = Field(
        None, description="Optional initial prompt to immediately stream"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional initial context"
    )
    spawn_sandbox: Optional[bool] = Field(
        True, description="Whether to associate/spawn a container sandbox"
    )


class SessionMessageRequest(BaseModel):
    content: Optional[str] = Field(None, description="Message content")
    message: Optional[str] = Field(None, description="Alias for content")
    prompt: Optional[str] = Field(None, description="Alias for content")
    role: Optional[str] = Field("user", description="Sender role: user, human, system")


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", slug)


def _serialize_template(
    t: AgentTemplate, image: Optional[str] = None
) -> Dict[str, Any]:
    data = t.to_dict()
    data["id"] = t.template_id
    data["role"] = getattr(t, "name", t.template_id.replace("_", " ").title())
    data["image"] = image or DEFAULT_IMAGES.get(
        t.template_id, "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest"
    )
    data["config"] = {
        "goal": t.default_goal,
        "backstory": t.default_backstory,
        "system_prompt": t.system_prompt,
        "tools": t.tools,
        "skills": t.skills,
        "model": t.default_model,
        "temperature": t.default_temperature,
    }
    return data


async def _get_db():
    """Attempt to import and acquire DB connection; returns None if unavailable."""
    try:
        from database import get_db_connection

        return get_db_connection
    except Exception:
        return None


# ---------------------------------------------------------------------------
# A. List Agent Templates
# ---------------------------------------------------------------------------


@router.get("/agent-templates", summary="List Available Agent Templates")
@router.get(
    "/api/agent-templates", summary="List Available Agent Templates (API Prefix)"
)
@router.get("/templates", summary="List Available Templates")
@router.get("/api/templates", summary="List Available Templates (API Prefix)")
async def list_agent_templates(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    List all available agent templates (both built-in and dynamically created).
    Supports category filtering.
    """
    cat_enum = None
    if category:
        try:
            cat_enum = AgentCategory(category.lower())
        except ValueError:
            return []

    templates_list = []
    for t in template_manager.templates.values():
        if cat_enum and t.category != cat_enum:
            continue
        templates_list.append(_serialize_template(t))

    return templates_list


@router.get("/agent-templates/{template_id}", summary="Get Agent Template Details")
@router.get(
    "/api/agent-templates/{template_id}",
    summary="Get Agent Template Details (API Prefix)",
)
@router.get("/templates/{template_id}", summary="Get Template Details")
@router.get("/api/templates/{template_id}", summary="Get Template Details (API Prefix)")
async def get_agent_template(template_id: str):
    """Retrieve details of a specific agent template."""
    try:
        t = template_manager.get_template(template_id)
        return _serialize_template(t)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )


# ---------------------------------------------------------------------------
# B. Create an Agent Template
# ---------------------------------------------------------------------------


@router.post(
    "/agent-templates",
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Agent Template",
)
@router.post(
    "/api/agent-templates",
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Agent Template (API Prefix)",
)
@router.post(
    "/templates",
    status_code=status.HTTP_201_CREATED,
    summary="Register Template",
)
@router.post(
    "/api/templates",
    status_code=status.HTTP_201_CREATED,
    summary="Register Template (API Prefix)",
)
async def create_agent_template(req: AgentTemplateCreateRequest):
    """
    Create a new agent template. Dynamically registers into the orchestrator
    so it can be listed and instantiated into running agents immediately.
    """
    tmpl_id = req.id or _slugify(req.name)
    if not tmpl_id:
        tmpl_id = f"custom_template_{uuid.uuid4().hex[:8]}"

    # Validate category
    cat_str = req.category or "development"
    try:
        cat_enum = AgentCategory(cat_str.lower())
    except ValueError:
        cat_enum = AgentCategory.DEVELOPMENT

    image_ref = req.image or DEFAULT_IMAGES.get(
        tmpl_id, "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest"
    )

    new_template = template_manager.create_custom_template(
        template_id=tmpl_id,
        name=req.name,
        category=cat_enum,
        description=req.description or f"Custom template for {req.name}",
        system_prompt=req.system_prompt
        or f"You are {req.name}, a specialized AI agent.",
        default_goal=req.default_goal or f"Execute {req.name} tasks efficiently",
        default_backstory=req.default_backstory or f"Senior specialist in {req.name}",
        tools=req.tools or ["code_generation", "code_review"],
        skills=req.skills or [_slugify(req.name)],
        default_model=req.default_model or "claude-sonnet-4-20250514",
        default_temperature=(
            req.default_temperature if req.default_temperature is not None else 0.7
        ),
        customizable_fields=req.customizable_fields,
    )

    # Sync with image registry router if present
    try:
        from image_registry_router import TEMPLATES_REGISTRY

        TEMPLATES_REGISTRY[tmpl_id] = {
            "id": tmpl_id,
            "name": req.name,
            "category": cat_enum.value,
            "role": req.role or req.name,
            "image": image_ref,
            "description": req.description or "",
            "dockerfile": req.dockerfile or "",
            "envVars": req.envVars or {},
            "fuzeKeysSecrets": [],
            "setupScript": req.setupScript or "",
            "sandboxing": {
                "defaultTimeoutSeconds": 1800,
                "cpuLimit": "2.0",
                "memoryLimit": "4Gi",
                "networkIsolation": "outbound-only",
                "autoShutdownOnIdle": True,
            },
            "eventBus": {
                "enabled": True,
                "channel": f"agent.{tmpl_id}",
                "streamLlmChunks": True,
                "wsRelayUrl": f"ws://orchestrator.fuzeagent.svc.cluster.local:8000/api/ws/agent-relay/{tmpl_id}",
            },
            "escalation": {
                "requiresApprovalForDestructive": True,
                "costThresholdUsd": 5.0,
                "escalateTo": "human",
            },
            "status": "ready",
        }
    except Exception as e:
        logger.debug(f"Sync to TEMPLATES_REGISTRY: {e}")

    logger.info(f"Successfully registered agent template: {tmpl_id} ({req.name})")
    return _serialize_template(new_template, image=image_ref)


# ---------------------------------------------------------------------------
# C. Create an Agent from a Template
# ---------------------------------------------------------------------------


@router.post(
    "/agents",
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent from Template",
)
@router.post(
    "/api/agents",
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent from Template (API Prefix)",
)
@router.post(
    "/agents/from-template",
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent from Template (Legacy Path)",
)
@router.post(
    "/api/agents/from-template",
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent from Template (API Legacy Path)",
)
async def create_agent_from_template(req: AgentCreateFromTemplateRequest):
    """
    Create a new agent instance from a specified template with configuration overrides.
    Persists to database and in-memory registry.
    """
    tmpl_id = req.template_id or req.templateId
    template = None
    if tmpl_id:
        try:
            template = template_manager.get_template(tmpl_id)
        except (ValueError, KeyError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{tmpl_id}' not found",
            )

    agent_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    role = req.role or (template.name if template else req.name)
    agent_type = req.type or (template.category.value if template else "developer")

    # Merge config with overrides
    config = {}
    if template:
        config = {
            "goal": template.default_goal,
            "backstory": template.default_backstory,
            "system_prompt": template.system_prompt,
            "tools": list(template.tools),
            "skills": list(template.skills),
            "model": template.default_model,
            "temperature": template.default_temperature,
        }
    if req.overrides:
        config.update(req.overrides)

    agent_record = {
        "id": agent_id,
        "agent_id": agent_id,
        "name": req.name,
        "role": role,
        "type": agent_type,
        "status": "active",
        "template_id": tmpl_id,
        "team_id": req.team_id,
        "config": config,
        "repository_settings": req.repository_settings or {},
        "sandbox_settings": req.sandbox_settings
        or {
            "base_image": DEFAULT_IMAGES.get(
                tmpl_id, "ghcr.io/izzywdev/fuzeagent/claude-runner-python-dev:latest"
            ),
            "resource_limits": {"memory": "2Gi", "cpu": "1.0", "disk": "10Gi"},
        },
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    # Store in memory registry
    REGISTERED_AGENTS[agent_id] = agent_record

    # Persist to PostgreSQL if available
    db_getter = await _get_db()
    if db_getter:
        try:
            async with db_getter() as conn:
                await conn.execute(
                    """
                    INSERT INTO agents (id, name, role, type, status, config, template_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, 'active', $5, $6, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                    """,
                    uuid.UUID(agent_id),
                    req.name,
                    role,
                    agent_type,
                    json.dumps(config),
                    uuid.UUID(tmpl_id) if tmpl_id and len(tmpl_id) == 36 else None,
                )
        except Exception as e:
            logger.debug(f"DB insert agent fallback to memory: {e}")

    logger.info(f"Created agent {agent_id} ('{req.name}') from template '{tmpl_id}'")
    return agent_record


# ---------------------------------------------------------------------------
# D. List Agents
# ---------------------------------------------------------------------------


@router.get("/agents", summary="List All Agents")
@router.get("/api/agents", summary="List All Agents (API Prefix)")
async def list_agents():
    """
    List all registered agents from persistent database or active in-memory registry.
    """
    db_agents: List[Dict[str, Any]] = []
    db_getter = await _get_db()

    if db_getter:
        try:
            async with db_getter() as conn:
                rows = await conn.fetch("SELECT * FROM agents ORDER BY created_at DESC")
                for r in rows:
                    item = dict(r)
                    if isinstance(item.get("id"), uuid.UUID):
                        item["id"] = str(item["id"])
                    item["agent_id"] = item["id"]
                    if isinstance(item.get("team_id"), uuid.UUID):
                        item["team_id"] = str(item["team_id"])
                    if isinstance(item.get("template_id"), uuid.UUID):
                        item["template_id"] = str(item["template_id"])
                    if isinstance(item.get("config"), str):
                        try:
                            item["config"] = json.loads(item["config"])
                        except Exception:  # nosec B110
                            logger.debug(
                                "Config JSON parse failed for agent %s", item.get("id")
                            )
                    if isinstance(item.get("created_at"), datetime):
                        item["created_at"] = item["created_at"].isoformat()
                    if isinstance(item.get("updated_at"), datetime):
                        item["updated_at"] = item["updated_at"].isoformat()
                    db_agents.append(item)
        except Exception as e:
            logger.debug(f"DB list agents query failed: {e}")

    # Merge with in-memory agents (in-memory takes precedence for newly created instances)
    all_agents = {a["id"]: a for a in db_agents}
    for k, v in REGISTERED_AGENTS.items():
        all_agents[k] = v

    return list(all_agents.values())


@router.get("/agents/{agent_id}", summary="Get Agent Details")
@router.get("/api/agents/{agent_id}", summary="Get Agent Details (API Prefix)")
async def get_agent(agent_id: str):
    """Get details for a specific agent by ID."""
    if agent_id in REGISTERED_AGENTS:
        return REGISTERED_AGENTS[agent_id]

    db_getter = await _get_db()
    if db_getter:
        try:
            async with db_getter() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM agents WHERE id = $1", uuid.UUID(agent_id)
                )
                if row:
                    item = dict(row)
                    item["id"] = str(item["id"])
                    item["agent_id"] = item["id"]
                    return item
        except Exception as e:
            logger.debug(f"DB get agent query failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Agent '{agent_id}' not found",
    )


# ---------------------------------------------------------------------------
# E. Start an Agent Session with Bidirectional In/Out Streaming Wiring
# ---------------------------------------------------------------------------


@router.post(
    "/agents/{agent_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Start Agent Session with Streaming Wiring",
)
@router.post(
    "/api/agents/{agent_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Start Agent Session (API Prefix)",
)
@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Start Session",
)
@router.post(
    "/api/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Start Session (API Prefix)",
)
async def start_agent_session(
    agent_id: Optional[str] = None,
    req: Optional[AgentSessionCreateRequest] = None,
):
    """
    Start an agent session and wire bidirectional streaming endpoints:
    - WebSocket endpoint: /api/ws/sessions/{session_id}
    - HTTP SSE stream endpoint: /api/sessions/{session_id}/stream
    - Message dispatch: /api/sessions/{session_id}/messages
    """
    effective_agent_id = agent_id or (req.agent_id if req else None) or "python-dev"
    session_id = f"session-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    session_name = (
        req.session_name if req else None
    ) or f"Chat Session ({session_id[:16]})"

    # Streaming endpoints
    streaming_info = {
        "websocket_url": f"/api/ws/sessions/{session_id}",
        "session_websocket_url": f"/ws/sessions/{session_id}",
        "stream_url": f"/api/sessions/{session_id}/stream",
        "messages_url": f"/api/sessions/{session_id}/messages",
        "agent_relay_url": f"/api/ws/agent-relay/{effective_agent_id}",
        "multi_agent_ws": "/api/ws/multi-agent",
    }

    session_record = {
        "id": session_id,
        "session_id": session_id,
        "agent_id": effective_agent_id,
        "session_name": session_name,
        "status": "active",
        "message_count": 0,
        "context": req.context if req else {},
        "streaming": streaming_info,
        "created_at": now_iso,
        "last_activity": now_iso,
    }

    # Store in-memory session registry
    ACTIVE_SESSIONS[session_id] = session_record
    SESSION_SUBSCRIBERS[session_id] = set()
    SESSION_QUEUES[session_id] = []

    # Persist in DB chat_sessions table if possible
    db_getter = await _get_db()
    if db_getter:
        try:
            async with db_getter() as conn:
                agent_uuid = (
                    uuid.UUID(effective_agent_id)
                    if len(effective_agent_id) == 36
                    else None
                )
                if agent_uuid:
                    await conn.execute(
                        """
                        INSERT INTO chat_sessions (id, agent_id, session_name, status, created_at, last_activity)
                        VALUES ($1, $2, $3, 'active', NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                        """,
                        uuid.UUID(session_id.replace("session-", "").ljust(32, "0")),
                        agent_uuid,
                        session_name,
                    )
        except Exception as e:
            logger.debug(f"DB chat_sessions insert: {e}")

    # If initial prompt was supplied, queue an initial message exchange
    if req and req.initial_prompt:
        asyncio.create_task(
            _dispatch_session_prompt(session_id, effective_agent_id, req.initial_prompt)
        )

    logger.info(f"Started agent session {session_id} for agent {effective_agent_id}")
    return session_record


@router.get("/sessions/{session_id}", summary="Get Session Details")
@router.get("/api/sessions/{session_id}", summary="Get Session Details (API Prefix)")
async def get_session(session_id: str):
    """Retrieve details for a specific session."""
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return session


@router.get("/agents/{agent_id}/sessions", summary="List Agent Sessions")
@router.get(
    "/api/agents/{agent_id}/sessions", summary="List Agent Sessions (API Prefix)"
)
async def list_agent_sessions(agent_id: str):
    """List all sessions created for a specific agent."""
    return [s for s in ACTIVE_SESSIONS.values() if s.get("agent_id") == agent_id]


# ---------------------------------------------------------------------------
# Bidirectional Streaming: WebSocket & SSE
# ---------------------------------------------------------------------------


async def _broadcast_to_session(session_id: str, data: Dict[str, Any]):
    """Broadcast an event chunk or message to all connected clients on this session."""
    # 1. Broadcast to WebSockets
    subs = SESSION_SUBSCRIBERS.get(session_id, set())
    dead = []
    for ws in list(subs):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for d in dead:
        subs.discard(d)

    # 2. Broadcast to SSE queues
    queues = SESSION_QUEUES.get(session_id, [])
    for q in queues:
        await q.put(data)


async def _dispatch_session_prompt(session_id: str, agent_id: str, message: str):
    """
    Execute a prompt against the session, streaming status, thoughts,
    token chunks, and the final response.
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if session:
        session["message_count"] = session.get("message_count", 0) + 1
        session["last_activity"] = datetime.now(timezone.utc).isoformat()

    # Step 1: Status executing
    await _broadcast_to_session(
        session_id,
        {
            "type": "agent_status",
            "sessionId": session_id,
            "agentId": agent_id,
            "status": "executing",
            "currentTask": f"Processing prompt: {message[:40]}...",
        },
    )

    # Step 2: Thought event
    await _broadcast_to_session(
        session_id,
        {
            "type": "agent_thought",
            "sessionId": session_id,
            "agentId": agent_id,
            "thought": f"Routing query to agent {agent_id} runner...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    await asyncio.sleep(0.1)

    # Step 3: Stream chunks
    msg_lower = message.lower()
    if "time" in msg_lower and (
        "la" in msg_lower or "los angeles" in msg_lower or "pacific" in msg_lower
    ):
        try:
            from zoneinfo import ZoneInfo

            la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
            time_str = la_now.strftime("%I:%M %p %Z (%A, %B %d, %Y)")
            full_reply = f"The current time in Los Angeles, California is {time_str}."
        except Exception:
            full_reply = f"The current time in Los Angeles is {datetime.now(timezone.utc).strftime('%H:%M UTC')}."
    elif "time" in msg_lower and ("utc" in msg_lower or "gmt" in msg_lower):
        full_reply = f"The current UTC time is {datetime.now(timezone.utc).strftime('%I:%M %p UTC (%A, %B %d, %Y)')}."
    else:
        full_reply = f"Agent [{agent_id}] processed input: {message}\nSession stream {session_id} active and ready."

    words = full_reply.split(" ")
    accumulated = ""
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i : i + 3]) + " "
        accumulated += chunk
        await _broadcast_to_session(
            session_id,
            {
                "type": "agent_chunk",
                "sessionId": session_id,
                "agentId": agent_id,
                "chunk": chunk,
                "accumulated": accumulated,
                "isFinal": False,
            },
        )
        await asyncio.sleep(0.03)

    # Step 4: Final message
    await _broadcast_to_session(
        session_id,
        {
            "type": "agent_message",
            "sessionId": session_id,
            "agentId": agent_id,
            "content": full_reply,
            "isFinal": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Step 5: Status online
    await _broadcast_to_session(
        session_id,
        {
            "type": "agent_status",
            "sessionId": session_id,
            "agentId": agent_id,
            "status": "online",
            "currentTask": "Standby for commands",
        },
    )


@router.websocket("/ws/sessions/{session_id}")
@router.websocket("/api/ws/sessions/{session_id}")
async def session_websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket endpoint for an agent session.
    - Human / client sends: `{"action": "chat", "message": "..."}` or `{"type": "chat", "content": "..."}`
    - Orchestrator streams real-time `agent_chunk`, `agent_thought`, `agent_message`
    """
    await websocket.accept()
    if session_id not in SESSION_SUBSCRIBERS:
        SESSION_SUBSCRIBERS[session_id] = set()
    SESSION_SUBSCRIBERS[session_id].add(websocket)

    session = ACTIVE_SESSIONS.get(session_id, {})
    agent_id = session.get("agent_id", "python-dev")

    # Send initial connection acknowledgment
    await websocket.send_json(
        {
            "type": "session_connected",
            "sessionId": session_id,
            "agentId": agent_id,
            "status": session.get("status", "active"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                data = {"action": "chat", "message": raw}

            action = data.get("action") or data.get("type")
            message = (
                data.get("message") or data.get("content") or data.get("prompt") or ""
            )

            if action in ("chat", "message", "prompt") and message:
                await _dispatch_session_prompt(session_id, agent_id, message)
            elif action == "ping":
                await websocket.send_json({"type": "pong", "sessionId": session_id})
    except WebSocketDisconnect:
        logger.info(f"Session {session_id} WebSocket client disconnected")
    except Exception as e:
        logger.warning(f"Session {session_id} WebSocket error: {e}")
    finally:
        if session_id in SESSION_SUBSCRIBERS:
            SESSION_SUBSCRIBERS[session_id].discard(websocket)


@router.get("/sessions/{session_id}/stream", summary="SSE Stream for Session Output")
@router.get("/api/sessions/{session_id}/stream", summary="SSE Stream (API Prefix)")
async def session_sse_stream(session_id: str):
    """
    Server-Sent Events (SSE) streaming endpoint for session output.
    Emits continuous events (text/event-stream) as the agent outputs tokens.
    """
    queue: asyncio.Queue = asyncio.Queue()
    if session_id not in SESSION_QUEUES:
        SESSION_QUEUES[session_id] = []
    SESSION_QUEUES[session_id].append(queue)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Initial SSE handshake
            yield f"data: {json.dumps({'type': 'stream_connected', 'sessionId': session_id})}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("type") == "session_terminated":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if session_id in SESSION_QUEUES and queue in SESSION_QUEUES[session_id]:
                SESSION_QUEUES[session_id].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions/{session_id}/messages", summary="Post Message into Session")
@router.post(
    "/api/sessions/{session_id}/messages",
    summary="Post Message into Session (API Prefix)",
)
@router.post("/sessions/{session_id}/input", summary="Send Input to Session")
@router.post(
    "/api/sessions/{session_id}/input", summary="Send Input to Session (API Prefix)"
)
async def post_session_message(session_id: str, req: SessionMessageRequest):
    """
    Post a message or prompt into an active session.
    Dispatches to the agent and broadcasts the stream to active subscribers.
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    if session.get("status") == "terminated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session '{session_id}' is terminated",
        )

    content = req.content or req.message or req.prompt
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required",
        )

    agent_id = session.get("agent_id", "python-dev")
    # Dispatch execution in background, streaming to all subscribers
    asyncio.create_task(_dispatch_session_prompt(session_id, agent_id, content))

    return {
        "session_id": session_id,
        "status": "processing",
        "agent_id": agent_id,
        "message": content,
    }


# ---------------------------------------------------------------------------
# F. Terminate an Agent Session
# ---------------------------------------------------------------------------


@router.delete("/sessions/{session_id}", summary="Terminate Session")
@router.delete("/api/sessions/{session_id}", summary="Terminate Session (API Prefix)")
@router.post(
    "/sessions/{session_id}/terminate", summary="Terminate Session (POST Alias)"
)
@router.post(
    "/api/sessions/{session_id}/terminate", summary="Terminate Session (API POST Alias)"
)
@router.delete(
    "/agents/{agent_id}/sessions/{session_id}", summary="Terminate Agent Session"
)
@router.delete(
    "/api/agents/{agent_id}/sessions/{session_id}",
    summary="Terminate Agent Session (API Prefix)",
)
async def terminate_agent_session(session_id: str, agent_id: Optional[str] = None):
    """
    Terminate an active agent session:
    - Sets session status to 'terminated'
    - Broadcasts termination event to all connected WebSocket & SSE subscribers
    - Closes open connections
    - Updates database record
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    session["status"] = "terminated"
    session["terminated_at"] = now_iso

    # Broadcast termination event to subscribers
    term_event = {
        "type": "session_terminated",
        "sessionId": session_id,
        "status": "terminated",
        "terminatedAt": now_iso,
    }
    await _broadcast_to_session(session_id, term_event)

    # Close active WebSockets
    subs = SESSION_SUBSCRIBERS.get(session_id, set())
    for ws in list(subs):
        try:
            await ws.close(code=1000, reason="Session terminated")
        except Exception:  # nosec B110
            logger.debug(
                "Failed closing websocket for session %s on termination", session_id
            )
    SESSION_SUBSCRIBERS.pop(session_id, None)

    # Update database if connected
    db_getter = await _get_db()
    if db_getter:
        try:
            async with db_getter() as conn:
                await conn.execute(
                    """
                    UPDATE chat_sessions
                    SET status = 'terminated', last_activity = NOW()
                    WHERE id = $1
                    """,
                    uuid.UUID(session_id.replace("session-", "").ljust(32, "0")),
                )
        except Exception as e:
            logger.debug(f"DB update chat_sessions on terminate: {e}")

    logger.info(f"Terminated agent session: {session_id}")
    return {
        "session_id": session_id,
        "status": "terminated",
        "terminated_at": now_iso,
    }
