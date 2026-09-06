import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, Tooltip } from "recharts";
import { colorForIndex, formatCompact, formatDateLabel } from "../lib/chartTheme.js";
import ChartTooltip from "./ChartTooltip.jsx";

// The answer to "too many series for one overlay plot" (choosing-a-form.md's
// series-count ladder): past a handful, fold into "Other" or facet. This is
// the facet -- one small chart per entity, each free to use its own y-scale
// so a $900M entity isn't flattened to a flat line next to a $138B one.
export default function SmallMultiples({ data, series, unit }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
      {series.map((name, i) => (
        <Facet key={name} name={name} data={data} unit={unit} colorIndex={i} />
      ))}
    </div>
  );
}

function Facet({ name, data, unit, colorIndex }) {
  // Keyed by the real entity name (not a generic "v") so ChartTooltip's
  // dataKey-based label and color lookup resolve correctly, same as every
  // other chart component -- a generic key would show "v" in the tooltip
  // and fail the color-slot lookup (indexOf("v") in [name] is -1).
  const facetData = data.map((d) => ({ x: d.x, [name]: d[name] }));
  const last = [...facetData].reverse().find((d) => d[name] !== null && d[name] !== undefined)?.[name] ?? 0;

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "12px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: colorForIndex(colorIndex), flexShrink: 0 }} />
          {name}
        </span>
        <span style={{ fontSize: 12, color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>{formatCompact(last, unit)}</span>
      </div>
      <div style={{ height: 100 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={facetData} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--gridline)" strokeWidth={1} />
            <XAxis dataKey="x" hide />
            <Tooltip
              content={<ChartTooltip unit={unit} seriesOrder={[name]} />}
              cursor={{ stroke: "var(--baseline)", strokeWidth: 1 }}
            />
            <Line
              type="monotone"
              dataKey={name}
              stroke={colorForIndex(colorIndex)}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
        <span>{formatDateLabel(facetData[0]?.x)}</span>
        <span>{formatDateLabel(facetData[facetData.length - 1]?.x)}</span>
      </div>
    </div>
  );
}
