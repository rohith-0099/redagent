"""Target adapter tests — TargetConfig + presets + generalized TargetClient.

All httpx traffic mocked via MockTransport. No real network.
"""

import asyncio

import httpx
import pytest

from core.contracts import Preset, TargetConfig
from tools.target_client import (
    TargetClient,
    TargetError,
    _extract,
    _substitute,
)
from tools.target_client import test_connection as probe_connection


def _client(config, handler) -> TargetClient:
    return TargetClient(config=config, transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# {{PROMPT}} substitution
# ---------------------------------------------------------------------------

def test_substitute_flat():
    assert _substitute({"message": "{{PROMPT}}"}, "hi") == {"message": "hi"}


def test_substitute_nested_and_lists():
    template = {"messages": [{"role": "user", "content": "{{PROMPT}}"}]}
    assert _substitute(template, "attack") == {
        "messages": [{"role": "user", "content": "attack"}]
    }


def test_substitute_leaves_non_strings():
    template = {"model": "x", "n": 1, "content": "{{PROMPT}}"}
    assert _substitute(template, "p") == {"model": "x", "n": 1, "content": "p"}


# ---------------------------------------------------------------------------
# response_path extraction (nested + list index)
# ---------------------------------------------------------------------------

def test_extract_flat():
    assert _extract({"response": "ok"}, "response") == "ok"


def test_extract_nested_list_index():
    data = {"choices": [{"message": {"content": "hello"}}]}
    assert _extract(data, "choices.0.message.content") == "hello"


# ---------------------------------------------------------------------------
# simple_json preset reproduces current VictimBot behavior
# ---------------------------------------------------------------------------

def test_simple_json_preset_matches_victim():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["method"] = req.method
        seen["body"] = req.content
        return httpx.Response(200, json={"response": "hello from bot"})

    config = TargetConfig(url="http://target/chat", preset=Preset.SIMPLE_JSON)
    c = _client(config, handler)
    assert asyncio.run(c.send("hi")) == "hello from bot"
    assert seen["method"] == "POST"
    assert seen["url"] == "http://target/chat"
    assert b'"message":"hi"' in seen["body"].replace(b" ", b"")


def test_bare_base_url_backward_compat():
    """Old TargetClient(base_url) path still POSTs {base}/chat {"message":...}."""
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"response": "ok"})

    c = TargetClient("http://target", transport=httpx.MockTransport(handler))
    assert asyncio.run(c.send("hi")) == "ok"
    assert seen["url"] == "http://target/chat"


# ---------------------------------------------------------------------------
# openai_chat preset builds a correct OpenAI-style body
# ---------------------------------------------------------------------------

def test_openai_chat_preset_body_and_extraction():
    seen = {}

    def handler(req):
        import json

        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "answer"}}]}
        )

    config = TargetConfig(
        url="http://llm/v1/chat/completions", preset=Preset.OPENAI_CHAT
    )
    c = _client(config, handler)
    assert asyncio.run(c.send("attack prompt")) == "answer"
    assert seen["body"]["messages"][0]["content"] == "attack prompt"
    assert seen["body"]["messages"][0]["role"] == "user"
    assert "model" in seen["body"]


# ---------------------------------------------------------------------------
# custom preset + headers
# ---------------------------------------------------------------------------

def test_custom_preset_template_and_headers():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = req.content
        return httpx.Response(200, json={"data": {"reply": "yo"}})

    config = TargetConfig(
        url="http://api/ask",
        headers={"Authorization": "Bearer tok"},
        request_template={"q": "{{PROMPT}}"},
        response_path="data.reply",
        preset=Preset.CUSTOM,
    )
    c = _client(config, handler)
    assert asyncio.run(c.send("hi")) == "yo"
    assert seen["auth"] == "Bearer tok"
    assert b'"q":"hi"' in seen["body"].replace(b" ", b"")


def test_custom_preset_requires_template_and_path():
    config = TargetConfig(url="http://api/ask", preset=Preset.CUSTOM)
    with pytest.raises(ValueError, match="custom preset requires"):
        _client(config, lambda req: httpx.Response(200))


# ---------------------------------------------------------------------------
# TargetError still fires on transport/HTTP failure
# ---------------------------------------------------------------------------

def test_send_raises_on_timeout():
    def handler(req):
        raise httpx.TimeoutException("timed out")

    config = TargetConfig(url="http://target/chat")
    with pytest.raises(TargetError):
        asyncio.run(_client(config, handler).send("hi"))


def test_send_raises_on_5xx():
    config = TargetConfig(url="http://target/chat")
    c = _client(config, lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(TargetError):
        asyncio.run(c.send("hi"))


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------

def test_connection_ok_on_good_response():
    config = TargetConfig(url="http://target/chat", preset=Preset.SIMPLE_JSON)
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"response": "hi there"})
    )
    result = asyncio.run(probe_connection(config, transport=transport))
    assert result == {"ok": True, "sample_reply": "hi there"}


def test_connection_false_on_error():
    config = TargetConfig(url="http://target/chat", preset=Preset.SIMPLE_JSON)
    transport = httpx.MockTransport(lambda req: httpx.Response(500, text="boom"))
    result = asyncio.run(probe_connection(config, transport=transport))
    assert result["ok"] is False
    assert "error" in result


def test_connection_false_on_bad_response_path():
    config = TargetConfig(
        url="http://target/chat",
        request_template={"message": "{{PROMPT}}"},
        response_path="nonexistent.key",
        preset=Preset.CUSTOM,
    )
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"response": "x"})
    )
    result = asyncio.run(probe_connection(config, transport=transport))
    assert result["ok"] is False
