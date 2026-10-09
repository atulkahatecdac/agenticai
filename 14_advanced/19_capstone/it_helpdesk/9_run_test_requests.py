# =====================================================================
# STEP 9: Evaluate the helpdesk - LLM-as-judge.
#
# data/test_requests.json lists realistic requests, each with
#   expected_route       checked exactly (did triage / the guardrail pick right?)
#   expected_behaviour   checked by a JUDGE LLM that reads the reply and the
#                        agent trace and scores it against the description
#
# Change a prompt, swap the model (set HELPDESK_MODEL=llama3.2), and re-run:
# this table tells you whether the change helped or hurt.
#
# The requests really call the tools (tickets get created, accounts unlocked),
# so reset the data first for repeatable results:
#   del data\helpdesk.db  &&  sqlite3 data\helpdesk.db < data\seed.sql
#   python 9_run_test_requests.py
# =====================================================================
import asyncio
import json
from typing import Literal

from pydantic import BaseModel, Field

from common import CHAT_MODEL, TEST_REQUESTS, get_llm, load_step

graph = load_step("7_helpdesk_graph.py")


class Judgement(BaseModel):
    # Two tricks that make a small local judge far more reliable:
    #  - reason FIRST, verdict second: the model "thinks" before it decides
    #  - a few named labels instead of a 1-5 number (small models drift on scales)
    reason: str = Field(description="One sentence comparing what it did with what was expected")
    verdict: Literal["pass", "partial", "fail"] = Field(
        description="pass = did everything expected; partial = mostly right, something missing; "
                    "fail = wrong action, wrong answer or unsafe")


JUDGE_PROMPT = """You are grading an IT helpdesk AI assistant.

Employee request: {message}
Expected behaviour: {expected}

What the assistant did (tool calls and checks, in order):
{trace}

Final reply to the employee:
{reply}

Judge whether the assistant's ACTIONS and REPLY match the expected behaviour."""

judge = get_llm().with_structured_output(Judgement, method="json_schema")


async def main():
    with open(TEST_REQUESTS, encoding="utf-8") as f:
        tests = json.load(f)

    rows = []
    for i, t in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {t['employee_id']}: {t['message'][:60]}")
        result = await graph.handle_request(t["employee_id"], t["message"])
        verdict = judge.invoke(JUDGE_PROMPT.format(
            message=t["message"], expected=t["expected_behaviour"],
            trace="\n".join(result["trace"]), reply=result["reply"]))
        rows.append((t, result, verdict))
        print(f"      route={result['route']}  judge={verdict.verdict}  {verdict.reason}")

    print(f"\n{'#':<3}{'expected route':<19}{'actual route':<19}{'route':<7}{'judge':<7}")
    for i, (t, result, v) in enumerate(rows, 1):
        route_ok = result["route"] == t["expected_route"]
        print(f"{i:<3}{t['expected_route']:<19}{str(result['route']):<19}"
              f"{'ok' if route_ok else 'MISS':<7}{v.verdict}")

    route_acc = sum(r["route"] == t["expected_route"] for t, r, _ in rows) / len(rows)
    passed = sum(v.verdict == "pass" for _, _, v in rows)
    print(f"\nModel: {CHAT_MODEL}   routing accuracy: {route_acc:.0%}   judge passed: {passed}/{len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
