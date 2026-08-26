# QB-ELIG-01 — Quality + B-Band missing-data eligibility policy v1

- **Status:** `STAGED_FUNNEL_AMENDED / NONFILING_TERMINAL_USER_APPROVED / CONTRACT_FROZEN / PLAN_ONLY / GENERAL_MARKET_AUTHORITY_MISSING`
- **Scope:** alternating staged QB-DATA authority and deterministic structural/quality/entry qualification
- **Consumer:** future quality, continuation, entry and ranking manifests

## 1. Outcome

Missing evidence is never converted to zero, a low score, an automatic threshold failure or a silently removed stock.

QB-DATA exact-cover remains unconditional within each approved stage. S0 exact-covers the broad independent Universe; every later data stage exact-covers only the deterministic qualified output set from its prior Strategy stage. Missing provider rows never define scope, and no stage may silently omit an expected issuer.

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

Industry history is a distinct future Bundle capability. Provisional planning vocabulary, pending Backtest-owner approval:

```text
industry_membership_revision@1
IndustryMembershipCoverageReportV1
```

The portfolio authority must exact-bind the approved industry report alongside Universe coverage. QB-UNIV-CA-01 freezes required semantics; G12B must approve exact schema/name before implementation.

A provider-covered financial subset, bar-presence subset, current constituent list, current industry classification or current controller field must never define historical Universe membership.

## 3. Alternating authority and Strategy stages

The staged sequence is frozen in [`quality-bband-staged-data-funnel-v1.md`](quality-bband-staged-data-funnel-v1.md):

```text
S0 lightweight broad authority
→ S1 structural qualification
→ S2 minimal financial authority + qualification
→ S3 governance/valuation authority + qualification
→ S4 market/action authority + entry/holding decisions
→ final composite authority
```

Data stages preserve existing QB-DATA failure precedence and atomic semantics. Strategy stages are pure deterministic transformations over accepted upstream manifests. Missing/foreign/conflicting source authority blocks the active data stage and emits no downstream scope; exact hard-filter failures may legally reduce the next stage's scope only after complete prior-stage closure.

Stage payloads may carry explicit source-bounded candidate intervals or N.A. declarations when their schemas and source coverage are mechanically complete. An accepted `official_annual_report_nonfiling_declaration@1` is one such terminal declaration: it covers the expected statement kinds but supplies no financial values and maps to `UNRESOLVED_DECISION_MATERIAL` only from its conservative availability boundary. Stage payloads may not silently fabricate an exact point.

## 4. Quality qualification

Quality stages are:

1. S1 structural scope over S0: ordinary沪深主板, non-financial, listed at least five years;
2. financial-quality hard filters after S2 exact-covers every S1 survivor;
3. audit, severe-penalty/fraud and controlling-shareholder-pledge hard filters after S3 exact-covers every financial survivor.

A complete decision-invariant failure at an earlier quality stage ends later feature calculation and legally removes that issuer/date from the next data-stage request scope. The active stage's own expected scope must still be exact-covered.

Every Universe member receives exactly one quality disposition:

| Quality disposition | Meaning |
| --- | --- |
| `STRUCTURALLY_OUT_OF_SCOPE` | complete point-in-time facts prove board, industry or listing-age exclusion |
| `QUALITY_HARD_FILTER_FAILED` | exact evidence or a wholly failing interval proves one frozen quality threshold fails |
| `QUALITY_QUALIFIED_POINT` | all quality hard filters pass with point-valued rank features |
| `QUALITY_QUALIFIED_INTERVAL` | all interpretations pass, but one or more rank features remain intervals |
| `UNRESOLVED_DECISION_MATERIAL` | evidence-supported interpretations change quality qualification, or competent-source confirmed non-filing leaves required annual financial qualification unavailable |

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

Fresh B-Band signal, current valuation percentile and cross-sectional rank are not continuation requirements. Every actually held Instrument, including one with `EXIT_REQUIRED`, occupies a slot until its exit execution is confirmed.

An exit may be emitted only through the separately frozen next-eligible-execution semantics. A pending or blocked exit emits no replacement target, no empty target and no fabricated liquidation instruction.

## 6. New-entry eligibility

Only non-held quality-qualified issuers may enter new-entry evaluation. Pending exits still occupy positions until execution is confirmed. At T close:

```text
available_slots = 4 - actual_held_instrument_count
```

If `available_slots = 0`, no new-entry ranking is required. No atomic sell-before-buy slot release is inferred.

New-entry stages are:

1. positive FCF yield and five-year valuation-percentile rule;
2. liquidity coverage and threshold;
3. complete T-close BOLL contraction/trend/volume-breakout signal;
4. interval-aware T-close ranking for the available slots.

T+1 gap, tradability and lot-capital checks apply only to selected names after ranking. Failure leaves cash and waits for a later complete signal; it does not promote another issuer at the same open.

Each quality-qualified non-held issuer receives one entry disposition:

| Entry disposition | Meaning | May enter ranking? |
| --- | --- | --- |
| `ENTRY_FILTER_FAILED` | complete evidence proves valuation, FCF-yield or liquidity entry rule fails | no |
| `NO_ENTRY_SIGNAL` | complete observations prove the frozen breakout signal is absent | no; non-blocking |
| `ENTRY_ELIGIBLE_POINT` | every entry predicate passes with point-valued rank features | yes |
| `ENTRY_ELIGIBLE_INTERVAL` | every entry predicate passes, but rank features remain intervals | yes, as intervals |
| `UNRESOLVED_DECISION_MATERIAL` | interpretations change entry/trade eligibility | no; blocks the decision date |

