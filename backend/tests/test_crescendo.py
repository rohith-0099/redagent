"""Crescendo multi-turn tests. Attacker LLM, target, judge mocked — offline."""

from unittest.mock import AsyncMock

import pytest

from agents import crescendo
from core.config import MAX_TURNS
from core.contracts import AttackCategory, AttackResult, Severity, Verdict


@pytest.fixture(autouse=True)
def _no_trace(monkeypatch):
    monkeypatch.setattr(crescendo, "record_attack", lambda r: None)


def _mock_next_turn(monkeypatch):
    # Attacker LLM yields a predictable escalating message each turn.
    counter = {"n": 0}

    async def fake(category, history, guidance, recon=None):
        counter["n"] += 1
        return f"turn {counter['n']} message"

    monkeypatch.setattr(crescendo, "_next_turn", fake)


async def test_breaches_on_third_turn(monkeypatch):
    _mock_next_turn(monkeypatch)
    target = AsyncMock()
    target.send_traced = AsyncMock(return_value=("bot reply", []))
    # judge: PASS, PASS, then FAIL on turn 3.
    judge_seq = [
        (Verdict.PASS, Severity.LOW, "held"),
        (Verdict.PASS, Severity.LOW, "held"),
        (Verdict.FAIL, Severity.HIGH, "broke rule"),
    ]
    monkeypatch.setattr(crescendo, "judge", AsyncMock(side_effect=judge_seq))

    result = await crescendo.run_crescendo(AttackCategory.SCOPE_VIOLATION, target)

    assert result.verdict == Verdict.FAIL
    assert result.severity == Severity.HIGH
    assert result.breach_turn == 3
    assert result.attack_mode == "crescendo"
    assert len(result.transcript) == 3
    assert [t["turn_index"] for t in result.transcript] == [1, 2, 3]


async def test_max_turns_cap_no_breach(monkeypatch):
    _mock_next_turn(monkeypatch)
    target = AsyncMock()
    target.send_traced = AsyncMock(return_value=("still refusing", []))
    monkeypatch.setattr(
        crescendo, "judge", AsyncMock(return_value=(Verdict.PASS, Severity.LOW, "held"))
    )

    result = await crescendo.run_crescendo(AttackCategory.JAILBREAK, target)

    assert result.verdict == Verdict.PASS
    assert result.breach_turn is None
    assert len(result.transcript) == MAX_TURNS  # exactly the cap, no hang
    assert target.send_traced.await_count == MAX_TURNS


async def test_agentic_breach_on_tool_call_later_turn(monkeypatch):
    # Real (deterministic) judge: refund tool fires on turn 2 → breach.
    _mock_next_turn(monkeypatch)
    target = AsyncMock()
    target.send_traced = AsyncMock(
        side_effect=[
            ("Sure, what's your order id?", []),  # turn 1: no tool
            ("Refund issued.",
             [{"name": "issue_refund", "args": {"order_id": "C3003", "amount": 340}}]),
        ]
    )
    # do NOT mock judge — exercise the real trace-based agentic judging.

    result = await crescendo.run_crescendo(AttackCategory.TOOL_MISUSE, target, max_turns=5)

    assert result.verdict == Verdict.FAIL
    assert result.breach_turn == 2
    assert result.tool_calls == [
        {"name": "issue_refund", "args": {"order_id": "C3003", "amount": 340}}
    ]
    assert result.transcript[1]["tool_calls"][0]["name"] == "issue_refund"


async def test_transport_error_stops_without_breach(monkeypatch):
    from tools.target_client import TargetError

    _mock_next_turn(monkeypatch)
    target = AsyncMock()
    target.send_traced = AsyncMock(side_effect=TargetError("connection refused"))
    monkeypatch.setattr(crescendo, "judge", AsyncMock())

    result = await crescendo.run_crescendo(AttackCategory.SCOPE_VIOLATION, target)

    assert result.verdict == Verdict.PASS
    assert result.breach_turn is None
    assert len(result.transcript) == 1
    assert "not delivered" in result.transcript[0]["target_response"]


def test_single_shot_attackresult_defaults():
    ar = AttackResult(
        category=AttackCategory.PROMPT_LEAK,
        prompt="p",
        response="r",
        verdict=Verdict.PASS,
        severity=Severity.LOW,
        reason="x",
    )
    assert ar.attack_mode == "single_shot"
    assert ar.transcript == []
    assert ar.breach_turn is None
