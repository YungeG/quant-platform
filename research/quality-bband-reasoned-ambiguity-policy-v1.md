# Quality + B-Band reasoned ambiguity policy v1

- **Status:** `POLICY_FROZEN / RESEARCH_CONTINUATION_AUTHORIZED / SOURCE_FACTS_UNCHANGED`
- **Approved intent:** explain common data contradictions through the most reasonable auditable inference chain; retain unresolved alternatives; block only when the contradiction can change a downstream qualification, rank or trade decision
- **Scope:** Research/Strategy feature interpretation only; no rewrite of Builder source/declaration/normalization evidence

## 1. Principle

A contradiction does not automatically stop research. It is classified by its effect on the downstream decision.

```text
source contradiction
→ enumerate every evidence-supported interpretation
→ explain the preferred interpretation
→ calculate the downstream result under every reasonable interpretation
→ continue only if the required decision is invariant
```

The policy never silently chooses a convenient value.

## 2. Exact classes

### `EXACTLY_RESOLVED`

Competent source authority provides one unique result. Use that value normally.

### `EXPLAINED_DECISION_INVARIANT`

No unique source-authoritative value exists, but:

1. the finite candidate set or interval is exact-bounded by retained evidence;
2. one interpretation may be identified as economically preferred with an explicit reasoning chain;
3. every reasonable interpretation produces the same required boolean qualification or trade decision;
4. the full candidate set/interval remains attached to the result.

Research may continue for that invariant decision. Exact point ranking remains unavailable unless rank order is also invariant across intervals.

### `UNRESOLVED_DECISION_MATERIAL`

Reasonable interpretations can change:

- pass/fail qualification;
- selected top-N membership or ordering;
- target weight;
- entry/exit decision;
- risk/accounting result.

The affected operation fails closed and records the conflict.

## 3. Layer boundary

Existing source artifacts remain unchanged:

```text
2021 declaration = DEBT_SCOPE_INCOMPLETE
2021 normalized observation set = absent
```

A later Research/Strategy feature assessment may consume the exact conflict evidence and produce an ambiguity-qualified result. It cannot relabel the declaration as exact, fabricate a Builder observation or rewrite historical identities.

Required interpretation evidence:

```python
{
  conflict_hash,
  candidate_values,
  preferred_candidate?,
  reasoning_refs,
  downstream_results_by_candidate,
  decision_kind,
  invariant_decision,
  exact_value_available=false,
  source_bounded=true,
  decision_grade_eligible=false,
  deployment_authorized=false,
}
```

## 4. Ranking rule

For a threshold rule, all candidates must lie on the same side of the threshold.

For top-N ranking:

- compare complete score intervals;
- continue only if selected membership and required ordering are identical for all combinations;
- overlapping intervals at the cutoff return `RANKING_AMBIGUOUS`;
- never rank by the preferred point estimate alone.

## 5. Gree 2021 application

Evidence-supported debt candidates:

```text
narrow = 43,561,695,281.25
broad  = 46,293,375,395.45
preferred economic interpretation = broad
source-authoritative exact value = unavailable
```

Preferred-reasoning chain:

1. the 2021 note labels the amount `企业借款及利息`;
2. the 2022 report carries the exact comparative amount under the same label;
3. the 2022 current-period amount is included in interest-bearing liabilities at `4.00%-5.00%` floating interest;
4. therefore omission from the 2021 interest-bearing table is most plausibly a disclosure-table omission;
5. because no explicit correction/restatement exists, the narrow candidate remains retained.

## 6. Downstream sensitivity

Using the frozen formula definitions:

| Metric | Narrow candidate | Broad candidate | Decision effect |
| --- | ---: | ---: | --- |
| 2021 ending debt | `43,561,695,281.25` | `46,293,375,395.45` | exact point ambiguous |
| 2021 ROIC | `127.2984%` | `118.8062%` | both pass `20%` |
| 2022 ROIC | `78.2238%` | `75.0674%` | both pass `20%` |
| five-year ROIC median | `127.2984%` | `118.8062%` | both pass `20%` |

Other exact financial-quality facts:

```text
2019 ROIC = 871.1452%
2020 ROIC = 605.8101%
2023 ROIC = 52.3342%
positive operating cash flow = 5 / 5 years
cumulative source-derived FCF = 107,662,796,746.80 CNY
2023 net debt / EBITDA = -0.8663154
```

The high ROIC values reflect very low/negative-net-debt invested-capital denominators and must not be interpreted as a general valuation conclusion. The 2021 OCF/FCF figures are Research-layer calculations from retained raw rows; they are not an emitted exact 2021 normalized set or QualityFeatureManifest.

## 7. Gree decision

```text
2021 debt exact value = unavailable
financial-quality threshold result = robust pass
financial-quality ranking value = interval, not exact point
2021 conflict blocks source exactness = yes
2021 conflict blocks the 20% quality threshold = no
2021 conflict blocks ranking when intervals overlap another issuer = yes
```

Therefore the contradiction no longer blocks continued fixed-issuer financial-quality research. It still prevents an exact point-valued feature and may block future cross-sectional ranking.

## 8. Remaining blockers

This policy does not supply:

- accepted PR #1–#8 authority;
- full-market financial coverage;
- audit-opinion, penalty, pledge or merger-history authority;
- historical valuation inputs;
- immutable Universe/corporate-action coverage;
- public multi-stock Backtest preparation;
- Strategy, Validation, Live or deployment authority.

Continuation moves to the next missing authority rather than pretending the accounting conflict disappeared.
