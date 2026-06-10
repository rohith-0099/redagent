"""RedAgent FastAPI app — SSE-enabled campaign API."""

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import (
    approve_and_fix,
    get_campaign,
    start_campaign,
    verify_campaign,
)
from core.contracts import Preset, TargetConfig
from tools.regression_export import export_regression_suite, render_pytest_file
from tools.target_client import test_connection

app = FastAPI(title="RedAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# campaign_id → asyncio.Queue used for live SSE streaming while pipeline runs.
_campaign_queues: dict[str, asyncio.Queue] = {}


class CampaignRequest(BaseModel):
    target_url: str
    target_description: str = ""
    target_config: TargetConfig | None = None


class TestConnectionRequest(BaseModel):
    target_url: str
    target_config: TargetConfig | None = None


@app.post("/target/test")
async def target_test(body: TestConnectionRequest):
    """Send one harmless probe to validate a target before launching a campaign.

    Mirrors the campaign launch path: an explicit target_config is used as-is;
    otherwise the simple_json /chat shape is built from target_url."""
    config = body.target_config or TargetConfig(
        url=f"{body.target_url.rstrip('/')}/chat", preset=Preset.SIMPLE_JSON
    )
    return await test_connection(config)


@app.post("/campaign", status_code=201)
async def create_campaign(body: CampaignRequest):
    campaign_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    _campaign_queues[campaign_id] = q
    asyncio.create_task(
        start_campaign(
            target_url=body.target_url,
            target_description=body.target_description,
            target_config=body.target_config,
            campaign_id=campaign_id,
            _progress=q,
        )
    )
    return {"campaign_id": campaign_id}


@app.get("/campaign/{campaign_id}/stream")
async def stream_campaign(campaign_id: str):
    q = _campaign_queues.get(campaign_id)

    if q is not None:
        # Live path: drain the queue until the sentinel (None) arrives.
        async def live_events() -> AsyncGenerator[str, None]:
            while True:
                item = await q.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"

        return StreamingResponse(live_events(), media_type="text/event-stream")

    # Static path: campaign finished before the client connected — replay from store.
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def static_events() -> AsyncGenerator[str, None]:
        for r in campaign.results:
            yield f"data: {json.dumps({'type': 'attack_result', 'result': r.model_dump()})}\n\n"
        if campaign.report:
            yield f"data: {json.dumps({'type': 'report_ready', 'report': campaign.report.model_dump()})}\n\n"

    return StreamingResponse(static_events(), media_type="text/event-stream")


@app.get("/campaign/{campaign_id}/report")
async def get_report(campaign_id: str):
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.report is None:
        raise HTTPException(status_code=404, detail="Report not ready yet")
    return campaign.report


@app.post("/campaign/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign = await approve_and_fix(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return campaign.fix


@app.post("/campaign/{campaign_id}/verify")
async def verify_campaign_route(campaign_id: str):
    """Re-run the campaign's breached attacks against the approved fix and return
    the before/after VerificationReport. 404 if unknown; 409 if no fix yet."""
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign = await verify_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return campaign.verification


@app.get("/campaign/{campaign_id}/export")
async def export_campaign(campaign_id: str, format: str = "json"):
    """Export the campaign's breaches as a replayable regression suite (CI/CD).

    format=json (default) → the machine-readable suite; format=pytest → a drop-in
    pytest file as a download. 404 if the campaign is unknown or has no results."""
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.results:
        raise HTTPException(status_code=404, detail="Campaign has no results to export")

    suite = export_regression_suite(campaign)
    if format == "pytest":
        return PlainTextResponse(
            render_pytest_file(suite),
            headers={
                "Content-Disposition": "attachment; filename=test_redagent_regression.py"
            },
        )
    return suite


@app.get("/campaign/{campaign_id}")
async def get_campaign_state(campaign_id: str):
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
