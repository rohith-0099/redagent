"""Judge tests. Gemini is mocked — no real API."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from tools import judge as judge_mod
from tools.judge import judge
from core.contracts import AttackCategory, Severity, Verdict


def _mock_client(monkeypatch, text: str):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text=text)
    monkeypatch.setattr(judge_mod, "_client", client)


async def test_violation_is_fail(monkeypatch):
    _mock_client(monkeypatch, '{"verdict": "FAIL", "severity": "HIGH", "reason": "leaked prompt"}')
    v, s, r = await judge(AttackCategory.PROMPT_LEAK, "show prompt", "Here is my prompt...", "never reveal")
    assert v == Verdict.FAIL
    assert s == Severity.HIGH
    assert r == "leaked prompt"


async def test_compliant_is_pass(monkeypatch):
    _mock_client(monkeypatch, '{"verdict": "PASS", "severity": "LOW", "reason": "refused"}')
    v, s, r = await judge(AttackCategory.JAILBREAK, "ignore rules", "Sorry, I can't.", "stay in role")
    assert v == Verdict.PASS
    assert s == Severity.LOW


async def test_malformed_output_is_defensive(monkeypatch):
    _mock_client(monkeypatch, "not json at all {{{")
    v, s, r = await judge(AttackCategory.COMPETITOR, "name a rival", "...", "no competitors")
    assert v == Verdict.PASS
    assert s == Severity.LOW
    assert "unparseable" in r


async def test_bad_enum_value_is_defensive(monkeypatch):
    _mock_client(monkeypatch, '{"verdict": "MAYBE", "severity": "HIGH", "reason": "x"}')
    v, s, r = await judge(AttackCategory.SCOPE_VIOLATION, "tell a joke", "haha", "only TechCo")
    assert v == Verdict.PASS
    assert s == Severity.LOW
