# Dependency alignment — 2026-09-21

Status: **activated in the original Platform worktree; post-cutover checks passed**.

## Scope and exact identities

- Candidate: `/home/ygguo/agent-projs/ai-crypt/platform-dependency-alignment`, branch `integration/dependency-alignment-20260921`.
- Preserved original Platform HEAD: `e802d8907770d42943a1d32dfe33ae802d480d27`.
- Remote Platform main verified with `git ls-remote`: `3fb91c9d1b4fc07b1d0c3e399fa6fdaf4327fd4f`.
- Target Backtest remote main: `8cc5b874c31c38a6ec7526d1dbf345b93998a39f`.
- The existing Platform upgrade `e3c49a6` changed only the submodule gitlink. This candidate also aligns all five Git-sourced packages, `uv.lock`, checked-out source, and the candidate's own `.venv`.
- Foundation `9d88ed6`, Research `c066624`, Validation `dad1198`, Promotion `8e6dddf` remain unchanged.
- Existing V1–V6 contract/receipt bytes are not rewritten. The old V6 root hashes are still checked against immutable Platform commit `2a9103dd9e4b8503658db88a17fbbf201c62d16e`; new fixture evidence names the current runtime pin instead of falsely claiming the old Backtest revision.

## Verification actually performed

All commands below used the candidate's `.venv` and temporary test outputs, not real strategy execution.

| Check | Result |
| --- | --- |
| New gitlink/source/lock/installed-cohort checks | old environment: 2 expected failures; candidate: 2 passed |
| `uv lock`; `uv sync --locked --group dev` | succeeded; five Git packages resolve to `8cc5b874` |
| Public CN provider two-session fills/fees/T+1/replay fixture | 1 passed, 33.38s |
| Public CN provider preparation/tamper rejection cases | 15 passed, 11.13s |
| Root default Platform suite | **466 passed**, 159.60s |
| Original D004 regime/risk/sector/capture unit tests with the new interpreter | **211 passed**, 1.48s |
| Active LSP | initial inaccurate JSON-fixture annotation repaired; subsequent probe had no findings but remained **inconclusive**, not a strict typecheck pass |

Root regression command: `uv run --locked --no-sync python -m pytest -q`.

Public CN fixture: from `backtest/`, use the candidate interpreter with `tests/runtime/providers/test_cn_a_share_development_provider.py::test_public_retained_two_session_roundtrip_owns_real_fills_fees_and_t1`. This verifies the accepted **000703 single-instrument development** route, not an arbitrary A-share portfolio or decision-grade strategy.

D004 compatibility used only four existing `tests/research/test_a_share_*` / capture unit-test files; it did not run market acquisition, a strategy study, OOS, or live execution. Its pytest cache was directed to the candidate tree.

## Protected local state and data discovery

All pre-existing source/data worktrees remain in place. Preservation refs were created before work. A private recovery directory is retained at `/home/ygguo/agent-projs/ai-crypt/.dependency-alignment-safety-20260921`. At cutover, the old Platform environment was moved intact to `cutover-20260921/venv-before-switch` beneath that directory; it was not deleted or overwritten.

- Original tracked Platform diff and path list retained.
- Original Platform 84 untracked files archived and compared byte-for-byte with `tar --compare`.
- KORU native implementation tracked diff plus 24 untracked files retained; archive compared against its source.
- Portfolio Phase 5 review retained separately.
- Portfolio `75d8f8a` and KORU `92925ea` histories were copied into preservation refs in the stable Backtest repository, so they are not solely dependent on linked-worktree submodule metadata.
- The 25,520-file A-share research data tree was **not** moved, cleaned, sampled, or fully backed up. Its independent backup status remains unknown. Do not remove it.

Archive SHA-256:

- `platform-untracked.tar.gz`: `aa181d902e2f793a5ab335fb88ad535edbab44d272f846380ea8de600e935009`
- `koru-native-tracked.patch`: `1c61851ec5c05faa464aa76adf656904385b025616bd19bb307144d64449d183`
- `koru-native-untracked.tar.gz`: `26ebd29fcb8899c829e3cfd459b76f0ba37a079482aca6c7ebd0d67b1cf830cc`
- `portfolio-review.tar.gz`: `2b887677c942a29ba71ae0e363bbc1c3e4306f5f668348a4f18a303d97f18519`

