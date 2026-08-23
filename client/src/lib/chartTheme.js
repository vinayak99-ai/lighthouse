// Categorical hues in fixed slot order -- never reassigned by rank, never
// cycled past 8. A palette that outgrows this list should fold into "Other"
// upstream (the backend already caps series at 8).
export const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
];

export function colorForIndex(i) {
  return SERIES_COLORS[i % SERIES_COLORS.length];
}

export function formatCompact(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (unit === "percent") return `${value.toFixed(2)}%`;
  const abs = Math.abs(value);
  const prefix = unit === "usd" ? "$" : "";
  if (abs >= 1e9) return `${prefix}${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${prefix}${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${prefix}${(value / 1e3).toFixed(1)}K`;
  return `${prefix}${value.toLocaleString(undefined, { maximumFractionDigits: unit === "percent" ? 2 : 0 })}`;
}

export function formatDateLabel(x) {
  const d = new Date(x + "T00:00:00Z");
  if (Number.isNaN(d.getTime())) return x;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}
