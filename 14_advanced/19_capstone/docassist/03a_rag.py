# Plain RAG: ALWAYS search, then answer from what was found.
# Run 02b_ingest_pdfs.py first.
import os
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI()
DATABASE_URL = os.environ["DATABASE_URL"]

MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"


def search(question, k=3):
    vector = client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    with psycopg.connect(DATABASE_URL) as conn:
        return conn.execute(
            "SELECT source, content FROM chunks "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (str(vector), k),
        ).fetchall()


def ask(question):
    chunks = search(question)
    context = "\n\n".join(f"[{source}]\n{content}" for source, content in chunks)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content":
                "Answer only from the context below. If the answer is not "
                "there, say you don't know. Name the source file.\n\n" + context},
            {"role": "user", "content": question},
        ],
    )
    print("Q:", question)
    print("searched:", [source for source, _ in chunks])
    print("A:", response.choices[0].message.content, "\n")


ask("How many days of annual leave can I carry forward?")
ask("What is the hotel limit in Pune?")
ask("Hi, good morning!")   # still searches the documents - wasted work
