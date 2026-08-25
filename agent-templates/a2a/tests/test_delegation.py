"""Tests for the delegated-principal extension.

The property under test is mostly that things are DENIED. An authz test suite
that only proves "the allowed call is allowed" proves nothing an unconditional
`return ALLOW` would not also pass.

Two of these are the reason the extension exists at all:
  * test_ceo_and_worker_are_distinguishable — under v1 they are not.
  * test_intersection_not_union — the load-bearing rule; a union is not a weaker
    version of it, it is the opposite of it.
"""

import unittest

from a2a.authz import AuthContext, Decision, authorize
from a2a.delegation import (
    EXTENSION_URI, Delegation, DelegationError, DelegationPolicy, SkillClass,
    parse_claims,
)

MANIFEST = {"providesTo": ["FuzeExecutive", "FuzeSales"]}

POLICY_BLOCK = {
    "extension": EXTENSION_URI,
    "authzBaseUrl": "http://fuzefront-backend:3001",
    "skills": {
        "plan-reader": "delegable",
        "plan-editor": "principal-required",
        "plan-purge": "never-delegable",
    },
    "brokerable": {
        "repo:FuzeExecutive": ["plan-reader", "plan-editor"],
        "repo:FuzeSales": ["plan-reader"],
    },
}

CEO_CLAIMS = {"sub": "user:ceo@fuzefront.com",
              "act": {"sub": "repo:FuzeExecutive", "act": {"sub": "agent:a2a-shared"}}}
WORKER_CLAIMS = {"sub": "user:worker@fuzefront.com",
                 "act": {"sub": "repo:FuzeExecutive", "act": {"sub": "agent:a2a-shared"}}}


def policy():
    return DelegationPolicy.from_manifest(POLICY_BLOCK)


def ctx(claims=None, caller="FuzeExecutive"):
    return AuthContext(caller=caller, delegation=parse_claims(claims))


def decide(claims=None, skill="plan-editor", permit=None, caller="FuzeExecutive"):
    return authorize(ctx(claims, caller), MANIFEST, skill_key=skill,
                     delegation_policy=policy(), permit_check=permit)


