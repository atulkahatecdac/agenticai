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
from langchain_core._api.deprecation import LangChainDeprecationWarning, LangChainPendingDeprecationWarning

# langchain_core re-enables its own deprecation warnings on import, which runs
# AFTER our filters above and so overrides them - reapply now (same fix as
# 14_advanced/05_langchain/05_4_persistent_chatbot.py).
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

os.environ.pop("OTEL_SDK_DISABLED", None)
os.environ["LANGFUSE_TRACING_ENABLED"] = "true"

from langfuse import get_client
from langfuse.langchain import CallbackHandler

# =====================================================================
# Same idea as langfuse_rag_tracing.py (retrieve -> generate, traced as a
# tree instead of one flat call) but built the LangChain-native way
# instead of by hand.
#
# langfuse_rag_tracing.py calls chromadb directly and manually opens a
# parent span plus a "retriever" and a "generation" child observation
# with langfuse.start_as_current_observation(). Here the RAG pipeline is
# an ordinary LangChain LCEL chain (same shape as
# langchain_long_term_memory_rag.py's retriever | prompt | llm chain),
# and langfuse.langchain.CallbackHandler is attached via
# config={"callbacks": [...]}. LangChain's own run events (chain start/
# end, retriever start/end, llm start/end) are what create the trace
# tree - retriever runs become "retriever" observations, the chat model
# call becomes a "generation" observation, automatically nested under
# the chain's run - no manual span code at all. This is the standard way
# to trace any LangChain/LangGraph app with Langfuse.
#
# After running, open the trace list at:
#   https://us.cloud.langfuse.com  ->  your project  ->  Tracing
# =====================================================================

CSV_PATH = os.path.join(os.path.dirname(__file__), "customer_support_qa_500.csv")
MODEL = "gpt-4o-mini"
TOP_K = 3

langfuse = get_client()
langfuse_handler = CallbackHandler()


def load_documents(csv_path: str) -> list[Document]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [Document(page_content=f"Q: {row['question']}\nA: {row['answer']}", metadata={"id": row["id"]}) for row in rows]


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(d.page_content for d in docs)


embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma.from_documents(load_documents(CSV_PATH), embeddings, collection_name="support_faq_langchain")
retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a customer support assistant. Answer using ONLY the FAQ context below - "
               "do not invent policies. Keep it short.\n\nFAQ context:\n{context}"),
    ("human", "{question}"),
])

llm = ChatOpenAI(model=MODEL, temperature=0)

# Same LCEL shape as langchain_long_term_memory_rag.py and
# 14_advanced/05_langchain/05_7_rag_pipeline.py:
# {"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


def ask(question: str) -> str:
    """Every node of the chain (retriever + chat model) reports itself to
    Langfuse through the callback handler - no manual tracing code here."""
    return chain.invoke(question, config={"callbacks": [langfuse_handler], "run_name": "support-query"})


if __name__ == "__main__":
    if not langfuse.auth_check():
        raise SystemExit("Langfuse authentication failed - check LANGFUSE_SECRET_KEY/PUBLIC_KEY/BASE_URL in .env.")
    print("Langfuse client authenticated.\n")

    questions = [
        "How do I reset my password?",
        "What is your return policy for damaged items?",
        "How do I enable two-factor authentication?",
    ]

    for question in questions:
        print(f"Q: {question}")
        print(f"A: {ask(question)}\n")

    langfuse.flush()  # short-lived script - make sure everything is sent before exit
    print("Traces sent. View them at https://us.cloud.langfuse.com -> your project -> Tracing")
