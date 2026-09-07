"""Adapter for an internal/corporate Python chat-completions package --
the integration point for "we have python packages with chat completions
functions and we can choose to use openai or anthropic or gemini... we
will need to parse the response and pick only the real value response and
use it for our purposes."

This file is the two-way translation CorporateLLMClient does at its own
boundary so the rest of the app never sees your wrapper's wire shape:

1. OUTBOUND -- convert.py's Converse-shaped `messages`/`tools` (the shape
   every LLMClient in this app is written against, see chat/llm_client.py)
   into whichever wire shape your wrapper's underlying model family
   expects: OpenAI-style `messages`/`tools` (also what most
   OpenAI-compatible corporate gateways expect regardless of the actual
   model behind them, Gemini included), or Anthropic-style
   `messages`/`system`/`tools`.
2. INBOUND -- `_parse_openai_response` / `_parse_anthropic_response` pick
   the real text and tool-call arguments out of whatever your wrapper
   function returns -- an SDK response object or a plain dict, since a
   lot of internal wrappers re-serialize the SDK object before handing it
   back.

`build_default_corporate_client()` is deliberately left unwired: swap in
the actual import and call signature of your package, and it plugs
straight into orchestrator.py with no other code changes.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Literal

from ..llm_client import LLMResponse, ToolCall

ResponseFormat = Literal["openai", "anthropic"]


# ---------------------------------------------------------------------------
# Outbound: Converse-shaped tools/messages -> wire shape
# ---------------------------------------------------------------------------


def to_openai_tools(converse_tools: list[dict]) -> list[dict]:
    out = []
    for t in converse_tools:
        spec = t["toolSpec"]
        out.append({"type": "function", "function": {"name": spec["name"], "description": spec["description"], "parameters": spec["inputSchema"]["json"]}})
    return out


def to_anthropic_tools(converse_tools: list[dict]) -> list[dict]:
    out = []
    for t in converse_tools:
        spec = t["toolSpec"]
        out.append({"name": spec["name"], "description": spec["description"], "input_schema": spec["inputSchema"]["json"]})
    return out


def converse_messages_to_openai(messages: list[dict], system: str) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        content = m.get("content") or []
        tool_results = [b["toolResult"] for b in content if "toolResult" in b]
        if tool_results:
            for tr in tool_results:
                text = "".join(c.get("text", "") for c in tr.get("content", []))
                out.append({"role": "tool", "tool_call_id": tr["toolUseId"], "content": text})
            continue
        text_parts = [b["text"] for b in content if "text" in b]
        tool_uses = [b["toolUse"] for b in content if "toolUse" in b]
        msg: dict[str, Any] = {"role": m["role"], "content": "\n".join(text_parts) or None}
        if tool_uses:
            msg["tool_calls"] = [
                {"id": tu["toolUseId"], "type": "function", "function": {"name": tu["name"], "arguments": json.dumps(tu.get("input") or {})}}
                for tu in tool_uses
            ]
        out.append(msg)
    return out


def converse_messages_to_anthropic(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        blocks = []
        for b in m.get("content") or []:
            if "text" in b:
                blocks.append({"type": "text", "text": b["text"]})
            elif "toolUse" in b:
                tu = b["toolUse"]
                blocks.append({"type": "tool_use", "id": tu["toolUseId"], "name": tu["name"], "input": tu.get("input") or {}})
            elif "toolResult" in b:
                tr = b["toolResult"]
                text = "".join(c.get("text", "") for c in tr.get("content", []))
                blocks.append({"type": "tool_result", "tool_use_id": tr["toolUseId"], "content": text, "is_error": tr.get("status") == "error"})
        out.append({"role": m["role"], "content": blocks})
    return out


# ---------------------------------------------------------------------------
# Inbound: wire response -> LLMResponse ("pick only the real value response")
# ---------------------------------------------------------------------------


def _field(obj: Any, name: str, default: Any = None) -> Any:
    """Reads `name` off `obj` whether it's an SDK object (attribute) or a
    plain dict -- the shape a wrapper hands back varies by team."""
    if hasattr(obj, name):
        return getattr(obj, name)
    return obj.get(name, default) if isinstance(obj, dict) else default


def parse_openai_response(raw: Any) -> LLMResponse:
    choice = _field(raw, "choices")[0]
    message = _field(choice, "message")
    text = _field(message, "content") or ""
    raw_tool_calls = _field(message, "tool_calls")
    tool_calls: list[ToolCall] = []
    for tc in raw_tool_calls or []:
        fn = _field(tc, "function")
        arguments = _field(fn, "arguments")
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(id=_field(tc, "id"), name=_field(fn, "name"), input=args))
    return LLMResponse(text=text.strip() if isinstance(text, str) else "", tool_calls=tool_calls)


def parse_anthropic_response(raw: Any) -> LLMResponse:
    content = _field(raw, "content")
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in content:
        block_type = _field(block, "type")
        if block_type == "text":
            text_parts.append(_field(block, "text"))
        elif block_type == "tool_use":
            tool_calls.append(ToolCall(id=_field(block, "id"), name=_field(block, "name"), input=_field(block, "input") or {}))
    return LLMResponse(text="\n".join(text_parts).strip(), tool_calls=tool_calls)


class CorporateLLMClient:
    """Wraps an internal chat-completions function so it satisfies the
    LLMClient protocol every other part of this app is written against."""

    def __init__(
        self,
        call_fn: Callable[..., Any],
        *,
        response_format: ResponseFormat,
        model: str,
        extra_kwargs: dict[str, Any] | None = None,
    ):
        self.call_fn = call_fn
        self.response_format = response_format
        self.model = model
        self.extra_kwargs = extra_kwargs or {}

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        if self.response_format == "openai":
            raw = self.call_fn(
                model=self.model,
                messages=converse_messages_to_openai(messages, system),
                tools=to_openai_tools(tools),
                tool_choice="auto",
                **self.extra_kwargs,
            )
            return parse_openai_response(raw)
        if self.response_format == "anthropic":
            raw = self.call_fn(
                model=self.model,
                system=system,
                messages=converse_messages_to_anthropic(messages),
                tools=to_anthropic_tools(tools),
                **self.extra_kwargs,
            )
            return parse_anthropic_response(raw)
        raise ValueError(f"Unknown response_format: {self.response_format}")


def build_default_corporate_client() -> CorporateLLMClient:
    """Wire this up to the real internal package before setting
    LIGHTHOUSE_LLM_PROVIDER=corporate:

        from my_company.llm import chat_completion  # your actual import

        return CorporateLLMClient(
            call_fn=chat_completion,
            response_format="openai",  # or "anthropic", matching what chat_completion returns
            model=os.environ["LIGHTHOUSE_CORPORATE_LLM_MODEL"],
        )

    Left raising so a misconfigured deploy fails loudly at startup instead
    of silently never calling any model.
    """
    raise NotImplementedError(
        "Wire build_default_corporate_client() (server_py/chat/providers/corporate.py) to your "
        "internal chat-completions package: import its function, pass it as call_fn to "
        "CorporateLLMClient, and set response_format to whichever shape it returns."
    )
