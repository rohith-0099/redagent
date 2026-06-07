"""Static config + env loading. No secrets hardcoded (CLAUDE.md section 8)."""

import os

MODEL = "gemini-2.5"
MAX_ATTACKS = 30
TARGET_TIMEOUT = 10  # seconds; demo must never hang
DEFAULT_PROMPTS_PER = 5

# Read from env / Secret Manager only. None if unset (no API call this slice).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
