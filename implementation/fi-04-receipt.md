# FI-04 whole-Platform decision-grade acceptance receipt

- **Platform golden revision:** `324f2fd08d8d9be4f4c32e222ee5bc63306ac81e`
- **Foundation revision:** `9d88ed67a84d06c558276f8bae2206b069bcec8f`
- **Research revision:** `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`
- **Validation revision:** `cd966d92dad2110af7d8b1bf580536f6c3cdb998`
- **Promotion revision:** `8e6dddf5da0494b57cca6990d5024fe4198e6b44`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Root `uv.lock` SHA-256:** `75a91665859490d03544066d0585bceec9b6dbe7156cf322b4cb67f95a6a420f`
- **Status:** ACCEPTED

## Whole-flow evidence

Integration v5 consumes the accepted Backtest canonical-v3 evidence through the existing Platform chain:

```text
BacktestCanonicalPublicationRefV2 / completed-v3
  result_grade = decision_grade
  exact typed durable-proof refs
→ AnalysisArtifactRefV2 / analysis-v2
  simple_period_return = 0.02392
  trade_count = 1
→ Admission@2 publication + analysis
→ singleton decision_grade ValidationReport = supported
→ PromotionEvaluation@2 = ELIGIBLE
→ PromotionDecision@2 = shadow_ready
```

Every V2 operation is selected only by exact nominal type/schema identity. Admission@1 and Admission@2 use their exact versioned event identities in the existing owner log. Platform validates typed proof refs at its boundaries but never decodes proof artifacts, duplicates them into Validation case evidence, synthesizes a grade, or retries through V1.

Whole-flow replay returns the same Candidate, Validation report, admission refs, Evaluation, and Decision. It creates no second provider run/derive or additional Research, Validation, admission, status, review, Evaluation, or Decision entry.

## Protected contract hashes

```text
BT-PORT-01  5f9971573154a92aa83f6ac6edbb36024721ad5b54a35f0f14414c1e393f69fa
BT-PORT-02  8884f7595a62995eaf296a7ad5f0518745146905da3e2fd69a92587a9423c4a8
Integration v2  4d6c764b6e0b6374daab462b8b74ce8c9f75b73b68d96979d3e7d3a99bd441bb
Integration v3  2f826867f54f8c083f9d3574702a8ccaac8c7ebea5e64f57fff791a6b0e500d9
Integration v4  0f030a47ffb5ac3b64d40330ab72686e04e4e85feddec7d489c9ae34f5c7ece7
Integration v5  1bd5ec02c990b87521f26ef42f309dc4dadfe1a62a0739a649040a935e513695
```

## V5 leaf receipts

- [`V5-CON-01`](v5-contract-decision-grade-proof-v1.md)
- [`V5-PIN-01`](v5-pin-01-receipt.md)
- [`DG-ADM-01`](dg-adm-01-receipt.md)
- [`RP-DG-01`](rp-dg-01-receipt.md)
- [`SV-DG-01`](sv-dg-01-receipt.md)
- [`PG-DG-01`](pg-dg-01-receipt.md)
- [`DG-THIN-01`](dg-thin-01-receipt.md)

## Verification

- Full local Platform workspace at the golden revision plus accepted leaf-receipt commit: `359 passed`.
- Fresh remote recursive clone at exact Platform revision `324f2fd08d8d9be4f4c32e222ee5bc63306ac81e`: `359 passed`.
- The fresh clone verified every protected contract hash and the exact lock hash, passed `uv lock --check`, checked out every recorded submodule revision, and ended with empty `git status --short`.
- Backtest fan-in acceptance remains `2438 passed`; its revision descends from both the accepted model seam and durable-proof seam.
- Root, Backtest, Foundation, Research, Validation, and Promotion revisions are remotely reachable.
- Existing Integration v1-v4 behavior and release tags remain protected by the same full workspace suite and ancestry guards.
- LSP, pi-lens, Ruff `E4,E7,E9,F,I`, lock, and diff guards are clean.

## Exclusions

Integration v5 adds no provider qualification, trusted copied-tree origin, future durability guarantee, Platform proof decoder, grade synthesis, new metric or Validation method, ShadowSpec implementation, Shadow runtime, Live/deployment authority, RBAC, credentials, order routing, infrastructure, or Backtest change. `shadow_ready` remains evidence only.
