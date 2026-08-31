import csv
import json
from pathlib import Path

from experiments.audit_dividend_cashflow_coverage import fiscal_year, is_annual, run


def test_title_classification():
    assert fiscal_year("2024年年度权益分派实施公告") == 2024
    assert is_annual("2024年年度权益分派实施公告")
    assert not is_annual("2024年半年度权益分派实施公告")


def test_cashflow_coverage_uses_latest_revision_available_at_publication(tmp_path: Path):
    dividends = tmp_path / "dividends.csv"
    with dividends.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["announcement_id", "security_code", "publish_date", "fiscal_year", "fiscal_period_type", "title", "status"])
        writer.writeheader()
        writer.writerow({"announcement_id": "a", "security_code": "000001", "publish_date": "2025-05-01", "fiscal_year": "2024", "fiscal_period_type": "ANNUAL", "title": "错误元数据", "status": "COMPLETE"})
        writer.writerow({"announcement_id": "b", "security_code": "000001", "publish_date": "2025-08-01", "fiscal_year": "2025", "fiscal_period_type": "INTERIM", "title": "错误元数据", "status": "COMPLETE"})
    cashflow = tmp_path / "cashflow.csv"
    with cashflow.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ts_code", "ann_date", "end_date", "n_cashflow_act", "update_flag"])
        writer.writeheader()
        writer.writerow({"ts_code": "000001.SZ", "ann_date": "20250420", "end_date": "20241231", "n_cashflow_act": "100", "update_flag": "0"})
        writer.writerow({"ts_code": "000001.SZ", "ann_date": "20250520", "end_date": "20241231", "n_cashflow_act": "200", "update_flag": "1"})
    out_json, out_md = tmp_path / "out.json", tmp_path / "out.md"

    result = run(str(dividends), str(cashflow), str(out_json), str(out_md))

    assert result["annual_dividend_rows_by_title"] == 1
    assert result["annual_rows_with_pit_cashflow"] == 1
    assert result["coverage_rate"] == 1.0
    assert json.loads(out_json.read_text())["trade_authorized"] is False
