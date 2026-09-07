import Anthropic from "@anthropic-ai/sdk";
import { TOOL_DEFINITIONS, runTool, ToolInputError } from "../../tools/tools.js";
import { buildSystemPrompt } from "../../tools/systemPrompt.js";
import { validateChart } from "../../tools/chartValidator.js";

const MODEL = process.env.ANTHROPIC_MODEL || process.env.LIGHTHOUSE_MODEL || "claude-sonnet-5";
const MAX_TURNS = 6;
const MAX_CHART_CORRECTIONS = 2;

/**
 * Runs the tool-use loop against Claude: ask the model, execute any tool
 * calls it requests (data tools hit SQLite; render_chart is checked against
 * chartValidator.js and only accepted once it passes), feed the results
 * back, repeat until it produces a valid chart or gives up.
 *
 * `client` is injectable so tests can pass a fake with a scripted
 * `messages.create` instead of hitting the real API.
 */
export async function runConversation(history, apiKey, client) {
  const anthropic = client || new Anthropic({ apiKey });
  const messages = history.map((m) => ({ role: m.role, content: m.content }));
  let chart = null;
  let replyText = "";
  let chartCorrections = 0;

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
        const { valid, issues } = validateChart(block.input);
        // Self-correct silently, within the same turn -- the user only ever
        // sees the corrected chart, never a failed attempt. Bounded so a
        // stubborn model still gets an answer instead of nothing.
        if (valid || chartCorrections >= MAX_CHART_CORRECTIONS) {
          chart = block.input;
          toolResults.push({ type: "tool_result", tool_use_id: block.id, content: "Chart rendered and shown to the user." });
        } else {
          chartCorrections++;
          toolResults.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: `This chart won't render well:\n- ${issues.join("\n- ")}\nCall render_chart again with a fix.`,
            is_error: true,
          });
        }
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
