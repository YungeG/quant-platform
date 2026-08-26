# QB-ELIG-01 — Quality + B-Band missing-data eligibility policy v1

- **Status:** `CONTRACT_FROZEN / INDEPENDENT_REVIEW_CORRECTIONS_APPLIED / PLAN_ONLY / GENERAL_MARKET_AUTHORITY_MISSING`
- **Scope:** downstream quality qualification, holding continuation and new-entry eligibility after successful QB-DATA Bundle construction
- **Consumer:** future quality, continuation, entry and ranking manifests

## 1. Outcome

Missing evidence is never converted to zero, a low score, an automatic threshold failure or a silently removed stock.

QB-DATA coverage remains unconditional: a successful Bundle must exact-cover the independently constructed point-in-time Universe and all declared financial, governance, valuation, industry, status, price and corporate-action capabilities. Downstream short-circuiting may avoid unnecessary Strategy feature calculation; it may not waive source acquisition, coverage reporting or Bundle exact-cover.

Quality qualification, existing-holding continuation and new-entry signal selection are separate decisions. A stock is never bought merely because it is high quality, and a retained holding is never sold merely because it has no fresh breakout, has become expensive or ranks below a new candidate.

## 2. Independent Universe first

Universe membership is established before inspecting financial, governance or valuation availability.

The Universe authority must independently exact-bind:

- full Instrument catalog identity;
- point-in-time listing/delisting membership;
- ordinary沪深主板 product/board classification;
- point-in-time industry membership sufficient to exclude financial issuers;
- listing-age facts;
- applicable status/risk-warning coverage.

Industry history is a distinct future Bundle capability:

```text
industry_membership_revision@1
IndustryMembershipCoverageReportV1
```

The portfolio authority must exact-bind that report alongside Universe coverage. QB-UNIV-CA-01 must freeze its schema before implementation.

A provider-covered financial subset, bar-presence subset, current constituent list, current industry classification or current controller field must never define historical Universe membership.

## 3. Two separate failure layers

### Layer A — QB-DATA Bundle construction

Existing [`quality-bband-data-contract-v1.md`](quality-bband-data-contract-v1.md) remains unchanged. Missing/foreign/conflicting source, revision, coverage or publication authority returns its existing atomic QB-DATA failure. No Bundle and no Strategy manifest is emitted.

The Bundle layer may carry explicit source-bounded candidate intervals or N.A. declarations when their schemas and source coverage are mechanically complete. It may not silently fabricate an exact point.

### Layer B — Strategy decisions

Only after Bundle success may Strategy perform:

1. quality qualification for the independently defined Universe;
2. continuation/exit assessment for existing holdings;
3. new-entry filter, signal and ranking for available slots.

Downstream short-circuiting does not weaken Layer A.

## 4. Quality qualification

Quality stages are:

1. structural scope: ordinary沪深主板, non-financial, listed at least five years;
2. five-year financial-quality hard filters;
3. audit, severe-penalty/fraud and controlling-shareholder-pledge hard filters.

A complete decision-invariant failure at an earlier quality stage ends later quality feature calculation for that issuer. Required Bundle coverage has already been established and is not skipped.

Every Universe member receives exactly one quality disposition:

| Quality disposition | Meaning |
| --- | --- |
| `STRUCTURALLY_OUT_OF_SCOPE` | complete point-in-time facts prove board, industry or listing-age exclusion |
| `QUALITY_HARD_FILTER_FAILED` | exact evidence or a wholly failing interval proves one frozen quality threshold fails |
| `QUALITY_QUALIFIED_POINT` | all quality hard filters pass with point-valued rank features |
| `QUALITY_QUALIFIED_INTERVAL` | all interpretations pass, but one or more rank features remain intervals |
| `UNRESOLVED_DECISION_MATERIAL` | evidence-supported interpretations change quality qualification |

Applicability such as `NO_CONTROLLING_SHAREHOLDER` is a predicate result inside a quality disposition, not a terminal disposition itself.

Mechanical quality closure requires:

