# Retrieval: PDF -> text -> chunks -> embeddings -> Postgres, and search.
from openai import OpenAI
from pypdf import PdfReader

import database

client = OpenAI()
EMBED_MODEL = "text-embedding-3-small"


def chunk(text, size=500, overlap=100):
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start:start + size])
        start += size - overlap
    return pieces


def embed(texts):
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]


def add_document(name, file):
    reader = PdfReader(file)
    text = "\n".join(page.extract_text() for page in reader.pages)
    pieces = chunk(text)
    if not pieces:
        return 0   # e.g. a scanned PDF with no text layer
    database.replace_chunks(name, pieces, embed(pieces))
    return len(pieces)


def search(query, k=3):
    return database.nearest_chunks(embed([query])[0], k)
