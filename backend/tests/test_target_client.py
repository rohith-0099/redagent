"""TargetClient tests. httpx is mocked via MockTransport — no real server."""

import asyncio

import httpx
import pytest

from tools.target_client import TargetClient, TargetError


def _client(handler) -> TargetClient:
    return TargetClient("http://target", transport=httpx.MockTransport(handler))


def test_send_returns_response_on_200():
    c = _client(lambda req: httpx.Response(200, json={"response": "hello from bot"}))
    assert asyncio.run(c.send("hi")) == "hello from bot"


def test_send_raises_on_timeout():
    def handler(req):
        raise httpx.TimeoutException("timed out")

    c = _client(handler)
    with pytest.raises(TargetError):
        asyncio.run(c.send("hi"))


def test_send_raises_on_5xx():
    c = _client(lambda req: httpx.Response(500, text="boom"))
    with pytest.raises(TargetError):
        asyncio.run(c.send("hi"))


def test_health_true_on_200():
    c = _client(lambda req: httpx.Response(200, json={"status": "ok"}))
    assert asyncio.run(c.health()) is True


def test_health_false_otherwise():
    c = _client(lambda req: httpx.Response(503))
    assert asyncio.run(c.health()) is False
