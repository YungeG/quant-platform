# Formal S2 implementation packet

## Verdict

**Overall: `NOT_READY`**

The accepted binding proves formal S1 and exact statement-member coverage, but it cannot support formal S2 normalization or five-year qualification yet.

**Bounded prior-balance remediation: `READY`**, but not executed because this task is read-only.

---

## 1. Pinned authority

| Clause | Authority | Required behavior |
|---|---|---|
| C1 | `quality-bband-staged-data-funnel-v1.md:76-106` | S2 consumes exact S1 scope; missing source/lineage/payload blocks publication. Provider absence never excludes an issuer. |
| C2 | `quality-bband-industrial-financial-field-mapping-v1.md:14-160` | Exact Decimal values, CNY/yuan authority, consolidated ordinary-industrial scope, declared debt/D&A, frozen formulas and no first-year shortcut. |
| C3 | Same, §7 | Five annual ROIC values require **six** annual balance endpoints. |
| C4 | `quality-bband-financial-availability-policy-v1.md:34-180` | Provider dates alone cannot produce `available_at`; no historical backfill from later evidence. |
| C5 | `quality-bband-financial-revision-lineage-v1.md:33-263` | `update_flag`, row order and dates do not establish supersession. |
| C6 | `quality-bband-financial-presentation-selection-v1.md:29-134` | Select the latest legally visible eligible presentation and one coherent trio; ambiguity fails closed. |
| C7 | `quality-bband-missing-data-eligibility-policy-v1.md:39-168` | Missing evidence is not zero, hard failure or silent removal. Complete intervals may qualify/fail only when decision-invariant. |
| C8 | `quality-bband-official-annual-nonfiling-terminal-v1.md:18-334` | Accepted nonfiling is issuer-local unresolved from its availability boundary, with no numeric values or backfill. |
| C9 | `quality-bband-data-contract-v1.md:41-162` | Builder owns normalization; Strategy/Build owns feature formulas and qualification. Failures remain atomic. |
| C10 | `quality-bband-pan-hai-2014-official-balance-backfill-v1.md:171-215` | The O backfill exact-covers one key but retains `STATEMENT_SCOPE_UNSUPPORTED` and `financial_scope_qualified=false`. |

### Frozen financial hard filters

For screen year `Y`, use annual periods `Y-5 … Y-1` and the `Y-6` closing balance endpoint:

1. Median of five annual **ROIC** values `>= 0.20`.
2. `n_cashflow_act > 0` in at least four of five years.
3. Sum of five canonical FCF values `> 0`.
4. Latest required annual `net_debt_to_EBITDA < 1.5`; negative net debt naturally passes when EBITDA is positive.

No ROCE fallback, provider ratio, first-year shortcut, TTM substitution or ending-capital substitution is permitted.

---

## 2. Frozen upstream inputs

### Preferred binding

`/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/tushare-s1-s2b-stage-bindings/2017-2025/20260827/v1-candidate-02`

- Manifest ID: `sha256:c54bac9818a24688699aa585e49e91bde64ddbaf3efa90e0aa18491ff9b86f5c`
- File SHA-256: `sha256:ba5abfc5fc592ceb88ce1cabc95ebbded24abe9a8b108e9f6a31c96a0cc0878c`
- Bytes: `7,323`
- `formal_s1_qualified=true`
- `formal_s2_qualified=false`
- Original S1/S2B bytes unchanged.

### S2B candidate 02

- Expected pairs: `32,179`
- Expected statement keys: `96,537`
- Expected-pairs hash: `sha256:336efc4e947062036b1c98add7977653c48abdab8f33350516626a521b9b2b3e`
- Expected-member hash: `sha256:0269e22c9f45b24b827e98a91515ac31ae5486ba0fda668f69112400b088e44b`
- Closure: `96,537 = 96,515 P + 1 O + 21 N`
- Pair classes: `32,171 P/P/P + 1 P/P/O + 7 N/N/N`

### Accepted S2A candidate 02

- Snapshot: `sha256:4e6574363c36f6cebe7f0ad46585a3a9e31b623546240196a2b8bcf55ec57160`
- Content tree: `sha256:3316ea2f6c71f092f5bd803aad6731039b2bc6956c7f176c67183ecaded3e199`
- Receipt SHA-256: `sha256:30afdba09e0a04da1257489a7e13fcee062f41233006fe1d5d8bc33c748791a9`
- Periods: `20121231–20241231`
- Balance schema lacks `lease_liab`.

