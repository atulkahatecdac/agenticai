import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
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

# =====================================================================
# A simple long-term-memory assistant, LangChain only (no LangGraph),
# using RAG as the actual memory mechanism.
#
# Contrast with 14_advanced/05_langchain/05_4_persistent_chatbot.py: that
# file persists the FULL raw message log (SQLChatMessageHistory) and
# replays all of it into the prompt every turn - fine for one ongoing
# chat, doesn't scale, and isn't RAG. Here, every past exchange is
# saved as its own document in a persistent Chroma vector store, and
# only the ones semantically relevant to the CURRENT question are
# retrieved - the actual point of using RAG for memory instead of just
# replaying history.
#
# "Long-term" is proven, not asserted: run this script once (arg "1")
# to have a conversation, then run it again as a SEPARATE process (arg
# "2") - the second run recalls facts from the first purely because
# Chroma's persist_directory survives the first process exiting.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "langchain_memory_db")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

memory_store = Chroma(
    collection_name="long_term_memory",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIR,
)
retriever = memory_store.as_retriever(search_kwargs={"k": 3})

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful personal assistant with long-term memory. Use the "
               "relevant past memories below if they help answer the question; ignore "
               "them if they're not relevant. Don't claim to remember something that "
               "isn't in the memories provided.\n\nRelevant memories:\n{memories}"),
    ("human", "{question}"),
])


def format_memories(docs) -> str:
    return "\n".join(f"- {d.page_content}" for d in docs) if docs else "(none found)"


# Same LCEL shape as 14_advanced/05_langchain/05_7_rag_pipeline.py:
# {"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm
chain = (
    {"memories": retriever | format_memories, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


def ask(question: str) -> str:
    answer = chain.invoke(question)
    memory_store.add_texts([f"Q: {question}\nA: {answer}"])  # write this exchange back for future retrieval
    return answer


if __name__ == "__main__":
    session = sys.argv[1] if len(sys.argv) > 1 else "1"

    if session == "1":
        print("=== SESSION 1 (run: python langchain_long_term_memory_rag.py 1) ===\n")

        q1 = "Hi, I'm Priya. I'm allergic to peanuts and I love hiking on weekends."
        print(f"You: {q1}")
        print(f"Assistant: {ask(q1)}\n")

        q2 = "Can you suggest a good trail snack for this weekend's hike?"
        print(f"You: {q2}")
        print(f"Assistant: {ask(q2)}\n")

        print("Now run this script again with arg '2' (a separate process) to see it "
              "recall these facts from the persisted vector store.")
    else:
        print("=== SESSION 2 (new process, run: python langchain_long_term_memory_rag.py 2) ===\n")

        q3 = "What do you remember about my dietary restrictions?"
        print(f"You: {q3}")
        print(f"Assistant: {ask(q3)}\n")

        q4 = "What do I like doing on weekends?"
        print(f"You: {q4}")
        print(f"Assistant: {ask(q4)}")
