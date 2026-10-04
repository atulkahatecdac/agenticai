# pip install flask openai-agents
import asyncio
import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime

from agents import OutputGuardrailTripwireTriggered, RunState, Runner
from flask import Flask, redirect, render_template_string, request, url_for

from common import (APP_PORT, DEFAULT_CUSTOMER, DEMO_CUSTOMERS, QUESTIONS_FILE, CustomerSession, load_step,
                    session_for, tool_output_text)

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 10: the whole system as one web app.
#
#   Customer page  /           chat as Rahul (C67890) or Priya (C11111)
#   Approver page  /approver   a claims officer approves or rejects claims
#
# Every chat turn:
#   1. PII masked, input rails checked                       (step 8)
#   2. agent runs with tools from the MCP server, launched
#      for THIS customer (CUSTOMER_ID env var)               (steps 3-7)
#   3. output rail checks amounts / clauses / promises        (step 8)
#   4. if the agent calls submit_claim, the MCP server's
#      require_approval setting pauses the run               (step 9)
#      -> the paused run is saved as text in PENDING
#      -> the approver clicks Approve/Reject
#      -> the run is restored from that text and resumed,
#         and the answer appears in the customer's chat
# Each answer has a "trace" showing the tool calls and guardrail results.
#
# State is kept in memory (restart = clean slate). A real app would put
# CHATS / HISTORY / PENDING in a database - PENDING is already plain text.
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python 10_app_flask.py       then open http://localhost:5020
# =====================================================================

guard = load_step("8_guardrails.py")
mcp = load_step("7b_mcp_agent.py")
claims = load_step("9_hitl_claim.py")

CHATS = {cid: [] for cid in DEMO_CUSTOMERS}     # what the page shows
HISTORY = {cid: [] for cid in DEMO_CUSTOMERS}   # what the agent remembers between turns
PENDING: dict[str, dict] = {}                   # approval id -> paused run waiting for a human
DECIDED: list[dict] = []                        # recent approvals / rejections

with open(QUESTIONS_FILE, encoding="utf-8") as f:
    SAMPLES = json.load(f)


def server_for(customer_id: str):
    """All four MCP tools; submit_claim always needs a human (MCP-level HITL)."""
    return mcp.insurance_mcp_server(customer_id, read_only=False,
                                    require_approval={"always": {"tool_names": ["submit_claim"]}})


def build_agent(server):
    return guard.build_agent(instructions=claims.instructions, mcp_servers=[server])


def trace_of(result, start: int = 0) -> list[str]:
    lines = []
    for item in result.new_items[start:]:
        if item.type == "tool_call_item":
            lines.append(f"→ {item.raw_item.name}({item.raw_item.arguments})")
        elif item.type == "tool_call_output_item":
            text = " ".join(tool_output_text(item.output).split())
            lines.append(f"← {text[:180]}{'…' if len(text) > 180 else ''}")
        elif item.type == "tool_approval_item":
            lines.append(f"⏸ {item.name} is waiting for a claims officer")
    return lines


def record(customer_id: str, result, trace: list[str], start: int = 0) -> None:
    """A run (new or resumed) either finished, or paused for approval."""
    trace = trace + trace_of(result, start)
    if result.interruptions:
        pid = uuid.uuid4().hex[:6]
        PENDING[pid] = {
            "id": pid, "customer_id": customer_id, "customer_name": DEMO_CUSTOMERS[customer_id],
            "calls": [{"tool": i.name, "args": json.loads(i.arguments or "{}")} for i in result.interruptions],
            "state": result.to_state().to_string(context_serializer=asdict),   # the paused run, as text
            "items_seen": len(result.new_items),
            "created": datetime.now().strftime("%H:%M:%S"),
        }
        CHATS[customer_id].append({"role": "assistant", "trace": trace, "kind": "pending",
                                   "text": "I've prepared your claim. A claims officer has to approve it before "
                                           "it is submitted - the answer will appear here."})
    else:
        HISTORY[customer_id] = result.to_input_list()
        CHATS[customer_id].append({"role": "assistant", "text": result.final_output, "trace": trace})