```text
Universe members
= structurally out of scope
+ quality hard-filter failed
+ quality qualified point
+ quality qualified interval
+ unresolved decision material
```

## 5. Existing-holding continuation and exit

Existing holdings are assessed before new-entry ranking.

Each holding receives exactly one continuation disposition:

| Continuation disposition | Meaning |
| --- | --- |
| `CONTINUE_HOLDING` | no frozen exit condition is satisfied |
| `EXIT_REQUIRED` | complete evidence satisfies a frozen exit condition |
| `UNRESOLVED_DECISION_MATERIAL` | evidence-supported interpretations change exit/continue |

Fresh B-Band signal, current valuation percentile and cross-sectional rank are not continuation requirements. `CONTINUE_HOLDING` reserves one of the four slots.

An exit may be emitted only through the separately frozen next-eligible-execution semantics. A blocked continuation decision emits no replacement target, no empty target and no fabricated liquidation instruction.

## 6. New-entry eligibility

Only non-held quality-qualified issuers may enter new-entry evaluation. Available slots are:

```text
available_slots = 4 - count(CONTINUE_HOLDING)
```

If `available_slots = 0`, no new-entry ranking is required.

New-entry stages are:

1. positive FCF yield and five-year valuation-percentile rule;
2. liquidity coverage and threshold;
3. complete T-close BOLL contraction/trend/volume-breakout signal;
4. frozen gap/tradability/lot-capital feasibility semantics;
5. interval-aware ranking for the available slots.

Each quality-qualified non-held issuer receives one entry disposition:

| Entry disposition | Meaning | May enter ranking? |
| --- | --- | --- |
| `ENTRY_FILTER_FAILED` | complete evidence proves valuation, FCF-yield or liquidity entry rule fails | no |
| `NO_ENTRY_SIGNAL` | complete observations prove the frozen breakout signal is absent | no; non-blocking |
| `ENTRY_ELIGIBLE_POINT` | every entry predicate passes with point-valued rank features | yes |
| `ENTRY_ELIGIBLE_INTERVAL` | every entry predicate passes, but rank features remain intervals | yes, as intervals |
| `UNRESOLVED_DECISION_MATERIAL` | interpretations change entry/trade eligibility | no; blocks the decision date |

Missing signal data is not `NO_ENTRY_SIGNAL`; it is a Layer A market-coverage failure.

## 7. Missing-data and ambiguity matrix

| Situation | Required treatment |
| --- | --- |
| Fewer than five complete fiscal years because complete listing history proves recent listing | `STRUCTURALLY_OUT_OF_SCOPE` |
| Five years should exist, but required report/source/availability evidence is absent | Layer A QB-DATA failure; no Bundle |
| Report/declaration exact-proves a line item or predicate is not applicable | use the report-specific value or N.A. predicate |
| Provider null has no report-specific meaning | Layer A payload/revision failure; never null→zero |
| Exact value fails a quality or entry hard filter | corresponding `*_FILTER_FAILED` disposition |
| Interval lies wholly on the failing side | decision-invariant filter failure; retain interval and mark evidence mode `INTERVAL_DECISION_INVARIANT` |
| Interval lies wholly on the passing side | interval-qualified disposition if later predicates pass |
| Interval straddles a hard threshold, exit condition or trade predicate | `UNRESOLVED_DECISION_MATERIAL` |
| Complete OHLCV proves no breakout | `NO_ENTRY_SIGNAL` |
| Provider/search returns zero rows for penalty, pledge, correction or corporate action | bounded observation only; cannot close Layer A absence authority |
| Complete competent-source declaration proves no event in a closed interval | use explicit no-event result |
| Current/final Universe, industry or controller state is projected backward | Layer A identity/coverage failure |

## 8. Manifest closure

Future Strategy manifests must exact-bind:

- accepted MarketBundle/coverage refs and the full Universe member set;
- one quality disposition per Universe member;
- one continuation disposition per existing holding;
- one entry disposition per non-held quality-qualified issuer when slots are available;
- first failing Strategy stage or all qualified feature refs;
- applicability decisions and candidate intervals;
- evidence mode for interval-based failures;
- exact continued-holding set, exit set and entry-ranking set;
- counts and closure equations for every layer.

