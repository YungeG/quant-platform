# P00-CON-02 Contract Proposal (human rendering)

- **Proposal:** `p00-contract-v2`
- **Status:** `approved`; both required repository-owner approvals recorded.
- **Scope:** a narrow successor proposal to approved `p00-contract-v1`

Machine proposal and structural guard:

- `foundation/tests/fixtures/architecture/p00-contract-v2.json`
- `foundation/tests/architecture/test_p00_contract_v2.py`

The JSON is a frozen proposal and hash-binding record whose only mutable fields were `status` and `approvals`. Both required repository-owner approvals are recorded from explicit owner authorization: Platform owner `YungeG` at `2026-08-14T04:03:59.553705Z` and Backtest owner `YungeG` at `2026-08-17T01:23:06.083983Z`. The guard verifies this exact approved state.

## Narrow supersession

On externally evidenced approval, P00-CON-02 supersedes **only** these `p00-contract-v1.downstream_unblock_conditions` machine keys:

| Human work package | Frozen JSON key |
| --- | --- |
| `P00-LEG-01` | `P00_LEG_01` |
| `P00-CUT-01` | `P00_CUT_01` |

`P00-LEG` and `P00-CUT` are gate-family shorthand only.

The replacement condition is:

```text
The existing immutable static historical capture and retirement receipt are
sufficient P00-LEG-01/P00-CUT-01 evidence. Hermetic replay is not required and must not be a P00-PLAT prerequisite.
```

This is a clarification of the legacy gate, not a replay claim. The static evidence remains classified `static_historical_evidence`; that evidence classification is distinct from a work-package lifecycle status. It is not Backtest canonical evidence, a callable adapter, economic authority, or a parity proof.

## Preserved approved decisions

P00-CON-02 does not modify P00-CON-01's Envelope v1 vector, `ArtifactRef`, Backtest public seam, lock/source rules, ownership map, or the approved fixture:

```text
foundation/tests/fixtures/architecture/p00-contract-v1.json
sha256:aebb1be1894d739b06856e012e4343d7835fc1ed0306d8c28a4bfb1d8025b782
```

The proposal fixture binds the current baseline capture and retirement receipts by path, classification, and SHA-256. The approved P00-CON-01 fixture is not edited by this work.

## Recorded approval

Both repository owners approved exactly:

```text
P00-CON-02 accepts the existing immutable static historical capture and
retirement receipt as sufficient P00-LEG-01/P00-CUT-01 evidence. Hermetic
replay is not required and must not be a P00-PLAT prerequisite. All other
P00-CON-01 decisions remain unchanged.
```

Approved target:

```text
foundation/tests/fixtures/architecture/p00-contract-v2.json
sha256:5ad32e59e56e6f46904af22dafdd256d84ad6332389fd4bf0b709c8c83c2f573
```

The approval closes only the static-legacy clarification. It does not require hermetic replay and does not authorize runtime or Backtest seam changes, fabricated receipts, or weakening any other P00-CON-01 decision.
