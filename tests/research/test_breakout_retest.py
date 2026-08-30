from experiments.breakout_retest import RetestBar, evaluate_retest


def bar(high, low, close, previous, amount=50, atr5=2, one_word=False):
    return RetestBar(high, low, close, previous, amount, atr5, one_word)


def test_support_break_has_highest_priority():
    outcome = evaluate_retest(
        [bar(101, 96, 97, 101, amount=40)],
        breakout_level=100,
        breakout_atr=2,
        breakout_amount=100,
    )
    assert outcome.terminal_reason == "support_break"


def test_distribution_selloff_is_recorded():
    outcome = evaluate_retest(
        [bar(103, 99, 100, 102, amount=120)],
        breakout_level=100,
        breakout_atr=2,
        breakout_amount=100,
    )
    assert outcome.terminal_reason == "distribution_selloff"


def test_missing_retest_times_out():
    bars = [bar(106, 104, 105, 105, amount=40) for _ in range(12)]
    outcome = evaluate_retest(
        bars, breakout_level=100, breakout_atr=2, breakout_amount=100
    )
    assert outcome.terminal_reason == "no_retest_timeout"


def test_retest_requires_contracting_amount_and_volatility():
    high_amount = [bar(105, 103, 104, 104, amount=90) for _ in range(2)] + [
        bar(103, 101, 102, 104, amount=90)
    ]
    assert evaluate_retest(
        high_amount, breakout_level=100, breakout_atr=2, breakout_amount=100
    ).terminal_reason == "retest_volume_not_contracted"

    high_vol = [bar(105, 103, 104, 104, amount=40) for _ in range(2)] + [
        bar(103, 101, 102, 104, amount=40, atr5=2.3)
    ]
    assert evaluate_retest(
        high_vol, breakout_level=100, breakout_atr=2, breakout_amount=100
    ).terminal_reason == "retest_volatility_expanded"


def test_retest_then_recovery_triggers():
    bars = [
        bar(105, 103, 104, 104, amount=40),
        bar(104, 102, 103, 104, amount=40),
        bar(103, 101, 101.5, 103, amount=40),
        bar(107, 101, 106, 101.5, amount=90),
    ]
    outcome = evaluate_retest(
        bars, breakout_level=100, breakout_atr=2, breakout_amount=100
    )
    assert outcome.terminal_reason == "triggered"
    assert outcome.retest_index == 3
    assert outcome.trigger_index == 4


def test_valid_retest_without_recovery_times_out():
    bars = [
        bar(105, 103, 104, 104, amount=40),
        bar(104, 102, 103, 104, amount=40),
        bar(103, 101, 101.5, 103, amount=40),
    ] + [bar(102, 100, 101, 101, amount=40) for _ in range(9)]
    outcome = evaluate_retest(
        bars, breakout_level=100, breakout_atr=2, breakout_amount=100
    )
    assert outcome.terminal_reason == "no_recovery_timeout"
