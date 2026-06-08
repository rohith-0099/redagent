"""Shared Gemini retry policy.

All Gemini call sites (direct google.genai + ADK runner) go through this
module. Retry only on transient errors (503 UNAVAILABLE, 429 RESOURCE
EXHAUSTED). Raise immediately on non-transient errors (400, 401, etc.).
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

RETRIES = 4
BASE_DELAY = 2.0  # seconds; doubles each attempt → 2, 4, 8, 16

_TRANSIENT_STATUS = {429, 503}
_TRANSIENT_KEYWORDS = {
    "503",
    "429",
    "unavailable",
    "resource exhausted",
    "quota exceeded",
    "rate limit",
}


def _is_transient(exc: Exception) -> bool:
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(code, int) and code in _TRANSIENT_STATUS:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in _TRANSIENT_KEYWORDS)


async def with_retry(fn, *, retries: int = RETRIES, base_delay: float = BASE_DELAY):
    """Call async callable fn(), retrying on transient Gemini errors.

    Raises immediately on non-transient errors. After max retries raises
    RuntimeError with the last transient exception as cause.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as exc:
            if not _is_transient(exc):
                raise
            last_exc = exc
            if attempt < retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Gemini transient error (attempt %d/%d): %s — retrying in %.0fs",
                    attempt + 1,
                    retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    raise RuntimeError(
        f"Gemini call failed after {retries} retries: {last_exc}"
    ) from last_exc


async def adk_run(runner, *, user_id: str, session_id: str, new_message) -> str:
    """Consume runner.run_async and return final response text, with retry.

    All ADK agent call sites use this instead of a bare async-for loop.
    """

    async def _invoke() -> str:
        text = ""
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_message
        ):
            if event.is_final_response() and event.content:
                text = event.content.parts[0].text
        return text

    return await with_retry(_invoke)
