"""Attacker tests. ADK generation, target, and judge all mocked — no real
API, no real network."""

import asyncio
from unittest.mock import AsyncMock

from agents import attacker
from core.contracts import AttackCategory, Severity, Verdict
from tools.target_client import TargetError


async def test_run_attacks_builds_results(monkeypatch):
    monkeypatch.setattr(
        attacker, "generate_prompts", AsyncMock(return_value=["p1", "p2"])
    )
    monkeypatch.setattr(
        attacker, "judge", AsyncMock(return_value=(Verdict.FAIL, Severity.HIGH, "broke rule"))
    )
    monkeypatch.setattr(attacker, "record_attack", lambda r: None)
    target = AsyncMock()
    target.send_traced = AsyncMock(return_value=("leaked secret", []))

    results = await attacker.run_attacks(AttackCategory.PROMPT_LEAK, target, 2)

    assert len(results) == 2
    for res, prompt in zip(results, ["p1", "p2"]):
        assert res.category == AttackCategory.PROMPT_LEAK
        assert res.prompt == prompt
        assert res.response == "leaked secret"
        assert res.verdict == Verdict.FAIL
        assert res.severity == Severity.HIGH
        assert res.reason == "broke rule"


async def test_run_attacks_forwards_memory_guidance(monkeypatch):
    """Attack-memory recall reaches generation when present (RAG #2 wiring)."""
    captured = {}

    async def fake_gen(category, prompts_per, store=None, recon=None, memory_guidance=""):
        captured["mg"] = memory_guidance
        return ["p1"]

    monkeypatch.setattr(attacker, "generate_prompts", fake_gen)
    monkeypatch.setattr(
        attacker, "judge", AsyncMock(return_value=(Verdict.PASS, Severity.LOW, "ok"))
    )
    monkeypatch.setattr(attacker, "record_attack", lambda r: None)
    target = AsyncMock()
    target.send_traced = AsyncMock(return_value=("r", []))

    await attacker.run_attacks(
        AttackCategory.COMPETITOR, target, 1, memory_guidance="EVOLVE THESE"
    )
    assert captured["mg"] == "EVOLVE THESE"


async def test_target_error_recorded_as_not_breached(monkeypatch):
    monkeypatch.setattr(
        attacker, "generate_prompts", AsyncMock(return_value=["p1"])
    )
    judge_called = False

    async def _judge(*a):
        nonlocal judge_called
        judge_called = True
        return (Verdict.FAIL, Severity.HIGH, "x")

    monkeypatch.setattr(attacker, "judge", _judge)
    monkeypatch.setattr(attacker, "record_attack", lambda r: None)
    target = AsyncMock()
    target.send_traced = AsyncMock(side_effect=TargetError("connection refused"))

    results = await attacker.run_attacks(AttackCategory.JAILBREAK, target, 1)

    assert len(results) == 1
    assert results[0].verdict == Verdict.PASS
    assert "not delivered" in results[0].reason
    assert judge_called is False
