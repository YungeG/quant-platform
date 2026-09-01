import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from experiments import fetch_resource_cycle_history as fetcher


def test_retains_sc_roll_lineage_and_replays_without_network(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("secret")
    output = tmp_path / "raw"
    output.mkdir()
    pd.DataFrame([
        {
            "api": "fut_daily",
            "product": "SC",
            "start": "20240102",
            "end": "20240103",
            "status": "success",
            "rows": 1,
            "error": "",
        }
    ]).to_csv(output / "queries.csv", index=False)
    calls = []

    def fake_call(token, api, params):
        assert token == "secret"
        calls.append((api, params.copy()))
        code = params.get("ts_code")
        def result(rows):
            return rows, "", json.dumps({"data": rows}, ensure_ascii=False).encode()

        if api == "fut_mapping":
            return result([
                {"ts_code": "SCL.INE", "trade_date": "20240102", "mapping_ts_code": "SC2402.INE"},
                {"ts_code": "SCL.INE", "trade_date": "20240103", "mapping_ts_code": "SC2402.INE"},
            ])
        if api == "fut_daily" and code == "SCL.INE":
            return result([{"ts_code": code, "trade_date": "20240102", "settle": 550.0}])
        if api == "fut_daily" and code == "SC2402.INE":
            return result([
                {"ts_code": code, "trade_date": "20240102", "settle": 551.0},
                {"ts_code": code, "trade_date": "20240103", "settle": 552.0},
            ])
        if api == "fut_wsr":
            return result([
                {
                    "trade_date": "20240102",
                    "symbol": "SC",
                    "fut_name": "中质含硫原油",
                    "warehouse": "test",
                    "pre_vol": 10,
                    "vol": 11,
                    "vol_chg": 1,
                    "unit": "桶",
                }
            ])
        raise AssertionError((api, params))

    monkeypatch.setattr(fetcher, "call", fake_call)
    first = fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"])

    assert first["products"] == {"SC": "SCL.INE"}
    assert not first["failed_queries"]
    assert {api for api, _ in calls} == {"fut_daily", "fut_mapping", "fut_wsr"}
    warehouse_call = next(params for api, params in calls if api == "fut_wsr")
    assert warehouse_call["start_date"] == "20240102"
    assert warehouse_call["end_date"] == "20240103"

    mapping = pd.read_parquet(output / "fut_mapping.parquet")
    native = pd.read_parquet(output / "fut_native_daily.parquet")
    assert mapping[["ts_code", "trade_date", "mapping_ts_code"]].to_dict("records") == [
        {"ts_code": "SCL.INE", "trade_date": "20240102", "mapping_ts_code": "SC2402.INE"},
        {"ts_code": "SCL.INE", "trade_date": "20240103", "mapping_ts_code": "SC2402.INE"},
    ]
    assert native[["ts_code", "trade_date", "settle"]].to_dict("records") == [
        {"ts_code": "SC2402.INE", "trade_date": "20240102", "settle": 551.0},
        {"ts_code": "SC2402.INE", "trade_date": "20240103", "settle": 552.0},
    ]
    for name in ["fut_daily", "fut_wsr", "fut_mapping", "fut_native_daily"]:
        path = output / f"{name}.parquet"
        assert first["outputs"][name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    query_rows = pd.read_csv(output / "queries.csv")
    assert set(query_rows.api) == {"fut_daily", "fut_daily_native", "fut_mapping", "fut_wsr"}
    assert query_rows.raw_path.map(lambda value: (output / value).exists()).all()
    assert query_rows.apply(
        lambda row: hashlib.sha256((output / row.raw_path).read_bytes()).hexdigest() == row.response_sha256,
        axis=1,
    ).all()
    assert first["raw_responses"]["files"] == 4
    assert first["query_ledger"]["sha256"] == hashlib.sha256((output / "queries.csv").read_bytes()).hexdigest()
    call_count = len(calls)
    second = fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"])
    assert len(calls) == call_count
    assert second["outputs"] == first["outputs"]
    assert second["raw_responses"] == first["raw_responses"]

    tampered = output / query_rows.iloc[0].raw_path
    tampered.write_text("tampered")
    third = fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"])
    assert len(calls) == call_count + 1
    assert third["raw_responses"] == first["raw_responses"]

    with pytest.raises(ValueError, match="output directory scope mismatch"):
        fetcher.run("2024-01-02", "2024-01-04", str(token_file), str(output), ["SC"])


def test_rejects_missing_native_mapping_coverage(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("secret")

    def fake_call(_token, api, params):
        code = params.get("ts_code")
        if api == "fut_mapping":
            rows = [
                {"ts_code": "SCL.INE", "trade_date": "20240102", "mapping_ts_code": "SC2402.INE"},
                {"ts_code": "SCL.INE", "trade_date": "20240103", "mapping_ts_code": "SC2402.INE"},
            ]
        elif api == "fut_daily" and code == "SCL.INE":
            rows = [{"ts_code": code, "trade_date": "20240102", "settle": 550.0}]
        elif api == "fut_daily" and code == "SC2402.INE":
            rows = [{"ts_code": code, "trade_date": "20240102", "settle": 551.0}]
        elif api == "fut_wsr":
            rows = []
        else:
            raise AssertionError((api, params))
        return rows, "", json.dumps({"data": rows}).encode()

    monkeypatch.setattr(fetcher, "call", fake_call)
    with pytest.raises(RuntimeError, match="mapping/native exact-cover failure"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(tmp_path / "raw"), ["SC"])
