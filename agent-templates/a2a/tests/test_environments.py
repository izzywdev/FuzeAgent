"""Unit tests for FA-14: resolving a role's ``environment`` -> a provider id.

Two layers:

* ``EnvironmentResolver`` (``a2a/environments.py``) — the basename->name->id lookup
  itself, its caching, and its errors, exercised directly against tmp_path fixtures
  (mirrors ``providers/provision.py``'s ``_env_basename_to_name`` + ``env_ids.get``).
* ``A2AAdapter._provision`` / ``_resolve_environment_id`` — the precedence chain
  (tenant override -> resolve(role.environment) -> role names none -> None), and that
  an unresolvable NAMED environment raises rather than silently producing ``None``.
"""

from __future__ import annotations

import json

import pytest
from a2a.adapter import A2AAdapter
from a2a.config import ProviderBinding, ServerConfig, TenantConfig
from a2a.environments import EnvironmentResolutionError, EnvironmentResolver

# --------------------------------------------------------------------------- #
# EnvironmentResolver
# --------------------------------------------------------------------------- #


def _write_env_file(envs_dir, basename, name):
    envs_dir.mkdir(parents=True, exist_ok=True)
    (envs_dir / f"{basename}.json").write_text(
        json.dumps({"name": name, "config": {"type": "cloud"}}), encoding="utf-8"
    )


def _write_ids(state_dir, ids):
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "environment-ids.json").write_text(json.dumps(ids), encoding="utf-8")


def test_resolves_known_basename_to_id(tmp_path):
    envs_dir = tmp_path / "environments"
    state_dir = tmp_path / "state"
    _write_env_file(envs_dir, "cloud-product", "fuzeplan-cloud-product")
    _write_ids(state_dir, {"fuzeplan-cloud-product": "env-123"})

    resolver = EnvironmentResolver(environments_dir=envs_dir, state_dir=state_dir)
    assert resolver("cloud-product") == "env-123"


def test_reads_are_cached_not_reread_per_call(tmp_path, monkeypatch):
    envs_dir = tmp_path / "environments"
    state_dir = tmp_path / "state"
    _write_env_file(envs_dir, "cloud-product", "fuzeplan-cloud-product")
    _write_ids(state_dir, {"fuzeplan-cloud-product": "env-123"})

    resolver = EnvironmentResolver(environments_dir=envs_dir, state_dir=state_dir)
    assert resolver("cloud-product") == "env-123"

    # Blow away both files: a cached resolver must not need to re-read them.
    (envs_dir / "cloud-product.json").unlink()
    (state_dir / "environment-ids.json").unlink()

    assert resolver("cloud-product") == "env-123"


def test_unknown_basename_raises_not_none(tmp_path):
    resolver = EnvironmentResolver(
        environments_dir=tmp_path / "environments", state_dir=tmp_path / "state"
    )
    with pytest.raises(EnvironmentResolutionError):
        resolver("does-not-exist")


def test_name_with_no_provisioned_id_raises_not_none(tmp_path):
    envs_dir = tmp_path / "environments"
    state_dir = tmp_path / "state"
    _write_env_file(envs_dir, "cloud-product", "fuzeplan-cloud-product")
    _write_ids(state_dir, {"some-other-env": "env-999"})  # our name absent

    resolver = EnvironmentResolver(environments_dir=envs_dir, state_dir=state_dir)
    with pytest.raises(EnvironmentResolutionError):
        resolver("cloud-product")


def test_missing_state_dir_still_raises_for_a_named_environment(tmp_path):
    envs_dir = tmp_path / "environments"
    _write_env_file(envs_dir, "cloud-product", "fuzeplan-cloud-product")
    # state_dir deliberately never created / never written to.

    resolver = EnvironmentResolver(
        environments_dir=envs_dir, state_dir=tmp_path / "state-does-not-exist"
    )
    with pytest.raises(EnvironmentResolutionError):
        resolver("cloud-product")


# --------------------------------------------------------------------------- #
# A2AAdapter provisioning precedence (FA-14 AC2)
# --------------------------------------------------------------------------- #


class _FakeProvider:
    def ensure_agent(self, manifest, multiagent=None):
        return {"name": manifest.get("role", "x"), "id": "agent-1", "version": "1"}

    def create_session(
        self, agent_id, version, environment_id, vault_ids=None, memory_resources=None, title=None
    ):
        return "sess-1"