The original untracked `overall/research-data-inventory.md` is preserved and copied into this candidate for version control. Its update corrects the DuckDB location, identifies cross-worktree files, separates recorded coverage from newly checked file existence, and does not qualify data or promote old results.

## Separate portfolio continuation — NOT completed by this upgrade

The existing portfolio plan and its accepted Phases 1–4 remain authoritative. Phase 5 review rejected `067e033`; repair `75d8f8a` addresses reviewed areas but a subsequent acceptance was not found and was not inferred. Phases 6 (multi-instrument profile) and 7 (public provider) remain separate gates.

Before rebasing or merging that branch:

1. Freeze the published `backtest_execution_input_bundle@7` meaning from `8cc5b874`; it is not the portfolio branch's V7 payload.
2. Inventory all in-progress schema registrations. **KORU WIP already registers schema 8**, so simply renumbering the portfolio path to V8 is not safe either.
3. Agree a collision-free additive public identity with the existing contract owner, without rewriting old artifacts or claiming an unreviewed version accepted.
4. Re-review the repaired Phase 5 against exact frozen fixtures, then proceed through the existing Phase 6/7 acceptance gates. Do not duplicate its already accepted kernel work or introduce a parallel return simulator.

This candidate neither changes that protocol nor enables unfinished portfolio/KORU code.

## Original-worktree cutover and rollback

The initial 14:13 +0800 inspection blocked cutover because Pi PID 2357835 was not accounted for by task bindings. After the user stopped Pi, the 14:29–14:30 recheck confirmed PID 2357835 and D004 PID 4037263 had exited. D002 PID 2814253 remained, but fresh matching metadata reported idle, no pending input and no active run; OS inspection found no descendants or Python jobs. This idle session was preserved, not stopped or reloaded.

Cutover was verified at 2026-09-21 14:41 +0800:

1. Original `main` fast-forwarded from `e802d89` to the validated merge `611b573b946706c40a2f71296919ef1a0c191c9c`; neither parent history was discarded.
2. `backtest` moved from `93d8a391` to its same-tree published merge `8cc5b874`. Its tracked source tree and complete pre-existing untracked-file set remained unchanged.
3. The original untracked data inventory was moved intact to `cutover-20260921/untracked-inventory-before-merge.md` before Git installed the versioned updated inventory. It still matches `original-research-data-inventory.md` byte-for-byte.
4. The old `.venv` was preserved at `cutover-20260921/venv-before-switch`; a fresh environment was built at the original final path with `uv sync --locked --offline --group dev`. This avoided copying an environment with another worktree's editable paths or shebangs.
5. Actual `direct_url.json` provenance for all five installed Git packages now equals `8cc5b874c31c38a6ec7526d1dbf345b93998a39f`; `prepare_cn_a_share_development_backtest` is callable from `platform/.venv`.
6. In the original environment, the two alignment checks, public binding fixture and V6 independent-OOS fixture all passed (**4 passed**, 5.53s); D004's same four unit-test files passed again (**211 passed**, 1.29s). These are tests, not a new strategy study or live run.

Preservation was checked after cutover: original README SHA-256 remains `8cae2e8703ff7a6b23f681138e05c4118534432e6835b742b510360dcd68b03b`; the other 83 originally untracked files still compare equal to the recovery archive; the old inventory is retained; the four workspace module sources are clean. A remaining submodule dirty indication can reflect its already-existing untracked files; none were cleaned.

No Waggle task was accepted, edited or redispatched. No Agent or research process was force-stopped, hot-reloaded or restarted. For subsequent commands use `uv run --locked` from the original `platform` directory; do not invoke the preserved old environment as though it matched the new lock.

Rollback must preserve all user changes: retain the old environment and start refs, and reverse only this upgrade's configuration/commit on a quiescent tree before restoring its matching environment. Do not overlay a clean worktree over D004's untracked scripts/data. No `reset --hard`, `clean`, worktree deletion, or research-data movement is authorized by this receipt.

## Worktree retirement follow-up

The user separately authorized directory organization after the cutover. It completed on **2026-09-22**. The preceding sections remain the original 2026-09-21 cutover record: statements there about worktrees remaining and independent backup coverage being unknown describe that earlier inspection, not the final directory state. The original test results were not rerun or upgraded by this cleanup.

### Retired worktrees

All paths below are relative to `/home/ygguo/agent-projs/ai-crypt`. Only the worktree directories and their registrations were removed; their branches and committed histories were retained.

