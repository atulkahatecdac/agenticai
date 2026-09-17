from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

# Kept in its own module, separate from main.py's routing/HTTP concerns, so the
# LangChain piece can be built/tested (or swapped for a different chain) without
# touching anything FastAPI-related.
_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You summarize text in at most 3 plain-language sentences. No preamble, no bullet points."),
        ("human", "{text}"),
    ]
)


def build_summarize_chain() -> Runnable:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _PROMPT | llm | StrOutputParser()
