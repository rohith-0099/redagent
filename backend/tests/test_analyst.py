"""Analyst tests. Phoenix query layer mocked — no real network, no npx."""

from unittest.mock import MagicMock

from agents import analyst
from agents.analyst import analyze, build_vuln_report
from core.contracts import AttackCategory, AttackResult, Severity, Verdict
from tools import phoenix_query


def _ar(category, verdict, severity) -> AttackResult:
    return AttackResult(
        category=category,
        prompt="p",
        response="r",
        verdict=verdict,
        severity=severity,
        reason="x",
    )


def test_build_vuln_report_aggregates_rates_and_severity():
    results = [
        # PROMPT_LEAK: 1 of 2 breached, worst breach HIGH
        _ar(AttackCategory.PROMPT_LEAK, Verdict.FAIL, Severity.HIGH),
        _ar(AttackCategory.PROMPT_LEAK, Verdict.PASS, Severity.LOW),
        # COMPETITOR: 2 of 2 breached, worst MED
        _ar(AttackCategory.COMPETITOR, Verdict.FAIL, Severity.LOW),
        _ar(AttackCategory.COMPETITOR, Verdict.FAIL, Severity.MED),
        # JAILBREAK: 0 of 1 breached
        _ar(AttackCategory.JAILBREAK, Verdict.PASS, Severity.LOW),
    ]

    report = build_vuln_report(results)
    pl = report.per_category[AttackCategory.PROMPT_LEAK]
    co = report.per_category[AttackCategory.COMPETITOR]
    jb = report.per_category[AttackCategory.JAILBREAK]

    assert pl.success_rate == 0.5
    assert pl.severity == Severity.HIGH
    assert len(pl.examples) == 1  # only the breach

    assert co.success_rate == 1.0
    assert co.severity == Severity.MED  # highest among breaches
    assert len(co.examples) == 2

    assert jb.success_rate == 0.0
    assert jb.severity == Severity.LOW  # no breach -> LOW
    assert jb.examples == []


def test_analyze_uses_fetched_spans(monkeypatch):
    fetched = [_ar(AttackCategory.SCOPE_VIOLATION, Verdict.FAIL, Severity.MED)]
    monkeypatch.setattr(analyst, "fetch_attack_spans", lambda project=None: fetched)

    report = analyze("redagent")

    sv = report.per_category[AttackCategory.SCOPE_VIOLATION]
    assert sv.success_rate == 1.0
    assert sv.severity == Severity.MED


def test_fetch_attack_spans_parses_attributes(monkeypatch):
    fake_spans = [
        {
            "attributes": {
                "attack.category": "PROMPT_LEAK",
                "attack.prompt": "leak it",
                "attack.response": "here you go...",
                "attack.verdict": "FAIL",
                "attack.severity": "HIGH",
                "attack.reason": "revealed prompt",
            }
        },
        {"attributes": {"some.other": "span"}},  # non-attack span ignored
    ]
    client = MagicMock()
    client.spans.get_spans.return_value = fake_spans
    monkeypatch.setattr(phoenix_query, "Client", lambda **kw: client)

    results = phoenix_query.fetch_attack_spans("redagent")

    assert len(results) == 1
    assert results[0].category == AttackCategory.PROMPT_LEAK
    assert results[0].verdict == Verdict.FAIL
    assert results[0].severity == Severity.HIGH
    assert results[0].response == "here you go..."
