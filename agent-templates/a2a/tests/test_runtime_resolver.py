"""Unit tests for ``runtime.LocalRepoResolver`` — the tenant checkout path.

The repo-sync init container clones each tenant to ``/repos/<tenant-name>``, so the
resolver MUST key on the tenant name, not the repo slug. Keying on the repo slug only
coincides while every tenant name equals its repo name; a second tenant over an existing
repo (``FuzeInfraOps`` over ``izzywdev/FuzeAgent``) would be read from the wrong tree.
"""

from __future__ import annotations

from pathlib import Path

from a2a.config import TenantConfig
from a2a.runtime import LocalRepoResolver


def test_resolver_reads_from_tenant_name_not_repo_slug(monkeypatch):
    seen: dict[str, Path] = {}

    def fake_load_repo(path):
        seen["path"] = Path(path)
        return ({"repo": "izzywdev/FuzeAgent"}, {})

    monkeypatch.setattr("a2a.runtime.load_repo", fake_load_repo)

    resolver = LocalRepoResolver("/repos")
    # tenant name differs from the repo slug on purpose
    tenant = TenantConfig(tenant="FuzeInfraOps", repo="izzywdev/FuzeAgent", enabled=True)
    resolver(tenant)

    assert seen["path"] == Path("/repos/FuzeInfraOps")  # tenant name, NOT "FuzeAgent"


def test_resolver_coincides_when_name_equals_repo(monkeypatch):
    seen: dict[str, Path] = {}
    monkeypatch.setattr(
        "a2a.runtime.load_repo",
        lambda path: (seen.__setitem__("path", Path(path)), ({}, {}))[1],
    )

    resolver = LocalRepoResolver("/repos")
    tenant = TenantConfig(tenant="FuzePlan", repo="izzywdev/FuzePlan", enabled=True)
    resolver(tenant)

    assert seen["path"] == Path("/repos/FuzePlan")
