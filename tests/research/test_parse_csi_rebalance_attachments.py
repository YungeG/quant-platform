from pathlib import Path

from openpyxl import Workbook

from experiments.parse_csi_rebalance_attachments import parse_pdf_text, parse_xlsx


def test_pdf_text_parser_tracks_index_sections_and_both_directions():
    text = """
沪深 300 指数样本调整名单：
  证券代码 证券名称 证券代码 证券名称
  000001 平安银行 600000 浦发银行
中证 500 指数样本调整名单：
  000002 万科 A 600001 邯郸钢铁
中证 A100 指数样本调整名单：
  000002 不应重复 600001 不应重复
"""

    rows = parse_pdf_text(text)

    assert rows == [
        {"index_name": "沪深300", "index_code": "000300", "direction": "OUT", "security_code": "000001", "security_name": "平安银行"},
        {"index_name": "沪深300", "index_code": "000300", "direction": "IN", "security_code": "600000", "security_name": "浦发银行"},
        {"index_name": "中证500", "index_code": "000905", "direction": "OUT", "security_code": "000002", "security_name": "万科 A"},
        {"index_name": "中证500", "index_code": "000905", "direction": "IN", "security_code": "600001", "security_name": "邯郸钢铁"},
    ]


def test_xlsx_parser_reads_official_in_out_sheet_shape(tmp_path: Path):
    path = tmp_path / "changes.xlsx"
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, security_code in (("调入", 300001), ("调出", 2)):
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(["指数代码", "指数简称", "证券代码", "证券简称"])
        sheet.append([852, "中证1000", security_code, "测试证券"])
    workbook.save(path)

    rows = parse_xlsx(path)

    assert rows == [
        {"index_name": "中证1000", "index_code": "000852", "direction": "OUT", "security_code": "000002", "security_name": "测试证券"},
        {"index_name": "中证1000", "index_code": "000852", "direction": "IN", "security_code": "300001", "security_name": "测试证券"},
    ]
