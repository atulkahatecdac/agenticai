import warnings
warnings.filterwarnings("ignore")

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

sys.stdout.reconfigure(encoding="utf-8")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# Embedding drift: are users asking different things than the RAG
# system was built for?
#
# A RAG help desk was built and tested on last month's questions. This
# week a new product launches (an EV wall charger) and customers start
# asking about it - the knowledge base has nothing on it. Nothing errors
# and latency is fine, so ordinary dashboards stay green. Only the
# MEANING of the traffic has moved.
#
# Three checks, from cheapest to most specific:
#   1. Centroid distance  - how far the average query vector has moved
#                           (the headline drift number Arize/Phoenix used)
#   2. KB coverage        - share of queries whose best KB match is weak
#   3. New clusters       - group this week's queries; a cluster with no
#                           close KB entry is a topic nobody planned for
#
# Arize Phoenix used to draw this as a UI ("Inferences"); current Phoenix
# (v21) dropped that feature and is now about tracing and evals - see
# 17_6. The maths is small enough to own, as below. No LLM, no API key.
# =====================================================================

with open(os.path.join(BASE_DIR, "..", "04_rag", "faq.csv"), encoding="utf-8") as f:
    FAQ = list(csv.DictReader(f))
kb_questions = [row["question"] for row in FAQ]

# Reference window: last month's real traffic - rewordings of FAQ topics.
reference = [
    "where is my parcel", "how many days for delivery", "can I pay with UPI", "is cash on delivery available",
    "how do I return shoes that don't fit", "when will I get my refund", "my order shows delivered but I didn't get it",
    "how to cancel my order", "change delivery address after ordering", "I forgot my password",
    "how to update my phone number", "is my phone under warranty", "does the warranty cover a cracked screen",
    "any discount coupons today", "how do I apply a promo code", "payment failed but money was deducted",
    "can I exchange for a different size", "do you deliver on Sundays", "how to track my shipment",
    "delete my account", "EMI options on credit card", "return pickup did not come",
]
# This week: the same mix, plus a burst of questions about a product the KB does not cover.
current = reference[:14] + [
    "how do I install the EV wall charger at home", "EV charger keeps tripping my MCB",
    "which car models work with your EV charger", "can the EV charger run on a 15 amp socket",
    "EV charger app won't pair over wifi", "is installation of the EV charger free",
    "what does the red light on the EV charger mean", "EV charger warranty for outdoor use",
]

model = SentenceTransformer("all-MiniLM-L6-v2")
embed = lambda texts: model.encode(texts, normalize_embeddings=True)
kb_vecs, ref_vecs, cur_vecs = embed(kb_questions), embed(reference), embed(current)

# ---------------------------------------------------------------------
# 1. Centroid distance, compared with normal week-to-week noise
# ---------------------------------------------------------------------
def centroid_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a.mean(axis=0) - b.mean(axis=0)))

# What does "no change" look like? Resample last month's queries at this
# week's size (a bootstrap) and see how far the centroid wanders by chance.
rng = np.random.default_rng(0)
noise = [centroid_distance(ref_vecs, ref_vecs[rng.integers(0, len(ref_vecs), len(cur_vecs))])
         for _ in range(500)]
baseline = float(np.percentile(noise, 95))
drift = centroid_distance(ref_vecs, cur_vecs)
print("1. CENTROID DISTANCE")
print(f"   chance variation (95th percentile, bootstrap): {baseline:.3f}")
print(f"   last month -> this week: {drift:.3f}  ->  {'DRIFT' if drift > baseline else 'no drift'}")
print(f"   ({len(current) - 14} of {len(current)} queries are new - an average can hide a shift in a minority,")
print("    which is why checks 2 and 3 look at individual queries)\n")

# ---------------------------------------------------------------------
# 2. KB coverage: best cosine similarity of each query to any KB question
# ---------------------------------------------------------------------
THRESHOLD = 0.5
best_ref = (ref_vecs @ kb_vecs.T).max(axis=1)
best_cur = (cur_vecs @ kb_vecs.T).max(axis=1)
print("2. KB COVERAGE (best match to the knowledge base below", THRESHOLD, "= poorly covered)")
print(f"   last month: {np.mean(best_ref < THRESHOLD):.0%} of queries poorly covered")
print(f"   this week : {np.mean(best_cur < THRESHOLD):.0%} of queries poorly covered\n")

# ---------------------------------------------------------------------
# 3. Cluster this week's queries; flag clusters the KB doesn't cover
# ---------------------------------------------------------------------
k = 4
labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(cur_vecs)
print("3. THIS WEEK'S TOPICS")
for c in range(k):
    members = [i for i in range(len(current)) if labels[i] == c]
    coverage = float(best_cur[members].mean())
    flag = "  <-- NEW: not covered by the KB" if coverage < THRESHOLD else ""
    print(f"   cluster {c}: {len(members):2} queries, KB match {coverage:.2f}{flag}")
    for i in members[:3]:
        print(f"      - {current[i]}")

# ---------------------------------------------------------------------
# A picture for the slide: 2-D projection (PCA via SVD, no extra deps)
# ---------------------------------------------------------------------
everything = np.vstack([kb_vecs, ref_vecs, cur_vecs])
centred = everything - everything.mean(axis=0)
_, _, vt = np.linalg.svd(centred, full_matrices=False)
xy = centred @ vt[:2].T
n_kb, n_ref = len(kb_vecs), len(ref_vecs)
plt.figure(figsize=(7, 4.5))
plt.scatter(*xy[:n_kb].T, s=18, c="#B8C2CC", label="knowledge base")
plt.scatter(*xy[n_kb:n_kb + n_ref].T, s=28, c="#1A7F8E", label="last month's queries")
plt.scatter(*xy[n_kb + n_ref:].T, s=28, c="#EA4B71", marker="^", label="this week's queries")
plt.legend(frameon=False)
plt.title("Query embeddings - the new cluster has no knowledge-base points near it")
plt.xticks([]), plt.yticks([])
out = os.path.join(BASE_DIR, "embedding_drift.png")
plt.tight_layout()
plt.savefig(out, dpi=130)
print(f"\nPlot saved: {out}")
print("Action: add EV-charger articles to the KB (or route those questions to a human) before answers degrade.")
