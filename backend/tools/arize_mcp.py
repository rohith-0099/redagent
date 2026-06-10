"""Arize Phoenix tracing — write side.

Every attack the Attacker fires is recorded as a Phoenix span/trace
(category, prompt, response, verdict, severity, reason). This is pure
instrumentation (CLAUDE.md section 6) — it must never alter or break attack
logic. When Phoenix isn't configured it no-ops silently.

The MCP query side (agents READING traces) lands with the Analyst slice.
"""

from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
from phoenix.otel import register

from core.config import PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT
from core.contracts import AttackResult

_PROJECT = "redagent"
_tracer = None  # set on first real use; stays None when unconfigured


def setup_tracing():
    """Register the Phoenix exporter + google-genai auto-instrumentation."""
    global _tracer
    # endpoint is intentionally NOT passed: register() reads
    # PHOENIX_COLLECTOR_ENDPOINT from env and normalizes a Phoenix Cloud space
    # URL to the correct /s/<space>/v1/traces path. Passing it explicitly skips
    # that normalization and POSTs to the bare space URL -> 405.
    provider = register(
        api_key=PHOENIX_API_KEY,
        project_name=_PROJECT,
        protocol="http/protobuf",
        batch=True,
        set_global_tracer_provider=True,
    )
    GoogleGenAIInstrumentor().instrument(tracer_provider=provider)
    _tracer = provider.get_tracer(__name__)
    return _tracer


def _tracer_or_init():
    if _tracer is not None:
        return _tracer
    if not PHOENIX_COLLECTOR_ENDPOINT:
        return None  # tracing disabled — no network, no-op
    return setup_tracing()


def record_attack(result: AttackResult) -> None:
    """Emit one Phoenix span for a fired attack. No-op if tracing is off."""
    tracer = _tracer_or_init()
    if tracer is None:
        return
    with tracer.start_as_current_span(f"attack:{result.category.value}") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("attack.category", result.category.value)
        span.set_attribute("attack.prompt", result.prompt)
        span.set_attribute("attack.response", result.response)
        span.set_attribute("attack.verdict", result.verdict.value)
        span.set_attribute("attack.severity", result.severity.value)
        span.set_attribute("attack.reason", result.reason)


def record_recon_probe(probe: str, response: str, tool_calls: list[dict]) -> None:
    """Emit one Phoenix span for a benign recon probe. No-op if tracing is off.

    Uses recon.* attributes (NOT attack.*) so the Analyst — which counts spans
    carrying attack.category — never mistakes a probe for an attack/breach."""
    tracer = _tracer_or_init()
    if tracer is None:
        return
    with tracer.start_as_current_span("recon:probe") as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("recon.probe", probe)
        span.set_attribute("recon.response", response)
        span.set_attribute("recon.tool_calls", str([c.get("name") for c in tool_calls]))
