import os
import cohere
from dotenv import load_dotenv

load_dotenv(override=True)

# =====================================================================
# Reranking: a first-pass retriever (keyword search, a cheap embedding
# model, whatever) is tuned for recall, not precision - it returns
# plausible candidates in a rough order. A reranker is a cross-encoder:
# it looks at the query and each FULL candidate together (instead of
# comparing two separate embeddings), which is slower but far more
# accurate - so it only runs on the small candidate list a retriever
# already narrowed things down to, not the whole corpus.
# =====================================================================

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

query = "How do I persist LangGraph state across runs?"

# Candidates as a naive keyword retriever might return them - ordered by
# crude word overlap with the query, not by which one actually answers it.
candidates = [
    "LangGraph supports conditional edges, which let the graph branch to different nodes based on the current state.",
    "A LangGraph StateGraph must be compiled into a runnable app with the .compile() method before it can be invoked.",
    "LangGraph provides checkpointers such as MemorySaver and SqliteSaver to persist graph state across runs, enabling human-in-the-loop workflows.",
    "State in LangGraph is just a TypedDict or Pydantic model that every node reads from and writes back to.",
    "LangGraph is built on top of LangChain and models an agent's workflow as a graph of nodes and edges.",
]

print(f"QUERY: {query}\n")
print("BEFORE (naive retrieval order):")
for i, doc in enumerate(candidates, start=1):
    print(f"  [{i}] {doc}")

results = co.rerank(
    model="rerank-v4.0-pro",
    query=query,
    documents=candidates,
    top_n=3,
)

print("\nAFTER (Cohere rerank, top 3 by true relevance):")
for rank, result in enumerate(results.results, start=1):
    print(f"  [{rank}] score={result.relevance_score:.3f}  {candidates[result.index]}")
