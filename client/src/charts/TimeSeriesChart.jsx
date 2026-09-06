import { useId } from "react";
import { ResponsiveContainer, LineChart, Line, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { colorForIndex, formatCompact, formatDateLabel } from "../lib/chartTheme.js";
import ChartTooltip from "./ChartTooltip.jsx";

export default function TimeSeriesChart({ type, data, series, unit, hoveredSeries, hiddenSeries }) {
  // Area fill is only correct for a SINGLE series -- with 2+ independent
  // series sharing a zero baseline, unstacked fills overlap and blend into a
  // muddy band, and stacking them would misrepresent independent entities
  // (e.g. three protocols' TVL) as a meaningful cumulative total. So a
  // multi-series "area" request renders as plain lines instead -- the form
  // choosing-a-form.md actually specifies for that job.
  const useArea = type === "area" && series.length === 1;
  const Chart = useArea ? AreaChart : LineChart;
  // SVG gradient ids are global to the document -- two area charts on the
  // same page (e.g. two chat turns) would otherwise collide on "lh-area-0".
  const gradientPrefix = useId().replace(/:/g, "");

  return (
    <ResponsiveContainer width="100%" height={320}>
      <Chart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        {useArea && (
          <defs>
            {series.map((key, i) => (
              <linearGradient key={key} id={`${gradientPrefix}-area-${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colorForIndex(i)} stopOpacity={0.22} />
                <stop offset="100%" stopColor={colorForIndex(i)} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
        )}
        <CartesianGrid vertical={false} stroke="var(--gridline)" strokeWidth={1} />
        <XAxis
          dataKey="x"
          tickFormatter={formatDateLabel}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
          minTickGap={32}
        />
        <YAxis
          tickFormatter={(v) => formatCompact(v, unit)}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={64}
        />
        <Tooltip
          content={<ChartTooltip unit={unit} seriesOrder={series} />}
          cursor={{ stroke: "var(--baseline)", strokeWidth: 1 }}
        />
        {series.map((key, i) => {
          if (hiddenSeries?.has(key)) return null;
          const dimmed = hoveredSeries && hoveredSeries !== key;
          const opacity = dimmed ? 0.25 : 1;
          return useArea ? (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colorForIndex(i)}
              strokeWidth={2}
              strokeOpacity={opacity}
              fill={`url(#${gradientPrefix}-area-${i})`}
              fillOpacity={dimmed ? 0.3 : 1}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface-1)" }}
              animationDuration={500}
              animationEasing="ease-out"
              style={{ transition: "opacity 0.2s ease" }}
            />
          ) : (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colorForIndex(i)}
              strokeWidth={2}
              strokeOpacity={opacity}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface-1)" }}
              animationDuration={500}
              animationEasing="ease-out"
              style={{ transition: "opacity 0.2s ease" }}
            />
          );
        })}
      </Chart>
    </ResponsiveContainer>
  );
}
