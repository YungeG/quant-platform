# Stage B prior-balance extraction/binding packet

**Status: `READY`**  
**Execution: prohibited by task; no repository or artifact changes made.**

## 1. Authority clauses

| ID | Source | Requirement |
|---|---|---|
| C1 | Current task; formal S2 packet `:187-205` | Consume exactly the preferred binding, S2B candidate-02, accepted S2A candidate-02 and accepted Stage A snapshot; reconstruct identities before deriving output. |
| C2 | Formal S2 packet `:79-148` | Derive `20,797 = 17,952 core + 850 S2A + 1,995 Stage A`; preserve frozen requirement hashes and period counts. |
| C3 | Formal S2 packet `:119-140`; revision-lineage plan `:224-240` | Retain every source revision. Row order, dates and `update_flag` are not selectors or supersession evidence. |
| C4 | Formal S2 packet `:207-243` | Exact additive cover is 2,845 keys; augmented member count is 99,382; formal S2 and every downstream authority remain false. |
| C5 | Formal S2 packet `:222-263` | Publish exactly three artifact members and modify exactly three Backtest files from base `0c00c82…`. |
| C6 | Formal S2 packet `:352-386` | Preserve failure precedence, fail atomically and emit no partial/reduced/empty downstream artifact. |
| C7 | Stage A snapshot and receipt | Bind snapshot `2bad8575…`, tree `7f853c02…`, receipt `89a8e968…`; exact required coverage is 1,995. |
| C8 | Existing hardened binding publisher `cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py:918-1002` | Scale the existing pinned-FD, no-follow, inode-verified, no-clobber publication pattern to three members. |

## 2. Ownership and exact write set

**Owner:** one Backtest writer.

**Base/worktree**

```text
base:     0c00c8266c2fe904e11f982979d804ff5d205700
branch:   research/qb-s1-s2b-prior-balance-binding-v1
worktree: /home/ygguo/agent-projs/ai-crypt/backtest-qb-prior-balance-binding
```

**Only permitted files**

1. `tools/acquisition/cn_a_share_quality_bband_s1_s2b_prior_balance_binding_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_quality_bband_s1_s2b_prior_balance_binding_v1.py`
3. `tests/architecture/test_quality_bband_s1_s2b_prior_balance_binding_v1_boundary.py`

No predecessor, root export, Runtime, Trading, Strategy, lockfile or existing artifact changes.

## 3. Frozen inputs

### Preferred stage binding

```text
root:
.../tushare-s1-s2b-stage-bindings/2017-2025/20260827/v1-candidate-02
type:       quality_bband_tushare_s1_s2b_stage_binding_manifest
manifest:   sha256:c54bac9818a24688699aa585e49e91bde64ddbaf3efa90e0aa18491ff9b86f5c
member:     stage-binding-manifest.json
bytes:      7,323
file SHA:   sha256:ba5abfc5fc592ceb88ce1cabc95ebbded24abe9a8b108e9f6a31c96a0cc0878c
```

### S2B candidate-02

```text
manifest:        sha256:e526416335016b9fd421e138655303673e76dc2bf6e2f53a6bb580904ed70d74
expected set:    sha256:8c679397ff7ecfe67e0bbf68951d9fa388de9f2adfaf53a4f8b5395b0cea2cf6
official cover:  sha256:f245ebd560bb15644b1b072d277d3847d3477e7125677bd2e683e5a7c0636907
files:           4
root bytes:      97,030,990
```

| Member | Bytes | SHA-256 |
|---|---:|---|
| `provisional-expected-set.json` | 6,587,372 | `55c4ecdee60e77feec3d2ee8c4d8da5b16a4e6a1e07bf2acc49a08669b8d1a29` |
| `provider-rows.jsonl` | 90,363,445 | `f4ed00c232930e1067c2796f7e5c3622397e8649e1afa0d5ae8730c964cf7abe` |
| `official-coverage.json` | 17,755 | `a0971482128b6e4e2f0bcdbdbb10f1102211974fd98157c0185ec25fc08e5b3b` |
| `extraction-manifest.json` | 62,418 | `74c60758f4b6eb9534900f868bdef444e5891ad6b4eee996e6713eb2e8ea876f` |

### Accepted S2A candidate-02

