import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core._api.deprecation import (
    LangChainDeprecationWarning,
    LangChainPendingDeprecationWarning,
)

# langchain_core re-enables its own deprecation warnings on import, which
# runs AFTER our filters above and so overrides them - reapply now.
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chat_history.db")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a friendly, helpful assistant. Keep answers concise."),
    MessagesPlaceholder(variable_name="history"), # Previous chat history
    ("human", "{input}"),
])

chain = prompt | llm

# All sessions share one SQLite DB, in a "message_store" table keyed by
# session_id - so the conversation survives even after this script exits
# and is rerun later, unlike the in-memory ConversationBufferMemory/etc.
# from memory_types.py.
def get_session_history(session_id: str) -> SQLChatMessageHistory:
    return SQLChatMessageHistory(session_id=session_id, connection=f"sqlite:///{DB_PATH}")

chatbot = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

if __name__ == "__main__":
    session_id = input("Enter your name/session id: ").strip() or "default_user"
    
    # This tells LangChain to load the history from disk for this session_id
    config = {"configurable": {"session_id": session_id}}

    # Load past messages for this user if they exist
    past_messages = get_session_history(session_id).messages
    if past_messages:
        print(f"\nWelcome back, {session_id}! Restored {len(past_messages)} messages from a previous session.")
    else:
        print(f"\nHi {session_id}, starting a new conversation.")

    print("Type 'quit' to exit. Your conversation is saved and will resume next time.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye! Your conversation has been saved.")
            break

        if not user_input:
            continue

        response = chatbot.invoke({"input": user_input}, config=config)
        print(f"Bot: {response.content}\n")
