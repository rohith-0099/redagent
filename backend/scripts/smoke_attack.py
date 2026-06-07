"""Live smoke test: one category of attacks against a running target.

Proves the attacker pipeline end-to-end (ADK prompt-gen -> target -> judge).
Needs GEMINI_API_KEY in env and a reachable target (default VictimBot on :8080,
override with TARGET_URL).
"""

import asyncio
import os

from agents.attacker import run_attacks
from core.contracts import AttackCategory
from tools.target_client import TargetClient

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8080")
CATEGORY = AttackCategory.PROMPT_LEAK
PROMPTS = 2


async def main() -> None:
    target = TargetClient(TARGET_URL)
    healthy = await target.health()
    print(f"target @ {TARGET_URL} health: {healthy}")
    if not healthy:
        print("target unreachable — start VictimBot first. aborting.")
        return

    print(f"running {CATEGORY.value} x{PROMPTS} ...\n")
    results = await run_attacks(CATEGORY, target, PROMPTS)

    for i, r in enumerate(results, 1):
        print(f"[{i}] {r.verdict.value} / {r.severity.value}")
        print(f"    prompt:   {r.prompt[:140]}")
        print(f"    response: {r.response[:200]}")
        print(f"    reason:   {r.reason}\n")

    breached = sum(1 for r in results if r.verdict.value == "FAIL")
    print(f"summary: {breached}/{len(results)} attacks landed (FAIL = bot broke its rule)")


if __name__ == "__main__":
    asyncio.run(main())
