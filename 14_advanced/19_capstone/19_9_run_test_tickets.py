# pip install langgraph langchain-openai mcp
import warnings
warnings.filterwarnings("ignore")
from capstone_common import quiet_langgraph_import
quiet_langgraph_import()

import json
import os
import sys
import time

# 20 test tickets must not send 20 push notifications to a real approver.
os.environ.setdefault("CAPSTONE_NO_PUSH", "1")

from langgraph.checkpoint.memory import MemorySaver

from capstone_common import TICKETS_FILE, load_step

agent = load_step("19_6_agent_graph.py")

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 9 of the capstone: the integration test / iteration loop.
#
# Runs all 20 tickets from data/test_tickets.json through the SAME graph
# the API uses and prints a scorecard. For every ticket it checks:
#   - DECISION   is it the expected one?
#   - APPROVAL   did the ticket go to a human exactly when it should?
#   - CITATION   does every refund/replacement/repair/reject cite a clause?
# The approver is simulated (always approves), so the run is unattended.
#
# This is the script to re-run after EVERY change to a prompt, a policy,
# the chunking or a rule - "20 of 20" is the gate for integration testing.
#
# Run it:
#   python 19_9_run_test_tickets.py             uses the LLM if OPENAI_API_KEY is set
#   python 19_9_run_test_tickets.py --offline   no LLM, no network
#   python 19_9_run_test_tickets.py T03 T07     only these tickets
# =====================================================================

if __name__ == "__main__":
    with open(TICKETS_FILE, encoding="utf-8") as f:
        tickets = json.load(f)
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if only:
        tickets = [t for t in tickets if t["id"] in only]

    app = agent.build_graph(MemorySaver())     # test runs do not need to survive a restart
    print(f"Warming up (PII engine: {agent.guardrails.pii_engine()}, MCP servers: {', '.join(agent.toolbox().SERVERS)}) ...")
    print("=" * 100)
    print(f"RUNNING {len(tickets)} TEST TICKETS   mode: {'OFFLINE' if agent.OFFLINE else 'LLM (gpt-4o-mini)'}")
    print("=" * 100)
    print(f"{'ID':<4} {'Scenario':<44} {'Expected':<13} {'Got':<13} {'Human?':<8} {'Cites':<6} {'Time':>6}  Result")
    print("-" * 100)

    passed, failures, total_time = 0, [], 0.0
    for ticket in tickets:
        started = time.perf_counter()
        try:
            result, config = agent.run_ticket(app, ticket["message"], f"{ticket['id']}-{int(time.time())}")
            went_to_human = "__interrupt__" in result
            if went_to_human:
                result = agent.resume_ticket(app, config, approved=True, note="auto-approved by test run")
            decision = result["decision"]
            cites = len(result.get("citations", []))
        except Exception as exc:
            decision, went_to_human, cites = f"ERROR {type(exc).__name__}", False, 0
        elapsed = time.perf_counter() - started
        total_time += elapsed

        problems = []
        if decision != ticket["expected"]:
            problems.append("wrong decision")
        if went_to_human != ticket["needs_approval"]:
            problems.append("approval " + ("missing" if ticket["needs_approval"] else "not needed"))
        if decision in ("refund", "replacement", "repair", "reject") and cites == 0:
            problems.append("no citation")
        ok = not problems
        passed += ok
        if not ok:
            failures.append((ticket, decision, problems))
        print(f"{ticket['id']:<4} {ticket['about'][:43]:<44} {ticket['expected']:<13} {decision[:12]:<13} "
              f"{'yes' if went_to_human else 'no':<8} {cites:<6} {elapsed:>5.1f}s  {'PASS' if ok else 'FAIL: ' + ', '.join(problems)}")

    print("-" * 100)
    print(f"SCORE: {passed} of {len(tickets)} tickets correct   |   average {total_time / len(tickets):.1f}s per ticket")
    for ticket, decision, problems in failures:
        print(f"\n  {ticket['id']} {', '.join(problems)}: expected {ticket['expected']}, got {decision}")
        print(f"     {ticket['message']}")
    if agent._toolbox:
        agent._toolbox.close()
    sys.exit(0 if passed == len(tickets) else 1)
