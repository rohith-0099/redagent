"""Phoenix query side — how the Analyst reads attack traces back.

Two paths, by design:
- phoenix_mcp_toolset(): the partner MCP (@arizeai/phoenix-mcp) wired as an ADK
  toolset, attached to the Analyst agent so it can query traces agentically
  (the hackathon "agent uses partner MCP" point).
- fetch_attack_spans(): a deterministic REST pull (phoenix client) used to build
  the authoritative VulnReport — LLMs can't be trusted to count success rates.
"""

from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from phoenix.client import Client

from core.config import PHOENIX_API_KEY, PHOENIX_COLLECTOR_ENDPOINT
from core.contracts import AttackCategory, AttackResult, Severity, Verdict

PROJECT = "redagent"


def phoenix_mcp_toolset() -> MCPToolset:
    """ADK toolset backed by the @arizeai/phoenix-mcp server (stdio/npx)."""
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@arizeai/phoenix-mcp@latest",
                    "--baseUrl",
                    PHOENIX_COLLECTOR_ENDPOINT or "http://localhost:6006",
                    "--apiKey",
                    PHOENIX_API_KEY or "",
                ],
            ),
            timeout=20,
        )
    )


def fetch_attack_spans(project: str = PROJECT) -> list[AttackResult]:
    """Pull attack spans for a project and rebuild them as AttackResults."""
    client = Client(
        base_url=PHOENIX_COLLECTOR_ENDPOINT or "http://localhost:6006",
        api_key=PHOENIX_API_KEY,
    )
    spans = client.spans.get_spans(project_identifier=project, limit=1000)

    results: list[AttackResult] = []
    for span in spans:
        attrs = span.get("attributes", {})
        if "attack.category" not in attrs:
            continue  # not one of our attack spans
        results.append(
            AttackResult(
                category=AttackCategory(attrs["attack.category"]),
                prompt=attrs.get("attack.prompt", ""),
                response=attrs.get("attack.response", ""),
                verdict=Verdict(attrs["attack.verdict"]),
                severity=Severity(attrs["attack.severity"]),
                reason=attrs.get("attack.reason", ""),
            )
        )
    return results
