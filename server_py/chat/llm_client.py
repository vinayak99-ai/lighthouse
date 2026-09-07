"""Common LLM tool-calling interface every provider implements, so the
tool-use loop in orchestrator.py is written exactly once and works
unchanged against AWS Bedrock's Converse API or a corporate Python
chat-completions wrapper routed through Bedrock to an
OpenAI/Anthropic/Gemini-family model.

Unlike the Node version (server/src/chat/providers/{anthropic,openai}.js),
which each hand-roll the tool-use loop against their own SDK's response
shape, every LLMClient here returns the same normalized LLMResponse --
so "parse the response and pick only the real value response" (the
integration need described for the corporate wrapper) happens once, at
each provider's own boundary, not duplicated in the orchestration loop.

Messages passed to `create()` use AWS Bedrock Converse's own shape:
    [{"role": "user" | "assistant",
      "content": [{"text": "..."}] | [{"toolUse": {...}}] | [{"toolResult": {...}}]}]
Converse already IS the industry's unified tool-calling format across
model providers hosted on Bedrock, so every adapter -- Bedrock itself, or
a corporate wrapper fronting a differently-shaped SDK -- translates into
and out of this one shape at its own boundary, instead of the
orchestrator knowing about several different wire formats.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None


class LLMClient(Protocol):
    """Anything that can run one turn of a tool-calling conversation."""

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...