async def chat_turn(customer_id: str, question: str) -> None:
    CHATS[customer_id].append({"role": "user", "text": question})
    async with server_for(customer_id) as server:
        out = await guard.ask(build_agent(server), question, session_for(customer_id), HISTORY[customer_id])
        trace = [f"🔒 PII masked before the LLM: {', '.join(out['pii'])}"] if out["pii"] else []
        if out["blocked"]:
            trace.append(f"🛡 blocked by the {out['blocked']} rail: {out['detail']}")
            CHATS[customer_id].append({"role": "assistant", "text": out["answer"], "trace": trace, "kind": "blocked"})
        else:
            record(customer_id, out["result"], trace)


async def resume(pid: str, approve: bool) -> None:
    p = PENDING.pop(pid)
    cid = p["customer_id"]
    async with server_for(cid) as server:
        agent = build_agent(server)
        state = await RunState.from_string(agent, p["state"],
                                           context_deserializer=lambda d: CustomerSession(**d))
        for item in state.get_interruptions():
            if approve:
                state.approve(item)
            else:
                state.reject(item, rejection_message="A claims officer rejected this claim submission.")
        trace = [f"{'✅ approved' if approve else '❌ rejected'} by the claims officer"]
        try:
            result = await Runner.run(agent, state, hooks=guard.EvidenceHooks())
            record(cid, result, trace, start=p["items_seen"])
        except OutputGuardrailTripwireTriggered as e:
            trace.append(f"🛡 blocked by the output rail: {e.guardrail_result.output.output_info}")
            CHATS[cid].append({"role": "assistant", "text": guard.BLOCKED_REPLY["output"], "trace": trace,
                               "kind": "blocked"})
    DECIDED.insert(0, {**p, "decision": "Approved" if approve else "Rejected",
                       "at": datetime.now().strftime("%H:%M:%S")})


