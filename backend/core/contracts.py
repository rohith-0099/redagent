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
    # Dotted path to a tool-call trace in the response (agentic targets). None =
    # target exposes no tool trace. Filled from preset when not set.
    tool_calls_path: str | None = None
    # Verifier only: a hardened system prompt to test, injected as a top-level
    # "system_prompt_override" field in the request body. None for normal attacks.
    system_prompt_override: str | None = None
    # How the Verifier applies a fix when re-testing:
    #   inject_field   = inject system_prompt_override into the request (only
    #                    works for targets that honor it, e.g. our VictimBot demo).
    #   manual_reverify= inject NOTHING; re-test the SAME target, assuming the
    #                    developer already applied the hardened prompt on their side.
    fix_application: Literal["inject_field", "manual_reverify"] = "inject_field"
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
    # Agentic categories (OWASP Agentic Top 10) — target an agent with tools.
    GOAL_HIJACK = "GOAL_HIJACK"
    TOOL_MISUSE = "TOOL_MISUSE"


class ReconReport(BaseModel):
    """Benign-probe profile of the target, produced by the Recon agent.

    Feeds the Strategist (plan tailoring) and Attacker (discovered_context
    replaces any hardcoded demo data). All defaulted so empty recon is valid."""

    target_purpose: str = ""
    discovered_tools: list[str] = Field(default_factory=list)
    refusal_style: str = ""
    exploitable_surface: list[str] = Field(default_factory=list)
    # Concrete identifiers/entities the target revealed (e.g. order ids, names).
    discovered_context: dict = Field(default_factory=dict)
    notes: str = ""


class AttackPlan(BaseModel):
    categories: list[AttackCategory]
    prompts_per: int
    attack_mode: str = "single_shot"  # "single_shot" | "crescendo"


class AttackResult(BaseModel):
    category: AttackCategory
    prompt: str
    response: str
    verdict: Verdict
    severity: Severity
    reason: str
    # Tool-call trace (agentic attacks). Each: {"name": str, "args": dict}.
    # For crescendo, this is the breaching turn's trace. Empty otherwise.
    tool_calls: list[dict] = Field(default_factory=list)
    attack_mode: str = "single_shot"  # "single_shot" | "crescendo"
    # Crescendo only: per-turn records
    # {turn_index, attacker_msg, target_response, tool_calls}. Empty single-shot.
    transcript: list[dict] = Field(default_factory=list)
    breach_turn: int | None = None  # 1-based turn the breach occurred on


class CategoryReport(BaseModel):
    """Per-category rollup inside a VulnReport.

    owasp_* / framework tag the finding to an industry-standard taxonomy
    (populated by the Analyst via core.owasp). Defaults keep hand-built reports
    valid; owasp_id is None for CUSTOM categories (no fabricated IDs).
    """

    success_rate: float
    severity: Severity
    examples: list[AttackResult]
    owasp_id: str | None = None
    owasp_title: str = "Unmapped"
    framework: str = "CUSTOM"


class VulnReport(BaseModel):
    per_category: dict[AttackCategory, CategoryReport]


class FixProposal(BaseModel):
    new_system_prompt: str
    guards: list[str]
    rationale: str


class FinalResult(BaseModel):
    before: VulnReport
    after: VulnReport


class VerificationReport(BaseModel):
    """Proof a fix holds: re-run the breached attacks against the hardened prompt.

    per_category maps each affected category to {"before": rate, "after": rate}.
    verdict: 'fix_effective' (0 still breach) | 'partial' | 'ineffective'.
    """

    original_breaches: int
    breaches_after_fix: int
    fixed: int
    still_breaching: list[AttackResult] = Field(default_factory=list)
    per_category: dict[AttackCategory, dict[str, float]] = Field(default_factory=dict)
    verdict: str
    # Which fix-application mode was used to re-test (honesty: did RedAgent inject
    # the hardened prompt, or re-test a target the developer hardened themselves).
    fix_application: str = "inject_field"
    note: str = ""


class Campaign(BaseModel):
    """Run state for a single red-teaming campaign."""

    campaign_id: str
    status: str = "created"  # created | running | awaiting_approval | done
    # How to reach the target — stored so a regression suite is self-contained
    # and replayable (CI/CD export, v2 step 10).
    target_config: TargetConfig | None = None
    recon: ReconReport | None = None
    plan: AttackPlan | None = None
    results: list[AttackResult] = Field(default_factory=list)
    report: VulnReport | None = None
    fix: FixProposal | None = None
    final: FinalResult | None = None
    verification: VerificationReport | None = None
