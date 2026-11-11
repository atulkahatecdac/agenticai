const M = "04_rag/";

module.exports = {
  section: "Module 04 – Embeddings and Vector Databases",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 04",
      title: "Embeddings, Vector Databases and Semantic Search",
      subtitle: "Turn meaning into numbers, store them, and find the closest matches fast – the retrieval half of RAG",
      goals: [
        { icon: "FaBook", title: "Know why RAG needs retrieval", text: "and what happens between question and answer" },
        { icon: "FaCubes", title: "Work with embeddings", text: "models, dimensions and similarity metrics" },
        { icon: "FaDatabase", title: "Use ChromaDB and FAISS", text: "CRUD, metadata filters, index types, speed" },
        { icon: "FaShuffle", title: "Retrieve better", text: "chunking, reranking, hybrid search, UMAP views" },
      ],
      agenda: [
        "Why RAG, and how retrieval works",
        "Embeddings and embedding models",
        "ChromaDB: storage, similarity, CRUD and filters",
        "Vector databases compared; FAISS and its indexes",
        "Similarity metrics",
        "Chunking strategies",
        "Two-stage retrieval and reranking",
        "Hybrid search: weighted average and RRF",
        "Visualising embeddings with UMAP",
      ],
    },
    {
      title: "Why Do We Need RAG?",
      subtitle: "The LLM knows the general rules of insurance – your premiums live only in your own knowledge base",
      demo: "Concept",
      blocks: [
        { type: "callout", eyebrow: "Customer asks", text: "\"My 2018 hatchback had one claim last year. Can I renew with **comprehensive** motor cover, and what will the premium be?\"" },
        { type: "compare", size: 10.5, cols: [
          { title: "LLM alone", color: "slate", items: [
            "✓ Eligibility: knows general guidelines – valid RC and licence, vehicle age limits, a claim resets the no-claim bonus",
            "✗ Premium: has never seen **your** rate card, so it guesses"
          ] },
          { title: "Internal KB (retrieved)", color: "coral", items: [
            "Premium rate card by vehicle age, city and IDV",
            "Claim loading and no-claim-bonus table",
            "Underwriting rules and current offers",
          ] },
          { title: "LLM + RAG", color: "teal", items: [
            "LLM reasons on eligibility from general knowledge",
            "Retrieved rate-card chunks supply the actual numbers",
            "Grounded answer that cites its source",
          ] },
        ] },
        { type: "callout", style: "dark", text: "RAG = Retrieve the internal facts → Augment the prompt with them → Generate an answer that combines both" },
      ],
    },
    // ------------------------------------------- Embeddings -> ChromaDB, one e-commerce FAQ example
    // Numbers on these four slides are real: ChromaDB 1.1.1 defaults (all-MiniLM-L6-v2, HNSW, squared L2).
    {
      title: "What Is a Vector Embedding?",
      subtitle: "A list of numbers that captures what a sentence means – shown on an online shop's help-desk FAQ",
      demo: M + "04_1_chromadb_faq_store.py",
      blocks: [
        { type: "flow", d: 0.6, items: [
          { icon: "FaComment", label: "A customer question", caption: "\"When will my order arrive?\"" },
          { icon: "FaMicrochip", label: "Embedding model", caption: "all-MiniLM-L6-v2 – ChromaDB's default" },
          { icon: "FaListOl", label: "A vector", caption: "384 numbers: [-0.06, -0.04, 0.03, …]" },
        ] },
        { type: "table", size: 10.5, widths: [3.2, 2.6, 1.6], head: ["FAQ question", "Its vector (first 3 of 384)", "Topic"], rows: [
          ["When will my order arrive?", "[-0.06, -0.04, 0.03, …]", "shipping"],
          ["What payment methods do you accept?", "[0.02, 0.04, 0.02, …]", "payments"],
          ["How do I return a product?", "[-0.00, 0.00, 0.02, …]", "returns"],
        ] },
        { type: "callout", eyebrow: "The key idea", text: "Similar meaning → nearby vectors. \"Where is my parcel?\" shares almost no words with \"When will my order arrive?\" – but their vectors sit close together." },
      ],
    },
    {
      title: "Storing the FAQ in ChromaDB",
      subtitle: "Each record keeps the question, its vector and the answer – only the question is embedded",
      demo: M + "04_1_chromadb_faq_store.py",
      blocks: [
        { type: "table", size: 10, widths: [0.5, 2.6, 1.9, 3.6], head: ["id", "document (embedded)", "embedding", "metadata (stored as is)"], rows: [
          ["1", "When will my order arrive?", "[-0.06, -0.04, …]", "answer: \"Orders arrive in 3–5 business days…\"  ·  category: shipping"],
          ["2", "What payment methods do you accept?", "[0.02, 0.04, …]", "answer: \"Cards, UPI, net banking, cash on delivery\"  ·  category: payments"],
          ["3", "How do I return a product?", "[-0.00, 0.00, …]", "answer: \"Start a return within 7 days of delivery\"  ·  category: returns"],
        ] },
        { type: "cols", ratio: [1.35, 1], cols: [
          [
            { type: "code", code:
`faq = client.create_collection("faq")
faq.add(
    ids=["1", "2", "3"],
    documents=["When will my order arrive?", ...],
    metadatas=[{"answer": "Orders arrive in 3-5 ...",
                "category": "shipping"}, ...],
)` },
          ],
          [
            { type: "icons", d: 0.34, size: 10.5, titleSize: 12, items: [
              { icon: "FaWandMagicSparkles", title: "Embedding is automatic", text: "Chroma runs its default model on every document you add" },
              { icon: "FaDiagramProject", title: "Indexed as you add", text: "Each vector joins an HNSW search graph" },
            ] },
          ],
        ] },
      ],
    },
    {
      title: "When a Customer Asks a Question",
      subtitle: "The question goes through the same model; Chroma returns the closest stored question – and its answer",
      demo: M + "04_2_chromadb_faq_query.py",
      blocks: [
        { type: "callout", eyebrow: "Customer types", text: "\"My parcel hasn't come yet – where is it?\"" },
        { type: "flow", d: 0.6, items: [
          { icon: "FaMicrochip", label: "1. Embed the question", caption: "Same model → 384 numbers" },
          { icon: "FaMagnifyingGlass", label: "2. Search the collection", caption: "Find the nearest stored question vectors" },
          { icon: "FaBullseye", label: "3. Best match", caption: "\"When will my order arrive?\"" },
          { icon: "FaReply", label: "4. Reply", caption: "Its answer from metadata – or hand it to an LLM to phrase the reply" },
        ] },
        { type: "code", code:
`hits = faq.query(query_texts=["My parcel hasn't come yet - where is it?"],
                 n_results=1)
hits["metadatas"][0][0]["answer"]    # 'Orders arrive in 3-5 business days. ...'` },
      ],
    },
    {
      title: "How ChromaDB Finds the Best Match",
      subtitle: "An HNSW index: hop through a graph of neighbours instead of comparing the query with every stored vector",
      demo: M + "04_2_chromadb_faq_query.py",
      split: [1.1, 1],
      left: [
        { type: "steps", size: 10.5, gap: 0.1, items: [
          { title: "Link each vector to its neighbours", text: "Done while adding: up to 16 links each, in a few layers – a sparse top layer, every vector at the bottom" },
          { title: "Start at the top layer", text: "Hop to whichever neighbour is closer to the query" },
          { title: "Drop a layer and repeat", text: "Long jumps first, then short, careful steps" },
          { title: "Return the closest", text: "Ranked by distance; the top n_results come back" },
        ] },
      ],
      right: [
        { type: "table", size: 10.5, widths: [3.2, 1.2], firstBold: false, head: ["Stored question", "Distance"], rows: [
          ["**When will my order arrive?**", "**1.07**"],
          ["Can I change my delivery address?", "1.25"],
          ["How do I return a product?", "1.34"],
          ["What payment methods do you accept?", "1.92"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Query: \"My parcel hasn't come yet – where is it?\" Default metric: squared L2 distance – **lower = closer**." },
        { type: "callout", eyebrow: "Approximate, by design", text: "HNSW skips most vectors, so it stays fast at millions of records – and almost always finds the true best match." },
      ],
    },
    {
      title: "Popular Embedding Models",
      subtitle: "More dimensions can capture more nuance – at the cost of storage and speed",
      demo: M + "04_3_chromadb_ollama_embeddings.py – MiniLM (384) vs nomic-embed-text (768)",
      blocks: [
        { type: "table", size: 10.5, widths: [2.2, 2.0, 3.4, 1.1], head: ["Model", "Provider", "Key features", "Dimensions"], rows: [
          ["text-embedding-3-small", "OpenAI", "Fast and cost-effective; search and clustering", "1536"],
          ["text-embedding-3-large", "OpenAI", "Highest quality semantic understanding", "3072"],
          ["all-MiniLM-L6-v2", "Hugging Face", "Very fast and small; good for local use", "384"],
          ["all-mpnet-base-v2", "Hugging Face", "Good balance of speed and accuracy", "768"],
          ["bge-base-en-v1.5", "Hugging Face (BAAI)", "Strong general-purpose retrieval", "768"],
          ["e5-base-v2", "Hugging Face (Microsoft)", "Strong for retrieval and Q&A", "768"],
          ["nomic-embed-text", "Nomic (via Ollama)", "Runs locally with Ollama", "768"],
        ] },
        { type: "callout", eyebrow: "Rule", text: "Embed documents and queries with the same model – vectors from different models can't be compared. 04_3 shows the error you get." },
      ],
    },
    {
      title: "ChromaDB: CRUD and Metadata Filters",
      subtitle: "The full help-desk FAQ – 48 questions from faq.csv, answers and categories as metadata",
      demo: M + "04_4_chromadb_crud.py",
      left: [
        { type: "code", caption: "Create", code:
`faq = client.create_collection("faq_all")
faq.add(ids=ids,              # 48 rows of faq.csv
        documents=questions,  # embedded
        metadatas=metas)      # answer, category` },
        { type: "code", caption: "Read, update, delete", code:
`faq.get(ids=["9"])
faq.get(where={"category": "payments"})
faq.get(where_document={"$contains": "OTP"})
faq.update(ids=["9"], metadatas=[new_meta])
faq.delete(ids=["47"])` },
      ],
      right: [
        { type: "code", caption: "Search by meaning + filter by metadata", code:
`faq.query(query_texts=["How long does it take?"],
          n_results=3,
          where={"category": "returns"})` },
        { type: "table", size: 10.5, widths: [2.0, 2.6], firstBold: false, head: ["\"How long does it take?\"", "Best match"], rows: [
          ["No filter", "When will my order arrive?"],
          ["where category = returns", "**When will I get my refund?**"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "A help widget on the Returns page already knows the context – the filter settles the ambiguity before ranking." },
      ],
    },
    {
      title: "Vector Databases Compared",
      subtitle: "Same job – store vectors, find the nearest ones fast – packaged in different ways",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.2, 1.7, 2.6, 2.6], head: ["Store", "What it is", "Strengths", "Watch out for"], rows: [
          ["ChromaDB", "Local / embedded DB", "Easiest start; documents + metadata + vectors together", "One index type (HNSW); one machine"],
          ["FAISS", "Search library", "Many index types, compression, GPU; billions of vectors", "Vectors only – you store the text and metadata"],
          ["Qdrant", "Open source + cloud", "Fast metadata filtering, simple API", "A server to run in production"],
          ["Weaviate", "Open source + cloud", "Built-in hybrid (keyword + vector) search", "More setup"],
          ["Milvus", "Open source + cloud", "Very large scale, many index types", "Needs real infrastructure"],
          ["Pinecone", "Managed cloud", "No infrastructure; scales on demand", "Paid, cloud only"],
        ] },
        { type: "callout", eyebrow: "Common ground", text: "All of them search an index (most often HNSW) – none compares the query with every stored vector unless you ask for exact search." },
      ],
    },
    {
      title: "ChromaDB or FAISS?",
      subtitle: "Both find nearest neighbours through an index – one is a database, the other a search engine you build around",
      demo: M + "04_5_faiss_search.py",
      split: [1, 1.1],
      left: [
        { type: "compare", size: 10.5, cols: [
          { title: "ChromaDB", color: "teal", items: [
            "A database: stores documents, metadata and vectors",
            "Embeds text for you; add, update, delete, where filters",
            "One built-in index: HNSW",
            "Returns documents and metadata",
          ] },
          { title: "FAISS", color: "navy", items: [
            "A library: stores vectors only",
            "Many indexes: exact Flat, IVF, HNSW, compressed PQ",
            "GPU support; billions of vectors",
            "Returns row numbers – you look up the text",
          ] },
        ] },
      ],
      right: [
        { type: "code", caption: "04_5_faiss_search.py (condensed)", code:
`embeddings = model.encode(questions)   # you embed
index = faiss.IndexFlatL2(384)         # exact search
index.add(embeddings)

distances, rows = index.search(model.encode([query]), 3)
for r in rows[0]:
    print(FAQ[r]["answer"])            # you look it up` },
        { type: "callout", eyebrow: "Rule of thumb", text: "Start with ChromaDB. Reach for FAISS when you need exact search, a GPU, or more vectors than fit in memory." },
      ],
    },
    {
      title: "Choosing a FAISS Index",
      subtitle: "Trade accuracy for speed and memory – ChromaDB makes this choice for you: HNSW",
      demo: M + "04_5_faiss_search.py",
      blocks: [
        { type: "table", size: 10.5, widths: [1.5, 3.0, 1.3, 1.3, 2.1], head: ["Index", "How it searches", "Results", "Memory", "Use when"], rows: [
          ["Flat", "Compares the query with every vector", "Exact", "Full vectors", "Up to ~100K vectors, or exact answers matter"],
          ["IVF", "Clusters vectors first (needs training); searches only the nearest clusters", "Approximate", "Full vectors", "Millions of vectors"],
          ["IVF + PQ", "IVF plus compressing each vector to a few bytes", "Approximate", "Very small", "More vectors than fit in RAM"],
          ["HNSW", "Hops through a graph of neighbours – the same index ChromaDB uses", "Approximate", "Full vectors + links", "Fast, high-recall search; no training"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "04_5 builds `IndexFlatL2` and `IndexHNSWFlat(384, 32)` over the FAQ: the same top 3 for every query, and the same distances ChromaDB reported." },
      ],
    },
    {
      title: "Similarity Metrics",
      subtitle: "Nearest-neighbour retrieval ranks stored vectors by how close they are to the query vector",
      demo: M + "04_6_similarity_metrics.py",
      blocks: [
        { type: "cards", size: 11, codeSize: 10, items: [
          { icon: "FaCompassDrafting", title: "Cosine similarity", lines: ["The angle between two vectors – ignores their length", "**Larger is better** (1 = same direction)"], code: "A·B / (‖A‖ ‖B‖)" },
          { icon: "FaRulerHorizontal", title: "L2 (Euclidean) distance", lines: ["Straight-line distance between two points", "**Smaller is better** (0 = identical)"], code: "√ Σ (Aᵢ − Bᵢ)²" },
          { icon: "FaArrowsLeftRight", title: "Dot product", lines: ["Alignment and magnitude together", "**Larger is better**; equals cosine for normalised vectors"], code: "Σ Aᵢ · Bᵢ" },
        ] },
        { type: "callout", eyebrow: "On the FAQ", text: "MiniLM vectors have length 1, so dot = cosine and squared L2 = 2 − 2·cosine – all three rank the same. That is ChromaDB's 1.07: 2 − 2 × 0.47. Make one vector 3× longer and only the dot product changes its answer." },
      ],
    },

    // ---------------------------------------------------------------- retrieval quality
    {
      title: "Chunking: Why and How",
      subtitle: "We cannot send whole documents to the LLM – and we should not want to",
      demo: "05_langchain/05_6_text_splitters.py",
      split: [1, 1.5],
      left: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaWindowMaximize", title: "Limited context window", text: "Even large windows fill up fast" },
          { icon: "FaBolt", title: "Faster, cheaper responses", text: "Fewer tokens per call" },
          { icon: "FaCubes", title: "Embedding limits", text: "Embedding models take less text than LLMs" },
          { icon: "FaBullseye", title: "Better retrieval", text: "Small focused chunks match questions better" },
        ] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.3, 2.5, 1.7], head: ["Strategy", "How it splits", "Best for"], rows: [
          ["Fixed-size", "Every N characters or tokens; add overlap to avoid cutting ideas", "Quick prototypes"],
          ["Sentence / paragraph", "At natural boundaries", "Articles, reports"],
          ["Recursive", "Paragraph → sentence → clause until it fits", "**General RAG (most common)**"],
          ["Document structure", "By headings and sections (#, ##)", "Manuals, Markdown"],
          ["Semantic", "Where the meaning or topic changes", "High-quality enterprise RAG"],
        ] },
      ],
    },
    {
      title: "Two-Stage Retrieval",
      subtitle: "First cast a wide net, then put the best matches first",
      demo: M + "04_7_reranking.py",
      split: [1, 1.1],
      left: [
        { type: "steps", size: 11, items: [
          { title: "Stage 1 – vector search", text: "ChromaDB returns 10 candidates. Goal: high **recall** – don't miss anything useful" },
          { title: "Stage 2 – reranking", text: "A cross-encoder reads the question with each candidate's question and answer. Goal: high **precision** – best first" },
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Reranker: mxbai-rerank-xsmall-v1, local, ~150 MB." },
      ],
      right: [
        { type: "text", text: "**\"I want my money back\"**", size: 11.5 },
        { type: "table", size: 10, widths: [2.3, 2.3], firstBold: false, head: ["Vector search order", "After reranking"], rows: [
          ["My payment failed but money was deducted", "**When will I get my refund?**"],
          ["When will I get my refund?", "My payment failed but money was deducted"],
          ["Can I return an item I bought on sale?", "How is a COD refund paid?"],
        ] },
        { type: "callout", eyebrow: "Test it on your data", text: "For \"I bought shoes in the wrong size\" the same reranker demotes the right answer – check before you switch one on." },
      ],
    },
    {
      title: "Hybrid Search",
      subtitle: "Keyword search and semantic search fail in different places – use both",
      demo: M + "04_8_hybrid_search.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Keyword search", color: "navy", items: ["Finds exact words", "Codes and acronyms (\"NEFT\", \"GSTIN\")"] },
          { title: "Semantic search", color: "teal", items: ["Finds meaning", "Paraphrases with no shared words"] },
          { title: "Hybrid = both", color: "coral", items: ["Best of both worlds", "Support, legal, medical, e-commerce"] },
        ] },
        { type: "callout", eyebrow: "Example", text: "\"Refund by NEFT for my COD order?\" – keyword search catches the exact terms NEFT and COD; semantic search understands \"refund\"." },
        { type: "cols", cols: [
          [{ type: "text", size: 11, text: "**Weighted average:** normalise both scores to 0–1, then `α·semantic + (1−α)·keyword` – simple and tunable." }],
          [{ type: "text", size: 11, text: "**Reciprocal Rank Fusion:** ignore raw scores; sum `1/(k + rank)` over each method's top results – rewards entries ranked high by both." }],
        ] },
      ],
    },
    {
      title: "Inside 04_8_hybrid_search.py",
      subtitle: "The 48 help-desk FAQs searched four ways – top answer for three customer questions",
      demo: M + "04_8_hybrid_search.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileCsv", label: "Load", caption: "faq.csv" },
          { icon: "FaFont", label: "Keyword", caption: "TF-IDF over question + answer" },
          { icon: "FaBrain", label: "Semantic", caption: "Embeddings of the questions" },
          { icon: "FaScaleBalanced", label: "Fuse", caption: "Weighted average and RRF", color: "coral" },
        ] },
        { type: "table", size: 10, widths: [2.2, 2.0, 2.0, 1.9, 1.9], firstBold: false, head: ["Customer types", "Keyword only", "Semantic only", "50 / 50", "RRF"], rows: [
          ["\"How do I cancel my order?\"", "✓ Cancel my order", "✓ Cancel my order", "✓", "✓"],
          ["\"can I get a bill for my company\"", "✗ Return shipping", "✓ GST invoice", "✓", "✓"],
          ["\"NEFT\"", "✓ COD refund", "✗ Card declined", "✓", "tie"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "RRF sees only ranks: for NEFT each method's #1 is missing from the other's top 10, so it ties. The weighted average uses how strong each match is." },
      ],
    },
    {
      title: "Seeing Embeddings with UMAP",
      subtitle: "Project hundreds of dimensions down to 2D while keeping neighbours close – spot clusters, overlaps and outliers",
      demo: M + "04_9_umap_visualization.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileLines", label: "48 FAQ questions", caption: "\"How do I return a product?\"" },
          { icon: "FaCubes", label: "Embedding model", caption: "384-dimensional vectors" },
          { icon: "FaCompress", label: "UMAP", caption: "Uniform Manifold Approximation and Projection", color: "coral" },
          { icon: "FaChartLine", label: "Scatter plot", caption: "One point per question, coloured by category", color: "teal" },
        ] },
        { type: "callout", eyebrow: "Why it helps", text: "Humans can't picture 384 dimensions. On the FAQ map, payments, account and warranty questions form their own islands while some shipping and returns questions overlap – a quick sanity check before you trust retrieval." },
      ],
    },
    {
      kind: "summary",
      title: "Module 04 Summary",
      subtitle: "What you built",
      built: [
        { tag: "chroma", title: "A help-desk FAQ in ChromaDB", text: "Store, query, CRUD and metadata filters" },
        { tag: "faiss", title: "The same FAQ in FAISS", text: "Exact and HNSW indexes, same distances" },
        { tag: "rerank", title: "Two-stage retrieval", text: "A local cross-encoder reorders the top 10" },
        { tag: "hybrid", title: "Hybrid search", text: "TF-IDF + embeddings fused by weights and by RRF" },
        { tag: "umap", title: "A map of the FAQ", text: "Question embeddings projected to 2D" },
      ],
      takeaways: [
        "Embeddings turn meaning into geometry",
        "Same embedding model for documents and queries",
        "ChromaDB is a database; FAISS is a toolkit of indexes",
        "Recall first, then rerank for precision",
        "Hybrid search covers what either method misses",
      ],
      next: "Module 05: LangChain Core",
    },
  ],
};
