"""
pgvector-backed document and brain store for FuzeAgent Brains.

Supports 4-tier brain hierarchy and cross-functional brains:
1. Organization Brain (scope='organization')
2. Cross-Functional Brain (scope='cross_functional', e.g. functional_domain='frontend', 'devops', 'backend')
3. Team Brain (scope='team', team_id=...)
4. Agent Persona Brain (scope='agent', agent_id=...)

Documents are chunked-free for simplicity: one embedding per document
(title + content), stored in `brain_documents` with a vector(384) column and
searched by cosine distance. Falls back to in-memory store when the
database or embedding model is unavailable, so the API never hard-fails.
"""

import asyncio
import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
assert EMBEDDING_DIM == 384, "update the brain_documents DDL in _ensure_table"
_model = None
_table_ready = False


# ---------------------------------------------------------------------------
# Pre-seeded built-in brains (authoritative defaults & in-memory fallback)
# ---------------------------------------------------------------------------
IN_MEMORY_BRAINS: Dict[str, Dict[str, Any]] = {
    "brain_org_global": {
        "id": "brain_org_global",
        "name": "Organization Global Architecture Brain",
        "description": "Enterprise-wide architecture baselines, security standards, and cross-cutting guidelines.",
        "organization_id": "org_default",
        "scope": "organization",
        "functional_domain": None,
        "team_id": None,
        "agent_id": None,
        "is_active": True,
        "tags": ["enterprise", "security", "architecture", "global"],
        "metadata": {
            "tier": 1,
            "access_level": "company_wide",
            "enforce_standards": True,
        },
        "document_count": 12,
        "vector_count": 2400,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-10-16T12:00:00Z",
    },
    "brain_cross_frontend": {
        "id": "brain_cross_frontend",
        "name": "Cross-Functional Frontend Brain",
        "description": "Shared frontend knowledge base across all squads: Design System tokens, microfrontend contracts, and UI accessibility guidelines.",
        "organization_id": "org_default",
        "scope": "cross_functional",
        "functional_domain": "frontend",
        "team_id": None,
        "agent_id": None,
        "is_active": True,
        "tags": ["frontend", "cross-functional", "design-system", "react", "ui"],
        "metadata": {
            "tier": 2,
            "domain": "frontend",
            "shared_with": ["frontend-dev", "ui-architect", "react-dev", "mobile-dev"],
        },
        "document_count": 28,
        "vector_count": 4820,
        "created_at": "2026-02-01T00:00:00Z",
        "updated_at": "2026-10-18T16:00:00Z",
    },
    "brain_cross_devops": {
        "id": "brain_cross_devops",
        "name": "Cross-Functional DevOps & SRE Brain",
        "description": "Shared cloud infrastructure, Kubernetes configurations, CI/CD pipelines, GitOps sync policies, and incident mitigation playbooks.",
        "organization_id": "org_default",
        "scope": "cross_functional",
        "functional_domain": "devops",
        "team_id": None,
        "agent_id": None,
        "is_active": True,
        "tags": ["devops", "sre", "kubernetes", "argocd", "gitops", "prometheus", "loki"],
        "metadata": {
            "tier": 2,
            "domain": "devops",
            "shared_with": ["devops-agent", "sre-agent", "platform-engineer", "security-agent"],
        },
        "document_count": 34,
        "vector_count": 6200,
        "created_at": "2026-02-01T00:00:00Z",
        "updated_at": "2026-10-19T08:30:00Z",
    },
    "brain_cross_backend": {
        "id": "brain_cross_backend",
        "name": "Cross-Functional Backend Brain",
        "description": "Shared backend architectural patterns, API contracts, asyncpg pool strategies, and database migration rules.",
        "organization_id": "org_default",
        "scope": "cross_functional",
        "functional_domain": "backend",
        "team_id": None,
        "agent_id": None,
        "is_active": True,
        "tags": ["backend", "fastapi", "asyncpg", "postgres", "microservices", "api"],
        "metadata": {
            "tier": 2,
            "domain": "backend",
            "shared_with": ["python-dev", "backend-dev", "database-admin"],
        },
        "document_count": 22,
        "vector_count": 3950,
        "created_at": "2026-02-15T00:00:00Z",
        "updated_at": "2026-10-17T14:15:00Z",
    },
    "brain_team_platform": {
        "id": "brain_team_platform",
        "name": "Platform Infrastructure Team Brain",
        "description": "Team-specific operational context, cluster resource allocations, and internal service mesh routing.",
        "organization_id": "org_default",
        "scope": "team",
        "functional_domain": "devops",
        "team_id": "team_platform",
        "agent_id": None,
        "is_active": True,
        "tags": ["team", "platform", "cluster-config", "k8s"],
        "metadata": {
            "tier": 3,
            "team_id": "team_platform",
        },
        "document_count": 15,
        "vector_count": 2840,
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-10-15T11:20:00Z",
    },
    "brain_agent_python_dev": {
        "id": "brain_agent_python_dev",
        "name": "Python Dev Agent Persona Memory",
        "description": "Agent persona-specific memory: Python idioms, test mocks, fast debug recipes, and prompt calibrations.",
        "organization_id": "org_default",
        "scope": "agent",
        "functional_domain": "backend",
        "team_id": "team_platform",
        "agent_id": "python-dev",
        "is_active": True,
        "tags": ["agent", "persona", "python", "developer"],
        "metadata": {
            "tier": 4,
            "agent_id": "python-dev",
        },
        "document_count": 9,
        "vector_count": 1650,
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-10-19T09:10:00Z",
    },
    "brain_agent_react_dev": {
        "id": "brain_agent_react_dev",
        "name": "React Frontend Dev Agent Persona Memory",
        "description": "Agent persona-specific memory: React hooks, Vite bundler nuances, CSS module conventions, and UI component tests.",
        "organization_id": "org_default",
        "scope": "agent",
        "functional_domain": "frontend",
        "team_id": "team_frontend",
        "agent_id": "react-dev",
        "is_active": True,
        "tags": ["agent", "persona", "react", "frontend"],
        "metadata": {
            "tier": 4,
            "agent_id": "react-dev",
        },
        "document_count": 11,
        "vector_count": 2100,
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-10-19T09:15:00Z",
    },
}


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


