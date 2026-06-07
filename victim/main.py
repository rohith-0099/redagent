"""VictimBot — TechCo support bot, the attack target.

DELIBERATELY NAIVE: no input filtering, no jailbreak defense, no output
guardrails. Weakness is the point — RedAgent attacks this to find holes.
Do NOT harden this file.
"""

import os
from pathlib import Path

from google import genai
from google.genai import types
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Gemini 2.5 family (CLAUDE.md). Bare "gemini-2.5" is not a valid model id,
# so we pin the resolvable flash variant.
MODEL = "gemini-2.5-flash"
TIMEOUT = 10  # seconds; demo must never hang (CLAUDE.md section 8)

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

# Secret read from env only — never hardcoded (CLAUDE.md section 8).
# HttpOptions.timeout is in milliseconds for the google.genai client.
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
