"""Picks the active data-source adapter. Same pattern as chat/orchestrator.py's
LLM provider picker, one level down the stack. Direct port of
server/src/data/dataSource.js.

Snowflake's adapter (and its snowflake-connector-python dependency) is only
imported lazily, on demand -- so nothing about running on the default
SQLite stub data requires that package to even be installed.
"""

import os


def get_data_source():
    forced = (os.environ.get("LIGHTHOUSE_DATA_SOURCE") or "").lower()
    if forced == "snowflake":
        from .adapters.snowflake_adapter import snowflake_adapter

        return snowflake_adapter
    if forced == "sqlite":
        from .adapters.sqlite_adapter import sqlite_adapter

        return sqlite_adapter

    if os.environ.get("SNOWFLAKE_ACCOUNT"):
        from .adapters.snowflake_adapter import snowflake_adapter

        return snowflake_adapter

    from .adapters.sqlite_adapter import sqlite_adapter

    return sqlite_adapter