```text
snapshot:             sha256:4e6574363c36f6cebe7f0ad46585a3a9e31b623546240196a2b8bcf55ec57160
content tree:         sha256:3316ea2f6c71f092f5bd803aad6731039b2bc6956c7f176c67183ecaded3e199
provenance:           sha256:fb1bfdc0646988d4881bb8a7c1abef61ebce91f46844b6cc83eb6925dc560e09
snapshot file:        69,608 / sha256:f0f1d394e98b298d0bb59990370c6ffb26ad70b89cb99aade3026f732aa1cba3
receipt file:         352,402 / sha256:30afdba09e0a04da1257489a7e13fcee062f41233006fe1d5d8bc33c748791a9
snapshot members:     245
regular files:        247
root bytes:           181,320,534
request hash:         sha256:1f6425374a2712c31f874f722fe99c31d102c252d40d255d0f8bf7e87dd57255
provider-requests:    sha256:921b08212a67329d08712558332c2466139fdff8cd6b7d1da5fe55544cf28902
root-trees hash:      sha256:f78c5e30403aeac09fabb8c42cacacfcb8b730a87ed57c66a5dc8ea2e70698a7
```

### Stage A 2011 candidate

```text
snapshot:          sha256:2bad85751bb5d6fb67509ea0119e61298f8b3083986c62bb3fe9fae35c0b34d9
content tree:      sha256:7f853c028026313ad1662214830b199ef9ff72fd7518e34b0bcbf1d751309f66
provenance:        sha256:452088d651f253b405e641b48b27f25aa0d2adcbe40af48c060ec3a924dc2dad
snapshot file:     907 / sha256:768810d6d5e68b47566629830a12e55400982af59cc97e0c20b7370893eefff9
receipt file:      4,679 / sha256:89a8e968ab5dae799a60de0973481e830e3189b8523bb3613e3a2d685c802081
response file:     1,168,904 / sha256:4eb227bfb7a978858f800b1eced93692faef4ddc96c940b8d7d97387e0ae4969
regular files:     3
root bytes:        1,174,490
request hash:      sha256:006acb5db4946a31ee474e4cec70f67f02a0d094c0016d8cf9e86b326a8d82e6
provider-requests: sha256:9c2bdb291bda9a3c0bc67d98a84e111fc59eef5a710582f907252013bbd218df
root-tree hash:    sha256:ee80ae157b2bae7716fdcf38cbe37fb479fa3c5eec4a4b2d1356d6c86fedebf4
```

## 4. Before/after flow

### Before

```text
formal-S1/S2B binding ───────┐
accepted S2A 2012–2024 ─────┼─ no six-balance-endpoint binding
Stage A 2011 snapshot ───────┘
```

### After

```text
build_quality_bband_s1_s2b_prior_balance_binding_v1
  -> secure preflight of four input roots and output parent
  -> reconstruct and verify all input bytes/IDs
  -> validate upstream authority and unchanged S2B closure
  -> derive 20,797 prior requirements
  -> partition 17,952 core / 850 S2A / 1,995 Stage A
  -> retain and identify all 5,677 additive provider rows
  -> validate zero missing, extra, overlap or partition-conflict keys
  -> construct and freeze three canonical members
  -> atomic three-member publication
```

No existing builder is called and no input bytes are copied or rewritten.

## 5. Public operation and CLI

```python
build_quality_bband_s1_s2b_prior_balance_binding_v1(
    *,
    stage_binding_root: Path,
    s2b_root: Path,
    s2a_root: Path,
    stage_a_root: Path,
    output_dir: Path,
) -> dict[str, object]
```

CLI contains exactly:

```text
--stage-binding-root
--s2b-root
--s2a-root
--stage-a-root
--output-dir
```

No defaults, environment discovery, network, credentials, “latest” lookup or fallback roots.

## 6. Symbol plan

