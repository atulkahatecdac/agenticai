# pip install sentence-transformers, sklearn, matplotlib
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# -----------------------------
# 1. Words
# -----------------------------
similar_words_1 = ["car", "automobile", "vehicle", "bike"]
similar_words_2 = ["shoes", "sandals", "socks", "footwear"]
dissimilar_words = ["banana", "democracy", "quantum", "bottle"]

words = similar_words_1 + similar_words_2 + dissimilar_words

# -----------------------------
# 2. Load Hugging Face model
# -----------------------------
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

embeddings = model.encode(words)
print(f"Embedding shape: {embeddings.shape}")

# -----------------------------
# 3. Cosine similarity
# -----------------------------
cos_sim = cosine_similarity(embeddings)

print("\n=== COSINE SIMILARITY ===\n")
for i, w1 in enumerate(words):
    for j, w2 in enumerate(words):
        print(f"{w1:12s} vs {w2:12s} = {cos_sim[i][j]:.3f}")
    print()

# -----------------------------
# 4. Euclidean distance
# -----------------------------
euc_dist = euclidean_distances(embeddings)

print("\n=== EUCLIDEAN DISTANCE ===\n")
for i, w1 in enumerate(words):
    for j, w2 in enumerate(words):
        print(f"{w1:12s} vs {w2:12s} = {euc_dist[i][j]:.3f}")
    print()

# -----------------------------
# 5. Reduce to 2D (visualization only)
# -----------------------------
pca = PCA(n_components=2)
vectors_2d = pca.fit_transform(embeddings)

# -----------------------------
# 6. Plot
# -----------------------------
plt.figure()
plt.scatter(vectors_2d[:, 0], vectors_2d[:, 1])

for i, word in enumerate(words):
    plt.text(
        vectors_2d[i, 0] + 0.01,
        vectors_2d[i, 1] + 0.01,
        word
    )

plt.title("Word Embeddings: PCA Projection\n(Cosine similarity ≈ angle, Euclidean distance ≈ spacing)")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.show()
