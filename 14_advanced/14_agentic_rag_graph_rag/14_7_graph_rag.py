# GraphRAG: extract entities -> build a graph -> retrieve by walking it.
# Vector search treats every chunk as isolated. GraphRAG has an LLM pull
# (subject, relation, object) triples out of the documents ONCE, stores
# them as a graph, and answers a question by finding the entities it
# mentions and collecting every fact connected to them.
# (14_8 chains facts with repeated vector searches instead - no stored graph.)

import os
import sys
import json
import chromadb
import networkx as nx
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    documents = json.load(f)

# Plain vector index over the whole KB, for the BEFORE comparison
kb = chromadb.Client().create_collection("policy_docs")
kb.add(ids=[str(i) for i in range(len(documents))], documents=documents)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Triple(BaseModel):
    subject: str
    relation: str
    object: str


class Triples(BaseModel):
    triples: list[Triple]


class Entities(BaseModel):
    entities: list[str]


# ---- Index time: build the graph from the entity-rich health-insurance chunks ----
KEYWORDS = ["cashless health insurance claim", "Third Party Administrator", "portability",
            "pre-existing diseases", "premium is not paid", "co-payment clause",
            "claim settlement ratio", "IRDAI mandates", "restoration benefit"]
graph_docs = [d for d in documents if any(k.lower() in d.lower() for k in KEYWORDS)]

print("Building the knowledge graph...")
graph = nx.Graph()
for doc in graph_docs:
    extracted = llm.with_structured_output(Triples).invoke(
        "Extract 2-4 (subject, relation, object) triples from this sentence. Use short entity "
        f"names (e.g. 'Cashless Claim', 'TPA') and name the same entity the same way every time.\n\n{doc}"
    )
    for t in extracted.triples:
        graph.add_edge(t.subject, t.object, relation=t.relation, source=doc)
        print(f"  {t.subject} --[{t.relation}]--> {t.object}")
print(f"Graph: {graph.number_of_nodes()} entities, {graph.number_of_edges()} relationships")


# ---- Query time: find the question's entities, collect connected facts ----
def graph_retrieve(question: str) -> list[str]:
    names = llm.with_structured_output(Entities).invoke(
        f"List 2-4 short entity names in this question, as they'd appear in a knowledge graph: {question}"
    ).entities
    matched = {n for e in names for n in graph.nodes if e.lower() in n.lower() or n.lower() in e.lower()}
    print(f"  matched entities: {sorted(matched)}")

    nearby = set()  # the matched entities plus their direct neighbours
    for node in matched:
        nearby |= set(nx.ego_graph(graph, node, radius=1))
    facts = {data["source"] for _, _, data in graph.edges(nearby, data=True)}
    print(f"  {len(facts)} connected fact(s) collected")
    return list(facts)


def answer(question: str, docs: list[str]) -> str:
    context = "\n".join(f"- {d}" for d in docs)
    return llm.invoke(f"Answer using ONLY the context. Be concise.\n\nContext:\n{context}\n\nQuestion: {question}").content


QUESTIONS = [
    "If I switch my health insurance to a new insurer through portability, do I keep credit "
    "for the waiting period I've already completed on pre-existing diseases?",
    "Who actually handles my cashless claim paperwork, and what do they check before the "
    "hospital and insurer settle up?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70 + f"\nQUESTION: {question}\n" + "=" * 70)

    vector_docs = kb.query(query_texts=[question], n_results=3)["documents"][0]
    print("\nBEFORE - vector search, top 3:")
    for doc in vector_docs:
        print(f"  - {doc}")
    print(f"  ANSWER: {answer(question, vector_docs)}")

    print("\nAFTER - graph retrieval:")
    print(f"  ANSWER: {answer(question, graph_retrieve(question))}")