| Symbol | Responsibility |
|---|---|
| `QualityBbandS1S2bPriorBalanceBindingFailure` | Exact seven-code enum in §11. |
| `QualityBbandS1S2bPriorBalanceBindingError` | Carries enum and optional frozen stage-local reason. |
| `_FrozenFile` | Name, byte count and SHA-256 for fixed artifact members. |
| `_FrozenSourceIdentity` | Snapshot/tree/provenance/file identities, receipt type and exact root counts. |
| `_ReadMember` | Optional retained bytes plus observed size/hash. |
| `_LoadedSourceRoot` | Verified snapshot, receipt and reconstructed source-member bytes. |
| `_PriorRequirementSets` | Ordered all/core/additive/S2A/Stage-A requirement arrays. |
| `_PriorExtraction` | Ordered provider records, row IDs, key set and audit details. |
| `_strict_json` | Reject duplicate keys, invalid UTF-8 and nonfinite values. |
| `_canonical_json`, `_canonical_hash`, `_bytes_hash` | Frozen serialization/hash rules. |
| `_read_exact_member` | FD-relative, `O_NOFOLLOW`, regular-file, bounded exact read/hash. |
| `_open_exact_fixed_root` | Exact one-/four-file roots for binding and S2B. |
| `_load_stage_binding` | Validate `c54bac98…`, its authority overlay and all false downstream flags. |
| `_load_s2b` | Validate exact four members, IDs and preserved closure. Stream-hash the 90 MB JSONL. |
| `_load_source_root` | Validate exact snapshot-derived member set; rebuild and verify SourceSnapshot using existing bundle-builder primitives. |
| `_validate_upstream_authority` | Require formal S1 and exact S2B; reject any formal-S2/downstream authority. |
| `_derive_prior_requirements` | Return the exact five requirement partitions. |
| `_build_requirements` | Build the frozen requirements member. |
| `_provider_rows` | Parse exact provider envelope and 19-field row shape. |
| `_source_row_id` | Hash the exact source-bound row-identity preimage. |
| `_classify_duplicate_rows` | Count single/update-only/metadata-only/economic variants without selection. |
| `_extract_prior_rows` | Scan relevant terminal leaves, retain all matching revisions and audit all extras. |
| `_validate_prior_closure` | Enforce the two equations and zero missing/extra/overlap/conflict keys. |
| `_build_manifest` | Construct only the frozen manifest schema. |
| `_output_parent_components`, `_open_output_parent`, `_verify_visible_output_parent` | Secure output traversal. |
| `_rename_noreplace_at`, `_same_inode`, `_readback_matches`, `_atomic_publish` | Durable no-clobber three-member publication. |
| `_build_preflighted` | Global failure-precedence orchestration. |
| `_parse_args`, `main` | Exact five-path CLI. |

Public `RawSourceMember`, `SourceSnapshotProvenance`, `freeze_source_snapshot` and `verify_source_snapshot` may be reused. Private predecessor modules must not be imported.

## 7. Requirement derivation

```text
20,797 prior endpoints
= 17,952 existing S2B balancesheet_vip keys
+ 850 accepted-S2A additive keys
+ 1,995 Stage-A additive keys

99,382 augmented statement members
= 96,537 existing S2B members
+ 2,845 additive prior balances
```

All 17,952 core references are existing P/provider keys; O and N core-prior reference counts are both zero.

| Period | All requirements | Core | Additive |
|---|---:|---:|---:|
| 20111231 | 1,995 | 0 | 1,995 |
| 20121231 | 2,034 | 1,987 | 47 |
| 20131231 | 2,053 | 2,027 | 26 |
| 20141231 | 2,143 | 2,035 | 108 |
| 20151231 | 2,224 | 2,125 | 99 |
| 20161231 | 2,434 | 2,205 | 229 |
| 20171231 | 2,612 | 2,404 | 208 |
| 20181231 | 2,635 | 2,577 | 58 |
| 20191231 | 2,667 | 2,592 | 75 |

Frozen hashes:

```text
all requirement list:
  sha256:25c51af2a2f6423628e45ad9a53a61f49abce56e94ab10fd99d97b37fa55f70d
all member keys:
  sha256:1a8c67951afffef40913eef9a09ed9c2aa15dc16163a6dca277fa266e26ee23a
core requirement list:
  sha256:ca92075c42cb2c671067765a18aa6141deb037e6bb83ec5f906531230c93fd85
core member keys:
  sha256:f014f802696a51a3c555bc23dd06bc175b3ec40d96a54db9f29e45c42469cd65
additive requirement list:
  sha256:1f3e1b7f235b7eb44af41e547312d88c7cc51acf609faeb9edde9cade49b0410
additive member keys:
  sha256:22df5bc4326477e0f4a3ff4da69a8a9681d7b7e0065c59f9d98b38179546918e
S2A requirement list:
  sha256:7cb4cd30074489cd0d11659ed917511ad4597ea21e7b5cdaaba621f64ea285f9
S2A simple keys:
  sha256:3105da5d6545d147c569f9d7319a9c265d68f187a877fb9861d790affbe9dc5a
Stage-A requirement list:
  sha256:a796d90e6b6b29368854207f7a4a85e16cc7bd8a28d7de93f04e90866c139a68
Stage-A simple keys:
  sha256:5b89864342028b6485ba38d170b52edb9e2df312e6615c35047407679406f0b5
```

