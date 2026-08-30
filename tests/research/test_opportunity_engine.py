from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from experiments.opportunity_engine import OpportunitySpec, evaluate_opportunities
from experiments.run_opportunity_shadow import run


def _spec(**changes) -> OpportunitySpec:
    values = {
        "opportunity_id": "test",
        "features": ("f1", "f2"),
        "positive_selection": "LEFT",
        "negative_selection": "RIGHT",
        "max_analogs": 10,
        "min_analogs": 8,
        "min_separation_months": 3,
        "bootstrap_samples": 200,
        "seed": 7,
    }
    values.update(changes)
    return OpportunitySpec(**values)


def _states(outcomes, *, current_complete=True, future_outcome=None) -> pd.DataFrame:
    dates = pd.date_range("2020-01-31", periods=len(outcomes), freq="3ME")
    rows = [
        {"decision_date": date, "f1": index / 100, "f2": -index / 200, "outcome": outcome, "current_complete": True}
        for index, (date, outcome) in enumerate(zip(dates, outcomes, strict=True))
    ]
    rows.append({"decision_date": "2026-08-27", "f1": 0.0, "f2": 0.0, "outcome": None, "current_complete": current_complete})
    if future_outcome is not None:
        rows.append({"decision_date": "2026-09-30", "f1": 0.0, "f2": 0.0, "outcome": future_outcome, "current_complete": True})
    return pd.DataFrame(rows)


def test_selects_positive_and_is_deterministic() -> None:
    states = _states([0.04, 0.05, 0.06, 0.07, 0.08, 0.04, 0.05, 0.06, 0.07, 0.08])
    first = evaluate_opportunities(states, "2026-08-27", [_spec()]).decisions[0]
    second = evaluate_opportunities(states, "2026-08-27", [_spec()]).decisions[0]
    assert first == second
    assert first.status == "SELECT"
    assert first.selection == "LEFT"
    assert first.evidence["bootstrap95"][0] > 0


def test_selects_negative() -> None:
    states = _states([-0.04, -0.05, -0.06, -0.07, -0.08, -0.04, -0.05, -0.06, -0.07, -0.08])
    decision = evaluate_opportunities(states, "2026-08-27", [_spec()]).decisions[0]
    assert decision.status == "SELECT"
    assert decision.selection == "RIGHT"
    assert decision.evidence["bootstrap95"][1] < 0


def test_one_sided_spec_does_not_select_negative() -> None:
    states = _states([-0.05] * 10)
    decision = evaluate_opportunities(states, "2026-08-27", [_spec(allow_negative_selection=False)]).decisions[0]
    assert decision.status == "NO-SELECTION"
    assert decision.selection is None


def test_incomplete_current_state_is_unresolved() -> None:
    decision = evaluate_opportunities(_states([0.05] * 10, current_complete=False), "2026-08-27", [_spec()]).decisions[0]
    assert decision.status == "UNRESOLVED"
    assert decision.reason == "current_data_incomplete"


def test_future_rows_and_post_cutoff_history_are_ignored() -> None:
    states = _states([0.05] * 10, future_outcome=-10)
    extra = pd.DataFrame([
        {"decision_date": "2026-01-31", "f1": 0.0, "f2": 0.0, "outcome": -10.0, "current_complete": True}
    ])
    states = pd.concat([states, extra], ignore_index=True)
    decision = evaluate_opportunities(states, "2026-08-27", [_spec(history_end="2025-12-31")]).decisions[0]
    assert decision.status == "SELECT"
    assert all(analog["date"] <= "2025-12-31" for analog in decision.analogs)


def test_monthly_candidates_are_separated() -> None:
    rows = [
        {"decision_date": date, "f1": index / 1000, "f2": 0.0, "outcome": 0.05, "current_complete": True}
        for index, date in enumerate(pd.date_range("2020-01-31", periods=30, freq="ME"))
    ]
    rows.append({"decision_date": "2026-08-27", "f1": 0.0, "f2": 0.0, "outcome": None, "current_complete": True})
    decision = evaluate_opportunities(pd.DataFrame(rows), "2026-08-27", [_spec()]).decisions[0]
    months = [pd.Period(item["date"], freq="M").ordinal for item in decision.analogs]
    assert len(months) == 10
    assert all(abs(left - right) >= 3 for index, left in enumerate(months) for right in months[index + 1 :])


