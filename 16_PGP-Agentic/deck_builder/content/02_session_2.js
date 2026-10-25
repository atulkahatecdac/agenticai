const S = "session_2/";

module.exports = {
  section: "Session 2 – LangChain Core",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 2  ·  Sat 25-Oct  ·  08:00–11:00 AM",
      title: "LangChain Core: Chains, Memory and RAG",
      subtitle: "Compose LLM apps from small parts, give them memory, and ground them in your own documents",
      goals: [
        { icon: "FaLink", title: "Compose chains with LCEL", text: "prompt | llm | parser, and the Runnables behind the pipe" },
        { icon: "FaMemory", title: "Add conversation memory", text: "buffer, summary and vector-store memory; persistence" },
        { icon: "FaDatabase", title: "Store and search embeddings", text: "ChromaDB and FAISS, similarity metrics, metadata filters" },
        { icon: "FaBook", title: "Build a RAG pipeline end to end", text: "load, split, embed, retrieve, generate – and a PDF Q&A bot" },
      ],
      agenda: [
        "LangChain overview and architecture",
        "LCEL and Runnables",
        "Prompt templates and output parsers",
        "Conversation memory (session and persistent)",
        "Embeddings and vector databases (Chroma, FAISS)",
        "Document loaders, text splitters and chunking",
        "Building a RAG pipeline with retrievers",
        "Hands-on: Q&A bot over PDFs",
      ],
    },

    // ---------------------------------------------------------------- LangChain + LCEL
    {
      title: "LangChain at a Glance",
      subtitle: "An open-source framework for building applications on top of LLMs",
      demo: S + "2_1_langchain_lcel.py",
      left: [
        { type: "icons", d: 0.38, items: [
          { icon: "FaComments", title: "Building blocks", text: "Models, prompts, output parsers, retrievers, tools – all interchangeable" },
          { icon: "FaRightLeft", title: "Provider-agnostic", text: "Swap OpenAI, Gemini or a local Ollama model without rewriting the app" },
          { icon: "FaLink", title: "LCEL", text: "Connect the blocks with `|`, then run any chain with `.invoke()`, `.batch()` or `.stream()`" },
        ] },
      ],
      right: [
        { type: "text", text: "**How LangChain evolved**", size: 12 },
        { type: "table", size: 10.5, widths: [1.3, 1.7, 1.3], head: ["Generation", "Architecture", "Status"], rows: [
          ["Early", "LLMChain", "Legacy"],
          ["Intermediate", "SequentialChain", "Legacy"],
          ["Modern", "LCEL (Runnables)", "**Recommended**"],
          ["Agentic", "LangGraph", "**Complex workflows**"],
        ] },
      ],
    },
    { kind: "image", src: "lcel_operators.png", alt: "LCEL operators and example", demo: S + "2_1_langchain_lcel.py, 2_2_langchain_lcel_ollama.py" },
    { kind: "image", src: "prompt_template_types.png", alt: "Three types of prompt templates in LangChain", demo: S + "2_3_prompt_templates.py" },
    { kind: "image", src: "output_parsers.png", alt: "LangChain output parsers", demo: S + "2_4_output_parsers.py" },

    // ---------------------------------------------------------------- memory
    {
      title: "Conversation Memory Types",
      subtitle: "Three ways to remember a customer-support chat – each trades detail for size",
      demo: S + "2_5_memory_types.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaListUl", title: "Buffer memory", tag: "Stores everything", lines: ["Sends every past turn, word for word, to the LLM every time", "**Simple**, but grows without limit"] },
          { icon: "FaCompress", title: "Summary memory", tag: "Stores a summary", lines: ["An LLM rewrites the chat into a running summary: \"Customer's blender arrived damaged; a replacement ships in 3 days.\"", "**Compact**, loses detail"] },
          { icon: "FaMagnifyingGlass", title: "Vector-store memory", tag: "Stores meaning", lines: ["Six turns about a laptop; \"My battery drains fast\" → retrieves the battery turn (turn 3) – the most **relevant**, not the most recent", "**Scales** to long histories"] },
        ] },
      ],
    },
    {
      title: "Persistent Memory",
      subtitle: "Session memory lives only while the app runs; persistent memory survives restarts",
      demo: S + "2_6_persistent_chatbot.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaGear", label: "System instruction", caption: "Who the assistant is" },
          { icon: "FaClockRotateLeft", label: "Previous conversation", caption: "Loaded from the database" },
          { icon: "FaComment", label: "Current question", caption: "This turn's input" },
          { icon: "FaMicrochip", label: "LLM", caption: "Answers with full context" },
          { icon: "FaDatabase", label: "Save the turn", caption: "Written back for next time" },
        ] },
        { type: "compare", size: 11, cols: [
          { title: "Session memory", color: "slate", items: ["Kept in RAM", "Lost when the program stops", "Fine for a single chat"] },
          { title: "Persistent memory", color: "teal", items: ["Kept in a database (e.g. SQLite)", "Survives restarts – multi-turn across days", "Needed for real assistants"] },
        ] },
      ],
    },

    // ---------------------------------------------------------------- RAG fundamentals
    { kind: "image", src: "why_rag_pgp.png", alt: "Why do we need RAG?", demo: S + "2_7_chroma_db_basic.py" },
    { kind: "image", src: "embeddings_pgp.png", alt: "Embeddings: turning text into vectors", demo: S + "2_7_chroma_db_basic.py, 2_8_rag_cosine_euclidean.py" },
    {
      title: "Measuring Similarity",
      subtitle: "Nearest-neighbour retrieval ranks stored vectors by how close they are to the query vector",
      demo: S + "2_8_rag_cosine_euclidean.py",
      blocks: [
        { type: "cards", size: 11, items: [
          { icon: "FaCompassDrafting", title: "Cosine similarity", lines: ["Angle between two vectors – ignores length", "**Larger is better** (1 = same direction)"] },
          { icon: "FaRulerHorizontal", title: "L2 (Euclidean) distance", lines: ["Straight-line distance between two points", "**Smaller is better** (0 = identical)"] },
          { icon: "FaArrowsLeftRight", title: "Dot product", lines: ["Alignment and magnitude together", "**Larger is better**; equals cosine for normalised vectors"] },
        ] },
        { type: "callout", eyebrow: "Retrieval in one line", text: "Embed the question, score it against every stored vector, keep the top-k closest – those chunks go to the LLM." },
      ],
    },
    { kind: "image", src: "chromadb_qa_vectors.png", alt: "How ChromaDB stores Q&A: questions as vectors, answers as text", demo: S + "2_9_chroma_db_adding_metadata.py" },
    {
      title: "ChromaDB: Meaning plus Metadata",
      subtitle: "A local, persistent vector database – documents, embeddings and metadata together",
      demo: S + "2_7_chroma_db_basic.py, 2_9_chroma_db_adding_metadata.py",
      left: [
        { type: "icons", d: 0.4, size: 11, items: [
          { icon: "FaFileLines", title: "Documents", text: "The text you store – here, FAQ questions" },
          { icon: "FaCubes", title: "Embeddings", text: "Created for you by Chroma's built-in model, or one you choose" },
          { icon: "FaTags", title: "Metadata", text: "Key–value tags on each item: category, priority, the answer text" },
        ] },
      ],
      right: [
        { type: "code", caption: "Search by meaning, filter by metadata", code:
`results = collection.query(
    query_texts=["delivery lag"],
    n_results=1,
    where={"category": "returns"},
)` },
        { type: "callout", eyebrow: "Order of work", text: "`where` narrows the candidates by metadata first; similarity then ranks what is left." },
      ],
    },
    {
      title: "Vector Databases Compared",
      subtitle: "Same idea – store vectors, find the nearest ones – different trade-offs",
      demo: S + "2_7_chroma_db_basic.py, 2_10_faiss_search.py",
      blocks: [
        { type: "table", size: 10, widths: [1.1, 1.4, 1.9, 2.0, 1.9], head: ["Database", "Type", "Best for", "Pros", "Cons"], rows: [
          ["ChromaDB", "Local / embedded", "Small–medium apps, notebooks", "Easy, local persistence, Python-first", "Not ideal at very large scale"],
          ["FAISS", "Library, not a DB", "Fast in-process search", "Very fast, offline, optimised", "No metadata store or server"],
          ["Pinecone", "Managed cloud", "Production, large scale", "Scalable, highly available, no infra", "Paid, cloud-only"],
          ["Qdrant", "Open source + cloud", "Production with filters", "Fast filtering, simple API", "Heavier to self-host"],
        ] },
      ],
    },
    { kind: "image", src: "chroma_vs_faiss.png", alt: "Chroma vs FAISS: documents with details vs vectors in a fast index", demo: S + "2_7_chroma_db_basic.py, 2_10_faiss_search.py" },
    {
      title: "FAISS: Search Without Comparing Everything",
      subtitle: "Facebook AI Similarity Search – Meta's library for fast similarity search over dense vectors",
      demo: S + "2_10_faiss_search.py",
      blocks: [
        { type: "text", text: "One million documents, and the user asks **\"What is machine learning?\"**" },
        { type: "compare", size: 11.5, cols: [
          { title: "Without FAISS – linear scan", color: "slate", items: ["Embed the query", "Compare with document 1, then 2, then 3 …", "… all the way to document 1,000,000", "Slow, and gets slower as data grows"] },
          { title: "With FAISS – an index", color: "teal", items: ["Embed the query", "Look it up in the FAISS index", "Get the top 5 results directly", "Saved to disk as a .index file (+ .pkl for the documents)"] },
        ] },
      ],
    },

    // ---------------------------------------------------------------- RAG pipeline
    {
      title: "The RAG Pipeline, End to End",
      subtitle: "Index once, then answer many questions",
      demo: S + "2_13_rag_pipeline.py",
      blocks: [
        { type: "text", text: "**Indexing** – done once, or when documents change", size: 11.5, color: "teal" },
        { type: "flow", gapBefore: 0.1, items: [
          { icon: "FaFilePdf", label: "Documents", caption: "PDF, Word, web, CSV, DB" },
          { icon: "FaFileImport", label: "Loader", caption: "→ Document objects" },
          { icon: "FaScissors", label: "Splitter", caption: "→ small chunks" },
          { icon: "FaCubes", label: "Embeddings", caption: "→ vectors" },
          { icon: "FaDatabase", label: "Vector DB", caption: "Chroma, FAISS, Pinecone" },
        ] },
        { type: "text", text: "**Answering** – for every user question", size: 11.5, color: "coral" },
        { type: "flow", gapBefore: 0.1, items: [
          { icon: "FaUser", label: "Question", caption: "From the user", color: "coral" },
          { icon: "FaCubes", label: "Embed it", caption: "Same embedding model", color: "coral" },
          { icon: "FaMagnifyingGlass", label: "Retriever", caption: "Top-k similar chunks", color: "coral" },
          { icon: "FaFileLines", label: "Prompt", caption: "Context + question", color: "coral" },
          { icon: "FaMicrochip", label: "LLM", caption: "Grounded answer", color: "coral" },
        ] },
      ],
    },
    {
      title: "Loading and Chunking Documents",
      subtitle: "Turn files into Document objects, then into chunks small enough to embed and retrieve",
      demo: S + "2_11_document_loaders.py, 2_12_text_splitters.py",
      split: [1, 1.4],
      left: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaFileImport", title: "Loaders", text: "One per format – PDF, CSV, web, Notion; a PDF loads as one Document per page" },
          { icon: "FaWindowMaximize", title: "Why chunk: context window", text: "Whole documents do not fit, and tokens cost money" },
          { icon: "FaBullseye", title: "Why chunk: better retrieval", text: "Small focused chunks match questions better" },
        ] },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.3, 2.6, 1.6], head: ["Strategy", "How it splits", "Best for"], rows: [
          ["Fixed-size", "Every N characters, with overlap so ideas are not cut in half", "Quick prototypes"],
          ["Recursive", "Paragraph → sentence → word until each chunk fits", "**General RAG (most common)**"],
          ["Semantic", "Where the topic changes, judged with embeddings", "High-quality RAG"],
        ] },
      ],
    },
    {
      title: "Retrievers",
      subtitle: "The bridge between the vector database and the LLM – only the relevant chunks reach the prompt",
      demo: S + "2_14_retrievers.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaMagnifyingGlass", title: "VectorStoreRetriever", tag: "The default", lines: ["Embeds the question and returns the most similar chunks", "**Fast**, but only as good as the question's wording"] },
          { icon: "FaShuffle", title: "MultiQueryRetriever", tag: "Rephrase", lines: ["An LLM writes several versions of the question, retrieves for each, merges the results", "**Catches** chunks a single wording misses"] },
          { icon: "FaCompress", title: "ContextualCompression", tag: "Trim", lines: ["Retrieves candidates, then an LLM keeps only the parts that answer the question", "**Less noise** in the prompt"] },
        ] },
        { type: "callout", eyebrow: "More in later sessions", text: "Self-query, parent-document and ensemble retrievers build on the same idea – they change how a question becomes the final chunks." },
      ],
    },
    {
      title: "Hands-on: Q&A Bot over PDFs",
      subtitle: "A LangServe app that answers questions about an insurance PDF",
      demo: S + "2_15_langchain_qand_a_bot_chroma.py, 2_16_langchain_qanda_bot_faiss.py",
      left: [
        { type: "steps", items: [
          { title: "Run the Chroma version", text: "`2_15_langchain_qand_a_bot_chroma.py`" },
          { title: "Open the playground", text: "`http://localhost:8000/ask/playground/`" },
          { title: "Ask about the policy", text: "Answers come only from the retrieved chunks" },
          { title: "Swap in FAISS", text: "`2_16_langchain_qanda_bot_faiss.py` – same app, different store" },
        ] },
      ],
      right: [
        { type: "compare", size: 11, cols: [
          { title: "Chroma", color: "navy", items: ["Manages a directory of files for us", "Persists automatically"] },
          { title: "FAISS", color: "teal", items: ["A single .index file + .pkl of documents", "`save_local` / `load_local`"] },
        ] },
      ],
    },

    {
      kind: "summary",
      title: "Session 2 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "2_1", title: "LCEL chains", text: "prompt | llm | parser, with OpenAI and with local Ollama models" },
        { tag: "2_5", title: "Memory", text: "Buffer, summary and vector-store memory; a persistent chatbot" },
        { tag: "2_7", title: "Vector stores", text: "ChromaDB search with metadata filters; FAISS indexes" },
        { tag: "2_13", title: "A RAG pipeline", text: "Load → split → embed → store → retrieve → generate" },
        { tag: "2_15", title: "PDF Q&A bot", text: "A LangServe app over an insurance document" },
      ],
      takeaways: [
        "In modern LangChain, everything is a Runnable joined with |",
        "Pick memory by what you can afford to send: all, a summary, or what is relevant",
        "Embeddings turn meaning into geometry; retrieval is nearest-neighbour search",
        "Chunking strategy often matters more than the choice of vector DB",
        "The retriever decides what the LLM gets to see",
      ],
      next: "Session 3: LangChain Agents and Tool Use",
    },
  ],
};
