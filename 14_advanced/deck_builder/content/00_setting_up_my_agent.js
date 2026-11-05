// Hands-on setup before Module 01: students fork the repo, start a fresh uv
// project on a scratch branch, and make a first LangChain call. There is no
// demo script in the repo for this section, so DEMO lines name the terminal
// command or the student's own main.py.
const MAIN = "Your project: main.py  ·  uv run main.py";

module.exports = {
  section: "Setting Up My Agent",
  slides: [
    {
      kind: "opener",
      eyebrow: "Before Module 01",
      title: "Setting Up My Agent",
      subtitle: "From a GitHub account to a working LangChain call – on OpenAI and on a local model",
      goals: [
        { icon: "FaCodeFork", title: "Your own copy of the course repo", text: "Fork, clone and a scratch branch to play in" },
        { icon: "FaBoxOpen", title: "A fresh Python project with uv", text: "uv init, uv add, uv run" },
        { icon: "FaKey", title: "API keys kept out of git", text: ".env, python-dotenv and a proper .gitignore" },
        { icon: "FaRobot", title: "A first LLM call", text: "A LangChain chain on OpenAI, then on Ollama" },
      ],
      agenda: [
        "Fork and clone the repo",
        "A scratch branch to experiment in",
        "Install uv",
        "Create the project and add packages",
        "Keep the API key in .env",
        "Read the key from code",
        "Your first LangChain chain",
        "Run it locally with Ollama",
      ],
    },
    {
      title: "Fork and Clone the Repo",
      subtitle: "A fork is your own copy on GitHub – you can push to it without touching the original",
      demo: "Browser: github.com/atulkahatecdac/agenticai  ·  then a terminal",
      split: [1, 1.1],
      left: [
        { type: "steps", size: 11, items: [
          { title: "Create a GitHub account", text: "github.com – free" },
          { title: "Open the course repo", text: "github.com/atulkahatecdac/agenticai" },
          { title: "Click Fork", text: "Keep the defaults and create the fork" },
          { title: "On your fork: Code → HTTPS", text: "Copy the URL" },
        ] },
      ],
      right: [
        { type: "code", caption: "Terminal (CMD or PowerShell)", code:
`cd C:\\
git clone https://github.com/YOUR_USERNAME/agenticai
cd agenticai` },
        { type: "callout", eyebrow: "Replace", text: "`YOUR_USERNAME` with your GitHub user name – or just paste the URL you copied." },
      ],
    },
    {
      title: "A Scratch Branch to Experiment In",
      subtitle: "An orphan branch starts empty, with no history – a clean folder for your own project",
      demo: "Terminal: git switch --orphan test-agent  ·  git status",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "Create it", code:
`git switch --orphan test-agent
git status
# On branch test-agent
# No commits yet` },
        { type: "callout", eyebrow: "Why git status?", text: "Until the first commit, `git branch` does not list test-agent at all – `git status` shows the branch you are on." },
      ],
      right: [
        { type: "code", caption: "Delete it later", code:
`git add -A
git commit -m "My first agent"
git switch main
git branch -D test-agent` },
        { type: "text", size: 11, text: "Commit first: your new README.md and .gitignore clash with the ones on main, so `git switch main` refuses while they are uncommitted." },
      ],
    },
    {
      title: "Install uv",
      subtitle: "One fast tool for Python versions, virtual environments and packages",
      demo: "Terminal: uv --version",
      blocks: [
        { type: "code", caption: "Check whether it is already installed", code: `uv --version` },
        { type: "code", caption: "If not: install it (works from CMD and PowerShell)", code:
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` },
        { type: "steps", size: 11, items: [
          { title: "Close and reopen the terminal", text: "so it picks up the new PATH" },
          { title: "Check again", text: "uv --version should now print a version number" },
        ] },
      ],
    },
    {
      title: "Create the Project",
      subtitle: "uv init writes the project files; uv add installs packages and creates the .venv",
      demo: "Terminal: uv init  ·  uv add …  ·  uv run main.py",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "Inside the agenticai folder", code:
`uv init                  # main.py, pyproject.toml
uv add langchain langchain-core
uv add langchain-openai  # OpenAI models
uv add python-dotenv     # reads .env
uv run main.py` },
        { type: "callout", eyebrow: "No activate needed", text: "`uv run` always uses the project's .venv. Activate it only to run plain `python`." },
      ],
      right: [
        { type: "table", size: 10.5, widths: [1.5, 2.3], head: ["Shell", "Activate .venv"], rows: [
          ["CMD", ".venv\\Scripts\\activate"],
          ["PowerShell", ".venv\\Scripts\\Activate.ps1"],
        ] },
        { type: "code", caption: "If PowerShell blocks Activate.ps1", code: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` },
      ],
    },
    {
      title: "Keep the API Key in .env",
      subtitle: "The key lives in a file git ignores – never in the code",
      demo: "Project folder: .gitignore and .env",
      blocks: [
        { type: "code", caption: "1. Get GitHub's standard Python .gitignore", code:
`curl.exe -o .gitignore https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore` },
        { type: "cols", gap: 0.4, cols: [
          [
            { type: "callout", eyebrow: "PowerShell", text: "Type `curl.exe`, not `curl` – in Windows PowerShell, `curl` is an alias for Invoke-WebRequest." },
          ],
          [
            { type: "code", caption: "2. Create .env", code: `OPENAI_API_KEY=sk-...your key...` },
            { type: "icons", d: 0.36, size: 11, items: [
              { icon: "FaFileShield", title: "Already ignored", text: "Python.gitignore lists .env, so the key never reaches GitHub" },
              { icon: "FaTriangleExclamation", title: "Name it exactly .env", text: "Notepad may save .env.txt – choose 'All files'", color: "coral" },
            ] },
          ],
        ] },
      ],
    },
    {
      title: "Read the Key from Code",
      subtitle: "load_dotenv() copies .env into the environment; os.environ reads it back",
      demo: MAIN,
      split: [1.25, 1],
      left: [
        { type: "code", caption: "main.py", code:
`from dotenv import load_dotenv
import os

load_dotenv()


def main():
    print("Hello from AI Agents!")
    api_key = os.environ.get("OPENAI_API_KEY")

    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:]
        print("OPENAI_API_KEY:", masked)
    else:
        print("OPENAI_API_KEY not found!")


if __name__ == "__main__":
    main()` },
      ],
      right: [
        { type: "code", caption: "Output", code:
`Hello from AI Agents!
OPENAI_API_KEY: sk-proj-...a1B2` },
        { type: "callout", eyebrow: "Print a mask", text: "Show only the first and last few characters – enough to check it loaded, never the whole key." },
      ],
    },
    {
      title: "Your First LangChain Chain",
      subtitle: "A prompt template piped into a model: summarize a biography and pull out two facts",
      demo: MAIN,
      split: [1.35, 1],
      left: [
        { type: "code", caption: "main.py", code:
`from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

information = """Geoffrey Hinton is a British-Canadian computer
scientist, a pioneer of deep learning ... (paste a full bio)"""

summary_template = """Given the information {information}
about a person, I want you to create:
1. A short summary
2. Two interesting facts about them"""

prompt = PromptTemplate.from_template(summary_template)
llm = ChatOpenAI(model="gpt-5")

chain = prompt | llm
response = chain.invoke({"information": information})
print(response.content)` },
      ],
      right: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaFileLines", title: "PromptTemplate", text: "Text with an {information} slot to fill" },
          { icon: "FaRobot", title: "ChatOpenAI", text: "The model, configured once" },
          { icon: "FaLink", title: "prompt | llm", text: "A chain: the filled prompt flows into the model" },
        ] },
        { type: "callout", eyebrow: "gpt-5", text: "Leave out `temperature=0` – gpt-5 accepts only the default and rejects any other value." },
      ],
    },
    {
      title: "Run It Locally with Ollama",
      subtitle: "Same chain, a model on your own machine – no API key, no cost per call",
      demo: "ollama.com  ·  ollama pull qwen3:8b  ·  uv run main.py",
      split: [1, 1.1],
      left: [
        { type: "code", caption: "Terminal", code:
`ollama --version
ollama pull qwen3:8b
ollama list
ollama run qwen3:8b   # /bye to exit
uv add langchain-ollama` },
        { type: "text", size: 11, text: "Install Ollama first from **ollama.com**. qwen3:8b is about 5 GB; on a small laptop try `qwen3:1.7b`." },
      ],
      right: [
        { type: "code", caption: "main.py – swap the model", code:
`from langchain_ollama import ChatOllama

# llm = ChatOpenAI(model="gpt-5")
llm = ChatOllama(model="qwen3:8b", temperature=0)` },
        { type: "callout", eyebrow: "Nothing else changes", text: "The prompt and the chain stay the same – LangChain hides which provider answers." },
      ],
    },
    {
      kind: "summary",
      title: "Setup Summary",
      subtitle: "What you set up",
      built: [
        { tag: "git", title: "Your fork and a scratch branch", text: "Clone of your fork, test-agent to experiment in" },
        { tag: "uv", title: "A uv project", text: "pyproject.toml, .venv, LangChain packages" },
        { tag: ".env", title: "A key kept out of git", text: "Loaded with python-dotenv, ignored by .gitignore" },
        { tag: "LLM", title: "A working chain", text: "On OpenAI and on a local Ollama model" },
      ],
      takeaways: [
        "Fork to get your own copy you can push to",
        "uv init, uv add, uv run – no manual pip or activate",
        "Keys go in .env, and .env goes in .gitignore",
        "A chain is a prompt piped into a model",
        "Switching providers is a one-line change",
      ],
      next: "Module 01: Python & AI Dev Environment",
    },
  ],
};
