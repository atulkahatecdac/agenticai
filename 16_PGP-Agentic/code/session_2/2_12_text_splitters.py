import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

# Three genuinely unrelated topics, stitched into one block of text - this
# makes it easy to see WHERE each splitter decides to cut.
topic_1 = (
    "Photosynthesis is the process by which plants convert sunlight into chemical "
    "energy. Chlorophyll in the leaves absorbs light, mainly in the blue and red "
    "wavelengths. This process produces glucose and releases oxygen as a byproduct."
)
topic_2 = (
    "The stock market had a volatile session today as investors reacted to new "
    "inflation data. Tech stocks led the decline, with several major companies "
    "losing more than five percent. Analysts now expect the central bank to raise "
    "interest rates next month."
)
topic_3 = (
    "To make a simple pasta dish, first boil water and add a generous amount of "
    "salt. Cook the pasta until it is al dente, usually around nine minutes. Toss "
    "it with olive oil, garlic, and fresh basil before serving."
)
full_text = f"{topic_1} {topic_2} {topic_3}"

def show(label: str, chunks) -> None:
    print(f"\n{'=' * 70}")
    print(f"{label} - {len(chunks)} chunk(s)")
    print("=" * 70)
    for i, chunk in enumerate(chunks, start=1):
        text = chunk if isinstance(chunk, str) else chunk.page_content
        print(f"\n--- Chunk {i} ({len(text)} chars) ---")
        print(text)

# -----------------------------
# 1. RecursiveCharacterTextSplitter
# Splits purely on SIZE: tries to cut on paragraph breaks first, then
# sentences, then words, then characters - falling back down that list of
# separators only when a chunk is still too big. It has no idea what the
# text is ABOUT, so with a small enough chunk_size it will happily cut a
# chunk in half mid-topic, as long as it's under the character limit.
# -----------------------------
recursive_splitter = RecursiveCharacterTextSplitter(chunk_size=150, chunk_overlap=20)
recursive_chunks = recursive_splitter.split_text(full_text)
show("1. RecursiveCharacterTextSplitter (chunk_size=150)", recursive_chunks)

# -----------------------------
# 2. SemanticChunker
# Embeds each sentence, then looks at how much the embedding changes from
# one sentence to the next. A big jump = a topic boundary ("breakpoint"),
# and that's where it cuts - regardless of resulting chunk size. This is
# why, on the text above, it should produce exactly 3 chunks lining up
# with the 3 topics, instead of cutting mid-sentence like the splitter above.
# -----------------------------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
semantic_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="standard_deviation",
    breakpoint_threshold_amount=0.7,
)
semantic_chunks = semantic_splitter.create_documents([full_text])
show("2. SemanticChunker (breakpoint_threshold_type='standard_deviation')", semantic_chunks)
