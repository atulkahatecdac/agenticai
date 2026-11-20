# Everything that talks to Postgres: the tables, the document chunks
# (with their pgvector embeddings) and the conversation memory.
import os
import psycopg

# On a laptop this comes from .env (localhost:5433);
# in Docker Compose it is set to db:5432 - same code, different address.
DATABASE_URL = os.environ["DATABASE_URL"]
MEMORY_SIZE = 10   # the agent sees only the last 10 messages of a session


def connect():
    return psycopg.connect(DATABASE_URL, autocommit=True)


def create_tables():
    with connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunks ("
            "id SERIAL PRIMARY KEY, source TEXT, content TEXT, embedding VECTOR(1536))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id SERIAL PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, "
            "created_at TIMESTAMPTZ DEFAULT now())"
        )


# ---- documents ----
def replace_chunks(source, pieces, vectors):
    with connect() as conn:
        conn.execute("DELETE FROM chunks WHERE source = %s", (source,))
        for piece, vector in zip(pieces, vectors):
            conn.execute(
                "INSERT INTO chunks (source, content, embedding) VALUES (%s, %s, %s)",
                (source, piece, str(vector)),
            )


def nearest_chunks(vector, k=3):
    with connect() as conn:
        return conn.execute(
            "SELECT source, content FROM chunks "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (str(vector), k),
        ).fetchall()


def list_sources():
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT source FROM chunks ORDER BY source").fetchall()
    return [row[0] for row in rows]


# ---- short-term memory ----
def save_message(session_id, role, content):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )


def load_history(session_id, limit=MEMORY_SIZE):
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = %s "
            "ORDER BY id DESC LIMIT %s",
            (session_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]
