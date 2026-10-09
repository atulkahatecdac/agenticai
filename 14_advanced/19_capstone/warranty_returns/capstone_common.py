"""Shared settings for the Module 19 capstone (Warranty & Returns Resolution Assistant).

Every numbered script in this folder runs on its own; this file only holds the
paths, business limits and the small helper they all share.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
POLICY_DIR = os.path.join(DATA_DIR, "policies")
ORDERS_DB = os.path.join(DATA_DIR, "orders.db")
TICKETS_FILE = os.path.join(DATA_DIR, "test_tickets.json")
META_FILE = os.path.join(DATA_DIR, "meta.json")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
CHECKPOINT_DB = os.path.join(DATA_DIR, "checkpoints.db")
APPROVAL_LOG = os.path.join(DATA_DIR, "approval_requests.log")

COLLECTION = "policies"
POLICY_VERSION = "2026-01"

# Business limits - the same numbers the policy PDFs state in words.
REFUND_APPROVAL_LIMIT = 5000      # refunds above this need a human
REPAIR_PRICE_THRESHOLD = 10000    # above this, in-warranty defects are repaired, not replaced
MAX_REVIEW_LOOPS = 2

API_PORT = 8019
API_URL = f"http://localhost:{API_PORT}"


def today() -> date:
    """The demo clock. Sample orders are dated relative to the day the data was
    generated, so every script uses THAT day as 'today' - otherwise a ticket that
    is 'inside the 10-day return window' would silently expire a week later."""
    with open(META_FILE, encoding="utf-8") as f:
        return date.fromisoformat(json.load(f)["as_of_date"])


def load_step(filename: str):
    """Import a sibling script such as '19_5_guardrails.py' as a module.
    (File names that start with a digit can't be used in a normal import.)"""
    name = "capstone_" + os.path.splitext(filename)[0]
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(BASE_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def quiet_langgraph_import():
    """langgraph prints a LangChain 'allowed_objects' deprecation notice the first
    time its checkpoint module is imported, and re-enables that warning itself, so
    warnings.filterwarnings() cannot hide it. Import it once with stderr muted to
    keep demo output clean. Call this BEFORE any other langgraph import."""
    with contextlib.redirect_stderr(io.StringIO()):
        import langgraph.checkpoint.base  # noqa: F401
