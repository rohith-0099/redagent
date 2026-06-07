"""JSON contracts shared across all RedAgent agents.

Agents communicate ONLY through these models (CLAUDE.md section 6).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class Severity(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class AttackCategory(str, Enum):
    PROMPT_LEAK = "PROMPT_LEAK"
    JAILBREAK = "JAILBREAK"
    COMPETITOR = "COMPETITOR"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"


class AttackPlan(BaseModel):
    categories: list[AttackCategory]
    prompts_per: int


class AttackResult(BaseModel):
    category: AttackCategory
    prompt: str
    response: str
    verdict: Verdict
    severity: Severity
    reason: str


class CategoryReport(BaseModel):
    """Per-category rollup inside a VulnReport."""

    success_rate: float
    severity: Severity
    examples: list[AttackResult]


class VulnReport(BaseModel):
    per_category: dict[AttackCategory, CategoryReport]


class FixProposal(BaseModel):
    new_system_prompt: str
    guards: list[str]
    rationale: str


class FinalResult(BaseModel):
    before: VulnReport
    after: VulnReport


class Campaign(BaseModel):
    """Run state for a single red-teaming campaign."""

    campaign_id: str
    status: str = "created"  # created | running | awaiting_approval | done
    plan: AttackPlan | None = None
    results: list[AttackResult] = Field(default_factory=list)
    report: VulnReport | None = None
    fix: FixProposal | None = None
    final: FinalResult | None = None
