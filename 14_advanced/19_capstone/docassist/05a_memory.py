# Short-term memory in Postgres: every message is saved in a table, and the
# last few messages of the same session are sent with each new question.
# Because the memory is in the database, it survives a restart of this script.
#   python 05a_memory.py first      -> asks a question
#   python 05a_memory.py second     -> a follow-up that only makes sense with memory
import importlib
import os
import sys
import psycopg

agent = importlib.import_module("04a_agentic_rag")   # reuse the agent from step 04
DATABASE_URL = os.environ["DATABASE_URL"]           # importing 04a already loaded .env
SESSION_ID = "demo-user-1"   # one conversation; the web app gives each browser its own
MEMORY_SIZE = 10             # "short-term": only the last 10 messages are remembered

with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, "
        "session_id TEXT, role TEXT, content TEXT, "
        "created_at TIMESTAMPTZ DEFAULT now())"
    )


def load_history(session_id):
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = %s "
            "ORDER BY id DESC LIMIT %s",
            (session_id, MEMORY_SIZE)).fetchall()
    # newest first from SQL -> oldest first
    return [{"role": role, "content": content}
            for role, content in reversed(rows)]


def save_message(session_id, role, content):
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )


def chat(question):
    history = load_history(SESSION_ID)
    print(f"(remembered {len(history)} earlier messages)")
    print("Q:", question)
    messages = ([{"role": "system", "content": agent.SYSTEM}] + history
                + [{"role": "user", "content": question}])
    answer = agent.run_agent(messages)
    save_message(SESSION_ID, "user", question)
    save_message(SESSION_ID, "assistant", answer)
    print("A:", answer, "\n")


if len(sys.argv) > 1 and sys.argv[1] == "second":
    chat("And what about interns?")          # "what about" what? memory knows
else:
    chat("How much annual leave does a full-time employee get?")
