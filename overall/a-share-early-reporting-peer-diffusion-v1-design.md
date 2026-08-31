# A-share early-reporting peer-diffusion study v1

**Status:** frozen before full outcome evaluation
**End date:** 2026-08-28
**Trading authorization:** false

## Frozen signal

For each SW2021 level-1 industry and quarterly report period, use only the first dated PIT announcement per stock. Compare reported revenue YoY and net-profit YoY with the immediately prior quarter. Emit at most one industry-period signal when:

- at least 3 reporters have both acceleration values;
- 10% through 35% of active non-ST mainland members have reported;
- at least 60% of valid reporters have positive revenue and profit acceleration.

Thresholds are frozen and are not tuned from returns.

## PIT universe and execution

SW membership is selected at the announcement date using `in_date <= date <= out_date` (or open-ended membership). Announcements after the decision date are unavailable. The decision is made after the announcement-day close and entry is at the next trading session open (T+1). Each completed trade exits at the 20th session close and deducts 31 bp round-trip cost.

Missing entry prices, insufficient 20-session history, non-finite prices, and non-positive entry opens produce no return rather than imputation.

## Separate arms

1. **Unreported peer stocks:** equal-weight the priced active industry members that have not yet reported.
2. **Direct industry ETF:** among listed direct-industry ETF candidates, select the ETF with the highest mean amount over up to 20 pre-entry sessions, requiring at least 10 observations.

## Evaluation

Report complete-event count, mean and median 20-session return, win rate, annual folds, and an explicit 2025 holdout for each arm. The frozen verdict is GO only when both arms have at least one complete 2025 event and positive mean 2025 return; otherwise NO-GO. `trade_authorized` remains false regardless of verdict.
