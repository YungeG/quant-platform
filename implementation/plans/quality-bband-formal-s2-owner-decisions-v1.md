# Quality-BBAND formal S2 owner decisions v1

- **Status:** `OWNER_APPROVED`
- **Approval date:** `2026-08-27`
- **Owner response:** `批准以上四项`
- **Strategy:** `cn-a-share.quality-bband-breakout.manual4.v1`

## Approved decisions

### 1. Unsupported official statement scope

`STATEMENT_SCOPE_UNSUPPORTED` is issuer-local:

```text
UNRESOLVED_DECISION_MATERIAL / STATEMENT_SCOPE_UNSUPPORTED
```

It provides no numeric values, financial hard-filter failure, S3 admission, forced exit, silent issuer exclusion, slot release, or global block for unrelated issuers.

### 2. Formula-domain failures

When accepted evidence yields any of:

```text
total_profit <= 0
EBITDA <= 0
invested_capital <= 0
```

the affected formula is unavailable and the issuer-local disposition is `UNRESOLVED_DECISION_MATERIAL`. No numeric ratio, fallback formula, denominator substitution, or first-year shortcut may be invented.

If another independent hard filter is already decision-invariantly failed using evidence visible at the same decision time, the overall financial disposition may be `FINANCIAL_HARD_FILTER_FAILED` using only that independent reason. The undefined formula remains recorded as unavailable.

### 3. Public normalization and qualification seam

Approve the two-artifact flow:

```text
quality_bband_s2_normalized_financial_evidence@1
  -> quality_bband_financial_qualification_manifest@1
```

Normalization owns source identity, availability, revision/presentation selection, currency, unit, consolidation, declared debt/D&A, canonical line items, pair disposition, and pair hash.

Qualification owns the frozen ROIC, OCF, FCF, leverage formulas, thresholds, interval/point evidence, screen/issuer disposition, and qualification hash.

`financial_payload_complete=true` means every expected pair is terminally represented by either:

1. a complete accepted numeric normalized payload; or
2. an accepted terminal nonnumeric unresolved/nonfiling record.

A terminal nonnumeric record retains `numeric_payload_complete=false`. Payload closure alone does not grant formal S2, Strategy, Backtest, Validation, decision-grade, or deployment authority.

### 4. Approved merge receipts

The approved order was executed:

| Repository | PR | Merge commit |
|---|---:|---|
| `quant-backtest` | #21 | `958268d33470ece10056b855d01aaa70a1952f1f` |
| `quant-backtest` | #22 | `cdb3197a6fd8c4b18b588c5bb661f38a84329e3e` |
| `quant-backtest` | #23 | `a2f4908304a24566482609de0034075fd5e986c3` |
| `quant-backtest` | #24 | `a5b31db95ca957b20e83ecf453f22af8cf39f001` |
| `quant-platform` | #12 | `6613bfd4971728c8cebf38573aa3816d0b3a975c` |

## Authority ceiling

These decisions resolve S2 semantics only. They do not establish full-market availability, unit/consolidation authority, revision supersession, debt/D&A scope, coherent trio selection, formal S2 qualification, Strategy targets, Backtest execution, Validation, Promotion, deployment, or trading authority.
