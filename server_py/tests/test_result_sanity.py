import pytest

from ..data.result_sanity import (
    NULL_RATIO_WARNING_THRESHOLD,
    ROW_COUNT_LIMIT,
    STALENESS_WARNING_DAYS,
    check_result_sanity,
)


def test_healthy_result_has_no_warning():
    rows = [{"bucket": "2026-08-20", "value": 1.0}, {"bucket": "2026-08-21", "value": 2.0}]
    assert check_result_sanity(rows, end_date="2026-08-22") is None


def test_empty_result_has_no_warning():
    """Empty results are chart_validator.py's problem ('data is empty'),
    not this check's -- an empty result isn't a data-quality issue."""
    assert check_result_sanity([], end_date="2026-08-22") is None


def test_row_count_over_limit_raises_value_error():
    rows = [{"bucket": "2026-01-01", "value": 1.0}] * (ROW_COUNT_LIMIT + 1)
    with pytest.raises(ValueError, match=f"{ROW_COUNT_LIMIT}-row"):
        check_result_sanity(rows, end_date="2026-08-22")


def test_row_count_at_limit_does_not_raise():
    rows = [{"bucket": "2026-01-01", "value": 1.0}] * ROW_COUNT_LIMIT
    check_result_sanity(rows, end_date="2026-08-22")  # should not raise


def test_null_heavy_result_warns():
    rows = [{"bucket": f"2026-01-{i:02d}", "value": None if i <= 4 else 1.0} for i in range(1, 11)]
    assert (sum(1 for r in rows if r["value"] is None) / len(rows)) >= NULL_RATIO_WARNING_THRESHOLD
    warning = check_result_sanity(rows, end_date="2026-08-22")
    assert warning is not None
    assert "no value" in warning


def test_low_null_ratio_does_not_warn():
    rows = [{"bucket": f"2026-08-{i:02d}", "value": None if i == 13 else 1.0} for i in range(13, 23)]
    assert check_result_sanity(rows, end_date="2026-08-22") is None


def test_stale_result_warns():
    rows = [{"bucket": "2026-08-01", "value": 1.0}]
    warning = check_result_sanity(rows, end_date="2026-08-22")  # 21 days stale
    assert warning is not None
    assert "days before the requested end date" in warning


def test_result_within_staleness_window_does_not_warn():
    rows = [{"bucket": "2026-08-18", "value": 1.0}]  # 4 days before end_date
    assert STALENESS_WARNING_DAYS > 4
    assert check_result_sanity(rows, end_date="2026-08-22") is None


def test_no_end_date_skips_staleness_check():
    rows = [{"bucket": "2020-01-01", "value": 1.0}]
    assert check_result_sanity(rows, end_date=None) is None


def test_both_null_heavy_and_stale_combines_warnings():
    rows = [{"bucket": "2026-08-01", "value": None} for _ in range(10)]
    warning = check_result_sanity(rows, end_date="2026-08-22")
    assert "no value" in warning
    assert "days before the requested end date" in warning
