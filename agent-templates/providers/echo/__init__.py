"""Echo/mock provider — ACCEPTANCE-GATE ONLY.

Selected with ``AGENT_PROVIDER=echo`` to stand the shared A2A server up inside the
Phase-3 acceptance workflow (``.github/workflows/a2a-acceptance.yml``) with NO real
external agent runtime (no Anthropic Managed Agents, no Jira/FuzePlan). It is never
selected in a real deployment (prod uses ``anthropic``).
"""
