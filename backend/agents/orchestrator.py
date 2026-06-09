"""Campaign orchestrator — sequences the four agents.

Pipeline: Strategist → Attacker → Analyst → [HUMAN GATE] → Defender

Human approval is a HARD pause (CLAUDE.md section 6): start_campaign() stops
at status=awaiting_approval. Defender only runs when approve_and_fix() is
called explicitly.
"""

import asyncio
import uuid
from pathlib import Path

from agents.analyst import build_vuln_report
from agents.attacker import run_attacks
from agents.defender import propose_fix
from agents.strategist import plan_campaign
from core.contracts import AttackResult, Campaign, TargetConfig
from core.state import store
from tools.target_client import TargetClient

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Maps campaign_id → current system prompt of the target (needed by Defender).
_system_prompts: dict[str, str] = {}


def _read_victim_prompt() -> str:
    path = _REPO_ROOT / "victim" / "system_prompt.txt"
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


async def start_campaign(
    target_url: str,
    target_description: str = "",
    current_system_prompt: str = "",
    campaign_id: str | None = None,
    target_config: TargetConfig | None = None,
    _progress: asyncio.Queue | None = None,
) -> str:
    """Run Strategist → Attacker → Analyst and pause for human approval.

    Returns the campaign_id. Campaign status will be 'awaiting_approval'.
    target_config: how to call an arbitrary target. When None, a default
                   simple_json config is built from target_url (VictimBot shape).
    _progress: optional asyncio.Queue for SSE streaming; receives dicts +
               a None sentinel when the pipeline reaches awaiting_approval.
    """
    campaign_id = campaign_id or str(uuid.uuid4())
    campaign = Campaign(campaign_id=campaign_id)
    store.create(campaign)
    _system_prompts[campaign_id] = current_system_prompt or _read_victim_prompt()

    # --- Strategist ---
    campaign.status = "running"
    store.update(campaign)

    plan = await plan_campaign(target_description)
    campaign.plan = plan
    store.update(campaign)

    # --- Attacker (one category at a time) ---
    if target_config is not None:
        target = TargetClient(config=target_config)
    else:
        target = TargetClient(base_url=target_url)
    all_results: list[AttackResult] = []
    for category in plan.categories:
        results = await run_attacks(category, target, plan.prompts_per)
        all_results.extend(results)
        if _progress:
            for r in results:
                await _progress.put({"type": "attack_result", "result": r.model_dump()})

    campaign.results = all_results
    store.update(campaign)

    # --- Analyst (deterministic rollup — no Phoenix refetch needed) ---
    report = build_vuln_report(all_results)
    campaign.report = report
    campaign.status = "awaiting_approval"
    store.update(campaign)

    if _progress:
        await _progress.put({"type": "report_ready", "report": report.model_dump()})
        await _progress.put(None)  # sentinel: stream closed

    return campaign_id


def get_campaign(campaign_id: str) -> Campaign:
    """Return current Campaign state."""
    return store.get(campaign_id)


async def approve_and_fix(campaign_id: str) -> Campaign:
    """Run the Defender and write the FixProposal. Hard-requires awaiting_approval.

    This is the human-approval gate (CLAUDE.md section 6). Calling this
    without human sign-off is a process violation, not a code bug.
    """
    campaign = store.get(campaign_id)
    if campaign is None:
        raise KeyError(campaign_id)
    if campaign.status != "awaiting_approval":
        raise ValueError(
            f"Campaign {campaign_id!r} not awaiting approval "
            f"(current status: {campaign.status!r})"
        )

    system_prompt = _system_prompts.get(campaign_id, "")
    fix = await propose_fix(campaign.report, system_prompt)
    campaign.fix = fix
    campaign.status = "done"
    store.update(campaign)
    return campaign
