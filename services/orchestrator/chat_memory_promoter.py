"""
chat_memory_promoter.py
Post-prompt continuous chat memory promotion engine for FuzeAgent.
Analyzes completed agent conversation turns and promotes reusable learnings to the appropriate
brain tier:
1. Agent Brain: Developer preferences, debugging nuances, prompt calibrations.
2. Team Brain: Sprint decisions, API endpoint contracts, team conventions.
3. Cross-Functional Brain: Shared UI component designs, CI/CD recipes, cross-cutting architectures.
4. Organization Brain: Global security policies, enterprise governance rules, compliance standards.
"""

import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from brain_store import add_document, get_agent_brains
from kafka_pipeline import brain_pipeline
from graph_client import brain_graph

logger = logging.getLogger(__name__)

class ChatMemoryPromoter:
    """
    Background worker that runs asynchronously after prompt completions to digest
    and promote actionable insights into long-term hierarchical brain memories.
    """

    async def digest_session_and_promote(
        self,
        session_id: str,
        agent_id: str,
        user_messages: List[str],
        agent_responses: List[str],
        team_id: Optional[str] = None,
        functional_domain: Optional[str] = None,
        organization_id: str = "org_default"
    ) -> Dict[str, Any]:
        """
        Analyzes conversation turns, extracts key learnings, and persists them into the matching tier.
        """
        if not user_messages or not agent_responses:
            return {"status": "skipped", "reason": "empty_conversation"}

        conversation_text = "\n".join(
            f"User: {u}\nAgent: {a}" for u, a in zip(user_messages, agent_responses)
        )

        logger.info(f"🧠 [MemoryPromoter] Digesting session {session_id} for agent={agent_id}...")

        # 1. Resolve agent brain hierarchy
        hierarchy = await get_agent_brains(
            agent_id=agent_id,
            team_id=team_id,
            functional_domain=functional_domain,
            organization_id=organization_id
        )

        promoted_records = []

        # 2. Rule-based / LLM classification of insights
        # Detect Agent persona level context
        agent_brain_id = f"brain_agent_{agent_id}"
        if any(term in conversation_text.lower() for term in ["prefer", "style", "always use", "shortcut", "remember that i"]):
            summary = self._extract_summary(conversation_text, "User Preference & Persona Insight")
            doc = await add_document(
                brain_id=agent_brain_id,
                title=f"Chat Insight: Session {session_id[:8]} Preference",
                content=summary,
                category="SessionMemory",
                author=agent_id,
                tags=["preference", "chat_promoted", session_id]
            )
            promoted_records.append({"tier": "agent", "brain_id": agent_brain_id, "doc": doc})

        # Detect Team level decisions (API routes, sprint work, database schema)
        if team_id and any(term in conversation_text.lower() for term in ["endpoint", "database", "schema", "sprint", "contract", "bug fix"]):
            team_brain_id = f"brain_team_{team_id}"
            summary = self._extract_summary(conversation_text, "Team Technical Decision & Agreement")
            doc = await add_document(
                brain_id=team_brain_id,
                title=f"Team Architectural Decision ({session_id[:8]})",
                content=summary,
                category="ArchitecturalDecision",
                author=agent_id,
                tags=["team_decision", "api_contract", session_id]
            )
            promoted_records.append({"tier": "team", "brain_id": team_brain_id, "doc": doc})

        # Detect Cross-Functional patterns (Design tokens, Docker, k8s, microfrontends)
        domain = hierarchy.get("functional_domain")
        if domain and any(term in conversation_text.lower() for term in ["design system", "token", "docker", "argocd", "microfrontend", "fastapi", "react"]):
            cf_brain_id = f"brain_cross_{domain}"
            summary = self._extract_summary(conversation_text, f"Cross-Functional {domain.capitalize()} Guideline")
            doc = await add_document(
                brain_id=cf_brain_id,
                title=f"Cross-Functional Pattern ({domain}): {session_id[:8]}",
                content=summary,
                category="StandardPattern",
                author=agent_id,
                tags=[domain, "cross_functional", session_id]
            )
            promoted_records.append({"tier": "cross_functional", "brain_id": cf_brain_id, "doc": doc})

        # Detect Enterprise Governance & Security
        if any(term in conversation_text.lower() for term in ["security", "cve", "authz", "compliance", "gdpr", "quota", "zero trust"]):
            org_brain_id = "brain_org_global"
            summary = self._extract_summary(conversation_text, "Global Security & Compliance Policy")
            doc = await add_document(
                brain_id=org_brain_id,
                title=f"Enterprise Policy Note ({session_id[:8]})",
                content=summary,
                category="Governance",
                author=agent_id,
                tags=["security", "enterprise_policy", session_id]
            )
            promoted_records.append({"tier": "organization", "brain_id": org_brain_id, "doc": doc})

        # 3. Emit Kafka event for audit & pipeline tracking
        await brain_pipeline.emit_event(
            topic="fuzeagent.chat.promoted",
            event_type="brain.chat.promoted",
            payload={
                "session_id": session_id,
                "agent_id": agent_id,
                "team_id": team_id,
                "promoted_count": len(promoted_records),
                "promoted_tiers": [p["tier"] for p in promoted_records]
            },
            key=agent_id
        )

        logger.info(f"✅ [MemoryPromoter] Promoted {len(promoted_records)} insights from session {session_id}.")
        return {
            "status": "completed",
            "session_id": session_id,
            "promoted_count": len(promoted_records),
            "promotions": promoted_records
        }

    def _extract_summary(self, conversation_text: str, topic: str) -> str:
        """Lightweight extractive summary of relevant conversation snippets."""
        lines = [line.strip() for line in conversation_text.split("\n") if line.strip()]
        snippet = "\n".join(lines[:12])
        return (
            f"### Automated Brain Learning: {topic}\n"
            f"Extracted from conversation turn at {datetime.now(timezone.utc).isoformat()}:\n\n"
            f"{snippet}..."
        )

# Global promoter instance
chat_memory_promoter = ChatMemoryPromoter()
