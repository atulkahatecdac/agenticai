# A 2D map of the help-desk FAQ (deck: "Seeing Embeddings with UMAP").
# Each of the 48 questions in faq.csv becomes a 384-number vector; UMAP squeezes
# them into 2D so you can SEE whether shipping, payments, returns ... questions
# form their own clusters - a quick sanity check on embeddings (and later, chunks).
# Numbers on the plot are the FAQ ids. No API key.
import os
import pandas as pd
import matplotlib.pyplot as plt

from sentence_transformers import SentenceTransformer
import umap.umap_ as umap

# -----------------------------
# Load data
# -----------------------------
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq.csv")
df = pd.read_csv(CSV_PATH)

# -----------------------------
# Create embeddings (questions only, as in every 04 script)
# -----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

embeddings = model.encode(
    df["question"].tolist(),
    show_progress_bar=True
)

print(embeddings.shape)

# -----------------------------
# UMAP
# -----------------------------

# Reduce dimensionality (defaults to 2D)
# n_neighbors: number of nearest neighbors to consider
# min_dist: minimum distance between clusters
reducer = umap.UMAP(
    n_neighbors=10,
    min_dist=0.15,
    metric="cosine",
    random_state=42
)

embedding_2d = reducer.fit_transform(embeddings)

# -----------------------------
# Plot
# -----------------------------

plt.figure(figsize=(14,10))

categories = df["category"].unique()

for category in categories:

    mask = df["category"] == category

    # scatter plot of each category
    plt.scatter(
        embedding_2d[mask,0], # x = UMAP dimension 1
        embedding_2d[mask,1], # y = UMAP dimension 2
        label=category,
        s=80 # marker size
    )

# Label each point

for i in range(len(df)):
    plt.text(
        embedding_2d[i,0],
        embedding_2d[i,1],
        str(df["id"][i]),
        fontsize=8
    )

plt.title("UMAP map of the help-desk FAQ (questions only)", fontsize=18)
plt.xlabel("UMAP Dimension 1")
plt.ylabel("UMAP Dimension 2")
plt.legend()
plt.grid(True)

plt.show()