### Official evidence

- Seven-N publication: `sha256:4a6f1e3231a1b840ac3b4320c4ca445f6ebf40b402a7ac6ac1efd1ad989a4c97`
- Receipt SHA-256: `sha256:6c20ed90b6928b0de19c2a49832d8a68f3cea2f31cc15ad20d0b6d5ca91c78ce`
- Pan Hai O backfill: `sha256:a19316973eb26196cf5cdd1292387cc41e55d2340d5ff98f8c66ba3e65dcd28a`

---

## 3. Material scope defect: five periods are insufficient

The bound expected set requests only five periods per screen. QB-FIN-FIELDS-01 requires six balance endpoints.

### Exact prior-balance requirement

| Item | Count |
|---|---:|
| Screen/issuer prior endpoints required | `20,797` |
| Already represented elsewhere in the 32,179 core pair union | `17,952` |
| Additive `balancesheet_vip` keys required | **`2,845`** |

Additive requirement-list schema:

```text
{
  api_name="balancesheet_vip",
  instrument_id,
  period,
  required_by_screen_dates
}
```

Sorted by `(venue, stable_key, period)`:

- List hash: `sha256:1f3e1b7f235b7eb44af41e547312d88c7cc51acf609faeb9edde9cade49b0410`
- Member-key hash: `sha256:22df5bc4326477e0f4a3ff4da69a8a9681d7b7e0065c59f9d98b38179546918e`

| Prior period | Additive keys |
|---|---:|
| `20111231` | **1,995** |
| `20121231` | 47 |
| `20131231` | 26 |
| `20141231` | 108 |
| `20151231` | 99 |
| `20161231` | 229 |
| `20171231` | 208 |
| `20181231` | 58 |
| `20191231` | 75 |

### Accepted S2A reuse

The accepted S2A terminal leaves already contain every additive 2012–2019 key:

- Covered keys: `850/850`
- Retained rows: `1,698`
- Maximum rows per key: `2`
- Canonical JSONL bytes: `1,030,659`
- SHA-256: `sha256:704ada4176dbdd1d8f8f3f901651b57e13223c65ad3599a1f2e2d06928116f3c`
- Row-ID hash: `sha256:cb0db295e029bfd3dc3bcf901c89ebcbd9c86d67de7f60e37c1f945689b5559e`
- Covered simple-key hash: `sha256:3105da5d6545d147c569f9d7319a9c265d68f187a877fb9861d790affbe9dc5a`
- Missing from that range: zero.

Row treatment:

- `846` update-flag-only duplicate keys;
- `2` single-row keys;
- `2` retained economic/revision conflicts:
  - `xshg:601608 / 20121231`
  - `xshe:002776 / 20151231`

No row is selected by `update_flag`.

### Required new source acquisition

S2A has no `20111231` root. Exactly `1,995` required balance keys therefore need acquisition.

Canonical simple-key hash:

`sha256:5b89864342028b6485ba38d170b52edb9e2df312e6615c35047407679406f0b5`

---

## 4. Cheapest staged remediation

### Stage A — one-root 2011 balance source capture

Use the existing S2A acquisition algorithm unchanged in semantics, but in an additive dedicated module:

```text
api_name    = balancesheet_vip
period      = 20111231
start_date  = 20111231
end_date    = 20260826
comp_type   = "1"
report_type = "1"
```

Fields are exactly the accepted 19-field S2A balance tuple.

Reuse:

- recursive inclusive announcement-date slicing;
- midpoint and terminal-leaf coverage rules;
- depth `16`;
- request ceiling `4096`;
- decoded-byte ceiling `536870912`;
- `0.5` second normal spacing;
- approved proxy, source-snapshot verification, no-clobber publication and credential scans.

This is a physical full-market `SOURCE_SUPERSET`; logical extraction scope is the exact 1,995-key set. Zero rows do not exclude an issuer.

Suggested artifact root:

```text
.../s2c-vip-prior-balance-source-snapshots/2011/20260827/v1-candidate-01
```

