import pytest

pd = pytest.importorskip("pandas")

from experiments.context_features import analyst_eps_revision, holm_adjust


def test_analyst_revision_uses_latest_per_org_at_each_cutoff():
    rows = pd.DataFrame(
        [
            {"quarter": "2026Q4", "org_name": org, "report_date": "20260101", "create_time": "2026-01-01", "eps": 1.0}
            for org in ("A", "B", "C")
        ]
        + [
            {"quarter": "2026Q4", "org_name": org, "report_date": "20260125", "create_time": "2026-01-25", "eps": 1.2}
            for org in ("A", "B", "C")
        ]
    )
    result = analyst_eps_revision(rows, pd.Timestamp("2026-02-01"))
    assert result["quarter"] == "2026Q4"
    assert result["current_count"] == result["prior_count"] == 3
    assert result["revision"] == pytest.approx(0.2)


def test_analyst_revision_requires_three_orgs_at_both_cutoffs():
    rows = pd.DataFrame(
        [
            {"quarter": "2026Q4", "org_name": "A", "report_date": "20260125", "create_time": "2026-01-25", "eps": 1.2},
            {"quarter": "2026Q4", "org_name": "B", "report_date": "20260125", "create_time": "2026-01-25", "eps": 1.3},
            {"quarter": "2026Q4", "org_name": "C", "report_date": "20260125", "create_time": "2026-01-25", "eps": 1.4},
        ]
    )
    assert pd.isna(analyst_eps_revision(rows, pd.Timestamp("2026-02-01"))["revision"])


def test_holm_adjustment_is_monotone_in_sorted_p_values():
    assert holm_adjust({"a": 0.01, "b": 0.02, "c": 0.04}) == {
        "a": pytest.approx(0.03),
        "b": pytest.approx(0.04),
        "c": pytest.approx(0.04),
    }
