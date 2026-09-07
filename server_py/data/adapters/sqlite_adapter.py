"""Default data source: the bundled stub dataset. Direct port of
server/src/data/adapters/sqliteAdapter.js.
"""

import re

from ..db import get_db

# query_engine.py builds SQL with @name placeholders (the shared convention
# across both the sqlite and Snowflake adapters -- see sql_binding.py for
# the Snowflake side's conversion to positional binds). Python's sqlite3
# module wants :name instead of @name for its named-parameter style.
_NAMED_PARAM = re.compile(r"@(\w+)")


def _to_sqlite_named_params(sql: str) -> str:
    return _NAMED_PARAM.sub(r":\1", sql)


class SqliteAdapter:
    dialect = "sqlite"

    def bucket_expr(self, granularity: str) -> str:
        if granularity == "week":
            return "date(date, '-' || ((strftime('%w', date) + 6) % 7) || ' days')"
        if granularity == "month":
            return "strftime('%Y-%m-01', date)"
        return "date"

    def run_query(self, sql: str, params: dict) -> list[dict]:
        rows = get_db().execute(_to_sqlite_named_params(sql), params).fetchall()
        return [dict(row) for row in rows]


sqlite_adapter = SqliteAdapter()
