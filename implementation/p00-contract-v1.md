# P00-CON-01 Contract Receipt (markdown rendering)

Receipt: `p00-contract-v1`

Package: `P00-CON-01`

Status: `approved`

Approvals recorded for both repository-owner roles at `2026-08-12T14:15:04Z` by explicit workspace-owner authorization.

Sole machine-normative archival artifact:

- `platform/foundation/tests/fixtures/architecture/p00-contract-v1.json`

Guard:

- `platform/foundation/tests/architecture/test_p00_contract.py`

Execution command:

- `cd platform && uvx --python 3.13.5 --from pytest==8.4.2 pytest -q foundation/tests/architecture/test_p00_contract.py`

The JSON receipt is immutable. Its `inspection_snapshot`, `evidence_anchors`, and historical `guard_spec` preserve archival inspection evidence only: the continuing guard is **not** that historical `guard_spec`. The local/archive-only guard neither resolves those paths nor reads sibling source, and it does not assert the absence of leaf locks. Current Platform design and local-only guard assertions carry the continuing interpretation; this does not claim that real `ArtifactRef`, Backtest, or Foundation integration exists.
