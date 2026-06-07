"""Static config + env loading. No secrets hardcoded (CLAUDE.md section 8)."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Auto-load repo-root .env so no manual shell export is needed.
# config.py -> core -> backend -> redagent (repo root).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = "gemini-2.5-flash"
MAX_ATTACKS = 30
TARGET_TIMEOUT = 10  # seconds; demo must never hang
DEFAULT_PROMPTS_PER = 5

# Read from env / Secret Manager only. None if unset.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PHOENIX_API_KEY = os.environ.get("PHOENIX_API_KEY")
PHOENIX_COLLECTOR_ENDPOINT = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
