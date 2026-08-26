import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import shutil
import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Corrective RAG (CRAG): plain RAG trusts whatever the retriever returns.
# CRAG adds a grading step that scores each retrieved document as
# relevant/irrelevant, then picks a corrective action based on the
# result - unlike agentic RAG (which decides IF/HOW MANY TIMES to
# retrieve), CRAG always retrieves once and instead decides what to do
# with what came back:
#   - CORRECT   (all docs relevant)   -> refine and answer from the KB alone
#   - AMBIGUOUS (some docs relevant)  -> refine the good parts, then
#                                        supplement with a real web search
#   - INCORRECT (no docs relevant)    -> discard the KB entirely, rewrite
#                                        the query, and answer from a real
#                                        web search only
# "Refinement" (decompose-then-recompose) splits each relevant document
# into strips and keeps only the strips that actually help - a document
# can be "relevant" overall while still containing noise.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "crag_chroma_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

KB_DOCUMENTS = [
    "LangGraph is a library for building stateful, multi-actor applications with LLMs, "
    "built on top of LangChain.",
    "LangGraph models an agent's workflow as a graph of nodes and edges, where nodes are "
    "functions and edges define control flow.",
    "LangGraph supports conditional edges, which let the graph branch to different nodes "
    "based on the current state, similar to an if/else in ordinary code.",
    "LangGraph provides checkpointers such as MemorySaver and SqliteSaver to persist graph "
    "state across runs, which enables human-in-the-loop workflows and time travel.",
    "A LangGraph StateGraph must be compiled into a runnable app with the .compile() method "
    "before it can be invoked or streamed.",
]

vectorstore = Chroma(
    collection_name="langgraph_docs",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory=PERSIST_DIR,
)
vectorstore.add_texts(KB_DOCUMENTS)

grader_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
refiner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
rewriter_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
search_tool = TavilySearch(max_results=3)

Grade = Literal["correct", "ambiguous", "incorrect"]


class CRAGState(TypedDict):
    question: str
    documents: list[str]
    doc_grades: list[bool]
    grade: Grade
    search_query: str
    context: list[str]
    response: str


class DocGrade(BaseModel):
    relevant: bool = Field(description="True if this document contains information that helps answer the question.")


class StripFilter(BaseModel):
    kept_strips: list[str] = Field(description="The subset of the given strips (verbatim) that directly help "
                                    "answer the question. Drop strips that are off-topic or unhelpful.")


class RewrittenQuery(BaseModel):
    search_query: str = Field(description="A short, keyword-focused rewrite of the question, optimized for a web search engine.")


def retrieve(state: CRAGState) -> CRAGState:
    docs = vectorstore.similarity_search(state["question"], k=3)
    print(f"[retrieve] {len(docs)} document(s) retrieved")
    return {"documents": [d.page_content for d in docs]}


def grade_documents(state: CRAGState) -> CRAGState:
    grades = []
    for doc in state["documents"]:
        verdict = grader_llm.with_structured_output(DocGrade).invoke(
            f"Question: {state['question']}\n\nDocument: {doc}\n\n"
            "Does this document contain information that helps answer the question?"
        )
        grades.append(verdict.relevant)
        print(f"[grade_documents] {'RELEVANT  ' if verdict.relevant else 'IRRELEVANT'} - {doc[:60]}...")

    relevant_count = sum(grades)
    if relevant_count == 0:
        grade: Grade = "incorrect"
    elif relevant_count == len(grades):
        grade = "correct"
    else:
        grade = "ambiguous"
    print(f"[grade_documents] overall grade: {grade.upper()} ({relevant_count}/{len(grades)} relevant)")
    return {"doc_grades": grades, "grade": grade}


def route_after_grading(state: CRAGState) -> str:
    return "refine_knowledge" if state["grade"] in ("correct", "ambiguous") else "transform_query"


def refine_knowledge(state: CRAGState) -> CRAGState:
    relevant_docs = [doc for doc, ok in zip(state["documents"], state["doc_grades"]) if ok]
    strips = [s.strip() for doc in relevant_docs for s in doc.split(". ") if s.strip()]

    filtered = refiner_llm.with_structured_output(StripFilter).invoke(
        f"Question: {state['question']}\n\nCandidate knowledge strips:\n"
        + "\n".join(f"- {s}" for s in strips)
        + "\n\nKeep only the strips that directly help answer the question."
    )
    print(f"[refine_knowledge] kept {len(filtered.kept_strips)}/{len(strips)} strip(s)")
    return {"context": filtered.kept_strips}


def route_after_refining(state: CRAGState) -> str:
    return "generate" if state["grade"] == "correct" else "transform_query"


def transform_query(state: CRAGState) -> CRAGState:
    rewritten = rewriter_llm.with_structured_output(RewrittenQuery).invoke(
        f"Rewrite this question into a short, keyword-focused web search query:\n\n{state['question']}"
    )
    print(f"[transform_query] rewritten query: {rewritten.search_query}")
    return {"search_query": rewritten.search_query}


def web_search(state: CRAGState) -> CRAGState:
    result = search_tool.invoke({"query": state["search_query"]})
    snippets = [r["content"] for r in result.get("results", [])]
    print(f"[web_search] {len(snippets)} result(s) found")
    return {"context": state["context"] + snippets}


def generate(state: CRAGState) -> CRAGState:
    context = "\n".join(f"- {c}" for c in state["context"]) or "(no supporting context found)"
    prompt = (
        f"Answer the question using ONLY the context below. Be concise.\n\n"
        f"Context:\n{context}\n\nQuestion: {state['question']}"
    )
    response = answer_llm.invoke(prompt)
    print(f"[generate] {response.content}")
    return {"response": response.content}


graph = StateGraph(CRAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("grade_documents", grade_documents)
graph.add_node("refine_knowledge", refine_knowledge)
graph.add_node("transform_query", transform_query)
graph.add_node("web_search", web_search)
graph.add_node("generate", generate)

graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "grade_documents")
graph.add_conditional_edges("grade_documents", route_after_grading, {
    "refine_knowledge": "refine_knowledge",
    "transform_query": "transform_query",
})
graph.add_conditional_edges("refine_knowledge", route_after_refining, {
    "generate": "generate",
    "transform_query": "transform_query",
})
graph.add_edge("transform_query", "web_search")
graph.add_edge("web_search", "generate")
graph.add_edge("generate", END)

app = graph.compile()


def run(question: str) -> None:
    print("\n" + "=" * 70)
    print(f"QUESTION: {question}")
    print("=" * 70)
    app.invoke({
        "question": question, "documents": [], "doc_grades": [], "grade": "incorrect",
        "search_query": "", "context": [], "response": "",
    })


if __name__ == "__main__":
    # CORRECT: fully answerable from the local knowledge base alone.
    run("How does LangGraph let a graph branch its execution based on state?")

    # AMBIGUOUS: the KB knows about checkpointers but not what's new -
    # the relevant doc is kept and a real web search fills the gap.
    run("Which LangGraph checkpointer should I use for production, and has a newer one been released recently?")

    # INCORRECT: nothing in the KB mentions version numbers - the KB is
    # discarded entirely and the answer comes from a real web search.
    run("What is the latest released version number of langgraph on PyPI right now?")
