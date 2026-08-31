from pathlib import Path


def test_hs_index_rebalance_audit_blocks_unqualified_backtest() -> None:
    audit = Path("research/hs-index-rebalance-forced-flow-source-audit-v1.md").read_text()
    assert "SOURCE-BLOCKED / NO_BACKTEST_RUN" in audit
    assert "announcement availability" in audit
    assert "current constituents" in audit
    assert "000300" in audit and "000905" in audit and "000852" in audit
