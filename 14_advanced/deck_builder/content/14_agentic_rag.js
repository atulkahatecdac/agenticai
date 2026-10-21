const M = "14_agentic_rag_graph_rag/";
const RAGAS = M + "14_1_ragas_evaluation.py";

module.exports = {
  section: "Module 14 – Agentic RAG and GraphRAG",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 14",
      title: "Agentic RAG and GraphRAG",
      subtitle: "When simple retrieve-then-generate is not enough: smarter retrieval, self-checking, graphs – and how to measure it",
      goals: [
        { icon: "FaTriangleExclamation", title: "Diagnose why RAG fails", text: "missed retrieval, noise, hallucination, fragmentation" },
        { icon: "FaGaugeHigh", title: "Measure RAG quality", text: "RAGAS: faithfulness, relevancy, precision, recall" },
        { icon: "FaRobot", title: "Let retrieval check itself", text: "Self-RAG, corrective RAG, reranking" },
        { icon: "FaCircleNodes", title: "Retrieve better and connect facts", text: "HyDE, multi-query, GraphRAG, multi-hop, hybrid" },
      ],
      agenda: [
        "RAG failure modes and the advanced toolbox",
        "Traditional vs agentic RAG",
        "Evaluating RAG with RAGAS",
        "Self-RAG and corrective RAG",
        "Reranking with Cohere",
        "HyDE and multi-query retrieval",
        "GraphRAG and multi-hop reasoning",
        "Hybrid vector + graph search",
      ],
    },
    {
      title: "How RAG Fails",
      subtitle: "Five failure modes to recognise before reaching for a fix",
      demo: "Concept",
      blocks: [
        { type: "table", size: 9.5, widths: [1.45, 2.3, 2.35, 2.4], head: ["Failure", "What happens", "Common causes", "Example"], rows: [
          ["Missed retrieval", "The answer is in the knowledge base but isn't retrieved", "Poor query wording, weak embeddings, top-k too small", "Policy has the ATM withdrawal limit; unrelated card-security chunks come back"],
          ["Irrelevant context", "Retrieved chunks aren't relevant enough", "Low retrieval precision, too much top-k, no reranking", "Refund question; shipping and warranty chunks retrieved"],
          ["Hallucination", "The LLM states facts the context doesn't support", "Missing information, model assumptions, overconfidence", "Context: refunds in 5 business days. LLM: \"…and you'll receive an email confirmation\""],
          ["Lost in the middle", "The right chunk is retrieved but buried among others", "Too much context, poor ordering", "The key clause sits at position 7 of 10 and is ignored"],
          ["Fragmentation", "The answer is split across chunks", "Naive fixed-size chunking, no overlap", "A rule and its exception land in different chunks"],
        ] },
      ],
    },
    {
      title: "The Advanced-RAG Toolbox",
      subtitle: "The techniques this module covers – each targets a specific weakness",
      demo: "Concept",
      blocks: [
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaGaugeHigh", title: "RAGAS", text: "Measure retrieval and answer quality" },
          { icon: "FaRobot", title: "Agentic RAG", text: "An agent decides what, how and when to retrieve" },
          { icon: "FaRotateRight", title: "Self-RAG", text: "Checks the evidence; retrieves again if weak" },
          { icon: "FaGlobe", title: "Corrective RAG", text: "Falls back to web search when local fails" },
          { icon: "FaRankingStar", title: "Reranking", text: "A stronger model re-orders the chunks" },
          { icon: "FaLightbulb", title: "HyDE", text: "Embed a hypothetical answer, search with it" },
          { icon: "FaClone", title: "Query expansion", text: "Several rewrites of the question" },
          { icon: "FaCircleNodes", title: "GraphRAG", text: "Entities and relationships as a graph" },
          { icon: "FaStairs", title: "Multi-hop", text: "Chain several facts to one answer" },
          { icon: "FaShuffle", title: "Hybrid RAG", text: "Combine vector and graph retrieval" },
        ] },
      ],
    },
    {
      title: "Traditional RAG vs Agentic RAG",
      subtitle: "A fixed pipeline vs an agent that plans its retrieval",
      demo: "Concept",
      blocks: [
        { type: "compare", size: 11.5, cols: [
          { title: "Traditional RAG", color: "slate", items: ["Fixed retrieval pipeline", "Retrieves once", "One LLM call", "No planning; follows a predefined sequence", "Simple architecture", "Best for straightforward Q&A"] },
          { title: "Agentic RAG", color: "teal", items: ["Intelligent, dynamic workflow", "Retrieves as many times as needed", "Several reasoning steps", "Plans, then chooses the best path", "Multi-step agent architecture", "Best for complex problem solving"] },
        ] },
      ],
    },
    { kind: "image", src: "traditional_vs_agentic_rag.png", alt: "Traditional RAG vs agentic RAG flow", demo: "Concept" },

    // ---------------------------------------------------------------- RAGAS
    {
      title: "Evaluating RAG with RAGAS",
      subtitle: "Retrieval-Augmented Generation Assessment – scores retrieval and generation, not just the final answer",
      demo: RAGAS,
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaBullseye", title: "Faithfulness", tag: "Accuracy", lines: ["Did the LLM make things up?", "Every claim must be backed by the context"] },
          { icon: "FaComments", title: "Answer relevancy", tag: "Relevance", lines: ["Did the LLM answer the question that was asked?"] },
          { icon: "FaFilter", title: "Context precision", tag: "Usefulness", lines: ["Was most of what we retrieved actually useful?"] },
          { icon: "FaListCheck", title: "Context recall", tag: "Completeness", lines: ["Did we retrieve everything the answer needed?"] },
        ] },
        { type: "text", size: 11, color: "slate", text: "An LLM judge produces numbers, so a different retriever, prompt or top-k can be compared objectively – not by eye." },
      ],
    },
    { kind: "image", src: "ragas_pipeline.png", alt: "RAGAS evaluation of a RAG pipeline", demo: RAGAS },
    {
      title: "RAGAS Metrics, Worked Through",
      subtitle: "\"Documents for a cashless health claim, and when must hospitalisation be intimated?\" – scored four ways",
      demo: RAGAS,
      blocks: [
        { type: "cards", size: 10, items: [
          { icon: "FaBullseye", title: "Faithfulness 0.67", lines: ["The answer makes 3 claims; the context backs 2", "\"Intimate within **12** hours\" – the context says 24", "**Score = 2 / 3**"] },
          { icon: "FaComments", title: "Relevancy 0.95 vs 0.30", lines: ["Questions are guessed back from the answer and compared with the original", "On-topic answer → 0.95", "Answer about waiting periods → 0.30"] },
          { icon: "FaFilter", title: "Precision 0.60", lines: ["5 chunks retrieved: 3 useful, 2 not (grace period, waiting period)", "**Score = 3 / 5**"] },
          { icon: "FaListCheck", title: "Recall 0.75", lines: ["4 facts needed; the TPA's role in settlement was never retrieved", "**Score = 3 / 4**"] },
        ] },
      ],
    },
    { kind: "image", src: "ragas_answer_relevancy.png", alt: "How answer relevancy is computed: guess the question back, compare with the original", demo: RAGAS },

    // ---------------------------------------------------------------- self-checking
    {
      title: "Self-RAG: Don't Trust the First Retrieval",
      subtitle: "Retrieve → check → retrieve or generate again if needed → answer",
      demo: M + "14_2_self_rag.py",
      blocks: [
        { type: "flow", loop: "evidence insufficient → retrieve again", items: [
          { icon: "FaUser", label: "Question", caption: "Documents for a cashless health claim?" },
          { icon: "FaMagnifyingGlass", label: "Retrieve", caption: "3 chunks from the policy DB" },
          { icon: "FaScaleBalanced", label: "Check", caption: "Sufficient and relevant? One chunk is off-topic", color: "coral" },
          { icon: "FaFileLines", label: "Generate", caption: "Claim form, original bills, discharge summary, prescription, diagnostic reports", color: "teal" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "Plain RAG trusts whatever comes back. Self-RAG grades its own evidence and searches again – here, specifically for cashless-claim documents." },
      ],
    },
    {
      title: "Corrective RAG (CRAG)",
      subtitle: "When local knowledge fails, fall back to the web instead of guessing",
      demo: M + "14_3_corrective_rag.py",
      blocks: [
        { type: "cols", ratio: [1.15, 1], cols: [
          [{ type: "tree", boxW: 2.0, labels: ["", "", "relevant?", ""], rows: [["Question"], ["Retrieve from the vector DB"], [{ label: "Grade the chunks", fill: "coral" }], [{ label: "Good → use them", fill: "teal" }, { label: "Poor → web search", fill: "navy" }], ["Generate the answer"]] }],
          [
            { type: "bullets", size: 11.5, items: ["Plain RAG answers from whatever it retrieved – even the wrong thing", "CRAG grades the retrieved chunks first", "Poor or missing evidence triggers a web search instead of a guess", "The answer comes from the best evidence available"] },
            { type: "callout", eyebrow: "Self-RAG vs CRAG", text: "Self-RAG retries the same knowledge base; CRAG reaches for a different source." },
          ],
        ] },
      ],
    },
    {
      title: "Reranking Retrieved Chunks",
      subtitle: "The most similar chunk is not always the most relevant one",
      demo: M + "14_4_cohere_reranking.py",
      blocks: [
        { type: "chain", items: ["Query", "Vector search", "Top 20 chunks", "Cohere reranker", "Best 3–5", "LLM"], highlight: [3] },
        { type: "table", size: 10.5, widths: [3.6, 1.1, 1.1], head: ["\"Documents for a cashless health insurance claim?\"", "Vector score", "Reranked"], rows: [
          ["A – Submit the claim form, original bills and discharge summary", "0.82", "**0.97 ✓**"],
          ["B – Premiums must be paid within the grace period", "0.79", "0.18 ✗"],
          ["C – Required documents include prescription and diagnostic reports", "0.76", "**0.94 ✓**"],
        ] },
        { type: "text", size: 11.5, color: "slate", text: "A cross-encoder reranker reads the query and each chunk together. B was only \"about health insurance\"; A and C go to the LLM." },
      ],
    },

    // ---------------------------------------------------------------- better queries
    {
      title: "HyDE: Hypothetical Document Embeddings",
      subtitle: "Short questions and long policy text don't share words – so search with a fake answer instead",
      demo: M + "14_5_hyde_retrieval.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "Query", caption: "\"What documents are required for a cashless claim?\"" },
          { icon: "FaPen", label: "LLM drafts an answer", caption: "\"Submit a pre-authorisation form, claim form, original bills, discharge summary…\"", color: "coral" },
          { icon: "FaCubes", label: "Embed the draft", caption: "It reads like the policy documents" },
          { icon: "FaMagnifyingGlass", label: "Vector search", caption: "Document-to-document matching", color: "teal" },
        ] },
        { type: "callout", eyebrow: "Important", text: "The hypothetical answer doesn't have to be correct. It only has to look like the documents we want to retrieve. The demo searches 50 insurance policy statements." },
      ],
    },
    {
      title: "Multi-Query Retrieval",
      subtitle: "One phrasing is one guess at the source's wording – generate several and search with all of them",
      demo: M + "14_6_multi_query_retrieval.py",
      split: [1.1, 1],
      left: [
        { type: "chain", size: 10, items: ["Query", "LLM rewrites", "Search each", "Merge + dedupe", "Rerank", "LLM"], highlight: [1, 3] },
        { type: "text", text: "**\"Why was my card declined abroad?\"** becomes:", size: 11.5 },
        { type: "bullets", size: 11, items: [
          "Debit card declined during an international transaction",
          "Reasons for card rejection overseas",
          "International card transaction declined",
          "Foreign ATM and card usage restrictions",
        ] },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "Gain", color: "teal", items: ["Higher recall – different wordings find different documents"] },
          { title: "Cost", color: "coral", items: ["An extra LLM call", "More retrieval calls", "Duplicates to remove", "Usually needs a reranker"] },
        ] },
      ],
    },

    // ---------------------------------------------------------------- graphs
    {
      title: "GraphRAG: Connecting Facts Across Documents",
      subtitle: "Extract entities and relationships into a knowledge graph instead of treating chunks as isolated",
      demo: M + "14_7_graph_rag.py",
      split: [1, 1.15],
      left: [
        { type: "text", text: "**Three separate policy documents**", size: 12 },
        { type: "steps", size: 10.5, titleSize: 11, gap: 0.08, items: [
          { title: "Account terms", text: "Savings Account Plus customers are enrolled in Zero Liability Protection" },
          { title: "Program rules", text: "It covers unauthorised transactions reported within 60 days" },
          { title: "Claims policy", text: "Claims go to the Fraud Resolution team; turnaround 5 business days" },
        ] },
      ],
      right: [
        { type: "text", text: "**The same facts as a graph**", size: 12 },
        { type: "tree", boxW: 2.1, size: 10.5, labels: ["enrols customers in", "covers (60 days) · processed by", "turnaround"], rows: [["Savings Account Plus"], [{ label: "Zero Liability Protection", fill: "navy" }], ["Unauthorised transactions", "Fraud Resolution team"], [{ label: "5 business days", fill: "teal" }]] },
      ],
    },
    {
      title: "Multi-Hop Reasoning",
      subtitle: "Follow several relationships to reach an answer no single chunk contains",
      demo: M + "14_8_multi_hop_reasoning.py",
      blocks: [
        { type: "callout", eyebrow: "Question", text: "\"Is a Savings Account Plus customer covered for fraud reported 3 weeks ago, and how long will resolution take?\"" },
        { type: "flow", items: [
          { icon: "FaBuildingColumns", label: "Savings Account Plus", caption: "enrols in →" },
          { icon: "FaShieldHalved", label: "Zero Liability", caption: "covers →" },
          { icon: "FaCalendarCheck", label: "Within 60 days", caption: "3 weeks ✓ inside the window", color: "teal" },
          { icon: "FaUserShield", label: "Fraud Resolution", caption: "turnaround →" },
          { icon: "FaClock", label: "5 business days", caption: "the answer", color: "coral" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "Four facts from three documents, plus a condition applied to this customer's situation." },
      ],
    },
    {
      title: "Hybrid Search: Vector + Graph",
      subtitle: "Each retrieval method covers the other's blind spot",
      demo: M + "14_9_hybrid_search.py",
      split: [1, 1.1],
      left: [
        { type: "text", size: 11.5, text: "**\"My Savings Account Plus card was used fraudulently – am I covered, and how long will it take?\"**" },
        { type: "icons", d: 0.36, size: 10.5, items: [
          { icon: "FaMagnifyingGlass", title: "Vector search finds", text: "The fraud-protection FAQ, the Zero Liability page, the Fraud Resolution contact page" },
          { icon: "FaCircleNodes", title: "Graph traversal finds", text: "Savings Account Plus → Zero Liability → 60-day window → Fraud Resolution → 5 business days", color: "teal" },
        ] },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "Vector", color: "navy", items: ["Topical matches, even with loose wording"] },
          { title: "Graph", color: "teal", items: ["Precise facts chained across documents – when the query maps to known entities"] },
        ] },
        { type: "callout", eyebrow: "How", text: "Merge both result pools into one candidate set, then rerank – no need to guess in advance which kind of question it is." },
      ],
    },
    {
      kind: "summary",
      title: "Module 14 Summary",
      subtitle: "What you built",
      built: [
        { tag: "14_1", title: "RAGAS evaluation", text: "Four metrics on an insurance Q&A pipeline" },
        { tag: "14_2", title: "Self-RAG and CRAG", text: "Grade the evidence; retry or fall back to the web" },
        { tag: "14_4", title: "Reranking", text: "A Cohere cross-encoder in front of the LLM" },
        { tag: "14_5", title: "HyDE and multi-query", text: "Better queries, better recall" },
        { tag: "14_7", title: "GraphRAG and multi-hop", text: "A bank-policy knowledge graph, plus hybrid search" },
      ],
      takeaways: [
        "Name the failure mode before choosing a fix",
        "Measure with RAGAS before and after every change",
        "Rerank – similar is not the same as relevant",
        "Rewrite the query when wording doesn't match",
        "Graphs answer questions that span documents",
      ],
      next: "Module 15: Agentic Workflows with n8n",
    },
  ],
};
