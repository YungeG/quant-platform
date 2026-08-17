# Foundation implementation plan

- **Normative contract:** [Integration v1 §2–3](../../overall/integration-v1.md#2-identity-time-and-publication)
- **Mutable status authority:** [Roadmap §2](../roadmap.md#2-status-registry)
- **Module design:** [Foundation design](../../foundation/design.md)

Foundation is one deep local persistence module. Callers learn one storage interface; CAS layout, atomic staging, locking, receipt hashing, sequence allocation, clock checks, and prefix reconstruction stay inside it.

## Execution DAG

```text
Integration §3 log/clock contract ─→ PF-LOG-01 ───────┐
P00-DOM ArtifactRef + Envelope v1 ────────────────────┴─→ PF-CORE-01
accepted package closure + release gates ─────────────────→ P00-PLAT-01
```

`PF-LOG-01` is deliberately independent of Backtest and the missing Domain `ArtifactRef`. It produces a useful generic append/checkpoint result rather than scaffolding. `PF-CORE-01` adds exact artifact storage and the structural reader without changing the log interface.

## `PF-LOG-01` — generic append ledger and immutable checkpoints

### Outcome

A caller can append exact payload bytes to a named log, replay the same event idempotently, detect conflicting bytes, obtain an immutable checkpoint, and reconstruct a verified prefix through either that checkpoint or a `LogEntryRef`.

### Inputs

- Integration v1 receipt, entry-ref, checkpoint, hash, and governance-clock rules.
- One filesystem root and one injected UTC governance clock.
- No Domain or Backtest package.

### Module interface

One injected store dependency exposes only:

```text
append(log_name, event_id, payload_bytes) -> AppendReceipt
checkpoint(log_name) -> LogCheckpoint
entries(log_name, through=LogCheckpoint | LogEntryRef) -> tuple[LogEntry, ...]
```

The interface includes these caller obligations:

- `log_name` and `event_id` are canonical nonempty strings;
- `payload_bytes` are exact immutable bytes;
- callers never supply sequence numbers, receipt hashes, or governance time;
- `through` belongs to the requested log.

### Invariants

1. One cooperative same-filesystem global lock assigns contiguous global and per-log sequences.
2. `accepted_at` comes from the injected clock under that lock, is non-decreasing, and may repeat; sequence orders equal instants.
3. Append atomically commits one registry file, which is the durable append-time record. The separate clock state atomically records each issued checkpoint tuple and its time; monotonicity compares that checkpoint time with the latest accepted registry entry, avoiding a two-file append commit.
4. Receipt hashes bind all receipt fields except `receipt_hash`; `payload_source_hash` binds exact payload bytes.
5. Repeating `(log_name, event_id, identical bytes)` returns the original receipt. Different bytes for that event are `LOG_CONFLICT`.
6. A checkpoint binds an upper log sequence and head hash. Later entries never enter it, including equal-time entries.
7. `entries()` verifies the complete requested prefix before returning anything; no partial prefix is exposed.
8. No stale-lock deletion or automatic log repair exists.

### Failure precedence

Per operation, not as one artificial cross-operation list:

1. bad public arguments → `TypeError` or `ValueError`, before filesystem access;
2. unsupported root/filesystem → `UNSUPPORTED_FILESYSTEM`;
3. unavailable cooperative lock → `WRITE_LOCK_UNAVAILABLE`;
4. backward governance clock during append/checkpoint → `CLOCK_NOT_MONOTONIC`;
5. duplicate event with different bytes → `LOG_CONFLICT`;
6. malformed/truncated/hash-invalid existing prefix → `LOG_INTEGRITY`;
7. failed durable append/finalize → `LOG_PUBLICATION_FAILED` or `SNAPSHOT_PUBLICATION_FAILED`.

No failure is converted into a domain event, Backtest terminal, empty snapshot, or successful receipt.

### Implemented write set

- `foundation/pyproject.toml` — package metadata only; no leaf lock
- `foundation/src/crypto_quant_foundation/__init__.py`
- `foundation/src/crypto_quant_foundation/storage.py`
- `foundation/tests/test_log_core.py`

One production file is sufficient until a second implementation seam is proven necessary.

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with-editable ./foundation \
  pytest -q -p no:cacheprovider foundation/tests/test_log_core.py
```

The focused test must cover:

- first append, exact replay, and conflicting replay;
- contiguous global/log sequence and receipt-chain verification;
- equal-time ordering, backward-clock failure, and append-after-checkpoint without a two-file append commit;
- empty/nonempty issued checkpoints and immutable prefix reconstruction; forged tuples fail closed;
- wrong-log, future, forged, truncated, and tampered refs/checkpoints;
- failed append/finalize returns no partial success;
- production source contains no Research, Validation, Promotion, or Backtest vocabulary.

## `PF-CORE-01` — exact artifact CAS and structural reader

### Outcome

The same Foundation module stores and reads exact canonical Envelope source bytes by the Domain-owned `ArtifactRef`, while preserving `PF-LOG-01` unchanged. Its read path can satisfy the accepted Backtest structural reader seam; Backtest retains all semantic verification.

### Inputs

- accepted P00-DOM `ArtifactRef` and `ArtifactEnvelope` v1 public types;
- completed `PF-LOG-01`;
- Integration v1 artifact layout, publication, and failure rules.

### Interface added

```text
put(*, envelope: ArtifactEnvelope) -> ArtifactRef
read(*, ref: ArtifactRef) -> ArtifactReadResult
```

No schema registry, decoder registry, repository abstraction, or provider-specific adapter is added.

### Invariants

1. Validate the exact Domain Envelope type, canonical source bytes, content hash, and derived ref before finalization.
2. Stage and read back on the same filesystem, then atomically rename to the immutable digest path.
3. Exact duplicate bytes are idempotent; different bytes for an occupied ref are an integrity conflict.
4. A CAS object is addressable but not published evidence until its exact Envelope bytes appear in its designated owner log.
5. `read()` validates ref/path/source-byte agreement but never interprets Backtest artifact meaning.

### Failure precedence

1. bad public arguments → `TypeError` or `ValueError`;
2. unsupported root/filesystem → `UNSUPPORTED_FILESYSTEM`;
3. missing object → `ARTIFACT_NOT_FOUND`;
4. ref/Envelope/path/hash disagreement → `ARTIFACT_INTEGRITY`;
5. unavailable write lock → `WRITE_LOCK_UNAVAILABLE`;
6. failed staging/read-back/rename → `ARTIFACT_PUBLICATION_FAILED`.

### Additional write set

- `foundation/tests/test_storage_core.py`
- minimal additions to the existing Foundation public root and `storage.py`

### Acceptance

```bash
uvx --python 3.13.5 --from pytest==8.4.2 \
  --with ./backtest/packages/trading-domain \
  --with ./backtest/packages/market-data-contracts \
  --with ./backtest/packages/trading-kernel \
  --with ./backtest/packages/backtest-runtime \
  --with-editable ./foundation \
  pytest -q -p no:cacheprovider \
  foundation/tests/test_log_core.py foundation/tests/test_storage_core.py
```

Required evidence:

- canonical put/read and exact-byte replay through `ArtifactReadResult.source_bytes`;
- conflicting, tampered, missing, wrong-type/version, and ref/path mismatch cases;
- failed staging/read-back/finalize leaves no published artifact;
- owner-log publication requires exact Envelope source bytes and source hash;
- structural-reader conformance uses accepted public Backtest types without Backtest decoding;
- AST/import guard proves Foundation has no sibling implementation import or domain-specific projection.

## `P00-PLAT-01` — package and root-workspace acceptance

### Outcome

A clean checkout installs the accepted Foundation package and all Platform packages from one root workspace/lock, with Domain, Market Data, Trading, and Backtest pinned to one accepted lowercase 40-character SHA.

### Inputs

- completed `PF-CORE-01`;
- accepted P00-DOM/P00-BT package closure and SHA;
- approved P00-CON-02 and satisfied P00-CUT-01.

### Write set

- one non-package root `pyproject.toml` workspace coordinator;
- one root `uv.lock`;
- P00-PLAT acceptance receipt;
- no leaf lock.

### Acceptance

```bash
uv lock --check
uv sync --all-packages --locked
uv run --locked pytest -q foundation/tests
```

The receipt records the Platform revision, accepted provider SHA, root lock hash, executed commands, result counts, package hashes, public-import guards, and explicit exclusions. Path/editable sibling sources, copied locks, branch/tag-only pins, `PYTHONPATH`, retained venvs, caches, and leaf locks fail acceptance.

## Dependencies

| Type | Node/artifact | Why |
| --- | --- | --- |
| Contract | Integration v1 §3 | Freezes generic log, receipt, clock, and checkpoint behavior for `PF-LOG-01`. |
| Contract | P00-DOM `ArtifactRef` + Envelope v1 | Required only by `PF-CORE-01` artifact operations. |
| Evidence | accepted provider SHA and package closure | Required only by `P00-PLAT-01`. |
| Write conflict | Foundation public root and `storage.py` | One writer owns both Foundation nodes. |
| Write conflict | root `pyproject.toml` and `uv.lock` | Created only by `P00-PLAT-01`; no leaf may edit them. |

## Exclusions

- sample-consumption semantics or coverage decisions;
- evidence-status parsing/projection or freshness policy;
- Backtest decoding, hydration, retention, integrity, terminals, or metrics;
- schema/plugin registries, database, queue, object store, network filesystem, distributed writer, or stale-lock janitor.
