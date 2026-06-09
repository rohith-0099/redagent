"""Static config + env loading. No secrets hardcoded (CLAUDE.md section 8)."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Auto-load repo-root .env so no manual shell export is needed.
# config.py -> core -> backend -> redagent (repo root).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = "gemini-2.5-flash"
MAX_ATTACKS = 30
TARGET_TIMEOUT = 30  # seconds; Vertex Flash ~2-5s, 30s is safe margin
DEFAULT_PROMPTS_PER = 5

# Read from env / Secret Manager only. None if unset.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PHOENIX_API_KEY = os.environ.get("PHOENIX_API_KEY")
PHOENIX_COLLECTOR_ENDPOINT = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")

# Vertex AI switch. When true, genai.Client uses ADC + the vars below.
# Set GOOGLE_GENAI_USE_VERTEXAI=1 for billing-project quota (no free-tier cap).
# Fallback: AI Studio (GEMINI_API_KEY) when this is false/unset.
USE_VERTEX = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("true", "1")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