### Stage B — additive extraction and rebinding

Inputs:

1. preferred `c54bac98…` stage binding;
2. exact S2B candidate 02;
3. accepted S2A candidate 02;
4. Stage-A 2011 SourceSnapshot/receipt.

Operation:

1. reconstruct all input bytes and IDs;
2. rederive the 20,797 prior requirements and frozen hashes;
3. reference 17,952 existing core balance keys;
4. extract the known 850 keys/1,698 rows from accepted S2A;
5. extract the exact 1,995 2011 keys from Stage A;
6. retain every revision candidate and audit all source extras;
7. require zero missing/overlap/conflict keys;
8. publish atomically.

Closure:

```text
20,797 prior endpoint requirements
= 17,952 existing core balance keys
+ 850 accepted-S2A extra keys
+ 1,995 new 2011 keys
```

Augmented statement-member requirement count:

```text
96,537 core + 2,845 prior balance = 99,382
```

Suggested artifact members:

```text
prior-balance-requirements.json
prior-balance-provider-rows.jsonl
prior-balance-binding-manifest.json
```

The resulting binding must still retain:

```text
formal_s1_qualified=true
s2b_exact_cover_complete=true
prior_balance_endpoint_cover_complete=true
formal_s2_qualified=false
strategy_authorized=false
backtest_authorized=false
strategy_target_authorized=false
validation_authorized=false
deployment_authorized=false
decision_grade_eligible=false
```

---

## 5. Exact remediation write set

### Stage A

1. `tools/acquisition/cn_a_share_tushare_s2c_2011_prior_balance_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_tushare_s2c_2011_prior_balance_source_bounded_v1.py`
3. `tests/architecture/test_g12a_tushare_s2c_2011_prior_balance_source_bounded_v1_boundary.py`

### Stage B

1. `tools/acquisition/cn_a_share_quality_bband_s1_s2b_prior_balance_binding_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_quality_bband_s1_s2b_prior_balance_binding_v1.py`
3. `tests/architecture/test_quality_bband_s1_s2b_prior_balance_binding_v1_boundary.py`

Recommended Backtest base: `0c00c8266c2fe904e11f982979d804ff5d205700`.

No predecessor, root export, Runtime, Trading, lockfile or existing artifact modification.

---

## 6. Eventual formal-S2 public seam

A single combined Builder artifact is not contract-compliant because normalization and Strategy qualification have different owners. The minimum honest seam is:

```text
quality_bband_s2_normalized_financial_evidence@1
    ↓
quality_bband_financial_qualification_manifest@1
```

### Normalized pair record

One record for each of the `32,179` core pairs, binding:

- P/O/N source class;
- all statement source-row/declaration IDs;
- decision-visible selected trio;
- official availability, document, currency, unit and consolidation;
- canonical raw line items as decimal strings;
- declared debt and D&A;
- pair disposition and hash.

No active-stage source defect may be converted to a record. N may emit only the frozen nonfiling unresolved record.

### Qualification record

Exactly `20,797` screen/issuer records, each binding:

- five pair hashes;
- opening balance endpoint hash;
- five ROIC values and median;
- five OCF and FCF values;
- latest leverage value;
- four exact threshold results;
- point/interval evidence mode;
- terminal disposition and hash.

Expected dispositions:

```text
FINANCIAL_QUALIFIED_POINT
FINANCIAL_QUALIFIED_INTERVAL
FINANCIAL_HARD_FILTER_FAILED
UNRESOLVED_DECISION_MATERIAL
```

Seven N screen records are already derivable as issuer-local:

```text
UNRESOLVED_DECISION_MATERIAL
/ REQUIRED_ANNUAL_REPORT_NOT_FILED
```

No values, S3 admission, threshold failure, forced exit or unrelated-issuer block.

---

## 7. Remaining formal-S2 blockers

Even after prior-balance rebinding, current P/O/N evidence is not normalization-ready:

