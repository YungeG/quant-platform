# QB-FIN-AVAIL-01 — A-share financial-statement availability policy v1

- **Status:** `CONTRACT_FROZEN_FOR_REVIEW / CURRENT_SNAPSHOT_BLOCKED`
- **Owner:** Backtest Market Bundle Builder availability normalization
- **Input prerequisite:** QB-FIN-SENTINEL-01 SourceSnapshot plus competent publication evidence
- **Consumer:** future `financial_statement_observations@1` Builder sentinel
- **Source matrix:** [`research/quality-bband-financial-governance-source-matrix.md`](../../research/quality-bband-financial-governance-source-matrix.md)

## 1. Outcome

Resolve one raw financial-statement disclosure to the earliest **defensible non-lookahead visibility boundary** that a Backtest Strategy may use.

V1 separates:

- report period/economic time;
- historical publication/Strategy visibility time;
- later acquisition time;
- later retrospective closure-evidence time.

It never substitutes acquisition time for historical availability, guesses an intraday timestamp from a date, or backdates a later confirmation document as a Strategy-visible event.

## 2. Authority

| ID | Authority | Requirement |
| --- | --- | --- |
| V1 | `backtest/docs/architecture/backtest-system-design.md` | Observation visibility requires `available_time <= decision time`; future revisions cannot rewrite earlier Decision Context. |
| V2 | `backtest/CONTEXT.md` definitions of Provider Availability, Acquisition and Assessment Time | These times are separate authorities and cannot substitute for one another. |
| V3 | `research/quality-bband-financial-governance-source-matrix.md` | Tushare `ann_date`/`f_ann_date` are day-granular; exact public time and revision closure are absent. |
| V4 | SZSE 2024 holiday notice | `2024-05-01` through `2024-05-05` were closed and `2024-05-06` reopened: <https://www.szse.cn/disclosure/notice/t20231226_605108.html>. |
| V5 | G11B point-in-time observation contract | Availability cutoff uses complete immutable evidence; unavailable or future facts fail closed. |

## 3. Evidence classes

### `EXACT_OFFICIAL_INSTANT`

Accepted only when competent exchange/CNINFO publication metadata exact-binds:

- issuer/security identity;
- document identity and exact content hash;
- publication timestamp with timezone or unambiguous UTC;
- source member and acquisition receipt;
- metadata schema/version.

Tushare dates do not override a matching exact official instant. If Tushare dates conflict with the exact instant's Asia/Shanghai local date, V1 fails rather than choosing either source.

### `OFFICIAL_DATE_ONLY`

Accepted only when a competent official metadata record or retrospective official confirmation exact-binds the document hash and states the publication calendar date, but supplies no defensible intraday timestamp.

A URL path date, PDF creation/modification metadata, filesystem time, HTTP `Date`, search-result date or Tushare date alone is not official publication-date authority.

### `PROVIDER_DATE_ONLY`

Tushare `ann_date`/`f_ann_date` are retained as provider observations. They may corroborate an accepted official date but cannot independently produce a Strategy `available_at` in v1.

### `UNUSABLE`

Missing document binding, date conflict, unsupported timezone/precision, provider-only date, or absent Calendar coverage produces no availability result.

## 4. Resolution algorithm

For one exact issuer/report/document lineage:

1. validate exact input types, schema versions, document/member hashes and issuer/period identity;
2. reject any evidence not bound to the exact report bytes;
3. classify official evidence as exact-instant or date-only;
4. validate Tushare `ann_date`/`f_ann_date` without treating `update_flag` as finality;
5. if exact official timestamp exists:
   - require one unique timestamp after duplicate collapse;
   - require every supplied official date and Tushare date to equal its Asia/Shanghai local date;
   - return that exact UTC timestamp;
6. otherwise require at least one official date-only record:
   - require official dates and non-null Tushare dates to agree;
   - resolve the first known Trading Session whose TradingDate is **strictly after** the official publication date;
   - set conservative availability to that Session's declared Asia/Shanghai continuous-auction open, normally 09:30;
7. require acquisition time and retrospective closure-evidence time not earlier than their source evidence;
8. return one immutable result or one structured failure; never return a partial/default timestamp.

V1 deliberately requires date agreement instead of taking `min` or `max`. Conflicting dates are evidence defects, not inputs to an averaging or conservative-selection heuristic.

## 5. Date-only conservative rule

```text
publication date D
→ caller-supplied Frozen Trading Calendar
→ first declared TradingDate strictly greater than D
→ declared continuous-auction open in Asia/Shanghai
→ UTC available_at
```

Rules:

- do not use natural-day, weekday or holiday arithmetic;
- do not use the same-day open even if the document might have been published before open;
- do not infer 09:30 unless the accepted SessionModel declares it;
- Calendar gap or missing next Session fails closed;
- the result remains `source_bounded` and `decision_grade_eligible=false` until broader source/closure qualification exists.

This ceiling is intentionally conservative. A future exact official timestamp can replace it only through a new source revision and new Bundle identity; it cannot rewrite an existing Bundle.

## 6. Retrospective confirmation

A later competent official document may state that the exact report was disclosed on date `D`. It may establish retrospective source authority for `D` when:

- issuer, report title/period and document hash are exact-bound;
- the confirmation bytes and publication metadata are retained;
- `closure_evidence_available_at` records when the confirmation became available;
- the derived report availability remains the conservative boundary after `D`, not the confirmation acquisition date;
- the confirmation itself is not exposed to historical Strategy decisions before its own availability.

