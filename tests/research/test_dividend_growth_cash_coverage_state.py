import pandas as pd

from experiments.build_dividend_growth_cash_coverage_state import evaluate


def test_evaluate_requires_strict_growth_and_each_year_cash_coverage():
    groups = pd.DataFrame([
        {"security_code": "000001", "fiscal_year": 2022, "cash_per_share": 0.10, "cash_payout": 10.0},
        {"security_code": "000001", "fiscal_year": 2023, "cash_per_share": 0.20, "cash_payout": 20.0},
        {"security_code": "000001", "fiscal_year": 2024, "cash_per_share": 0.30, "cash_payout": 30.0},
        {"security_code": "000002", "fiscal_year": 2022, "cash_per_share": 0.10, "cash_payout": 10.0},
        {"security_code": "000002", "fiscal_year": 2023, "cash_per_share": 0.10, "cash_payout": 10.0},
        {"security_code": "000002", "fiscal_year": 2024, "cash_per_share": 0.20, "cash_payout": 20.0},
    ])
    cashflow = pd.DataFrame([
        {"security_code": code, "fiscal_year": year, "n_cashflow_act": payout * 1.5}
        for code, year, payout in (
            ("000001", 2022, 10.0), ("000001", 2023, 20.0), ("000001", 2024, 30.0),
            ("000002", 2022, 10.0), ("000002", 2023, 10.0), ("000002", 2024, 20.0),
        )
    ])

    state = evaluate(groups, cashflow).set_index("security_code")

    assert bool(state.loc["000001", "eligible"])
    assert not bool(state.loc["000002", "strict_dividend_growth"])
    assert not bool(state.loc["000002", "eligible"])
