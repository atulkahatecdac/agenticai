# =====================================================================
# STEP 1: Build the knowledge base (the "R" in RAG).
#
# The IT runbooks and policies in data/kb/ are plain Markdown files.
# We split them into chunks, embed each chunk with a LOCAL embedding
# model (nomic-embed-text via Ollama) and store them in Chroma.
#
# Every chunk keeps a "doc_id" (KB-101, POL-201 ...) so that answers can
# cite their source later.
#
# Run once (and again whenever you edit a document in data/kb/):
#   ollama pull nomic-embed-text
#   python 1_ingest_kb.py
# =====================================================================
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import KB_DIR, get_vectorstore

# 1. Load every Markdown file in data/kb/
docs = DirectoryLoader(KB_DIR, glob="*.md", loader_cls=TextLoader,
                       loader_kwargs={"encoding": "utf-8"}).load()

# 2. Chunk - split on Markdown headings first, so one chunk is (roughly) one section
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=100,
    separators=["\n## ", "\n\n", "\n", " "],
)
chunks = splitter.split_documents(docs)

# 3. Tag every chunk with its document id, taken from the file name: KB-101_vpn... -> KB-101
for chunk in chunks:
    file_name = chunk.metadata["source"].replace("\\", "/").split("/")[-1]
    chunk.metadata["doc_id"] = file_name.split("_")[0]

# 4. Embed and store (start from an empty collection so re-runs don't duplicate)
store = get_vectorstore()
store.reset_collection()
store.add_documents(chunks)
print(f"Stored {len(chunks)} chunks from {len(docs)} documents.\n")

# 5. Quick retrieval test - no LLM involved yet, just vector similarity
for question in ["VPN keeps dropping", "who approves AWS production access", "lost my phone"]:
    print(f"Q: {question}")
    for doc in store.similarity_search(question, k=2):
        print(f"   [{doc.metadata['doc_id']}] {doc.page_content[:90]!r}")
    print()
