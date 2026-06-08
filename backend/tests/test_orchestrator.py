"""Orchestrator tests. All four agents + target mocked — no real API/network."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import orchestrator
from core.contracts import (
    AttackCategory,
    AttackPlan,
    AttackResult,
    CategoryReport,
    FixProposal,
    Severity,
    VulnReport,
    Verdict,
)
from core.state import store


@pytest.fixture(autouse=True)
def reset_state():
    """Wipe in-memory store + orchestrator prompt cache between tests."""
    store._store.clear()
    orchestrator._system_prompts.clear()
    yield
    store._store.clear()
    orchestrator._system_prompts.clear()


def _make_plan(*categories, prompts_per=2):
    return AttackPlan(categories=list(categories), prompts_per=prompts_per)


def _make_result(cat, verdict=Verdict.FAIL):
    return AttackResult(
        category=cat,
        prompt="p",
        response="r",
        verdict=verdict,
        severity=Severity.MED,
        reason="test",
    )


def _make_report(breached_cats=()):
    per = {}
    for cat in breached_cats:
        per[cat] = CategoryReport(
            success_rate=1.0,
            severity=Severity.MED,
            examples=[_make_result(cat)],
        )
    return VulnReport(per_category=per)


def _make_fix():
    return FixProposal(
        new_system_prompt="hardened",
        guards=["Block competitor mentions"],
        rationale="COMPETITOR breached",
    )


# ---------------------------------------------------------------------------
# Pipeline reaches awaiting_approval WITHOUT calling Defender
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_campaign_reaches_awaiting_approval():
    plan = _make_plan(AttackCategory.COMPETITOR)
    results = [_make_result(AttackCategory.COMPETITOR)]
    report = _make_report(breached_cats=[AttackCategory.COMPETITOR])

    with (
        patch.object(orchestrator, "plan_campaign", AsyncMock(return_value=plan)),
        patch.object(orchestrator, "run_attacks", AsyncMock(return_value=results)),
        patch.object(orchestrator, "build_vuln_report", return_value=report),
        patch.object(orchestrator, "propose_fix", AsyncMock()) as mock_defender,
        patch("agents.orchestrator.TargetClient"),
    ):
        campaign_id = await orchestrator.start_campaign(
            "http://victim", "TechCo bot", "old system prompt"
        )

    mock_defender.assert_not_called()
    campaign = orchestrator.get_campaign(campaign_id)
    assert campaign.status == "awaiting_approval"
    assert campaign.report is not None
    assert campaign.fix is None


@pytest.mark.asyncio
async def test_start_campaign_stores_plan_and_results():
    plan = _make_plan(AttackCategory.SCOPE_VIOLATION, prompts_per=3)
    results = [_make_result(AttackCategory.SCOPE_VIOLATION, Verdict.PASS)]
    report = _make_report()

    with (
        patch.object(orchestrator, "plan_campaign", AsyncMock(return_value=plan)),
        patch.object(orchestrator, "run_attacks", AsyncMock(return_value=results)),
        patch.object(orchestrator, "build_vuln_report", return_value=report),
        patch.object(orchestrator, "propose_fix", AsyncMock()),
        patch("agents.orchestrator.TargetClient"),
    ):
        campaign_id = await orchestrator.start_campaign("http://victim")

    campaign = orchestrator.get_campaign(campaign_id)
    assert campaign.plan == plan
    assert campaign.results == results


# ---------------------------------------------------------------------------
# approve_and_fix runs Defender and transitions to done
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_and_fix_runs_defender():
    plan = _make_plan(AttackCategory.COMPETITOR)
    results = [_make_result(AttackCategory.COMPETITOR)]
    report = _make_report(breached_cats=[AttackCategory.COMPETITOR])
    fix = _make_fix()

    with (
        patch.object(orchestrator, "plan_campaign", AsyncMock(return_value=plan)),
        patch.object(orchestrator, "run_attacks", AsyncMock(return_value=results)),
        patch.object(orchestrator, "build_vuln_report", return_value=report),
        patch.object(orchestrator, "propose_fix", AsyncMock(return_value=fix)),
        patch("agents.orchestrator.TargetClient"),
    ):
        campaign_id = await orchestrator.start_campaign(
            "http://victim", current_system_prompt="old"
        )
        campaign = await orchestrator.approve_and_fix(campaign_id)

    assert campaign.status == "done"
    assert campaign.fix == fix


# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_state_transitions_are_correct():
    statuses: list[str] = []

    original_update = store.update

    def recording_update(campaign):
        statuses.append(campaign.status)
        return original_update(campaign)

    plan = _make_plan(AttackCategory.JAILBREAK)
    results = [_make_result(AttackCategory.JAILBREAK, Verdict.PASS)]
    report = _make_report()
    fix = _make_fix()

    with (
        patch.object(orchestrator, "plan_campaign", AsyncMock(return_value=plan)),
        patch.object(orchestrator, "run_attacks", AsyncMock(return_value=results)),
        patch.object(orchestrator, "build_vuln_report", return_value=report),
        patch.object(orchestrator, "propose_fix", AsyncMock(return_value=fix)),
        patch("agents.orchestrator.TargetClient"),
        patch.object(store, "update", side_effect=recording_update),
    ):
        campaign_id = await orchestrator.start_campaign("http://victim")
        await orchestrator.approve_and_fix(campaign_id)

    assert statuses[0] == "running"
    assert "awaiting_approval" in statuses
    assert statuses[-1] == "done"


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_and_fix_rejects_wrong_status():
    plan = _make_plan(AttackCategory.COMPETITOR)
    report = _make_report(breached_cats=[AttackCategory.COMPETITOR])

    with (
        patch.object(orchestrator, "plan_campaign", AsyncMock(return_value=plan)),
        patch.object(orchestrator, "run_attacks", AsyncMock(return_value=[])),
        patch.object(orchestrator, "build_vuln_report", return_value=report),
        patch.object(orchestrator, "propose_fix", AsyncMock(return_value=_make_fix())),
        patch("agents.orchestrator.TargetClient"),
    ):
        campaign_id = await orchestrator.start_campaign("http://victim")
        await orchestrator.approve_and_fix(campaign_id)  # moves to done

    # Calling again on a done campaign should raise
    with pytest.raises(ValueError, match="not awaiting approval"):
        await orchestrator.approve_and_fix(campaign_id)