class BackwardCompatibilityTests(unittest.TestCase):
    """No policy == the callee never adopted the extension == exact v1."""

    def test_without_a_policy_v1_behaviour_is_untouched(self):
        r = authorize(AuthContext(caller="FuzeExecutive"), MANIFEST)
        self.assertIs(r.decision, Decision.ALLOW)

    def test_a_caller_outside_providesto_is_denied_before_any_principal(self):
        """Channel authz still decides first; the extension narrows, never widens."""
        r = decide(CEO_CLAIMS, caller="FuzeSocial", permit=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("providesTo", r.reason)


class ClosedClassificationTests(unittest.TestCase):
    def test_an_unclassified_skill_is_denied_not_defaulted_to_delegable(self):
        """spec.md §3: no fourth bucket, and no default."""
        r = decide(CEO_CLAIMS, skill="plan-undeclared", permit=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("unclassified", r.reason)

    def test_never_delegable_denies_even_a_fully_permitted_subject(self):
        r = decide(CEO_CLAIMS, skill="plan-purge", permit=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("never-delegable", r.reason)

    def test_delegable_needs_no_principal(self):
        r = decide(None, skill="plan-reader")
        self.assertIs(r.decision, Decision.ALLOW)

    def test_an_unknown_class_in_the_policy_is_a_load_error(self):
        bad = dict(POLICY_BLOCK, skills={"x": "maybe"})
        with self.assertRaises(DelegationError):
            DelegationPolicy.from_manifest(bad)

    def test_a_policy_naming_no_extension_is_refused(self):
        bad = dict(POLICY_BLOCK)
        del bad["extension"]
        with self.assertRaises(DelegationError):
            DelegationPolicy.from_manifest(bad)


class PrincipalTests(unittest.TestCase):
    def test_ceo_and_worker_are_distinguishable(self):
        """THE gap. Under v1 both arrive as caller='FuzeExecutive' and both pass."""
        v1_ceo = authorize(AuthContext(caller="FuzeExecutive"), MANIFEST)
        v1_worker = authorize(AuthContext(caller="FuzeExecutive"), MANIFEST)
        self.assertEqual(v1_ceo.decision, v1_worker.decision)  # indistinguishable

        permit = lambda sub, _skill: sub == "user:ceo@fuzefront.com"
        self.assertIs(decide(CEO_CLAIMS, permit=permit).decision, Decision.ALLOW)
        self.assertIs(decide(WORKER_CLAIMS, permit=permit).decision, Decision.DENY)

    def test_principal_required_without_a_subject_is_denied(self):
        r = decide(None, permit=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("no verified subject", r.reason)


class IntersectionTests(unittest.TestCase):
    """effective = permitted(sub) ∩ brokerable(actor). Both, or neither counts."""

    def test_intersection_not_union(self):
        allow_all = lambda *_: True
        deny_all = lambda *_: False

        # Subject permitted, actor may broker -> ALLOW.
        self.assertIs(decide(CEO_CLAIMS, permit=allow_all).decision, Decision.ALLOW)

        # Subject permitted, actor may NOT broker -> DENY. A union would allow.
        sales_claims = {"sub": "user:ceo@fuzefront.com",
                        "act": {"sub": "repo:FuzeSales"}}
        r = authorize(ctx(sales_claims, caller="FuzeSales"), MANIFEST,
                      skill_key="plan-editor", delegation_policy=policy(),
                      permit_check=allow_all)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("broker", r.reason)

        # Actor may broker, subject NOT permitted -> DENY. A union would allow.
        r = decide(CEO_CLAIMS, permit=deny_all)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("not permitted", r.reason)

    def test_an_actor_absent_from_brokerable_brokers_nothing(self):
        """Absence is not a wildcard."""
        claims = {"sub": "user:ceo@fuzefront.com", "act": {"sub": "repo:FuzeUnknown"}}
        r = authorize(ctx(claims), MANIFEST, skill_key="plan-editor",
                      delegation_policy=policy(), permit_check=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)


class FailClosedTests(unittest.TestCase):
    def test_permit_unreachable_is_deny_never_allow(self):
        """DECISION_UNAVAILABLE is a DENY. This is the fail-open branch, spelled out."""
        def boom(*_):
            raise ConnectionError("authz service unreachable")
        r = decide(CEO_CLAIMS, permit=boom)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("unavailable", r.reason)

    def test_no_authz_client_wired_is_deny_not_skip(self):
        r = decide(CEO_CLAIMS, permit=None)
        self.assertIs(r.decision, Decision.DENY)
        self.assertIn("cannot", r.reason)

    def test_missing_skill_key_is_deny(self):
        r = authorize(ctx(CEO_CLAIMS), MANIFEST, delegation_policy=policy(),
                      permit_check=lambda *_: True)
        self.assertIs(r.decision, Decision.DENY)


class ClaimParsingTests(unittest.TestCase):
    def test_untyped_subject_is_rejected(self):
        with self.assertRaises(DelegationError):
            parse_claims({"sub": "izzy", "act": {"sub": "repo:X"}})

    def test_untyped_actor_is_rejected_not_dropped(self):
        """A reference that cannot be evaluated must not be treated as satisfied."""
        with self.assertRaises(DelegationError):
            parse_claims({"sub": "user:a@b.c", "act": {"sub": "FuzeExecutive"}})

    def test_subject_without_an_actor_chain_is_rejected(self):
        with self.assertRaises(DelegationError):
            parse_claims({"sub": "user:a@b.c"})

    def test_no_claims_is_none_not_an_error(self):
        self.assertIsNone(parse_claims(None))
        self.assertIsNone(parse_claims({}))

    def test_chain_is_outermost_first(self):
        d = parse_claims(CEO_CLAIMS)
        self.assertEqual(d.actor_chain, ("repo:FuzeExecutive", "agent:a2a-shared"))
        self.assertEqual(d.subject, "user:ceo@fuzefront.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
