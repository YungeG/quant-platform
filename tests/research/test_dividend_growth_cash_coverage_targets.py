import pandas as pd

from experiments.build_dividend_growth_cash_coverage_targets import practical_universe


def test_practical_universe_rejects_st_and_keeps_top_liquid_large_names():
    frame = pd.DataFrame({
        "Symbol": [f"{number:06d}" for number in range(1, 5)],
        "is_st": [False, True, False, False],
        "suspended": [False, False, False, False],
        "age": [300, 300, 300, 300],
        "Close": [10.0, 10.0, 10.0, 4.0],
        "Volume": [100.0, 100.0, 100.0, 100.0],
        "CircMV": [400.0, 300.0, 200.0, 100.0],
        "adv20": [400.0, 300.0, 200.0, 100.0],
    })

    selected = practical_universe(frame)

    assert selected.Symbol.tolist() == ["000001"]
