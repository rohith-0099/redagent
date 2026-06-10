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
    suggest_response_paths,
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


# ---------------------------------------------------------------------------
# FIX 1 — response_path auto-suggest (onboarding)
# ---------------------------------------------------------------------------

def test_suggest_paths_openai_shape():
    data = {
        "model": "gpt-3.5-turbo",
        "choices": [{"message": {"role": "assistant", "content": "the answer"}}],
    }
    paths = {p["path"] for p in suggest_response_paths(data)}
    assert "choices.0.message.content" in paths


def test_suggest_paths_simple_shape():
    paths = suggest_response_paths({"response": "hi there"})
    assert {"path": "response", "preview": "hi there"} in paths


def test_suggest_paths_skips_empty_strings_and_caps_depth():
    data = {"a": "", "b": "value", "deep": {"x": {"y": {"z": "leaf"}}}}
    paths = {p["path"] for p in suggest_response_paths(data)}
    assert "a" not in paths  # empty string skipped
    assert "b" in paths


def test_connection_suggests_paths_on_wrong_path():
    config = TargetConfig(
        url="http://llm/v1/chat",
        request_template={"messages": [{"content": "{{PROMPT}}"}]},
        response_path="response",  # wrong for an OpenAI-shaped reply
        preset=Preset.CUSTOM,
    )
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, json={"choices": [{"message": {"content": "answer"}}]}
        )
    )
    result = asyncio.run(probe_connection(config, transport=transport))
    assert result["ok"] is False
    assert "Couldn't find the reply" in result["error"]
    suggested = {p["path"] for p in result["suggested_paths"]}
    assert "choices.0.message.content" in suggested
    assert "raw_sample" in result


# ---------------------------------------------------------------------------
# FIX 2 — non-JSON / plain-text targets never crash
# ---------------------------------------------------------------------------

def test_plaintext_target_uses_body_text_when_no_path():
    config = TargetConfig(
        url="http://plain/chat",
        request_template={"q": "{{PROMPT}}"},
        response_path="",  # no path → raw body is the reply
        preset=Preset.CUSTOM,
    )
    c = _client(config, lambda req: httpx.Response(200, text="just plain text"))
    assert asyncio.run(c.send("hi")) == "just plain text"


def test_connection_plaintext_ok_when_no_path():
    config = TargetConfig(
        url="http://plain/chat",
        request_template={"q": "{{PROMPT}}"},
        response_path="",
        preset=Preset.CUSTOM,
    )
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="pong"))
    result = asyncio.run(probe_connection(config, transport=transport))
    assert result == {"ok": True, "sample_reply": "pong"}


def test_non_json_with_path_raises_targeterror_not_crash():
    config = TargetConfig(
        url="http://plain/chat",
        request_template={"q": "{{PROMPT}}"},
        response_path="response",  # set, but body is plain text
        preset=Preset.CUSTOM,
    )
    c = _client(config, lambda req: httpx.Response(200, text="not json"))
    with pytest.raises(TargetError, match="not JSON"):
        asyncio.run(c.send("hi"))


def test_wrong_path_in_campaign_raises_targeterror_not_crash():
    config = TargetConfig(
        url="http://t/chat",
        request_template={"q": "{{PROMPT}}"},
        response_path="missing.key",
        preset=Preset.CUSTOM,
    )
    c = _client(config, lambda req: httpx.Response(200, json={"response": "x"}))
    with pytest.raises(TargetError, match="not found"):
        asyncio.run(c.send("hi"))


# ---------------------------------------------------------------------------
# FIX 3 — fix_application mode gates override injection
# ---------------------------------------------------------------------------

def _capture_body(config):
    seen = {}

    def handler(req):
        import json

        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"response": "ok"})

    asyncio.run(_client(config, handler).send("hi"))
    return seen["body"]


def test_inject_field_mode_injects_override():
    config = TargetConfig(
        url="http://t/chat",
        preset=Preset.SIMPLE_JSON,
        system_prompt_override="HARDENED",
        fix_application="inject_field",
    )
    body = _capture_body(config)
    assert body["system_prompt_override"] == "HARDENED"


def test_manual_reverify_mode_injects_nothing():
    config = TargetConfig(
        url="http://t/chat",
        preset=Preset.SIMPLE_JSON,
        system_prompt_override="HARDENED",
        fix_application="manual_reverify",
    )
    body = _capture_body(config)
    assert "system_prompt_override" not in body
    assert body == {"message": "hi"}  # original request, untouched
