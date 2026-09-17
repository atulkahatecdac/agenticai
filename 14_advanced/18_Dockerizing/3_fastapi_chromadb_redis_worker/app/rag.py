import os

import chromadb
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Everything in this module runs ONLY in the worker - the api container never
# imports this file's OpenAI/Chroma logic, it only ever touches Redis (queue.py).
CHROMA_HOST = os.environ.get("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
COLLECTION_NAME = "agent_docs"

_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer the question using ONLY the provided context. If the context doesn't "
            "contain the answer, say you don't know. Be concise.",
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def build_vectorstore() -> Chroma:
    # ChromaDB runs as its OWN container (not embedded in-process) specifically
    # so multiple worker replicas (see docker-compose.yml's --scale note) can
    # all read/write the same collection instead of each holding a private,
    # out-of-sync copy of the index.
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )


def build_answer_chain() -> Runnable:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _ANSWER_PROMPT | llm | StrOutputParser()


async def ingest_document(vectorstore: Chroma, doc_id: str, text: str) -> dict:
    vectorstore.add_texts(texts=[text], ids=[doc_id])
    return {"doc_id": doc_id, "chars_indexed": len(text)}


async def answer_question(vectorstore: Chroma, answer_chain: Runnable, question: str, k: int = 3) -> dict:
    docs = vectorstore.similarity_search(question, k=k)
    if not docs:
        return {"answer": "I don't know - no documents have been ingested yet.", "sources": []}
    context = "\n\n".join(doc.page_content for doc in docs)
    answer = await answer_chain.ainvoke({"context": context, "question": question})
    sources = [doc.id for doc in docs if getattr(doc, "id", None)]
    return {"answer": answer.strip(), "sources": sources}