Any omission, duplicate, foreign member or count mismatch is a downstream exact-cover failure. It cannot become an empty candidate set.

## 9. Legitimate cash, thin selection and ranking

Existing `CONTINUE_HOLDING` names reserve slots before any new candidate is considered. Ranking applies only to entry-eligible non-held issuers and only for `available_slots`.

Define:

```text
K = min(available_slots, entry_eligible_count)
```

- If `K = 0`, no entry ranking is required.
- If `entry_eligible_count <= available_slots`, every feasible entry-eligible issuer may be selected; no cross-sectional membership ordering is required.
- Otherwise ranking must determine a decision-invariant prefix long enough to fill available slots under the separately frozen sequential feasibility/skip rule.
- Point features rank as degenerate intervals `[x, x]`; ambiguity-policy intervals remain intervals.
- No midpoint, preferred candidate or provider value may silently replace an interval.
- If interval overlap changes the consumed selected/replacement prefix, return `RANKING_AMBIGUOUS`.

An empty or thin new-entry set is legitimate only after Layer A success, complete quality/continuation/entry closure and no unresolved ambiguity. Thresholds are never loosened to fill positions.

## 10. Blocked decisions publish no target

`UNRESOLVED_DECISION_MATERIAL`, `RANKING_AMBIGUOUS` or any upstream authority failure publishes:

```text
no TargetSnapshot
no target event
no execution request
```

It must not publish an empty complete snapshot: under the existing complete-snapshot contract, omission inside a published snapshot means zero target and could fabricate liquidation. The last valid effective target/holding state remains unchanged until a later unblocked decision or explicit authorized exit.

## 11. Failure precedence

### Bundle layer

QB-DATA retains its existing order unchanged:

1. `INPUT_TYPE_MISMATCH`;
2. `CATALOG_IDENTITY_MISMATCH`;
3. `SOURCE_MEMBER_CONFLICT`;
4. `UNIVERSE_CLOSURE_MISMATCH`;
5. `MARKET_COVERAGE_MISMATCH`;
6. `FINANCIAL_REVISION_MISMATCH`;
7. `FINANCIAL_PAYLOAD_INCOMPLETE`;
8. `GOVERNANCE_AUTHORITY_MISMATCH`;
9. `CORPORATE_ACTION_CLOSURE_MISMATCH`;
10. `VALUATION_AUTHORITY_MISMATCH`;
11. `BUNDLE_EXACT_COVER_MISMATCH`;
12. `PUBLICATION_INTEGRITY_FAILURE`.

### Strategy layer after Bundle success

1. manifest/Bundle/Universe identity mismatch;
2. quality/continuation/entry disposition closure mismatch;
3. `UNRESOLVED_DECISION_MATERIAL` in quality, exit or entry eligibility;
4. `RANKING_AMBIGUOUS` for the consumed available-slot prefix;
5. legitimate continued holdings plus thin/empty new-entry result.

An authority or Strategy block is not downgraded to cash, no signal or liquidation.

## 12. Fixed-issuer examples

- Gree 2021 debt: both interpretations pass `ROIC >= 20%`; quality may continue as `QUALITY_QUALIFIED_INTERVAL`, while rank retains the ROIC interval.
- Gree pledge: no controlling shareholder makes that specific predicate N.A.; the largest-shareholder `100%` pledge remains an advisory, not a post-hoc filter.
- Gree valuation: both PE interpretations pass the 60th-percentile new-entry rule; valuation rank remains an interval.
- A held Gree position is not sold because valuation later rises or no new breakout appears; only frozen exit conditions control continuation.
- Valuation candidate 01 is explicitly invalid and excluded. Candidate 02 is valid; no source-layer supersession is inferred.

## 13. Readiness decision

The policy corrections preserve QB-DATA, holding priority, breakout-only entry and no-target-on-block semantics. Full-market execution remains blocked: no accepted immutable Universe/industry authority, issuer-complete source coverage, corporate-action closure, exact feasibility semantics or public multi-stock preparation operation exists.