async def _embed(text: str) -> List[float]:
    loop = asyncio.get_event_loop()
    vec = await loop.run_in_executor(
        None, lambda: _get_model().encode(text, normalize_embeddings=True).tolist()
    )
    return vec


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


async def _ensure_table(conn) -> None:
    global _table_ready
    if _table_ready:
        return
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS brains (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            organization_id TEXT NOT NULL DEFAULT 'org_default',
            scope TEXT NOT NULL DEFAULT 'organization',
            functional_domain TEXT,
            team_id TEXT,
            agent_id TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            tags TEXT[] NOT NULL DEFAULT '{}',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            document_count INTEGER NOT NULL DEFAULT 0,
            vector_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_brains_org ON brains(organization_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_brains_scope ON brains(scope)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_brains_domain ON brains(functional_domain)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_brains_team ON brains(team_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_brains_agent ON brains(agent_id)")

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS brain_documents (
            id TEXT PRIMARY KEY,
            brain_id TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General',
            content TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT 'unknown',
            tags TEXT[] NOT NULL DEFAULT '{}',
            embedding vector(384),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_brain_documents_brain ON brain_documents(brain_id)"
    )

    # Seed default brains if empty
    count = await conn.fetchval("SELECT COUNT(*) FROM brains")
    if count == 0:
        for b in IN_MEMORY_BRAINS.values():
            await conn.execute(
                """
                INSERT INTO brains (
                    id, name, description, organization_id, scope, functional_domain,
                    team_id, agent_id, is_active, tags, metadata, document_count, vector_count,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                b["id"],
                b["name"],
                b["description"],
                b["organization_id"],
                b["scope"],
                b.get("functional_domain"),
                b.get("team_id"),
                b.get("agent_id"),
                b["is_active"],
                b.get("tags", []),
                b.get("metadata", {}),
                b.get("document_count", 0),
                b.get("vector_count", 0),
            )

    _table_ready = True


def _row_to_brain(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "organization_id": row["organization_id"],
        "scope": row["scope"],
        "functional_domain": row["functional_domain"],
        "team_id": row["team_id"],
        "agent_id": row["agent_id"],
        "is_active": row["is_active"],
        "tags": list(row["tags"] or []),
        "metadata": row["metadata"] if isinstance(row["metadata"], dict) else {},
        "document_count": row["document_count"],
        "vector_count": row["vector_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
    }


def _row_to_doc(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "content": row["content"],
        "author": row["author"],
        "updatedAt": row["created_at"].isoformat() if row["created_at"] else "",
        "tags": list(row["tags"] or []),
        "chunksCount": max(1, len(row["content"]) // 250),
    }


# ---------------------------------------------------------------------------
# Brain CRUD & Association Operations
# ---------------------------------------------------------------------------


async def list_brains(
    organization_id: Optional[str] = None,
    scope: Optional[str] = None,
    functional_domain: Optional[str] = None,
    team_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List brains for the company/org with optional scope and domain filtering."""
    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            query = "SELECT * FROM brains WHERE 1=1"
            params: List[Any] = []
            idx = 1

            if organization_id:
                query += f" AND organization_id = ${idx}"
                params.append(organization_id)
                idx += 1
            if scope:
                query += f" AND scope = ${idx}"
                params.append(scope)
                idx += 1
            if functional_domain:
                query += f" AND functional_domain = ${idx}"
                params.append(functional_domain)
                idx += 1
            if team_id:
                query += f" AND team_id = ${idx}"
                params.append(team_id)
                idx += 1
            if agent_id:
                query += f" AND agent_id = ${idx}"
                params.append(agent_id)
                idx += 1

            query += " ORDER BY created_at ASC"
            rows = await conn.fetch(query, *params)
            if rows:
                return [_row_to_brain(r) for r in rows]
    except Exception as e:
        logger.warning(f"brain_store.list_brains fallback to in-memory: {e}")

    # Fallback to in-memory store
    results = []
    for b in IN_MEMORY_BRAINS.values():
        if organization_id and b.get("organization_id") != organization_id:
            continue
        if scope and b.get("scope") != scope:
            continue
        if functional_domain and b.get("functional_domain") != functional_domain:
            continue
        if team_id and b.get("team_id") != team_id:
            continue
        if agent_id and b.get("agent_id") != agent_id:
            continue
        results.append(copy.deepcopy(b))
    return results


async def get_brain(brain_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a single brain by ID."""
    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            row = await conn.fetchrow("SELECT * FROM brains WHERE id = $1", brain_id)
            if row:
                return _row_to_brain(row)
    except Exception as e:
        logger.warning(f"brain_store.get_brain fallback to in-memory: {e}")

    if brain_id in IN_MEMORY_BRAINS:
        return copy.deepcopy(IN_MEMORY_BRAINS[brain_id])
    return None


async def create_brain(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new brain scoped to org, team, agent persona, or cross-functional domain."""
    brain_id = data.get("id") or f"brain_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    brain_entry = {
        "id": brain_id,
        "name": data.get("name", "Untitled Brain"),
        "description": data.get("description", ""),
        "organization_id": data.get("organization_id", "org_default"),
        "scope": data.get("scope", "organization"),
        "functional_domain": data.get("functional_domain"),
        "team_id": data.get("team_id"),
        "agent_id": data.get("agent_id"),
        "is_active": data.get("is_active", True),
        "tags": list(data.get("tags", [])),
        "metadata": dict(data.get("metadata", {})),
        "document_count": int(data.get("document_count", 0)),
        "vector_count": int(data.get("vector_count", 0)),
        "created_at": now,
        "updated_at": now,
    }

    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            await conn.execute(
                """
                INSERT INTO brains (
                    id, name, description, organization_id, scope, functional_domain,
                    team_id, agent_id, is_active, tags, metadata, document_count, vector_count,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    scope = EXCLUDED.scope,
                    functional_domain = EXCLUDED.functional_domain,
                    team_id = EXCLUDED.team_id,
                    agent_id = EXCLUDED.agent_id,
                    is_active = EXCLUDED.is_active,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                brain_entry["id"],
                brain_entry["name"],
                brain_entry["description"],
                brain_entry["organization_id"],
                brain_entry["scope"],
                brain_entry["functional_domain"],
                brain_entry["team_id"],
                brain_entry["agent_id"],
                brain_entry["is_active"],
                brain_entry["tags"],
                brain_entry["metadata"],
                brain_entry["document_count"],
                brain_entry["vector_count"],
            )
    except Exception as e:
        logger.warning(f"brain_store.create_brain persisting in memory only: {e}")

    IN_MEMORY_BRAINS[brain_id] = copy.deepcopy(brain_entry)
    return brain_entry


async def update_brain(brain_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update brain metadata, configuration, or active state."""
    existing = await get_brain(brain_id)
    if not existing:
        return None

    updated = copy.deepcopy(existing)
    for field in [
        "name",
        "description",
        "organization_id",
        "scope",
        "functional_domain",
        "team_id",
        "agent_id",
        "is_active",
        "tags",
        "metadata",
    ]:
        if field in data and data[field] is not None:
            updated[field] = data[field]

    now = datetime.now(timezone.utc).isoformat()
    updated["updated_at"] = now

    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            await conn.execute(
                """
                UPDATE brains SET
                    name = $2,
                    description = $3,
                    organization_id = $4,
                    scope = $5,
                    functional_domain = $6,
                    team_id = $7,
                    agent_id = $8,
                    is_active = $9,
                    tags = $10,
                    metadata = $11,
                    updated_at = NOW()
                WHERE id = $1
                """,
                brain_id,
                updated["name"],
                updated["description"],
                updated["organization_id"],
                updated["scope"],
                updated["functional_domain"],
                updated["team_id"],
                updated["agent_id"],
                updated["is_active"],
                updated["tags"],
                updated["metadata"],
            )
    except Exception as e:
        logger.warning(f"brain_store.update_brain persisting in memory only: {e}")

    IN_MEMORY_BRAINS[brain_id] = copy.deepcopy(updated)
    return updated


async def delete_brain(brain_id: str) -> bool:
    """Delete a brain and associated documents."""
    found = False
    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            res = await conn.execute("DELETE FROM brains WHERE id = $1", brain_id)
            await conn.execute("DELETE FROM brain_documents WHERE brain_id = $1", brain_id)
            if "DELETE 1" in res:
                found = True
    except Exception as e:
        logger.warning(f"brain_store.delete_brain error: {e}")

    if brain_id in IN_MEMORY_BRAINS:
        del IN_MEMORY_BRAINS[brain_id]
        found = True

    return found


async def associate_brain(brain_id: str, association: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Associate a brain with an org, team, agent persona, or cross-functional domain.
    """
    scope = association.get("scope")
    if not scope:
        raise ValueError("Association requires 'scope'")

    payload = {"scope": scope}
    if scope == "organization":
        payload["organization_id"] = association.get("organization_id", "org_default")
        payload["team_id"] = None
        payload["agent_id"] = None
        payload["functional_domain"] = None
    elif scope == "team":
        payload["team_id"] = association.get("team_id")
        payload["agent_id"] = None
        if "functional_domain" in association:
            payload["functional_domain"] = association.get("functional_domain")
    elif scope == "agent":
        payload["agent_id"] = association.get("agent_id")
        if "team_id" in association:
            payload["team_id"] = association.get("team_id")
        if "functional_domain" in association:
            payload["functional_domain"] = association.get("functional_domain")
    elif scope == "cross_functional":
        payload["functional_domain"] = association.get("functional_domain")
        payload["team_id"] = None
        payload["agent_id"] = None
    else:
        raise ValueError(f"Unsupported scope '{scope}'")

    if "metadata" in association:
        payload["metadata"] = association["metadata"]

    return await update_brain(brain_id, payload)


async def get_agent_brains(
    agent_id: str,
    team_id: Optional[str] = None,
    functional_domain: Optional[str] = None,
    organization_id: Optional[str] = "org_default",
) -> Dict[str, Any]:
    """
    Resolves the full multi-tier brain hierarchy for an agent:
    1. Agent Persona Brain (scope='agent', agent_id=agent_id)
    2. Team Brain (scope='team', team_id=team_id)
    3. Cross-Functional Brain (scope='cross_functional', functional_domain=functional_domain)
       - e.g. all frontend agents share the frontend cross-functional brain,
       - all devops agents share the devops cross-functional brain.
    4. Organization Global Brain (scope='organization', organization_id=organization_id)
    """
    # Auto-infer functional_domain if not provided
    inferred_domain = functional_domain
    if not inferred_domain:
        aid = agent_id.lower()
        if any(term in aid for term in ["react", "frontend", "ui", "front", "mobile", "css", "web"]):
            inferred_domain = "frontend"
        elif any(term in aid for term in ["devops", "sre", "infra", "k8s", "argocd", "ops", "cloud"]):
            inferred_domain = "devops"
        elif any(term in aid for term in ["python", "backend", "api", "db", "server", "sql"]):
            inferred_domain = "backend"

    all_brains = await list_brains(organization_id=organization_id)

    agent_brain = None
    team_brain = None
    cross_functional_brain = None
    org_brain = None

    for b in all_brains:
        scope = b.get("scope")
        if scope == "agent" and b.get("agent_id") == agent_id:
            agent_brain = b
        elif scope == "team" and team_id and b.get("team_id") == team_id:
            team_brain = b
        elif (
            scope == "cross_functional"
            and inferred_domain
            and b.get("functional_domain") == inferred_domain
        ):
            cross_functional_brain = b
        elif scope == "organization":
            org_brain = b

    # If any specific tier wasn't found in DB, check in-memory defaults
    if not agent_brain and f"brain_agent_{agent_id}" in IN_MEMORY_BRAINS:
        agent_brain = IN_MEMORY_BRAINS[f"brain_agent_{agent_id}"]
    if not cross_functional_brain and inferred_domain:
        cf_key = f"brain_cross_{inferred_domain}"
        if cf_key in IN_MEMORY_BRAINS:
            cross_functional_brain = IN_MEMORY_BRAINS[cf_key]
    if not org_brain and "brain_org_global" in IN_MEMORY_BRAINS:
        org_brain = IN_MEMORY_BRAINS["brain_org_global"]

    resolved_list = []
    hierarchy_layers = []

    if agent_brain:
        resolved_list.append(agent_brain)
        hierarchy_layers.append({"tier": 1, "scope": "agent", "brain_id": agent_brain["id"], "name": agent_brain["name"]})
    if team_brain:
        resolved_list.append(team_brain)
        hierarchy_layers.append({"tier": 2, "scope": "team", "brain_id": team_brain["id"], "name": team_brain["name"]})
    if cross_functional_brain:
        resolved_list.append(cross_functional_brain)
        hierarchy_layers.append({
            "tier": 3,
            "scope": "cross_functional",
            "functional_domain": inferred_domain,
            "brain_id": cross_functional_brain["id"],
            "name": cross_functional_brain["name"],
        })
    if org_brain:
        resolved_list.append(org_brain)
        hierarchy_layers.append({"tier": 4, "scope": "organization", "brain_id": org_brain["id"], "name": org_brain["name"]})

    return {
        "agent_id": agent_id,
        "team_id": team_id,
        "functional_domain": inferred_domain,
        "organization_id": organization_id,
        "total_brains": len(resolved_list),
        "brains": resolved_list,
        "hierarchy": hierarchy_layers,
    }


# ---------------------------------------------------------------------------
# Document & Search Operations
# ---------------------------------------------------------------------------


async def list_documents(brain_id: str) -> Optional[List[Dict[str, Any]]]:
    """Return stored docs for a brain, or None if the store is unavailable."""
    try:
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            rows = await conn.fetch(
                "SELECT id, title, category, content, author, tags, created_at "
                "FROM brain_documents WHERE brain_id = $1 ORDER BY created_at DESC",
                brain_id,
            )
            return [_row_to_doc(r) for r in rows]
    except Exception as e:
        logger.warning(f"brain_store.list_documents unavailable: {e}")
        return None


async def add_document(
    brain_id: str,
    title: str,
    content: str,
    category: str = "General",
    author: str = "unknown",
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Embed and persist a document. Returns the doc, or None if unavailable."""
    try:
        vec = await _embed(f"{title}\n{content}")
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            row = await conn.fetchrow(
                "INSERT INTO brain_documents "
                "(id, brain_id, title, category, content, author, tags, embedding) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8::vector) "
                "RETURNING id, title, category, content, author, tags, created_at",
                doc_id,
                brain_id,
                title,
                category,
                content,
                author,
                tags or [],
                _vec_literal(vec),
            )
            await conn.execute(
                "UPDATE brains SET document_count = document_count + 1 WHERE id = $1",
                brain_id,
            )
            return _row_to_doc(row)
    except Exception as e:
        logger.warning(f"brain_store.add_document unavailable: {e}")
        return None


async def search(
    brain_id: str, query: str, limit: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """Cosine-similarity search. Returns docs with a `score`, or None if unavailable."""
    try:
        vec = await _embed(query)
        async with get_db_connection() as conn:
            await _ensure_table(conn)
            rows = await conn.fetch(
                "SELECT id, title, category, content, author, tags, created_at, "
                "1 - (embedding <=> $2::vector) AS score "
                "FROM brain_documents WHERE brain_id = $1 AND embedding IS NOT NULL "
                "ORDER BY embedding <=> $2::vector LIMIT $3",
                brain_id,
                _vec_literal(vec),
                limit,
            )
            out = []
            for r in rows:
                d = _row_to_doc(r)
                d["score"] = float(r["score"])
                out.append(d)
            return out
    except Exception as e:
        logger.warning(f"brain_store.search unavailable: {e}")
        return None
