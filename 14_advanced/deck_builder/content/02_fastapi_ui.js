const ST = "02_streamlit_fastapi/";
const GR = "02_gradio_fastapi/";

module.exports = {
  section: "Module 02 – FastAPI, Streamlit and Gradio",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 02",
      title: "FastAPI, Streamlit and Gradio for AI Apps",
      subtitle: "Expose an LLM or agent as a REST API, stream its output, and put a web front end on it",
      goals: [
        { icon: "FaServer", title: "Understand REST APIs", text: "methods, status codes and the request/response lifecycle" },
        { icon: "FaBolt", title: "Serve LLM calls with FastAPI", text: "Pydantic models, async endpoints, SSE streaming" },
        { icon: "FaWindowMaximize", title: "Build quick front ends", text: "Streamlit and Gradio, with chat history" },
        { icon: "FaLayerGroup", title: "Wire front end to back end", text: "a UI calling a FastAPI service over HTTP" },
      ],
      agenda: [
        "REST API fundamentals",
        "FastAPI: endpoints, Pydantic, LLM calls",
        "FastAPI with asyncio",
        "Streaming with Server-Sent Events",
        "Streamlit apps and chat history",
        "Gradio apps and sharing them",
        "Streamlit / Gradio front end + FastAPI back end",
      ],
    },
    {
      title: "REST APIs: How Agents Reach Everything",
      subtitle: "A standard way for applications to talk to each other over HTTP",
      demo: "Concept",
      split: [1, 1.15],
      left: [
        { type: "text", text: "**AI applications use REST APIs to:**", size: 12 },
        { type: "bullets", size: 11.5, items: [
          "Call LLM services (OpenAI, Anthropic, Gemini)",
          "Read data from databases",
          "Run web searches",
          "Send emails and notifications",
          "Reach MCP gateways and business services",
        ] },
      ],
      right: [
        { type: "table", size: 10.5, widths: [0.9, 1.8, 2.2], head: ["Method", "Purpose", "Example"], rows: [
          ["GET", "Retrieve data", "GET /patients/1001"],
          ["POST", "Create a resource", "POST /appointments"],
          ["PUT", "Replace a resource", "PUT /patients/1001"],
          ["PATCH", "Partially update", "Change a phone number"],
          ["DELETE", "Remove a resource", "DELETE /appointments/25"],
        ] },
        { type: "chain", size: 10, items: ["Agent", "HTTP request", "API server", "JSON"], highlight: [2] },
      ],
    },
    {
      title: "REST Calls Inside an Agent",
      subtitle: "One user question can fan out into several API calls before the agent answers",
      demo: "Concept",
      blocks: [
        { type: "tree", boxW: 1.95, size: 10.5, rows: [
          ["User query"],
          [{ label: "AI agent", fill: "navy" }],
          ["GET patient details", "POST insurance claim", "GET treatment history", "POST email notification"],
          [{ label: "Combine results → final response", fill: "teal" }],
        ] },
      ],
    },
    {
      title: "FastAPI",
      subtitle: "A Python framework for building REST APIs – expose a function, an LLM call or a whole agent over HTTP",
      demo: GR + "main.py  ·  uvicorn main:app --reload",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaPlug", title: "Other apps call your Python", text: "Any client that speaks HTTP can use the agent" },
          { icon: "FaCircleCheck", title: "Request validation", text: "Pydantic checks every request body" },
          { icon: "FaBook", title: "Docs for free", text: "Interactive API docs at `/docs`" },
        ] },
        { type: "chain", size: 10, items: ["Client", "FastAPI", "Agent / LLM"], highlight: [1] },
      ],
      right: [
        { type: "code", caption: "main.py – the smallest app", code:
`from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello FastAPI!"}` },
        { type: "code", caption: "Run it", code:
`pip install fastapi uvicorn
uvicorn main:app --reload
# http://127.0.0.1:8000/       the response
# http://127.0.0.1:8000/docs   interactive docs` },
      ],
    },
    {
      title: "Accepting Input and Calling an LLM",
      subtitle: "A Pydantic model describes the request body; FastAPI validates it before your code runs",
      demo: GR + "backend.py",
      split: [1.25, 1],
      left: [
        { type: "code", caption: "backend.py – POST /chat", code:
`from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()
client = OpenAI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest):
    response = client.responses.create(
        model="gpt-4o-mini",
        input=request.message)
    return {"reply": response.output_text}` },
      ],
      right: [
        { type: "text", text: "**Pydantic** validates, parses and serialises data using Python type hints – no hand-written checks.", size: 11.5 },
        { type: "code", caption: "Test body (from /docs)", code:
`{
  "message": "What is FastAPI used for?"
}` },
        { type: "callout", eyebrow: "Bad input?", text: "A missing or wrongly typed field is rejected with a 422 error – the LLM is never called." },
      ],
    },
    {
      title: "FastAPI with asyncio",
      subtitle: "An async endpoint can run several LLM calls at once – three analyses for the price of the slowest",
      demo: GR + "main.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "main.py", code:
`client = AsyncOpenAI()

async def ask(prompt):
    r = await client.responses.create(
        model="gpt-4o-mini", input=prompt)
    return r.output_text

@app.post("/analyze")
async def analyze(text: str):
    summary, keywords, sentiment = await asyncio.gather(
        ask("Summarize: " + text),
        ask("Extract five keywords: " + text),
        ask("Determine sentiment: " + text))
    return {"summary": summary, "keywords": keywords,
            "sentiment": sentiment}` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Start the server", text: "`uvicorn main:app --reload`" },
          { title: "Open /docs", text: "Expand POST /analyze → Try it out" },
          { title: "Paste some text", text: "\"Python is easy to learn. It is widely used in data science and AI.\"" },
          { title: "Read three results", text: "Summary, keywords and sentiment – fetched concurrently" },
        ] },
      ],
    },
    {
      title: "Streaming with Server-Sent Events",
      subtitle: "Send tokens to the client as they are generated instead of waiting for the whole answer",
      demo: "Concept",
      split: [1, 1.2],
      left: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaGaugeHigh", title: "Feels faster", text: "Users start reading immediately" },
          { icon: "FaComments", title: "Made for chat", text: "And for long-running answers" },
          { icon: "FaArrowRight", title: "SSE", text: "One-way server → client updates over one plain HTTP connection" },
        ] },
      ],
      right: [
        { type: "code", caption: "An async generator that yields SSE events", code:
`client = AsyncOpenAI()

async def stream_llm(prompt):
    stream = await client.responses.create(
        model="gpt-5", input=prompt, stream=True)
    async for event in stream:
        if event.type == "response.output_text.delta":
            yield f"data: {event.delta}\\n\\n"` },
        { type: "text", size: 11, color: "slate", text: "`stream=True` makes OpenAI respond at once; `yield` returns one chunk, pauses and resumes – `return` would end after the first." },
      ],
    },

    // ---------------------------------------------------------------- Streamlit
    {
      title: "Streamlit",
      subtitle: "Interactive web apps in pure Python – no HTML, CSS or JavaScript",
      demo: ST + "frontend.py  ·  streamlit run frontend.py",
      split: [1, 1.15],
      left: [
        { type: "bullets", size: 11.5, items: [
          "Demo LLM apps and agent prototypes quickly",
          "Text inputs, buttons, chat widgets, tables, status indicators",
          "The whole script re-runs on every interaction – keep state in `st.session_state`",
        ] },
        { type: "code", caption: "Run", code: `streamlit run app.py` },
      ],
      right: [
        { type: "code", caption: "app.py – ask an LLM", code:
`import streamlit as st
from openai import OpenAI

client = OpenAI()
st.title("AI Helpdesk Assistant")
question = st.text_input("Enter your question")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Generating answer..."):
            r = client.responses.create(
                model="gpt-4.1-mini", input=question)
        st.markdown(r.output_text)` },
      ],
    },
    {
      title: "A Streamlit Chat with History",
      subtitle: "session_state survives the re-runs, so the conversation stays on screen",
      demo: "03_llm_examples/ollama_chatbot_streamlit.py",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "app.py", code:
`if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:          # redraw history
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if question := st.chat_input("Ask a question"):
    st.session_state.messages.append(
        {"role": "user", "content": question})
    st.chat_message("user").markdown(question)
    answer = client.responses.create(
        model="gpt-4.1-mini", input=question).output_text
    st.session_state.messages.append(
        {"role": "assistant", "content": answer})
    st.chat_message("assistant").markdown(answer)` },
      ],
      right: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaDatabase", title: "st.session_state", text: "Per-browser-tab storage that outlives each re-run" },
          { icon: "FaComment", title: "st.chat_input", text: "The chat box pinned to the bottom" },
          { icon: "FaComments", title: "st.chat_message", text: "A bubble for the user or the assistant" },
        ] },
        { type: "callout", eyebrow: "Note", text: "This sends only the latest question. To give the LLM memory, pass the whole message list as input." },
      ],
    },

    // ---------------------------------------------------------------- Gradio
    {
      title: "Gradio",
      subtitle: "Wrap a Python function in a browser UI – text, chat, images, audio and files",
      demo: GR + "frontend.py  (pip install -r " + GR + "requirements.txt)",
      blocks: [
        { type: "compare", size: 11, codeSize: 9, cols: [
          { title: "gr.Interface – one function, one form", color: "navy", code:
`def answer_question(question):
    return client.responses.create(
        model="gpt-4.1-mini",
        input=question).output_text

gr.Interface(fn=answer_question,
    inputs=gr.Textbox(label="Ask", lines=3),
    outputs=gr.Textbox(label="Answer"),
    title="AI Helpdesk Assistant").launch()` },
          { title: "gr.ChatInterface – a chat UI", color: "teal", code:
`def chat(message, history):
    return client.responses.create(
        model="gpt-4.1-mini",
        input=message).output_text

gr.ChatInterface(fn=chat,
    title="AI Helpdesk Assistant").launch()` },
        ] },
        { type: "callout", eyebrow: "Own requirements", text: "Gradio isn't in the repo-wide requirements.txt – install it from this demo's own requirements.txt." },
      ],
    },
    {
      title: "Sharing a Gradio Demo",
      subtitle: "Let people try your app in a browser without installing Python",
      demo: "Concept",
      split: [1, 1.2],
      left: [
        { type: "icons", d: 0.36, size: 11, items: [
          { icon: "FaLink", title: "Temporary public link", text: "`demo.launch(share=True)` – a URL that lasts while your app runs" },
          { icon: "FaCloud", title: "Hugging Face Spaces", text: "Free hosting for public Gradio apps" },
          { icon: "FaComments", title: "Why share", text: "Showcase work, collect feedback, no servers to manage" },
        ] },
      ],
      right: [
        { type: "steps", size: 10.5, gap: 0.1, items: [
          { title: "Create a Space", text: "huggingface.co → Spaces → New space → SDK: Gradio" },
          { title: "Clone it", text: "`git clone https://huggingface.co/spaces/<user>/<space>`" },
          { title: "Add app.py (and requirements.txt)" },
          { title: "Push", text: "`git add .` · `git commit -m \"Initial app\"` · `git push`" },
          { title: "Open the Space", text: "It builds and goes live within a minute or so" },
        ] },
      ],
    },
    {
      title: "Front End + Back End",
      subtitle: "The common architecture: a thin UI calling a FastAPI service that does the real work",
      demo: ST + "backend.py + frontend.py  ·  " + GR + "backend.py + frontend.py",
      blocks: [
        { type: "flow", items: [
          { icon: "FaUser", label: "User", caption: "In the browser" },
          { icon: "FaWindowMaximize", label: "Streamlit / Gradio", caption: "Front end" },
          { icon: "FaArrowRightArrowLeft", label: "HTTP request", caption: "JSON over REST" },
          { icon: "FaServer", label: "FastAPI", caption: "Back end", color: "coral" },
          { icon: "FaGears", label: "LLM + logic", caption: "Database, files, tools", color: "teal" },
        ] },
        { type: "cols", cols: [
          [{ type: "code", caption: "Streamlit version", code:
`cd 14_advanced/02_streamlit_fastapi
uvicorn backend:app --reload     # terminal 1
streamlit run frontend.py        # terminal 2` }],
          [{ type: "code", caption: "Gradio version", code:
`cd 14_advanced/02_gradio_fastapi
uvicorn backend:app --reload     # terminal 1
python frontend.py               # terminal 2` }],
        ] },
      ],
    },
    {
      title: "Streamlit or Gradio?",
      subtitle: "Both are quick; they are good at different things",
      demo: "Concept",
      blocks: [
        { type: "table", size: 10.5, widths: [1.8, 2.9, 2.9], head: ["", "Streamlit", "Gradio"], rows: [
          ["Primary purpose", "Data apps and dashboards", "AI/ML demos and chat interfaces"],
          ["Learning curve", "Easy", "Very easy"],
          ["Layout", "Highly customisable", "Simple and predefined"],
          ["Best for", "Dashboards, analytics, business apps", "LLMs, image generation, speech, ML models"],
          ["Chat interface", "Available", "Excellent, built in"],
          ["Data visualisation", "Excellent", "Basic"],
          ["Deployment", "Streamlit Cloud, Docker", "Hugging Face Spaces, Docker"],
          ["Typical users", "Data scientists, analysts", "AI/ML engineers, researchers"],
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 02 Summary",
      subtitle: "What you built",
      built: [
        { tag: "API", title: "An LLM behind FastAPI", text: "Pydantic request models, auto-generated /docs" },
        { tag: "async", title: "Concurrent endpoint", text: "Summary, keywords and sentiment in one gather()" },
        { tag: "SSE", title: "Streaming", text: "Tokens yielded to the client as they arrive" },
        { tag: "UI", title: "Two front ends", text: "Streamlit and Gradio calling the same back end" },
      ],
      takeaways: [
        "REST is how agents reach almost every external system",
        "FastAPI + Pydantic: validated input before any LLM call",
        "Use async endpoints when one request makes several calls",
        "Stream long answers – perceived speed matters",
        "Keep the UI thin; put logic in the back end",
      ],
      next: "Module 03: LLM Fundamentals, Context and Prompt Engineering",
    },
  ],
};
