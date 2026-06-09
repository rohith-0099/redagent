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

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._config.timeout_seconds,
            transport=self._transport,
        )

    async def send(self, message: str) -> str:
        """Deliver one prompt to the target, return its extracted response text."""
        text, _ = await self.send_traced(message)
        return text

    async def send_traced(self, message: str) -> tuple[str, list[dict]]:
        """Deliver one prompt; return (response_text, tool_calls).

        tool_calls is the agentic tool-call trace extracted via tool_calls_path
        (each {"name", "args"}); empty list when the target exposes no trace.
        """
        body = _substitute(self._config.request_template, message)
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
        data = resp.json()
        text = _extract(data, self._config.response_path)
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

    Returns {"ok": True, "sample_reply": <text>} or {"ok": False, "error": <msg>}.
    Used by the UI/API to validate a TargetConfig before a campaign.
    """
    client = TargetClient(config=config, transport=transport)
    try:
        reply = await client.send("Hello")
    except TargetError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # malformed response_path / template extraction failure
        return {"ok": False, "error": f"could not parse target reply: {e}"}
    return {"ok": True, "sample_reply": reply}
