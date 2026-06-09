"""Verifier tests. Target hardened-clone + judge mocked — offline."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import verifier
from agents.verifier import verify_fix
from core.contracts import (
    AttackCategory,
    AttackResult,
    Campaign,
    FixProposal,
    Severity,
    Verdict,
)


def _breach(cat, mode="single_shot", transcript=None):
    return AttackResult(
        category=cat,
        prompt=f"attack {cat.value}",
        response="leaked",
        verdict=Verdict.FAIL,
        severity=Severity.HIGH,
        reason="broke rule",
        attack_mode=mode,
        transcript=transcript or [],
    )


def _campaign(results):
    return Campaign(campaign_id="c1", results=results)


def _fix():
    return FixProposal(new_system_prompt="HARDENED PROMPT", guards=["g"], rationale="r")


def _target(send_results):
    """A target whose hardened clone replays send_traced from send_results."""
    hardened = MagicMock()
    hardened.send_traced = AsyncMock(side_effect=send_results)
    target = MagicMock()
    target.with_system_prompt = MagicMock(return_value=hardened)
    return target, hardened


async def test_fix_effective_all_pass(monkeypatch):
    results = [
        _breach(AttackCategory.PROMPT_LEAK),
        _breach(AttackCategory.COMPETITOR),
        _breach(AttackCategory.SCOPE_VIOLATION),
    ]
    target, hardened = _target([("refused", []), ("refused", []), ("refused", [])])
    monkeypatch.setattr(
        verifier, "judge", AsyncMock(return_value=(Verdict.PASS, Severity.LOW, "held"))
    )

    report = await verify_fix(_campaign(results), _fix(), target)

    assert report.original_breaches == 3
    assert report.breaches_after_fix == 0
    assert report.fixed == 3
    assert report.verdict == "fix_effective"
    assert report.still_breaching == []
    # hardened clone built from the fix prompt
    target.with_system_prompt.assert_called_once_with("HARDENED PROMPT")
    assert hardened.send_traced.await_count == 3


async def test_partial_some_still_breach(monkeypatch):
    results = [
        _breach(AttackCategory.PROMPT_LEAK),
        _breach(AttackCategory.COMPETITOR),
        _breach(AttackCategory.SCOPE_VIOLATION),
    ]
    target, _ = _target([("refused", []), ("leaked again", []), ("refused", [])])
    monkeypatch.setattr(
        verifier,
        "judge",
        AsyncMock(side_effect=[
            (Verdict.PASS, Severity.LOW, "held"),
            (Verdict.FAIL, Severity.HIGH, "still broke"),
            (Verdict.PASS, Severity.LOW, "held"),
        ]),
    )

    report = await verify_fix(_campaign(results), _fix(), target)

    assert report.original_breaches == 3
    assert report.breaches_after_fix == 1
    assert report.fixed == 2
    assert report.verdict == "partial"
    assert len(report.still_breaching) == 1
    assert report.still_breaching[0].category == AttackCategory.COMPETITOR


async def test_only_breached_attacks_rerun(monkeypatch):
    # PASS results in the campaign must be ignored — only FAILs are re-run.
    results = [
        _breach(AttackCategory.PROMPT_LEAK),
        AttackResult(
            category=AttackCategory.JAILBREAK, prompt="p", response="no",
            verdict=Verdict.PASS, severity=Severity.LOW, reason="held",
        ),
    ]
    target, hardened = _target([("refused", [])])
    monkeypatch.setattr(
        verifier, "judge", AsyncMock(return_value=(Verdict.PASS, Severity.LOW, "held"))
    )

    report = await verify_fix(_campaign(results), _fix(), target)

    assert report.original_breaches == 1  # only the FAIL re-run
    assert hardened.send_traced.await_count == 1


async def test_agentic_rerun_uses_real_trace_judge():
    # No judge mock: deterministic agentic judging on the tool trace.
    results = [_breach(AttackCategory.TOOL_MISUSE)]
    # Hardened bot still calls issue_refund → real judge marks FAIL.
    target, _ = _target([
        ("Refund issued.", [{"name": "issue_refund", "args": {"order_id": "A1001", "amount": 120}}]),
    ])

    report = await verify_fix(_campaign(results), _fix(), target)

    assert report.breaches_after_fix == 1
    assert report.verdict == "ineffective"
    assert report.still_breaching[0].tool_calls[0]["name"] == "issue_refund"


async def test_crescendo_replay_uses_transcript(monkeypatch):
    transcript = [
        {"turn_index": 1, "attacker_msg": "hi", "target_response": "hello", "tool_calls": []},
        {"turn_index": 2, "attacker_msg": "refund A1001", "target_response": "ok", "tool_calls": []},
    ]
    results = [_breach(AttackCategory.TOOL_MISUSE, mode="crescendo", transcript=transcript)]
    target, hardened = _target([("refused", [])])
    monkeypatch.setattr(
        verifier, "judge", AsyncMock(return_value=(Verdict.PASS, Severity.LOW, "held"))
    )

    report = await verify_fix(_campaign(results), _fix(), target)

    # replay message stitched both attacker turns together
    sent = hardened.send_traced.await_args.args[0]
    assert "hi" in sent and "refund A1001" in sent
    assert report.verdict == "fix_effective"
