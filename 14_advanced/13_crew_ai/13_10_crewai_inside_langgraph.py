import warnings
warnings.filterwarnings("ignore")

import sys
from typing import Literal, TypedDict

from crewai import LLM, Agent, Crew, Process, Task
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# CrewAI + LangGraph: use each for what it is good at.
#
#   LangGraph owns the CONTROL FLOW - routing, loops, state, retries,
#             and (Module 08) checkpoints and human approval.
#   CrewAI    owns the TEAMWORK inside one step - role-based agents
#             handing work to each other.
#
#   START -> triage --(merch request)--> crew_node -> quality_gate --pass--> END
#                  \--(anything else)--> polite_decline -> END    \--fail (once)--> crew_node
#
# The crew is just a function call inside a node: crew.kickoff(inputs)
# in, text out. The graph neither knows nor cares that three agents
# collaborated to produce it.
#
# Fully local - no API key:   ollama pull qwen3:8b
# =====================================================================

crew_llm = LLM(model="ollama/qwen3:8b", base_url="http://localhost:11434")
graph_llm = ChatOllama(model="qwen3:8b", temperature=0, reasoning=False)


class MerchState(TypedDict, total=False):
    request: str
    route: str
    draft: str
    feedback: str
    attempts: int


# ---------------------------------------------------------------------
# The crew: a sequential retail-merchandising team of two.
# ---------------------------------------------------------------------
trend_analyst = Agent(
    role="Retail Trend Analyst",
    goal="Spot which product categories are rising for an online fashion retailer",
    backstory="You read sales signals and seasonal patterns and explain them plainly.",
    llm=crew_llm,
    verbose=False,
)
copywriter = Agent(
    role="Merchandising Copywriter",
    goal="Turn trend notes into a short, actionable weekly merchandising brief",
    backstory="You write crisp briefs that store teams can act on the same day.",
    llm=crew_llm,
    verbose=False,
)
analyse = Task(
    description="Request: {request}\nList the 3 most important trends for this request, one line each, with why.",
    expected_output="3 numbered trend lines",
    agent=trend_analyst,
)
brief = Task(
    description=(
        "Write the weekly merchandising brief from the trend notes. Exactly 3 bullet points, "
        "each starting with an action verb, under 90 words in total.\n{feedback}"
    ),
    expected_output="3 bullet points, under 90 words",
    agent=copywriter,
    context=[analyse],
)
merch_crew = Crew(agents=[trend_analyst, copywriter], tasks=[analyse, brief], process=Process.sequential)


# ---------------------------------------------------------------------
# The graph's nodes
# ---------------------------------------------------------------------
def triage(state: MerchState) -> MerchState:
    answer = graph_llm.invoke(
        "Is this a request for retail merchandising or product-trend advice? Answer yes or no.\n\n"
        + state["request"]
    ).content.strip().lower()
    return {"route": "crew" if answer.startswith("yes") else "decline", "attempts": 0, "feedback": ""}


def crew_node(state: MerchState) -> MerchState:
    print(f"\n[crew_node] kickoff #{state['attempts'] + 1} - two CrewAI agents at work…")
    result = merch_crew.kickoff(inputs={"request": state["request"], "feedback": state.get("feedback", "")})
    return {"draft": result.raw, "attempts": state["attempts"] + 1}


def quality_gate(state: MerchState) -> MerchState:
    # Plain code, not an LLM: the brief's rules are checkable.
    bullets = [l for l in state["draft"].splitlines() if l.strip().startswith(("-", "*", "•"))]
    words = len(state["draft"].split())
    problems = []
    if len(bullets) != 3:
        problems.append(f"it has {len(bullets)} bullet points, not 3")
    if words > 110:
        problems.append(f"it is {words} words, keep it under 90")
    print(f"[quality_gate] {len(bullets)} bullets, {words} words -> {'FAIL: ' + '; '.join(problems) if problems else 'PASS'}")
    return {"feedback": ("Your previous draft was rejected because " + " and ".join(problems) + ". Fix that.") if problems else ""}


def after_gate(state: MerchState) -> Literal["crew_node", "__end__"]:
    return "crew_node" if state["feedback"] and state["attempts"] < 2 else END


def polite_decline(state: MerchState) -> MerchState:
    return {"draft": "This assistant only handles merchandising and product-trend requests."}


g = StateGraph(MerchState)
g.add_node("triage", triage)
g.add_node("crew_node", crew_node)
g.add_node("quality_gate", quality_gate)
g.add_node("polite_decline", polite_decline)
g.add_edge(START, "triage")
g.add_conditional_edges("triage", lambda s: s["route"], {"crew": "crew_node", "decline": "polite_decline"})
g.add_edge("crew_node", "quality_gate")
g.add_conditional_edges("quality_gate", after_gate, ["crew_node", END])
g.add_edge("polite_decline", END)
app = g.compile()

if __name__ == "__main__":
    for request in [
        "Our online fashion store's summer sale starts next week in India. What should we promote?",
        "Write me a poem about the sea.",
    ]:
        print("=" * 70 + f"\nREQUEST: {request}")
        out = app.invoke({"request": request})
        print(f"\nRESULT (route={out['route']}, crew runs={out.get('attempts', 0)}):\n{out['draft']}\n")
