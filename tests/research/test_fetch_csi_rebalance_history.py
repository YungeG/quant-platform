from experiments.fetch_csi_rebalance_history import _effective_dates, _search


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

    def post(self, url, json, timeout):
        page = json["page"]["page"]
        self.pages.append((url, json, timeout))
        size = 100 if page == 1 else 1
        data = [{"id": (page - 1) * 100 + number} for number in range(size)]
        return _Response({"code": "200", "msg": "Success", "data": data, "total": 101})


def test_search_paginates_official_rebalance_filter():
    session = _Session()

    rows = _search(session, "沪深300")

    assert len(rows) == 101
    assert [call[1]["page"]["page"] for call in session.pages] == [1, 2]
    assert session.pages[0][1]["relatedTopics"] == ["index_rebalance"]
    assert session.pages[0][1]["typeList"] == ["announcement"]


def test_effective_dates_use_publish_year_when_notice_omits_year():
    content = "决定调整指数样本，于2024年12月13日收市后生效；另一项自9月1日起调整。"

    assert _effective_dates(content, "2026-08-31") == ["2024-12-13", "2026-09-01"]
