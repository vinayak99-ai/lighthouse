import * as anthropicProvider from "./providers/anthropic.js";
import * as openaiProvider from "./providers/openai.js";

// Provider selection: an explicit LLM_PROVIDER wins; otherwise whichever API
// key is present decides, Anthropic first. Both tool-calling loops speak the
// same tool/render_chart contract (server/src/tools/tools.js), so swapping
// providers changes nothing else in the app.
function resolveProvider() {
  const forced = process.env.LLM_PROVIDER?.toLowerCase();
  if (forced === "openai" && process.env.OPENAI_API_KEY) return "openai";
  if (forced === "anthropic" && process.env.ANTHROPIC_API_KEY) return "anthropic";
  if (process.env.ANTHROPIC_API_KEY) return "anthropic";
  if (process.env.OPENAI_API_KEY) return "openai";
  return null;
}

export function hasApiKey() {
  return resolveProvider() !== null;
}

export function activeProvider() {
  return resolveProvider();
}

export function activeModel() {
  const provider = resolveProvider();
  if (provider === "anthropic") return anthropicProvider.MODEL_NAME;
  if (provider === "openai") return openaiProvider.MODEL_NAME;
  return null;
}

export async function runConversation(history) {
  const provider = resolveProvider();
  if (provider === "anthropic") return anthropicProvider.runConversation(history, process.env.ANTHROPIC_API_KEY);
  if (provider === "openai") return openaiProvider.runConversation(history, process.env.OPENAI_API_KEY);

  const err = new Error("No LLM API key configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY).");
  err.code = "NO_API_KEY";
  throw err;
}