## 8. Exact output schemas and identities

Candidate root:

```text
.../tushare-s1-s2b-prior-balance-bindings/
  2017-2025/20260827/v1-candidate-01
```

Serialization:

```text
JSON: ensure_ascii=false, allow_nan=false, sort_keys=true,
      separators=(",", ":"), UTF-8, no trailing newline
JSONL: one canonical JSON object plus "\n" per row; final row has newline
IDs: sha256(canonical body excluding the ID field)
```

### `prior-balance-requirements.json`

Top-level exact fields:

```text
type
schema_version
inputs
derivation
accounting
hashes
requirements
requirements_id
```

`requirements` stores only the 2,845 additive members; the 17,952 immutable core references are rederived and hash-bound rather than duplicated.

Each requirement is exactly:

```text
{
  api_name: "balancesheet_vip",
  instrument_id: {
    type: "instrument_id",
    venue,
    stable_key
  },
  period,
  required_by_screen_dates
}
```

Ordering: `(instrument_id.venue, instrument_id.stable_key, period)`.

```text
requirements_id:
  sha256:226c7f1e5e678e1d8b35eca4a52a7427030b83605088199bbb14a297020e1a6e
bytes:
  486,611
file SHA:
  sha256:b51724cc10ce8fb2556ed59bb75e654a7dfff60f1a142ae0abf2bd7eede357cb
```

### `prior-balance-provider-rows.jsonl`

Each line is exactly:

```text
{
  type: "quality_bband_prior_balance_provider_row",
  schema_version: 1,
  source_row_id,
  source_role: "ACCEPTED_S2A" | "STAGE_A_2011",
  source_snapshot_id,
  api_name: "balancesheet_vip",
  instrument_id,
  provider_code,
  period,
  source_member_key,
  source_row_index,
  row
}
```

`source_row_id` is the canonical hash of:

```text
{
  type: "quality_bband_prior_balance_source_row_identity",
  schema_version: 1,
  source_role,
  source_snapshot_id,
  source_member_key,
  source_member_content_hash,
  source_row_index,
  api_name,
  field_set_hash,
  row
}
```

19-field-set hash:

```text
sha256:478395530452a41e1629230ecfae47b60010660f812052bd72030eb21e88c1ef
```

Row order:

```text
instrument_id.venue
instrument_id.stable_key
period
source_role
source_member_key
source_row_index
source_row_id
```

```text
rows:          5,677
keys:          2,845
surplus rows:  2,832
row-ID hash:   sha256:1418102e92a50c28b379751fdc012af4f6751b90dc420f1b2711abf4f3fd63b3
bytes:         4,237,509
file SHA:      sha256:2b83d008ce3783f10e0a4e505e3cf165baa04baba885e6e1f4d9fe54345ae4bc
```

### `prior-balance-binding-manifest.json`

Top-level exact fields:

```text
type
schema_version
backtest_base_commit
inputs
requirements_id
source_extractions
closure
preserved_s2b_members
output_members
flags
limitations
manifest_id
```

The nested `inputs`, `source_extractions`, `closure`, `preserved_s2b_members`, `output_members`, `flags`, and duplicate profiles contain the exact identities and counts frozen in this packet.

```text
type:
  quality_bband_s1_s2b_prior_balance_binding_manifest
manifest_id:
  sha256:1b34a72179420bd0da6ca336d0ee6a46c039177117c23993c79afed2e888d674
bytes:
  19,299
file SHA:
  sha256:f5c4c2f83352f68948e31a9cb049d8dfba20e6e12bcd9d6adc8e37152fdee124
```

## 9. Revision and duplicate evidence

