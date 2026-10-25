"""
agent_persona_service.py
Agent Persona & Avatar Studio service for FuzeAgent.
Provides:
- Human naming (e.g. 'John', 'Sarah') alongside technical role ('Backend Engineer')
- SVG avatar generator with dynamic gradients, initials, and deterministic seeds
- Avatar S3 bucket persistence in brains/{brain_id}/avatars/{agent_id}/
- Picture placeholder fallback
"""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from s3_storage import s3_storage

logger = logging.getLogger(__name__)

# Predefined human name defaults for standard roles if not assigned
DEFAULT_AGENT_PERSONAS: Dict[str, Dict[str, str]] = {
    "python-dev": {
        "human_name": "John",
        "role_title": "Senior Backend Engineer",
        "functional_domain": "backend",
        "color_theme": "#3B82F6",  # Electric Blue
        "bio": "Specializes in Python, FastAPI, asyncpg, and high-performance microservices.",
    },
    "react-dev": {
        "human_name": "Sarah",
        "role_title": "Frontend Architect",
        "functional_domain": "frontend",
        "color_theme": "#10B981",  # Emerald Green
        "bio": "Expert in React 19, Design System tokens, microfrontends, and accessible UI/UX.",
    },
    "devops-agent": {
        "human_name": "Alex",
        "role_title": "DevOps & SRE Specialist",
        "functional_domain": "devops",
        "color_theme": "#F59E0B",  # Amber
        "bio": "Coordinates Kubernetes clusters, ArgoCD GitOps syncs, Prometheus alerting, and cloud security.",
    },
    "qa-agent": {
        "human_name": "Elena",
        "role_title": "Lead Quality & Test Engineer",
        "functional_domain": "qa",
        "color_theme": "#8B5CF6",  # Purple
        "bio": "Designs end-to-end Playwright suites, API contract validation, and load testing pipelines.",
    },
}


class AgentPersona(BaseModel):
    agent_id: str
    human_name: str
    role_title: str
    functional_domain: str = "general"
    avatar_url: Optional[str] = None
    avatar_svg: Optional[str] = None
    bio: Optional[str] = None
    color_theme: str = "#6366F1"


def generate_svg_avatar(
    human_name: str, role_title: str, seed: Optional[str] = None
) -> str:
    """
    Generates a sleek, modern SVG avatar with dual-tone gradient background,
    geometric avatar silhouette, and stylized initials badge.
    """
    initials = "".join(part[0].upper() for part in human_name.split()[:2]) or "AG"
    h = hashlib.sha256((seed or f"{human_name}_{role_title}").encode()).hexdigest()

    # Deterministic palette selection
    palettes = [
        ("#6366F1", "#8B5CF6"),  # Indigo to Purple
        ("#3B82F6", "#06B6D4"),  # Blue to Cyan
        ("#10B981", "#14B8A6"),  # Emerald to Teal
        ("#F59E0B", "#EF4444"),  # Amber to Red
        ("#EC4899", "#8B5CF6"),  # Pink to Purple
    ]
    color_idx = int(h[:2], 16) % len(palettes)
    c1, c2 = palettes[color_idx]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="grad_{h[:6]}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <clipPath id="circleClip">
      <circle cx="64" cy="64" r="60"/>
    </clipPath>
  </defs>
  <circle cx="64" cy="64" r="62" fill="none" stroke="{c1}" stroke-width="2" stroke-dasharray="6,4"/>
  <g clip-path="url(#circleClip)">
    <rect width="128" height="128" fill="url(#grad_{h[:6]})"/>
    <circle cx="64" cy="50" r="22" fill="#FFFFFF" fill-opacity="0.85"/>
    <path d="M28 116 C28 88, 100 88, 100 116 Z" fill="#FFFFFF" fill-opacity="0.85"/>
  </g>
  <rect x="76" y="76" width="44" height="44" rx="22" fill="#0F172A" stroke="#FFFFFF" stroke-width="2"/>
  <text x="98" y="103" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="14" font-weight="700" fill="#38BDF8" text-anchor="middle">{initials}</text>
</svg>"""
    return svg


class AgentPersonaService:
    def __init__(self):
        self._personas: Dict[str, AgentPersona] = {}
        self._init_defaults()

    def _init_defaults(self):
        for aid, data in DEFAULT_AGENT_PERSONAS.items():
            svg = generate_svg_avatar(data["human_name"], data["role_title"], seed=aid)
            self._personas[aid] = AgentPersona(
                agent_id=aid,
                human_name=data["human_name"],
                role_title=data["role_title"],
                functional_domain=data["functional_domain"],
                color_theme=data["color_theme"],
                bio=data["bio"],
                avatar_svg=svg,
                avatar_url=f"/api/v1/agents/{aid}/avatar",
            )

    def get_persona(self, agent_id: str) -> AgentPersona:
        if agent_id in self._personas:
            return self._personas[agent_id]

        # Generate default name if missing
        human_name = f"Agent {agent_id.replace('-', ' ').title()}"
        role_title = "AI Co-Pilot Specialist"
        svg = generate_svg_avatar(human_name, role_title, seed=agent_id)
        persona = AgentPersona(
            agent_id=agent_id,
            human_name=human_name,
            role_title=role_title,
            avatar_svg=svg,
            avatar_url=f"/api/v1/agents/{agent_id}/avatar",
        )
        self._personas[agent_id] = persona
        return persona

    def update_persona(
        self,
        agent_id: str,
        human_name: Optional[str] = None,
        role_title: Optional[str] = None,
        bio: Optional[str] = None,
        organization_id: str = "org_default",
    ) -> AgentPersona:
        current = self.get_persona(agent_id)
        if human_name:
            current.human_name = human_name
        if role_title:
            current.role_title = role_title
        if bio:
            current.bio = bio

        # Regenerate avatar
        current.avatar_svg = generate_svg_avatar(
            current.human_name, current.role_title, seed=agent_id
        )

        # Upload to S3 bucket if available
        brain_id = f"brain_agent_{agent_id}"
        try:
            s3_storage.upload_file(
                organization_id=organization_id,
                brain_id=brain_id,
                data=current.avatar_svg.encode("utf-8"),
                filename=f"{agent_id}_avatar.svg",
                category="avatars",
                content_type="image/svg+xml",
            )
        except Exception as e:
            logger.warning(f"Could not persist avatar to S3: {e}")

        self._personas[agent_id] = current
        return current

    def list_personas(self) -> List[AgentPersona]:
        return list(self._personas.values())


# Global persona service instance
agent_persona_service = AgentPersonaService()
