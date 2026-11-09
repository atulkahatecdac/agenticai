import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)

# Tool/LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Conditional routing graph: one "router" node classifies the incoming
# question, then a conditional edge sends state to exactly one of three
# specialist nodes based on that classification. Each specialist is the
# same underlying LLM but with a different system prompt/persona - the
# graph's STRUCTURE is what gives each branch its expertise, not a
# bigger or fine-tuned model.
# =====================================================================


class SupportState(TypedDict):
    question: str
    category: str
    answer: str


# ---------------------------------------------------------------------
# Router node - constrained via with_structured_output to one of three
# labels, so the conditional edge downstream never has to guard against
# an unexpected/misspelled category string coming back from the LLM.
# ---------------------------------------------------------------------
class Routing(BaseModel):
    category: Literal["billing", "technical", "general"] = Field(
        description="Which specialist should handle this support request."
    )


router_prompt = ChatPromptTemplate.from_template("""\
Classify the customer support question below into exactly one category:

- billing: invoices, payments, refunds, subscription plans, pricing
- technical: errors, bugs, installation, product not working as expected
- general: anything else - account questions, feedback, general info

Question: {question}""")

router_chain = router_prompt | llm.with_structured_output(Routing)


def classify(state: SupportState) -> SupportState:
    result = router_chain.invoke({"question": state["question"]})
    print(f"[router] classified as: {result.category}")
    return {"category": result.category}


def route_to_specialist(state: SupportState) -> str:
    return state["category"]


# ---------------------------------------------------------------------
# Specialist nodes - factory so the three branches share the plumbing
# and differ only in their system prompt.
# ---------------------------------------------------------------------
def make_specialist(system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}"),
    ])
    chain = prompt | llm

    def node(state: SupportState) -> SupportState:
        response = chain.invoke({"question": state["question"]})
        return {"answer": response.content}

    return node


billing_node = make_specialist(
    "You are a billing support specialist. Answer questions about invoices, "
    "payments, refunds, subscriptions and pricing. Be precise about policy - "
    "state a standard 30-day refund window if refunds come up. Keep it to a "
    "couple of sentences."
)

technical_node = make_specialist(
    "You are a technical support specialist. Help debug errors, installation "
    "issues and unexpected product behavior. Ask one clarifying question if "
    "the problem description is too vague to diagnose, otherwise give "
    "concrete troubleshooting steps. Keep it to a couple of sentences."
)

general_node = make_specialist(
    "You are a general customer support agent. Handle anything that isn't "
    "billing or technical - account questions, feedback, general info. Keep "
    "answers friendly and brief."
)

# ---------------------------------------------------------------------
# Graph: START -> classify -> (conditional) -> {billing|technical|general} -> END
# ---------------------------------------------------------------------
graph = StateGraph(SupportState)
graph.add_node("classify", classify)
graph.add_node("billing", billing_node)
graph.add_node("technical", technical_node)
graph.add_node("general", general_node)

graph.add_edge(START, "classify")
graph.add_conditional_edges(
    "classify",
    route_to_specialist,
    {"billing": "billing", "technical": "technical", "general": "general"},
)
graph.add_edge("billing", END)
graph.add_edge("technical", END)
graph.add_edge("general", END)

app = graph.compile()

# --------------------------
# Draw and save graph image (best-effort - needs internet access since
# draw_mermaid_png renders via the remote mermaid.ink API).
# --------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(BASE_DIR, "conditional_routing_graph.png")
    app.get_graph().draw_mermaid_png(output_file_path=graph_path)
    print(f"Graph image saved at: {graph_path}")
except Exception as exc:
    print(f"(skipped graph image - {exc})")

if __name__ == "__main__":
    questions = [
        "I was charged twice for my subscription this month, can I get a refund?",
        "The app crashes every time I try to upload a photo larger than 5MB.",
        "Do you have a mobile app as well as the website?",
    ]

    for q in questions:
        print("=" * 70)
        print(f"Question: {q}")
        result = app.invoke({"question": q, "category": "", "answer": ""})
        print(f"Category: {result['category']}")
        print(f"Answer:   {result['answer']}")
        print()
