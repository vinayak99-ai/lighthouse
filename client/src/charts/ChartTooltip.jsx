import { colorForIndex, formatCompact, formatDateLabel } from "../lib/chartTheme.js";

export default function ChartTooltip({ active, payload, label, unit, seriesOrder }) {
  if (!active || !payload || payload.length === 0) return null;
  const order = seriesOrder || payload.map((p) => p.dataKey);
  const rows = [...payload].sort((a, b) => order.indexOf(a.dataKey) - order.indexOf(b.dataKey));

  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "8px 12px",
        boxShadow: "var(--shadow-tooltip)",
        fontSize: 13,
        minWidth: 160,
      }}
    >
      <div style={{ color: "var(--text-muted)", marginBottom: 6, fontSize: 12 }}>{formatDateLabel(label)}</div>
      {rows.map((row) => {
        const idx = order.indexOf(row.dataKey);
        return (
          <div key={row.dataKey} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "2px 0" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: colorForIndex(idx), flexShrink: 0 }} />
              {row.dataKey}
            </span>
            <span style={{ color: "var(--text-primary)", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
              {formatCompact(row.value, unit)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
