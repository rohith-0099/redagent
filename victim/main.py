"""VictimBot — TechCo support bot, the attack target.

DELIBERATELY NAIVE: no input filtering, no jailbreak defense, no output
guardrails. Weakness is the point — RedAgent attacks this to find holes.
Do NOT harden this file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Load repo-root .env (same file the backend reads).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Gemini 2.5 family (CLAUDE.md). Bare "gemini-2.5" is not a valid model id,
# so we pin the resolvable flash variant.
MODEL = "gemini-2.5-flash"
# Generous timeout — Vertex Flash responds in ~2-5s; 25s avoids false timeouts
# without letting the demo hang.
TIMEOUT = 25  # seconds

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

# Mirror the backend's Vertex AI switch (CLAUDE.md section 5).
# GOOGLE_GENAI_USE_VERTEXAI=1 → ADC (no api_key). Else AI Studio key.
_use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
if _use_vertex:
    _client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        http_options=types.HttpOptions(timeout=TIMEOUT * 1000),
    )
else:
    _api_key = os.environ.get("GEMINI_API_KEY")
    _client = (
        genai.Client(
            api_key=_api_key,
            http_options=types.HttpOptions(timeout=TIMEOUT * 1000),
        )
        if _api_key
        else None
    )

app = FastAPI(title="VictimBot")


class ChatRequest(BaseModel):
    message: str


def generate(message: str) -> str:
    # NAIVE on purpose: user message goes straight to Gemini, no sanitizing.
    resp = _client.models.generate_content(
        model=MODEL,
        contents=message,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return resp.text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    return {"response": generate(req.message)}
