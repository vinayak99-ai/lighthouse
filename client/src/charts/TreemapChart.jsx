import { ResponsiveContainer, Treemap, Tooltip } from "recharts";
import { colorForIndex, formatCompact } from "../lib/chartTheme.js";

// A treemap needs Recharts' own nested shape ({ name, size, fill }), not the
// flat { x, <series key>: number } rows every other chart_type uses -- reuse
// that same input shape here (x = entity name, series[0] = the one metric
// each box is sized by, per chart_validator's "exactly one series" rule) and
// convert at render time, so the backend contract stays as small as possible.
function toTreemapData(data, valueKey) {
  return data
    .map((row, i) => ({ name: row.x, size: row[valueKey], fill: colorForIndex(i) }))
    .filter((d) => typeof d.size === "number" && d.size > 0);
}

function TreemapCell({ x, y, width, height, name, size, fill, unit }) {
  const canShowValue = width > 70 && height > 34;
  const canShowName = width > 40 && height > 18;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="var(--surface-1)" strokeWidth={2} rx={4} />
      {canShowName && (
        <text x={x + 8} y={y + 18} fill="#fff" fontSize={12} fontWeight={600}>
          {name}
        </text>
      )}
      {canShowValue && (
        <text x={x + 8} y={y + 34} fill="#fff" fontSize={11} fillOpacity={0.9}>
          {formatCompact(size, unit)}
        </text>
      )}
    </g>
  );
}

function TreemapTooltip({ active, payload, unit }) {
  if (!active || !payload || payload.length === 0) return null;
  const { name, size } = payload[0].payload;
  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "8px 12px",
        boxShadow: "var(--shadow-tooltip)",
        fontSize: 13,
      }}
    >
      <div style={{ color: "var(--text-primary)", fontWeight: 600 }}>{name}</div>
      <div style={{ color: "var(--text-secondary)", fontVariantNumeric: "tabular-nums" }}>{formatCompact(size, unit)}</div>
    </div>
  );
}

export default function TreemapChart({ data, series, unit }) {
  const treemapData = toTreemapData(data, series[0]);
  return (
    <ResponsiveContainer width="100%" height={340}>
      <Treemap
        data={treemapData}
        dataKey="size"
        nameKey="name"
        stroke="var(--surface-1)"
        animationDuration={500}
        animationEasing="ease-out"
        content={<TreemapCell unit={unit} />}
      >
        <Tooltip content={<TreemapTooltip unit={unit} />} />
      </Treemap>
    </ResponsiveContainer>
  );
}
