import os
import psycopg
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv(override=True)
client = OpenAI()
DATABASE_URL = os.environ["DATABASE_URL"]

EMBED_MODEL = "text-embedding-3-small"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "sample_docs")


def read_pdf(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() for page in reader.pages)


def chunk(text, size=500, overlap=100):
    # Fixed-size pieces that overlap a little, so a sentence cut at
    # the end of one chunk also appears at the start of the next
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start:start + size])
        start += size - overlap
    return pieces


def embed(texts):
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [str(item.embedding) for item in response.data]


conn = psycopg.connect(DATABASE_URL, autocommit=True)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
conn.execute(
    "CREATE TABLE IF NOT EXISTS chunks ("
    "id SERIAL PRIMARY KEY, source TEXT, content TEXT, embedding VECTOR(1536))"
)

for file_name in sorted(os.listdir(DOCS_DIR)):
    if not file_name.endswith(".pdf"):
        continue
    pieces = chunk(read_pdf(os.path.join(DOCS_DIR, file_name)))
    # Running the script again replaces a document instead of duplicating it
    conn.execute("DELETE FROM chunks WHERE source = %s", (file_name,))
    for piece, vector in zip(pieces, embed(pieces)):   # one API call per file
        conn.execute(
            "INSERT INTO chunks (source, content, embedding) VALUES (%s, %s, %s)",
            (file_name, piece, vector),
        )
    print(f"{file_name}: {len(pieces)} chunks stored")

total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
print("Total chunks in Postgres:", total)
conn.close()