def _cfg_and_tenant(*, environment_id=None):
    tenant = TenantConfig(
        tenant="FuzePlan",
        repo="izzywdev/FuzePlan",
        enabled=True,
        provider=ProviderBinding(name="fake", environment_id=environment_id),
    )
    cfg = ServerConfig(enabled=True, tenants=(tenant,))
    return cfg, tenant


def _noop_resolver(_tenant):
    return {}, {}


def test_role_naming_environment_resolves_to_id():
    cfg, tenant = _cfg_and_tenant()
    calls = []

    def env_resolver(basename):
        calls.append(basename)
        return "env-resolved-1"

    a = A2AAdapter(cfg, _FakeProvider(), _noop_resolver, environment_resolver=env_resolver)
    role = {"role": "product-manager", "environment": "cloud-product"}

    agent_id, version, environment_id = a._provision(tenant, role)

    assert environment_id == "env-resolved-1"
    assert calls == ["cloud-product"]  # never null, resolved via the role's env


def test_tenant_provider_environment_id_takes_precedence():
    cfg, tenant = _cfg_and_tenant(environment_id="tenant-env-override")

    def env_resolver(basename):
        raise AssertionError("must not be called: tenant.provider.environment_id wins")

    a = A2AAdapter(cfg, _FakeProvider(), _noop_resolver, environment_resolver=env_resolver)
    role = {"role": "product-manager", "environment": "cloud-product"}

    _, _, environment_id = a._provision(tenant, role)

    assert environment_id == "tenant-env-override"


def test_role_naming_no_environment_resolves_to_none_legitimately():
    cfg, tenant = _cfg_and_tenant()

    def env_resolver(basename):
        raise AssertionError("must not be called: role names no environment")

    a = A2AAdapter(cfg, _FakeProvider(), _noop_resolver, environment_resolver=env_resolver)
    role = {"role": "product-manager"}  # no "environment" key at all

    _, _, environment_id = a._provision(tenant, role)

    assert environment_id is None


def test_unresolvable_named_environment_raises_never_null():
    cfg, tenant = _cfg_and_tenant()

    def env_resolver(basename):
        raise EnvironmentResolutionError(f"no such environment: {basename}")

    a = A2AAdapter(cfg, _FakeProvider(), _noop_resolver, environment_resolver=env_resolver)
    role = {"role": "product-manager", "environment": "totally-unknown"}

    with pytest.raises(EnvironmentResolutionError):
        a._provision(tenant, role)


def test_default_environment_resolver_is_shared_env_resolver_instance():
    """Constructing an adapter without ``environment_resolver`` still wires a real,
    cached ``EnvironmentResolver`` (built once at __init__, not read per call)."""
    cfg, tenant = _cfg_and_tenant()
    a = A2AAdapter(cfg, _FakeProvider(), _noop_resolver)
    assert isinstance(a.resolve_environment_id, EnvironmentResolver)


# --------------------------------------------------------------------------- #
# End-to-end: send_message actually passes the resolved id into create_session
# --------------------------------------------------------------------------- #


def test_send_message_passes_resolved_environment_id_to_create_session(fuzeplan_repo):
    from a2a.authz import AuthContext
    from a2a.loader import load_repo

    manifest, roles = load_repo(fuzeplan_repo)
    roles = dict(roles)
    roles["product-manager"] = {**roles["product-manager"], "environment": "cloud-product"}

    def resolver(_tenant):
        return manifest, roles

    class RecordingProvider(_FakeProvider):
        def __init__(self):
            self.seen_environment_ids = []

        def create_session(
            self, agent_id, version, environment_id, vault_ids=None, memory_resources=None,
            title=None,
        ):
            self.seen_environment_ids.append(environment_id)
            return "sess-1"

        def run_until_block(self, session_id, prompt=None):
            return {"text": "done", "status": "idle", "pending": None}

    cfg = ServerConfig(
        enabled=True,
        tenants=(
            TenantConfig(
                tenant="FuzePlan",
                repo="izzywdev/FuzePlan",
                enabled=True,
                provider=ProviderBinding(name="fake"),
            ),
        ),
    )
    prov = RecordingProvider()
    a = A2AAdapter(cfg, prov, resolver, environment_resolver=lambda basename: "env-e2e-1")

    params = {
        "tenant": "FuzePlan",
        "message": {
            "messageId": "m1",
            "role": "ROLE_USER",
            "parts": [{"text": "hi"}],
            "metadata": {"skillId": "product-manager"},
        },
    }
    out = a.send_message(params, AuthContext(caller="FuzeSales"))

    assert out["task"]["status"]["state"] == "TASK_STATE_COMPLETED"
    assert prov.seen_environment_ids == ["env-e2e-1"]  # never None/null
