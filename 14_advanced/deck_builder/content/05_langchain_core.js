const M = "05_langchain/";
const LCEL = "../3_langgraph/3_0_langchain_lcel.py";

module.exports = {
  section: "Module 05 – LangChain Core",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 05",
      title: "LangChain Core",
      subtitle: "Compose LLM apps from small parts, give them memory, and ground them in your own documents",
      goals: [
        { icon: "FaLink", title: "Compose chains with LCEL", text: "prompt | llm | parser, and the Runnables behind the pipe" },
        { icon: "FaMemory", title: "Add conversation memory", text: "buffer, summary and vector-store memory; persistence" },
        { icon: "FaBook", title: "Build a RAG pipeline", text: "loaders, splitters, embeddings, retrievers" },
        { icon: "FaEye", title: "Observe and combine", text: "callbacks, and one retriever over many sources" },
      ],
      agenda: [
        "LangChain overview; LCEL and Runnables",
        "Prompt templates and output parsers",
        "Conversation memory, session and persistent",
        "Document loaders and text splitters",
        "The RAG pipeline end to end",
        "Retriever types, with a worked example",
        "Callbacks",
        "Combining several retrievers",
      ],
    },
    {
      title: "LangChain at a Glance",
      subtitle: "An open-source framework for building applications on top of LLMs",
      demo: LCEL,
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
      demo: LCEL + ", 3_0_langchain_lcel_ollama.py",
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
    { kind: "image", src: "lcel_operators.png", alt: "LCEL operators and example", demo: LCEL },
    {
      title: "Three Runnables You Will Use Often",
      subtitle: "Small building blocks that make chains flexible",
      demo: LCEL,
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
    { kind: "image", src: "prompt_template_types.png", alt: "Three types of prompt templates in LangChain", demo: M + "prompt_templates.py, " + M + "prompt_templates_openai.py" },
    { kind: "image", src: "output_parsers.png", alt: "LangChain output parsers", demo: M + "output_parsers.py, " + M + "output_parsers_openai.py" },

    // ---------------------------------------------------------------- memory
    {
      title: "Conversation Memory Types",
      subtitle: "Six turns: a laptop purchase, returns, a dead battery, delivery, a replacement, support",
      demo: M + "memory_types.py",
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
      demo: M + "persistent_chatbot.py",
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

    // ---------------------------------------------------------------- RAG pipeline
    {
      title: "Document Loaders and Text Splitters",
      subtitle: "Turn files into Document objects, then into chunks small enough to embed",
      demo: M + "document_loaders.py, " + M + "text_splitters.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { icon: "FaFileImport", title: "Document loaders", lines: ["Read a source and return Document objects (text + metadata)", "One format = one loader: PyPDFLoader, WebBaseLoader, CSVLoader, NotionDirectoryLoader …", "PyPDFLoader returns **one Document per page**"],
            code: `loader = PyPDFLoader("banking.pdf")
documents = loader.load()` },
          { icon: "FaScissors", title: "Text splitters", lines: ["**RecursiveCharacterTextSplitter** tries paragraph → newline → sentence → space → character, keeping sentences whole", "**SemanticChunker** asks \"does the topic change here?\" using embeddings instead of counting characters"] },
        ] },
      ],
    },
    {
      title: "The RAG Pipeline, End to End",
      subtitle: "Index once, then answer many questions",
      demo: M + "rag_pipeline.py, " + M + "rag_pipeline_ollama.py",
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
      title: "Retrievers",
      subtitle: "The bridge between the vector database and the LLM – only the relevant chunks reach the prompt",
      demo: M + "retrievers.py",
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
      title: "Retrievers, Worked Through",
      subtitle: "\"What is the work-from-home policy for employees with children?\" – what each one returns",
      demo: M + "retrievers.py",
      blocks: [
        { type: "table", size: 9.5, widths: [1.9, 5.3], head: ["Retriever", "What it finally hands to the LLM"], rows: [
          ["VectorStoreRetriever", "Chunks that mention work-from-home, remote work, employees with children"],
          ["MultiQueryRetriever", "Chunks found via rewrites like \"WFH policy for parents\" and \"flexible working for carers\""],
          ["ContextualCompression", "A smaller, focused version of the retrieved text – sentences unrelated to parents removed"],
          ["SelfQueryRetriever", "Documents matching the meaning and a metadata filter, e.g. department = \"HR\""],
          ["ParentDocumentRetriever", "The whole HR policy section around \"Employees may work remotely up to 3 days a week…\""],
          ["MultiVectorRetriever", "The original policy document, matched through its summary or hypothetical-question vectors"],
          ["EnsembleRetriever", "One reranked list from BM25 keyword search + vector search, fused with RRF"],
        ] },
      ],
    },
    {
      title: "Callbacks",
      subtitle: "Hooks that fire on every event – see what was sent, retrieved, called and how long it took",
      demo: M + "callbacks.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "callbacks.py – a custom handler", code:
`class LifecycleLogger(BaseCallbackHandler):
    def on_chain_start(self, serialized, inputs, **kw):
        print(f"[chain started] input={inputs}")
    def on_llm_start(self, serialized, prompts, **kw):
        print(f"[llm call started] {len(prompts)} prompt(s)")
    def on_llm_end(self, response, **kw):
        print("[llm call ended]")

chain.invoke({"question": "What is a p-value?"},
             config={"callbacks": [LifecycleLogger()]})` },
        { type: "code", caption: "Streaming – one event per token", code:
`class TokenPrinter(BaseCallbackHandler):
    def on_llm_new_token(self, token, **kw):
        print(token, end="", flush=True)` },
      ],
      right: [
        { type: "text", text: "**Questions callbacks answer**", size: 12 },
        { type: "bullets", size: 11, items: [
          "What prompt was sent?",
          "Which documents were retrieved?",
          "How many tokens were used? (`get_openai_callback`)",
          "How long did the LLM take?",
          "Which tool was called? Did anything fail?",
        ] },
        { type: "callout", eyebrow: "Next step", text: "LangSmith (Module 09) records all of this for you, as traces." },
      ],
    },
    {
      title: "One Retriever over Many Sources",
      subtitle: "Company knowledge lives in PDFs, wikis and databases – search them all with one call",
      demo: M + "combining_retrievers.py",
      split: [1, 1.2],
      left: [
        { type: "tree", boxW: 1.3, size: 10, rows: [["Question"], [{ label: "EnsembleRetriever", fill: "navy" }], ["Policy PDF", "Wiki (Notion)", "Limits DB"], [{ label: "One fused list (RRF)", fill: "teal" }]] },
      ],
      right: [
        { type: "code", caption: "combining_retrievers.py (condensed)", code:
`policy_pages = PyPDFLoader(pdf_path).load()
wiki_docs = NotionDirectoryLoader(wiki_path).load()

class ReimbursementLimitsRetriever(BaseRetriever):
    def _get_relevant_documents(self, query, ...):
        ...   # SQL lookup – not vectors at all

ensemble_retriever = EnsembleRetriever(
    retrievers=[policy_retriever, wiki_retriever,
                limits_retriever],
    weights=[1/3, 1/3, 1/3])` },
        { type: "text", size: 11, color: "slate", text: "Any retriever works in the ensemble – even a custom one over SQL." },
      ],
    },
    {
      kind: "summary",
      title: "Module 05 Summary",
      subtitle: "What you built",
      built: [
        { tag: "LCEL", title: "Chains", text: "prompt | llm | parser, with OpenAI and Ollama" },
        { tag: "memory", title: "Memory", text: "Buffer, summary, vector-store; a persistent chatbot" },
        { tag: "RAG", title: "A RAG pipeline", text: "Load → split → embed → store → retrieve → generate" },
        { tag: "multi", title: "Many sources, one retriever", text: "PDF + wiki + SQL fused with RRF" },
      ],
      takeaways: [
        "In modern LangChain, everything is a Runnable joined with |",
        "Pick memory by what you can afford to send",
        "Chunking often matters more than the vector DB",
        "The retriever decides what the LLM gets to see",
        "Callbacks make every step observable",
      ],
      next: "Module 06: LangChain Agents and Tool Use",
    },
  ],
};
