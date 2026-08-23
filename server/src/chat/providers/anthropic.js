import Anthropic from "@anthropic-ai/sdk";
import { TOOL_DEFINITIONS, runTool, ToolInputError } from "../../tools/tools.js";
import { buildSystemPrompt } from "../../tools/systemPrompt.js";

const MODEL = process.env.ANTHROPIC_MODEL || process.env.LIGHTHOUSE_MODEL || "claude-sonnet-5";
const MAX_TURNS = 6;

/**
 * Runs the tool-use loop against Claude: ask the model, execute any tool
 * calls it requests (data tools hit SQLite; render_chart is captured, not
 * executed), feed the results back, repeat until it produces a chart or
 * gives up.
 */
export async function runConversation(history, apiKey) {
  const anthropic = new Anthropic({ apiKey });
  const messages = history.map((m) => ({ role: m.role, content: m.content }));
  let chart = null;
  let replyText = "";

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 4096,
      system: buildSystemPrompt(),
      tools: TOOL_DEFINITIONS,
      messages,
    });

    const text = response.content
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("\n")
      .trim();
    if (text) replyText = text;

    const toolUseBlocks = response.content.filter((b) => b.type === "tool_use");
    messages.push({ role: "assistant", content: response.content });

    if (toolUseBlocks.length === 0) break;

    const toolResults = [];
    for (const block of toolUseBlocks) {
      if (block.name === "render_chart") {
        chart = block.input;
        toolResults.push({ type: "tool_result", tool_use_id: block.id, content: "Chart rendered and shown to the user." });
        continue;
      }
      try {
        const result = runTool(block.name, block.input);
        toolResults.push({ type: "tool_result", tool_use_id: block.id, content: JSON.stringify(result) });
      } catch (err) {
        const message = err instanceof ToolInputError ? err.message : `Tool failed: ${err.message}`;
        toolResults.push({ type: "tool_result", tool_use_id: block.id, content: message, is_error: true });
      }
    }
    messages.push({ role: "user", content: toolResults });

    if (chart) break;
  }

  return { reply: replyText || chart?.insight || "Here's what I found.", chart };
}

export const MODEL_NAME = MODEL;
