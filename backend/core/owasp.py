"""Single source of truth: AttackCategory → OWASP standard mapping.

Maps each red-team category to an industry-standard taxonomy so the VulnReport
is credible to security/compliance teams. Deterministic Python — no LLM.

Frameworks:
- "LLM"     → OWASP LLM Top 10 (2025)
- "AGENTIC" → OWASP Agentic Top 10 (2026)
- "CUSTOM"  → no clean standard fit; owasp_id is None (we do NOT fabricate IDs)
"""

from dataclasses import dataclass

from core.contracts import AttackCategory


@dataclass(frozen=True)
class OwaspMapping:
    owasp_id: str | None  # None for CUSTOM — never invent an ID
    owasp_title: str
    framework: str  # "LLM" | "AGENTIC" | "CUSTOM"


# COMPETITOR has no clean OWASP fit: it's a brand/content-policy guardrail, not
# Excessive Agency (which is unauthorized *actions*). Marked CUSTOM, no ID.
_MAPPING: dict[AttackCategory, OwaspMapping] = {
    AttackCategory.PROMPT_LEAK: OwaspMapping("LLM07", "System Prompt Leakage", "LLM"),
    AttackCategory.JAILBREAK: OwaspMapping("LLM01", "Prompt Injection", "LLM"),
    AttackCategory.SCOPE_VIOLATION: OwaspMapping("LLM06", "Excessive Agency", "LLM"),
    AttackCategory.COMPETITOR: OwaspMapping(None, "Brand/Policy Violation", "CUSTOM"),
}

# Future agentic categories slot in here once their AttackCategory values exist:
#   GOAL_HIJACK -> OwaspMapping("ASI01", "Agent Goal Hijacking", "AGENTIC")
#   TOOL_MISUSE -> OwaspMapping("ASI02", "Tool Misuse", "AGENTIC")

_UNMAPPED = OwaspMapping(None, "Unmapped", "CUSTOM")


def owasp_for(category: AttackCategory) -> OwaspMapping:
    """Return the OWASP mapping for a category. Unknown → CUSTOM/Unmapped."""
    return _MAPPING.get(category, _UNMAPPED)
