# QB-VAL-SRC-01 — Gree fixed-window valuation source sentinel v1

- **Status:** `IMPLEMENTED / PR_9_OPEN / CANDIDATE_02_INDEPENDENTLY_ACCEPTED / SOURCE_BOUNDED`
- **Owner:** Backtest Market Bundle Builder acquisition tooling
- **Issuer:** `000651.SZ` / `xshe:000651`
- **Purpose:** retain the fixed five-year market-value inputs needed to assess the 2024-05-06 valuation gate without trusting a mutable provider ratio as canonical

## 1. Scope

One additive Backtest acquisition sentinel may query the approved xiaodefa Tushare proxy exactly once:

```text
api_name = daily_basic
ts_code = 000651.SZ
start_date = 20190506
end_date = 20240506
fields = ts_code,trade_date,close,pe,pe_ttm,total_share,total_mv,circ_mv
```

The fixed interval contains the five-year lookback ending on the first SZSE session at which the retained 2023 annual report is conservatively available.

The sentinel is not a generic valuation provider, daily-bar provider, corporate-action authority, feature calculator, Universe selector or Strategy operation.

## 2. Exact three-file write set

Implementation may change only:

1. `tools/acquisition/cn_a_share_tushare_gree_valuation_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_tushare_gree_valuation_source_bounded_v1.py`
3. `tests/architecture/test_g12a_gree_valuation_source_bounded_v1_boundary.py`

All predecessor bytes are protected.

## 3. Output

Successful acquisition creates one previously absent directory containing:

```text
response/tushare/daily_basic/000651.SZ-20190506-20240506-v1.json
source-snapshot.json
acquisition-receipt.json
```

Files are write-once, mode `0600`; the directory is created atomically enough that a failure leaves no partial final output. Existing output fails closed.

The `SourceSnapshot` must freeze the raw response bytes and exact acquisition timestamps. The receipt records request facts, member hash/size, observed envelope, cardinality, limitations and snapshot identity. It must not contain the token.

## 4. Validation

The provider response must satisfy all of the following:

- HTTP 200 and provider `code = 0`;
- exact requested field order;
- `has_more = false`, provider `count = 0`;
- exactly `1,213` rows;
- every row has exactly eight cells;
- every `ts_code` is `000651.SZ`;
- every `trade_date` is a real date within `20190506..20240506`;
- dates are unique and the set includes exact endpoints `20190506` and `20240506`;
- `close`, `total_share`, `total_mv` and `circ_mv` are finite positive JSON numbers, never quoted numerics;
- `pe` and `pe_ttm` are either finite JSON numbers or null;
- no pagination, redirect, field mismatch, malformed envelope, credential-shaped text or duplicate JSON keys.

Row order is provider evidence and is retained unchanged. The sentinel must not sort or rewrite source rows.

## 5. Transport and credential boundary

- Only the approved endpoints already admitted by the xiaodefa proxy helper are allowed.
- Authentication is the exact `x-api-key` header.
- `TUSHARE_PROXY_TOKEN` is supplied only through the environment.
- Exceptions, receipts, stdout and artifacts must not expose the token.
- Retries reuse the existing bounded proxy helper; no alternate direct Tushare route is allowed.

## 6. Permitted downstream research

The retained canonical numerator candidate is:

```text
total_market_value_cny = total_mv * 10,000
```

`total_mv` is a provider market-value observation whose interface unit is `10,000 CNY`. The raw `pe` and `pe_ttm` fields are advisory interpretations only because their formula version and denominator lineage are absent.

A separate research assessment may compare:

1. provider `pe_ttm`; and
2. self-recomputed annual PE using retained `total_mv` and the latest annual attributable profit whose conservative availability boundary is not later than the trading date.

If both supported interpretations produce the same below/above-60th-percentile decision, the fixed-issuer valuation decision is `EXPLAINED_DECISION_INVARIANT`. Otherwise it is `UNRESOLVED_DECISION_MATERIAL`.

## 7. Nonclaims

The emitted candidate remains:

```text
source_bounded = true
revision_closure_complete = false
decision_grade_eligible = false
deployment_authorized = false
provider_revision_id = null
```

It does not prove:

- historical provider revision closure;
- exact first availability of any daily row;
- share-count or corporate-action lineage;
- an accepted `valuation_observation_revision@1`;
- full-market or fold coverage;
- a Strategy qualification, Backtest result, Promotion, Live or trading authority.

## 8. Implementation evidence

- Backtest commit: `5b99e50826a526cfd81ea8a28d2a1d1bf3daf52c`
- PR: <https://github.com/YungeG/quant-backtest/pull/9>
- Focused validation: `22 passed`
- Builder/acquisition validation: `552 passed, 5 skipped`
- Broad non-architecture validation: `2365 passed, 5 skipped`; three unrelated cross-repository fixture-path tests failed because `/home/ygguo/agent-projs/ai-crypt/tests/contracts/backtest-consumer-port-v1.json` is absent
- Independent review: accepted `v1-candidate-02`
- Valid SourceSnapshot: `sha256:97120ac129e6bb8fb63b2dfdbb141e6501d281d01011fb1120bb1d29c8228c30`
- Invalid retained predecessor: `v1-candidate-01`, because it recorded invocation time before response receipt

## 9. Acceptance

Minimum evidence:

- focused tests pass;
- architecture boundary passes;
- builder-wide tests pass;
- credential redaction and failure atomicity are covered;
- a real opt-in capture publishes exactly one immutable candidate;
- independent review reproduces the raw member and snapshot hashes;
- predecessor-byte check is clean.
