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
          { icon: "FaBoxOpen", title: "Core packages", text: "langchain, langchain-core, langchain-community, plus one per provider (langchain-openai, langchain-ollama, …)" },
          { icon: "FaComments", title: "Building blocks", text: "Models, prompts, output parsers, retrievers, tools – all interchangeable" },
          { icon: "FaLink", title: "LCEL", text: "Connect the blocks with the pipe operator: `prompt | llm | parser`" },
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
    {
      title: "LCEL: Everything Is a Runnable",
      subtitle: "LangChain Expression Language – a declarative way to compose AI applications",
      demo: S + "2_1_langchain_lcel.py, 2_2_langchain_lcel_ollama.py",
      left: [
        { type: "text", text: "Instead of creating many chain objects, we connect **Runnables** with the pipe operator `|`. The output of one becomes the input of the next." },
        { type: "chain", items: ["Prompt", "LLM", "Parser", "Retriever", "Lambda", "…"] },
        { type: "callout", eyebrow: "Every Runnable has", text: "`.invoke()` for one input, `.batch()` for many, `.stream()` for token-by-token output." },
      ],
      right: [
        { type: "code", caption: "Prompt | LLM with a local model (Ollama)", code:
`from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in simple terms.")
llm = ChatOllama(model="llama3.2")

chain = prompt | llm
response = chain.invoke({"topic": "embeddings"})
print(response.content)` },
      ],
    },
    { kind: "image", src: "lcel_operators.png", alt: "LCEL operators and example", demo: S + "2_1_langchain_lcel.py" },
    {
      title: "Three Runnables You Will Use Often",
      subtitle: "Small building blocks that make chains flexible",
      demo: S + "2_1_langchain_lcel.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { icon: "FaCode", title: "RunnableLambda", lines: ["Wraps any Python function so it can sit in a chain – cleaning, formatting, extracting values"],
            code: `add = RunnableLambda(
    lambda t: t + "!")
add.invoke("Hello")  # Hello!` },
          { icon: "FaCodeBranch", title: "RunnableParallel", lines: ["Runs several Runnables on the same input at once and returns a dict of their results"],
            code: `RunnableParallel(
  upper=up, lower=low
).invoke("Hi")
# {'upper': 'HI', ...}` },
          { icon: "FaArrowRight", title: "RunnablePassthrough", lines: ["Passes the input through unchanged – keep the original while other branches transform it"],
            code: `{"q": RunnablePassthrough(),
 "ctx": retriever}
| prompt | llm` },
        ] },
      ],
    },
    { kind: "image", src: "prompt_template_types.png", alt: "Three types of prompt templates in LangChain", demo: S + "2_5_prompt_templates.py, 2_6_prompt_templates_openai.py" },
    { kind: "image", src: "output_parsers.png", alt: "LangChain output parsers", demo: S + "2_3_output_parsers.py, 2_4_output_parsers_openai.py" },

    // ---------------------------------------------------------------- memory
    {
      title: "Conversation Memory Types",
      subtitle: "Six turns: a laptop purchase, returns, a dead battery, delivery, a replacement, support",
      demo: S + "2_7_memory_types.py",
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaListUl", title: "Buffer memory", tag: "Stores everything", lines: ["Sends the entire conversation – all six turns – to the LLM every time", "**Simple**, but grows without limit"] },
          { icon: "FaCompress", title: "Summary memory", tag: "Stores a summary", lines: ["\"Customer bought a laptop with a battery problem, asked about returns and delivery, now wants a replacement and support.\"", "**Compact**, loses detail"] },
          { icon: "FaMagnifyingGlass", title: "Vector-store memory", tag: "Stores meaning", lines: ["\"How do I replace my laptop?\" → retrieves turns 5, 2 and 3 – the most **relevant**, not the most recent", "**Scales** to long histories"] },
        ] },
      ],
    },
    {
      title: "Persistent Memory",
      subtitle: "Session memory lives only while the app runs; persistent memory survives restarts",
      demo: S + "2_8_persistent_chatbot.py",
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
    { kind: "image", src: "why_rag.png", alt: "Why do we need RAG?", demo: S + "2_9_chroma_db_basic.py, 2_10_vector_embedding_cosine_similarity.py" },
    { kind: "image", src: "what_happens_in_rag.png", alt: "What happens in RAG", demo: S + "2_9_chroma_db_basic.py, 2_10_vector_embedding_cosine_similarity.py" },
    { kind: "image", src: "embeddings.png", alt: "Embeddings: turning text into vectors", demo: S + "2_10_vector_embedding_cosine_similarity.py" },
    { kind: "image", src: "vector_similarity.png", alt: "Vector similarity: finding meaningful matches", demo: S + "2_10_vector_embedding_cosine_similarity.py, 2_16_rag_cosine_euclidean_1.py" },
    {
      title: "Measuring Similarity",
      subtitle: "Nearest-neighbour retrieval ranks stored vectors by how close they are to the query vector",
      demo: S + "2_16_rag_cosine_euclidean_1.py",
      blocks: [
        { type: "cards", size: 11, items: [
          { icon: "FaCompassDrafting", title: "Cosine similarity", lines: ["Angle between two vectors – ignores length", "**Larger is better** (1 = same direction)"] },
          { icon: "FaRulerHorizontal", title: "L2 (Euclidean) distance", lines: ["Straight-line distance between two points", "**Smaller is better** (0 = identical)"] },
          { icon: "FaArrowsLeftRight", title: "Dot product", lines: ["Alignment and magnitude together", "**Larger is better**; equals cosine for normalised vectors"] },
        ] },
        { type: "callout", eyebrow: "ChromaDB default", text: "Chroma uses squared L2 distance unless you choose otherwise – so lower scores mean closer matches." },
      ],
    },
    { kind: "image", src: "chromadb_qa_vectors.png", alt: "How ChromaDB stores Q&A: questions as vectors, answers as text", demo: S + "2_9_chroma_db_basic.py" },
    {
      title: "ChromaDB: CRUD and Metadata Filters",
      subtitle: "A local, persistent vector database – documents, embeddings and metadata together",
      demo: S + "2_11_chromadb_crud.py, 2_12_chromadb_search.py, 2_13_chroma_db_adding_metadata.py",
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
      demo: S + "2_9_chroma_db_basic.py, 2_14_faiss_search.py",
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
    {
      title: "FAISS: Search Without Comparing Everything",
      subtitle: "Facebook AI Similarity Search – Meta's library for fast similarity search over dense vectors",
      demo: S + "2_14_faiss_search.py, 2_15_faiss_search_ollama.py",
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
      demo: S + "2_19_rag_pipeline.py, 2_20_rag_pipeline_ollama.py, 2_21_langchain_rag.py",
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
      title: "Document Loaders and Text Splitters",
      subtitle: "Turn files into Document objects, then into chunks small enough to embed",
      demo: S + "2_17_document_loaders.py, 2_18_text_splitters.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { icon: "FaFileImport", title: "Document loaders", lines: ["Read a source and return Document objects (text + metadata)", "One format = one loader: PDF, Word, HTML, CSV, Notion, …", "PyPDFLoader returns **one Document per page**"],
            code: `loader = PyPDFLoader("banking.pdf")
documents = loader.load()` },
          { icon: "FaScissors", title: "Text splitters", lines: ["**RecursiveCharacterTextSplitter** tries paragraph → newline → sentence → space → character, keeping sentences whole", "**SemanticChunker** asks \"does the topic change here?\" using embeddings instead of counting characters"] },
        ] },
      ],
    },
    {
      title: "Why Chunk, and How",
      subtitle: "We cannot send whole documents to the LLM – and we should not want to",
      demo: S + "2_18_text_splitters.py, 2_21_langchain_rag.py",
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
      title: "Retrievers",
      subtitle: "The bridge between the vector database and the LLM – only the relevant chunks reach the prompt",
      demo: S + "2_22_retrievers.py",
      blocks: [
        { type: "table", size: 10, widths: [2.0, 5.2], head: ["Retriever", "What it does"], rows: [
          ["VectorStoreRetriever", "Embeds the query and returns the most similar chunks – the default"],
          ["MultiQueryRetriever", "An LLM writes several versions of the question, retrieves for each, merges the results"],
          ["ContextualCompression", "Retrieves candidates, then a compressor or reranker keeps only the relevant parts"],
          ["SelfQueryRetriever", "An LLM splits the question into a semantic query plus metadata filters"],
          ["ParentDocumentRetriever", "Matches on small child chunks, returns the larger parent for more context"],
          ["MultiVectorRetriever", "Several vectors per document (summary, chunks, questions) map back to one document"],
          ["EnsembleRetriever", "Runs several retrievers and fuses the rankings (Reciprocal Rank Fusion)"],
        ] },
      ],
    },
    {
      title: "Hands-on: Q&A Bot over PDFs",
      subtitle: "A LangServe app that answers questions about an insurance PDF",
      demo: S + "2_23_…_chroma.py, 2_24_…_chroma_ollama.py, 2_25_…_faiss.py, 2_26_…_pdf_chatbot.py",
      left: [
        { type: "steps", items: [
          { title: "Run the Chroma version", text: "`2_23_langchain_qand_a_bot_chroma.py` (or `2_24` with local Ollama embeddings)" },
          { title: "Open the playground", text: "`http://localhost:8000/ask/playground/`" },
          { title: "Ask about the policy", text: "Answers come only from the retrieved chunks" },
          { title: "Swap in FAISS", text: "`2_25_langchain_qanda_bot_faiss.py` – same app, different store" },
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
        { tag: "2_7", title: "Memory", text: "Buffer, summary and vector-store memory; a persistent chatbot" },
        { tag: "2_11", title: "Vector stores", text: "ChromaDB CRUD with metadata filters; FAISS indexes" },
        { tag: "2_19", title: "A RAG pipeline", text: "Load → split → embed → store → retrieve → generate" },
        { tag: "2_23", title: "PDF Q&A bot", text: "A LangServe app over an insurance document" },
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
