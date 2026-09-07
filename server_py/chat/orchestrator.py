"""Provider-agnostic tool-use loop -- the Python equivalent of
server/src/chat/orchestrator.js, but written once against the LLMClient
Protocol (chat/llm_client.py) instead of once per SDK. The Node version
duplicates the loop in providers/anthropic.js and providers/openai.js
because each SDK returns a genuinely different response shape; here every
provider (Bedrock's own Converse API, or a corporate wrapper fronting
OpenAI/Anthropic/Gemini-family models -- see chat/providers/) normalizes
into the same LLMResponse at its own boundary, so the loop -- including
the self-correcting render_chart retry -- exists exactly once.
"""

from __future__ import annotations

import json
import os

from .llm_client import LLMClient, LLMResponse
from .providers.bedrock import CONVERSE_TOOLS
from ..tools.chart_validator import validate_chart
from ..tools.system_prompt import build_system_prompt
from ..tools.tools import ToolInputError, run_tool

MAX_TURNS = 6
MAX_CHART_CORRECTIONS = 2


def _resolve_provider() -> str | None:
    forced = (os.environ.get("LIGHTHOUSE_LLM_PROVIDER") or "").lower()
    if forced in ("bedrock", "corporate"):
        return forced
    if os.environ.get("LIGHTHOUSE_CORPORATE_LLM_MODEL"):
        return "corporate"
    if os.environ.get("BEDROCK_MODEL_ID") or os.environ.get("AWS_REGION"):
        return "bedrock"
    return None


def has_llm_client() -> bool:
    return _resolve_provider() is not None


def active_provider() -> str | None:
    return _resolve_provider()


def _build_client(provider: str) -> LLMClient:
    if provider == "bedrock":
        from .providers.bedrock import BedrockConverseClient

        return BedrockConverseClient()
    if provider == "corporate":
        from .providers.corporate import build_default_corporate_client

        return build_default_corporate_client()
    raise ValueError(f"Unknown provider: {provider}")


def active_model() -> str | None:
    """Reads the configured model name straight from the environment rather
    than constructing a client, so /api/health stays cheap and never fails
    just because boto3 isn't installed or the corporate wrapper isn't wired
    yet (see providers/bedrock.py, providers/corporate.py)."""
    provider = _resolve_provider()
    if provider == "bedrock":
        from .providers.bedrock import DEFAULT_MODEL_ID

        return os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
    if provider == "corporate":
        return os.environ.get("LIGHTHOUSE_CORPORATE_LLM_MODEL")
    return None


def _history_to_converse(history: list[dict]) -> list[dict]:
    """Frontend turns are always plain-text ({"role", "content": str}, see
    client/src/App.jsx) -- no image/array content to translate."""
    return [{"role": m["role"], "content": [{"text": m["content"]}]} for m in history]


def _tool_result(tool_use_id: str, text: str, *, status: str) -> dict:
    return {"toolResult": {"toolUseId": tool_use_id, "content": [{"text": text}], "status": status}}


def run_conversation(history: list[dict], client: LLMClient | None = None) -> dict:
    if client is None:
        provider = _resolve_provider()
        if provider is None:
            raise RuntimeError("No LLM client configured (set LIGHTHOUSE_LLM_PROVIDER=bedrock|corporate).")
        client = _build_client(provider)

    messages = _history_to_converse(history)
    chart: dict | None = None
    reply_text = ""
    chart_corrections = 0

    for _turn in range(MAX_TURNS):
        response: LLMResponse = client.create(system=build_system_prompt(), messages=messages, tools=CONVERSE_TOOLS)
        if response.text:
            reply_text = response.text

        assistant_content = []
        if response.text:
            assistant_content.append({"text": response.text})
        for tool_call in response.tool_calls:
            assistant_content.append({"toolUse": {"toolUseId": tool_call.id, "name": tool_call.name, "input": tool_call.input}})
        messages.append({"role": "assistant", "content": assistant_content})

        if not response.tool_calls:
            break

        tool_result_blocks = []
        for tool_call in response.tool_calls:
            if tool_call.name == "render_chart":
                result = validate_chart(tool_call.input)
                # Self-correct silently, within the same turn -- the user only
                # ever sees the corrected chart, never a failed attempt.
                # Bounded so a stubborn model still gets an answer instead of
                # nothing. Mirrors server/src/chat/providers/anthropic.js.
                if result["valid"] or chart_corrections >= MAX_CHART_CORRECTIONS:
                    chart = tool_call.input
                    tool_result_blocks.append(_tool_result(tool_call.id, "Chart rendered and shown to the user.", status="success"))
                else:
                    chart_corrections += 1
                    issues = "\n- ".join(result["issues"])
                    tool_result_blocks.append(
                        _tool_result(
                            tool_call.id,
                            f"This chart won't render well:\n- {issues}\nCall render_chart again with a fix.",
                            status="error",
                        )
                    )
                continue
            try:
                tool_output = run_tool(tool_call.name, tool_call.input)
                tool_result_blocks.append(_tool_result(tool_call.id, json.dumps(tool_output), status="success"))
            except ToolInputError as err:
                tool_result_blocks.append(_tool_result(tool_call.id, str(err), status="error"))
            except Exception as err:  # model-supplied args can trigger any query-layer error; surface it, don't crash the turn
                tool_result_blocks.append(_tool_result(tool_call.id, f"Tool failed: {err}", status="error"))

        messages.append({"role": "user", "content": tool_result_blocks})

        if chart:
            break

    return {"reply": reply_text or (chart.get("insight") if chart else None) or "Here's what I found.", "chart": chart}
