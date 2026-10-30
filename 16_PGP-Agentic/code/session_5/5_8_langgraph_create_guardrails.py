import os
# pip install datasets langchain-community

from datasets import load_dataset
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Original dataset: https://huggingface.co/datasets/budecosystem/guardrail-training-data
# Load dataset
ds = load_dataset("budecosystem/guardrail-training-data", split="train")

# sample categories
TARGET_CATEGORIES = {
    "jailbreak_prompt_injection",
    "violence_aiding_and_abetting_incitement",
    "financial_crime_property_crime_theft",
    "discrimination_stereotype_injustice",
    "non_violent_unethical_behavior",
    "privacy_violation",
    "fraud_deception_misinformation"
}

MAX_PER_CATEGORY = 1000  # keep small for practice
CHROMA_PATH = os.path.join(BASE_DIR, "guardrail_chromadb")

collected = {cat: 0 for cat in TARGET_CATEGORIES}
texts = []
metadatas = []

for row in ds:
    category = row.get("category")

    if category in TARGET_CATEGORIES and collected[category] < MAX_PER_CATEGORY:
        text = row.get("text", "")
        if text:
            texts.append(text)
            metadatas.append({
                "category": category,
                "is_safe": row.get("is_safe"),
                "source": row.get("source")
            })
            collected[category] += 1
            print(f"Collected {collected[category]} samples for {category}")

    # stop early when all categories are filled
    if all(count >= MAX_PER_CATEGORY for count in collected.values()):
        break

print("Collected samples:")
for k, v in collected.items():
    print(f"{k}: {v}")

print(f"\nTotal samples: {len(texts)}")

# ----------------------------
# ADD TO CHROMA VECTOR DB
# ----------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = Chroma.from_texts(
    texts=texts,
    metadatas=metadatas,
    embedding=embeddings,
    persist_directory=CHROMA_PATH
)

vectorstore.persist()
