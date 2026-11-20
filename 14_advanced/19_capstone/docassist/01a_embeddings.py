from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)
client = OpenAI()

EMBED_MODEL = "text-embedding-3-small"   # turns text into 1536 numbers

SENTENCES = [
    "Employees get 18 days of annual leave per year.",
    "The hotel limit in Mumbai is INR 7,000 per night.",
    "Our office cafeteria serves lunch from 12 to 2.",
]
QUESTION = "How many holidays can I take in a year?"

response = client.embeddings.create(
    model=EMBED_MODEL,
    input=SENTENCES + [QUESTION],
)
vectors = [item.embedding for item in response.data]
print("Each text became", len(vectors[0]), "numbers")


def similarity(a, b):
    # OpenAI embeddings have length 1, so the dot product is the cosine similarity
    return sum(x * y for x, y in zip(a, b))


question_vector = vectors[-1]
for sentence, vector in zip(SENTENCES, vectors):
    print(f"{similarity(question_vector, vector):.3f}  {sentence}")

# The leave sentence scores highest although it shares no words with
# "holidays" - embeddings compare meaning, not keywords.