Missing signal data is not `NO_ENTRY_SIGNAL`; it is an S4 market-coverage failure.

## 7. Missing-data and ambiguity matrix

| Situation | Required treatment |
| --- | --- |
| Fewer than five complete fiscal years because complete listing history proves recent listing | `STRUCTURALLY_OUT_OF_SCOPE` |
| Five years should exist, but required report/source/availability evidence is absent | active data-stage QB-DATA failure; no downstream manifest |
| Competent issuer/exchange/regulator evidence confirms the annual report was not filed by the statutory deadline and QB-S2-NONFILE-01 exact-cover is accepted | terminal-cover the three expected statement kinds; `UNRESOLVED_DECISION_MATERIAL` from declaration availability; no numeric values, S3/ranking admission or forced exit |
| Report/declaration exact-proves a line item or predicate is not applicable | use the report-specific value or N.A. predicate |
| Provider null has no report-specific meaning | active data-stage payload/revision failure; never null→zero |
| Exact value fails a quality or entry hard filter | corresponding `*_FILTER_FAILED` disposition |
| Interval lies wholly on the failing side | decision-invariant filter failure; retain interval and mark evidence mode `INTERVAL_DECISION_INVARIANT` |
| Interval lies wholly on the passing side | interval-qualified disposition if later predicates pass |
| Interval straddles a hard threshold, exit condition or trade predicate | `UNRESOLVED_DECISION_MATERIAL` |
| Complete OHLCV proves no breakout | `NO_ENTRY_SIGNAL` |
| Provider/search returns zero rows for penalty, pledge, correction or corporate action | bounded observation only; cannot close the active data stage's absence authority |
| Complete competent-source declaration proves no event in a closed interval | use explicit no-event result |
| Current/final Universe, industry or controller state is projected backward | S0/S3 identity or coverage failure |

## 8. Manifest closure

Future Strategy manifests must exact-bind:

- accepted MarketBundle/coverage refs and the full Universe member set;
- one quality disposition per Universe member;
- one continuation disposition per existing holding;
- one entry disposition per non-held quality-qualified issuer when slots are available;
- first failing Strategy stage or all qualified feature refs;
- applicability decisions and candidate intervals;
- evidence mode for interval-based failures and any official annual-report non-filing declaration refs;
- exact continued-holding set, exit set and entry-ranking set;
- counts and closure equations for every layer.

Any omission, duplicate, foreign member or count mismatch is a downstream exact-cover failure. It cannot become an empty candidate set.

## 9. Legitimate cash, thin selection and ranking

Every actually held Instrument reserves a slot until its exit execution is confirmed. Ranking applies only to entry-eligible non-held issuers and only for `available_slots`.

Define:

```text
K = min(available_slots, entry_eligible_count)
```

- If `K = 0`, no entry ranking is required.
- If `entry_eligible_count <= available_slots`, every entry-eligible issuer may be selected; no cross-sectional membership ordering is required.
- Otherwise ranking must determine one decision-invariant T-close top-`K` set.
- Point features rank as degenerate intervals `[x, x]`; ambiguity-policy domains remain exact finite vectors or constrained intervals.
- No midpoint, preferred candidate or provider value may silently replace ambiguity.
- If admissible interpretations change top-`K` membership, return `RANKING_AMBIGUOUS`.
- T+1 failure for a selected name leaves the slot in cash; no lower-ranked same-open replacement is authorized.

An empty or thin new-entry set is legitimate only after every consumed S0–S4 stage succeeds, complete quality/continuation/entry closure exists and no globally blocking ambiguity remains. The issuer-local `UNRESOLVED_DECISION_MATERIAL / REQUIRED_ANNUAL_REPORT_NOT_FILED` outcome under QB-S2-NONFILE-01 is a closed noncandidate, not a global ambiguity; it removes only that issuer from S3/entry scope. Thresholds are never loosened to fill positions.

## 10. Blocked decisions publish no target

Any globally blocking `UNRESOLVED_DECISION_MATERIAL`, `RANKING_AMBIGUOUS` or active-stage authority failure publishes:

```text
no TargetSnapshot
no target event
no execution request
```

It must not publish an empty complete snapshot: under the existing complete-snapshot contract, omission inside a published snapshot means zero target and could fabricate liquidation. The last valid effective target/holding state remains unchanged until a later unblocked decision or explicit authorized exit.

Exception: `UNRESOLVED_DECISION_MATERIAL / REQUIRED_ANNUAL_REPORT_NOT_FILED` is issuer-local after accepted QB-S2-NONFILE-01 exact cover. It excludes that issuer from S3/new-entry ranking while unrelated issuers continue. If the issuer is held, continuation/exit is evaluated independently; non-filing alone emits no exit, slot release or replacement target. Every other unresolved reason remains globally blocking.

## 11. Failure precedence

### Data-stage failures

Every active S0/S2/S3/S4 data stage retains the existing QB-DATA order unchanged:

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

### Strategy-stage failures

After each required upstream data-stage success, S1/financial/governance-entry/ranking transformations use:

1. manifest/stage/Universe identity mismatch;
2. quality/continuation/entry disposition closure mismatch;
3. globally blocking `UNRESOLVED_DECISION_MATERIAL` in quality, exit or entry eligibility; issuer-local `REQUIRED_ANNUAL_REPORT_NOT_FILED` is already closed as a noncandidate and does not enter this failure branch;
4. `RANKING_AMBIGUOUS` for T-close top-`K` membership;
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
