# Cosine, L2 and dot product on the help-desk FAQ (deck: "Similarity Metrics").
#
# The customer's question is compared with the four FAQ questions from 04_1
# using each metric. all-MiniLM-L6-v2 returns NORMALISED vectors (length 1), and
# for those the three metrics always agree on the ranking:
#     dot = cosine      and      squared L2 = 2 - 2 * cosine
# That is why ChromaDB's default (squared L2) and a "cosine" collection rank
# the same here. The last part scales one vector to show where they differ.
#
# pip install sentence-transformers numpy   (no API key)
import csv
import os

import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "faq.csv"), encoding="utf-8") as f:
    questions = [row["question"] for row in list(csv.DictReader(f))[:4]]

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
query = "My parcel hasn't come yet - where is it?"
q = model.encode(query)
docs = model.encode(questions)
print(f"Vector lengths: query {np.linalg.norm(q):.2f}, FAQ {[round(float(np.linalg.norm(d)), 2) for d in docs]}\n")


def cosine(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def l2(a, b):
    return float(np.linalg.norm(a - b))


print(f'Customer: "{query}"')
print(f"  {'FAQ question':<38}{'cosine':>8}{'L2':>7}{'L2^2':>7}{'dot':>7}   2-2*cos")
for text, d in zip(questions, docs):
    c = cosine(q, d)
    print(f"  {text:<38}{c:8.2f}{l2(q, d):7.2f}{l2(q, d) ** 2:7.2f}{float(q @ d):7.2f}   {2 - 2 * c:.2f}")
print("  Higher cosine/dot = closer; lower L2 = closer. L2^2 is the distance ChromaDB reports.\n")

# When vectors are NOT normalised, dot product also rewards length
scaled = docs.copy()
scaled[3] = scaled[3] * 3          # pretend "Can I change my delivery address?" came out 3x longer
best_by = {
    "cosine": max(range(4), key=lambda i: cosine(q, scaled[i])),
    "L2": min(range(4), key=lambda i: l2(q, scaled[i])),
    "dot": max(range(4), key=lambda i: float(q @ scaled[i])),
}
print("After making one vector 3x longer, the best match by each metric:")
for metric, i in best_by.items():
    print(f"  {metric:<7} {questions[i]}")
