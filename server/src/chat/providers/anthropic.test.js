import test from "node:test";
import assert from "node:assert/strict";
import { seedAll } from "../../data/seed.js";
import { runConversation } from "./anthropic.js";

test.before(() => {
  seedAll();
});

const BAD_CHART = {
  chart_type: "area",
  title: "TVL",
  series: ["Aave", "Lido"], // area + 2 series -> invalid
  data: [{ x: "2026-01-01", Aave: 1, Lido: 2 }],
};

const GOOD_CHART = {
  chart_type: "line",
  title: "TVL",
  series: ["Aave", "Lido"],
  data: [{ x: "2026-01-01", Aave: 1, Lido: 2 }],
};

function renderChartBlock(id, input) {
  return { type: "tool_use", id, name: "render_chart", input };
}

test("an invalid render_chart call is corrected within the same turn, invisibly", async () => {
  let call = 0;
  const capturedMessages = [];
  const fakeClient = {
    messages: {
      create: async ({ messages }) => {
        call++;
        capturedMessages.push(structuredClone(messages));
        if (call === 1) {
          return { content: [renderChartBlock("call_1", BAD_CHART)] };
        }
        return { content: [renderChartBlock("call_2", GOOD_CHART)] };
      },
    },
  };

  const result = await runConversation([{ role: "user", content: "chart TVL" }], "fake-key", fakeClient);

  assert.equal(call, 2, "should have retried exactly once after the bad chart");
  assert.deepEqual(result.chart, GOOD_CHART);

  // The second request must carry the corrective feedback from the first attempt.
  const secondRequestMessages = capturedMessages[1];
  const toolResultMsg = secondRequestMessages.find(
    (m) => m.role === "user" && Array.isArray(m.content) && m.content.some((c) => c.type === "tool_result")
  );
  const toolResultText = toolResultMsg.content[0].content;
  assert.match(toolResultText, /won't render well/i);
  assert.match(toolResultText, /muddy band/i);
});

test("gives up after 2 corrections and accepts the last attempt rather than returning nothing", async () => {
  let call = 0;
  const fakeClient = {
    messages: {
      create: async () => {
        call++;
        // Always invalid -- the loop must still terminate with *something*.
        return { content: [renderChartBlock(`call_${call}`, BAD_CHART)] };
      },
    },
  };

  const result = await runConversation([{ role: "user", content: "chart TVL" }], "fake-key", fakeClient);

  // 1 initial attempt + 2 corrections = 3 calls, then the 3rd is accepted best-effort.
  assert.equal(call, 3);
  assert.deepEqual(result.chart, BAD_CHART);
});

test("a valid chart on the first try is accepted with no retry", async () => {
  let call = 0;
  const fakeClient = {
    messages: {
      create: async () => {
        call++;
        return { content: [renderChartBlock("call_1", GOOD_CHART)] };
      },
    },
  };

  const result = await runConversation([{ role: "user", content: "chart TVL" }], "fake-key", fakeClient);

  assert.equal(call, 1);
  assert.deepEqual(result.chart, GOOD_CHART);
});
