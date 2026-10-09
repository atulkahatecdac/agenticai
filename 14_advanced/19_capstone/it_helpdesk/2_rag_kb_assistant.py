# =====================================================================
# STEP 2: Answer "how do I ...?" questions with RAG.
#
#   question -> retrieve top chunks from Chroma -> stuff them into the
#   prompt -> local LLM writes an answer that CITES the doc ids.
#
# The prompt does the heavy lifting:
#   - answer ONLY from the context (grounding)
#   - cite every fact as [KB-101]
#   - say "I don't know" when the context doesn't cover it
#     (try the last sample question - it is not in the KB)
#
# This file also defines search_kb as a LangChain TOOL, so the agents in
# later steps can decide for themselves WHEN to look things up.
#
# Run it:
#   python 2_rag_kb_assistant.py
#   python 2_rag_kb_assistant.py "how long is a password reset link valid?"
# =====================================================================
import sys

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from common import get_llm, get_vectorstore

retriever = get_vectorstore().as_retriever(search_kwargs={"k": 4})


def format_docs(docs) -> str:
    return "\n\n".join(f"[{d.metadata['doc_id']}]\n{d.page_content}" for d in docs)


@tool
def search_kb(query: str) -> str:
    """Search the IT knowledge base (troubleshooting guides and IT policies:
    VPN, passwords/MFA, email, Wi-Fi, printing, access policy, laptops,
    security incidents, ticket priorities). Returns text passages, each
    labelled with its document id such as [KB-101]."""
    return format_docs(retriever.invoke(query))


RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are the BrightPath IT helpdesk assistant.\n"
     "Answer the employee's question using ONLY the context below.\n"
     "- Give short, numbered steps when the answer is a procedure.\n"
     "- Cite the source after each fact, like [KB-101].\n"
     "- If the context does not contain the answer, say: "
     "\"I don't have that in the IT knowledge base\" and suggest raising a ticket. Do not guess.\n\n"
     "Context:\n{context}"),
    ("human", "{question}"),
])

# LCEL: a dict of parallel steps -> prompt -> LLM -> plain string
rag_chain = (
    {"context": retriever | format_docs, "question": lambda q: q}
    | RAG_PROMPT
    | get_llm()
    | StrOutputParser()
)


if __name__ == "__main__":
    questions = sys.argv[1:] or [
        "How do I print on the office printer?",
        "I got a new phone, what happens to my MFA?",
        "Who has to approve access to the Payroll System?",
        "How do I book a meeting room?",          # not in the KB -> should say so
    ]
    for q in questions:
        print(f"Q: {q}")
        print(f"A: {rag_chain.invoke(q)}\n" + "-" * 70)
