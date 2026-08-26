# Quality + B-Band full-market data infeasibility decision v1

- **Status:** `DATA_INFEASIBLE_UNDER_CURRENT_PUBLIC_AUTHORITY / STRATEGY_NOT_REJECTED / PLAN_ONLY`
- **Checked:** 2026-08-26
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`

## 1. Decision

Fold A/B Experiment and OOS Validation cannot be executed honestly under the currently approved public-source and Platform/Backtest authority.

This is not a strategy rejection. No formal Experiment, candidate selection, OOS Validation or strategy-return result exists. The stop is caused by missing full-market point-in-time source closure and unaccepted public execution authority, not by observed poor performance.

## 2. Evidence completed before stopping

The fixed issuer `xshe:000651` now has source-bounded, auditable research for:

- 2018–2023 official annual-report evidence;
- financial declarations, normalization and presentation selection candidates;
- reasoned 2021 debt ambiguity and invariant `ROIC >= 20%` pass;
- standard unqualified audits;
- source-bounded severe-issuer-penalty pass;
- no controlling shareholder, with largest-shareholder `100%` pledge advisory;
- major acquisition history;
- fixed-window valuation SourceSnapshot and invariant `<60%` PE-percentile pass;
- positive canonical FCF yield.

Backtest PRs #1–#11 and Platform PR #1 retain the implementation/planning evidence. None is merged or accepted.

A fixed-issuer pass is not a cross-sectional selection result and cannot substitute for a full-market peer set.

## 3. Irreducible current data blockers

### Historical Universe and industry

No accepted source provides one immutable, complete historical set of:

- listed and delisted ordinary A-share Instruments;
- board/product changes;
- CSRC industry membership revisions;
- listing-age inputs and corrections;
- status/risk-warning/suspension history;
- terminal completeness and explicit empty scopes.

Current lists, current `stock_basic`, bar presence and final constituents would introduce survivorship bias.

### Corporate actions

No accepted source closes the full historical action inventory, corrections and lifecycle terms for all potentially consumed Instruments. Public Tushare `dividend`/`adj_factor` responses are bounded observations without provider revision IDs, supersession or terminal completeness.

Without closure, point-in-time adjusted signal prices and held-position cash/share effects cannot be certified across the Folds.

### Financial, governance and valuation peer coverage

The fixed Gree lane does not supply full-market:

- coherent five-year financial statement revisions and units;
- audit opinions and correction/reissue lineage;
- competent severe-penalty/fraud no-event closure;
- point-in-time controller identity and pledge history;
- canonical market-value/annual-PE observations with revision coverage.

Search absence and provider zero-row responses cannot prove no event.

### Public execution authority

Even with data, execution is still blocked by:

- unaccepted Backtest PR stack #1–#11;
- no accepted full-market QB-DATA Bundle or coverage reports;
- provisional G12B capability/report names;
- no canonical constrained-domain ranking witness schema;
- no accepted T+1 selected-name gap/tradability/lot transport;
- no public multi-stock A-share PREP operation or qualified Profile.

## 4. Bounded capture boundary after staged-funnel approval

An unscoped heavy approved-proxy Tushare pull could preserve more returned bytes, but it cannot create the missing provider/source properties:

- historical-as-of identity;
- correction/supersession lineage;
- complete pagination/terminal declaration;
- competent no-event authority;
- corporate-action lifecycle closure.

It would therefore remain nonauthority input and would not unlock the required public Platform/Backtest flow.

The user-approved exception is one staged S0 lightweight catalog capture. It may preserve returned broad identity/listing/company bytes, test exact stage plumbing and estimate structural-funnel scope while keeping historical completeness, survivorship, revision closure and decision-grade flags false. S1–S4 acquisition must wait for exact prior-stage manifests; this exception does not change the no-economic-run decision.

## 5. Forbidden substitutes

Do not proceed by:

- using mutable DuckDB/Parquet/pickle as official evidence;
- projecting current/final constituents backward;
- accepting provider ROIC/PE/FCF ratios as canonical;
- treating missing rows as hard-filter failure or event absence;
- dropping hard-to-source issuers from ranking;
- writing a private simulator or custom profit-and-loss calculation and calling it Platform evidence;
- forcing an empty Universe, cash target or no-trade terminal from blocked data.

## 6. Exact unblocking paths

At least one competent data path must be approved:

1. a licensed feed/export with historical listed/delisted catalog, board, CSRC industry, status and corporate-action inventory; stable snapshot/publication identity; complete pagination/export declaration; corrections/revisions; and explicit terminal/empty-scope semantics; or
2. an official exchange/CNINFO data-service contract that supplies equivalent machine-verifiable closure; or
3. an explicit owner-approved contract pivot that lowers result grade and defines exactly which source-bounded incompleteness is acceptable without claiming survivorship safety or decision-grade evidence.

Then all of the following remain required:

- Backtest-owner approval of schemas/names and PRs #1–#11;
- deterministic full-market QB-DATA publication/reopen;
- interval-domain ranking proof artifacts;
- accepted T+1 execution feasibility semantics;
- public multi-stock PREP/Profile authority;
- precommitted Fold A/B Experiment and OOS Validation.

## 7. Final classification

```text
fixed-issuer quality/governance/valuation threshold assessment = source-bounded pass
cross-sectional top-four membership = unavailable
strategy performance hypothesis = untested
strategy rejection = no
formal support = no
current next executable economic run = none
stop reason = genuine data/authority infeasibility under current constraints
```

No economic Experiment/OOS run should resume until one unblocking data/authority path is concretely available. Non-economic PR review and data-source qualification/procurement may proceed. The approved S0 lightweight source-bounded plumbing capture is complete; further unscoped heavy capture or unofficial backtesting would not close the authority gap and would violate the precommit/evidence boundary if presented as official evidence.
