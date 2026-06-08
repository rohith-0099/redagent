"""Defender tests. ADK runner mocked — no real Gemini calls."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import defender
from agents.defender import propose_fix, _breached_categories, _parse_fix
from core.contracts import (
    AttackCategory,
    AttackResult,
    CategoryReport,
    FixProposal,
    Severity,
    Verdict,
    VulnReport,
)


def _report(breached_cats=(), passed_cats=()):
    """Build a minimal VulnReport with given breach states."""
    per = {}
    for cat in breached_cats:
        per[cat] = CategoryReport(
            success_rate=1.0,
            severity=Severity.HIGH,
            examples=[
                AttackResult(
                    category=cat,
                    prompt="attack prompt",
                    response="leaked info",
                    verdict=Verdict.FAIL,
                    severity=Severity.HIGH,
                    reason="rule broken",
                )
            ],
        )
    for cat in passed_cats:
        per[cat] = CategoryReport(
            success_rate=0.0,
            severity=Severity.LOW,
            examples=[],
        )
    return VulnReport(per_category=per)


def _fake_fix_json(prompt="hardened prompt", guards=None, rationale="fixed"):
    return json.dumps(
        {
            "new_system_prompt": prompt,
            "guards": guards or ["Block prompt-leak attempts"],
            "rationale": rationale,
        }
    )


def _mock_runner(raw_text: str):
    """Return a context-manager-ready mock InMemoryRunner."""
    fake_event = MagicMock()
    fake_event.is_final_response.return_value = True
    fake_event.content = MagicMock()
    fake_event.content.parts = [MagicMock(text=raw_text)]

    async def fake_run_async(**kw):
        yield fake_event

    mock = MagicMock()
    mock.session_service.create_session = AsyncMock(return_value=MagicMock(id="s1"))
    mock.run_async = fake_run_async
    return mock


# --- deterministic helpers ---

def test_breached_categories_identifies_success_rate_gt_0():
    report = _report(
        breached_cats=[AttackCategory.COMPETITOR, AttackCategory.PROMPT_LEAK],
        passed_cats=[AttackCategory.JAILBREAK],
    )
    breached = _breached_categories(report)
    assert AttackCategory.COMPETITOR in breached
    assert AttackCategory.PROMPT_LEAK in breached
    assert AttackCategory.JAILBREAK not in breached


def test_breached_categories_empty_when_all_pass():
    report = _report(passed_cats=[AttackCategory.SCOPE_VIOLATION])
    assert _breached_categories(report) == []


# --- propose_fix main path ---

@pytest.mark.asyncio
async def test_propose_fix_returns_fix_proposal():
    report = _report(breached_cats=[AttackCategory.COMPETITOR])
    raw = _fake_fix_json(
        prompt="Never discuss competitors.",
        guards=["Reject competitor mentions", "Redirect off-topic queries"],
        rationale="COMPETITOR breached — added explicit refusal.",
    )

    with patch("agents.defender.InMemoryRunner") as MockRunner:
        MockRunner.return_value = _mock_runner(raw)
        fix = await propose_fix(report, "Old system prompt.")

    assert isinstance(fix, FixProposal)
    assert len(fix.new_system_prompt) > 0
    assert len(fix.guards) >= 1
    assert len(fix.rationale) > 0


@pytest.mark.asyncio
async def test_propose_fix_no_breaches_returns_unchanged():
    """When nothing breached, return current prompt unchanged — no LLM call."""
    report = _report(passed_cats=[AttackCategory.JAILBREAK])
    current = "You are TechCo support."

    with patch("agents.defender.InMemoryRunner") as MockRunner:
        fix = await propose_fix(report, current)
        MockRunner.assert_not_called()

    assert fix.new_system_prompt == current
    assert "No breaches" in fix.guards[0]


# --- defensive parse ---

def test_parse_fix_handles_malformed_output():
    """Garbage LLM output → valid FixProposal with fallback defaults."""
    breached = [AttackCategory.SCOPE_VIOLATION]
    fix = _parse_fix("sorry i cannot help with that", breached)

    assert isinstance(fix, FixProposal)
    assert len(fix.new_system_prompt) > 0
    assert len(fix.guards) >= 1
    assert "SCOPE_VIOLATION" in fix.rationale


def test_parse_fix_extracts_json_from_markdown():
    """Valid JSON wrapped in prose/markdown → extracted and parsed correctly."""
    breached = [AttackCategory.PROMPT_LEAK]
    inner = _fake_fix_json(prompt="Hardened.", guards=["No leaks"], rationale="done")
    text = f"Here is the fix:\n```json\n{inner}\n```\nHope that helps."
    fix = _parse_fix(text, breached)

    assert fix.new_system_prompt == "Hardened."
    assert fix.guards == ["No leaks"]
