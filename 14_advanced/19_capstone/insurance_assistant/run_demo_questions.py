# pip install openai-agents
import asyncio
import json
import sys
import time

from common import QUESTIONS_FILE, load_step, session_for

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Pre-class check: run every question in data/demo_questions.json through
# the FULL system (guardrails + MCP tools + approval setting, exactly as
# step 10 builds it) and compare with what we expect:
#     contains / contains_any / absent   text in the answer
#     blocked: input                     an input rail stopped it
#     pii_masked                         PII was masked before the LLM
#     approval                           the run paused for a human
# Paused claims are NOT approved here, so no claim is written.
#
# LLM answers vary a little from run to run - a "contains" miss is worth a
# look, not necessarily a bug (e.g. "5 lakh" instead of "5,00,000").
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python run_demo_questions.py
#   python run_demo_questions.py Q01 Q13      only these questions
# =====================================================================

guard = load_step("8_guardrails.py")
app = load_step("10_app_flask.py")


def check(expect: dict, out: dict) -> list[str]:
    answer = out["answer"] or ""
    result = out["result"]
    paused = bool(result and result.interruptions)
    misses = []
    misses += [f"missing '{s}'" for s in expect.get("contains", []) if s not in answer]
    if expect.get("contains_any") and not any(s.lower() in answer.lower() for s in expect["contains_any"]):
        misses.append(f"none of {expect['contains_any']}")
    misses += [f"should not contain '{s}'" for s in expect.get("absent", []) if s in answer]
    if expect.get("blocked") == "input" and out["blocked"] not in ("injection", "topic"):
        misses.append("expected an input rail to block it")
    if not expect.get("blocked") and out["blocked"]:
        misses.append(f"unexpectedly blocked by the {out['blocked']} rail")
    if expect.get("pii_masked") and not out["pii"]:
        misses.append("PII was not masked")
    if expect.get("approval") and not paused:
        misses.append("expected a pause for approval")
    return misses


async def main() -> None:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)
    if len(sys.argv) > 1:
        questions = [q for q in questions if q["id"] in sys.argv[1:]]

    passed = 0
    for customer_id in dict.fromkeys(q["customer"] for q in questions):     # one MCP server per customer
        async with app.server_for(customer_id) as server:
            agent = app.build_agent(server)
            for q in (q for q in questions if q["customer"] == customer_id):
                start = time.time()
                out = await guard.ask(agent, q["question"], session_for(customer_id))
                misses = check(q["expect"], out)
                passed += not misses
                result = out["result"]
                tools = [i.raw_item.name for i in result.new_items if i.type == "tool_call_item"] if result else []
                status = ("blocked: " + out["blocked"]) if out["blocked"] else \
                         ("PAUSED for approval" if result and result.interruptions else "answered")
                print(f"{'PASS' if not misses else 'FAIL'}  {q['id']}  {customer_id}  {time.time() - start:4.1f}s  "
                      f"{q['note']}")
                print(f"      Q: {q['question']}")
                print(f"      {status}; tools: {', '.join(tools) or '-'}")
                if out["answer"]:
                    print(f"      A: {' '.join(out['answer'].split())[:200]}")
                for m in misses:
                    print(f"      !! {m}")
                print()
    print(f"{passed}/{len(questions)} as expected")


if __name__ == "__main__":
    asyncio.run(main())
