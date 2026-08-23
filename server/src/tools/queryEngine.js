import { getDb } from "../data/db.js";

// Turns a granularity into the SQL expression used to bucket `date`.
// week buckets to the Monday that starts the week; month buckets to the 1st.
export function bucketExpr(granularity) {
  if (granularity === "week") return "date(date, '-' || ((strftime('%w', date) + 6) % 7) || ' days')";
  if (granularity === "month") return "strftime('%Y-%m-01', date)";
  return "date";
}

export class ToolInputError extends Error {}

function assertKnownValues(values, allowed, label) {
  if (!values || values.length === 0) return;
  const bad = values.filter((v) => !allowed.includes(v));
  if (bad.length > 0) {
    throw new ToolInputError(`Unknown ${label}: ${bad.join(", ")}. Valid values: ${allowed.join(", ")}`);
  }
}

/**
 * Builds and runs a parameterized, read-only SQL query grouping a value column
 * over time, optionally split by an entity dimension. This is the "backend
 * builds the query" layer: the model supplies structured, typed arguments —
 * never raw SQL — and this function is the only thing that touches the DB.
 */
export function runGroupedTimeSeries({
  table,
  entityCol,
  entityAllowed,
  entities,
  extraFilters = [], // [{col, allowed, values}]
  valueCol,
  aggregate = "SUM",
  startDate,
  endDate,
  granularity = "day",
  groupByEntity = true,
}) {
  assertKnownValues(entities, entityAllowed, entityCol);
  for (const f of extraFilters) assertKnownValues(f.values, f.allowed, f.col);

  const where = [];
  const params = {};
  if (startDate) {
    where.push("date >= @startDate");
    params.startDate = startDate;
  }
  if (endDate) {
    where.push("date <= @endDate");
    params.endDate = endDate;
  }
  if (entities && entities.length > 0) {
    const placeholders = entities.map((_, i) => `@entity${i}`).join(", ");
    entities.forEach((v, i) => (params[`entity${i}`] = v));
    where.push(`${entityCol} IN (${placeholders})`);
  }
  extraFilters.forEach((f, fi) => {
    if (f.values && f.values.length > 0) {
      const placeholders = f.values.map((_, i) => `@filter${fi}_${i}`).join(", ");
      f.values.forEach((v, i) => (params[`filter${fi}_${i}`] = v));
      where.push(`${f.col} IN (${placeholders})`);
    }
  });

  const bucket = bucketExpr(granularity);
  const selectEntity = groupByEntity ? `${entityCol} AS entity,` : "";
  const groupBy = groupByEntity ? `bucket, ${entityCol}` : "bucket";

  const sql = `
    SELECT ${bucket} AS bucket, ${selectEntity} ${aggregate}(${valueCol}) AS value
    FROM ${table}
    ${where.length ? "WHERE " + where.join(" AND ") : ""}
    GROUP BY ${groupBy}
    ORDER BY bucket ASC${groupByEntity ? `, ${entityCol} ASC` : ""}
  `;

  const rows = getDb().prepare(sql).all(params);
  return { sql: sql.trim(), rows };
}

/** Reshapes grouped rows [{bucket, entity, value}] into chart-ready wide rows:
 * [{ x: bucket, [entity]: value, ... }], plus the ordered list of series keys.
 */
export function pivotByEntity(rows, { fallbackSeriesName } = {}) {
  const byBucket = new Map();
  const seriesSet = [];
  for (const row of rows) {
    const key = row.entity ?? fallbackSeriesName ?? "value";
    if (!seriesSet.includes(key)) seriesSet.push(key);
    if (!byBucket.has(row.bucket)) byBucket.set(row.bucket, { x: row.bucket });
    byBucket.get(row.bucket)[key] = row.value;
  }
  return { data: Array.from(byBucket.values()), series: seriesSet };
}
