import pandas as pd

from experiments.run_quarterly_sue import quarterly_sue


def test_quarterly_sue_derives_q2_from_cumulative_and_uses_only_prior_history():
    rows = []
    for year in range(2015, 2024):
        value = (year - 2010) ** 2
        for quarter, end_date, ann_date, cumulative in ((1, f"{year}0331", f"{year}0415", value), (2, f"{year}0630", f"{year}0715", 3 * value), (3, f"{year}0930", f"{year}1015", 6 * value), (4, f"{year}1231", f"{year + 1}0315", 10 * value)):
            rows.append({"ts_code": "000001.SZ", "ann_date": ann_date, "end_date": end_date, "n_income_attr_p": cumulative, "update_flag": 0})
    result = quarterly_sue(pd.DataFrame(rows))
    q2 = result[result.end_date == pd.Timestamp("2023-06-30")].iloc[0]
    assert q2.single_profit == 2 * (2023 - 2010) ** 2
    assert q2.prior_count == 8
    assert q2.ann_date == pd.Timestamp("2023-07-15")
