"""agent.py - the AI part of the app: send the question to an LLM, return the answer.

backend.py calls run_agent(query). The UI and the API never talk to the LLM
directly, so you can make this smarter later (tools, memory...) without
touching the other two files.
"""
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

llm = ChatOpenAI(model="gpt-4o-mini")


def run_agent(query: str):
    response = llm.invoke(query)
    return response.content


if __name__ == "__main__":
    # Quick check without the API or UI: python agent.py
    print(run_agent("What is FastAPI used for? Answer in one sentence."))
