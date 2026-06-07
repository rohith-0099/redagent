"""Attacker tests. ADK generation, target, and judge all mocked — no real
API, no real network."""

import asyncio
from unittest.mock import AsyncMock

from agents import attacker
from core.contracts import AttackCategory, Severity, Verdict
from tools.target_client import TargetError


def test_run_attacks_builds_results(monkeypatch):
    monkeypatch.setattr(
        attacker, "generate_prompts", AsyncMock(return_value=["p1", "p2"])
    )
    monkeypatch.setattr(
        attacker, "judge", lambda c, p, r, rules: (Verdict.FAIL, Severity.HIGH, "broke rule")
    )
    monkeypatch.setattr(attacker, "record_attack", lambda r: None)  # no tracing in tests
    target = AsyncMock()
    target.send = AsyncMock(return_value="leaked secret")

    results = asyncio.run(
        attacker.run_attacks(AttackCategory.PROMPT_LEAK, target, 2)
    )

    assert len(results) == 2
    for res, prompt in zip(results, ["p1", "p2"]):
        assert res.category == AttackCategory.PROMPT_LEAK
        assert res.prompt == prompt
        assert res.response == "leaked secret"
        assert res.verdict == Verdict.FAIL
        assert res.severity == Severity.HIGH
        assert res.reason == "broke rule"


def test_target_error_recorded_as_not_breached(monkeypatch):
    monkeypatch.setattr(
        attacker, "generate_prompts", AsyncMock(return_value=["p1"])
    )
    # judge must NOT run when delivery fails.
    judge_called = False

    def _judge(*a):
        nonlocal judge_called
        judge_called = True
        return (Verdict.FAIL, Severity.HIGH, "x")

    monkeypatch.setattr(attacker, "judge", _judge)
    monkeypatch.setattr(attacker, "record_attack", lambda r: None)  # no tracing in tests
    target = AsyncMock()
    target.send = AsyncMock(side_effect=TargetError("connection refused"))

    results = asyncio.run(
        attacker.run_attacks(AttackCategory.JAILBREAK, target, 1)
    )

    assert len(results) == 1
    assert results[0].verdict == Verdict.PASS  # not a breach
    assert "not delivered" in results[0].reason
    assert judge_called is False
