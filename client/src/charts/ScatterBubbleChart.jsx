import { ResponsiveContainer, ScatterChart, Scatter, ZAxis, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { colorForIndex, formatCompact } from "../lib/chartTheme.js";

// A bubble chart is just a scatter chart where every point also carries a
// `z` value -- Recharts renders that as point radius via ZAxis, so this one
// component covers both; no separate "bubble" chart_type is needed.
const BUBBLE_RANGE = [80, 900]; // Recharts area range, px^2 -- min/max dot size

function ScatterTooltip({ active, payload, xUnit, yUnit, xLabel, yLabel, zLabel }) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: "8px 12px",
        boxShadow: "var(--shadow-tooltip)",
        fontSize: 13,
        minWidth: 180,
      }}
    >
      <div style={{ color: "var(--text-primary)", fontWeight: 600, marginBottom: 6 }}>{point.label}</div>
      <TooltipRow name={xLabel || "x"} value={formatCompact(point.x, xUnit)} />
      <TooltipRow name={yLabel || "y"} value={formatCompact(point.y, yUnit)} />
      {point.z !== undefined && point.z !== null && <TooltipRow name={zLabel || "z"} value={formatCompact(point.z)} />}
    </div>
  );
}

function TooltipRow({ name, value }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "2px 0" }}>
      <span style={{ color: "var(--text-secondary)" }}>{name}</span>
      <span style={{ color: "var(--text-primary)", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );
}

export default function ScatterBubbleChart({ data, series, unit, xUnit, xAxisLabel, yAxisLabel, zAxisLabel, hoveredSeries, hiddenSeries }) {
  const hasZ = data.some((row) => row.z !== undefined && row.z !== null);
  const groups = series && series.length > 0 ? series : ["value"];

  return (
    <div>
      {(xAxisLabel || yAxisLabel || (hasZ && zAxisLabel)) && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, fontSize: 12, color: "var(--text-muted)", padding: "0 4px 8px" }}>
          {xAxisLabel && <span>x: {xAxisLabel}</span>}
          {xAxisLabel && yAxisLabel && <span>·</span>}
          {yAxisLabel && <span>y: {yAxisLabel}</span>}
          {hasZ && zAxisLabel && (yAxisLabel || xAxisLabel) && <span>·</span>}
          {hasZ && zAxisLabel && <span>bubble size: {zAxisLabel}</span>}
        </div>
      )}
      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <CartesianGrid stroke="var(--gridline)" strokeWidth={1} />
          <XAxis
            type="number"
            dataKey="x"
            name={xAxisLabel}
            tickFormatter={(v) => formatCompact(v, xUnit)}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
          />
          <YAxis
            type="number"
            dataKey="y"
            name={yAxisLabel}
            tickFormatter={(v) => formatCompact(v, unit)}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={64}
          />
          {hasZ && <ZAxis type="number" dataKey="z" range={BUBBLE_RANGE} name={zAxisLabel} />}
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "var(--baseline)" }}
            content={<ScatterTooltip xUnit={xUnit} yUnit={unit} xLabel={xAxisLabel} yLabel={yAxisLabel} zLabel={zAxisLabel} />}
          />
          {groups.map((name, i) => {
            if (hiddenSeries?.has(name)) return null;
            const dimmed = hoveredSeries && hoveredSeries !== name;
            const points = data.filter((row) => (row.group ?? groups[0]) === name);
            return (
              <Scatter
                key={name}
                name={name}
                data={points}
                fill={colorForIndex(i)}
                fillOpacity={dimmed ? 0.35 : 0.85}
                animationDuration={500}
                animationEasing="ease-out"
                style={{ transition: "opacity 0.2s ease" }}
              />
            );
          })}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
