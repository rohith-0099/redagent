"""Strategist tests. ADK runner mocked — no real Gemini calls."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.strategist import plan_campaign
from core.contracts import AttackCategory, AttackPlan
from core.config import MAX_ATTACKS


def _fake_plan_json(categories, prompts_per):
    return json.dumps(
        {"categories": [c.value for c in categories], "prompts_per": prompts_per}
    )


@pytest.mark.asyncio
async def test_plan_campaign_returns_attack_plan(monkeypatch):
    """plan_campaign returns a valid AttackPlan from mocked ADK output."""
    categories = [AttackCategory.COMPETITOR, AttackCategory.SCOPE_VIOLATION]
    raw = _fake_plan_json(categories, 5)

    fake_event = MagicMock()
    fake_event.is_final_response.return_value = True
    fake_event.content = MagicMock()
    fake_event.content.parts = [MagicMock(text=raw)]

    async def fake_run_async(**kw):
        yield fake_event

    with patch("agents.strategist.InMemoryRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.session_service.create_session = AsyncMock(
            return_value=MagicMock(id="s1")
        )
        instance.run_async = fake_run_async

        plan = await plan_campaign("TechCo bot")

    assert isinstance(plan, AttackPlan)
    assert AttackCategory.COMPETITOR in plan.categories
    assert AttackCategory.SCOPE_VIOLATION in plan.categories
    assert plan.prompts_per >= 1


@pytest.mark.asyncio
async def test_plan_campaign_caps_prompts_per(monkeypatch):
    """LLM returning oversized prompts_per gets clamped to MAX_ATTACKS budget."""
    all_cats = list(AttackCategory)
    # Ask for 999 per category — way over budget
    raw = _fake_plan_json(all_cats, 999)

    fake_event = MagicMock()
    fake_event.is_final_response.return_value = True
    fake_event.content = MagicMock()
    fake_event.content.parts = [MagicMock(text=raw)]

    async def fake_run_async(**kw):
        yield fake_event

    with patch("agents.strategist.InMemoryRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.session_service.create_session = AsyncMock(
            return_value=MagicMock(id="s2")
        )
        instance.run_async = fake_run_async

        plan = await plan_campaign()

    # prompts_per * len(categories) must not exceed MAX_ATTACKS
    assert plan.prompts_per * len(plan.categories) <= MAX_ATTACKS


@pytest.mark.asyncio
async def test_plan_campaign_default_context(monkeypatch):
    """plan_campaign works with no target_description (uses built-in default)."""
    categories = [AttackCategory.COMPETITOR]
    raw = _fake_plan_json(categories, 3)

    fake_event = MagicMock()
    fake_event.is_final_response.return_value = True
    fake_event.content = MagicMock()
    fake_event.content.parts = [MagicMock(text=raw)]

    async def fake_run_async(**kw):
        yield fake_event

    with patch("agents.strategist.InMemoryRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.session_service.create_session = AsyncMock(
            return_value=MagicMock(id="s3")
        )
        instance.run_async = fake_run_async

        plan = await plan_campaign()  # no arg

    assert isinstance(plan, AttackPlan)
    assert len(plan.categories) >= 1
