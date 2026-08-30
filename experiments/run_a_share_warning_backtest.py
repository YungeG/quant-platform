"""Build and evaluate the research-only KSTAR early-warning prototype."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
import urllib.request
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from experiments.a_share_risk_state import (
    EARLY_CONFIRMATION_CONFIG,
    BreadthSnapshot,
    CloseSeries,
    PricePoint,
    RiskPhase,
    classify_phase,
    evaluate_early_warning,
    evaluate_risk_state_from_breadth,
)


SOHU_URL = (
    "https://q.stock.sohu.com/hisHq?code=zs_{code}&start=20190101&end={end}"
    "&stat=1&order=D&period=d&rt=json"
)
SECTORS = (
    ("801081.SI", "semiconductor"),
    ("801104.SI", "software"),
    ("801078.SI", "automation-equipment"),
)


@dataclass(frozen=True, slots=True)
class BreadthRow:
    trading_date: date
    breadth20: Decimal
    eligible20: int
    breadth60: Decimal
    eligible60: int
    expected: int


@dataclass(frozen=True, slots=True)
class WeeklySignal:
    trading_date: date
    phase: str
    watch: bool
    confirmed: bool
    conditions_met: int
    breadth_acceleration: float
    relative_strength_spread: float
    current_bandwidth: float
    bandwidth_cutoff: float
    turnover_ratio: float
    sector_diffusion: float


@dataclass(frozen=True, slots=True)
class StrategyResult:
    name: str
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float | None
    max_drawdown: float
    calmar: float | None
    switches: int
    average_target_weight: float
    year_returns: dict[str, float]


def _decode_json(raw: bytes) -> object:
    for encoding in ("utf-8", "gb18030"):
        try:
            return json.loads(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError("Sohu response encoding is unsupported")


def fetch_sohu_series(
    code: str,
    name: str,
    end_date: date,
    cache_dir: Path,
) -> tuple[CloseSeries, dict[str, object]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"sohu-zs-{code}-through-{end_date:%Y%m%d}.json"
    url = SOHU_URL.format(code=code, end=end_date.strftime("%Y%m%d"))
    if path.exists():
        raw = path.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        for attempt in range(1, 6):
            try:
                raw = urllib.request.urlopen(request, timeout=30).read()
                break
            except OSError:
                if attempt == 5:
                    raise
                time.sleep(attempt * 2)
        path.write_bytes(raw)
        time.sleep(2)

    payload = _decode_json(raw)
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError(f"unexpected Sohu envelope for {code}")
    envelope = payload[0]
    if not isinstance(envelope, dict) or envelope.get("status") != 0:
        raise ValueError(f"Sohu rejected {code}")
    rows = envelope.get("hq")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Sohu returned no rows for {code}")

    points = []
    for row in reversed(rows):
        if not isinstance(row, list) or len(row) < 9:
            raise ValueError(f"malformed Sohu row for {code}")
        points.append(
            PricePoint(
                date.fromisoformat(row[0]),
                Decimal(row[2]),
                Decimal(row[8]),
            )
        )
    series = CloseSeries(name, tuple(points))
    return series, {
        "url": url,
        "cache_path": str(path),
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "rows": len(points),
        "first_date": points[0].trading_date.isoformat(),
        "last_date": points[-1].trading_date.isoformat(),
    }


def load_sector_series(
    connection: duckdb.DuckDBPyConnection,
    code: str,
    name: str,
    end_date: date,
) -> CloseSeries:
    rows = connection.execute(
        """
        SELECT TradeDate, Close
        FROM IndustryDailyData
        WHERE TSCode = ? AND TradeDate <= ?
        ORDER BY TradeDate
        """,
        [code, end_date],
    ).fetchall()
    return CloseSeries(
        name,
        tuple(PricePoint(row[0], Decimal(str(row[1]))) for row in rows),
    )


def load_star_breadth(
    connection: duckdb.DuckDBPyConnection,
    end_date: date,
) -> dict[date, BreadthRow]:
    rows = connection.execute(
        """
        WITH star AS (
            SELECT
                TradingDay,
                Symbol,
                Close,
                count(*) OVER (
                    PARTITION BY Symbol ORDER BY TradingDay
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS history_count,
                avg(Close) OVER (
                    PARTITION BY Symbol ORDER BY TradingDay
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS ma20,
                avg(Close) OVER (
                    PARTITION BY Symbol ORDER BY TradingDay
                    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                ) AS ma60
            FROM MarketData
            WHERE (Symbol LIKE '688%' OR Symbol LIKE '689%')
              AND TradingDay <= ?
        ),
        bounds AS (
            SELECT Symbol, min(TradingDay) AS first_day, max(TradingDay) AS last_day
            FROM MarketData
            WHERE Symbol LIKE '688%' OR Symbol LIKE '689%'
            GROUP BY Symbol
        ),
        calendar AS (
            SELECT DISTINCT TradingDay FROM star
        ),
        expected AS (
            SELECT calendar.TradingDay, count(*) AS expected_count
            FROM calendar
            JOIN bounds
              ON calendar.TradingDay BETWEEN bounds.first_day AND bounds.last_day
            GROUP BY calendar.TradingDay
        ),
        breadth AS (
            SELECT
                TradingDay,
                count(*) FILTER (WHERE history_count >= 20) AS eligible20,
                avg(CASE WHEN Close > ma20 THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE history_count >= 20) AS breadth20,
                count(*) FILTER (WHERE history_count >= 60) AS eligible60,
                avg(CASE WHEN Close > ma60 THEN 1.0 ELSE 0.0 END)
                    FILTER (WHERE history_count >= 60) AS breadth60
            FROM star
            GROUP BY TradingDay
        )
        SELECT
            breadth.TradingDay,
            breadth.breadth20,
            breadth.eligible20,
            breadth.breadth60,
            breadth.eligible60,
            expected.expected_count
        FROM breadth
        JOIN expected USING (TradingDay)
        WHERE breadth.eligible20 > 0 AND breadth.eligible60 > 0
        ORDER BY breadth.TradingDay
        """,
        [end_date],
    ).fetchall()
    return {
        row[0]: BreadthRow(
            trading_date=row[0],
            breadth20=Decimal(str(row[1])),
            eligible20=row[2],
            breadth60=Decimal(str(row[3])),
            eligible60=row[4],
            expected=row[5],
        )
        for row in rows
    }


def _prefix(series: CloseSeries, trading_date: date) -> CloseSeries:
    dates = [point.trading_date for point in series.points]
    end = bisect_right(dates, trading_date)
    if end == 0 or dates[end - 1] != trading_date:
        raise ValueError(f"{series.instrument} has no point for {trading_date}")
    return CloseSeries(series.instrument, series.points[:end])


def build_weekly_signals(
    target: CloseSeries,
    benchmark: CloseSeries,
    sectors: tuple[CloseSeries, ...],
    breadth: dict[date, BreadthRow],
) -> tuple[WeeklySignal, ...]:
    common_dates = set(point.trading_date for point in target.points)
    common_dates &= set(point.trading_date for point in benchmark.points)
    for sector in sectors:
        common_dates &= set(point.trading_date for point in sector.points)
    common_dates &= set(breadth)

    weekly_dates: dict[tuple[int, int], date] = {}
    for trading_date in sorted(common_dates):
        iso = trading_date.isocalendar()
        weekly_dates[(iso.year, iso.week)] = trading_date

    target_dates = [point.trading_date for point in target.points]
    signals = []
    for trading_date in weekly_dates.values():
        target_index = bisect_right(target_dates, trading_date) - 1
        if target_index < 270:
            continue
        prior_date = target_dates[target_index - 10]
        if prior_date not in breadth:
            continue
        target_prefix = _prefix(target, trading_date)
        benchmark_prefix = _prefix(benchmark, trading_date)
        sector_prefixes = tuple(_prefix(sector, trading_date) for sector in sectors)
        current = breadth[trading_date]
        prior = breadth[prior_date]
        warning = evaluate_early_warning(
            target=target_prefix,
            benchmark=benchmark_prefix,
            current_breadth=BreadthSnapshot(
                trading_date,
                current.breadth20,
                Decimal(current.eligible20) / Decimal(current.expected),
                current.eligible20,
                current.expected,
            ),
            prior_breadth=BreadthSnapshot(
                prior_date,
                prior.breadth20,
                Decimal(prior.eligible20) / Decimal(prior.expected),
                prior.eligible20,
                prior.expected,
            ),
            sectors=sector_prefixes,
        )
        confirmation = evaluate_risk_state_from_breadth(
            target=target_prefix,
            benchmark=benchmark_prefix,
            breadth=BreadthSnapshot(
                trading_date,
                current.breadth60,
                Decimal(current.eligible60) / Decimal(current.expected),
                current.eligible60,
                current.expected,
            ),
            config=EARLY_CONFIRMATION_CONFIG,
        )
        phase = classify_phase(warning=warning, confirmation=confirmation)
        signals.append(
            WeeklySignal(
                trading_date=trading_date,
                phase=phase.value,
                watch=warning.watch,
                confirmed=confirmation.risk_on,
                conditions_met=warning.conditions_met,
                breadth_acceleration=float(warning.breadth_acceleration),
                relative_strength_spread=float(warning.relative_strength_spread),
                current_bandwidth=float(warning.current_bandwidth),
                bandwidth_cutoff=float(warning.bandwidth_cutoff),
                turnover_ratio=float(warning.turnover_ratio),
                sector_diffusion=float(warning.sector_diffusion),
            )
        )
    return tuple(signals)


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    return drawdown


def simulate(
    name: str,
    weights: dict[date, float],
    target: CloseSeries,
    benchmark: CloseSeries,
    start_date: date,
    switch_cost: float,
) -> StrategyResult:
    target_close = {point.trading_date: float(point.close) for point in target.points}
    benchmark_close = {
        point.trading_date: float(point.close) for point in benchmark.points
    }
    dates = sorted(set(target_close) & set(benchmark_close))
    dates = [value for value in dates if value >= start_date]
    effective_weights = {}
    for signal_date, weight in weights.items():
        index = bisect_right(dates, signal_date)
        if index < len(dates):
            effective_weights[dates[index]] = weight

    current_weight = 0.0
    switches = 0
    daily_returns = []
    weights_used = []
    equity = [1.0]
    equity_dates = [dates[0]]
    for index, trading_date in enumerate(dates[:-1]):
        cost = 0.0
        if trading_date in effective_weights:
            next_weight = effective_weights[trading_date]
            change = abs(next_weight - current_weight)
            if change:
                cost = change * switch_cost
                switches += 1
            current_weight = next_weight
        next_date = dates[index + 1]
        target_return = target_close[next_date] / target_close[trading_date] - 1.0
        benchmark_return = (
            benchmark_close[next_date] / benchmark_close[trading_date] - 1.0
        )
        market_return = (
            current_weight * target_return + (1.0 - current_weight) * benchmark_return
        )
        daily_return = (1.0 - cost) * (1.0 + market_return) - 1.0
        daily_returns.append(daily_return)
        weights_used.append(current_weight)
        equity.append(equity[-1] * (1.0 + daily_return))
        equity_dates.append(next_date)

    years = (equity_dates[-1] - equity_dates[0]).days / 365.25
    cagr = equity[-1] ** (1.0 / years) - 1.0
    volatility = statistics.pstdev(daily_returns) * math.sqrt(252)
    mean_return = statistics.mean(daily_returns)
    daily_std = statistics.pstdev(daily_returns)
    sharpe = None if daily_std == 0 else mean_return / daily_std * math.sqrt(252)
    max_drawdown = _max_drawdown(equity)
    calmar = None if max_drawdown == 0 else cagr / abs(max_drawdown)

    year_returns = {}
    years_present = sorted({value.year for value in equity_dates})
    for year in years_present:
        end = max(i for i, value in enumerate(equity_dates) if value.year == year)
        prior = [i for i, value in enumerate(equity_dates) if value.year < year]
        start_equity = equity[prior[-1]] if prior else equity[0]
        year_returns[str(year)] = equity[end] / start_equity - 1.0

    return StrategyResult(
        name=name,
        total_return=equity[-1] - 1.0,
        cagr=cagr,
        annualized_volatility=volatility,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
        calmar=calmar,
        switches=switches,
        average_target_weight=statistics.mean(weights_used),
        year_returns=year_returns,
    )


def warning_quality(
    signals: tuple[WeeklySignal, ...],
    target: CloseSeries,
    benchmark: CloseSeries,
) -> dict[str, object]:
    target_close = {point.trading_date: float(point.close) for point in target.points}
    benchmark_close = {
        point.trading_date: float(point.close) for point in benchmark.points
    }
    dates = sorted(set(target_close) & set(benchmark_close))
    date_index = {value: index for index, value in enumerate(dates)}
    labelled = []
    entries = []
    previous_watch = False
    for signal in signals:
        index = date_index[signal.trading_date]
        if index + 60 >= len(dates):
            continue
        target20 = target_close[dates[index + 20]] / target_close[dates[index]] - 1.0
        benchmark20 = (
            benchmark_close[dates[index + 20]] / benchmark_close[dates[index]] - 1.0
        )
        target60 = target_close[dates[index + 60]] / target_close[dates[index]] - 1.0
        benchmark60 = (
            benchmark_close[dates[index + 60]] / benchmark_close[dates[index]] - 1.0
        )
        event = target20 - benchmark20 >= 0.05 and target60 - benchmark60 > 0
        labelled.append((signal, event))
        if signal.watch and not previous_watch:
            days_to_threshold = None
            for horizon in range(1, 21):
                target_return = (
                    target_close[dates[index + horizon]] / target_close[dates[index]] - 1.0
                )
                benchmark_return = (
                    benchmark_close[dates[index + horizon]]
                    / benchmark_close[dates[index]]
                    - 1.0
                )
                if target_return - benchmark_return >= 0.05:
                    days_to_threshold = horizon
                    break
            entries.append((event, days_to_threshold))
        previous_watch = signal.watch

    positives = sum(event for _, event in labelled)
    watch_count = sum(signal.watch for signal, _ in labelled)
    watch_hits = sum(signal.watch and event for signal, event in labelled)
    confirmed_count = sum(signal.confirmed for signal, _ in labelled)
    confirmed_hits = sum(signal.confirmed and event for signal, event in labelled)
    entry_hits = sum(event for event, _ in entries)
    leads = [lead for event, lead in entries if event and lead is not None]
    span_years = (
        (labelled[-1][0].trading_date - labelled[0][0].trading_date).days / 365.25
        if labelled
        else 0.0
    )
    return {
        "label_definition": "future20_excess>=5% and future60_excess>0",
        "labelled_weeks": len(labelled),
        "positive_weeks": positives,
        "positive_rate": None if not labelled else positives / len(labelled),
        "watch_weeks": watch_count,
        "watch_precision": None if watch_count == 0 else watch_hits / watch_count,
        "watch_recall": None if positives == 0 else watch_hits / positives,
        "confirmed_weeks": confirmed_count,
        "confirmed_precision": (
            None if confirmed_count == 0 else confirmed_hits / confirmed_count
        ),
        "confirmed_recall": None if positives == 0 else confirmed_hits / positives,
        "watch_entries": len(entries),
        "watch_entry_hits": entry_hits,
        "watch_entry_precision": None if not entries else entry_hits / len(entries),
        "false_watch_entries_per_year": (
            None
            if span_years == 0
            else (len(entries) - entry_hits) / span_years
        ),
        "median_trading_days_to_5pct_excess": (
            None if not leads else statistics.median(leads)
        ),
    }


def _strategy_weights(
    signals: tuple[WeeklySignal, ...],
) -> dict[str, dict[date, float]]:
    return {
        "benchmark_buy_hold": {signal.trading_date: 0.0 for signal in signals},
        "target_buy_hold": {signal.trading_date: 1.0 for signal in signals},
        "confirmation_only": {
            signal.trading_date: 1.0 if signal.confirmed else 0.0 for signal in signals
        },
        "warning_full": {
            signal.trading_date: 0.0
            if signal.phase == RiskPhase.OFF.value
            else 1.0
            for signal in signals
        },
        "warning_staged": {
            signal.trading_date: (
                1.0 if signal.phase == RiskPhase.ON.value else 0.5
                if signal.phase == RiskPhase.WATCH.value
                else 0.0
            )
            for signal in signals
        },
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    end_date = date.fromisoformat(args.end_date)
    cache_dir = Path(args.cache_dir)
    target, target_source = fetch_sohu_series(
        args.target_code, args.target_name, end_date, cache_dir
    )
    benchmark, benchmark_source = fetch_sohu_series(
        "000300", "csi-300", end_date, cache_dir
    )
    connection = duckdb.connect(args.database, read_only=True)
    sectors = tuple(
        load_sector_series(connection, code, name, end_date) for code, name in SECTORS
    )
    breadth = load_star_breadth(connection, end_date)
    signals = build_weekly_signals(target, benchmark, sectors, breadth)
    if not signals:
        raise RuntimeError("no weekly signals were produced")

    weights = _strategy_weights(signals)
    start_date = signals[0].trading_date
    switch_cost = args.switch_cost_bps / 10_000
    results = [
        simulate(name, values, target, benchmark, start_date, switch_cost)
        for name, values in weights.items()
    ]
    sensitivity = {}
    for cost_bps in (10, 20, 30, 50):
        sensitivity[str(cost_bps)] = {
            name: asdict(
                simulate(
                    name,
                    weights[name],
                    target,
                    benchmark,
                    start_date,
                    cost_bps / 10_000,
                )
            )
            for name in ("confirmation_only", "warning_full", "warning_staged")
        }
    condition_sensitivity = {}
    for minimum_conditions in (2, 3, 4, 5):
        condition_weights = {
            signal.trading_date: 1.0
            if signal.confirmed or signal.conditions_met >= minimum_conditions
            else 0.0
            for signal in signals
        }
        condition_sensitivity[str(minimum_conditions)] = asdict(
            simulate(
                f"minimum_conditions_{minimum_conditions}",
                condition_weights,
                target,
                benchmark,
                start_date,
                switch_cost,
            )
        )

    phase_counts = {
        phase.value: sum(signal.phase == phase.value for signal in signals)
        for phase in RiskPhase
    }
    return {
        "research_only": True,
        "target_code": args.target_code,
        "target_name": args.target_name,
        "generated_at_data_cutoff": end_date.isoformat(),
        "signal_start": signals[0].trading_date.isoformat(),
        "signal_end": signals[-1].trading_date.isoformat(),
        "weekly_signals": len(signals),
        "phase_counts": phase_counts,
        "switch_cost_bps": args.switch_cost_bps,
        "sources": {
            "target": target_source,
            "benchmark": benchmark_source,
            "breadth": {
                "database": args.database,
                "table": "MarketData",
                "universe": "all observed 688*/689* symbols, listing-span proxy",
                "dates": len(breadth),
            },
            "sectors": [
                {"code": code, "name": name, "table": "IndustryDailyData"}
                for code, name in SECTORS
            ],
        },
        "strategies": [asdict(result) for result in results],
        "cost_sensitivity": sensitivity,
        "condition_threshold_sensitivity": condition_sensitivity,
        "warning_quality": warning_quality(signals, target, benchmark),
        "signals": [
            {**asdict(signal), "trading_date": signal.trading_date.isoformat()}
            for signal in signals
        ],
        "limitations": [
            "Sohu index history is a third-party research source, not immutable provider authority.",
            "Breadth uses all observed STAR-board 688*/689* stocks, not historical 000690 constituents.",
            "Sector diffusion uses three Shenwan industry proxies.",
            f"{args.target_code} history begins at {target_source['first_date']}; the 271-observation warmup shortens the evaluation sample.",
            "Returns use index closes and assumed switch costs, not ETF tracking, fees, slippage, or executable fills.",
            "Rules were evaluated retrospectively and are not genuine prospective out-of-sample evidence.",
        ],
    }


def write_markdown(result: dict[str, object], path: Path) -> None:
    strategies = result["strategies"]
    quality = result["warning_quality"]
    lines = [
        f"# {result['target_name']}提前预警历史回测",
        "",
        "> Research-only；不构成投资建议或 decision-grade 证据。",
        "",
        f"- 数据截止：{result['generated_at_data_cutoff']}",
        f"- 信号区间：{result['signal_start']} 至 {result['signal_end']}",
        f"- 周度信号：{result['weekly_signals']} 个",
        f"- 状态计数：`{json.dumps(result['phase_counts'], ensure_ascii=False)}`",
        f"- 基准切换成本：{result['switch_cost_bps']} bps/满额切换",
        "",
        "## 策略结果",
        "",
        "| 策略 | CAGR | 波动率 | Sharpe | 最大回撤 | Calmar | 切换 | 科创暴露 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in strategies:
        lines.append(
            "| {name} | {cagr:.2%} | {annualized_volatility:.2%} | {sharpe} | "
            "{max_drawdown:.2%} | {calmar} | {switches} | {average_target_weight:.1%} |".format(
                name=item["name"],
                cagr=item["cagr"],
                annualized_volatility=item["annualized_volatility"],
                sharpe="—" if item["sharpe"] is None else f"{item['sharpe']:.2f}",
                max_drawdown=item["max_drawdown"],
                calmar="—" if item["calmar"] is None else f"{item['calmar']:.2f}",
                switches=item["switches"],
                average_target_weight=item["average_target_weight"],
            )
        )
    lines.extend(
        [
            "",
            "## 预警质量",
            "",
            f"- 标签：`{quality['label_definition']}`",
            f"- 标签基础发生率：{quality['positive_weeks']}/{quality['labelled_weeks']}（{_percent(quality['positive_rate'])}）",
            f"- WATCH 周精确率：{_percent(quality['watch_precision'])}",
            f"- WATCH 周召回率：{_percent(quality['watch_recall'])}",
            f"- 确认周精确率：{_percent(quality['confirmed_precision'])}",
            f"- 确认周召回率：{_percent(quality['confirmed_recall'])}",
            f"- WATCH 新预警命中：{quality['watch_entry_hits']}/{quality['watch_entries']}",
            f"- 新预警精确率：{_percent(quality['watch_entry_precision'])}",
            f"- 每年假预警：{_number(quality['false_watch_entries_per_year'])}",
            f"- 命中后达到 5% 相对超额的中位交易日：{_number(quality['median_trading_days_to_5pct_excess'])}",
            "",
            "## 条件数量敏感性",
            "",
            "| 最少满足条件 | CAGR | Sharpe | 最大回撤 | 切换 | 科创暴露 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for minimum, item in result["condition_threshold_sensitivity"].items():
        lines.append(
            f"| {minimum} | {item['cagr']:.2%} | {item['sharpe']:.2f} | "
            f"{item['max_drawdown']:.2%} | {item['switches']} | "
            f"{item['average_target_weight']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 年度收益",
            "",
        ]
    )
    for item in strategies:
        lines.append(
            f"- `{item['name']}`："
            + ", ".join(
                f"{year} {value:.2%}" for year, value in item["year_returns"].items()
            )
        )
    lines.extend(["", "## 限制", ""])
    lines.extend(f"- {value}" for value in result["limitations"])
    lines.extend(
        [
            "",
            "完整数值和逐周信号见同名 JSON。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _percent(value: Any) -> str:
    return "—" if value is None else f"{value:.1%}"


def _number(value: Any) -> str:
    return "—" if value is None else f"{value:.1f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        default="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb",
    )
    parser.add_argument("--end-date", default="2026-05-07")
    parser.add_argument("--target-code", default="000690")
    parser.add_argument("--target-name", default="科创成长")
    parser.add_argument("--cache-dir", default="/tmp/a-share-warning-data")
    parser.add_argument("--switch-cost-bps", type=int, default=20)
    parser.add_argument(
        "--output",
        default="overall/a-share-early-warning-backtest.json",
    )
    args = parser.parse_args()
    result = run(args)
    output = Path(args.output)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(result, output.with_suffix(".md"))
    print(output)


if __name__ == "__main__":
    main()
