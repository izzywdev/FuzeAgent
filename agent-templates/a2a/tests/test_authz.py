"""Unit tests for the callee-enforced allowlist (authz.md).

The security-critical property is FAIL-CLOSED: absent/empty ``providesTo`` denies.
"""
from __future__ import annotations

import pytest
from a2a.authz import AuthContext, Decision, authorize, valid_caller_identity


def ctx(caller="FuzeSales", scopes=frozenset(), authenticated=True):
    return AuthContext(caller=caller, scopes=scopes, authenticated=authenticated)


# --- step 4: providesTo allowlist ------------------------------------------
def test_absent_providesto_denies_fail_closed():
    manifest = {"repo": "izzywdev/FuzePlan"}  # no providesTo
    assert authorize(ctx(), manifest).decision is Decision.DENY


def test_empty_providesto_denies():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": []}
    assert authorize(ctx(), manifest).decision is Decision.DENY


def test_caller_not_in_providesto_denies():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": ["FuzeService"]}
    assert authorize(ctx(caller="FuzeSales"), manifest).decision is Decision.DENY


def test_allowlisted_caller_allowed():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": ["FuzeSales", "FuzeService"]}
    res = authorize(ctx(caller="FuzeSales"), manifest)
    assert res.decision is Decision.ALLOW and res.allowed


def test_dependson_grants_nothing():
    # A caller listing the callee in its OWN dependsOn must not self-grant.
    manifest = {"repo": "izzywdev/FuzePlan", "dependsOn": ["FuzeSales"]}  # no providesTo
    assert authorize(ctx(caller="FuzeSales"), manifest).decision is Decision.DENY


# --- step 1/2: identity -----------------------------------------------------
def test_unauthenticated_denied():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": ["FuzeSales"]}
    assert authorize(ctx(authenticated=False), manifest).decision is Decision.DENY


def test_invalid_caller_identity_denied():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": ["FuzeSales"]}
    assert authorize(ctx(caller="not a repo!!"), manifest).decision is Decision.DENY


@pytest.mark.parametrize(
    "caller,ok",
    [("FuzeSales", True), ("Exec-cto", True), ("izzywdev/FuzeSales", False), ("", False), ("bad name", False)],
)
def test_valid_caller_identity(caller, ok):
    assert valid_caller_identity(caller) is ok


# --- step 3: unknown callee -------------------------------------------------
def test_unknown_callee_denied():
    assert authorize(ctx(), None).decision is Decision.DENY


# --- step 5: skill + scopes -------------------------------------------------
def test_unknown_skill_denied():
    manifest = {"repo": "izzywdev/FuzePlan", "providesTo": ["FuzeSales"]}
    assert authorize(ctx(caller="FuzeSales"), manifest, skill_known=False).decision is Decision.DENY


def test_missing_scope_is_scope_required_not_deny():
    manifest = {"repo": "izzywdev/FuzeInfra", "providesTo": ["FuzeSales"]}
    role = {"role": "cto", "a2a": {"scopes": ["a2a.exec.escalate"]}}
    res = authorize(ctx(caller="FuzeSales", scopes=frozenset()), manifest, skill_role=role)
    assert res.decision is Decision.SCOPE_REQUIRED
    assert res.missing_scopes == ("a2a.exec.escalate",)


def test_present_scope_allows():
    manifest = {"repo": "izzywdev/FuzeInfra", "providesTo": ["FuzeSales"]}
    role = {"role": "cto", "a2a": {"scopes": ["a2a.exec.escalate"]}}
    res = authorize(
        ctx(caller="FuzeSales", scopes=frozenset({"a2a.exec.escalate"})), manifest, skill_role=role
    )
    assert res.decision is Decision.ALLOW
