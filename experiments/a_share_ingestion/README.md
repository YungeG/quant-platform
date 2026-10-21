# Project-local A-share ingestion

Local ports of the inspected daily collector, SW industry collector, CSV importer
and schema initializer. No `operations.*` imports, external project configuration,
external interpreter or external project's source code are required at runtime.
This is a data utility, **not** the D009 real Adapter or research Reader.

## Dependencies

The required third-party libraries are declared in `requirements.txt`. They must
be installed in **this project's** environment, after installation is authorized:

```bash
uv pip install --python .venv/bin/python -r experiments/a_share_ingestion/requirements.txt
```

The local project environment has been validated with DuckDB 1.5.4, pandas 3.0.6
and Tushare 1.4.29; these direct dependencies are pinned in `requirements.txt`.
Existing installed package versions and the workspace `pyproject.toml`/`uv.lock`
were preserved. A separately authorized one-stock/one-day engineering smoke passed
using a bounded Xiaodefa HTTP driver and these local normalization/import modules.
That capture's one-request allowance is exhausted. The CLI transport integration
below is validated offline, not by issuing another real request.
Missing libraries produce an explicit refusal on execution. Help and plan mode
use only the standard library. No credentials are copied. Official mode reads
`TUSHARE_TOKEN`; explicit Xiaodefa mode reads `TUSHARE_PROXY_TOKEN` or the explicitly
supplied mode-0600 token file. Proxy credentials never fall back to official mode.

## Plan-first CLI

```bash
.venv/bin/python -m experiments.a_share_ingestion --help
.venv/bin/python -m experiments.a_share_ingestion daily \
  --data-root /path/to/owned-stage --start-date 20240101 --target-date 20240105 \
  --limit 1 --max-requests 2
.venv/bin/python -m experiments.a_share_ingestion industry \
  --data-root /path/to/owned-stage --start-date 20240101 --end-date 20240105 \
  --max-requests 10
.venv/bin/python -m experiments.a_share_ingestion init \
  --data-root /path/to/owned-stage --db /path/to/new.duckdb
.venv/bin/python -m experiments.a_share_ingestion import \
  --data-root /path/to/owned-stage --db /path/to/new.duckdb --table market
```

These commands are **plan-only**: no network, library imports, directory creation,
CSV reads or DB connections. Actual I/O requires `--execute`; the importer also
requires `--replace`. Flags are safeguards, **not human authorization**, source
qualification or a fresh budget. Real operations still need a separately accepted
finite scope, representative smoke, cumulative budgets and stopping conditions.
The logical API-call cap includes failed/retried calls. Official SDK-internal HTTP
behavior remains separate; Xiaodefa enforces an additional shared physical HTTP
cap, including failures and concurrent calls, with no automatic retry/failover.
Success summaries record the transport, exact endpoint and request counts; these
are local diagnostic metadata, not immutable raw-response captures or authority.

## Explicit Xiaodefa transport (ADR0010)

```bash
.venv/bin/python -m experiments.a_share_ingestion daily \
  --transport xiaodefa \
  --proxy-token-file "$HOME/.config/ai-crypt/xiaodefa-token" \
  --symbols 000001.SZ --limit 1 --max-requests 1 \
  --start-date 20240102 --target-date 20240102 \
  --proxy-max-response-bytes 65536 \
  --data-root /path/to/owned-stage
```

This remains **plan-only**: it does not even open the credential file. Do not add
`--execute` to reuse the exhausted smoke approval. A new live scope must be accepted.
`--symbols` bypasses the whole-market `stock_basic` call; it does not establish
ST/listing/PIT eligibility. Without it, the legacy listed-stock selection remains.

Only `https://fast.xiaodefa.cn/` (default) and `https://tt.xiaodefa.cn/` are accepted
by `--proxy-endpoint`. One client is bound to one endpoint; there is no automatic
fallback, and changing the endpoint requires a new capture/identity. Token values
appear only in the `x-api-key` header, never request bodies/URLs/metadata/errors.
File credentials must be regular, owner-owned, mode 0600, stable during reading,
and reached without following symlinks. Nonblocking open and descriptor checks
precede content reading, so a path swapped to a FIFO is rejected without reading.
An explicit bad file never falls back to another credential. Official mode rejects
proxy credential/endpoint options.