# ---------------------------------------------------------------- web
app = Flask(__name__)

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>SecureLife Assistant</title>
{% if refresh %}<meta http-equiv="refresh" content="4">{% endif %}
<style>
 body{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f9;margin:0;color:#1d2733}
 header{background:#0f4c81;color:#fff;padding:14px 24px;display:flex;align-items:center;gap:24px}
 header a{color:#cfe3f7;text-decoration:none;font-weight:600} header a.on{color:#fff;border-bottom:2px solid #fff}
 main{max-width:980px;margin:20px auto;padding:0 16px}
 .card{background:#fff;border-radius:10px;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 3px #0001}
 .msg{margin:10px 0;max-width:80%;padding:10px 14px;border-radius:12px;white-space:pre-wrap}
 .user{background:#0f4c81;color:#fff;margin-left:auto} .assistant{background:#eef2f7}
 .blocked{background:#fdecea} .pending{background:#fff4e0}
 details{font-size:12px;color:#55606e;margin-top:6px} details div{font-family:Consolas,monospace;margin:2px 0}
 textarea{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;border:1px solid #c5ced8;font:inherit}
 button{background:#0f4c81;color:#fff;border:0;border-radius:6px;padding:8px 14px;cursor:pointer;font:inherit}
 button.sample{background:#e3ebf4;color:#0f4c81;margin:3px;padding:5px 10px;font-size:13px}
 button.ok{background:#1e7d3a} button.no{background:#b3261e}
 table{width:100%;border-collapse:collapse} td,th{text-align:left;padding:8px;border-bottom:1px solid #e6eaef;vertical-align:top}
 .banner{background:#fff4e0;border-left:4px solid #e8a33d;padding:10px 14px;border-radius:6px;margin-bottom:12px}
 .muted{color:#6b7683;font-size:13px}
</style></head><body>
<header><b>SecureLife Insurance Assistant</b>
 <a href="{{ url_for('chat', customer=customer) }}" class="{{ 'on' if page=='chat' }}">Customer chat</a>
 <a href="{{ url_for('approver') }}" class="{{ 'on' if page=='approver' }}">Claims approver ({{ pending|length }})</a>
</header><main>
{% if page == 'chat' %}
 <div class="card"><form method="get" style="display:flex;gap:10px;align-items:center">
  Logged in as <select name="customer" onchange="this.form.submit()">
  {% for cid, name in customers.items() %}<option value="{{cid}}" {{'selected' if cid==customer}}>{{name}} ({{cid}})</option>{% endfor %}
  </select><span class="muted">demo login - in a real app this comes from the session</span></form></div>
 {% if waiting %}<div class="banner">⏳ Your claim is waiting for a claims officer. This page refreshes on its own.</div>{% endif %}
 <div class="card">
 {% for m in chat %}
  <div class="msg {{ m.role }} {{ m.kind or '' }}">{{ m.text }}
  {% if m.trace %}<details><summary>trace ({{ m.trace|length }})</summary>{% for t in m.trace %}<div>{{ t }}</div>{% endfor %}</details>{% endif %}
  </div>
 {% else %}<p class="muted">Ask about your policy, or click a sample question below.</p>{% endfor %}
 </div>
 <div class="card"><form method="post" action="{{ url_for('ask') }}">
  <input type="hidden" name="customer" value="{{ customer }}">
  <textarea name="question" rows="2" placeholder="e.g. What is the coverage amount in my health insurance policy?"></textarea>
  <div style="margin-top:8px;display:flex;justify-content:space-between"><button>Send</button>
  <button formaction="{{ url_for('reset') }}" style="background:#6b7683">Clear chat</button></div>
  <p class="muted" style="margin:10px 0 4px">Sample questions:</p>
  {% for s in samples %}<button class="sample" name="question" value="{{ s.question }}" title="{{ s.note }}">{{ s.id }}</button>{% endfor %}
 </form></div>
{% else %}
 <div class="card"><h3 style="margin-top:0">Claims waiting for approval</h3>
 {% if pending %}<table><tr><th>Customer</th><th>Requested action</th><th>Received</th><th></th></tr>
  {% for p in pending %}<tr><td>{{ p.customer_name }}<br><span class="muted">{{ p.customer_id }}</span></td>
   <td>{% for c in p.calls %}<b>{{ c.tool }}</b><br>{% for k, v in c.args.items() %}<span class="muted">{{k}}:</span> {{v}}<br>{% endfor %}{% endfor %}</td>
   <td>{{ p.created }}</td>
   <td><form method="post" action="{{ url_for('decide') }}"><input type="hidden" name="id" value="{{ p.id }}">
    <button class="ok" name="decision" value="approve">Approve</button>
    <button class="no" name="decision" value="reject">Reject</button></form></td></tr>{% endfor %}
 </table>{% else %}<p class="muted">Nothing waiting. This page refreshes on its own.</p>{% endif %}</div>
 {% if decided %}<div class="card"><h3 style="margin-top:0">Recent decisions</h3><table>
  {% for d in decided[:10] %}<tr><td>{{ d.at }}</td><td>{{ d.customer_name }}</td>
  <td>{{ d.calls[0].tool }} ₹{{ d.calls[0].args.amount }}</td><td><b>{{ d.decision }}</b></td></tr>{% endfor %}
 </table></div>{% endif %}
{% endif %}
</main></body></html>"""


def customer_arg() -> str:
    cid = request.values.get("customer", DEFAULT_CUSTOMER)
    return cid if cid in DEMO_CUSTOMERS else DEFAULT_CUSTOMER


@app.get("/")
def chat():
    cid = customer_arg()
    waiting = any(p["customer_id"] == cid for p in PENDING.values())
    return render_template_string(PAGE, page="chat", customer=cid, customers=DEMO_CUSTOMERS, chat=CHATS[cid],
                                  samples=[s for s in SAMPLES if s["customer"] == cid],
                                  pending=list(PENDING.values()), waiting=waiting, refresh=waiting)


@app.post("/ask")
def ask():
    cid = customer_arg()
    question = request.form.get("question", "").strip()
    if question:
        asyncio.run(chat_turn(cid, question))
    return redirect(url_for("chat", customer=cid))


@app.post("/reset")
def reset():
    cid = customer_arg()
    CHATS[cid].clear()
    HISTORY[cid].clear()
    return redirect(url_for("chat", customer=cid))


@app.get("/approver")
def approver():
    return render_template_string(PAGE, page="approver", customer=DEFAULT_CUSTOMER, pending=list(PENDING.values()),
                                  decided=DECIDED, refresh=not PENDING)


@app.post("/decide")
def decide():
    pid = request.form.get("id", "")
    if pid in PENDING:
        asyncio.run(resume(pid, request.form.get("decision") == "approve"))
    return redirect(url_for("approver"))


if __name__ == "__main__":
    print(f"SecureLife assistant on http://localhost:{APP_PORT}   (needs: python 5a_insurance_api.py)")
    app.run(port=APP_PORT, debug=False, threaded=True)
