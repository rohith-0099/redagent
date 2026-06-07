"""HTTP client RedAgent uses to reach a target AI app (e.g. VictimBot).

Target-agnostic: works with any endpoint exposing POST /chat ({message} ->
{response}) and GET /health.
"""

import httpx

from core.config import TARGET_TIMEOUT


class TargetError(Exception):
    """Transport-level failure reaching the target (timeout / non-2xx).

    Distinct from a normal bot response. Lets the Attacker tell an attack that
    failed to land (network/error) apart from the bot refusing in its reply.
    """


class TargetClient:
    def __init__(
        self, base_url: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport  # injected in tests; None = real network

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=TARGET_TIMEOUT,
            transport=self._transport,
        )

    async def send(self, message: str) -> str:
        """Deliver one prompt to the target, return its response text."""
        try:
            async with self._client() as client:
                resp = await client.post("/chat", json={"message": message})
        except httpx.TimeoutException as e:
            raise TargetError(f"target timed out after {TARGET_TIMEOUT}s") from e
        except httpx.RequestError as e:
            raise TargetError(f"target request failed: {e}") from e

        if resp.status_code // 100 != 2:
            raise TargetError(
                f"target returned {resp.status_code} {resp.reason_phrase}"
            )
        return resp.json()["response"]

    async def health(self) -> bool:
        """True if the target's /health returns 200. Never raises."""
        try:
            async with self._client() as client:
                resp = await client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
