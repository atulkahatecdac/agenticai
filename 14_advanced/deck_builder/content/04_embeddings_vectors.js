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
        "Similarity metrics and benchmarks",
        "Chunking strategies",
        "Two-stage retrieval and reranking",
        "Hybrid search: weighted average and RRF",
        "Visualising embeddings with UMAP",
      ],
    },
    { kind: "image", src: "why_rag.png", alt: "Why do we need RAG?", demo: "Concept" },
    { kind: "image", src: "what_happens_in_rag.png", alt: "What happens in RAG", demo: "Concept" },
    { kind: "image", src: "rag_retriever.png", alt: "How the retriever works", demo: "Concept" },
    { kind: "image", src: "embeddings.png", alt: "Embeddings: turning text into vectors", demo: "Concept" },
    { kind: "image", src: "vector_similarity.png", alt: "Vector similarity: finding meaningful matches", demo: "Concept" },
    {
      title: "Popular Embedding Models",
      subtitle: "More dimensions can capture more nuance – at the cost of storage and speed",
      demo: M + "faiss_search.py (all-MiniLM-L6-v2), faiss_search_ollama.py (nomic-embed-text)",
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
        { type: "callout", eyebrow: "Rule", text: "Embed documents and queries with the same model – vectors from different models can't be compared." },
      ],
    },

    // ---------------------------------------------------------------- ChromaDB
    { kind: "image", src: "chromadb_qa_vectors.png", alt: "How ChromaDB stores Q&A: questions as vectors, answers as text", demo: M + "chromadb_search.py" },
    { kind: "image", src: "chromadb_similarity_metrics.png", alt: "How ChromaDB uses similarity in search", demo: M + "chromadb_search.py" },
    {
      title: "ChromaDB: CRUD and Metadata Filters",
      subtitle: "A local, persistent vector database – documents, embeddings and metadata together",
      demo: M + "chromadb_crud.py, " + M + "chromadb_search.py",
      left: [
        { type: "code", caption: "Create", code:
`client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_or_create_collection("employees")
col.add(ids=["1", "2"],
        documents=["Alice works in Finance.",
                   "Bob works in HR."],
        metadatas=[{"department": "Finance"},
                   {"department": "HR"}])` },
        { type: "code", caption: "Read, update, delete", code:
`col.get(ids=["1"])["documents"]
col.update(ids=["1"],
    documents=["Alice is now the Finance Manager."])
col.delete(ids=["2"])` },
      ],
      right: [
        { type: "code", caption: "Search by meaning + filter by metadata", code:
`results = col.query(
    query_texts=["budget"],
    n_results=5,
    where={"department": "Finance"},
)` },
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaMagnifyingGlass", title: "query_texts", text: "Embedded automatically, then compared by similarity" },
          { icon: "FaFilter", title: "where", text: "Narrows results by metadata before ranking" },
        ] },
      ],
    },
    {
      title: "Vector Databases Compared",
      subtitle: "Same idea – store vectors, find the nearest ones – different trade-offs",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [1.1, 1.4, 1.9, 2.0, 1.9], head: ["Database", "Type", "Best for", "Pros", "Cons"], rows: [
          ["ChromaDB", "Local / embedded", "Small–medium apps, notebooks", "Easy, local persistence, Python-first", "Not ideal at very large scale"],
          ["FAISS", "Library, not a DB", "Fast in-process search", "Very fast, offline, optimised", "No metadata store or server"],
          ["Pinecone", "Managed cloud", "Production, large scale", "Scalable, highly available, no infra", "Paid, cloud-only"],
          ["Weaviate", "Open source + cloud", "Search with metadata", "Hybrid search, schema, GraphQL", "More setup"],
          ["Milvus", "Open source + cloud", "Heavy workloads", "Highly scalable, rich index options", "Needs infrastructure"],
          ["Qdrant", "Open source + cloud", "Production with filters", "Fast filtering, simple API", "Heavier to self-host"],
          ["Redis", "Add-on to Redis", "Apps already on Redis", "Fast, real-time", "Not specialised"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- FAISS
    { kind: "image", src: "chromadb_vs_faiss.png", alt: "ChromaDB vs FAISS – what's the difference?", demo: M + "faiss_search.py" },
    {
      title: "FAISS: Search Without Comparing Everything",
      subtitle: "Facebook AI Similarity Search – Meta's library for fast similarity search over dense vectors",
      demo: M + "faiss_search.py, " + M + "faiss_search_ollama.py",
      blocks: [
        { type: "text", text: "One million documents, and the user asks **\"What is machine learning?\"**" },
        { type: "compare", size: 11.5, cols: [
          { title: "Without FAISS – linear scan", color: "slate", items: ["Embed the query", "Compare with document 1, then 2, then 3 …", "… all the way to document 1,000,000", "Slow, and gets slower as data grows"] },
          { title: "With FAISS – an index", color: "teal", items: ["Embed the query", "Look it up in the FAISS index", "Get the top 5 results directly", "Pick the index type to trade accuracy for speed"] },
        ] },
      ],
    },
    { kind: "image", src: "faiss_index_types.png", alt: "FAISS index types compared: Flat, IVF, HNSW", demo: M + "faiss_search.py" },
    {
      title: "Choosing a FAISS Index",
      subtitle: "Different applications need different trade-offs between accuracy, speed and memory",
      demo: M + "faiss_search.py",
      blocks: [
        { type: "table", size: 10.5, widths: [1.7, 2.1, 2.1, 2.1], head: ["", "Flat L2", "IVF (inverted file)", "HNSW (graph)"], rows: [
          ["Search", "Exact", "Approximate", "Approximate"],
          ["Accuracy", "Best (100%)", "High", "Very high"],
          ["Speed", "Slow on big data", "Fast", "Very fast"],
          ["Memory", "High", "Medium", "High"],
          ["Training needed", "No", "Yes (clustering)", "No"],
          ["How it works", "Compares the query with every vector", "Finds the nearest cluster, searches inside it", "Hops through a graph of neighbouring vectors"],
          ["Best for", "Small datasets", "Large datasets", "Real-time applications"],
        ] },
      ],
    },
    { kind: "image", src: "embeddings_create_store_retrieve.png", alt: "How embeddings work: create, store, retrieve, look up", demo: M + "faiss_search.py" },
    {
      title: "Similarity Metrics",
      subtitle: "Nearest-neighbour retrieval ranks stored vectors by how close they are to the query vector",
      demo: "Concept",
      blocks: [
        { type: "cards", size: 11, codeSize: 10, items: [
          { icon: "FaCompassDrafting", title: "Cosine similarity", lines: ["The angle between two vectors – ignores their length", "**Larger is better** (1 = same direction)"], code: "A·B / (‖A‖ ‖B‖)" },
          { icon: "FaRulerHorizontal", title: "L2 (Euclidean) distance", lines: ["Straight-line distance between two points", "**Smaller is better** (0 = identical)"], code: "√ Σ (Aᵢ − Bᵢ)²" },
          { icon: "FaArrowsLeftRight", title: "Dot product", lines: ["Alignment and magnitude together", "**Larger is better**; equals cosine for normalised vectors"], code: "Σ Aᵢ · Bᵢ" },
        ] },
        { type: "table", size: 10.5, widths: [2.2, 2.0, 2.0], head: ["Vectors stored", "ChromaDB (typical)", "FAISS (typical)"], rows: [
          ["10K", "5–10 ms", "2–5 ms"],
          ["1 million", "100–500 ms", "20–80 ms"],
          ["10 million", "Seconds", "< 200 ms"],
        ] },
      ],
    },

    // ---------------------------------------------------------------- retrieval quality
    {
      title: "Chunking: Why and How",
      subtitle: "We cannot send whole documents to the LLM – and we should not want to",
      demo: "05_langchain/text_splitters.py",
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
      subtitle: "First cast a wide net, then put the best chunks first",
      demo: "Concept",
      split: [1, 1.1],
      left: [
        { type: "steps", size: 11, items: [
          { title: "Stage 1 – candidate generation", text: "Retrieve a generous set of chunks. Goal: high **recall** – don't miss anything useful" },
          { title: "Stage 2 – reranking", text: "Reorder them with a more accurate model. Goal: high **precision** – best first" },
        ] },
        { type: "chain", size: 10, items: ["Relevance reranking", "MMR (diversity)", "Custom rules"] },
      ],
      right: [
        { type: "text", text: "**\"How do I reset my Windows password?\"**", size: 11.5 },
        { type: "table", size: 10, widths: [2.2, 2.2], head: ["Vector search order", "After reranking"], rows: [
          ["Change Windows password", "**Reset forgotten Windows password**"],
          ["Reset forgotten Windows password", "Change Windows password"],
          ["Windows login troubleshooting", "Windows login troubleshooting"],
          ["Password manager", "Password manager"],
        ] },
        { type: "callout", eyebrow: "Key idea", text: "Vector search finds similar documents; reranking finds the most relevant ones." },
      ],
    },
    {
      title: "Hybrid Search",
      subtitle: "Keyword search and semantic search fail in different places – use both",
      demo: M + "hybrid_search.py",
      blocks: [
        { type: "compare", size: 11, cols: [
          { title: "Keyword search", color: "navy", items: ["Finds exact words", "Error codes, names, acronyms (\"ELSS\")"] },
          { title: "Semantic search", color: "teal", items: ["Finds meaning", "Paraphrases with no shared words"] },
          { title: "Hybrid = both", color: "coral", items: ["Best of both worlds", "Support, legal, medical, e-commerce"] },
        ] },
        { type: "callout", eyebrow: "Example", text: "\"My computer is slow and shows error 0x80070057\" – keyword search catches the exact error code; semantic search understands \"computer is slow\"." },
        { type: "cols", cols: [
          [{ type: "text", size: 11, text: "**Weighted average:** normalise both scores to 0–1, then `α·semantic + (1−α)·keyword` – simple and tunable." }],
          [{ type: "text", size: 11, text: "**Reciprocal Rank Fusion:** ignore raw scores; sum `1/(k + rank)` across both lists – rewards documents ranked high by both." }],
        ] },
      ],
    },
    { kind: "image", src: "hybrid_search_rrf_weighted.png", alt: "Hybrid search: two ways to combine results – RRF and weighted average", demo: M + "hybrid_search.py" },
    {
      title: "Inside hybrid_search.py",
      subtitle: "100 short documents (finance, sports, tech …) searched three ways, side by side",
      demo: M + "hybrid_search.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileCsv", label: "Load", caption: "documents.csv" },
          { icon: "FaFont", label: "Keyword", caption: "TF-IDF vectors, cosine score" },
          { icon: "FaBrain", label: "Semantic", caption: "Sentence-transformer embeddings" },
          { icon: "FaScaleBalanced", label: "Fuse", caption: "Weighted average and RRF", color: "coral" },
          { icon: "FaTableList", label: "Compare", caption: "Each method's ranking", color: "teal" },
        ] },
        { type: "tiles", cols: 3, items: [
          { icon: "FaEquals", title: "Balanced query", text: "Both signals agree" },
          { icon: "FaPersonCane", title: "\"Put money away for old age\"", text: "Zero word overlap – semantic wins" },
          { icon: "FaFont", title: "\"ELSS\"", text: "An acronym – keyword wins" },
        ] },
        { type: "text", size: 11, color: "slate", text: "Why not just add the raw scores? TF-IDF and embedding cosine live on different scales – one would dominate." },
      ],
    },
    {
      title: "Seeing Embeddings with UMAP",
      subtitle: "Project hundreds of dimensions down to 2D while keeping neighbours close – spot clusters, overlaps and outliers",
      demo: M + "umap_visualization.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFileLines", label: "Documents", caption: "\"I want to invest in mutual funds.\"" },
          { icon: "FaCubes", label: "Embedding model", caption: "384-dimensional vectors" },
          { icon: "FaCompress", label: "UMAP", caption: "Uniform Manifold Approximation and Projection", color: "coral" },
          { icon: "FaChartLine", label: "Scatter plot", caption: "2D points, one per document", color: "teal" },
        ] },
        { type: "callout", eyebrow: "Why it helps", text: "Humans can't picture 384 dimensions. A 2D map shows whether topics separate cleanly – a quick sanity check on your embeddings and chunks." },
      ],
    },
    {
      kind: "summary",
      title: "Module 04 Summary",
      subtitle: "What you built",
      built: [
        { tag: "chroma", title: "ChromaDB", text: "CRUD, similarity search and metadata filters" },
        { tag: "faiss", title: "FAISS", text: "An in-process index with local and Ollama embeddings" },
        { tag: "hybrid", title: "Hybrid search", text: "TF-IDF + embeddings fused by weights and by RRF" },
        { tag: "umap", title: "A map of meaning", text: "Document embeddings projected to 2D" },
      ],
      takeaways: [
        "Embeddings turn meaning into geometry",
        "Same embedding model for documents and queries",
        "Chroma manages data; FAISS is a fast index",
        "Recall first, then rerank for precision",
        "Hybrid search covers what either method misses",
      ],
      next: "Module 05: LangChain Core",
    },
  ],
};
