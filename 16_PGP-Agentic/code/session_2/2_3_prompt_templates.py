import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from datetime import date
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# -----------------------------
# 1. ChatPromptTemplate
# A fixed sequence of role/content pairs with {variables} filled in at
# invoke time. This is the basic building block every chain starts from.
# -----------------------------
print("=" * 70)
print("1. ChatPromptTemplate - fixed structure, variables filled at invoke time")
print("=" * 70)

basic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a {tone} assistant who explains things simply."),
    ("human", "Explain {topic} in one sentence."),
])

basic_chain = basic_prompt | llm | StrOutputParser()
result = basic_chain.invoke({"tone": "cheerful", "topic": "photosynthesis"})
print(f"Answer: {result}")

# format_messages() shows exactly what gets sent to the LLM, without calling it
print("\nActual messages sent:")
for m in basic_prompt.format_messages(tone="cheerful", topic="photosynthesis"):
    print(f"  [{m.type}] {m.content}")

# -----------------------------
# 2. MessagesPlaceholder
# Reserves a spot in the template for a variable-length LIST of messages -
# typically prior conversation turns - instead of a single {variable}.
# -----------------------------
print("\n" + "=" * 70)
print("2. MessagesPlaceholder - inserting chat history into the template")
print("=" * 70)

history_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Keep answers short."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

chat_history = [
    HumanMessage(content="My name is Atul."),
    AIMessage(content="Nice to meet you, Atul!"),
]

history_chain = history_prompt | llm | StrOutputParser()
result = history_chain.invoke({"history": chat_history, "question": "What is my name?"})
print(f"Answer: {result}")

print("\nActual messages sent:")
for m in history_prompt.format_messages(history=chat_history, question="What is my name?"):
    print(f"  [{m.type}] {m.content}")

# -----------------------------
# 3. Partial templates
# .partial() freezes some variables ahead of time so callers only need to
# supply the ones that actually change per call. Frozen values can be a
# fixed value, or a zero-arg callable that's re-evaluated on every call
# (useful for things like "today's date").
# -----------------------------
print("\n" + "=" * 70)
print("3. Partial templates - freezing some variables before invoke time")
print("=" * 70)

partial_prompt = ChatPromptTemplate.from_messages([
    ("system", "Today's date is {today}. You are a {tone} assistant."),
    ("human", "{question}"),
])

# Freeze "tone" to a fixed value, and "today" to a callable evaluated at call time
frozen_prompt = partial_prompt.partial(
    tone="formal",
    today=lambda: date.today().isoformat(),
)

print(f"Original input variables: {partial_prompt.input_variables}")
print(f"Remaining input variables after partial(): {frozen_prompt.input_variables}")

partial_chain = frozen_prompt | llm | StrOutputParser()
result = partial_chain.invoke({"question": "What is today's date, and can you confirm your tone?"})
print(f"\nAnswer: {result}")
