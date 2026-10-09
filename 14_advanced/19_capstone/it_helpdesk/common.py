"""Shared settings for the IT Helpdesk Copilot capstone.

Everything runs locally: Ollama for the LLM and embeddings, Chroma for the
knowledge base, SQLite for the helpdesk data. Each numbered script runs on its
own; this file only holds paths, the model choice and two tiny helpers.
"""
import contextlib
import importlib.util
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")   # LLM replies may contain emoji; Windows consoles default to cp1252

# langgraph prints an 'allowed_objects' deprecation notice on first import that
# filterwarnings cannot hide (it re-enables it itself) - import it once quietly.
with contextlib.redirect_stderr(io.StringIO()):
    import langgraph.checkpoint.base  # noqa: F401

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
KB_DIR = os.path.join(DATA_DIR, "kb")
HELPDESK_DB = os.path.join(DATA_DIR, "helpdesk.db")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
CHECKPOINT_DB = os.path.join(DATA_DIR, "checkpoints.db")
NOTIFY_LOG = os.path.join(DATA_DIR, "notifications.log")
TEST_REQUESTS = os.path.join(DATA_DIR, "test_requests.json")

# qwen3:8b follows tool-calling and JSON-schema instructions reliably.
# llama3.2 (3B) is faster but makes more routing mistakes - try both!
CHAT_MODEL = os.getenv("HELPDESK_MODEL", "qwen3:8b")
EMBED_MODEL = "nomic-embed-text"
COLLECTION = "it_kb"

FLASK_PORT = 5021


def get_llm(temperature: float = 0):
    # reasoning=False switches off qwen3's long "thinking" output - faster, and
    # the answer arrives in .content instead of being mixed with the thoughts.
    return ChatOllama(model=CHAT_MODEL, temperature=temperature, reasoning=False)


def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=OllamaEmbeddings(model=EMBED_MODEL),
        persist_directory=CHROMA_DIR,
    )


# The two MCP servers, launched as subprocesses over stdio by
# langchain-mcp-adapters' MultiServerMCPClient.
MCP_SERVERS = {
    "helpdesk": {
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "3_mcp_helpdesk_server.py")],
        "transport": "stdio",
    },
    "identity": {
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "4_mcp_identity_server.py")],
        "transport": "stdio",
    },
}


def load_step(filename: str):
    """Import a sibling script such as '6_guardrails.py' as a module.
    (File names that start with a digit can't be used in a normal import.)"""
    name = "helpdesk_" + os.path.splitext(filename)[0]
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(BASE_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
