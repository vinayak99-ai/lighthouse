"""Reference LLMClient implementation against AWS Bedrock's Converse API.

boto3's bedrock-runtime `converse()` call normalizes tool-calling across
every model family Bedrock hosts (Anthropic, Amazon Nova, Meta Llama,
Mistral, Cohere...) into one request/response shape -- exactly the "parse
the response and pick only the real value" problem the corporate wrapper
adapter (chat/providers/corporate.py) also solves, except here AWS has
already done the normalizing, so this file is mostly the concrete, working
half of the design: real enough to run against a live Bedrock endpoint,
and boto3-client-injectable so tests never need real AWS credentials.

boto3 is imported lazily (inside __init__) so nothing about running the
app against the corporate provider, or against no live LLM at all,
requires boto3 to even be installed.
"""

from __future__ import annotations

import os
from typing import Any

from ..llm_client import LLMResponse, ToolCall
from ...tools.tools import TOOL_DEFINITIONS

DEFAULT_MODEL_ID = "anthropic.claude-sonnet-5-20251101-v1:0"


def to_converse_tools(tool_defs: list[dict] = TOOL_DEFINITIONS) -> list[dict]:
    """TOOL_DEFINITIONS already carries Anthropic's {name, description,
    input_schema} tool shape -- Converse wraps the same JSON Schema as
    {toolSpec: {name, description, inputSchema: {json}}}."""
    return [
        {
            "toolSpec": {
                "name": d["name"],
                "description": d["description"],
                "inputSchema": {"json": d["input_schema"]},
            }
        }
        for d in tool_defs
    ]


CONVERSE_TOOLS = to_converse_tools()


def parse_converse_response(response: dict[str, Any]) -> LLMResponse:
    message = response["output"]["message"]
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in message.get("content", []):
        if "text" in block:
            text_parts.append(block["text"])
        elif "toolUse" in block:
            tool_use = block["toolUse"]
            tool_calls.append(ToolCall(id=tool_use["toolUseId"], name=tool_use["name"], input=tool_use.get("input") or {}))
    return LLMResponse(text="\n".join(text_parts).strip(), tool_calls=tool_calls, stop_reason=response.get("stopReason"))


class BedrockConverseClient:
    """`boto_client` is injectable so tests can pass a fake with a
    scripted `converse()` instead of hitting real AWS."""

    def __init__(self, model_id: str | None = None, region: str | None = None, boto_client: Any = None):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        if boto_client is not None:
            self._client = boto_client
        else:
            import boto3

            self._client = boto3.client("bedrock-runtime", region_name=region or os.environ.get("AWS_REGION"))

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        response = self._client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=messages,
            toolConfig={"tools": tools, "toolChoice": {"auto": {}}},
        )
        return parse_converse_response(response)
