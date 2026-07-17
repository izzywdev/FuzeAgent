#!/usr/bin/env python3
"""Deterministic cross-environment hand-forward chain (orchestrator-driven).

Runs a goal through an ordered list of roles, one SESSION per role so each step
executes in its OWN environment (cloud vs the devops self-hosted worker) — which
the `multiagent` coordinator cannot do (its sub-agents share one environment).

For each step: create the role's session (+ vault creds + shared handoff memory),
seed it with the accumulated HANDOFF LEDGER + this step's instruction, run to
completion, append the agent's result to the ledger, then ARCHIVE the session (the
handing agent terminates). The next role re-launches fresh with the accumulated
context. Provider selected by AGENT_PROVIDER (default anthropic).

    python relay.py --chain backend qa devops --goal "add /health to svc X and deploy"
    python relay.py --chain backend qa devops --goal "..." --auto allow   # headless

For the AGENT-INITIATED version (an agent decides who to hand to, mid-task), use
the handoff MCP server (orchestration/handoff_mcp/) instead.
"""
import argparse
import os
import sys

TEMPLATES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (TEMPLATES_ROOT, os.path.join(TEMPLATES_ROOT, "sync")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from providers.base import interactive_approver, auto_approver  # noqa: E402
import launch_session as ls  # noqa: E402  (reuse PROVIDER + _resolve + vault_ids + memory_resources)

PROVIDER = ls.PROVIDER

LEDGER_HEADER = "# HANDOFF LEDGER\n\nGoal: {goal}\n"
STEP_TEMPLATE = (
    "{ledger}\n\n---\n\nYou are the **{role}** in a hand-forward chain. Do YOUR slice only, "
    "against the context above. When done, end with your honest 'SCOPE DONE (verified): ...' / "
    "'OUT OF SCOPE — NOT DONE: ...' report — it becomes the context handed to the next role."
)


def main():
    ap = argparse.ArgumentParser(description="Cross-environment hand-forward relay.")
    ap.add_argument("--chain", nargs="+", required=True, help="ordered role keys, e.g. backend qa devops")
    ap.add_argument("--goal", required=True, help="the overall goal seeded into the ledger")
    ap.add_argument("--auto", choices=["allow", "deny"], help="headless approval mode (default: interactive)")
    ap.add_argument("--no-vault", action="store_true")
    ap.add_argument("--no-memory", action="store_true")
    args = ap.parse_args()

    approver = auto_approver(args.auto) if args.auto else interactive_approver
    vaults = ls.vault_ids(args.no_vault)
    memory = ls.memory_resources(args.no_memory)  # shared handoff store across every hop
    ledger = LEDGER_HEADER.format(goal=args.goal)

    for i, role in enumerate(args.chain, 1):
        entry = ls._resolve(role)
        print(f"\n===== step {i}/{len(args.chain)}: {role} =====")
        session_id = PROVIDER.create_session(entry["id"], entry["version"], entry["environment_id"],
                                             vault_ids=vaults, memory_resources=memory, title=f"relay:{role}:{i}")
        print(f"session {session_id} (env {entry['environment_id']})\n")

        result = PROVIDER.run_turn(session_id, STEP_TEMPLATE.format(ledger=ledger, role=role), approver)
        ledger += f"\n\n## {role} update (step {i})\n{result.strip()}\n"

        PROVIDER.archive_session(session_id)  # handing agent terminates
        print(f"\n[{role} handed forward; session archived]")

    print("\n\n===== chain complete =====")
    print(ledger)


if __name__ == "__main__":
    main()
