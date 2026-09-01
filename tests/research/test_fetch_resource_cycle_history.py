import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from experiments import fetch_resource_cycle_history as fetcher


def write_attestation(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps({
        "data_slice": {
            "start_inclusive": manifest["start"],
            "provider_end_inclusive": manifest["end"],
        },
        "products": manifest["products"],
        "outputs": manifest["outputs"],
        "capture": {
            "query_ledger": manifest["query_ledger"],
            "raw_responses": manifest["raw_responses"],
        },
    }))


def test_retains_sc_roll_lineage_and_replays_without_network(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("secret")
    output = tmp_path / "raw"
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
    attestation = tmp_path / "attestation.json"
    write_attestation(attestation, first)
    with pytest.raises(ValueError, match="requires a tracked attestation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"])
    second = fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    assert len(calls) == call_count
    assert second["outputs"] == first["outputs"]
    assert second["raw_responses"] == first["raw_responses"]

    raw_path = output / query_rows.iloc[0].raw_path
    raw_bytes = raw_path.read_bytes()
    raw_path.write_text("tampered")
    with pytest.raises(ValueError, match="raw responses failed integrity validation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    raw_path.write_bytes(raw_bytes)

    ledger_path = output / "queries.csv"
    ledger_bytes = ledger_path.read_bytes()
    ledger_path.write_bytes(ledger_bytes + b"\n")
    with pytest.raises(ValueError, match="query ledger failed integrity validation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    ledger_path.write_bytes(ledger_bytes)

    parquet_path = output / "fut_daily.parquet"
    parquet_bytes = parquet_path.read_bytes()
    parquet_path.write_bytes(parquet_bytes + b"tampered")
    with pytest.raises(ValueError, match="output failed integrity validation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    parquet_path.write_bytes(parquet_bytes)

    manifest_path = output / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_path.unlink()
    with pytest.raises(ValueError, match="capture artifacts require a manifest"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"])
    manifest_path.write_bytes(manifest_bytes)

    incomplete_manifest = json.loads(manifest_bytes)
    incomplete_manifest.pop("raw_responses")
    manifest_path.write_text(json.dumps(incomplete_manifest))
    with pytest.raises(ValueError, match="manifest lacks required integrity sections"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    manifest_path.write_bytes(manifest_bytes)

    missing_output = json.loads(manifest_bytes)
    missing_output["outputs"].pop("fut_wsr")
    manifest_path.write_text(json.dumps(missing_output))
    with pytest.raises(ValueError, match="exact expected output entries"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    manifest_path.write_bytes(manifest_bytes)

    orphan_raw = output / "raw" / "orphan.bin"
    orphan_raw.write_bytes(b"orphan")
    with pytest.raises(ValueError, match="raw responses failed integrity validation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    orphan_raw.unlink()

    orphan_parquet = output / "nested" / "orphan.parquet"
    orphan_parquet.parent.mkdir()
    pd.DataFrame([{"value": 1}]).to_parquet(orphan_parquet)
    with pytest.raises(ValueError, match="Parquet inventory does not match"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    orphan_parquet.unlink()

    raw_path.write_text("coordinated tamper")
    coordinated_queries = pd.read_csv(ledger_path, dtype=str)
    coordinated_queries.loc[coordinated_queries.raw_path.eq(str(raw_path.relative_to(output))), "response_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    coordinated_queries.to_csv(ledger_path, index=False)
    coordinated_manifest = json.loads(manifest_bytes)
    coordinated_manifest["query_ledger"]["sha256"] = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    count, digest = fetcher._raw_receipt_digest(output)
    coordinated_manifest["raw_responses"].update({"files": count, "sha256": digest})
    manifest_path.write_text(json.dumps(coordinated_manifest))
    with pytest.raises(ValueError, match="tracked attestation"):
        fetcher.run("2024-01-02", "2024-01-03", str(token_file), str(output), ["SC"], str(attestation))
    raw_path.write_bytes(raw_bytes)
    ledger_path.write_bytes(ledger_bytes)
    manifest_path.write_bytes(manifest_bytes)
    assert len(calls) == call_count

    with pytest.raises(ValueError, match="output directory scope mismatch"):
        fetcher.run("2024-01-02", "2024-01-04", str(token_file), str(output), ["SC"], str(attestation))


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


def test_rejects_conflicting_source_rows(tmp_path: Path):
    path = tmp_path / "daily.parquet"
    fetcher.append(path, [{"ts_code": "SC2402.INE", "trade_date": "20240102", "settle": 551.0}], ["ts_code", "trade_date"])
    with pytest.raises(ValueError, match="conflicting duplicate source rows"):
        fetcher.append(path, [{"ts_code": "SC2402.INE", "trade_date": "20240102", "settle": 552.0}], ["ts_code", "trade_date"])


def test_pg_uses_dce_continuous_lineage():
    assert fetcher._selected_products(["pg", "PP"]) == {"PG": "PGL.DCE", "PP": "PPL.DCE"}
    assert {"PG", "PP"}.issubset(fetcher.LINEAGE_PRODUCTS)


def test_chunk_boundaries_are_exact_and_inverted_ranges_fail():
    assert fetcher.year_chunks("2022-12-31", "2025-01-01") == [
        ("20221231", "20231231"),
        ("20240101", "20250101"),
    ]
    assert fetcher.month_chunks("2024-02-28", "2024-03-01") == [
        ("20240228", "20240229"),
        ("20240301", "20240301"),
    ]
    with pytest.raises(ValueError, match="start must not exceed end"):
        fetcher.year_chunks("2024-01-02", "2024-01-01")
    with pytest.raises(ValueError, match="start must not exceed end"):
        fetcher.month_chunks("2024-01-02", "2024-01-01")
