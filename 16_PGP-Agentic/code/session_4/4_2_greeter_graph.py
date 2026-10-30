import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# =====================================================================
# Deliberately the simplest possible graph with a branch - just enough
# for LangGraph Studio to show something worth looking at: a classify
# node, a conditional edge, and two reply nodes. Studio imports this
# module and reads the compiled `app` object below - it must NOT run
# anything (no .invoke()/.stream() at module scope), it only calls the
# graph when you send it input from the Studio UI.
# =====================================================================


class GreeterState(TypedDict):
    message: str
    mood: str
    reply: str


class MoodClassification(BaseModel):
    mood: Literal["happy", "sad"] = Field(description="Overall mood of the message.")


classify_prompt = ChatPromptTemplate.from_template(
    "Classify the overall mood of this message as happy or sad:\n\n{message}"
)
classify_chain = classify_prompt | llm.with_structured_output(MoodClassification)


def classify_mood(state: GreeterState) -> GreeterState:
    result = classify_chain.invoke({"message": state["message"]})
    return {"mood": result.mood}


def route_by_mood(state: GreeterState) -> str:
    return state["mood"]


def cheerful_reply(state: GreeterState) -> GreeterState:
    response = llm.invoke(f"Reply cheerfully and briefly to: {state['message']}")
    return {"reply": response.content}


def sympathetic_reply(state: GreeterState) -> GreeterState:
    response = llm.invoke(f"Reply with a short, warm, sympathetic message to: {state['message']}")
    return {"reply": response.content}


graph = StateGraph(GreeterState)
graph.add_node("classify_mood", classify_mood)
graph.add_node("cheerful_reply", cheerful_reply)
graph.add_node("sympathetic_reply", sympathetic_reply)

graph.add_edge(START, "classify_mood")
graph.add_conditional_edges(
    "classify_mood",
    route_by_mood,
    {"happy": "cheerful_reply", "sad": "sympathetic_reply"},
)
graph.add_edge("cheerful_reply", END)
graph.add_edge("sympathetic_reply", END)

# Studio looks up a compiled graph by name, so this one could be added to
# langgraph.json too (that file currently lists only stock_news).
app = graph.compile()

if __name__ == "__main__":
    # Optional: lets you sanity-check the graph with `python 4_2_greeter_graph.py`
    # without needing Studio at all.
    for msg in ["I just got promoted!", "My cat passed away yesterday."]:
        result = app.invoke({"message": msg, "mood": "", "reply": ""})
        print(f"Message: {msg}\nMood: {result['mood']}\nReply: {result['reply']}\n")
