# Quality-BBAND official S2 remediation source assessment v1

Status: `SOURCE_CANDIDATE_ACCEPTED / DECLARATIONS_AND_EXTRACTION_PENDING / S2B_FALSE`  
Date: 2026-08-26  
Implementation: Backtest commit `7276c69`, PR <https://github.com/YungeG/quant-backtest/pull/13>

## Selected candidate

`/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/official-s2-remediation-source-snapshots/eight-issuer/20260826/v1-candidate-01`

| Identity | Value |
|---|---|
| SourceSnapshot | `sha256:8195e9d9e99949802c829f218929bdbf740b336152d83ad789a060e0355d116e` |
| Content tree | `sha256:c315b9b36d5817fc058da240b50e2c170f530f2b2b4b49808554ef6ddedac15b` |
| Provenance | `sha256:cbce2903c280938647526abfc0511cc497d85d61f5486e79469ab0714a9c05a2` |
| Snapshot file | `sha256:78448e043e966b929d48db6c547be22e2102a498bd6c2a73c1ce47f9208d7294` |
| Receipt file | `sha256:6d60f18e75ca87a1762430d34b43b2af08d141f5103af39573779dde09144fa7` |
| Canonical 24-file manifest | `sha256:0e0cb078379dc86b3dc2b3cc21d90e5e89ba5e1cf9638fb96e985f59325bb658` |

## Capture facts

- 24 exact regular files, all disk mode `0600`;
- 22 SourceSnapshot raw members, logical mode `0644`;
- 7 CNINFO metadata members containing 63 records;
- 11 selected metadata facts and 52 retained extras;
- 15 official PDFs;
- 6,858,620 raw bytes and 6,893,924 total bytes.

Independent review reconstructed the SourceSnapshot exactly and accepted every receipt/member/file hash, size, timestamp and mode binding. All selected metadata IDs, normalized titles, dates and adjunct URLs matched. Every PDF retained `%PDF-` magic and matched its frozen byte count and SHA-256.

Focused tests passed `29`; bundle-builder/acquisition regression passed `688`, with `5` configured real-artifact skips. LSP was clean.

## Evidence lanes

### Existing filing

`000046.SZ` FY2014 official annual report is retained as:

```text
response/official/000046/1200788303.pdf
sha256:0a5bce6a608fcc444d5405c29e81428efe349370c6d8cc4ba72dca26272bec1c
```

The report contains the consolidated balance sheet on PDF pages 77–79. Source capture does not yet review, declare, map or normalize those values.

### Non-filing evidence

Two source documents were retained for each of:

```text
000693.SZ / FY2018
600090.SH / FY2021
600146.SH / FY2021
000038.SZ / FY2022
000976.SZ / FY2023
000622.SZ / FY2024
601028.SH / FY2024
```

The bytes are candidates for QB-S2-NONFILE-01 review and declaration construction. Capture alone does not prove that each pair satisfies `INITIAL_NONFILING_PROOF` plus `TERMINAL_CONFIRMATION`.

In particular, the retained `601028.SH` terminal document proves voluntary termination/delisting but does not itself state that FY2024 remained unfiled through termination. The pure declaration constructor must reject it if the reviewed evidence cannot satisfy the frozen terminal assertion. No search absence may repair that gap.

## Authority boundary

The candidate proves official source-byte retention only. Receipt flags correctly keep all of these false:

- official evidence reviewed;
- non-filing declarations constructed;
- financial statement extracted;
- financial availability qualified;
- revision closure complete;
- S2B exact cover complete;
- decision grade and deployment authority.

Generator commit `7276c69` is external provenance and is not embedded in the receipt schema.

## Next safe work

1. implement the already READY pure QB-S2-NONFILE-01 Builder operation;
2. review source pages/excerpts and construct only declarations that satisfy the exact initial/terminal and availability contracts;
3. freeze and implement `000046.SZ` official consolidated-balance extraction with units, presentation and lineage;
4. rebuild S2B only after the target equation can be supported:

```text
96,537 = 96,515 provider-covered + 1 official backfill + 21 accepted non-filing terminal keys
```

The equation remains provisional until formal S1 authority exists.
