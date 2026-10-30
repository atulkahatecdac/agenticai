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
      subtitle: "Common techniques, each aimed at a specific weakness – this session demos most of them",
      demo: "Concept",
      blocks: [
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaRobot", title: "Agentic RAG", text: "An agent decides what, how and when to retrieve" },
          { icon: "FaRotateRight", title: "Self-RAG", text: "Checks its draft answer; regenerates if unsupported" },
          { icon: "FaGlobe", title: "Corrective RAG", text: "Falls back to web search when local fails" },
          { icon: "FaRankingStar", title: "Reranking", text: "A stronger model re-orders the chunks" },
          { icon: "FaLightbulb", title: "HyDE", text: "Embed a hypothetical answer, search with it" },
          { icon: "FaClone", title: "Query expansion", text: "Several rewrites of the question" },
          { icon: "FaCircleNodes", title: "GraphRAG", text: "Entities and relationships as a graph" },
          { icon: "FaShuffle", title: "Hybrid RAG", text: "Combine keyword and vector search" },
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
    { kind: "image", src: "traditional_vs_agentic_rag.png", alt: "Traditional RAG vs agentic RAG flow", demo: S + "8_3_traditional_vs_agentic_rag.py (FAQ index from 8_2_support_ticketing_agent_hitl.py)" },
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
          { icon: "FaLayerGroup", title: "Multi-source", text: "Combine the FAQ knowledge base, web search and a calculator" },
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
      title: "Self-RAG: Don't Trust the First Draft",
      subtitle: "Retrieve → draft → critique the draft → regenerate if needed → answer",
      demo: S + "8_11_self_rag.py",
      blocks: [
        { type: "flow", loop: "draft not supported → regenerate, at most 2 more times", items: [
          { icon: "FaUser", label: "Question", caption: "Covered after 3 years? Can I switch insurer?" },
          { icon: "FaMagnifyingGlass", label: "Retrieve", caption: "Chunks from the insurance policy KB" },
          { icon: "FaFileLines", label: "Draft", caption: "A first answer from those chunks" },
          { icon: "FaScaleBalanced", label: "Critique", caption: "Every claim backed? Question fully answered?", color: "coral" },
          { icon: "FaRotateRight", label: "Regenerate", caption: "Stricter grounding or a follow-up retrieval", color: "teal" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "This catches what grading documents cannot: the chunks were relevant, but the answer still overreached beyond them." },
      ],
    },
    {
      title: "Corrective RAG (CRAG)",
      subtitle: "When local knowledge fails, fall back to the web instead of guessing",
      demo: S + "8_12_corrective_rag.py",
      blocks: [
        { type: "cols", ratio: [1.15, 1], cols: [
          [{ type: "tree", boxW: 1.5, labels: ["", "", "how many are relevant?", ""], rows: [["Question"], ["Retrieve from the vector DB"], [{ label: "Grade the documents", fill: "coral" }], [{ label: "All: KB only", fill: "teal" }, { label: "Some: KB + web", fill: "slate" }, { label: "None: web only", fill: "navy" }], ["Generate the answer"]] }],
          [
            { type: "bullets", size: 11.5, items: ["Plain RAG answers from whatever it retrieved – even the wrong thing", "CRAG grades the retrieved chunks first", "Some relevant: refine them, then add a web search. None: rewrite the query and use the web only", "The answer comes from the best evidence available"] },
            { type: "callout", eyebrow: "Self-RAG vs CRAG", text: "Self-RAG grades the generated answer; CRAG grades the retrieved documents and can change source." },
          ],
        ] },
      ],
    },
    {
      title: "Reranking Retrieved Chunks",
      subtitle: "The most similar chunk is not always the most relevant one",
      demo: S + "8_13_cohere_reranking.py",
      blocks: [
        { type: "chain", items: ["Query", "Vector search", "Top 10 chunks", "Reranker", "Best 3", "LLM"], highlight: [3] },
        { type: "table", size: 10.5, widths: [3.6, 1.1, 1.1], head: ["\"Documents for a cashless health insurance claim?\" (illustrative scores)", "Vector score", "Reranked"], rows: [
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
            { type: "text", text: "**TF-IDF + embeddings (8_14)**", size: 12.5 },
            { type: "compare", size: 11, cols: [
              { title: "Keyword", color: "navy", items: ["Exact words", "\"SIP investment plan\""] },
              { title: "Semantic", color: "teal", items: ["Meaning", "\"put money away for old age\""] },
            ] },
            { type: "text", size: 10.5, color: "slate", text: "Two ways to combine: a weighted average, or Reciprocal Rank Fusion." },
          ],
          [
            { type: "text", text: "**BM25 + dense vectors (8_15)**", size: 12.5 },
            { type: "bullets", size: 10.5, items: [
              "**Favours BM25:** \"What is the IRDAI mandated claim settlement timeline…?\" – an exact acronym",
              "**Favours vectors:** \"If my mom already had a health condition…\" – avoids the policy's own wording",
              "Reciprocal Rank Fusion lifts a document ranked highly by either retriever",
            ] },
          ],
        ] },
      ],
    },
    {
      title: "GraphRAG: Connecting Facts Across Documents",
      subtitle: "Extract entities and relationships into a knowledge graph instead of treating chunks as isolated",
      demo: S + "8_16_graph_rag.py",
      split: [1.2, 1],
      left: [
        { type: "text", text: "**\"If I switch insurer through portability, do I keep credit for the waiting period already completed?\"**", size: 11.5 },
        { type: "steps", size: 10.5, titleSize: 11, gap: 0.08, items: [
          { title: "Extract once", text: "An LLM pulls (subject, relation, object) triples from the policy chunks" },
          { title: "Build the graph", text: "Those triples become a networkx graph" },
          { title: "Find the entities", text: "Match what the question mentions to graph nodes" },
          { title: "Walk outward", text: "Collect every connected fact in one traversal" },
        ] },
      ],
      right: [
        { type: "text", text: "**One triple as a graph**", size: 12 },
        { type: "tree", boxW: 2.1, size: 10.5, labels: ["processed_by"], rows: [[{ label: "Cashless Claim", fill: "navy" }], [{ label: "TPA", fill: "teal" }]] },
      ],
    },
    {
      title: "Multi-Hop Reasoning",
      subtitle: "Follow several facts to reach an answer no single chunk contains",
      demo: S + "8_17_multi_hop_reasoning.py",
      blocks: [
        { type: "callout", eyebrow: "Question", text: "\"I'm on a Family Floater Gold plan and intimated the insurer 20 hours after an emergency admission. Will a cashless claim be accepted, who processes it, and how long will settlement take?\"" },
        { type: "flow", loop: "at most 4 hops", items: [
          { icon: "FaMagnifyingGlass", label: "Retrieve", caption: "Vector search for the current query" },
          { icon: "FaBrain", label: "Decide", caption: "What is still missing?", color: "coral" },
          { icon: "FaRoute", label: "next_hop_query", caption: "A new search for the missing fact" },
          { icon: "FaReply", label: "Answer", caption: "From everything collected", color: "teal" },
        ] },
        { type: "text", size: 11.5, color: "slate", text: "The demo compares this with a single search (k=3). Unlike GraphRAG, it chains facts with repeated vector searches and no stored graph." },
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
      subtitle: "One cashless-claim question, scored four ways (illustrative numbers – run the demos for real scores)",
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
        { tag: "8_11", title: "Self-RAG and CRAG", text: "Grade the answer or the documents; regenerate or use the web" },
        { tag: "8_13", title: "Reranking and hybrid search", text: "Cohere reranker; keyword + semantic with rank fusion" },
        { tag: "8_16", title: "GraphRAG and multi-hop", text: "An insurance-policy knowledge graph; chained searches" },
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
