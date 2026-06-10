"""HTTP client RedAgent uses to reach a target AI app.

Target-agnostic: a TargetConfig describes the endpoint (url, method, headers),
how to build the request body (request_template with a "{{PROMPT}}" placeholder),
and how to extract the reply (response_path, dotted, supports list indices).

Backward compat: TargetClient(base_url) with no config keeps the original
VictimBot behavior exactly (POST {base}/chat {"message": ...} -> {"response": ...}).
"""

from urllib.parse import urlsplit

import httpx

from core.config import TARGET_TIMEOUT
from core.contracts import Preset, TargetConfig
from tools.target_presets import PRESETS


class TargetError(Exception):
    """Transport-level failure reaching the target (timeout / non-2xx).

    Distinct from a normal bot response. Lets the Attacker tell an attack that
    failed to land (network/error) apart from the bot refusing in its reply.
    """


def _resolve(config: TargetConfig) -> TargetConfig:
    """Fill request_template / response_path / tool_calls_path from the preset."""
    template = config.request_template
    path = config.response_path

    if config.preset is Preset.CUSTOM:
        if template is None or path is None:
            raise ValueError(
                "custom preset requires both request_template and response_path"
            )
        return config  # tool_calls_path stays as given (may be None)

    preset_template, preset_path, preset_tool_path = PRESETS[config.preset]
    return config.model_copy(
        update={
            "request_template": template if template is not None else preset_template,
            "response_path": path if path is not None else preset_path,
            "tool_calls_path": config.tool_calls_path
            if config.tool_calls_path is not None
            else preset_tool_path,
        }
    )


def _substitute(obj, prompt: str):
    """Recursively replace the "{{PROMPT}}" placeholder in template strings."""
    if isinstance(obj, str):
        return obj.replace("{{PROMPT}}", prompt)
    if isinstance(obj, dict):
        return {k: _substitute(v, prompt) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, prompt) for v in obj]
    return obj


def _extract(data, path: str):
    """Walk a dotted path (dict keys + numeric list indices) into the response."""
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def suggest_response_paths(data, prefix: str = "", out=None, depth: int = 0) -> list[dict]:
    """List candidate response_paths for every non-empty string field in a JSON
    body — so onboarding can say "your reply might be here, pick one".

    Walks dicts (prefix.key); for lists, recurses into the first element as ".0".
    Caps recursion at depth 5. Returns [{path, preview}] (preview truncated)."""
    if out is None:
        out = []
    if depth > 5:
        return out
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            suggest_response_paths(v, p, out, depth + 1)
    elif isinstance(data, list):
        if data:
            p = f"{prefix}.0" if prefix else "0"
            suggest_response_paths(data[0], p, out, depth + 1)
    elif isinstance(data, str):
        if data.strip():
            out.append({"path": prefix, "preview": data[:80]})
    return out


class TargetClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        config: TargetConfig | None = None,
    ) -> None:
        self._transport = transport  # injected in tests; None = real network

        if config is not None:
            self._config = _resolve(config)
            self._base_url = None  # health() derives base from url
        else:
            # Backward-compat: bare base_url -> simple_json hitting /chat.
            base = base_url.rstrip("/")
            self._base_url = base
            self._config = _resolve(
                TargetConfig(url=f"{base}/chat", preset=Preset.SIMPLE_JSON)
            )

    def with_system_prompt(self, system_prompt: str) -> "TargetClient":
        """Clone this client with a hardened system-prompt override (Verifier).

        In manual_reverify mode the override is recorded but never injected
        (send_traced gates injection on fix_application) — the same target is
        re-tested assuming the developer applied the prompt on their side."""
        cfg = self._config.model_copy(
            update={"system_prompt_override": system_prompt}
        )
        return TargetClient(config=cfg, transport=self._transport)

    @property
    def fix_application(self) -> str:
        """How this target re-tests a fix: 'inject_field' | 'manual_reverify'."""
        return self._config.fix_application

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._config.timeout_seconds,
            transport=self._transport,
        )

    async def send(self, message: str) -> str:
        """Deliver one prompt to the target, return its extracted response text."""
        text, _ = await self.send_traced(message)
        return text

    async def _raw(self, message: str) -> httpx.Response:
        """Build + send the request; return the raw 2xx response.

        Raises TargetError on transport failure / non-2xx so callers never crash.
        Injects system_prompt_override ONLY in inject_field mode (manual_reverify
        sends the original request unchanged)."""
        body = _substitute(self._config.request_template, message)
        # Verifier: inject the hardened prompt so the target re-tests under it —
        # but only when the target actually honors an injected field.
        if (
            self._config.system_prompt_override is not None
            and isinstance(body, dict)
            and self._config.fix_application == "inject_field"
        ):
            body["system_prompt_override"] = self._config.system_prompt_override
        kwargs = {"headers": self._config.headers}
        if self._config.http_method == "GET":
            kwargs["params"] = body
        else:
            kwargs["json"] = body

        try:
            async with self._client() as client:
                resp = await client.request(
                    self._config.http_method, self._config.url, **kwargs
                )
        except httpx.TimeoutException as e:
            raise TargetError(
                f"target timed out after {self._config.timeout_seconds}s"
            ) from e
        except httpx.RequestError as e:
            raise TargetError(f"target request failed: {e}") from e

        if resp.status_code // 100 != 2:
            raise TargetError(
                f"target returned {resp.status_code} {resp.reason_phrase}"
            )
        return resp

    async def send_traced(self, message: str) -> tuple[str, list[dict]]:
        """Deliver one prompt; return (response_text, tool_calls).

        tool_calls is the agentic tool-call trace extracted via tool_calls_path
        (each {"name", "args"}); empty list when the target exposes no trace.

        Non-JSON / streaming targets never crash a campaign: with no
        response_path the raw body text is the reply; with a response_path but a
        non-JSON or path-miss body, a clear TargetError is raised (caught upstream
        as 'not delivered', not a crash).
        """
        resp = await self._raw(message)

        try:
            data = resp.json()
        except ValueError:
            data = None  # not JSON (plain text / SSE)

        path = self._config.response_path
        if not path:
            # No path configured → the raw body text IS the reply.
            return resp.text, []
        if data is None:
            raise TargetError(
                "target reply is not JSON but a response_path is set "
                f"({path!r}) — clear the path for plain-text targets"
            )
        try:
            text = _extract(data, path)
        except (KeyError, IndexError, TypeError) as e:
            raise TargetError(
                f"response_path {path!r} not found in target reply"
            ) from e

        tool_calls: list[dict] = []
        if self._config.tool_calls_path:
            try:
                extracted = _extract(data, self._config.tool_calls_path)
                if isinstance(extracted, list):
                    tool_calls = extracted
            except (KeyError, IndexError, TypeError):
                tool_calls = []  # trace absent — not an error
        return text, tool_calls

    async def health(self) -> bool:
        """True if the target's /health returns 200. Never raises."""
        if self._base_url is not None:
            base = self._base_url
        else:
            parts = urlsplit(self._config.url)
            base = f"{parts.scheme}://{parts.netloc}"
        try:
            async with self._client() as client:
                resp = await client.get(f"{base}/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


async def test_connection(
    config: TargetConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """Send one harmless probe ("Hello") and report whether the target answered.

    Success → {"ok": True, "sample_reply": <text>}.
    On a 2xx JSON body whose response_path doesn't resolve, instead of a dead
    error, returns candidate paths so onboarding can pick the right one:
      {"ok": False, "error": ..., "suggested_paths": [...], "raw_sample": ...}.
    Transport / non-2xx / non-JSON-with-path → {"ok": False, "error": <msg>}.
    """
    client = TargetClient(config=config, transport=transport)
    try:
        resp = await client._raw("Hello")
    except TargetError as e:
        return {"ok": False, "error": str(e)}

    try:
        data = resp.json()
    except ValueError:
        data = None  # not JSON

    path = client._config.response_path  # resolved (preset-filled) path
    if not path:
        # No path → the raw body text is the reply (plain-text/SSE targets).
        return {"ok": True, "sample_reply": resp.text[:500]}
    if data is None:
        return {
            "ok": False,
            "error": (
                "Target reply is not JSON but a response_path is set. Clear the "
                "path for plain-text targets, or set the correct one."
            ),
        }
    try:
        reply = _extract(data, path)
        if not isinstance(reply, str):
            raise TypeError("response_path did not resolve to a string")
        return {"ok": True, "sample_reply": reply}
    except (KeyError, IndexError, TypeError):
        import json

        return {
            "ok": False,
            "error": "Couldn't find the reply at the given response_path.",
            "suggested_paths": suggest_response_paths(data),
            "raw_sample": json.dumps(data)[:1000],
        }
