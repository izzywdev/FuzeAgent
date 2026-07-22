"""Read a repo's projection inputs from disk.

Loads ``.fuze/manifest.json`` and every ``agent-templates/roles/*/role.json`` from a
checked-out repo tree (GitOps: the git ref is the source of truth, never live state).
Role ``extends`` inheritance is intentionally NOT flattened here — the projection reads
only ``role``, ``name``, ``description``, ``services``, ``metadata``, ``coordinator``
and the optional ``a2a`` block, none of which are inherited from ``_base`` in practice.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_manifest(repo_root: str | Path) -> dict:
    path = Path(repo_root) / ".fuze" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_roles(repo_root: str | Path) -> dict[str, dict]:
    roles_dir = Path(repo_root) / "agent-templates" / "roles"
    roles: dict[str, dict] = {}
    if not roles_dir.is_dir():
        return roles
    for child in sorted(roles_dir.iterdir()):
        role_file = child / "role.json"
        if role_file.is_file():
            role = json.loads(role_file.read_text(encoding="utf-8"))
            roles[role.get("role", child.name)] = role
    return roles


def load_repo(repo_root: str | Path) -> tuple[dict, dict[str, dict]]:
    return load_manifest(repo_root), load_roles(repo_root)
