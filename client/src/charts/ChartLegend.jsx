import { colorForIndex } from "../lib/chartTheme.js";

// A legend is always present for 2+ series (the dependable identity channel);
// a single series needs no legend box -- the chart title already names it.
export default function ChartLegend({ series }) {
  if (!series || series.length < 2) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", padding: "4px 4px 12px" }}>
      {series.map((name, i) => (
        <span key={name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)" }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: colorForIndex(i), flexShrink: 0 }} />
          {name}
        </span>
      ))}
    </div>
  );
}
