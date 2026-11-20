# Start Postgres with the pgvector extension first (one command, see README):
#   docker run -d --name docassist-db -e POSTGRES_PASSWORD=docassist123
#     -e POSTGRES_DB=docassist -p 5433:5432 pgvector/pgvector:pg17
import os
import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI()
DATABASE_URL = os.environ["DATABASE_URL"]   # the database address comes from .env

EMBED_MODEL = "text-embedding-3-small"


def embed(texts):
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    # pgvector accepts a vector written as text: "[0.1, 0.2, ...]"
    return [str(item.embedding) for item in response.data]


conn = psycopg.connect(DATABASE_URL, autocommit=True)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
conn.execute("DROP TABLE IF EXISTS demo")
conn.execute("CREATE TABLE demo (content TEXT, embedding VECTOR(1536))")

SENTENCES = [
    "Employees get 18 days of annual leave per year.",
    "The hotel limit in Mumbai is INR 7,000 per night.",
    "Our office cafeteria serves lunch from 12 to 2.",
]
for sentence, vector in zip(SENTENCES, embed(SENTENCES)):
    conn.execute("INSERT INTO demo VALUES (%s, %s)", (sentence, vector))

question = "Where can I stay in Mumbai?"
question_vector = embed([question])[0]

# <=> is pgvector's cosine distance: smaller = more similar
rows = conn.execute(
    "SELECT content, embedding <=> %s::vector AS distance "
    "FROM demo ORDER BY distance LIMIT 2",
    (question_vector,),
).fetchall()

print("Question:", question)
for content, distance in rows:
    print(f"{distance:.3f}  {content}")
conn.close()
