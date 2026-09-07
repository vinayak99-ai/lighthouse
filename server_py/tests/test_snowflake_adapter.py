import pytest

from ..data.adapters.snowflake_adapter import (
    UnsafeQueryError,
    assert_select_only,
    execute_with_timeout,
    get_connection,
    reset_connection_cache,
)


def test_assert_select_only_allows_select_and_with():
    assert_select_only("SELECT 1")
    assert_select_only("WITH x AS (SELECT 1) SELECT * FROM x")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE foo",
        "SELECT 1; DROP TABLE foo",
        "INSERT INTO foo VALUES (1)",
        "UPDATE foo SET a = 1",
        "CALL some_procedure()",
    ],
)
def test_assert_select_only_blocks_unsafe_statements(sql):
    with pytest.raises(UnsafeQueryError):
        assert_select_only(sql)


class _FakeCursor:
    def __init__(self, sfqid, description, rows):
        self.sfqid = sfqid
        self.description = description
        self._rows = rows
        self.executed = []

    def execute_async(self, sql, params):
        self.executed.append(("async", sql, params))

    def execute(self, sql):
        self.executed.append(("sync", sql))

    def get_results_from_sfqid(self, sfqid):
        pass

    def fetchall(self):
        return self._rows


class _FakeConnectionDone:
    def __init__(self):
        self._cursor = _FakeCursor("q1", [("bucket",), ("value",)], [("2026-08-01", 100.0)])

    def cursor(self):
        return self._cursor

    def get_query_status(self, query_id):
        return "SUCCESS"

    def is_still_running(self, status):
        return False


class _FakeConnectionNeverDone:
    def cursor(self):
        return _FakeCursor("q2", [], [])

    def get_query_status(self, query_id):
        return "RUNNING"

    def is_still_running(self, status):
        return True


def test_execute_with_timeout_returns_rows_on_success():
    rows = execute_with_timeout(_FakeConnectionDone(), "SELECT bucket, value FROM x", {})
    assert rows == [{"bucket": "2026-08-01", "value": 100.0}]


def test_execute_with_timeout_cancels_and_raises_on_timeout():
    with pytest.raises(TimeoutError):
        execute_with_timeout(_FakeConnectionNeverDone(), "SELECT 1", {}, timeout_seconds=0.2)


def test_get_connection_does_not_cache_a_failed_attempt():
    reset_connection_cache()
    attempts = {"n": 0}

    def flaky_connect():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("network blip")
        return "real-connection"

    with pytest.raises(RuntimeError):
        get_connection(flaky_connect)

    assert get_connection(flaky_connect) == "real-connection"
    assert attempts["n"] == 2
    reset_connection_cache()


def test_get_connection_caches_across_calls():
    reset_connection_cache()
    calls = {"n": 0}

    def connect_fn():
        calls["n"] += 1
        return "connection"

    get_connection(connect_fn)
    get_connection(connect_fn)
    assert calls["n"] == 1
    reset_connection_cache()
