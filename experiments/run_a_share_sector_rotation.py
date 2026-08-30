"""Research-only weekly cross-industry rotation backtest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb


BENCHMARK_CODE = "801003.SI"
EXCLUDED_L1_CODES = {"801230.SI"}
HEALTHCARE_CODE = "801150.SI"
WARMUP_WEEKS = 55


@dataclass(frozen=True, slots=True)
class WeeklyBar:
    week_end: date
    close: float
    amount: float


@dataclass(frozen=True, slots=True)
class IndustryFeature:
    code: str
    name: str
    leading_score: int
    confirmation_score: int
    excess_4w: float
    excess_13w: float
    breadth_13w: float
    breadth_acceleration: float
    breadth_coverage: float
    relative_strength_turn: bool
    volatility_compression: bool
    turnover_expansion: bool
    subindustry_diffusion: float
    leading_conditions: tuple[bool, bool, bool, bool, bool]
    confirmation_conditions: tuple[bool, bool, bool]


@dataclass(frozen=True, slots=True)
class RunResult:
    name: str
    dates: tuple[date, ...]
    returns: tuple[float, ...]
    turnovers: tuple[float, ...]
    invested: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class DetectionResult:
    event_kind: str
    lead_window_weeks: int
    signal: str
    threshold: int
    event_count: int
    signal_count: int
    recall: float | None
    precision: float | None
    false_alarms_per_year: float
    median_lead_weeks: float | None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_taxonomy(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    rows = connection.execute(
        """
        SELECT
            l1.IndexCode,
            l1.IndustryName,
            list(l2.IndexCode ORDER BY l2.IndexCode) AS children
        FROM IndustryTaxonomyData l1
        JOIN IndustryTaxonomyData l2
          ON l2.ParentCode = l1.IndustryCode
         AND l2.Level = 'L2'
         AND l2.IsPub = 1
         AND l2.Src = 'SW2021'
        WHERE l1.Level = 'L1'
          AND l1.IsPub = 1
          AND l1.Src = 'SW2021'
        GROUP BY l1.IndexCode, l1.IndustryName
        ORDER BY l1.IndexCode
        """
    ).fetchall()
    names = {
        row[0]: row[1] for row in rows if row[0] not in EXCLUDED_L1_CODES
    }
    children = {
        row[0]: tuple(row[2])
        for row in rows
        if row[0] in names
    }
    if len(names) != 30 or any(len(values) < 2 for values in children.values()):
        raise ValueError("frozen 30-industry SW2021 universe is unavailable")
    return names, children


def load_weekly_bars(
    connection: duckdb.DuckDBPyConnection,
    codes: tuple[str, ...],
) -> dict[str, dict[date, WeeklyBar]]:
    placeholders = ",".join("?" for _ in codes)
    rows = connection.execute(
        f"""
        SELECT
            TSCode,
            CAST(date_trunc('week', TradeDate) + INTERVAL 4 DAY AS DATE) AS WeekEnd,
            arg_max(Close, TradeDate) AS Close,
            avg(coalesce(Amount, 0)) AS Amount
        FROM IndustryDailyData
        WHERE TSCode IN ({placeholders})
          AND Close > 0
        GROUP BY TSCode, WeekEnd
        ORDER BY TSCode, WeekEnd
        """,
        list(codes),
    ).fetchall()
    result: dict[str, dict[date, WeeklyBar]] = {code: {} for code in codes}
    for code, week_end, close, amount in rows:
        result[code][week_end] = WeeklyBar(
            week_end=week_end,
            close=float(close),
            amount=float(amount),
        )
    missing = [code for code, values in result.items() if not values]
    if missing:
        raise ValueError(f"weekly data missing for {missing}")
    return result


def common_weeks(
    bars: dict[str, dict[date, WeeklyBar]],
    required_codes: tuple[str, ...],
) -> tuple[date, ...]:
    weeks = set(bars[required_codes[0]])
    for code in required_codes[1:]:
        weeks &= set(bars[code])
    result = tuple(sorted(weeks))
    if len(result) <= WARMUP_WEEKS:
        raise ValueError("insufficient common weekly history")
    return result


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _return(values: list[float], window: int) -> float:
    return values[-1] / values[-window - 1] - 1.0


def _bandwidth(values: list[float]) -> float:
    average = _mean(values)
    return 4.0 * statistics.pstdev(values) / average


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(math.ceil(len(ordered) * percentile) - 1, 0)
    return ordered[rank]


def _exact_closes(
    code: str,
    end_index: int,
    count: int,
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
) -> list[float] | None:
    selected = weeks[end_index - count + 1 : end_index + 1]
    if len(selected) != count or any(week not in bars[code] for week in selected):
        return None
    return [bars[code][week].close for week in selected]


def _child_breadth(
    child_codes: tuple[str, ...],
    end_index: int,
    ma_window: int,
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
) -> tuple[float, float]:
    above = 0
    eligible = 0
    for code in child_codes:
        closes = _exact_closes(code, end_index, ma_window, weeks, bars)
        if closes is None:
            continue
        eligible += 1
        above += closes[-1] > _mean(closes)
    coverage = eligible / len(child_codes)
    return (above / eligible if eligible else 0.0), coverage


def _child_diffusion(
    child_codes: tuple[str, ...],
    end_index: int,
    benchmark_closes: list[float],
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
) -> tuple[float, float]:
    benchmark_return = _return(benchmark_closes, 4)
    outperforming = 0
    eligible = 0
    for code in child_codes:
        closes = _exact_closes(code, end_index, 5, weeks, bars)
        if closes is None:
            continue
        eligible += 1
        outperforming += _return(closes, 4) > benchmark_return
    coverage = eligible / len(child_codes)
    return (outperforming / eligible if eligible else 0.0), coverage


def build_features(
    names: dict[str, str],
    children: dict[str, tuple[str, ...]],
    bars: dict[str, dict[date, WeeklyBar]],
    weeks: tuple[date, ...],
) -> dict[date, dict[str, IndustryFeature]]:
    features: dict[date, dict[str, IndustryFeature]] = {}
    benchmark_values = [bars[BENCHMARK_CODE][week].close for week in weeks]
    for index in range(WARMUP_WEEKS - 1, len(weeks)):
        week = weeks[index]
        benchmark_history = benchmark_values[: index + 1]
        week_features: dict[str, IndustryFeature] = {}
        for code, name in names.items():
            closes = [bars[code][value].close for value in weeks[: index + 1]]
            amounts = [bars[code][value].amount for value in weeks[: index + 1]]
            child_codes = children[code]

            breadth_now, coverage_now = _child_breadth(
                child_codes, index, 13, weeks, bars
            )
            breadth_prior, coverage_prior = _child_breadth(
                child_codes, index - 4, 13, weeks, bars
            )
            breadth_acceleration = breadth_now - breadth_prior
            breadth_acceleration_ok = (
                min(coverage_now, coverage_prior) >= 0.80
                and breadth_acceleration >= 0.20
            )

            ratios = [
                industry / benchmark
                for industry, benchmark in zip(
                    closes[-6:], benchmark_history[-6:], strict=True
                )
            ]
            current_relative_ma = _mean(ratios[-4:])
            prior_relative_ma = _mean(ratios[-6:-2])
            relative_strength_turn = (
                ratios[-1] > current_relative_ma
                and current_relative_ma > prior_relative_ma
            )

            bandwidths = [
                _bandwidth(closes[end - 4 : end])
                for end in range(len(closes) - 51, len(closes) + 1)
            ]
            volatility_compression = bandwidths[-1] <= _percentile(
                bandwidths, 0.30
            )

            turnover_ratio = _mean(amounts[-4:]) / _mean(amounts[-13:])
            turnover_expansion = turnover_ratio >= 1.20

            diffusion, diffusion_coverage = _child_diffusion(
                child_codes, index, benchmark_history, weeks, bars
            )
            diffusion_ok = diffusion_coverage >= 0.80 and diffusion >= 2.0 / 3.0

            excess_4w = _return(closes, 4) - _return(benchmark_history, 4)
            excess_13w = _return(closes, 13) - _return(benchmark_history, 13)
            trend_ok = closes[-1] > _mean(closes[-26:])
            relative_13w_ok = excess_13w > 0
            breadth_ok = coverage_now >= 0.80 and breadth_now >= 0.55

            leading_conditions = (
                breadth_acceleration_ok,
                relative_strength_turn,
                volatility_compression,
                turnover_expansion,
                diffusion_ok,
            )
            confirmation_conditions = (trend_ok, relative_13w_ok, breadth_ok)
            week_features[code] = IndustryFeature(
                code=code,
                name=name,
                leading_score=sum(leading_conditions),
                confirmation_score=sum(confirmation_conditions),
                excess_4w=excess_4w,
                excess_13w=excess_13w,
                breadth_13w=breadth_now,
                breadth_acceleration=breadth_acceleration,
                breadth_coverage=coverage_now,
                relative_strength_turn=relative_strength_turn,
                volatility_compression=volatility_compression,
                turnover_expansion=turnover_expansion,
                subindustry_diffusion=diffusion,
                leading_conditions=leading_conditions,
                confirmation_conditions=confirmation_conditions,
            )
        features[week] = week_features
    return features


def _warning_ranking(
    rows: dict[str, IndustryFeature], warning_threshold: int
) -> list[IndustryFeature]:
    return sorted(
        (row for row in rows.values() if row.leading_score >= warning_threshold),
        key=lambda row: (
            row.leading_score,
            row.excess_4w,
            row.excess_13w,
            row.code,
        ),
        reverse=True,
    )


def select_weights(
    rows: dict[str, IndustryFeature],
    strategy: str,
    top_k: int,
    warning_threshold: int,
) -> dict[str, float]:
    values = list(rows.values())
    if strategy == "all_industries":
        selected = values
    elif strategy == "momentum":
        selected = sorted(
            values,
            key=lambda row: (row.excess_13w, row.excess_4w, row.code),
            reverse=True,
        )[:top_k]
    elif strategy == "confirmation":
        selected = sorted(
            values,
            key=lambda row: (
                row.confirmation_score,
                row.excess_13w,
                row.leading_score,
                row.code,
            ),
            reverse=True,
        )[:top_k]
    elif strategy == "warning":
        selected = _warning_ranking(rows, warning_threshold)[:top_k]
    elif strategy == "hybrid":
        candidates = [row for row in values if row.confirmation_score >= 2]
        selected = sorted(
            candidates,
            key=lambda row: (
                row.leading_score,
                row.confirmation_score,
                row.excess_13w,
                row.code,
            ),
            reverse=True,
        )[:top_k]
    else:
        raise ValueError(f"unknown strategy {strategy}")
    if not selected:
        return {}
    weight = 1.0 / len(selected)
    return {row.code: weight for row in selected}


def _buy_turnover(previous: dict[str, float], current: dict[str, float]) -> float:
    return sum(
        max(current.get(code, 0.0) - previous.get(code, 0.0), 0.0)
        for code in set(previous) | set(current)
    )


def run_strategy(
    *,
    strategy: str,
    features: dict[date, dict[str, IndustryFeature]],
    bars: dict[str, dict[date, WeeklyBar]],
    weeks: tuple[date, ...],
    start_date: date,
    top_k: int,
    cost_bps: int,
    warning_threshold: int,
    rebalance_every: int = 1,
    minimum_hold_weeks: int = 8,
) -> RunResult:
    week_index = {week: index for index, week in enumerate(weeks)}
    signal_weeks = [
        week
        for week in features
        if week >= start_date and week_index[week] + 1 < len(weeks)
    ]
    previous: dict[str, float] = {}
    locked_until: dict[str, int] = {}
    returns: list[float] = []
    turnovers: list[float] = []
    invested: list[bool] = []
    result_dates: list[date] = []
    for position, week in enumerate(signal_weeks):
        next_week = weeks[week_index[week] + 1]
        if position % rebalance_every != 0:
            weights = previous
        elif strategy == "warning_hold":
            locked = [
                code
                for code in previous
                if position < locked_until.get(code, -1)
            ]
            selected = locked[:top_k]
            for row in _warning_ranking(features[week], warning_threshold):
                if row.code not in selected:
                    selected.append(row.code)
                if len(selected) == top_k:
                    break
            for code in selected:
                if code not in previous:
                    locked_until[code] = position + minimum_hold_weeks
            weights = (
                {code: 1.0 / len(selected) for code in selected}
                if selected
                else {}
            )
        else:
            weights = select_weights(
                features[week], strategy, top_k, warning_threshold
            )
        turnover = _buy_turnover(previous, weights)
        gross_return = sum(
            weight
            * (bars[code][next_week].close / bars[code][week].close - 1.0)
            for code, weight in weights.items()
        )
        returns.append(gross_return - turnover * cost_bps / 10_000.0)
        turnovers.append(turnover)
        invested.append(bool(weights))
        result_dates.append(next_week)
        previous = weights
    return RunResult(
        name=strategy,
        dates=tuple(result_dates),
        returns=tuple(returns),
        turnovers=tuple(turnovers),
        invested=tuple(invested),
    )


def run_benchmark(
    bars: dict[str, dict[date, WeeklyBar]],
    weeks: tuple[date, ...],
    start_date: date,
) -> RunResult:
    selected = [week for week in weeks if week >= start_date]
    returns = tuple(
        bars[BENCHMARK_CODE][selected[index + 1]].close
        / bars[BENCHMARK_CODE][selected[index]].close
        - 1.0
        for index in range(len(selected) - 1)
    )
    return RunResult(
        name="broad_market",
        dates=tuple(selected[1:]),
        returns=returns,
        turnovers=(0.0,) * len(returns),
        invested=(True,) * len(returns),
    )


def metrics(result: RunResult, baseline: RunResult | None = None) -> dict[str, Any]:
    if not result.returns:
        raise ValueError("run has no returns")
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    year_wealth: dict[int, float] = {}
    for current_date, weekly_return in zip(
        result.dates, result.returns, strict=True
    ):
        wealth *= 1.0 + weekly_return
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
        year_wealth[current_date.year] = year_wealth.get(current_date.year, 1.0) * (
            1.0 + weekly_return
        )
    years = max((result.dates[-1] - result.dates[0]).days / 365.25, 1 / 52)
    cagr = wealth ** (1.0 / years) - 1.0
    volatility = statistics.pstdev(result.returns) * math.sqrt(52)
    sharpe = (
        statistics.mean(result.returns)
        / statistics.pstdev(result.returns)
        * math.sqrt(52)
        if statistics.pstdev(result.returns) > 0
        else None
    )
    baseline_returns = (
        dict(zip(baseline.dates, baseline.returns, strict=True))
        if baseline is not None
        else {}
    )
    comparable = [
        weekly_return > baseline_returns[current_date]
        for current_date, weekly_return in zip(
            result.dates, result.returns, strict=True
        )
        if current_date in baseline_returns
    ]
    return {
        "total_return": wealth - 1.0,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0 else None,
        "annualized_turnover": sum(result.turnovers) / years,
        "invested_week_fraction": sum(result.invested) / len(result.invested),
        "weekly_win_rate_vs_all": (
            sum(comparable) / len(comparable) if comparable else None
        ),
        "week_count": len(result.returns),
        "year_returns": {
            str(year): value - 1.0 for year, value in sorted(year_wealth.items())
        },
    }


def _future_excess(
    code: str,
    index: int,
    horizon: int,
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
) -> float:
    start = weeks[index]
    end = weeks[index + horizon]
    return (
        bars[code][end].close / bars[code][start].close
        - bars[BENCHMARK_CODE][end].close / bars[BENCHMARK_CODE][start].close
    )


def launch_events(
    *,
    features: dict[date, dict[str, IndustryFeature]],
    names: dict[str, str],
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
    start_date: date,
    event_kind: str,
) -> list[dict[str, Any]]:
    week_index = {week: index for index, week in enumerate(weeks)}
    last_event = {code: -100 for code in names}
    events: list[dict[str, Any]] = []
    for week in sorted(features):
        index = week_index[week]
        if week < start_date or index + 13 >= len(weeks):
            continue
        for code in names:
            future_4w = _future_excess(code, index, 4, weeks, bars)
            future_13w = _future_excess(code, index, 13, weeks, bars)
            qualifies = (
                future_4w >= 0.08 and future_13w > 0
                if event_kind == "fast_4w"
                else future_13w >= 0.10
                if event_kind == "sustained_13w"
                else False
            )
            if qualifies and index - last_event[code] >= 13:
                row = features[week][code]
                events.append(
                    {
                        "event_kind": event_kind,
                        "code": code,
                        "name": names[code],
                        "week": week.isoformat(),
                        "week_index": index,
                        "future_4w_excess": future_4w,
                        "future_13w_excess": future_13w,
                        "leading_score": row.leading_score,
                        "confirmation_score": row.confirmation_score,
                        "leading_conditions": list(row.leading_conditions),
                        "confirmation_conditions": list(
                            row.confirmation_conditions
                        ),
                    }
                )
                last_event[code] = index
    return events


def detection_metrics(
    *,
    signal: str,
    threshold: int,
    events: list[dict[str, Any]],
    features: dict[date, dict[str, IndustryFeature]],
    names: dict[str, str],
    weeks: tuple[date, ...],
    start_date: date,
    event_kind: str,
    lead_window_weeks: int,
) -> DetectionResult:
    week_index = {week: index for index, week in enumerate(weeks)}
    event_by_code = {code: [] for code in names}
    for event in events:
        event_by_code[event["code"]].append(event["week_index"])

    signal_starts: list[tuple[str, int]] = []
    for code in names:
        previous = False
        last_start = -100
        for week in sorted(features):
            if week < start_date:
                continue
            index = week_index[week]
            row = features[week][code]
            active = (
                row.leading_score >= threshold
                if signal == "warning"
                else row.confirmation_score >= threshold
            )
            if active and not previous and index - last_start >= 4:
                signal_starts.append((code, index))
                last_start = index
            previous = active

    warning_hits = [
        any(
            signal_index <= event_index <= signal_index + lead_window_weeks
            for event_index in event_by_code[code]
        )
        for code, signal_index in signal_starts
    ]
    event_leads: list[int] = []
    for event in events:
        code = event["code"]
        event_index = event["week_index"]
        candidates = []
        for week in sorted(features):
            index = week_index[week]
            if index < event_index - lead_window_weeks or index > event_index:
                continue
            row = features[week][code]
            active = (
                row.leading_score >= threshold
                if signal == "warning"
                else row.confirmation_score >= threshold
            )
            if active:
                candidates.append(event_index - index)
        if candidates:
            event_leads.append(max(candidates))

    study_weeks = [week for week in features if week >= start_date]
    years = max((study_weeks[-1] - study_weeks[0]).days / 365.25, 1 / 52)
    false_alarms = len(warning_hits) - sum(warning_hits)
    return DetectionResult(
        event_kind=event_kind,
        lead_window_weeks=lead_window_weeks,
        signal=signal,
        threshold=threshold,
        event_count=len(events),
        signal_count=len(signal_starts),
        recall=len(event_leads) / len(events) if events else None,
        precision=sum(warning_hits) / len(warning_hits) if warning_hits else None,
        false_alarms_per_year=false_alarms / years,
        median_lead_weeks=(statistics.median(event_leads) if event_leads else None),
    )


def score_calibration(
    *,
    features: dict[date, dict[str, IndustryFeature]],
    names: dict[str, str],
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
    start_date: date,
) -> list[dict[str, Any]]:
    week_index = {week: index for index, week in enumerate(weeks)}
    grouped: dict[tuple[str, int], list[tuple[float, float]]] = {}
    for week, rows in features.items():
        index = week_index[week]
        if week < start_date or index + 13 >= len(weeks):
            continue
        for code in names:
            future_4w = _future_excess(code, index, 4, weeks, bars)
            future_13w = _future_excess(code, index, 13, weeks, bars)
            for field in ("leading_score", "confirmation_score"):
                score = getattr(rows[code], field)
                grouped.setdefault((field, score), []).append(
                    (future_4w, future_13w)
                )
    result = []
    for (field, score), values in sorted(grouped.items()):
        result.append(
            {
                "score_type": field,
                "score": score,
                "sample_count": len(values),
                "average_future_4w_excess": statistics.mean(
                    value[0] for value in values
                ),
                "average_future_13w_excess": statistics.mean(
                    value[1] for value in values
                ),
                "fast_launch_rate": sum(
                    future_4w >= 0.08 and future_13w > 0
                    for future_4w, future_13w in values
                )
                / len(values),
                "sustained_launch_rate": sum(
                    future_13w >= 0.10 for _, future_13w in values
                )
                / len(values),
            }
        )
    return result


def healthcare_cases(
    *,
    events: list[dict[str, Any]],
    features: dict[date, dict[str, IndustryFeature]],
    weeks: tuple[date, ...],
    bars: dict[str, dict[date, WeeklyBar]],
    start_date: date,
) -> list[dict[str, Any]]:
    cases = [event for event in events if event["code"] == HEALTHCARE_CODE]
    cases = sorted(cases, key=lambda value: value["future_13w_excess"], reverse=True)[:6]
    if not any(date.fromisoformat(value["week"]).year >= 2025 for value in cases):
        week_index = {week: index for index, week in enumerate(weeks)}
        recent = []
        for week in sorted(features):
            index = week_index[week]
            if week < max(start_date, date(2025, 1, 1)) or index + 13 >= len(weeks):
                continue
            row = features[week][HEALTHCARE_CODE]
            recent.append(
                {
                    "code": HEALTHCARE_CODE,
                    "name": "医药生物",
                    "week": week.isoformat(),
                    "week_index": index,
                    "future_4w_excess": _future_excess(
                        HEALTHCARE_CODE, index, 4, weeks, bars
                    ),
                    "future_13w_excess": _future_excess(
                        HEALTHCARE_CODE, index, 13, weeks, bars
                    ),
                    "leading_score": row.leading_score,
                    "confirmation_score": row.confirmation_score,
                    "leading_conditions": list(row.leading_conditions),
                    "confirmation_conditions": list(row.confirmation_conditions),
                }
            )
        if recent:
            cases.append(max(recent, key=lambda value: value["future_13w_excess"]))

    enriched = []
    for case in cases:
        event_index = case["week_index"]
        prior_rows = [
            (event_index - index, features[weeks[index]][HEALTHCARE_CODE])
            for index in range(max(event_index - 8, 0), event_index + 1)
            if weeks[index] in features
        ]
        warning_leads = [lead for lead, row in prior_rows if row.leading_score >= 3]
        confirmation_leads = [
            lead for lead, row in prior_rows if row.confirmation_score >= 2
        ]
        enriched.append(
            {
                **case,
                "prior_8w_max_leading_score": max(
                    row.leading_score for _, row in prior_rows
                ),
                "prior_8w_max_confirmation_score": max(
                    row.confirmation_score for _, row in prior_rows
                ),
                "warning_3_earliest_lead_weeks": (
                    max(warning_leads) if warning_leads else None
                ),
                "confirmation_2_earliest_lead_weeks": (
                    max(confirmation_leads) if confirmation_leads else None
                ),
            }
        )
    return enriched


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.2%}"


def render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# A 股申万行业启动识别与轮动回测",
        "",
        f"- 数据库：`{payload['database']['path']}`",
        f"- SHA-256：`{payload['database']['sha256']}`",
        f"- 周频区间：{payload['data']['first_week']} 至 {payload['data']['last_week']}",
        f"- 行业宇宙：{payload['data']['industry_count']} 个 SW2021 一级行业（排除综合）",
        "- 信号在本周收盘后形成，收益使用下一周收盘；指数价格收益，不代表 ETF 净收益。",
        "",
    ]
    for section in ("primary", "extended"):
        lines += [
            f"## {payload[section]['label']}",
            "",
            "| 策略 | CAGR | 波动 | Sharpe | 最大回撤 | Calmar | 年换手 | 持仓周 | 周胜率vs等权 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for name, values in payload[section]["main"].items():
            lines.append(
                f"| {name} | {_pct(values['cagr'])} | {_pct(values['annualized_volatility'])} | "
                f"{('—' if values['sharpe'] is None else f'{values['sharpe']:.2f}')} | "
                f"{_pct(values['max_drawdown'])} | "
                f"{('—' if values['calmar'] is None else f'{values['calmar']:.2f}')} | "
                f"{values['annualized_turnover']:.2f} | {_pct(values['invested_week_fraction'])} | "
                f"{_pct(values['weekly_win_rate_vs_all'])} |"
            )
        lines += [
            "",
            "### 再平衡频率敏感性（Top-3、20bp、warning阈值3）",
            "",
            "| 策略 | 每隔几周再平衡 | CAGR | 最大回撤 | 年换手 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for values in payload[section]["rebalance_sensitivity"]:
            lines.append(
                f"| {values['strategy']} | {values['rebalance_every_weeks']} | "
                f"{_pct(values['cagr'])} | {_pct(values['max_drawdown'])} | "
                f"{values['annualized_turnover']:.2f} |"
            )
        lines += [
            "",
            "### warning 固定持有期敏感性（20bp、阈值3）",
            "",
            "| Top-K | 最短持有周 | CAGR | 最大回撤 | 年换手 |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
        for values in payload[section]["hold_sensitivity"]:
            lines.append(
                f"| {values['top_k']} | {values['minimum_hold_weeks']} | "
                f"{_pct(values['cagr'])} | {_pct(values['max_drawdown'])} | "
                f"{values['annualized_turnover']:.2f} |"
            )
        lines.append("")

    lines += [
        "## 分数校准（2022—2026）",
        "",
        "| 分数类型 | 分数 | 样本 | 未来4周平均超额 | 未来13周平均超额 | 快启动率 | 慢启动率 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["score_calibration"]:
        lines.append(
            f"| {row['score_type']} | {row['score']} | {row['sample_count']} | "
            f"{_pct(row['average_future_4w_excess'])} | "
            f"{_pct(row['average_future_13w_excess'])} | "
            f"{_pct(row['fast_launch_rate'])} | {_pct(row['sustained_launch_rate'])} |"
        )

    lines += [
        "",
        "## 启动事件识别",
        "",
        "快启动定义为未来四周相对申万A指超额至少 8% 且未来十三周为正；慢启动定义为未来十三周超额至少 10%。同一行业事件间隔至少十三周。",
        "",
        "| 事件 | 观察窗 | 信号 | 阈值 | 事件数 | 新信号数 | Recall | Precision | 假警报/年 | 中位提前周 |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["detection"]:
        lines.append(
            f"| {row['event_kind']} | {row['lead_window_weeks']}周 | {row['signal']} | "
            f"{row['threshold']} | {row['event_count']} | {row['signal_count']} | "
            f"{_pct(row['recall'])} | {_pct(row['precision'])} | {row['false_alarms_per_year']:.1f} | "
            f"{('—' if row['median_lead_weeks'] is None else f'{row['median_lead_weeks']:.1f}')} |"
        )

    lines += [
        "",
        "## 医药生物案例",
        "",
        "| 信号周 | 未来4周超额 | 未来13周超额 | 当周领先/确认 | 前8周最高领先/确认 | warning≥3最早提前 | confirmation≥2最早提前 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in payload["healthcare_cases"]:
        lines.append(
            f"| {case['week']} | {_pct(case['future_4w_excess'])} | "
            f"{_pct(case['future_13w_excess'])} | {case['leading_score']}/{case['confirmation_score']} | "
            f"{case['prior_8w_max_leading_score']}/{case['prior_8w_max_confirmation_score']} | "
            f"{('—' if case['warning_3_earliest_lead_weeks'] is None else str(case['warning_3_earliest_lead_weeks']) + '周')} | "
            f"{('—' if case['confirmation_2_earliest_lead_weeks'] is None else str(case['confirmation_2_earliest_lead_weeks']) + '周')} |"
        )

    lines += [
        "",
        "## 限制",
        "",
        "- 2022 年前使用 SW2021 taxonomy 回溯历史，属于 post-hoc 分类稳健性检查，不是当时可部署证据。",
        "- 行业日线在部分周只有少量观察；周频降低但没有消除来源缺口。",
        "- 行业指数不可直接交易，未计 ETF 跟踪误差、复制冲击、股息和次周开盘跳空。",
        "- 结果只能判断固定规则在该样本中的增量价值，不能证明未来收益。",
        "",
    ]
    return "\n".join(lines)


def run_study(database: Path) -> dict[str, Any]:
    connection = duckdb.connect(str(database), read_only=True)
    names, children = load_taxonomy(connection)
    all_codes = tuple(
        sorted(
            {BENCHMARK_CODE, *names, *(code for values in children.values() for code in values)}
        )
    )
    bars = load_weekly_bars(connection, all_codes)
    weeks = common_weeks(bars, tuple(sorted({BENCHMARK_CODE, *names})))
    features = build_features(names, children, bars, weeks)

    study_specs = {
        "primary": ("主结论：2022-01 至 2026-05", date(2022, 1, 1)),
        "extended": ("扩展回溯：2016 至 2026-05", next(iter(features))),
    }
    study_payload: dict[str, Any] = {}
    primary_fast_events: list[dict[str, Any]] = []
    primary_sustained_events: list[dict[str, Any]] = []
    for key, (label, start_date) in study_specs.items():
        broad = run_benchmark(bars, weeks, start_date)
        all_industries = run_strategy(
            strategy="all_industries",
            features=features,
            bars=bars,
            weeks=weeks,
            start_date=start_date,
            top_k=3,
            cost_bps=20,
            warning_threshold=3,
        )
        runs = {
            "broad_market": broad,
            "all_industries": all_industries,
            **{
                strategy: run_strategy(
                    strategy=strategy,
                    features=features,
                    bars=bars,
                    weeks=weeks,
                    start_date=start_date,
                    top_k=3,
                    cost_bps=20,
                    warning_threshold=3,
                )
                for strategy in (
                    "momentum",
                    "confirmation",
                    "warning",
                    "warning_hold",
                    "hybrid",
                )
            },
        }
        main = {
            name: metrics(result, all_industries if name != "all_industries" else None)
            for name, result in runs.items()
        }
        sensitivity = []
        for top_k in (1, 3, 5):
            for cost_bps in (0, 20, 50):
                for threshold in (2, 3, 4):
                    for strategy in ("momentum", "confirmation", "warning", "hybrid"):
                        result = run_strategy(
                            strategy=strategy,
                            features=features,
                            bars=bars,
                            weeks=weeks,
                            start_date=start_date,
                            top_k=top_k,
                            cost_bps=cost_bps,
                            warning_threshold=threshold,
                        )
                        sensitivity.append(
                            {
                                "strategy": strategy,
                                "top_k": top_k,
                                "cost_bps": cost_bps,
                                "warning_threshold": threshold,
                                **metrics(result, all_industries),
                            }
                        )
        rebalance_sensitivity = []
        for rebalance_every in (1, 2, 4):
            for strategy in ("momentum", "confirmation", "warning", "hybrid"):
                result = run_strategy(
                    strategy=strategy,
                    features=features,
                    bars=bars,
                    weeks=weeks,
                    start_date=start_date,
                    top_k=3,
                    cost_bps=20,
                    warning_threshold=3,
                    rebalance_every=rebalance_every,
                )
                rebalance_sensitivity.append(
                    {
                        "strategy": strategy,
                        "rebalance_every_weeks": rebalance_every,
                        **metrics(result, all_industries),
                    }
                )
        hold_sensitivity = []
        for top_k in (1, 3, 5):
            for minimum_hold_weeks in (4, 8, 13):
                result = run_strategy(
                    strategy="warning_hold",
                    features=features,
                    bars=bars,
                    weeks=weeks,
                    start_date=start_date,
                    top_k=top_k,
                    cost_bps=20,
                    warning_threshold=3,
                    minimum_hold_weeks=minimum_hold_weeks,
                )
                hold_sensitivity.append(
                    {
                        "top_k": top_k,
                        "minimum_hold_weeks": minimum_hold_weeks,
                        **metrics(result, all_industries),
                    }
                )
        study_payload[key] = {
            "label": label,
            "start_date": start_date.isoformat(),
            "main": main,
            "sensitivity": sensitivity,
            "rebalance_sensitivity": rebalance_sensitivity,
            "hold_sensitivity": hold_sensitivity,
        }
        if key == "primary":
            primary_fast_events = launch_events(
                features=features,
                names=names,
                weeks=weeks,
                bars=bars,
                start_date=start_date,
                event_kind="fast_4w",
            )
            primary_sustained_events = launch_events(
                features=features,
                names=names,
                weeks=weeks,
                bars=bars,
                start_date=start_date,
                event_kind="sustained_13w",
            )

    detection = [
        asdict(
            detection_metrics(
                signal=signal,
                threshold=threshold,
                events=events,
                features=features,
                names=names,
                weeks=weeks,
                start_date=date(2022, 1, 1),
                event_kind=event_kind,
                lead_window_weeks=lead_window_weeks,
            )
        )
        for event_kind, lead_window_weeks, events in (
            ("fast_4w", 4, primary_fast_events),
            ("sustained_13w", 8, primary_sustained_events),
        )
        for signal, thresholds in (
            ("warning", (2, 3, 4)),
            ("confirmation", (1, 2, 3)),
        )
        for threshold in thresholds
    ]
    payload = {
        "database": {
            "path": str(database),
            "size_bytes": database.stat().st_size,
            "sha256": _sha256(database),
        },
        "data": {
            "industry_count": len(names),
            "first_week": weeks[0].isoformat(),
            "last_week": weeks[-1].isoformat(),
            "common_week_count": len(weeks),
            "feature_week_count": len(features),
            "benchmark_code": BENCHMARK_CODE,
            "healthcare_code": HEALTHCARE_CODE,
            "industries": names,
            "children": {code: list(values) for code, values in children.items()},
        },
        **study_payload,
        "score_calibration": score_calibration(
            features=features,
            names=names,
            weeks=weeks,
            bars=bars,
            start_date=date(2022, 1, 1),
        ),
        "event_definition": {
            "fast_4w": {
                "future_4w_excess_min": 0.08,
                "future_13w_excess_min": 0.0,
                "lead_window_weeks": 4,
            },
            "sustained_13w": {
                "future_13w_excess_min": 0.10,
                "lead_window_weeks": 8,
            },
            "same_industry_cooldown_weeks": 13,
        },
        "event_count": {
            "fast_4w": len(primary_fast_events),
            "sustained_13w": len(primary_sustained_events),
        },
        "detection": detection,
        "healthcare_cases": healthcare_cases(
            events=primary_sustained_events,
            features=features,
            weeks=weeks,
            bars=bars,
            start_date=date(2022, 1, 1),
        ),
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("overall/a-share-sector-rotation-backtest.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("overall/a-share-sector-rotation-backtest.md"),
    )
    args = parser.parse_args()
    payload = run_study(args.database)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.markdown_output.write_text(render_report(payload), encoding="utf-8")
    print(args.markdown_output)


if __name__ == "__main__":
    main()