1. **Availability:** all 96,515 P keys have provider dates only; QB-FIN-AVAIL-01 rejects them as authority.
2. **Unit/consolidation:** no full-market official CNY/yuan statement declarations exist.
3. **Debt and D&A:** no full-market financing-note or D&A semantic declarations exist; `lease_liab` is absent from S2A.
4. **Revisions:** 5,861 provider keys contain economic variants; no generic supersession binders exist.
5. **Trio coherence:** 883 P-only pairs lack even a common provider `ann_date/f_ann_date` candidate across all three APIs. This is diagnostic, not a legal selector.
6. **O pair:** `000046.SZ/20141231` remains mixed-layout and scope-unqualified, affecting the 2017, 2018 and 2019 screens.
7. **Public owner seam:** the repository has no approved Strategy-Build owner module for financial qualification.

Consequently, no pass/fail counts or formal-S2 output hashes are derivable.

---

## 8. Unavoidable owner decisions

Only these decisions remain genuinely semantic:

1. **Unsupported O disposition:** decide whether `STATEMENT_SCOPE_UNSUPPORTED` becomes an explicit issuer-local financial-scope exclusion, or remains a stage-blocking payload failure. It cannot be silently treated as an industrial hard-filter failure.
2. **Formula-domain disposition:** specify whether complete evidence with `total_profit <= 0`, `EBITDA <= 0` or nonpositive invested capital is a hard-filter failure or unresolved qualification. The field contract currently says “unavailable,” not which S2 disposition follows.
3. **Public split/flags:** approve the two-artifact normalization→qualification seam and define `financial_payload_complete` semantics when accepted N records contain no numeric payload.

No decision is needed for the six-balance rule, numeric thresholds, prior-endpoint remediation, N behavior, revision selection or unit/debt formulas.

---

## 9. Failure precedence

Preserve the existing QB-DATA order, restricted to relevant S2 branches:

1. `INPUT_TYPE_MISMATCH`
2. `CATALOG_IDENTITY_MISMATCH`
3. `SOURCE_MEMBER_CONFLICT`
4. `FINANCIAL_REVISION_MISMATCH`
5. `FINANCIAL_PAYLOAD_INCOMPLETE`
6. `BUNDLE_EXACT_COVER_MISMATCH`
7. `PUBLICATION_INTEGRITY_FAILURE`

Stage-local exact-cover reasons include:

```text
STAGE_INPUT_SCOPE_MISMATCH
EXPECTED_MEMBER_MISSING
PRIOR_BALANCE_ENDPOINT_MISSING
PAIR_DISPOSITION_CLOSURE_MISMATCH
```

No failure emits partial normalized pairs, a reduced issuer set or an empty downstream manifest.

---

## 10. Sentinels and validation allocation

### Remediation sentinels

- Omit one 2011 key → `BUNDLE_EXACT_COVER_MISMATCH/EXPECTED_MEMBER_MISSING`, no binding.
- Mutate the 850-key set → frozen covered-key hash fails.
- Change one extracted row byte → provider JSONL SHA fails.
- Reorder source pages/rows → canonical output unchanged.
- Economic duplicate rows remain retained; `update_flag=1` never wins.
- Original stage-binding and S2B member hashes remain byte-identical.

### Formal-S2 sentinels

- Five trios without opening balance → `PRIOR_BALANCE_ENDPOINT_MISSING`.
- Provider-only dates → `FINANCIAL_REVISION_MISMATCH`.
- Missing unit/debt declaration → `FINANCIAL_PAYLOAD_INCOMPLETE`.
- Accepted N → issuer-local unresolved with no numeric fields.
- Any omitted screen member → disposition closure failure.
- Every Strategy/Backtest/Validation/deployment flag remains false.

### Validation pyramid

- Writer: each focused test plus one real-artifact opt-in check.
- Candidate: both focused suites, all acquisition/Builder tests and architecture boundaries.
- Shared-node gate: one full locked Backtest suite.
- Fan-in: protected hashes, clean status and blocker-only review.

---

## 11. Completion record

- Repository files changed: **none**
- Candidate diff/commit: **none**
- Artifact publication performed: **none**
- Verified: upstream SHA-256 values, P/O/N closure, prior-endpoint derivation, accepted S2A 850-key extraction, canonical counts/hashes and relevant Backtest branch symbols.
- Formal S2 authority: **false**
- Strategy/Backtest/Validation/deployment authority: **all false**
- Next owner: Backtest G12A acquisition owner for Stage A, then the prior-balance rebinding writer for Stage B.
