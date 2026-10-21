const M = "03_llm_examples/";

module.exports = {
  section: "Module 03 – LLM Fundamentals and Prompting",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 03",
      title: "LLM Fundamentals, Context and Prompt Engineering",
      subtitle: "How an LLM turns text into an answer, how to call one from code, and how to prompt it well",
      goals: [
        { icon: "FaBrain", title: "Explain how an LLM works", text: "tokens, embeddings, attention, next-token prediction" },
        { icon: "FaPlug", title: "Call OpenAI, Anthropic and Ollama", text: "requests, responses, models and cost" },
        { icon: "FaPenToSquare", title: "Use the main prompting patterns", text: "personas, few-shot, CoT, ToT, ReAct" },
        { icon: "FaGaugeHigh", title: "Control output, tokens and quality", text: "structured output, tool calling, tiktoken, evaluation" },
      ],
      agenda: [
        "How an LLM works, step by step",
        "The context window",
        "The OpenAI and Anthropic APIs; choosing a model",
        "Local models with Ollama",
        "System prompts and personas",
        "Zero/few-shot, chain-of-thought, tree-of-thought, ReAct",
        "Structured output and tool calling",
        "Measuring tokens with tiktoken",
        "Evaluating LLM output",
      ],
    },
    {
      title: "How an LLM Works",
      subtitle: "Five steps from a pile of text to the next word of an answer",
      demo: "Concept",
      blocks: [
        { type: "flow", items: [
          { n: 1, label: "Train", caption: "On massive amounts of text" },
          { n: 2, label: "Tokenise", caption: "Split text into tokens" },
          { n: 3, label: "Embed", caption: "Tokens become vectors of numbers" },
          { n: 4, label: "Attend", caption: "The transformer weighs context" },
          { n: 5, label: "Predict", caption: "One token at a time, appended to the answer", color: "coral" },
        ] },
        { type: "cols", cols: [
          [{ type: "text", text: "**1 · Training data**", size: 12 }, { type: "tiles", cols: 3, size: 10, titleSize: 11, items: [
            { icon: "FaBook", title: "Books" }, { icon: "FaGlobe", title: "Websites" }, { icon: "FaNewspaper", title: "Articles" },
            { icon: "FaWikipediaW", title: "Wiki" }, { icon: "FaCode", title: "Code" }, { icon: "FaFlask", title: "Research" },
          ] }],
          [{ type: "text", text: "**2 · Tokens, not words**", size: 12 },
           { type: "chain", size: 10, items: ["Chat", "G", "PT", " is", " amazing", "."] },
           { type: "bullets", size: 10.5, items: ["Pricing and limits are counted in tokens", "Try platform.openai.com/tokenizer"] }],
        ] },
      ],
    },
    { kind: "image", src: "embedding_space_2d.png", alt: "Step 3 – embeddings: similar meaning, nearby points", demo: "Concept" },
    { kind: "image", src: "attention.png", alt: "Step 4 – attention: each word looks at every other word", demo: "Concept" },
    { kind: "image", src: "next_token_prediction.png", alt: "Step 5 – the model predicts one token at a time", demo: "Concept" },
    {
      title: "The Context Window",
      subtitle: "Everything the model can consider at once – its working memory for this request",
      demo: "Concept",
      split: [1, 1.15],
      left: [
        { type: "text", text: "**What fills it**", size: 12 },
        { type: "icons", d: 0.32, size: 10.5, titleSize: 11.5, gap: 0.1, items: [
          { icon: "FaGear", title: "System instructions" },
          { icon: "FaClockRotateLeft", title: "Previous conversation" },
          { icon: "FaUser", title: "The user's prompt" },
          { icon: "FaFileLines", title: "Uploaded documents and retrieved context" },
          { icon: "FaReply", title: "The model's own response", color: "coral" },
        ] },
        { type: "text", size: 11, color: "slate", text: "1 token ≈ 0.75 words, so 1,000 tokens ≈ 750 words." },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.6, 2.2], head: ["Model", "Context window"], rows: [
          ["GPT-5.5", "Up to 400K tokens"],
          ["Claude 4", "Up to 200K tokens"],
          ["Gemini 2.5 Pro", "Up to 1M tokens"],
          ["Llama 3.1", "Up to 128K tokens"],
          ["Mistral Large", "Up to 128K tokens"],
          ["DeepSeek-V3", "Up to 128K tokens"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Limits change often – check the provider's docs. See and compare models: poloclub.github.io/transformer-explainer · artificialanalysis.ai · livebench.ai · openrouter.ai/models" },
      ],
    },

    // ---------------------------------------------------------------- APIs
    {
      title: "The OpenAI API",
      subtitle: "Send a prompt over HTTPS, get generated text back – authenticated by an API key, billed per token",
      demo: M + "openai_exaple.py",
      split: [1, 1.1],
      left: [
        { type: "chain", size: 10, items: ["Python", "HTTPS", "OpenAI API", "Response"], highlight: [2] },
        { type: "table", size: 10, widths: [1.2, 2.9], head: ["Request field", "Purpose"], rows: [
          ["model", "Which LLM to use"],
          ["instructions", "The AI's role or behaviour (system prompt)"],
          ["input", "The user's prompt or question"],
          ["temperature", "Randomness: 0 = deterministic, 2 = most creative"],
        ] },
      ],
      right: [
        { type: "text", text: "**What comes back**", size: 12 },
        { type: "table", size: 10, widths: [1.3, 2.9], head: ["Response field", "Meaning"], rows: [
          ["id", "Unique ID of this response"],
          ["model", "The model that generated it"],
          ["created_at", "Unix timestamp"],
          ["status", "completed, in_progress or incomplete"],
          ["output", "Items generated: messages, tool calls, reasoning"],
          ["output_text", "SDK helper – all text in one string"],
        ] },
      ],
    },
    {
      title: "The Anthropic API",
      subtitle: "The Messages API – with the system prompt as its own top-level parameter",
      demo: M + "claude_example.py",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "claude_example.py", code:
`from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
    messages=[{"role": "user",
               "content": "Explain Artificial Intelligence."}],
)
print(response.content[0].text)` },
      ],
      right: [
        { type: "code", caption: "Adding a system prompt", code:
`client.messages.create(
    model="claude-sonnet-4-6",
    system="You are a friendly Python instructor.",
    max_tokens=200,
    messages=[{"role": "user",
               "content": "Explain loops."}])` },
        { type: "callout", eyebrow: "Different from OpenAI chat", text: "No \"system\" role inside messages – use `system=`. And `max_tokens` is required." },
      ],
    },
    {
      title: "Choosing a Model",
      subtitle: "Smaller models are faster and cheaper; larger ones reason better – pick the smallest that does the job",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10, widths: [1.3, 1.6, 3.2, 2.4], head: ["Model", "Price in / out (per 1M)", "Best for", "Notes"], rows: [
          ["GPT-5 nano", "$0.05 / $0.40", "Classification, extraction, high volume", "Cheapest"],
          ["GPT-5 mini", "$0.25 / $2.00", "Chatbots, education, RAG, agents", "Best value for most apps"],
          ["GPT-5", "$1.25 / $10.00", "Coding, agentic AI, research, production", "Flagship"],
          ["Claude Haiku", "Lowest", "Chatbots, classification, summarisation", "Fastest Claude"],
          ["Claude Sonnet", "Medium", "General AI, coding, RAG, agents", "The everyday workhorse"],
          ["Claude Opus", "Highest", "Research, complex reasoning, enterprise coding", "Most capable"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Prices are typical list prices at the time of writing – check the provider's pricing page before you estimate costs." },
      ],
    },
    {
      title: "Local Models with Ollama",
      subtitle: "Run open-weight LLMs on your own machine – no internet needed once a model is downloaded",
      demo: M + "ollama_example.py, ollama_chatbot.py, ollama_chatbot_streamlit.py",
      split: [1.05, 1],
      left: [
        { type: "code", caption: "ollama.com → install, then", code:
`ollama --version
ollama pull qwen3:8b     # download a model
ollama run qwen3:8b      # chat in the terminal
ollama list              # models on disk
ollama rm qwen3:8b       # delete one` },
        { type: "code", caption: "From Python – Ollama speaks the OpenAI API", code:
`client = OpenAI(base_url="http://localhost:11434/v1",
                api_key="ollama")` },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.5, 2.4], head: ["Open-weight model", "Best for"], rows: [
          ["Qwen 3", "General use, RAG, agents"],
          ["Gemma 3", "Vision, chatbots"],
          ["Llama 3.x", "General AI"],
          ["DeepSeek R1", "Reasoning"],
          ["Qwen3-Coder", "Programming"],
          ["Mistral", "Lightweight apps"],
          ["Phi", "Small, fast models"],
        ] },
        { type: "text", size: 10.5, color: "slate", text: "Works with LangChain, LangGraph, n8n and Open WebUI too." },
      ],
    },

    // ---------------------------------------------------------------- prompting
    {
      title: "System Prompts for Domain-Expert Personas",
      subtitle: "Set the role, expertise, rules and style before any user interaction",
      demo: M + "prompting_techniques.py",
      split: [1, 1.25],
      left: [
        { type: "table", size: 10.5, widths: [1.3, 2.6], head: ["Component", "Purpose"], rows: [
          ["Role", "The assistant's expertise"],
          ["Goal", "The primary objective"],
          ["Knowledge scope", "Domain or information sources"],
          ["Instructions", "How to generate answers"],
          ["Constraints", "What to avoid"],
          ["Output format", "Shape of the response"],
          ["Tone", "Formal, friendly, technical …"],
        ] },
      ],
      right: [
        { type: "code", caption: "Template", code:
`You are an expert <ROLE>.
Your goal is to <OBJECTIVE>.
Use your expertise in <DOMAIN>.
When answering:
- Explain concepts clearly.
- Ask clarifying questions if information is missing.
- Do not make up facts. If uncertain, say so.
Respond in a professional and concise manner.` },
        { type: "code", caption: "Example", code:
`You are an experienced physician specialising
in internal medicine. Always:
- Explain medical terminology simply.
- Recommend a professional for emergencies.
- Do not diagnose with certainty from limited data.` },
      ],
    },
    {
      title: "Zero-Shot, One-Shot and Few-Shot Prompting",
      subtitle: "Show the model examples of what you want – or none at all",
      demo: M + "prompting_techniques.py",
      blocks: [
        { type: "cards", size: 10.5, codeSize: 8.5, items: [
          { n: 0, title: "Zero-shot", tag: "Instruction only", lines: ["**Best for:** QA, summaries, translation, simple classification", "**Watch out:** inconsistent on complex tasks"],
            code: `Classify the sentiment:
"Arrived on time, works
perfectly."` },
          { n: 1, title: "One-shot", tag: "One example", lines: ["**Best for:** teaching a format or style", "**Watch out:** one example rarely covers every case"],
            code: `Review: Terrible phone.
→ Negative
Review: Arrived on time…
→ ?` },
          { n: "2+", title: "Few-shot", tag: "2–10 examples", lines: ["**Best for:** complex classification, extraction, structured output", "**Watch out:** longer prompts cost tokens and time"],
            code: `Excellent service. → Positive
Very slow delivery. → Negative
Damaged packaging. → Negative
Arrived on time… → ?` },
        ] },
      ],
    },
    {
      title: "Chain-of-Thought (CoT) Prompting",
      subtitle: "Ask the model to reason step by step before it answers – for logic, planning and multi-step maths",
      demo: M + "prompting_techniques.py",
      blocks: [
        { type: "text", text: "**Prompt:** A customer has a budget of $1,200 and needs a laptop for programming, machine learning and occasional gaming. Recommend the best option." },
        { type: "compare", size: 11, cols: [
          { title: "Without CoT", color: "slate", items: [
            "\"I recommend Laptop B because it offers the best balance of CPU, GPU, memory and price.\"",
            "Plausible – but we cannot see or check the reasoning",
          ] },
          { title: "With CoT: \"Reason step by step first\"", color: "teal", items: [
            "Budget limit is $1,200",
            "Programming needs a fast CPU and 16 GB+ RAM",
            "ML and gaming both need a dedicated GPU",
            "Laptop B: i7, 16 GB, RTX 4060, 1 TB SSD – $1,180",
            "**So:** Laptop B meets every requirement within budget",
          ] },
        ] },
      ],
    },
    { kind: "image", src: "tree_of_thought.png", alt: "Tree-of-Thought: explore several reasoning paths, evaluate them, keep the best", demo: M + "prompting_techniques.py" },
    {
      title: "ReAct Prompting",
      subtitle: "Reason + Act: alternate thinking with tool calls, and use each result to decide the next step",
      demo: M + "prompting_techniques.py",
      split: [1, 1.35],
      left: [
        { type: "text", text: "**User:** I have ₹10 lakh to invest for 10 years. Equity mutual fund, fixed deposit or balanced fund?" },
        { type: "chain", items: ["Question", "Thought", "Action", "Observation", "Thought", "Answer"], highlight: [2] },
      ],
      right: [
        { type: "steps", size: 10.5, titleSize: 11.5, gap: 0.09, items: [
          { n: "T", title: "Thought: I need the user's risk profile" },
          { n: "A", title: "Action: getCustomerProfile(id)", color: "navy" },
          { n: "O", title: "Observation: age 38, moderate risk, 10-year horizon", color: "teal" },
          { n: "T", title: "Thought: compare returns and risk of the options" },
          { n: "A", title: "Action: getInvestmentOptions([...])", color: "navy" },
          { n: "O", title: "Observation: equity 12% high · FD 7% low · balanced 10% medium", color: "teal" },
          { n: "✓", title: "Answer: a balanced fund suits a moderate risk profile over 10 years", color: "slate" },
        ] },
      ],
    },

    // ---------------------------------------------------------------- output, tools, tokens, eval
    {
      title: "Structured Output",
      subtitle: "Make the model return a predefined shape that code can rely on – not free text to parse",
      demo: M + "structured_output_investment_advisor.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "structured_output_investment_advisor.py (condensed)", code:
`class InvestmentRecommendation(BaseModel):
    risk_profile: Literal["Low", "Medium", "High"]
    recommended_product: str
    expected_return: float   # annual, in percent
    reason: str

response = client.responses.parse(
    model="gpt-4o-mini",
    input=[{"role": "system", "content": "You are a financial..."},
           {"role": "user", "content": customer_profile}],
    text_format=InvestmentRecommendation)

rec = response.output_parsed   # a validated object` },
      ],
      right: [
        { type: "callout", eyebrow: "Free text", text: "\"The customer's risk profile is moderate. A balanced fund is recommended because…\"" },
        { type: "code", caption: "Structured – rec.model_dump()", code:
`{"risk_profile": "Medium",
 "recommended_product": "Balanced Fund",
 "expected_return": 10.0,
 "reason": "Balanced growth, moderate risk"}` },
        { type: "text", size: 11, color: "slate", text: "Consistent responses, easy parsing, built-in validation, reliable integration with APIs and databases." },
      ],
    },
    {
      title: "Tool Calling with the Agents SDK",
      subtitle: "The LLM decides when to call a function and with what arguments; the SDK runs it",
      demo: M + "create_sales_db.py → " + M + "sales_db_agent.py",
      split: [1.2, 1],
      left: [
        { type: "chain", size: 10, items: ["Query", "Pick tool", "Args", "Run", "Answer"], highlight: [1, 2] },
        { type: "code", caption: "sales_db_agent.py (condensed)", code:
`@function_tool
def run_sql(query: str) -> str:
    """Execute a read-only SQL query on the sales database."""
    ...

agent = Agent(name="Sales Assistant", model="gpt-4o-mini",
    instructions="Use the run_sql tool whenever "
                 "database information is needed.",
    tools=[run_sql])
Runner.run_sync(agent, "Which products generated "
                       "more than ₹200,000 in revenue?")` },
      ],
      right: [
        { type: "text", text: "**Try other questions**", size: 12 },
        { type: "bullets", size: 10.5, items: [
          "What is the total revenue for Laptop?",
          "Which product sold the highest quantity?",
          "Show the top three products by revenue",
          "What was the total revenue in March 2026?",
          "What is the average revenue per sale?",
        ] },
        { type: "callout", eyebrow: "Careful", text: "The docstring says read-only, but nothing enforces it. Open the database read-only before giving an LLM SQL." },
      ],
    },
    {
      title: "Measuring Tokens with tiktoken",
      subtitle: "Count tokens before you send a request – to estimate cost, stay within limits and cut latency",
      demo: M + "tiktoken_tokenization_example.py, tiktoken_tokenization_hindi_example.py",
      split: [1.15, 1],
      left: [
        { type: "code", caption: "tiktoken_tokenization_example.py", code:
`import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4o-mini")

def show_tokens(text):
    tokens = encoding.encode(text)
    print(f"Number of tokens: {len(tokens)}")
    for token_id in tokens:
        print(token_id, "->",
              repr(encoding.decode([token_id])))` },
      ],
      right: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaIndianRupeeSign", title: "Estimate cost", text: "Providers bill input and output tokens" },
          { icon: "FaWindowMaximize", title: "Stay within the window", text: "Trim or chunk before you hit the limit" },
          { icon: "FaLanguage", title: "Language matters", text: "The Hindi example needs many more tokens for the same meaning" },
        ] },
      ],
    },
    {
      title: "Evaluating LLM Output",
      subtitle: "The same input can give different outputs – so measure quality systematically before you deploy",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.5, 3.2, 3.3], head: ["Metric", "Question it answers", "Example"], rows: [
          ["Accuracy", "Is the answer factually correct?", "Is the investment advice correct?"],
          ["Relevance", "Does it answer the question asked?", "Did it address the actual query?"],
          ["Completeness", "Are all required points covered?", "Were all symptoms addressed?"],
          ["Consistency", "Are similar questions answered alike?", "Do repeat queries give similar advice?"],
          ["Safety", "Does it avoid harmful or biased content?", "Does it refuse unsafe requests?"],
          ["Latency", "How quickly does it respond?", "Is the response time acceptable?"],
          ["Cost", "How many tokens does it use?", "Is the application economical?"],
        ] },
        { type: "text", size: 11, color: "slate", text: "Module 09 (LangSmith) and Module 14 (RAGAS) turn these into automated evaluations." },
      ],
    },
    {
      kind: "summary",
      title: "Module 03 Summary",
      subtitle: "What you built",
      built: [
        { tag: "API", title: "Three providers", text: "OpenAI, Anthropic and a local Ollama model" },
        { tag: "prompt", title: "Prompting patterns", text: "Personas, few-shot, CoT, ToT and ReAct on one use case" },
        { tag: "JSON", title: "Structured output", text: "A Pydantic investment recommendation" },
        { tag: "tool", title: "A tool-calling agent", text: "Natural-language questions over a sales database" },
      ],
      takeaways: [
        "An LLM predicts the next token from everything in its context",
        "The context window is a budget – count tokens",
        "Use the smallest model that does the job well",
        "Prompt structure (role, rules, format) drives quality",
        "Ask for structured output whenever code consumes the answer",
      ],
      next: "Module 04: Embeddings, Vector Databases and Semantic Search",
    },
  ],
};
