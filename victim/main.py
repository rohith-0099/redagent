"""VictimBot — TechCo support bot, the attack target.

DELIBERATELY NAIVE: no input filtering, no jailbreak defense, no output
guardrails. Weakness is the point — RedAgent attacks this to find holes.
Do NOT harden this file.
"""

import os
from pathlib import Path

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Gemini 2.5 family (CLAUDE.md). Bare "gemini-2.5" is not a valid model id,
# so we pin the resolvable flash variant.
MODEL = "gemini-2.5-flash"
TIMEOUT = 10  # seconds; demo must never hang (CLAUDE.md section 8)

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

# Secret read from env only — never hardcoded (CLAUDE.md section 8).
_api_key = os.environ.get("GEMINI_API_KEY")
if _api_key:
    genai.configure(api_key=_api_key)

app = FastAPI(title="VictimBot")


class ChatRequest(BaseModel):
    message: str


def generate(message: str) -> str:
    # NAIVE on purpose: user message goes straight to Gemini, no sanitizing.
    model = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT)
    resp = model.generate_content(message, request_options={"timeout": TIMEOUT})
    return resp.text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")
    return {"response": generate(req.message)}
