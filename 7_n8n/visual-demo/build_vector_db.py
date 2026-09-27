"""
Build the Qdrant vector database for the visual-similarity demo.

For every photo in ../synthetic_people_demo (P001.jpg ... P050.jpg):
    image -> FastAPI /embedding (MTCNN + FaceNet) -> 512 numbers -> Qdrant

The person's metadata from people.csv is stored alongside each vector as the
Qdrant "payload", so a search returns both the similarity score and who it is.

Prerequisites:
    1. Embedding API running:   venv\\Scripts\\python main.py
    2. Qdrant running locally:  http://localhost:6333

Run:
    venv\\Scripts\\python build_vector_db.py
"""

import csv
import os

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


EMBEDDING_API = "http://localhost:8001/embedding"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "people_faces"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "synthetic_people_demo")
CSV_FILE = os.path.join(DATA_DIR, "people.csv")


def get_embedding(image_path):
    # Same service n8n calls, so stored and query vectors match exactly
    with open(image_path, "rb") as f:
        response = requests.post(
            EMBEDDING_API,
            files={"image": (os.path.basename(image_path), f, "image/jpeg")},
            data={"save": "false"}      # database photos don't need an upload copy
        )
    response.raise_for_status()
    return response.json()["embedding"]


def main():
    client = QdrantClient(url=QDRANT_URL)

    # Start fresh each run so the demo is repeatable
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)

    # 512 dimensions = FaceNet output, cosine = angle between face vectors
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=512, distance=Distance.COSINE)
    )
    print(f"Created collection '{COLLECTION}'")

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        people = list(csv.DictReader(f))

    points = []
    for person in people:
        image_path = os.path.join(DATA_DIR, person["image_file"])

        try:
            vector = get_embedding(image_path)
        except requests.HTTPError as e:
            print(f"  SKIP {person['image_file']}: {e.response.text}")
            continue

        points.append(
            PointStruct(
                # Qdrant ids must be int or UUID: P017 -> 17
                id=int(person["person_id"][1:]),
                vector=vector,
                payload={
                    "person_id": person["person_id"],
                    "name": person["name"],
                    "age": int(person["age"]),
                    "department": person["department"],
                    "location": person["location"],
                    "image_file": person["image_file"],
                }
            )
        )
        print(f"  Embedded {person['image_file']} ({person['name']})")

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"\nInserted {len(points)} vectors into '{COLLECTION}'")

    # Sanity check: search with P017's own photo, it should be match #1
    test_vector = get_embedding(os.path.join(DATA_DIR, "P017.jpg"))
    results = client.query_points(
        collection_name=COLLECTION,
        query=test_vector,
        limit=5,
        with_payload=True
    ).points

    print("\nTest search with P017.jpg - top 5:")
    for rank, hit in enumerate(results, start=1):
        payload = hit.payload or {}
        print(f"  Match {rank} -> {payload['person_id']} "
              f"{payload['name']:<10} -> {hit.score:.2f}")


if __name__ == "__main__":
    main()