This is retrospective qualification, not backdating later evidence.

## 7. Proposed public values

Names remain provisional pending Backtest-owner review:

```python
FinancialPublicationPrecisionV1 = EXACT_INSTANT | DATE_ONLY

FinancialPublicationEvidenceV1 = {
  schema_version,
  issuer_key,
  instrument_id,
  report_period,
  document_hash,
  source_key,
  source_hash,
  precision,
  publication_instant?,
  publication_date?,
  acquired_at,
}

FinancialAvailabilityRequestV1 = {
  schema_version,
  evidence,
  provider_ann_date?,
  provider_f_ann_date?,
  calendar,
  session_model,
  captured_at,
}

FinancialAvailabilityResultV1 = {
  schema_version,
  request_hash,
  document_hash,
  event_period_end,
  available_at_utc,
  resolution_kind,
  official_evidence_hashes,
  provider_date_observations,
  source_bounded=true,
  decision_grade_eligible=false,
  deployment_authorized=false,
}
```

Builder event phase/source-sequence composition is out of scope for this policy and must be frozen with `financial_statement_observations@1`. V1 resolves the UTC visibility boundary only.

## 8. Failure precedence

| Priority | Condition | Proposed code |
| ---: | --- | --- |
| 1 | request/value exact type or schema mismatch | `INPUT_MISMATCH` |
| 2 | issuer/report/document/member hash mismatch | `DOCUMENT_IDENTITY_MISMATCH` |
| 3 | malformed/unsupported publication evidence | `PUBLICATION_EVIDENCE_INVALID` |
| 4 | multiple non-identical exact official instants | `OFFICIAL_INSTANT_CONFLICT` |
| 5 | official/provider local dates disagree | `PUBLICATION_DATE_CONFLICT` |
| 6 | provider-only date with no official authority | `OFFICIAL_PUBLICATION_AUTHORITY_MISSING` |
| 7 | exact instant timezone/local-date mismatch | `PUBLICATION_TIMEZONE_MISMATCH` |
| 8 | Calendar does not cover publication/next-session search | `CALENDAR_COVERAGE_MISSING` |
| 9 | no unique next declared Session | `NEXT_SESSION_UNAVAILABLE` |
| 10 | Session open/timezone cannot be represented exactly | `SESSION_BOUNDARY_UNREPRESENTABLE` |
| 11 | acquisition/closure/captured-at causality mismatch | `EVIDENCE_TIME_MISMATCH` |
| 12 | final result reconstruction/hash mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

Every failure returns no `available_at` and writes no observation/Bundle publication.

## 9. Exact Gree sentinel decision

Current PR [`YungeG/quant-backtest#1`](https://github.com/YungeG/quant-backtest/pull/1) retains:

- Tushare rows with date `20240430`;
- CNINFO report PDF `1219928418.PDF`;
- exact report hash `sha256:32ebc475a2291ce4f1b5c1a9f9da55227e03192f07e75041e976c29d213ec8aa`.

It does **not** retain official publication metadata or an official confirmation member. Therefore its exact V1 availability outcome is:

```text
OFFICIAL_PUBLICATION_AUTHORITY_MISSING
available_at = null
Builder normalization = terminated
```

A candidate retrospective confirmation is CNINFO document `1220300051.PDF`, which states that the issuer disclosed the 2023 annual report on `2024-04-30`:

- URL: `https://static.cninfo.com.cn/finalpage/2024-06-08/1220300051.PDF`;
- bytes: `302155`;
- SHA-256: `sha256:a78a67865a7ea989c4fd8b053fad1aa75f36d22c10d14387800ff16b698dbc60`.

If an accepted successor SourceSnapshot retains that confirmation, exact document binding is approved, and an accepted Calendar/SessionModel proves the 2024 Labour Day closure, the date-only candidate boundary is:

```text
2024-05-06T09:30:00+08:00
= 2024-05-06T01:30:00Z
= UtcInstant(1714959000000000000)
```

This candidate value is not yet an accepted `available_at`.

## 10. Compatibility and forbidden paths

- QB-FIN-SENTINEL-01 bytes, receipt and PR remain unchanged.
- Tushare `ann_date`, `f_ann_date`, `update_flag`, HTTP request time and local acquisition time cannot directly become `available_at`.
- CNINFO/SZSE URL path dates and PDF metadata cannot directly become `available_at`.
- A later confirmation can qualify history retrospectively but cannot appear in historical ObservationView before its own availability.
- Missing Calendar dates cannot be filled by Python weekday logic.
- No Strategy/Runtime module may resolve availability from raw provider rows.
- No exact-time result may be downgraded to date-only because another source is less precise; conflicts fail closed.

## 11. Acceptance

A future pure implementation must prove:

1. exact official timestamp success and timezone conversion;
2. date-only next-session success across weekday, weekend and multi-day holiday closures;
3. same-day open is never selected for date-only evidence;
4. provider-only date, path date and PDF metadata fail;
5. official/provider date conflicts and multiple official instants fail at precedence;
6. Calendar gap, no next Session and unrepresentable boundary fail;
7. retrospective confirmation does not enter historical Strategy visibility;
8. input order, duplicate evidence and batch shape do not alter result/hash;
9. no observation/Bundle bytes on failure;
10. protected SourceSnapshot and PR #1 identities remain unchanged.

## 12. Readiness decision

The policy contract is frozen for review. The current four-member SourceSnapshot remains unavailable for Builder normalization. The next safe data action is to freeze the financial revision lineage contract, then design a successor acquisition member for competent publication-date confirmation.
