module.exports = {
  section: "RAG with Postgres",
  slides: [
    {
      title: "01a – Embeddings",
      subtitle: "An embedding turns text into numbers; similar meaning gives similar numbers",
      demo: "01a_embeddings.py",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "01a_embeddings.py", code:
"response = client.embeddings.create(\n    model=\"text-embedding-3-small\",\n    input=SENTENCES + [QUESTION],\n)\nvectors = [item.embedding for item in response.data]\n\ndef similarity(a, b):\n    return sum(x * y for x, y in zip(a, b))" },
      ],
      right: [
        { type: "text", text: "**Question:** \"How many holidays can I take in a year?\"", size: 11.5 },
        { type: "table", size: 10, widths: [0.8, 3], head: ["Score", "Sentence"], rows: [
          ["0.402", "Employees get 18 days of annual leave per year."],
          ["0.155", "The hotel limit in Mumbai is INR 7,000 per night."],
          ["0.153", "Our office cafeteria serves lunch from 12 to 2."],
        ] },
        { type: "callout", eyebrow: "Meaning, not keywords", text: "\"holidays\" never appears in the leave sentence, yet it wins." },
      ],
    },
    {
      title: "02a – Vectors in Postgres",
      subtitle: "pgvector adds a VECTOR column type and distance operators to ordinary SQL",
      demo: "02a_pgvector.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "02a_pgvector.py", code:
"conn = psycopg.connect(DATABASE_URL, autocommit=True)\nconn.execute(\"CREATE EXTENSION IF NOT EXISTS vector\")\nconn.execute(\"CREATE TABLE demo (content TEXT, \"\n             \"embedding VECTOR(1536))\")\n\nrows = conn.execute(\n    \"SELECT content, embedding <=> %s::vector AS distance \"\n    \"FROM demo ORDER BY distance LIMIT 2\",\n    (question_vector,),\n).fetchall()" },
      ],
      right: [
        { type: "icons", items: [
          { icon: "FaPuzzlePiece", title: "CREATE EXTENSION vector", text: "Once per database" },
          { icon: "FaRulerHorizontal", title: "<=>  cosine distance", text: "0 = same meaning; smaller is closer" },
          { icon: "FaLayerGroup", title: "One database for everything", text: "Vectors, chat memory, and later users and orders – no separate vector DB" },
        ] },
        { type: "code", caption: "output", code: "Question: Where can I stay in Mumbai?\n0.388  The hotel limit in Mumbai is INR 7,000 ...\n0.886  Employees get 18 days of annual leave ..." },
      ],
    },
    {
      title: "02b – Ingest the PDFs",
      subtitle: "Read, cut into overlapping chunks, embed in one call per file, store",
      demo: "02b_ingest_pdfs.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaFilePdf", label: "PDF", caption: "sample_docs/*.pdf" },
          { icon: "FaAlignLeft", label: "Text", caption: "pypdf, page by page" },
          { icon: "FaScissors", label: "Chunks", caption: "500 characters, 100 overlap", color: "coral" },
          { icon: "FaCubes", label: "Embeddings", caption: "one API call per file" },
          { icon: "FaDatabase", label: "chunks table", caption: "source, content, embedding", color: "teal" },
        ] },
        { type: "cols", cols: [
          [{ type: "code", caption: "02b_ingest_pdfs.py", code:
"def chunk(text, size=500, overlap=100):\n    pieces = []\n    start = 0\n    while start < len(text):\n        pieces.append(text[start:start + size])\n        start += size - overlap\n    return pieces" }],
          [{ type: "bullets", size: 10.5, items: [
            "**Overlap:** a sentence cut at the end of one chunk is whole at the start of the next",
            "**Re-run safe:** `DELETE ... WHERE source = %s` before inserting a file again",
            "Output: leave_policy.pdf 4 chunks, travel_policy.pdf 3 chunks",
          ] }],
        ] },
      ],
    },
    {
      title: "03a – Plain RAG",
      subtitle: "Always search, put the results in the prompt, answer only from them",
      demo: "03a_rag.py",
      split: [1, 1.1],
      left: [
        { type: "steps", items: [
          { title: "Embed the question", text: "Same model as the chunks" },
          { title: "Find the 3 nearest chunks", text: "ORDER BY embedding <=> question" },
          { title: "Answer from the context", text: "\"If the answer is not there, say you don't know\"" },
        ] },
      ],
      right: [
        { type: "table", size: 10, widths: [1.9, 2.3], head: ["Question", "Answer"], rows: [
          ["Annual leave carry forward?", "Up to 10 days; the rest lapse on 31 March"],
          ["Hotel limit in Pune?", "INR 5,500 per night"],
          ["Hi, good morning!", "**I don't know.**"],
        ] },
        { type: "callout", eyebrow: "The problem", text: "Plain RAG searches for every message – even a greeting – and then answers from irrelevant chunks." },
      ],
    },
  ],
};
