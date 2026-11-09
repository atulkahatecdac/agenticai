import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import csv
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tracers.context import tracing_v2_enabled
from langchain_core._api.deprecation import LangChainDeprecationWarning, LangChainPendingDeprecationWarning

# langchain_core re-enables its own deprecation warnings on import, which runs
# AFTER our filters above and so overrides them - reapply now (same fix as
# 14_advanced/05_langchain/05_4_persistent_chatbot.py).
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with other exercises in this repo (a
# CrewAI market-research demo) - use a dedicated project here, same reasoning
# as 14_advanced/09_langsmith/09_1_langsmith_tracing.py, so traces don't mix.
os.environ["LANGSMITH_PROJECT"] = "agenticai-15-real-support-rag"

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Same idea as langfuse_rag_tracing.py / langfuse_langchain_rag_tracing.py
# (retrieve -> generate, traced as a tree of steps) but sent to LangSmith
# instead of Langfuse.
#
# The RAG chain itself is IDENTICAL to langfuse_langchain_rag_tracing.py -
# same LCEL shape, same FAQ vectorstore. The only thing that changes is
# where the trace goes and how tracing gets turned on:
#   - Langfuse (langfuse_langchain_rag_tracing.py) needed an explicit
#     CallbackHandler attached via config={"callbacks": [...]}.
#   - LangSmith needs NO code at all - with LANGSMITH_TRACING=true and
#     LANGSMITH_API_KEY set (already in .env), every LangChain run in this
#     process is traced automatically. tracing_v2_enabled() below is only
#     used to grab each run's URL afterward to prove it landed there - not
#     to turn tracing on (it's already on). Same distinction drawn in
#     14_advanced/09_langsmith/09_1_langsmith_tracing.py's part 1.
#
# LangSmith also builds the retriever-then-LLM tree automatically, the
# same way Langfuse's CallbackHandler does - open a run in the LangSmith
# UI and the retriever step and the chat model call show up as separate
# nested spans under the chain run.
#
# After running, open the trace list at:
#   https://smith.langchain.com  ->  project "agenticai-15-real-support-rag"
# =====================================================================

CSV_PATH = os.path.join(os.path.dirname(__file__), "customer_support_qa_500.csv")
MODEL = "gpt-4o-mini"
TOP_K = 3


def load_documents(csv_path: str) -> list[Document]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [Document(page_content=f"Q: {row['question']}\nA: {row['answer']}", metadata={"id": row["id"]}) for row in rows]


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(d.page_content for d in docs)


embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma.from_documents(load_documents(CSV_PATH), embeddings, collection_name="support_faq_langsmith")
retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a customer support assistant. Answer using ONLY the FAQ context below - "
               "do not invent policies. Keep it short.\n\nFAQ context:\n{context}"),
    ("human", "{question}"),
])

llm = ChatOpenAI(model=MODEL, temperature=0)

# Same LCEL shape as langfuse_langchain_rag_tracing.py, langchain_long_term_memory_rag.py,
# and 14_advanced/05_langchain/05_7_rag_pipeline.py:
# {"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


def ask(question: str) -> tuple[str, str]:
    """Tracing is already on via env vars - tracing_v2_enabled() here is only
    used to capture the resulting run's URL, not to enable tracing itself."""
    with tracing_v2_enabled(project_name=os.environ["LANGSMITH_PROJECT"]) as tracer:
        answer = chain.invoke(question, config={"run_name": "support-query"})
        return answer, tracer.get_run_url()


if __name__ == "__main__":
    questions = [
        "How do I reset my password?",
        "What is your return policy for damaged items?",
        "How do I enable two-factor authentication?",
    ]

    for question in questions:
        answer, trace_url = ask(question)
        print(f"Q: {question}")
        print(f"A: {answer}")
        print(f"View trace: {trace_url}\n")

    print(f"All traces: https://smith.langchain.com -> project '{os.environ['LANGSMITH_PROJECT']}'")