### Accepted S2A extraction

```text
relevant roots:              8
terminal leaves:             42
terminal rows scanned:       67,907
selected keys/rows:          850 / 1,698
single-row keys:             2
duplicate keys:              848
update-flag-only duplicates: 846
economic conflicts:          2
maximum rows/key:            2
extras:                      66,209 rows / 36,218 keys
```

Legacy extraction proof remains:

```text
bytes:        1,030,659
SHA-256:      sha256:704ada4176dbdd1d8f8f3f901651b57e13223c65ad3599a1f2e2d06928116f3c
row-ID hash:  sha256:cb0db295e029bfd3dc3bcf901c89ebcbd9c86d67de7f60e37c1f945689b5559e
```

Economic conflicts, both rows retained:

| Key | Source indexes / new row IDs | Economic differences |
|---|---|---|
| `xshe:002776 / 20151231` | `3075` → `4720adac…`; `4455` → `badaa535…` | cash, assets, liabilities, both equity totals, liabilities+equity |
| `xshg:601608 / 20121231` | `925` → `698320a6…`; `2754` → `29096576…` | assets, liabilities, both equity totals, liabilities+equity |

### Stage A 2011 — all duplicate counts

#### Entire physical source

```text
rows / keys:                 6,435 / 3,283
single-row keys:             131
duplicate keys:              3,152
revision-surplus rows:       3,152
update-flag-only duplicates: 3,146
metadata-only revisions:     2
economic conflicts:          4
maximum rows/key:            2
```

#### Required 1,995-key logical extraction

```text
rows / keys:                 3,979 / 1,995
single-row keys:             11
duplicate keys:              1,984
revision-surplus rows:       1,984
update-flag-only duplicates: 1,978
metadata-only revisions:     2
economic conflicts:          4
maximum rows/key:            2
```

#### Audited extras

```text
rows / keys:                 2,456 / 1,288
single-row keys:             120
duplicate keys:              1,168
update-flag-only duplicates: 1,168
metadata/economic conflicts: 0 / 0
provider codes:              1,265 SH/SZ + 23 BJ
```

All six non-update-only 2011 revisions are retained:

| Key | Kind | Source indexes / row IDs | Differences beyond `update_flag` |
|---|---|---|---|
| `xshe:000713 / 20111231` | economic | `815` `19776eb3…`; `3528` `93bfe4b8…` | `f_ann_date`, liabilities, both equity totals |
| `xshe:002052 / 20111231` | economic | `2070` `d0b40add…`; `6425` `af0d2ac3…` | `f_ann_date`, liabilities, both equity totals |
| `xshe:002113 / 20111231` | metadata-only | `1255` `d487cf31…`; `6426` `10297dd4…` | `f_ann_date` only |
| `xshe:002246 / 20111231` | economic | `2182` `749985a0…`; `6427` `c634ce12…` | `f_ann_date`, cash, assets, liabilities, equity, minority interest |
| `xshg:600287 / 20111231` | metadata-only | `2417` `7f9f018d…`; `5420` `c10978d1…` | `f_ann_date` only |
| `xshg:600319 / 20111231` | economic | `858` `92383390…`; `5448` `0a380ef8…` | `f_ann_date`, liabilities, equity, minority interest |

No branch may sort, filter, prefer or deduplicate on `update_flag`.

## 10. Exact flags and limitations

Flags:

```text
owner_approved_tushare_authority = true
formal_s1_qualified = true
provider_scope_exact = true
s2b_exact_cover_complete = true
prior_balance_provider_scope_exact = true
prior_balance_endpoint_cover_complete = true

formal_s2_qualified = false
financial_payload_complete = false
financial_scope_qualified = false
decision_grade_eligible = false
strategy_authorized = false
strategy_target_authorized = false
backtest_authorized = false
validation_authorized = false
deployment_authorized = false
```

Sorted limitations:

```text
FINANCIAL_PAYLOAD_AND_SCOPE_NOT_QUALIFIED
FORMAL_S2_FALSE
NO_REVISION_SUPERSESSION_SELECTION
NO_STRATEGY_BACKTEST_VALIDATION_OR_DEPLOYMENT_AUTHORITY
ORIGINAL_UPSTREAM_ARTIFACT_BYTES_UNCHANGED
PRIOR_BALANCE_BINDING_ADDS_ENDPOINT_COVER_ONLY
PROVIDER_DATES_NOT_AVAILABILITY_AUTHORITY
REVISION_CANDIDATES_RETAINED_WITHOUT_UPDATE_FLAG_SELECTION
```

