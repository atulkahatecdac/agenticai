"""Run by CI on every push - no API key, no network (the LLM is a fake)."""
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.main import app, get_llm


def client_with_fake_llm(reply: str = "Refunds take 5-7 days.") -> TestClient:
    app.dependency_overrides[get_llm] = lambda: FakeListChatModel(responses=[reply])
    return TestClient(app)


def test_health_and_ready():
    with TestClient(app) as c:                       # "with" runs the lifespan startup
        assert c.get("/health").json() == {"status": "ok"}
        assert c.get("/ready").json()["status"] == "ready"


def test_ask_returns_answer_and_version():
    with client_with_fake_llm() as c:
        r = c.post("/ask", json={"question": "How long do refunds take?"})
        assert r.status_code == 200
        assert r.json()["answer"] == "Refunds take 5-7 days."
        assert "version" in r.json()


def test_ask_rejects_bad_input():
    with client_with_fake_llm() as c:
        assert c.post("/ask", json={"question": "hi"}).status_code == 422      # too short
        assert c.post("/ask", json={}).status_code == 422


def test_no_key_means_503_not_a_crash(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    with TestClient(app) as c:
        assert c.post("/ask", json={"question": "anything?"}).status_code == 503


def test_secret_is_read_from_a_file(tmp_path, monkeypatch):
    from app.config import secret
    key_file = tmp_path / "openai_api_key"
    key_file.write_text("sk-from-file\n")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(key_file))
    assert secret("OPENAI_API_KEY") == "sk-from-file"          # the file wins over the variable
