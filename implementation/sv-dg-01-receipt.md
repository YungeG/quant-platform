# SV-DG-01 decision-grade Validation acceptance receipt

- **Platform implementation revision:** `11a5ad4ca2873f747873ec899cecf23519dfb134`
- **Validation accepted revision:** `cd966d92dad2110af7d8b1bf580536f6c3cdb998`
- **Research accepted revision:** `1557ec1904de6f2a8f8a32c2f37ce038a0daa022`
- **Backtest fan-in revision:** `8de544e7794ee05b652355c9809b5454d7ace494`
- **Status:** ACCEPTED

## Accepted Validation behavior

Existing ValidationPolicy, ValidationPlan, CaseResult, ValidationReport, and public runtime interfaces remain unchanged. A Plan now selects exactly one accepted grade mode:

```text
("development",) | ("decision_grade",)
```

Mixed modes fail validation. Exact nominal type/schema dispatch selects V1 or V2 completed/analysis operations. Completed-v3 evidence requires decision grade and exact typed rebuild-verification/proof-publication refs. Analysis-v2 must match the completed publication, execution-result hash, metric profile, grade, and nominal version.

Backtest proof refs are verified at the Backtest/candidate boundary but are not copied into CompletedCaseEvidence or ValidationReport. A static-proof/version/link failure produces no ValidationReport and never falls back to V1.

The decision-grade fixture publishes a supported report for canonical `0.02392`, one trade, and threshold `0`, then replays without a second run or derivation.

## Verification

- focused Validation core/shell: `24 passed`;
- full Validation package: `55 passed`;
- root Validation + V2/V5 architecture gate: `68 passed`;
- fresh remote recursive clone at exact Platform/Validation revisions: `68 passed`;
- `uv lock --check`: passed locally and remotely;
- LSP and Ruff `E4,E7,E9,F,I`: clean;
- diff guards: clean;
- remote clone ended with empty `git status --short`.

## Exclusions

This receipt does not accept Promotion Admission@2 publication facts, whole-Platform decision-grade fan-in, proof decoding, grade synthesis, provider qualification, Shadow implementation, Live/deployment, or any Backtest change.
