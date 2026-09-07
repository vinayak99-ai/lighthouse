from ..tools.chart_validator import LINE_OVERLAY_SERIES_LIMIT, MAX_SERIES, STACKED_BAR_BAR_LIMIT, validate_chart


def _chart(**overrides):
    base = {
        "chart_type": "line",
        "title": "t",
        "series": ["A"],
        "data": [{"x": "1", "A": 1}],
    }
    base.update(overrides)
    return base


def test_no_chart_object():
    result = validate_chart(None)
    assert result["valid"] is False
    assert "no chart object" in result["issues"][0]


def test_empty_series_is_invalid():
    result = validate_chart(_chart(series=[]))
    assert result["valid"] is False
    assert any("series" in issue for issue in result["issues"])


def test_empty_data_is_invalid():
    result = validate_chart(_chart(data=[]))
    assert result["valid"] is False
    assert any("data" in issue for issue in result["issues"])


def test_valid_single_series_line_chart():
    result = validate_chart(_chart())
    assert result == {"valid": True, "issues": []}


def test_too_many_series_is_invalid():
    series = [f"s{i}" for i in range(MAX_SERIES + 1)]
    data = [{"x": "1", **{s: 1 for s in series}}]
    result = validate_chart(_chart(series=series, data=data))
    assert result["valid"] is False
    assert any(f"{MAX_SERIES}-series cap" in issue for issue in result["issues"])


def test_area_chart_with_multiple_series_is_invalid():
    result = validate_chart(_chart(chart_type="area", series=["A", "B"], data=[{"x": "1", "A": 1, "B": 2}]))
    assert result["valid"] is False
    assert any("area" in issue for issue in result["issues"])


def test_area_chart_with_single_series_is_valid():
    result = validate_chart(_chart(chart_type="area"))
    assert result["valid"] is True


def test_stacked_bar_over_limit_is_invalid():
    data = [{"x": str(i), "A": i} for i in range(STACKED_BAR_BAR_LIMIT + 1)]
    result = validate_chart(_chart(chart_type="stacked_bar", data=data))
    assert result["valid"] is False
    assert any("barcode" in issue for issue in result["issues"])


def test_line_chart_over_overlay_limit_is_invalid():
    series = [f"s{i}" for i in range(LINE_OVERLAY_SERIES_LIMIT + 1)]
    data = [{"x": "1", **{s: 1 for s in series}}]
    result = validate_chart(_chart(chart_type="line", series=series, data=data))
    assert result["valid"] is False
    assert any("small_multiples" in issue for issue in result["issues"])


def test_series_with_no_data_is_invalid():
    result = validate_chart(_chart(series=["A", "B"], data=[{"x": "1", "A": 1}]))
    assert result["valid"] is False
    assert any("B" in issue for issue in result["issues"])
