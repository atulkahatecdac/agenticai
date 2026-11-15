"""Tests for the API - no OpenAI key or network needed.

dependency_overrides swaps the real LLM for a fake one that returns canned replies.
This is the main payoff of Depends(): the endpoints don't change, only what they are given.

Run from 14_advanced/02_fastapi_production:
    pytest -q test_api.py
"""
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.dependencies import get_llm
from app.main import app

fake_llm = FakeListChatModel(responses=["- point one\n- point two\n- point three"])
app.dependency_overrides[get_llm] = lambda: fake_llm
client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_uses_the_injected_llm():
    r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json()["reply"].startswith("- point one")


def test_chat_validates_the_body():
    assert client.post("/chat", json={"message": ""}).status_code == 422   # min_length=1


def test_stream_sends_sse_lines():
    r = client.post("/chat/stream", json={"message": "hi"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.text.strip().endswith("data: [DONE]")


def test_upload_a_text_file():
    files = {"file": ("note.txt", b"Refunds take 5 days. Returns within 30 days.", "text/plain")}
    r = client.post("/documents/summarize", files=files)
    assert r.status_code == 200
    assert r.json()["filename"] == "note.txt"
    assert r.json()["characters"] > 0


def test_wrong_file_type_is_rejected():
    files = {"file": ("photo.png", b"\x89PNG", "image/png")}
    assert client.post("/documents/summarize", files=files).status_code == 415
