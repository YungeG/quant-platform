# Dependency alignment — 2026-09-21

Status: **candidate validated; original-worktree cutover blocked pending quiescence**.

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

Original Platform and all pre-existing worktrees/environments remain in place. Preservation refs were created before work. A private recovery directory is retained at `/home/ygguo/agent-projs/ai-crypt/.dependency-alignment-safety-20260921`.

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

## Cutover condition and rollback

At 2026-09-21 14:13 +0800, D002 and D004 metadata showed idle, but original-worktree Pi processes still existed; PID 2357835 was not accounted for by those task bindings. No process was stopped/reloaded, no real task was edited or redispatched, and no original environment was synchronized.

Proceed only after **all** original-tree writers and Python jobs are quiescent and before/after refs/dirty files are rechecked. Then integrate the validated candidate without discarding the original tracked or untracked work, synchronize the same lock into the original environment, and rerun the two alignment checks plus the smallest behavioral smoke. Do not recreate the existing directory by copying a clean worktree over it. Do not hot-reload an active Pi or research process.

Until then, the original `.venv` intentionally remains at `f73d068d`; commands requiring the new public CN preparation must use the isolated candidate explicitly. The candidate does not automatically contain D004's untracked scripts/data. A future cutover must preserve these files, not mistake their absence from Git for permission to drop them.

Rollback must preserve all user changes: retain the old environment and start refs, and reverse only this upgrade's configuration/commit on a quiescent tree. No `reset --hard`, `clean`, worktree deletion, or data movement is authorized by this receipt.
