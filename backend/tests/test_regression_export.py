"""Regression export tests. Target + judge mocked — offline, no network."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from core.contracts import (
    AttackCategory,
    AttackResult,
    Campaign,
    CategoryReport,
    FixProposal,
    Preset,
    Severity,
    TargetConfig,
    Verdict,
    VulnReport,
)
from core.state import store
from tools import regression_runner
from tools.regression_export import (
    export_regression_suite,
    render_pytest_file,
    render_workflow,
)


def _single(cat, verdict=Verdict.FAIL):
    return AttackResult(
        category=cat,
        prompt=f"break {cat.value}",
        response="leaked",
        verdict=verdict,
        severity=Severity.HIGH,
        reason="broke the rule",
    )


def _crescendo(cat):
    return AttackResult(
        category=cat,
        prompt="turn 1 opener",
        response="final breach",
        verdict=Verdict.FAIL,
        severity=Severity.MED,
        reason="escalated to breach",
        attack_mode="crescendo",
        breach_turn=2,
        transcript=[
            {"turn_index": 1, "attacker_msg": "soft opener", "target_response": "ok"},
            {"turn_index": 2, "attacker_msg": "the escalation", "target_response": "breach"},
        ],
    )


def _campaign(with_fix=False, with_target=True):
    results = [
        _single(AttackCategory.COMPETITOR),
        _single(AttackCategory.SCOPE_VIOLATION, Verdict.PASS),  # not a breach
        _crescendo(AttackCategory.JAILBREAK),
    ]
    report = VulnReport(
        per_category={
            AttackCategory.COMPETITOR: CategoryReport(
                success_rate=1.0,
                severity=Severity.HIGH,
                examples=[results[0]],
                owasp_id="LLM07",
            )
        }
    )
    camp = Campaign(
        campaign_id="camp-1",
        status="awaiting_approval",
        results=results,
        report=report,
        target_config=TargetConfig(url="http://victim/chat", preset=Preset.SIMPLE_JSON)
        if with_target
        else None,
    )
    if with_fix:
        camp.fix = FixProposal(
            new_system_prompt="HARDENED PROMPT", guards=["g"], rationale="r"
        )
    return camp


# ---------------------------------------------------------------------------
# export_regression_suite
# ---------------------------------------------------------------------------

def test_export_has_one_case_per_breach():
    suite = export_regression_suite(_campaign())
    # 2 breaches (COMPETITOR + JAILBREAK); the PASS result is excluded
    assert len(suite["cases"]) == 2
    cats = {c["category"] for c in suite["cases"]}
    assert cats == {"COMPETITOR", "JAILBREAK"}


def test_export_case_fields():
    suite = export_regression_suite(_campaign())
    comp = next(c for c in suite["cases"] if c["category"] == "COMPETITOR")
    assert comp["expected_verdict"] == "PASS"
    assert comp["severity"] == "HIGH"
    assert comp["owasp_id"] == "LLM07"
    assert comp["attack_mode"] == "single_shot"
    assert comp["replay_prompt"] == "break COMPETITOR"
    assert suite["target_config"]["url"] == "http://victim/chat"


def test_export_crescendo_carries_transcript_and_joined_replay():
    suite = export_regression_suite(_campaign())
    cres = next(c for c in suite["cases"] if c["category"] == "JAILBREAK")
    assert cres["attack_mode"] == "crescendo"
    assert len(cres["transcript"]) == 2
    assert cres["breach_turn"] == 2
    # replay joins the escalating attacker turns so it can be replayed verbatim
    assert "soft opener" in cres["replay_prompt"]
    assert "the escalation" in cres["replay_prompt"]


def test_export_with_fix_sets_hardened_override():
    suite = export_regression_suite(_campaign(with_fix=True))
    assert suite["target_config"]["system_prompt_override"] == "HARDENED PROMPT"


def test_export_without_fix_has_no_override():
    suite = export_regression_suite(_campaign(with_fix=False))
    assert suite["target_config"]["system_prompt_override"] is None


def test_export_without_target_config():
    suite = export_regression_suite(_campaign(with_target=False))
    assert suite["target_config"] is None
    assert len(suite["cases"]) == 2


# ---------------------------------------------------------------------------
# generated pytest file
# ---------------------------------------------------------------------------

def test_generated_pytest_file_is_valid_python_and_uses_runner():
    src = render_pytest_file(export_regression_suite(_campaign(with_fix=True)))
    compile(src, "test_redagent_regression.py", "exec")  # syntactically valid
    assert "from tools.regression_runner import check_case" in src
    assert "camp-1" in src
    assert "test_attack_must_not_breach" in src


def test_workflow_is_nonempty_yaml():
    wf = render_workflow()
    assert "RedAgent Regression" in wf
    assert "pytest test_redagent_regression.py" in wf


# ---------------------------------------------------------------------------
# runner — passes when target now holds, fails when it still breaches
# ---------------------------------------------------------------------------

def _patch_runner(monkeypatch, response, verdict):
    class _FakeTarget:
        def __init__(self, *a, **k):
            pass

        async def send_traced(self, msg):
            return response, []

    monkeypatch.setattr(regression_runner, "TargetClient", _FakeTarget)

    async def _judge(category, prompt, resp, rules, tool_calls=None):
        return verdict, Severity.HIGH, "judged"

    monkeypatch.setattr(regression_runner, "judge", _judge)


def test_runner_passes_when_target_now_holds(monkeypatch):
    _patch_runner(monkeypatch, "I cannot discuss that.", Verdict.PASS)
    suite = export_regression_suite(_campaign(with_fix=True))
    case = suite["cases"][0]
    result = regression_runner.check_case(case, suite["target_config"])
    assert result["passed"] is True
    assert result["verdict"] == "PASS"


def test_runner_fails_when_target_still_breaches(monkeypatch):
    _patch_runner(monkeypatch, "Sure, our rival BrandX is worse.", Verdict.FAIL)
    suite = export_regression_suite(_campaign(with_fix=False))
    case = suite["cases"][0]
    result = regression_runner.check_case(case, suite["target_config"])
    assert result["passed"] is False
    assert result["verdict"] == "FAIL"


def test_runner_target_error_counts_as_pass(monkeypatch):
    from tools.target_client import TargetError

    class _FakeTarget:
        def __init__(self, *a, **k):
            pass

        async def send_traced(self, msg):
            raise TargetError("connection refused")

    monkeypatch.setattr(regression_runner, "TargetClient", _FakeTarget)
    suite = export_regression_suite(_campaign())
    result = regression_runner.check_case(suite["cases"][0], suite["target_config"])
    assert result["passed"] is True
    assert "not delivered" in result["response"]


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    store._store.clear()
    c = TestClient(main.app)
    yield c
    store._store.clear()


def test_export_endpoint_returns_suite(client):
    store.create(_campaign())
    resp = client.get("/campaign/camp-1/export")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == "camp-1"
    assert len(body["cases"]) == 2


def test_export_endpoint_pytest_format(client):
    store.create(_campaign())
    resp = client.get("/campaign/camp-1/export?format=pytest")
    assert resp.status_code == 200
    assert "test_attack_must_not_breach" in resp.text
    assert "attachment" in resp.headers["content-disposition"]


def test_export_endpoint_unknown_404(client):
    resp = client.get("/campaign/nope/export")
    assert resp.status_code == 404


def test_export_endpoint_no_results_404(client):
    store.create(Campaign(campaign_id="empty", status="running"))
    resp = client.get("/campaign/empty/export")
    assert resp.status_code == 404
