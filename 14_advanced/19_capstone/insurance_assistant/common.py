"""Shared settings for the Insurance Policy Assistant capstone.

Every numbered script in this folder runs on its own; this file only holds the
paths, the "logged-in customer" session, and two small helpers they all share.
"""
import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
load_dotenv(os.path.join(REPO_ROOT, ".env"), override=True)

DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")
CUSTOMER_DB = os.path.join(DATA_DIR, "customers.db")        # "SQL Database" box in the diagram
INSURANCE_API_DB = os.path.join(DATA_DIR, "insurance_api.db")  # owned by the Insurance API only
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
QUESTIONS_FILE = os.path.join(DATA_DIR, "demo_questions.json")

COLLECTION = "insurance_docs"
MODEL = "gpt-4o-mini"

INSURANCE_API_PORT = 8020      # 19_7_api.py in the parent folder already uses 8019
INSURANCE_API_URL = f"http://localhost:{INSURANCE_API_PORT}"
APP_PORT = 5020                # the Flask app in step 10

# The demo "login". In a real app this comes from the login session, never from the chat.
DEMO_CUSTOMERS = {
    "C67890": "Rahul Mehta",
    "C11111": "Priya Nair",
}
DEFAULT_CUSTOMER = "C67890"


@dataclass
class CustomerSession:
    """Passed to every run as the Agents SDK 'context'. Tools read the customer id
    from here, so the LLM never decides WHOSE data is read."""
    customer_id: str = DEFAULT_CUSTOMER
    customer_name: str = DEMO_CUSTOMERS[DEFAULT_CUSTOMER]
    user_input: str = ""                                    # filled by step 8 (output grounding check)
    tool_outputs: list[str] = field(default_factory=list)  # filled by step 8's run hooks


def session_for(customer_id: str) -> CustomerSession:
    return CustomerSession(customer_id=customer_id, customer_name=DEMO_CUSTOMERS.get(customer_id, customer_id))


def load_step(filename: str):
    """Import a sibling script such as '3_tool_sql.py' as a module.
    (File names that start with a digit can't be used in a normal import.)"""
    name = "insurance_" + os.path.splitext(filename)[0]
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(BASE_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def tool_output_text(output) -> str:
    """A tool result as plain text. MCP tool results arrive wrapped as {"type": "text", "text": ...}."""
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except ValueError:
            return output
    parts = output if isinstance(output, list) else [output]
    if parts and all(isinstance(p, dict) and p.get("type") in ("text", "input_text") for p in parts):
        return "\n".join(p["text"] for p in parts)
    return json.dumps(output)


def print_trace(result, start: int = 0) -> None:
    """Print what the agent did: every tool call, its result, and the final answer.
    start: skip items already printed (used after resuming a paused run)."""
    for item in result.new_items[start:]:
        if item.type == "tool_call_item":
            raw = item.raw_item
            name = getattr(raw, "name", None) or raw.get("name")
            args = getattr(raw, "arguments", None) or raw.get("arguments")
            print(f"  -> TOOL CALL   {name}({args})")
        elif item.type == "tool_call_output_item":
            text = " ".join(tool_output_text(item.output).split())
            print(f"  <- TOOL RESULT {text[:220]}{'...' if len(text) > 220 else ''}")
        elif item.type == "tool_approval_item":
            print(f"  || PAUSED      {item.name}({item.arguments}) is waiting for a human")
    if result.final_output is not None:
        print(f"\nASSISTANT: {result.final_output}")
