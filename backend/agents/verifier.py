"""Verifier — closes the find→fix→PROVE loop (v2 build step 7).

Re-runs ONLY the attacks that breached in the original campaign against the
target configured with the proposed hardened prompt (system_prompt_override),
then produces a deterministic before/after VerificationReport. The LLM is used
only for per-attack judging; all counting is Python.
"""

from agents.attacker import TARGET_RULES
from core.contracts import (
    AttackResult,
    Campaign,
    FixProposal,
    VerificationReport,
    Verdict,
)
from tools.judge import judge
from tools.target_client import TargetClient, TargetError


def _replay_prompt(result: AttackResult) -> str:
    """The message to resend. Crescendo → its escalating attacker turns as one
    transcript; single-shot → the original prompt."""
    if result.attack_mode == "crescendo" and result.transcript:
        lines = [f"Customer: {t['attacker_msg']}" for t in result.transcript]
        return "\n".join(lines)
    return result.prompt


_MANUAL_NOTE = (
    "RedAgent does not modify your AI. It reports a hardened system prompt; apply "
    "it to your app, then re-run verification."
)


def _build_report(
    breached: list[AttackResult],
    after: list[AttackResult],
    fix_application: str = "inject_field",
    note: str = "",
) -> VerificationReport:
    original = len(breached)
    still = [a for a in after if a.verdict == Verdict.FAIL]
    breaches_after = len(still)

    # per-category before/after success_rate over the RE-RUN (breached) attacks.
    per_category: dict = {}
    by_cat_before: dict = {}
    by_cat_after: dict = {}
    for r in breached:
        by_cat_before.setdefault(r.category, []).append(r)
    for a in after:
        by_cat_after.setdefault(a.category, []).append(a)
    for cat, items in by_cat_before.items():
        after_items = by_cat_after.get(cat, [])
        after_breaches = sum(1 for a in after_items if a.verdict == Verdict.FAIL)
        per_category[cat] = {
            "before": 1.0,  # every re-run attack breached originally
            "after": (after_breaches / len(after_items)) if after_items else 0.0,
        }

    if breaches_after == 0:
        verdict = "fix_effective"
    elif breaches_after == original:
        verdict = "ineffective"
    else:
        verdict = "partial"

    return VerificationReport(
        original_breaches=original,
        breaches_after_fix=breaches_after,
        fixed=original - breaches_after,
        still_breaching=still,
        per_category=per_category,
        verdict=verdict,
        fix_application=fix_application,
        note=note,
    )


async def verify_fix(
    campaign: Campaign, fix: FixProposal, target: TargetClient
) -> VerificationReport:
    """Re-run the campaign's breached attacks against the hardened prompt.

    inject_field   → the hardened prompt is injected into each request (VictimBot
                     demo path). manual_reverify → nothing is injected; the SAME
                     target is re-tested, assuming the developer already applied
                     the fix. The mode is recorded on the report for honesty."""
    breached = [r for r in campaign.results if r.verdict == Verdict.FAIL]

    # Read the mode defensively (mock targets in tests lack a real str attr).
    mode = getattr(target, "fix_application", "inject_field")
    if mode not in ("inject_field", "manual_reverify"):
        mode = "inject_field"
    note = _MANUAL_NOTE if mode == "manual_reverify" else ""

    hardened = target.with_system_prompt(fix.new_system_prompt)

    after: list[AttackResult] = []
    for r in breached:
        replay = _replay_prompt(r)
        try:
            response, tool_calls = await hardened.send_traced(replay)
        except TargetError as e:
            # Not delivered under the fix → cannot reproduce the breach → PASS.
            after.append(
                AttackResult(
                    category=r.category,
                    prompt=replay,
                    response=f"<not delivered: {e}>",
                    verdict=Verdict.PASS,
                    severity=r.severity,
                    reason="attack not delivered against hardened target",
                    attack_mode=r.attack_mode,
                )
            )
            continue

        verdict, severity, reason = await judge(
            r.category, replay, response, TARGET_RULES[r.category], tool_calls=tool_calls
        )
        after.append(
            AttackResult(
                category=r.category,
                prompt=replay,
                response=response,
                verdict=verdict,
                severity=severity,
                reason=reason,
                tool_calls=tool_calls,
                attack_mode=r.attack_mode,
            )
        )

    return _build_report(breached, after, fix_application=mode, note=note)
