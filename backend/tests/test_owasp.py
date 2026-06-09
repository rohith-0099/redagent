"""OWASP mapping tests — deterministic category → standard taxonomy."""

from core.contracts import AttackCategory
from core.owasp import owasp_for


def test_prompt_leak_maps_to_llm07():
    m = owasp_for(AttackCategory.PROMPT_LEAK)
    assert m.owasp_id == "LLM07"
    assert m.framework == "LLM"
    assert m.owasp_title == "System Prompt Leakage"


def test_jailbreak_maps_to_llm01():
    m = owasp_for(AttackCategory.JAILBREAK)
    assert m.owasp_id == "LLM01"
    assert m.framework == "LLM"


def test_scope_violation_maps_to_llm06():
    m = owasp_for(AttackCategory.SCOPE_VIOLATION)
    assert m.owasp_id == "LLM06"
    assert m.framework == "LLM"


def test_competitor_is_custom_with_no_fabricated_id():
    m = owasp_for(AttackCategory.COMPETITOR)
    assert m.owasp_id is None
    assert m.framework == "CUSTOM"
    assert m.owasp_title  # has a sensible title, not empty


def test_every_category_has_a_mapping():
    for cat in AttackCategory:
        m = owasp_for(cat)
        assert m.framework in ("LLM", "AGENTIC", "CUSTOM")
        # CUSTOM must not carry a fabricated OWASP id
        if m.framework == "CUSTOM":
            assert m.owasp_id is None
        else:
            assert m.owasp_id