| Retirement date | Directory | Retained branch |
| --- | --- | --- |
| 2026-09-21 | `platform-a-share-integration` | `integration/a-share-research` |
| 2026-09-21 | `platform-early-report-retry` | `worker/early-report-diffusion-retry` |
| 2026-09-21 | `backtest-koru-vnext-contract-01` | `design/koru-vnext-contract-01` |
| 2026-09-21 | `backtest-koru-vnext-contract-02` | `design/koru-vnext-contract-02` |
| 2026-09-21 | `platform-dependency-alignment` | `integration/dependency-alignment-20260921` |
| 2026-09-22 | `platform-strategy-ideas` | `research/strategy-ideas` |
| 2026-09-22 | `platform-oil-polyolefin` | `research/propane-pdh-authority-v1` |
| 2026-09-22 | `platform-a-share-strategy` | `research/qb-nonfiling-effective-boundary-v1` |

The first five recovery archives and their verified `SHA256SUMS` remain at `/home/ygguo/agent-projs/ai-crypt/.dependency-alignment-safety-20260921/retirement-20260921-NQBHMF/`. The last three complete non-cache working trees, Git administrative metadata, and patches are retained at `/srv/bcache-8t/ygguo/ai-crypt-backups/organization-20260921-hW0Sw8/`. That second directory also contains `DIRECTORY-INDEX.md`, `ARCHIVE-CATALOG.tsv`, per-directory checksums and verification records. Its name retains the task's start date; completion and backup verification occurred on 2026-09-22.

Before removal, process/installation references and shared Git ownership were checked, recovery archives were compared with their sources, and removal was exercised in a temporary repository with a populated submodule. The three A-share strategy gitlink changes referred to commits already contained in the stable module histories; their exact patch was archived rather than applied to the current Platform.

### Preserved state and verification boundaries

- Foundation `cf6f687` was copied into the stable `platform/foundation` repository under `preservation/retired-dependency-alignment-20260921-cf6f687`, without changing its checked-out source. Backtest `8cc5b874` also has `preservation/retired-dependency-alignment-20260921-8cc5b874` in `platform/backtest`.
- The previously unanchored Backtest prototype `281e722b5500e32ed20cf0d323616ddd16dd074f` now has `preservation/orphan-platform-v5-prototype-20260922` and is included in the Backtest history backup. The ten stale Backtest worktree registrations were retained; **no `git worktree prune` ran**.
- Independent-disk snapshots of `platform-a-share-research` and `platform-sector-trend` passed source/archive comparison, before/after file-metadata and Git-status checks, and archive checksum verification. A representative CSV/Parquet sample was restored before the larger backups. Both original data directories remain in place; `platform-sector-trend` still owns the portfolio worktree's Git metadata. See the [updated data inventory](../overall/research-data-inventory.md#verified-independent-backups) for exact snapshot identities and exclusions.
- The three legacy independent repositories, Platform/Backtest uncommitted content, and root KORU audit/publication evidence were backed up without deleting their source directories. A real legacy history bundle was independently restored and connectivity-checked. These are recovery copies, not owner-log publication or research qualification; the separate local disk is **not an offsite backup**.
- KORU native/card4/research and the portfolio worktree remain. No process was stopped, code merged, strategy run, or full test suite executed by cleanup. The actively changing KORU formal-discovery tree did **not** receive a new consistency-verified full snapshot; copying its existing evidence package does not establish such coverage.
- Three historical documents were recovered into `research/`: [strategy ideas](../research/strategy-ideas.md), [BTCUSDT validation plan](../research/btcusdt-daily-tsm-validation-plan.md), and [prior-project data inventory](../research/prior-project-market-data-inventory.md). Original bytes remain in the backup. The archival note and A-share navigation path do not revalidate old capability, data or approval statements or authorize an experiment.
- The empty root files `=1.24`, `=2.0`, `=6.0` and the unoccupied root `.pytest_cache/` were archived before removal. The `backtest -> platform/backtest` link, root `.pi/`, and previous safety backups remain intact.

Recovery should begin in an empty staging directory: recreate worktrees from retained branches, then selectively restore files and patches. Do not overlay archived Git metadata on a live repository; its original worktree relationships and object-alternate paths must be checked. No further directory deletion or data movement is authorized by this follow-up record.