def test_duplicate_dates_fail_closed() -> None:
    states = _states([0.05] * 10)
    states = pd.concat([states, states.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one row per date"):
        evaluate_opportunities(states, "2026-08-27", [_spec()])


def _write_catalog(tmp_path: Path, source: Path, *, kind="relative_industry_v1") -> Path:
    catalog = {
        "version": 1,
        "as_of": "2026-08-27",
        "capital": 0,
        "trade_authorized": False,
        "opportunities": [
            {
                "opportunity_id": "relative",
                "kind": kind,
                "source": str(source),
                "left": "LEFT",
                "right": "RIGHT",
                "features": ["f1"],
                "source_outcome_column": "future63",
                "history_end": "2025-12-31",
                "positive_selection": "LEFT",
                "negative_selection": "RIGHT",
                "max_analogs": 8,
                "min_analogs": 8,
                "min_separation_months": 3,
                "min_abs_median": 0.03,
                "min_direction_share": 0.60,
                "bootstrap_samples": 100,
                "seed": 7,
                "coverage_rules": [{"column": "coverage", "minimum": 0.9}],
            }
        ],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    return path


def _write_relative_source(tmp_path: Path) -> Path:
    rows = []
    for index, date in enumerate(pd.date_range("2020-01-31", periods=8, freq="3ME")):
        rows.extend([
            {"decision_date": date, "industry": "LEFT", "f1": index / 100, "future63": 0.08, "coverage": 1.0},
            {"decision_date": date, "industry": "RIGHT", "f1": 0.0, "future63": 0.0, "coverage": 1.0},
        ])
    rows.extend([
        {"decision_date": "2026-08-27", "industry": "LEFT", "f1": 0.0, "future63": None, "coverage": 1.0},
        {"decision_date": "2026-08-27", "industry": "RIGHT", "f1": 0.0, "future63": None, "coverage": 1.0},
    ])
    path = tmp_path / "states.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_runner_ledger_is_idempotent(tmp_path: Path) -> None:
    source = _write_relative_source(tmp_path)
    catalog = _write_catalog(tmp_path, source)
    report = tmp_path / "report.json"
    ledger = tmp_path / "ledger.csv"
    first = run(str(catalog), str(report), str(ledger))
    second = run(str(catalog), str(report), str(ledger))
    assert first == second
    assert first["decisions"][0]["status"] == "SELECT"
    assert len(pd.read_csv(ledger)) == 1


def test_monthly_signal_adapter(tmp_path: Path) -> None:
    rows = [
        {"decision_date": date, "f1": index / 100, "outcome": 0.05, "current_complete": True}
        for index, date in enumerate(pd.date_range("2020-01-31", periods=8, freq="3ME"))
    ]
    rows.append({"decision_date": "2026-08-26", "f1": 0.0, "outcome": None, "current_complete": True})
    source = tmp_path / "monthly.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    catalog = {
        "version": 1,
        "as_of": "2026-08-27",
        "capital": 0,
        "trade_authorized": False,
        "opportunities": [{
            "opportunity_id": "monthly",
            "kind": "monthly_signal_state_v1",
            "source": str(source),
            "as_of": "2026-08-26",
            "features": ["f1"],
            "positive_selection": "ENABLE",
            "negative_selection": "DISABLE",
            "allow_negative_selection": False,
            "history_end": "2025-12-31",
            "max_analogs": 8,
            "min_analogs": 8,
            "min_separation_months": 3,
            "bootstrap_samples": 100,
            "seed": 7,
        }],
    }
    catalog_path = tmp_path / "monthly-catalog.json"
    catalog_path.write_text(json.dumps(catalog))
    payload = run(str(catalog_path), str(tmp_path / "report.json"), str(tmp_path / "ledger.csv"))
    assert payload["decisions"][0]["as_of"] == "2026-08-26"
    assert payload["decisions"][0]["selection"] == "ENABLE"


def test_runner_rejects_unknown_kind(tmp_path: Path) -> None:
    source = _write_relative_source(tmp_path)
    catalog = _write_catalog(tmp_path, source, kind="future_magic")
    with pytest.raises(ValueError, match="unsupported opportunity kind"):
        run(str(catalog), str(tmp_path / "report.json"), str(tmp_path / "ledger.csv"))
