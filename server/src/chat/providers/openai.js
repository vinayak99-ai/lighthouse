import OpenAI from "openai";
import { TOOL_DEFINITIONS, runTool, ToolInputError } from "../../tools/tools.js";
import { buildSystemPrompt } from "../../tools/systemPrompt.js";

const MODEL = process.env.OPENAI_MODEL || "gpt-4o";
const MAX_TURNS = 6;

// Anthropic's tool shape is { name, description, input_schema }.
// OpenAI's function-calling shape wraps the same JSON schema differently.
function toOpenAiTools(defs) {
  return defs.map((d) => ({
    type: "function",
    function: { name: d.name, description: d.description, parameters: d.input_schema },
  }));
}

const OPENAI_TOOLS = toOpenAiTools(TOOL_DEFINITIONS);

/**
 * Same tool-use loop as the Anthropic provider, adapted to OpenAI's Chat
 * Completions function-calling shape: tool calls arrive on
 * `message.tool_calls`, and each result goes back as its own
 * { role: "tool", tool_call_id, content } message instead of a single
 * tool_result block.
 */
export async function runConversation(history, apiKey) {
  const client = new OpenAI({ apiKey });
  const messages = [
    { role: "system", content: buildSystemPrompt() },
    ...history.map((m) => ({ role: m.role, content: m.content })),
  ];
  let chart = null;
  let replyText = "";

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const response = await client.chat.completions.create({
      model: MODEL,
      messages,
      tools: OPENAI_TOOLS,
      tool_choice: "auto",
    });

    const message = response.choices[0].message;
    if (message.content) replyText = message.content.trim();
    messages.push(message);

    const toolCalls = message.tool_calls || [];
    if (toolCalls.length === 0) break;

    for (const call of toolCalls) {
      const args = safeParse(call.function.arguments);
      if (call.function.name === "render_chart") {
        chart = args;
        messages.push({ role: "tool", tool_call_id: call.id, content: "Chart rendered and shown to the user." });
        continue;
      }
      try {
        const result = runTool(call.function.name, args);
        messages.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(result) });
      } catch (err) {
        const errMessage = err instanceof ToolInputError ? err.message : `Tool failed: ${err.message}`;
        messages.push({ role: "tool", tool_call_id: call.id, content: errMessage });
      }
    }

    if (chart) break;
  }

  return { reply: replyText || chart?.insight || "Here's what I found.", chart };
}

function safeParse(json) {
  try {
    return JSON.parse(json || "{}");
  } catch {
    return {};
  }
}

export const MODEL_NAME = MODEL;
