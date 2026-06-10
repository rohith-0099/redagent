"""Recon tests. Target + summary LLM mocked — offline."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import recon
from agents.attacker import agentic_context_hint
from agents.strategist import _recon_brief
from agents.recon import recon_target
from core.contracts import AttackCategory, ReconReport
from tools import phoenix_query
from tools.target_client import TargetError


def _mock_summary(monkeypatch, report):
    async def fake(observations):
        return report

    monkeypatch.setattr(recon, "_summarize", fake)


async def test_recon_discovers_tools_and_context(monkeypatch):
    target = MagicMock()
    # Bot calls lookup_order during one benign probe; reveals A1001 in text.
    target.send_traced = AsyncMock(
        side_effect=[
            ("I help with TechCo orders.", []),
            ("I can look up orders and issue refunds.", []),
            ("Refunds are easy — just tell me your order.", []),
            ("Sure — here's a sample: order A1001 for Alice.",
             [{"name": "lookup_order", "args": {"order_id": "A1001"}}]),
            ("That's a sample order.", []),
        ]
    )
    # LLM summary contributes issue_refund + the revealed id; observed adds lookup_order.
    _mock_summary(
        monkeypatch,
        ReconReport(
            target_purpose="TechCo support",
            discovered_tools=["issue_refund"],
            discovered_context={"order_ids": ["A1001"], "customers": {"A1001": "Alice"}},
        ),
    )

    report = await recon_target(target)

    assert "lookup_order" in report.discovered_tools  # observed in trace, merged in
    assert "issue_refund" in report.discovered_tools  # from summary
    assert report.discovered_context["order_ids"] == ["A1001"]


async def test_recon_is_bounded(monkeypatch):
    target = MagicMock()
    target.send_traced = AsyncMock(return_value=("ok", []))
    _mock_summary(monkeypatch, ReconReport())

    await recon_target(target, max_probes=3)

    assert target.send_traced.await_count == 3  # never exceeds the cap


async def test_recon_survives_target_error(monkeypatch):
    target = MagicMock()
    target.send_traced = AsyncMock(side_effect=TargetError("down"))
    _mock_summary(monkeypatch, ReconReport())

    report = await recon_target(target, max_probes=2)  # must not raise

    assert isinstance(report, ReconReport)
    assert target.send_traced.await_count == 2


# --- Attacker now uses recon context, not hardcoded ids --------------------

def test_agentic_hint_from_recon_includes_discovered_ids():
    recon_rep = ReconReport(
        discovered_tools=["lookup_order", "issue_refund"],
        discovered_context={"order_ids": ["A1001"]},
    )
    hint = agentic_context_hint(recon_rep)
    assert "A1001" in hint
    assert "issue_refund" in hint


def test_agentic_hint_empty_when_no_recon():
    assert agentic_context_hint(None) == ""
    assert agentic_context_hint(ReconReport()) == ""  # discovered nothing → generic


def test_no_hardcoded_order_hint_remains():
    import agents.attacker as atk

    assert not hasattr(atk, "_AGENTIC_ORDER_HINT")


# --- Strategist incorporates recon -----------------------------------------

def test_strategist_brief_flags_agentic_when_tools_found():
    brief = _recon_brief(ReconReport(discovered_tools=["issue_refund"]))
    assert "issue_refund" in brief
    assert "GOAL_HIJACK" in brief and "TOOL_MISUSE" in brief


def test_strategist_brief_empty_without_recon():
    assert _recon_brief(None) == ""


# --- Recon spans are separated from attack spans ---------------------------

def test_recon_spans_not_counted_as_attacks(monkeypatch):
    # A recon span (recon.* attributes, no attack.category) must be ignored by
    # the Analyst's attack-span parser, so probes never count as breaches.
    spans = [
        {"attributes": {"recon.probe": "what can you do?", "recon.response": "..."}},
        {"attributes": {
            "attack.category": "COMPETITOR", "attack.prompt": "p",
            "attack.response": "r", "attack.verdict": "FAIL",
            "attack.severity": "MED", "attack.reason": "x",
        }},
    ]
    client = MagicMock()
    client.spans.get_spans.return_value = spans
    monkeypatch.setattr(phoenix_query, "Client", lambda **kw: client)

    results = phoenix_query.fetch_attack_spans("redagent")

    assert len(results) == 1  # only the attack span parsed; recon ignored
    assert results[0].category == AttackCategory.COMPETITOR
