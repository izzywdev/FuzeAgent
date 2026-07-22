#!/usr/bin/env python3
"""Deterministic cross-agent hand-forward chain, driven over the A2A wire.

Runs a goal through an ordered list of target agents, one A2A **task** per hop, so
each step executes in the callee's OWN environment behind its own Agent Card. The
orchestrator (this script) holds NONE of the callees' tools or credentials — it only
hands each a goal and reads back a Task (card-projection.md §7).

For each step: `SendMessage` the accumulated HANDOFF LEDGER + this step's instruction
to the role's A2A agent, drive any INPUT_REQUIRED/AUTH_REQUIRED pause to resolution
via the approval mode (interactive by default; `--auto allow|deny` headless), append
the agent's settled result to the ledger, and move to the next role. There is no
task table and no transcript copy — the callee owns its session state
(state-mapping.md §1, §7).

    python relay.py --chain FuzePlan FuzeService --goal "plan and action the rollout"
    python relay.py --chain FuzePlan FuzeService --goal "..." --auto allow   # headless

Targets are resolved via A2A_TARGETS / convention (see a2a_transport). For the
AGENT-INITIATED version (an agent decides who to hand to, mid-task), use the handoff
MCP server (orchestration/handoff_mcp/) instead.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))                     # orchestration/
TEMPLATES_ROOT = os.path.dirname(HERE)                               # agent-templates/
for _p in (HERE, TEMPLATES_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import a2a_transport as a2a  # noqa: E402

#: How many times a single hop may be re-prompted while it keeps pausing before the
#: relay records the pause and moves on. Exec-tier pauses can legitimately dwell on a
#: human (state-mapping.md §4); relay is deterministic orchestration, so it caps
#: rather than blocking a chain forever. Override with A2A_RELAY_MAX_PAUSES.
MAX_PAUSES = int(os.environ.get("A2A_RELAY_MAX_PAUSES", "8"))

LEDGER_HEADER = "# HANDOFF LEDGER\n\nGoal: {goal}\n"
STEP_TEMPLATE = (
    "{ledger}\n\n---\n\nYou are the **{role}** in a hand-forward chain. Do YOUR slice only, "
    "against the context above. When done, end with your honest 'SCOPE DONE (verified): ...' / "
    "'OUT OF SCOPE — NOT DONE: ...' report — it becomes the context handed to the next role."
)


def _answer_pause(session_id: str, pending: dict, auto: str | None) -> dict:
    """Resolve one INPUT_REQUIRED/AUTH_REQUIRED pause by continuing the task with a
    decision. A caller MUST read pending['message'] first (state-mapping.md §4)."""
    ask = (pending or {}).get("message", "(no message)")
    if auto == "allow":
        decision = "APPROVE: proceed."
    elif auto == "deny":
        decision = "DENY: auto-denied (headless)."
    else:
        print(f"\nPAUSE ({pending.get('kind')}): {ask}")
        ans = input("  [y]allow / [n]deny > ").strip().lower()
        if ans in ("y", "yes", "allow"):
            decision = "APPROVE: proceed."
        else:
            decision = "DENY: " + (input("  deny reason > ").strip() or "denied by operator")
    return a2a.continue_task(session_id, decision)


def _run_hop(role: str, prompt: str, auto: str | None) -> dict:
    """Start a task for one role and drive it to a settled (or capped) state."""
    res = a2a.start(role, prompt, return_immediately=False)
    pauses = 0
    while res["status"] == "blocked":
        if pauses >= MAX_PAUSES:
            res["reply"] = (res.get("reply") or "") + (
                f"\n\n[relay: still {res['pending'].get('state')} after {pauses} prompts — "
                f"the callee may be awaiting a human (state-mapping.md §4); recorded and moved on.]")
            break
        pauses += 1
        res = _answer_pause(res["session_id"], res["pending"], auto)
    return res


def main():
    ap = argparse.ArgumentParser(description="Cross-agent hand-forward relay over the A2A wire.")
    ap.add_argument("--chain", nargs="+", required=True,
                    help="ordered target agent keys, e.g. FuzePlan FuzeService")
    ap.add_argument("--goal", required=True, help="the overall goal seeded into the ledger")
    ap.add_argument("--auto", choices=["allow", "deny"], help="headless approval mode (default: interactive)")
    # Accepted for CLI compatibility; over A2A the vault/memory live on the callee.
    ap.add_argument("--no-vault", action="store_true", help="(ignored over A2A — callee-side)")
    ap.add_argument("--no-memory", action="store_true", help="(ignored over A2A — callee-side)")
    args = ap.parse_args()

    ledger = LEDGER_HEADER.format(goal=args.goal)

    for i, role in enumerate(args.chain, 1):
        print(f"\n===== step {i}/{len(args.chain)}: {role} =====")
        res = _run_hop(role, STEP_TEMPLATE.format(ledger=ledger, role=role), args.auto)
        print(f"task {res['session_id']} -> {res['status']}")
        ledger += f"\n\n## {role} update (step {i}) [{res['status']}]\n{(res.get('reply') or '').strip()}\n"
        print(f"\n[{role} handed forward]")

    print("\n\n===== chain complete =====")
    print(ledger)


if __name__ == "__main__":
    main()
