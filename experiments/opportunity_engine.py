"""Deterministic state-conditioned opportunity evaluation.

The engine is pure: callers provide a frozen one-row-per-date state table and
precommitted specs. It performs no I/O, acquisition, portfolio simulation, or
trade authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping, Sequence

import numpy as np
import pandas as pd

DecisionStatus = Literal["SELECT", "NO-SELECTION", "UNRESOLVED"]


@dataclass(frozen=True)
class OpportunitySpec:
    opportunity_id: str
    features: tuple[str, ...]
    positive_selection: str
    negative_selection: str
    allow_negative_selection: bool = True
    outcome_column: str = "outcome"
    date_column: str = "decision_date"
    current_complete_column: str = "current_complete"
    history_end: str | None = None
    max_analogs: int = 10
    min_separation_months: int = 3
    min_analogs: int = 8
    min_abs_median: float = 0.03
    min_direction_share: float = 0.60
    bootstrap_samples: int = 2_000
    seed: int = 20_260_829

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "OpportunitySpec":
        return cls(
            opportunity_id=str(value["opportunity_id"]),
            features=tuple(str(item) for item in value["features"]),
            positive_selection=str(value["positive_selection"]),
            negative_selection=str(value["negative_selection"]),
            allow_negative_selection=bool(value.get("allow_negative_selection", True)),
            outcome_column=str(value.get("outcome_column", "outcome")),
            date_column=str(value.get("date_column", "decision_date")),
            current_complete_column=str(value.get("current_complete_column", "current_complete")),
            history_end=str(value["history_end"]) if value.get("history_end") else None,
            max_analogs=int(value.get("max_analogs", 10)),
            min_separation_months=int(value.get("min_separation_months", 3)),
            min_analogs=int(value.get("min_analogs", 8)),
            min_abs_median=float(value.get("min_abs_median", 0.03)),
            min_direction_share=float(value.get("min_direction_share", 0.60)),
            bootstrap_samples=int(value.get("bootstrap_samples", 2_000)),
            seed=int(value.get("seed", 20_260_829)),
        )

    def validate(self) -> None:
        if not self.opportunity_id or not self.features:
            raise ValueError("opportunity_id and features are required")
        if self.max_analogs < self.min_analogs or self.min_analogs < 1:
            raise ValueError("max_analogs must be >= min_analogs >= 1")
        if self.min_separation_months < 1 or self.bootstrap_samples < 1:
            raise ValueError("separation and bootstrap samples must be positive")
        if not 0.5 <= self.min_direction_share <= 1.0:
            raise ValueError("min_direction_share must be between 0.5 and 1")
        if self.min_abs_median < 0:
            raise ValueError("min_abs_median must be nonnegative")


@dataclass(frozen=True)
class OpportunityDecision:
    opportunity_id: str
    as_of: str
    status: DecisionStatus
    selection: str | None
    reason: str
    current_vector: dict[str, float | None]
    analogs: tuple[dict[str, Any], ...]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpportunityReport:
    as_of: str
    decisions: tuple[OpportunityDecision, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"as_of": self.as_of, "decisions": [decision.to_dict() for decision in self.decisions]}


def evaluate_opportunities(
    state_table: pd.DataFrame,
    as_of: str | pd.Timestamp,
    specs: Sequence[OpportunitySpec],
) -> OpportunityReport:
    """Evaluate every frozen spec against one canonical state table."""
    timestamp = pd.Timestamp(as_of)
    decisions = tuple(_evaluate_one(state_table, timestamp, spec) for spec in specs)
    return OpportunityReport(as_of=timestamp.date().isoformat(), decisions=decisions)


def _evaluate_one(table: pd.DataFrame, as_of: pd.Timestamp, spec: OpportunitySpec) -> OpportunityDecision:
    spec.validate()
    required = {spec.date_column, spec.outcome_column, spec.current_complete_column, *spec.features}
    missing_columns = sorted(required.difference(table.columns))
    if missing_columns:
        raise ValueError(f"state table missing columns: {missing_columns}")

    states = table.copy()
    states[spec.date_column] = pd.to_datetime(states[spec.date_column], errors="coerce")
    if states[spec.date_column].isna().any():
        raise ValueError("state table contains invalid dates")
    if states[spec.date_column].duplicated().any():
        raise ValueError("state table must contain one row per date")
    states = states.sort_values(spec.date_column).reset_index(drop=True)

    current_rows = states[states[spec.date_column] == as_of]
    if len(current_rows) != 1:
        return _unresolved(spec, as_of, "current_state_missing", {})
    current = current_rows.iloc[0]
    vector = {feature: _optional_float(current[feature]) for feature in spec.features}
    if not bool(current[spec.current_complete_column]):
        return _unresolved(spec, as_of, "current_data_incomplete", vector)
    if any(value is None for value in vector.values()):
        return _unresolved(spec, as_of, "current_feature_missing", vector)

    history = states[states[spec.date_column] < as_of]
    if spec.history_end is not None:
        history = history[history[spec.date_column] <= pd.Timestamp(spec.history_end)]
    history = history.dropna(subset=[*spec.features, spec.outcome_column]).copy()
    if history.empty:
        return _no_selection(spec, as_of, "no_historical_outcomes", vector, (), {"count": 0})

    distance = np.zeros(len(history), dtype=float)
    for feature in spec.features:
        distance += np.square(pd.to_numeric(history[feature], errors="raise").to_numpy(float) - float(vector[feature]))
    history["distance"] = np.sqrt(distance)
    analogs = _select_independent_analogs(history, spec)
    records = tuple(_analog_record(row, spec) for _, row in analogs.iterrows())
    if len(analogs) < spec.min_analogs:
        return _no_selection(
            spec,
            as_of,
            "insufficient_independent_analogs",
            vector,
            records,
            {"count": len(analogs)},
        )

    outcomes = pd.to_numeric(analogs[spec.outcome_column], errors="raise").to_numpy(float)
    mean = float(outcomes.mean())
    median = float(np.median(outcomes))
    positive_share = float((outcomes > 0).mean())
    interval = _bootstrap_mean_interval(outcomes, spec.bootstrap_samples, spec.seed)
    evidence = {
        "count": len(outcomes),
        "mean": mean,
        "median": median,
        "positive_share": positive_share,
        "negative_share": 1.0 - positive_share,
        "bootstrap95": list(interval),
    }

    if (
        median >= spec.min_abs_median
        and positive_share >= spec.min_direction_share
        and interval[0] > 0
    ):
        return OpportunityDecision(
            opportunity_id=spec.opportunity_id,
            as_of=as_of.date().isoformat(),
            status="SELECT",
            selection=spec.positive_selection,
            reason="positive_gate_passed",
            current_vector=vector,
            analogs=records,
            evidence=evidence,
        )
    if spec.allow_negative_selection and (
        median <= -spec.min_abs_median
        and (1.0 - positive_share) >= spec.min_direction_share
        and interval[1] < 0
    ):
        return OpportunityDecision(
            opportunity_id=spec.opportunity_id,
            as_of=as_of.date().isoformat(),
            status="SELECT",
            selection=spec.negative_selection,
            reason="negative_gate_passed",
            current_vector=vector,
            analogs=records,
            evidence=evidence,
        )
    return _no_selection(spec, as_of, "statistical_gate_failed", vector, records, evidence)


def _select_independent_analogs(history: pd.DataFrame, spec: OpportunitySpec) -> pd.DataFrame:
    selected: list[pd.Series] = []
    for _, row in history.sort_values(["distance", spec.date_column]).iterrows():
        month = _month_index(pd.Timestamp(row[spec.date_column]))
        if all(abs(month - _month_index(pd.Timestamp(item[spec.date_column]))) >= spec.min_separation_months for item in selected):
            selected.append(row)
        if len(selected) >= spec.max_analogs:
            break
    return pd.DataFrame(selected, columns=history.columns)


def _bootstrap_mean_interval(values: np.ndarray, samples: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    for index in range(samples):
        means[index] = values[rng.integers(0, len(values), len(values))].mean()
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def _analog_record(row: pd.Series, spec: OpportunitySpec) -> dict[str, Any]:
    return {
        "date": pd.Timestamp(row[spec.date_column]).date().isoformat(),
        "distance": float(row["distance"]),
        "outcome": float(row[spec.outcome_column]),
    }


def _month_index(value: pd.Timestamp) -> int:
    return value.year * 12 + value.month


def _optional_float(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)


def _unresolved(
    spec: OpportunitySpec,
    as_of: pd.Timestamp,
    reason: str,
    vector: dict[str, float | None],
) -> OpportunityDecision:
    return OpportunityDecision(spec.opportunity_id, as_of.date().isoformat(), "UNRESOLVED", None, reason, vector, (), {})


def _no_selection(
    spec: OpportunitySpec,
    as_of: pd.Timestamp,
    reason: str,
    vector: dict[str, float | None],
    analogs: tuple[dict[str, Any], ...],
    evidence: dict[str, Any],
) -> OpportunityDecision:
    return OpportunityDecision(spec.opportunity_id, as_of.date().isoformat(), "NO-SELECTION", None, reason, vector, analogs, evidence)
