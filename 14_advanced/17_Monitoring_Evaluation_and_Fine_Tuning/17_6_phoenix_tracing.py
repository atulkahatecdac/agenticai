"""Arize Phoenix today: open-source tracing for LLM apps, one line to instrument LangChain.

17_1/17_2 send OpenTelemetry spans to Jaeger - generic spans, you add the attributes yourself.
Phoenix speaks the same OpenTelemetry, but its instrumentors (OpenInference) already know what an
LLM call, a retriever and a prompt are: you get the prompt text, token counts, latency and the
retrieved documents per step, without writing a single span.

(Phoenix used to also have an "Inferences" view for embedding drift. Version 21 removed it - see
17_5 for doing drift checks yourself.)

Needs its own venv - Phoenix's OpenTelemetry pins differ from this repo's:
    uv venv .venv-phoenix --python 3.12
    .venv-phoenix\\Scripts\\activate             (macOS/Linux: source .venv-phoenix/bin/activate)
    uv pip install -r 17_6_requirements.txt

Then two terminals (both with that venv active):
    phoenix serve                                -> UI and trace collector on http://localhost:6006
    python 17_6_phoenix_tracing.py
(or run the server in Docker instead: docker run -p 6006:6006 arizephoenix/phoenix:latest)
"""
import csv
import os
import re
import sys

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI
from phoenix.otel import register

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"), override=True)
sys.stdout.reconfigure(encoding="utf-8")

PHOENIX = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")

# The only Phoenix-specific line: point OpenTelemetry at the Phoenix server
# and auto-instrument every installed library that has an OpenInference
# instrumentor - here, LangChain. The app does not run Phoenix itself.
register(endpoint=f"{PHOENIX}/v1/traces", project_name="helpdesk-rag", auto_instrument=True, verbose=False)

# ---------------------------------------------------------------------
# A small RAG chain over the Module 04 help-desk FAQ. The retriever is a
# plain word-overlap function so this venv needs no vector database;
# Phoenix still shows it as its own step with the documents it returned.
# ---------------------------------------------------------------------
with open(os.path.join(BASE_DIR, "..", "04_rag", "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower())) - {"i", "my", "a", "the", "is", "do", "how", "to", "can", "you", "what", "of"}


def retrieve(question: str) -> str:
    ranked = sorted(FAQ, key=lambda r: len(words(question) & words(r["question"] + " " + r["answer"])), reverse=True)
    return "\n".join(f"Q: {r['question']}\nA: {r['answer']}" for r in ranked[:3])


prompt = ChatPromptTemplate.from_template(
    "Answer the customer from the FAQ entries only, in one or two sentences.\n\nFAQ:\n{context}\n\nCustomer: {question}"
)
chain = (
    {"context": RunnableLambda(retrieve).with_config(run_name="faq_retriever"), "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(model="gpt-4o-mini", temperature=0)
)

if __name__ == "__main__":
    for q in ["My parcel hasn't arrived yet - where is it?",
              "Can I pay with UPI?",
              "How do I return shoes that don't fit?"]:
        print(f"Q: {q}\nA: {chain.invoke(q).content}\n")

    print(f"Phoenix UI: {PHOENIX}  ->  project 'helpdesk-rag'")
    print("One trace per question: faq_retriever (with the FAQ text it returned), the prompt, and the LLM span")
    print("with token counts and latency. Click a trace to see the exact prompt that was sent.")
