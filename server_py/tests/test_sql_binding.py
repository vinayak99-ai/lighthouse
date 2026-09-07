import pytest

from ..data.sql_binding import to_pyformat


def test_converts_named_placeholders_to_pyformat():
    sql = "SELECT * FROM t WHERE a = @foo AND b = @bar"
    result = to_pyformat(sql, {"foo": 1, "bar": 2})
    assert result == "SELECT * FROM t WHERE a = %(foo)s AND b = %(bar)s"


def test_repeated_placeholder_converts_every_occurrence():
    sql = "SELECT @x, @x"
    result = to_pyformat(sql, {"x": 1})
    assert result == "SELECT %(x)s, %(x)s"


def test_missing_bind_param_raises_key_error():
    with pytest.raises(KeyError):
        to_pyformat("SELECT @missing", {})
