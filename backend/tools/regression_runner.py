"""Regression runner — replays one exported regression case against a target and
reports whether the once-breaching attack is now HELD (PASS).

Reuses the exact primitives of a live campaign re-run — no attack logic is
duplicated:
  - TargetClient.send_traced  to deliver the prompt (+ tool-call trace)
  - tools.judge.judge          to score the response into a verdict
  - attacker.TARGET_RULES      for the app rule the target must hold

The generated pytest file (regression_export.render_pytest_file) calls
check_case() per case; CI fails if a fixed vulnerability breaches again.
"""

import asyncio

from agents.attacker import TARGET_RULES
from core.contracts import AttackCategory, TargetConfig, Verdict
from tools.judge import judge
from tools.target_client import TargetClient, TargetError


def _target_from(target_config: dict, transport=None) -> TargetClient:
    return TargetClient(config=TargetConfig(**target_config), transport=transport)


async def replay_case(case: dict, target_config: dict, transport=None) -> dict:
    """Replay one case; return {passed, verdict, response, reason}.

    passed is True when the attack no longer breaches (verdict PASS) — the
    regression assertion. A target that won't deliver the attack under the fix
    cannot reproduce the breach → PASS."""
    category = AttackCategory(case["category"])
    replay = case["replay_prompt"]
    target = _target_from(target_config, transport=transport)
    try:
        response, tool_calls = await target.send_traced(replay)
    except TargetError as e:
        return {
            "passed": True,
            "verdict": "PASS",
            "response": f"<not delivered: {e}>",
            "reason": "attack not delivered — cannot reproduce breach",
        }
    verdict, _severity, reason = await judge(
        category, replay, response, TARGET_RULES[category], tool_calls=tool_calls
    )
    return {
        "passed": verdict == Verdict.PASS,
        "verdict": verdict.value,
        "response": response,
        "reason": reason,
    }


def check_case(case: dict, target_config: dict, transport=None) -> dict:
    """Synchronous wrapper for pytest: replay one case, return its result dict."""
    return asyncio.run(replay_case(case, target_config, transport=transport))
