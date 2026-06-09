"""Built-in request/response shapes for common target endpoints.

Each preset maps to (request_template, response_path). The attack prompt is
substituted wherever "{{PROMPT}}" appears in the template.

- simple_json: matches VictimBot exactly ({"message": ...} -> {"response": ...}).
- openai_chat: OpenAI /v1/chat/completions style body + nested response path.
"""

from core.contracts import Preset

# preset -> (request_template, response_path, tool_calls_path)
# tool_calls_path: dotted path to the tool-call trace, or None if the target
# exposes none. simple_json IS the VictimBot shape, which now returns tool_calls.
PRESETS: dict[Preset, tuple[dict, str, str | None]] = {
    Preset.SIMPLE_JSON: ({"message": "{{PROMPT}}"}, "response", "tool_calls"),
    Preset.OPENAI_CHAT: (
        {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "{{PROMPT}}"}],
        },
        "choices.0.message.content",
        None,
    ),
}
