"""Direct port of server/src/tools/queryEngine.js. Builds and runs a
parameterized, read-only SQL query grouping a value column over time,
optionally split by an entity dimension. This is the "backend builds the
query" layer: the model supplies structured, typed arguments -- never raw
SQL -- and this function is the only thing that touches the DB, via
whichever data source is active (SQLite stub data, or a real Snowflake
warehouse -- see data/data_source.py).
"""

from ..data.data_source import get_data_source
from ..data.result_sanity import check_result_sanity


class ToolInputError(Exception):
    pass


def bucket_expr(granularity: str) -> str:
    """Delegates to whichever data source is active -- the exact date-
    bucketing expression is dialect-specific (SQLite vs Snowflake date
    functions differ)."""
    return get_data_source().bucket_expr(granularity)


def _assert_known_values(values, allowed, label):
    if not values:
        return
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ToolInputError(f"Unknown {label}: {', '.join(bad)}. Valid values: {', '.join(allowed)}")


def run_grouped_time_series(
    *,
    table: str,
    entity_col: str,
    entity_allowed: list[str],
    entities: list[str] | None = None,
    extra_filters: list[dict] | None = None,  # [{"col", "allowed", "values"}]
    value_col: str,
    aggregate: str = "SUM",
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "day",
    group_by_entity: bool = True,
) -> dict:
    extra_filters = extra_filters or []
    _assert_known_values(entities, entity_allowed, entity_col)
    for f in extra_filters:
        _assert_known_values(f.get("values"), f["allowed"], f["col"])

    where = []
    params: dict = {}
    if start_date:
        where.append("date >= @startDate")
        params["startDate"] = start_date
    if end_date:
        where.append("date <= @endDate")
        params["endDate"] = end_date
    if entities:
        placeholders = ", ".join(f"@entity{i}" for i in range(len(entities)))
        for i, v in enumerate(entities):
            params[f"entity{i}"] = v
        where.append(f"{entity_col} IN ({placeholders})")
    for fi, f in enumerate(extra_filters):
        values = f.get("values")
        if values:
            placeholders = ", ".join(f"@filter{fi}_{i}" for i in range(len(values)))
            for i, v in enumerate(values):
                params[f"filter{fi}_{i}"] = v
            where.append(f"{f['col']} IN ({placeholders})")

    data_source = get_data_source()
    bucket = data_source.bucket_expr(granularity)
    group_by = "bucket, entity" if group_by_entity else "bucket"

    # Two-stage aggregation. A table can carry a dimension the caller didn't
    # ask to split by (e.g. stablecoin_supply has both issuer and chain) --
    # rows sharing the same (date, entity) are components of one total and
    # must always be SUMmed first (a stablecoin's total supply is the sum of
    # its per-chain supplies, not their average). Only *then*, across the
    # distinct dates inside one time bucket, does the SUM-vs-AVG choice for
    # stock vs. flow metrics apply -- summing a stock like TVL across a week
    # of days would inflate it; averaging a flow like volume would deflate it.
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    entity_select = f"{entity_col} AS entity," if group_by_entity else ""
    entity_group = f", {entity_col}" if group_by_entity else ""
    bucket_entity_select = "entity," if group_by_entity else ""
    order_entity = ", entity ASC" if group_by_entity else ""

    sql = f"""
        WITH daily AS (
          SELECT date, {entity_select} SUM({value_col}) AS value
          FROM {table}
          {where_clause}
          GROUP BY date{entity_group}
        )
        SELECT {bucket} AS bucket, {bucket_entity_select} {aggregate}(value) AS value
        FROM daily
        GROUP BY {group_by}
        ORDER BY bucket ASC{order_entity}
    """

    rows = data_source.run_query(sql, params)

    # The choke point every data tool's rows pass through regardless of
    # which adapter served them -- see data/result_sanity.py for why a
    # runaway row count fails loud (ToolInputError) while null-heavy or
    # stale data only annotates the result with a warning instead of
    # blocking it.
    try:
        warning = check_result_sanity(rows, value_col="value", end_date=end_date)
    except ValueError as err:
        raise ToolInputError(str(err)) from err

    return {"sql": sql.strip(), "rows": rows, "warning": warning}


def pivot_by_entity(rows: list[dict], fallback_series_name: str | None = None) -> dict:
    """Reshapes grouped rows [{bucket, entity, value}] into chart-ready wide
    rows: [{x: bucket, <entity>: value, ...}], plus the ordered series list."""
    by_bucket: dict[str, dict] = {}
    series_set: list[str] = []
    for row in rows:
        key = row.get("entity") or fallback_series_name or "value"
        if key not in series_set:
            series_set.append(key)
        bucket = row["bucket"]
        if bucket not in by_bucket:
            by_bucket[bucket] = {"x": bucket}
        by_bucket[bucket][key] = row["value"]
    return {"data": list(by_bucket.values()), "series": series_set}
