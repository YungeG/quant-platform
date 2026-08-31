from experiments.fetch_cninfo_dividend_lifecycle import _query, _title
from experiments.parse_cninfo_dividend_lifecycle import parse_text


class _Response:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class _Session:
    def __init__(self):
        self.pages = []

    def post(self, url, data, timeout):
        page = data["pageNum"]
        self.pages.append((url, data, timeout))
        count = 30 if page == 1 else 1
        return _Response({"totalAnnouncement": 31, "announcements": [{"page": page}] * count})


def test_cninfo_query_paginates_and_strips_highlight_markup():
    session = _Session()

    rows = _query(session, "2025-01-01", "2025-01-31")

    assert len(rows) == 31
    assert [call[1]["pageNum"] for call in session.pages] == [1, 2]
    assert session.pages[0][1]["searchkey"] == "权益分派实施公告"
    assert _title("2024年度<em>权益</em><em>分派</em><em>实施</em><em>公告</em>") == "2024年度权益分派实施公告"


def test_parse_shanghai_table_lifecycle_and_per_share_cash():
    text = """
A 股每股现金红利 0.15 元
股份类别 股权登记日 最后交易日 除权（息）日 现金红利发放日
普通股 2025/2/10 － 2025/2/11 2025/2/11
"""

    assert parse_text(text) == {
        "record_date": "2025-02-10",
        "ex_date": "2025-02-11",
        "payment_date": "2025-02-11",
        "cash_per_share": 0.15,
        "status": "COMPLETE",
    }


def test_font_mapped_year_glyphs_are_normalized_to_month_and_day():
    text = "股权登记日为：2025年6年3年；除权除息日为：2025年6年4年。现金红利将于2025年6年4年发放。每10股派1.50元。"

    parsed = parse_text(text)

    assert (parsed["record_date"], parsed["ex_date"], parsed["payment_date"]) == ("2025-06-03", "2025-06-04", "2025-06-04")


def test_parse_four_date_table_uses_final_date_for_cash_payment():
    text = """
每股现金红利0.70元
股权登记日 除权（息）日 新增无限售条件流通股份上市日 现金红利发放日
2025/4/24 2025/4/25 2025/4/25 2025/4/25
"""

    parsed = parse_text(text)

    assert (parsed["record_date"], parsed["ex_date"], parsed["payment_date"]) == ("2025-04-24", "2025-04-25", "2025-04-25")


def test_non_cash_stock_dividend_is_excluded_from_cash_lifecycle():
    text = "公司每10股派发现金股利0元，以资本公积每股转增0.2股，共计转增股份。"

    assert parse_text(text)["status"] == "NO_CASH_DIVIDEND"


def test_cash_dividend_uses_first_pre_tax_cash_stock_amount():
    text = "向全体股东每10股派发现金股利3.00元人民币（含税），扣税后每10股派2.70元。"

    assert parse_text(text)["cash_per_share"] == 0.3


def test_parse_shenzhen_sentence_lifecycle_and_per_ten_cash():
    text = """
公司向全体股东每 10 股派 0.400000 元人民币现金。
本次权益分派股权登记日为：2025 年 2 月 7 日，除权除息日为：2025 年 2 月 10 日。
本公司现金红利将于 2025\n3\n年 2 月 10 日发放。
"""

    assert parse_text(text) == {
        "record_date": "2025-02-07",
        "ex_date": "2025-02-10",
        "payment_date": "2025-02-10",
        "cash_per_share": 0.04,
        "status": "COMPLETE",
    }