## 11. Failure precedence

Exact enum order:

1. `INPUT_TYPE_MISMATCH`
2. `CATALOG_IDENTITY_MISMATCH`
3. `SOURCE_MEMBER_CONFLICT`
4. `FINANCIAL_REVISION_MISMATCH`
5. `FINANCIAL_PAYLOAD_INCOMPLETE`
6. `BUNDLE_EXACT_COVER_MISMATCH`
7. `PUBLICATION_INTEGRITY_FAILURE`

Stage-local exact-cover reasons:

```text
STAGE_INPUT_SCOPE_MISMATCH
EXPECTED_MEMBER_MISSING
PRIOR_BALANCE_ENDPOINT_MISSING
PAIR_DISPOSITION_CLOSURE_MISMATCH
```

All four roots are inspected sufficiently to select the globally highest-precedence failure. A failure returns no manifest, no partial destination and no downstream object.

Economic or metadata variants are evidence to retain, not `SOURCE_MEMBER_CONFLICT`. That code applies only when one immutable source identity has conflicting bytes.

## 12. Hardened publication

- Output must be outside all four input roots and absent at preflight.
- Traverse output ancestors FD-relatively; reject `..`, symlinks and replaced ancestors.
- Pin the output-parent descriptor and identity.
- Create one hidden staging directory with `0700`.
- Create exactly three regular members using `O_CREAT|O_EXCL|O_NOFOLLOW`, mode `0600`.
- Retain every file inode; fsync and read back each complete byte sequence.
- Fsync staging; verify staging and member pathnames still resolve to pinned inodes.
- Publish with `renameat2(RENAME_NOREPLACE)`.
- Reopen and verify published directory and all three member inodes/content.
- Fsync parent and reverify visible ancestor identity.
- Never delete a race-created or substituted path. Failed races may leave quarantined paths for inspection.

## 13. Tests and validation

### Focused tests

- Exact requirement counts, period partitions and all frozen hashes.
- S2A legacy extraction reproduces `1,030,659 / 704ada… / cb0db2…`.
- Both 850 economic conflicts retain both rows.
- Stage A reproduces the full and selected duplicate profiles above.
- `update_flag` mutation never changes inclusion or ordering.
- Omit one 2011 key → `BUNDLE_EXACT_COVER_MISMATCH/EXPECTED_MEMBER_MISSING`.
- Mutate the 850 set → frozen simple-key/hash failure.
- Add source-partition overlap → closure mismatch.
- Reorder loader/tree/member iteration → identical canonical outputs.
- Change immutable row bytes → source identity failure.
- Exact three output identities match §8.
- Global failure precedence across different bad roots.
- Parent/ancestor/staging/member substitution and no-clobber race tests.

Real-artifact sentinel flag:

```text
QB_S1_S2B_PRIOR_BALANCE_REAL_ARTIFACT_SENTINEL=1
```

### Architecture checks

- Production module is offline and does not inspect environment variables.
- No predecessor acquisition/binding-module imports.
- Exact public signature and five CLI arguments.
- Exact enum order, output names, hashes, flags and base.
- No `MarketBundle`, `TargetSnapshot`, Strategy, Runtime, Trading or execution types.
- Exact three-file diff from `0c00c82…`.
- AST/source sentinel that `update_flag` is never a selector.

### Validation allocation

```text
writer:
  focused test module
  one opt-in real-artifact sentinel

candidate:
  focused + architecture tests
  adjacent acquisition tests
  import-boundary/static checks

shared-node:
  one full locked Backtest suite

fan-in:
  clean status, protected hashes, blocker-only review
```

## 14. Readiness disposition

Every clause maps to a symbol, output field and sentinel. The seam, exact write set, schemas, output identities, preserved failures and publication mechanics are fixed. One writer can implement without an architectural decision.

**READY**

Completion record:

```text
repository changes: none
candidate diff/commit: none
artifact publication: none
worktree status: clean
formal S2: false
all downstream authority: false
next owner: single Backtest Stage B writer
```
