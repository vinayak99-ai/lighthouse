"""Direct port of server/src/data/adapters/snowflakeAdapter.js -- keeps the
same three-layer safety story: a session-level STATEMENT_TIMEOUT_IN_SECONDS
(Snowflake's own server-side abort -- the real guarantee, holds even if
this process crashes), an app-level timeout + explicit SYSTEM$CANCEL_QUERY
backstop for the case that somehow doesn't fire (a stuck session, a
network partition), and a connect-timeout short enough that an
unreachable account fails a chat request in seconds, not the driver's own
much longer default retry.

The actual write-safety boundary is still the Snowflake role this app
connects as (a dedicated, read-only role with SELECT-only grants -- see
server/src/data/snowflakeSetup.sql, reused unchanged for this backend);
assert_select_only() below is defense-in-depth, not the guarantee.

snowflake-connector-python's Cursor.execute() blocks synchronously for the
whole query, so unlike this app's other adapters (call it, get rows back),
enforcing an app-level timeout here needs execute_async() + polling +
SYSTEM$CANCEL_QUERY rather than a simple wall-clock wrapper.

snowflake-connector-python is imported lazily (inside _connect()) so
nothing about running on the default SQLite stub data requires it to be
installed.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable

from ..sql_binding import to_pyformat

# Snowflake's own hard stop -- the warehouse itself aborts a query past
# this, independent of anything in this process.
STATEMENT_TIMEOUT_SECONDS = int(os.environ.get("SNOWFLAKE_STATEMENT_TIMEOUT_SECONDS", "60"))
# A few seconds of slack past Snowflake's own timeout, so in the normal
# case Snowflake's server-side abort fires first and this is just a
# backstop for the case it somehow doesn't.
APP_LEVEL_TIMEOUT_SECONDS = STATEMENT_TIMEOUT_SECONDS + 5
# How long to wait for the connection itself to be established. The
# driver's own default retry policy is much longer, which would otherwise
# leave a chat request hanging well past the query-level timeout ever
# getting a chance to run.
CONNECT_TIMEOUT_SECONDS = int(os.environ.get("SNOWFLAKE_CONNECT_TIMEOUT_SECONDS", "20"))
POLL_INTERVAL_SECONDS = 0.25

_WRITE_OR_DDL_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|COPY\s+INTO|CALL|EXECUTE\s+IMMEDIATE)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(Exception):
    pass


def assert_select_only(sql: str) -> None:
    """Defense-in-depth, not the real guarantee -- see module docstring."""
    statement = re.sub(r";+\s*$", "", sql.strip())
    if ";" in statement:
        raise UnsafeQueryError("Refusing to run multiple SQL statements in one call.")
    if not re.match(r"^(WITH|SELECT)\b", statement, re.IGNORECASE):
        raise UnsafeQueryError("Refusing to run a statement that isn't a SELECT (or a WITH...SELECT).")
    if _WRITE_OR_DDL_KEYWORDS.search(statement):
        raise UnsafeQueryError("Refusing to run a statement containing a write/DDL keyword.")


def _connect() -> Any:
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
        login_timeout=CONNECT_TIMEOUT_SECONDS,
        network_timeout=CONNECT_TIMEOUT_SECONDS,
    )
    # Session-level enforcement of the statement cap -- applies to every
    # query this connection runs from here on, not just the next one.
    conn.cursor().execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {STATEMENT_TIMEOUT_SECONDS}")
    return conn


_connection: Any = None


def get_connection(connect_fn: Callable[[], Any] = _connect) -> Any:
    """`connect_fn` is injectable so tests can exercise the cache/retry
    behavior without a real snowflake-connector-python connection. A
    failed connect_fn() call leaves the module-level cache untouched
    (still None), so the next call gets a fresh attempt instead of a
    transient network issue poisoning every query for the process's life."""
    global _connection
    if _connection is None:
        _connection = connect_fn()
    return _connection


def reset_connection_cache() -> None:
    """Exposed for tests."""
    global _connection
    _connection = None


def execute_with_timeout(connection: Any, sql: str, params: dict, timeout_seconds: float = APP_LEVEL_TIMEOUT_SECONDS) -> list[dict]:
    """`timeout_seconds` is a parameter (not read from the module constant
    directly) so tests can exercise the cancel-on-timeout path in a
    fraction of a second instead of waiting out a real 60+ second
    production timeout."""
    cursor = connection.cursor()
    cursor.execute_async(sql, params)
    query_id = cursor.sfqid
    deadline = time.monotonic() + timeout_seconds

    while connection.is_still_running(connection.get_query_status(query_id)):
        if time.monotonic() >= deadline:
            try:
                connection.cursor().execute(f"SELECT SYSTEM$CANCEL_QUERY('{query_id}')")
            except Exception:
                pass  # best-effort: stop it burning warehouse credits after we've given up
            raise TimeoutError(f"Query exceeded the {timeout_seconds}s application-level timeout and was cancelled.")
        time.sleep(POLL_INTERVAL_SECONDS)

    cursor.get_results_from_sfqid(query_id)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class SnowflakeAdapter:
    dialect = "snowflake"

    def bucket_expr(self, granularity: str) -> str:
        if granularity == "week":
            return "DATE_TRUNC('WEEK', date)"
        if granularity == "month":
            return "DATE_TRUNC('MONTH', date)"
        return "date"

    def run_query(self, sql_with_named_params: str, params: dict) -> list[dict]:
        assert_select_only(sql_with_named_params)
        sql = to_pyformat(sql_with_named_params, params)
        connection = get_connection()
        return execute_with_timeout(connection, sql, params)


snowflake_adapter = SnowflakeAdapter()