Redirects, malformed HTTP parser errors and provider error text are redacted.
Credential echoes are checked both in raw bytes and decoded JSON (including escaped
strings), and credentials are rejected in request parameters/bodies. Concurrent
responses are validated against request-local status, not shared diagnostics.
`--proxy-timeout` defaults to
15 seconds (maximum 60); `--proxy-max-response-bytes` defaults to 1MiB (maximum
16MiB), independently limiting compressed and decoded bytes. Defaults are technical
refusal bounds, **not acquisition permission or a resource-budget grant**. Only the
five ingestion APIs used here are supported; this is not a generic provider registry.
Optional proxy count/has_more fields do not override actual response items.

Paths are local to the explicitly supplied `--data-root`:
`market_data/`, `static/`, `fundamentals/`, `extended/`, `industry/`, `logs/`,
and `download_progress_tushare.json`. No old `/srv` root is silently selected.
The DB path is always explicit. Import replacement is one transaction and rolls
back on failure; no usable market rows is a refusal, not an empty replacement.
The default imported table is market; other copied legacy import functions are
available only through an explicit table choice.

DB configuration starts at 4 threads / 2GiB managed memory / no spill, with native
OpenBLAS threads set to 1 before numerical imports. This is **not** a 6GiB process
RSS enforcement mechanism; real execution requires a host memory limit/monitor
and the accepted system-headroom policy. No host limits were changed by the port.

## Preserved semantics and limits

- Daily collection calls `daily`, converts volume x100 and amount x1000, and uses
  the original standard CSV columns. Import preserves the old Source marker and
  local import-time UpdateAt; neither is historical Provider Availability.
- Initialization creates both the base and industry tables in a fresh database;
  it no longer assumes a pre-existing external lake schema.
- CSV input is read as text before table-specific conversions, preserving
  leading-zero IDs and non-null YYYYMMDD dates in otherwise nullable columns.
  This fixes a reproduced local import issue; it does not repair retained data.
- Existing daily CSV dates use keep-last merging. These mutable CSVs do not
  preserve an immutable historical revision chain.
- Industry collection preserves SW2021 taxonomy, Y/N member queries, half-month
  daily windows, metadata and deduplication. Fetch times are local acquisition
  evidence, not proof of historical publication.
- The legacy numeric coercion/DOUBLE storage, current listed-stock selection,
  optional ST exclusion and effective-member logic are not PIT qualification.
- Historical availability, joint coverage, source alias/consumption, immutable
  refs and Reader admission remain unresolved. D009 stays NOT_READY.
- No delisted-stock collector was invented: that producer has not been located.
- Import modules are side-effect free; the command dispatcher catches failures
  without printing SDK response/error prose or credentials.

## Copied sources

The original files remain unchanged. Copies remove project-specific imports,
credential-file lookup and import-time logging/config I/O, add plan/execute and
replacement gates, and localize dependencies. Half-month date windows use the
standard library; API/CSV transformations retain the inspected logic.

| Original | SHA256 |
| --- | --- |
| `cycle-rotation-platform/operations/apps/fetch_data_tushare.py` | `3d8365f842fb3fc8efa14e838cc7bfdada7d3d7c0483bb769633d7d4ccdf0acc` |
| `cycle-rotation-platform/operations/apps/fetch_industry_data_tushare.py` | `8bff29655b1366d7649b25f9c96cbda7ae0a3921b07f2e11fd532bde46cc4805` |
| `cycle-rotation-platform/operations/apps/import_to_duckdb.py` | `ccde07547b162362f280d608c102c52bb9f19bea6551a583889934066b873147` |
| `cycle-rotation-workbench/scripts/init_duckdb.py` | `1cff3a5ea34f697740e9d8be5bd4016cf1dc5b1326779d06ad7a5b9c6d5c2412` |

## Offline validation

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/research/test_a_share_ingestion.py \
  tests/research/test_a_share_ingestion_proxy.py -q
```

Tests use spies, real pandas transforms and temporary synthetic DuckDB databases.
Daily and industry fake API responses exercise collection → CSV/metadata → import,
including failed-import rollback. No live API or retained market source is used.
The real SDK constructor is checked offline with a synthetic token and HTTP
blocked; it must not write home credentials. Proxy tests use only synthetic keys,
fake HTTP and temporary files, including the single-stock CLI route; they never
read the host's actual proxy token or contact a live endpoint. These engine/SDK checks are skipped
explicitly in environments missing the local libraries; a skip is a validation
gap, not a passing check.
