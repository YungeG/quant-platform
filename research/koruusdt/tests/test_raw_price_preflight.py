from __future__ import annotations

import csv
import io
import zipfile
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).parents[1] / "data"


def _is_tick_aligned(value: str) -> bool:
    return (Decimal(value) * 100) % 1 == 0


def _column_values(path: Path, column: str) -> tuple[str, ...]:
    with path.open(newline="") as source:
        return tuple(row[column] for row in csv.DictReader(source) if row[column])


def _aggregate_trade_price_sample(limit: int = 10_000) -> tuple[str, ...]:
    prices: list[str] = []
    archives = sorted(
        (DATA / "binance_usdm" / "aggTrades" / "daily").glob("*.zip")
    )[:3]
    for archive in archives:
        with zipfile.ZipFile(archive) as bundle:
            with bundle.open(bundle.namelist()[0]) as member:
                for row in csv.DictReader(io.TextIOWrapper(member, newline="")):
                    prices.append(row["price"])
                    if len(prices) >= limit:
                        return tuple(prices)
    return tuple(prices)


def test_retained_raw_price_preflight_covers_every_planned_precision_path() -> None:
    mark = DATA / "binance_mark_raw.csv"
    index = DATA / "binance_index_raw.csv"
    funding = DATA / "binance_funding_raw.csv"

    assert any(not _is_tick_aligned(value) for value in _column_values(mark, "close"))
    assert any(not _is_tick_aligned(value) for value in _column_values(mark, "low"))
    assert any(not _is_tick_aligned(value) for value in _column_values(mark, "high"))
    assert any(not _is_tick_aligned(value) for value in _column_values(index, "close"))
    assert any(
        not _is_tick_aligned(value) for value in _column_values(funding, "mark_price")
    )

    execution_prices = _aggregate_trade_price_sample()
    assert len(execution_prices) == 10_000
    assert all(_is_tick_aligned(value) for value in execution_prices)
