"""API tests — orchestrator/agents mocked, no real network."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agents import orchestrator
from core.contracts import (
    AttackCategory,
    AttackPlan,
    AttackResult,
    Campaign,
    CategoryReport,
    FixProposal,
    Severity,
    VulnReport,
    Verdict,
)
from core.state import store
from main import _campaign_queues, app


@pytest.fixture(autouse=True)
def reset_state():
    store._store.clear()
    orchestrator._system_prompts.clear()
    _campaign_queues.clear()
    yield
    store._store.clear()
    orchestrator._system_prompts.clear()
    _campaign_queues.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _result(cat=AttackCategory.COMPETITOR):
    return AttackResult(
        category=cat,
        prompt="test prompt",
        response="test response",
        verdict=Verdict.FAIL,
        severity=Severity.MED,
        reason="breach",
    )


def _report(cat=AttackCategory.COMPETITOR):
    return VulnReport(
        per_category={
            cat: CategoryReport(success_rate=1.0, severity=Severity.MED, examples=[_result(cat)])
        }
    )


def _fix():
    return FixProposal(
        new_system_prompt="hardened prompt",
        guards=["Block competitor mentions"],
        rationale="COMPETITOR breached",
    )


def _campaign(campaign_id="test-id", status="awaiting_approval"):
    c = Campaign(
        campaign_id=campaign_id,
        status=status,
        plan=AttackPlan(categories=[AttackCategory.COMPETITOR], prompts_per=2),
        results=[_result()],
        report=_report(),
    )
    return c


# ---------------------------------------------------------------------------
# POST /campaign
# ---------------------------------------------------------------------------


def test_post_campaign_returns_id(client):
    with patch("main.start_campaign", new_callable=AsyncMock):
        resp = client.post(
            "/campaign",
            json={"target_url": "http://victim", "target_description": "TechCo bot"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert "campaign_id" in body
    assert isinstance(body["campaign_id"], str)


def test_post_campaign_registers_queue(client):
    with patch("main.start_campaign", new_callable=AsyncMock):
        resp = client.post("/campaign", json={"target_url": "http://victim"})
    cid = resp.json()["campaign_id"]
    assert cid in _campaign_queues


# ---------------------------------------------------------------------------
# GET /campaign/{id}/report
# ---------------------------------------------------------------------------


def test_get_report_returns_report(client):
    c = _campaign()
    store._store[c.campaign_id] = c
    resp = client.get(f"/campaign/{c.campaign_id}/report")
    assert resp.status_code == 200
    assert "per_category" in resp.json()


def test_get_report_not_ready_404(client):
    c = Campaign(campaign_id="running-id", status="running")
    store._store["running-id"] = c
    resp = client.get("/campaign/running-id/report")
    assert resp.status_code == 404


def test_get_report_unknown_404(client):
    resp = client.get("/campaign/does-not-exist/report")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /campaign/{id}/approve
# ---------------------------------------------------------------------------


def test_approve_returns_fix(client):
    c = _campaign(status="awaiting_approval")
    store._store[c.campaign_id] = c
    orchestrator._system_prompts[c.campaign_id] = ""

    c_done = _campaign(status="done")
    c_done.fix = _fix()

    with patch("main.approve_and_fix", new_callable=AsyncMock, return_value=c_done):
        resp = client.post(f"/campaign/{c.campaign_id}/approve")

    assert resp.status_code == 200
    body = resp.json()
    assert body["new_system_prompt"] == "hardened prompt"
    assert "guards" in body


def test_approve_unknown_campaign_404(client):
    resp = client.post("/campaign/does-not-exist/approve")
    assert resp.status_code == 404


def test_approve_wrong_status_409(client):
    c = _campaign(status="done")
    store._store[c.campaign_id] = c

    with patch(
        "main.approve_and_fix",
        new_callable=AsyncMock,
        side_effect=ValueError("not awaiting approval"),
    ):
        resp = client.post(f"/campaign/{c.campaign_id}/approve")

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /campaign/{id}
# ---------------------------------------------------------------------------


def test_get_campaign_state(client):
    c = _campaign()
    store._store[c.campaign_id] = c
    resp = client.get(f"/campaign/{c.campaign_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "awaiting_approval"
    assert body["campaign_id"] == c.campaign_id


def test_get_campaign_unknown_404(client):
    resp = client.get("/campaign/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /campaign/{id}/stream (static replay path)
# ---------------------------------------------------------------------------


def test_stream_unknown_campaign_404(client):
    resp = client.get("/campaign/does-not-exist/stream")
    assert resp.status_code == 404


def test_stream_static_replay(client):
    c = _campaign(status="awaiting_approval")
    store._store[c.campaign_id] = c
    # No queue registered → static replay path
    resp = client.get(f"/campaign/{c.campaign_id}/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    # Body should contain SSE data lines
    text = resp.text
    assert "attack_result" in text
    assert "report_ready" in text
