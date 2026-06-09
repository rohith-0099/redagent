"""JSON contracts shared across all RedAgent agents.

Agents communicate ONLY through these models (CLAUDE.md section 6).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from core.config import TARGET_TIMEOUT


class Preset(str, Enum):
    """Named request/response shape for a target. CUSTOM = user supplies both."""

    SIMPLE_JSON = "simple_json"
    OPENAI_CHAT = "openai_chat"
    CUSTOM = "custom"


class TargetConfig(BaseModel):
    """How to call an arbitrary chatbot/agent HTTP endpoint.

    request_template / response_path may be left None when a non-CUSTOM preset
    fills them (resolved in tools.target_client). The attack prompt is
    substituted wherever the string "{{PROMPT}}" appears in request_template.
    """

    url: str
    http_method: Literal["POST", "GET"] = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    request_template: dict | None = None
    response_path: str | None = None
    timeout_seconds: int = TARGET_TIMEOUT
    preset: Preset = Preset.SIMPLE_JSON


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
