// Codifies the same chart-design rules the system prompt asks the model to
// follow (server/src/tools/systemPrompt.js) and the dataviz skill's
// choosing-a-form.md documents, as an enforced backend check rather than
// prose the model might not perfectly follow. Used two ways:
//
// 1. The live LLM providers (chat/providers/{anthropic,openai}.js) run this
//    right after a render_chart tool call, BEFORE showing anything to the
//    user. A failure never reaches the chat -- it goes back to the model as
//    a corrective tool_result so it can retry with a fixed chart_type or
//    re-bucketed data, all within the same turn. The user only ever sees
//    the corrected result, never the failed attempt: "build, self-check,
//    correct" without breaking the one-question-one-answer conversational
//    shape.
// 2. The offline fallback router asserts its own output always passes this
//    (see fallbackRouter.test.js) as a regression guard, since its
//    heuristics were hand-tuned against these same rules separately.

const MAX_SERIES = 8;
const STACKED_BAR_BAR_LIMIT = 16;
const LINE_OVERLAY_SERIES_LIMIT = 6;
const SCATTER_POINT_LIMIT = 200;

// scatter's row shape is fundamentally different from every other
// chart_type: a row is one entity's point ({ label, x, y, z?, group? }),
// not a time/category bucket with one column per series -- so it gets its
// own checks instead of the generic per-series-column ones below.
function validateScatter(series, data) {
  const issues = [];

  if (data.length > SCATTER_POINT_LIMIT) {
    issues.push(
      `scatter has ${data.length} points, over the ${SCATTER_POINT_LIMIT}-point readability cap. Aggregate or filter down to the entities that matter most.`
    );
  }

  const groupNames = new Set(series);
  let badRows = 0;
  const badGroups = new Set();
  for (const row of data) {
    const xOk = typeof row.x === "number" && !Number.isNaN(row.x);
    const yOk = typeof row.y === "number" && !Number.isNaN(row.y);
    const labelOk = typeof row.label === "string" && row.label !== "";
    if (!(xOk && yOk && labelOk)) badRows++;
    const group = row.group ?? series[0];
    if (!groupNames.has(group)) badGroups.add(group);
  }

  if (badRows > 0) {
    issues.push(
      `${badRows} of ${data.length} scatter points are missing a numeric \`x\`, numeric \`y\`, or a non-empty \`label\` -- every point needs all three.`
    );
  }
  if (badGroups.size > 0) {
    issues.push(
      `These point \`group\` values don't match any entry in \`series\`: ${[...badGroups].join(", ")}. Every point's group must be one of the declared series names.`
    );
  }

  return issues;
}

export function validateChart(chart) {
  const issues = [];

  if (!chart || typeof chart !== "object") {
    return { valid: false, issues: ["render_chart received no chart object."] };
  }

  const { chart_type, series, data } = chart;

  if (!Array.isArray(series) || series.length === 0) {
    issues.push("`series` is empty -- there's nothing to render. Include at least one series.");
    return { valid: false, issues }; // nothing else is checkable without series
  }

  if (!Array.isArray(data) || data.length === 0) {
    issues.push("`data` is empty -- there are no points to plot. Re-check the tool result before calling render_chart.");
    return { valid: false, issues };
  }

  if (series.length > MAX_SERIES) {
    issues.push(
      `\`series\` has ${series.length} entries, over the ${MAX_SERIES}-series cap. Keep the largest ones and fold the rest into "Other".`
    );
  }

  if (chart_type === "scatter") {
    issues.push(...validateScatter(series, data));
    return { valid: issues.length === 0, issues };
  }

  if (chart_type === "area" && series.length > 1) {
    issues.push(
      "chart_type 'area' with more than one independent series overlaps into a muddy band (or misrepresents the entities if stacked). Use 'line' for a multi-entity trend instead."
    );
  }

  if (chart_type === "stacked_bar" && data.length > STACKED_BAR_BAR_LIMIT) {
    issues.push(
      `stacked_bar has ${data.length} bars, which reads as an unreadable barcode past ~${STACKED_BAR_BAR_LIMIT}. Re-query with a coarser granularity (week or month).`
    );
  }

  if (chart_type === "line" && series.length > LINE_OVERLAY_SERIES_LIMIT) {
    issues.push(
      `A line chart with ${series.length} overlapping series is hard to read past ~${LINE_OVERLAY_SERIES_LIMIT}. Use chart_type 'small_multiples' instead so each entity gets its own small chart.`
    );
  }

  const seriesWithNoData = series.filter((name) => !data.some((row) => row[name] !== undefined && row[name] !== null));
  if (seriesWithNoData.length > 0) {
    issues.push(
      `These series never appear with a value in any data row, so they'd render as empty: ${seriesWithNoData.join(", ")}. Remove them or check the data mapping.`
    );
  }

  return { valid: issues.length === 0, issues };
}
