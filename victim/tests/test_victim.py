"""VictimBot tests. Gemini is mocked — tests never hit the real API."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_normal(monkeypatch):
    monkeypatch.setattr(main, "generate", lambda m: "TechCo's router supports WiFi 6.")
    r = client.post("/chat", json={"message": "Does the router support WiFi 6?"})
    assert r.status_code == 200
    assert r.json()["response"]  # non-empty


def test_chat_empty_message():
    r = client.post("/chat", json={"message": "   "})
    assert r.status_code == 422


def test_chat_missing_message():
    r = client.post("/chat", json={})
    assert r.status_code == 422
