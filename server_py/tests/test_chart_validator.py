from ..tools.chart_validator import (
    LINE_OVERLAY_SERIES_LIMIT,
    MAX_SERIES,
    SCATTER_POINT_LIMIT,
    STACKED_BAR_BAR_LIMIT,
    TREEMAP_TILE_LIMIT,
    validate_chart,
)


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


def _scatter_chart(**overrides):
    base = {
        "chart_type": "scatter",
        "title": "t",
        "series": ["value"],
        "data": [{"label": "Aave", "x": 1.0, "y": 2.0, "group": "value"}],
    }
    base.update(overrides)
    return base


def test_valid_scatter_with_single_ungrouped_series():
    result = validate_chart(_scatter_chart())
    assert result == {"valid": True, "issues": []}


def test_valid_scatter_with_group_omitted_when_series_has_one_entry():
    result = validate_chart(_scatter_chart(data=[{"label": "Aave", "x": 1.0, "y": 2.0}]))
    assert result["valid"] is True


def test_valid_bubble_chart_with_z_and_multiple_groups():
    result = validate_chart(
        _scatter_chart(
            series=["L1", "L2"],
            data=[
                {"label": "Ethereum", "x": 100, "y": 2.5, "z": 4e11, "group": "L1"},
                {"label": "Arbitrum", "x": 20, "y": -1.2, "z": 3e9, "group": "L2"},
            ],
        )
    )
    assert result["valid"] is True


def test_scatter_point_missing_x_is_invalid():
    result = validate_chart(_scatter_chart(data=[{"label": "Aave", "y": 2.0}]))
    assert result["valid"] is False
    assert any("numeric `x`" in issue for issue in result["issues"])


def test_scatter_point_missing_label_is_invalid():
    result = validate_chart(_scatter_chart(data=[{"x": 1.0, "y": 2.0}]))
    assert result["valid"] is False


def test_scatter_point_group_not_in_series_is_invalid():
    result = validate_chart(_scatter_chart(data=[{"label": "Aave", "x": 1.0, "y": 2.0, "group": "nope"}]))
    assert result["valid"] is False
    assert any("nope" in issue for issue in result["issues"])


def test_scatter_over_point_limit_is_invalid():
    data = [{"label": f"e{i}", "x": i, "y": i, "group": "value"} for i in range(SCATTER_POINT_LIMIT + 1)]
    result = validate_chart(_scatter_chart(data=data))
    assert result["valid"] is False
    assert any(f"{SCATTER_POINT_LIMIT}-point" in issue for issue in result["issues"])


def test_scatter_still_enforces_max_series():
    series = [f"s{i}" for i in range(MAX_SERIES + 1)]
    data = [{"label": "e", "x": 1, "y": 1, "group": series[0]}]
    result = validate_chart(_scatter_chart(series=series, data=data))
    assert result["valid"] is False
    assert any(f"{MAX_SERIES}-series cap" in issue for issue in result["issues"])


def _treemap_chart(**overrides):
    base = {
        "chart_type": "treemap",
        "title": "t",
        "series": ["tvl"],
        "data": [{"x": "Aave", "tvl": 22_010_000_000}, {"x": "Curve", "tvl": 2_330_000_000}],
    }
    base.update(overrides)
    return base


def test_valid_treemap():
    result = validate_chart(_treemap_chart())
    assert result == {"valid": True, "issues": []}


def test_treemap_with_more_than_one_series_is_invalid():
    result = validate_chart(_treemap_chart(series=["tvl", "volume"], data=[{"x": "Aave", "tvl": 1, "volume": 2}]))
    assert result["valid"] is False
    assert any("one metric" in issue for issue in result["issues"])


def test_treemap_over_tile_limit_is_invalid():
    data = [{"x": f"e{i}", "tvl": i} for i in range(TREEMAP_TILE_LIMIT + 1)]
    result = validate_chart(_treemap_chart(data=data))
    assert result["valid"] is False
    assert any(f"{TREEMAP_TILE_LIMIT}-tile" in issue for issue in result["issues"])


def test_treemap_within_tile_limit_is_valid():
    data = [{"x": f"e{i}", "tvl": i} for i in range(TREEMAP_TILE_LIMIT)]
    result = validate_chart(_treemap_chart(data=data))
    assert result["valid"] is True
