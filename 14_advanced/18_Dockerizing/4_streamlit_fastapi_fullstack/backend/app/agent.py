"""The AI part of the app: send the question to an LLM, return the answer.

main.py calls run_agent(query). Neither the API layer nor the UI talks to the
LLM directly, so this can grow (tools, memory, RAG...) without touching them.
Same split as 14_advanced/02_frontend_backend_agent/agent.py.
"""
from langchain_openai import ChatOpenAI


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


def run_agent(llm: ChatOpenAI, query: str) -> str:
    return str(llm.invoke(query).content)
