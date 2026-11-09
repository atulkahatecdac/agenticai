import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import json
import os
import shutil
import sys
import networkx as nx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# GraphRAG: Entity extraction -> Relationship graph -> Graph retrieval.
#
# Plain vector search treats every chunk as an independent bag of
# meaning - it has no notion that "Cashless Claim" and "TPA" and
# "Portability" are the SAME handful of entities showing up across many
# different chunks, connected by explicit relationships. GraphRAG makes
# that structure explicit up front: an LLM extracts (subject, relation,
# object) triples from the corpus once, those triples become a graph,
# and a query is answered by finding the entities it mentions and
# walking the graph outward from them - collecting every fact connected
# to those entities in one traversal, rather than hoping similarity
# search happens to rank them all in the same top-k.
#
# This differs from 8_9_multi_hop_reasoning.py, which chains FACTS
# together with repeated vector searches and no persistent structure.
# GraphRAG instead builds the structure once (the index-time cost) and
# retrieves by traversing it (the query-time payoff).
#
# Knowledge base: a curated subset of the health-insurance statements
# from the shared 50-statement KB - the ones dense with named entities
# and relationships (TPA, portability, waiting periods) that a graph
# can actually connect.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_PERSIST_DIR = os.path.join(BASE_DIR, "graphrag_chroma_db")
shutil.rmtree(VECTOR_PERSIST_DIR, ignore_errors=True)

with open(os.path.join(BASE_DIR, "policy_documents.json"), encoding="utf-8") as f:
    ALL_POLICY_DOCUMENTS = json.load(f)

# Health-insurance chunks rich in named entities/relationships - the
# ones worth building a graph over for this demo's two questions.
GRAPH_SOURCE_KEYWORDS = [
    "cashless health insurance claim", "Third Party Administrator", "portability",
    "pre-existing diseases", "premium is not paid", "co-payment clause",
    "claim settlement ratio", "IRDAI mandates", "restoration benefit",
]
GRAPH_DOCUMENTS = [
    doc for doc in ALL_POLICY_DOCUMENTS
    if any(kw.lower() in doc.lower() for kw in GRAPH_SOURCE_KEYWORDS)
]

# Plain vector index over the FULL 50-document KB, for the BEFORE comparison.
vectorstore = Chroma(
    collection_name="policy_docs",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    persist_directory=VECTOR_PERSIST_DIR,
)
vectorstore.add_texts(ALL_POLICY_DOCUMENTS)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class Triple(BaseModel):
    subject: str = Field(description="A short entity name, e.g. 'Cashless Claim' or 'TPA'.")
    relation: str = Field(description="A short relationship phrase, e.g. 'processed_by' or 'requires'.")
    object: str = Field(description="A short entity name this subject relates to.")


class ExtractedTriples(BaseModel):
    triples: list[Triple] = Field(description="2 to 4 (subject, relation, object) triples that "
                                   "capture the key entities and relationships stated in this "
                                   "sentence. Keep entity names short and reusable so the same "
                                   "entity is named consistently across different sentences.")


class QueryEntities(BaseModel):
    entities: list[str] = Field(description="2 to 4 short entity names mentioned or implied by "
                                 "this question, phrased to match how they'd appear in a "
                                 "knowledge graph (e.g. 'Cashless Claim', 'TPA', 'Portability').")


# -----------------------------
# Index-time: extract triples from each source document and build the graph.
# -----------------------------
print("Building knowledge graph from source documents...")
graph = nx.DiGraph()
for doc in GRAPH_DOCUMENTS:
    extracted = llm.with_structured_output(ExtractedTriples).invoke(
        f"Extract (subject, relation, object) triples from this sentence:\n\n{doc}"
    )
    for t in extracted.triples:
        graph.add_edge(t.subject, t.object, relation=t.relation, source=doc)
        print(f"  {t.subject} --[{t.relation}]--> {t.object}")

print(f"\nGraph built: {graph.number_of_nodes()} entities, {graph.number_of_edges()} relationships")


def match_node(entity: str) -> str | None:
    entity_lower = entity.lower()
    for node in graph.nodes:
        if entity_lower in node.lower() or node.lower() in entity_lower:
            return node
    return None


def graph_retrieve(question: str, hops: int = 2) -> list[str]:
    query_entities = llm.with_structured_output(QueryEntities).invoke(
        f"Question: {question}"
    ).entities

    matched_nodes = {n for e in query_entities if (n := match_node(e)) is not None}
    print(f"  matched entities: {sorted(matched_nodes) or '(none)'}")

    visited = set(matched_nodes)
    frontier = set(matched_nodes)
    facts: list[str] = []
    seen_sources = set()

    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            for _, nbr, data in graph.out_edges(node, data=True):
                print(f"  traverse: {node} --[{data['relation']}]--> {nbr}")
                if data["source"] not in seen_sources:
                    seen_sources.add(data["source"])
                    facts.append(data["source"])
                if nbr not in visited:
                    next_frontier.add(nbr)
            for pred, _, data in graph.in_edges(node, data=True):
                print(f"  traverse: {pred} --[{data['relation']}]--> {node}")
                if data["source"] not in seen_sources:
                    seen_sources.add(data["source"])
                    facts.append(data["source"])
                if pred not in visited:
                    next_frontier.add(pred)
        visited |= next_frontier
        frontier = next_frontier

    return facts


def answer_from(label: str, question: str, context: list[str]) -> None:
    context_block = "\n".join(f"- {c}" for c in context) or "(no supporting context found)"
    response = llm.invoke(
        f"Answer the question using ONLY the context below. Be concise.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {question}"
    )
    print(f"\n{label}\n  {response.content}")


QUESTIONS = [
    "If I switch my health insurance to a new insurer through portability, do I keep credit "
    "for the waiting period I've already completed on pre-existing diseases?",

    "Who actually handles my cashless claim paperwork, and what do they check before the "
    "hospital and insurer settle up?",
]

for question in QUESTIONS:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)

    # BEFORE: plain vector similarity search over the full flat KB.
    before_docs = [d.page_content for d in vectorstore.similarity_search(question, k=3)]
    print("\nBEFORE (plain vector retrieval, top 3):")
    for doc in before_docs:
        print(f"  - {doc}")
    answer_from("BEFORE ANSWER (vector context):", question, before_docs)

    # AFTER: find the entities the question is about and traverse the graph.
    print("\nAFTER (graph retrieval):")
    graph_docs = graph_retrieve(question)
    answer_from(f"AFTER ANSWER (graph context, {len(graph_docs)} connected fact(s)):", question, graph_docs)
