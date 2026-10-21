const S = "session_8/";
const RAGAS = S + "8_18_ragas_evaluation.py, 8_19_ragas_evaluation_customer_support.py";

module.exports = {
  section: "Session 8 – Agentic RAG and GraphRAG",
  slides: [
    {
      kind: "opener",
      eyebrow: "Session 8  ·  Sat 15-Nov  ·  08:00–11:00 AM",
      title: "Agentic RAG and GraphRAG for Agents",
      subtitle: "When simple retrieve-then-generate is not enough: smarter retrieval, self-checking, graphs – and how to measure it",
      goals: [
        { icon: "FaTriangleExclamation", title: "Diagnose why RAG fails", text: "missed retrieval, noise, hallucination, fragmentation" },
        { icon: "FaRobot", title: "Let an agent drive retrieval", text: "adaptive strategies, Self-RAG, corrective RAG" },
        { icon: "FaRankingStar", title: "Improve what reaches the LLM", text: "reranking and hybrid keyword + semantic search" },
        { icon: "FaCircleNodes", title: "Connect facts and measure quality", text: "GraphRAG, multi-hop reasoning, RAGAS metrics" },
      ],
      agenda: [
        "RAG failure modes and advanced approaches",
        "Traditional RAG vs agentic RAG",
        "Retrieval + reasoning",
        "Self-RAG",
        "Corrective RAG (CRAG)",
        "Re-ranking retrieved chunks",
        "Hybrid search",
        "GraphRAG",
        "Multi-hop reasoning",
        "Evaluating RAG with RAGAS",
      ],
    },
    {
      title: "How RAG Fails",
      subtitle: "Five failure modes to recognise before reaching for a fix",
      demo: S + "8_1_rag_hallucination_eval.py",
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
      subtitle: "The techniques this session covers – each targets a specific weakness",
      demo: S + "8_1_rag_hallucination_eval.py",
      blocks: [
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaRobot", title: "Agentic RAG", text: "An agent decides what, how and when to retrieve" },
          { icon: "FaRotateRight", title: "Self-RAG", text: "Checks the evidence; retrieves again if weak" },
          { icon: "FaGlobe", title: "Corrective RAG", text: "Falls back to web search when local fails" },
          { icon: "FaRankingStar", title: "Reranking", text: "A stronger model re-orders the chunks" },
          { icon: "FaLightbulb", title: "HyDE", text: "Embed a hypothetical answer, search with it" },
          { icon: "FaClone", title: "Query expansion", text: "Several rewrites of the question" },
          { icon: "FaCircleNodes", title: "GraphRAG", text: "Entities and relationships as a graph" },
          { icon: "FaShuffle", title: "Hybrid RAG", text: "Combine keyword, vector and graph search" },
          { icon: "FaStairs", title: "Multi-hop", text: "Chain several facts to one answer" },
          { icon: "FaBrain", title: "Retrieval + reasoning", text: "Compute and decide on retrieved facts" },
          { icon: "FaGaugeHigh", title: "RAGAS", text: "Measure retrieval and answer quality" },
          { icon: "FaShieldHalved", title: "Grounding checks", text: "Every claim backed by context" },
        ] },
      ],
    },
    {
      title: "Traditional RAG vs Agentic RAG",
      subtitle: "A fixed pipeline vs an agent that plans its retrieval",
      demo: S + "8_3_…_vs_agentic_rag.py, 8_4_…_serp.py, 8_5_…_traditional_rag.py vs 8_6_…_agentic_rag.py",
      blocks: [
        { type: "compare", size: 11.5, cols: [
          { title: "Traditional RAG", color: "slate", items: ["Fixed retrieval pipeline", "Retrieves once", "One LLM call", "No planning; follows a predefined sequence", "Simple architecture", "Best for straightforward Q&A"] },
          { title: "Agentic RAG", color: "teal", items: ["Intelligent, dynamic workflow", "Retrieves as many times as needed", "Several reasoning steps", "Plans, then chooses the best path", "Multi-step agent architecture", "Best for complex problem solving"] },
        ] },
      ],
    },
    { kind: "image", src: "traditional_vs_agentic_rag.png", alt: "Traditional RAG vs agentic RAG flow", demo: S + "8_3_traditional_vs_agentic_rag.py" },
    {
      title: "Adaptive Retrieval Strategies",
      subtitle: "An agentic system picks how to retrieve – including not retrieving at all",
      demo: S + "8_7_adaptive_retrieval_strategies.py, 8_8_adaptive_retrieval_strategies_serp.py",
      blocks: [
        { type: "tiles", cols: 3, items: [
          { icon: "FaForwardFast", title: "Skip retrieval", text: "Answer directly when existing knowledge is enough" },
          { icon: "FaMagnifyingGlass", title: "Single retrieval", text: "Retrieve once for simple factual questions" },
          { icon: "FaRotate", title: "Iterative retrieval", text: "Fetch more when the first pass isn't enough" },
          { icon: "FaPenToSquare", title: "Query reformulation", text: "Rewrite the question for better search" },
          { icon: "FaLayerGroup", title: "Multi-source", text: "Combine vector DB, SQL, APIs and web search" },
          { icon: "FaScrewdriverWrench", title: "Tool-based", text: "Pick the right tool for the request" },
        ] },
      ],
    },
    {
      title: "Retrieval + Reasoning",
      subtitle: "Retrieval supplies the facts; reasoning uses them to solve the user's problem",
      demo: S + "8_9_loan_eligibility_rag_reasoning.py",
      blocks: [
        { type: "callout", eyebrow: "The question", text: "\"Can I get a ₹50 lakh home loan? My salary is ₹18 lakh a year, I already have a car loan, and my credit score is 760.\"" },
        { type: "compare", size: 11, cols: [
          { title: "Retrieval finds", color: "navy", items: ["Loan eligibility policy", "Current interest rates", "Customer profile and existing loans", "Credit-score rules, RBI lending rules"] },
          { title: "Reasoning does", color: "coral", items: ["Calculates the debt-to-income ratio", "Checks credit-score eligibility", "Applies the policy rules", "Works out the maximum amount and suitable options"] },
        ] },
      ],
    },
    {
      title: "A Cohere RAG Pipeline",
      subtitle: "Embed, rerank and generate – with grounding built into the chat endpoint",
      demo: S + "8_10_cohere_rag_pipeline.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaCubes", label: "embed()", caption: "Text → 1536-dim vectors (embed-v4.0)" },
          { icon: "FaRankingStar", label: "rerank()", caption: "324 FAQs → the top 3 for the query (rerank-v3.5)" },
          { icon: "FaComments", label: "chat()", caption: "Answer with the reranked FAQs passed as documents=" },
        ] },
        { type: "callout", eyebrow: "Notice", text: "\"How do I get my money back for an order?\" – reranking correctly surfaces the three refund FAQs. Cohere's chat endpoint grounds the answer itself; with OpenAI you build that prompt yourself." },
      ],
    },
    {
      title: "Self-RAG: Don't Trust the First Retrieval",
      subtitle: "Retrieve → check → retrieve or generate again if needed → answer",
      demo: S + "8_11_self_rag.py",
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
      demo: S + "8_12_corrective_rag.py",
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
      demo: S + "8_13_cohere_reranking.py",
      blocks: [
        { type: "chain", items: ["Query", "Vector search", "Top 20 chunks", "Reranker", "Best 3–5", "LLM"], highlight: [3] },
        { type: "table", size: 10.5, widths: [3.6, 1.1, 1.1], head: ["\"Documents for a cashless health insurance claim?\"", "Vector score", "Reranked"], rows: [
          ["A – Submit the claim form, original bills and discharge summary", "0.82", "**0.97 ✓**"],
          ["B – Premiums must be paid within the grace period", "0.79", "0.18 ✗"],
          ["C – Required documents include prescription and diagnostic reports", "0.76", "**0.94 ✓**"],
        ] },
        { type: "text", size: 11.5, color: "slate", text: "A cross-encoder reranker reads the query and each chunk together. B was only \"about health insurance\"; A and C go to the LLM." },
      ],
    },
    {
      title: "Hybrid Search",
      subtitle: "Combine methods so each one covers the other's blind spot",
      demo: S + "8_14_hybrid_search.py, 8_15_agentic_hybrid_search.py",
      blocks: [
        { type: "cols", cols: [
          [
            { type: "text", text: "**Keyword + semantic (8_14)**", size: 12.5 },
            { type: "compare", size: 11, cols: [
              { title: "Keyword", color: "navy", items: ["Exact words", "Error codes, names, acronyms"] },
              { title: "Semantic", color: "teal", items: ["Meaning", "Paraphrases, natural language"] },
            ] },
          ],
          [
            { type: "text", text: "**Vector + graph (8_15)**", size: 12.5 },
            { type: "text", size: 11, text: "\"My Savings Account Plus card was used fraudulently – am I covered, and how long will it take?\"" },
            { type: "bullets", size: 10.5, items: [
              "**Vector** finds the fraud-protection FAQ and the Zero Liability page",
              "**Graph** chains Savings Account Plus → Zero Liability → 60-day window → Fraud Resolution → 5 business days",
              "Merge both pools, then rerank",
            ] },
          ],
        ] },
      ],
    },
    {
      title: "GraphRAG: Connecting Facts Across Documents",
      subtitle: "Extract entities and relationships into a knowledge graph instead of treating chunks as isolated",
      demo: S + "8_16_graph_rag.py",
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
      demo: S + "8_17_multi_hop_reasoning.py",
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

    // ---------------------------------------------------------------- RAGAS
    {
      title: "Evaluating RAG with RAGAS",
      subtitle: "Retrieval-Augmented Generation Assessment – scores retrieval and generation, no manual labelling",
      demo: RAGAS,
      blocks: [
        { type: "cards", size: 10.5, items: [
          { icon: "FaBullseye", title: "Faithfulness", tag: "Accuracy", lines: ["Did the LLM make things up?", "Every claim must be backed by the context"] },
          { icon: "FaComments", title: "Answer relevancy", tag: "Relevance", lines: ["Did the LLM answer the question that was asked?"] },
          { icon: "FaFilter", title: "Context precision", tag: "Usefulness", lines: ["Was most of what we retrieved actually useful?"] },
          { icon: "FaListCheck", title: "Context recall", tag: "Completeness", lines: ["Did we retrieve everything the answer needed?"] },
        ] },
      ],
    },
    { kind: "image", src: "ragas_pipeline.png", alt: "RAGAS evaluation of a RAG pipeline", demo: RAGAS },
    {
      title: "RAGAS Metrics, Worked Through",
      subtitle: "One cashless-claim question, scored four ways",
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
    {
      kind: "summary",
      title: "Session 8 Summary",
      subtitle: "What you built today",
      built: [
        { tag: "8_3", title: "Traditional vs agentic RAG", text: "The same question through both pipelines" },
        { tag: "8_11", title: "Self-RAG and CRAG", text: "Grade the evidence; retry or fall back to the web" },
        { tag: "8_13", title: "Reranking and hybrid search", text: "Cohere reranker; keyword + semantic + graph" },
        { tag: "8_16", title: "GraphRAG and multi-hop", text: "A bank-policy knowledge graph" },
        { tag: "8_18", title: "RAGAS evaluation", text: "Four metrics on an insurance Q&A system" },
      ],
      takeaways: [
        "Name the failure mode before choosing a fix",
        "Agentic RAG decides when, what and how often to retrieve",
        "Rerank – similar is not the same as relevant",
        "Graphs answer questions that span documents",
        "Measure with RAGAS before and after every change",
      ],
      next: "Session 9: Deep Agents – Reflection, Planning and Long-Term Memory",
    },
  ],
};
