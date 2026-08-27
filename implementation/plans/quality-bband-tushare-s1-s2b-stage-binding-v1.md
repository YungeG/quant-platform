# Tushare Formal S1 → Provisional S2B Stage Binding — Full Implementation Packet

**Status: `READY`**  
**Execution:** not started; task is read-only. Repository worktrees remain clean.

## Outcome

Add one offline Backtest artifact builder that:

1. binds accepted formal S1 manifest `dcd0fecb…` to accepted S2B extraction `e5264163…`;
2. deeply proves identical screen-eligible arrays, period arrays, pair arrays, derived member-key arrays and their hashes;
3. changes only the effective input-authority classification;
4. leaves all S1/S2B source bytes untouched;
5. publishes exactly one `stage-binding-manifest.json`;
6. keeps formal S2 and every Strategy/Backtest/Validation/deployment authority false.

## Authority

| ID | Source | Requirement |
|---|---|---|
| C1 | Current task | Use the two accepted candidate roots and Backtest base `0d373b7…`; additive three-file, no-network seam. |
| C2 | `quality-bband-tushare-s1-authority-pivot-v1.md:3-28` | Tushare is owner-approved controlling S1 authority only; official authority and downstream qualification remain false. |
| C3 | Same plan `:145-217` | Freeze 9 screens, `2,845` union, `32,179` pairs, `96,537` members and five expected-set hashes. |
| C4 | Same plan `:219-254,320-332,362-384` | S1 arrays, ordering, canonical serialization and exact flags are authoritative. |
| C5 | S1 artifact `tushare-s1-structural-manifest.json` | Manifest `dcd0fecb…`, file `c8f96831…`, formal S1 flags and exact arrays are accepted. |
| C6 | S2B artifact `provisional-expected-set.json` | Expected-set ID `8c679397…`; original classification is provisional/formal-S1-false. |
| C7 | S2B artifact `extraction-manifest.json` | Manifest `e5264163…`; exact cover is `96537 = 96515 P + 1 O + 21 N`; formal S2 and downstream flags are false. |
| C8 | Backtest `0d373b7:tools/acquisition/cn_a_share_quality_bband_s2b_provisional_exact_v1.py:491-630,1528-1599` | Existing ordering, identities, output member hashes and S2B failure surface remain unchanged. |

## Ownership

- **Owner:** one Backtest writer.
- **Base:** `0d373b71b263a53b6b00e50b26ae1508dcfc986f`.
- **Proposed branch:** `research/qb-tushare-s1-s2b-stage-binding-v1`.
- **Exact write set:**
  1. `tools/acquisition/cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py`
  2. `tests/tools/acquisition/test_cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py`
  3. `tests/architecture/test_quality_bband_tushare_s1_s2b_stage_binding_v1_boundary.py`
- No shared existing file is modified.

## Flow and seam

Before:

```text
accepted S1 manifest ── no binding ──┐
                                     ├─ downstream still sees provisional S2B/formal_s1=false
accepted S2B extraction ─────────────┘
```

After:

```text
caller
  -> build_quality_bband_tushare_s1_s2b_stage_binding_v1
  -> exact bounded reads and identity checks
  -> deep S1/S2B expected-set equivalence
  -> accepted S2B closure/byte-preservation checks
  -> authority-classification overlay
  -> atomic one-file stage-binding publication
```

Existing S1 and S2B builders are not called or changed.

## Public operation

```python
build_quality_bband_tushare_s1_s2b_stage_binding_v1(
    *,
    s1_root: Path,
    s2b_root: Path,
    output_dir: Path,
) -> dict[str, object]
```

CLI has exactly:

```text
--s1-root
--s2b-root
--output-dir
```

No defaults, environment discovery, “latest” selection or network fallback.

## Symbol plan

| Symbol | Action | Responsibility |
|---|---|---|
| `QualityBbandTushareS1S2bBindingFailure` | add enum | Exact eight failure classes below. |
| `QualityBbandTushareS1S2bBindingError` | add exception | Carries only the enum code. |
| `_FrozenFile` | add dataclass | Filename, exact byte count and SHA-256. |
| `_strict_json` | add | Reject duplicate keys, invalid UTF-8 and nonfinite JSON. |
| `_read_exact_member` | add | FD-relative, no-follow, regular-file, exact-size read/hash. Provider rows are stream-hashed only. |
| `_load_s1` | add | Validate exact one-file S1 root, schema, body ID, flags and identity. |
| `_load_s2b` | add | Validate exact four-file S2B root and accepted manifest identities. |
| `_derive_s2b_instrument_union` | add | Return ordered union derived from S2B screen arrays. |
| `_derive_s2b_member_keys` | add | Return API-first member keys from exact `derivation.api_order` and pair order. |
| `_validate_equivalence` | add | Deep-array comparisons plus all frozen counts/hashes. |
| `_validate_s2b_closure` | add | Validate accepted P/O/N accounting, O/N arrays and preserved files. |
| `_build_manifest` | add | Construct only the frozen schema below. |
| `_rename_noreplace_at`, `_atomic_publish` | add | Hardened FD-relative, durable no-clobber publication. |
| `_parse_args`, `main` | add | Exact three-path CLI. |

## Exact output

Candidate root:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  tushare-s1-s2b-stage-bindings/2017-2025/20260827/v1-candidate-01
```

Only member:

```text
stage-binding-manifest.json
```

Serialization:

```text
UTF-8 canonical JSON
ensure_ascii=false
allow_nan=false
sort_keys=true
separators=(",", ":")
no trailing newline
manifest_id = sha256(canonical body without manifest_id)
```

Frozen output identity:

| Value | Exact identity |
|---|---|
| `manifest_id` | `sha256:c54bac9818a24688699aa585e49e91bde64ddbaf3efa90e0aa18491ff9b86f5c` |
| byte count | `7,323` |
| file SHA-256 | `sha256:ba5abfc5fc592ceb88ce1cabc95ebbded24abe9a8b108e9f6a31c96a0cc0878c` |

### Exact top-level fields

```text
type
schema_version
backtest_base_commit
inputs
shared_source_bindings
classification_replacement
equivalence
s2b_closure
preserved_s2b_members
flags
limitations
manifest_id
```

Constants:

```text
type = "quality_bband_tushare_s1_s2b_stage_binding_manifest"
schema_version = 1
backtest_base_commit = "0d373b71b263a53b6b00e50b26ae1508dcfc986f"
```

### Input identities

| Input | IDs and bytes |
|---|---|
| Formal S1 | type `quality_bband_tushare_s1_structural_manifest`; manifest `dcd0fecbfca29ce090b53462f3972174d4977116e52472309055b4110046df85`; `40,104,662` bytes; file SHA `c8f96831bd68cc1a46a291c59c5c97e10ce0c31eba54e53d9be8929366dfd059`; owner decision `62974819…`; packet `aeb8ac2b…` |
| S2B | type `quality_bband_s2b_provisional_exact_extraction_manifest`; manifest `e526416335016b9fd421e138655303673e76dc2bf6e2f53a6bb580904ed70d74`; `62,418` bytes; file SHA `74c60758…`; expected set `8c679397…`; official coverage `f245ebd5…` |

`shared_source_bindings` contains the exact matching S0 and annual-roster snapshot, content-tree, provenance, snapshot-file and receipt-file hashes from both manifests.

### Classification replacement

```text
source expected-set:
  authority_level = SOURCE_BOUNDED_PROVISIONAL
  formal_s1_qualified = false

source extraction:
  formal_s1_qualified = false
  limitation = FORMAL_S1_FALSE

bound stage:
  authority_level = OWNER_APPROVED_TUSHARE_FORMAL_S1
  owner_approved_tushare_authority = true
  formal_s1_qualified = true
```

Only these effective classifications are superseded:

```text
extraction-manifest.json:formal_s1_qualified
extraction-manifest.json:limitations/FORMAL_S1_FALSE
provisional-expected-set.json:authority_level
provisional-expected-set.json:formal_s1_qualified
```

Also frozen:

```text
data_fields_rewritten = []
original_artifact_bytes_modified = false
```

## Exact equivalence closure

Full arrays, not merely counts or hashes, must compare equal:

```text
S1 screens[*].eligible_instrument_ids
  == S2B screens[*].instrument_ids

S1 period_requirements
  == S2B period_requirements

S1 instrument_union
  == union derived from S2B screens

S1 expected_pairs
  == S2B expected_pairs

S1 expected_member_keys
  == [api, pair.instrument_id, pair.period]
     for API in S2B derivation.api_order
     for pair in S2B expected_pairs
```

Frozen aggregate values:

| Value | Exact |
|---|---:|
| screens | 9 |
| instrument union | 2,845 |
| expected pairs | 32,179 |
| expected member keys | 96,537 |

Shared hashes:

```text
screen_membership_hash
  sha256:00b6f4487ffd946ca1db05a4fc353f45ba9da235cc954e1248902da3103a8f2b
period_requirements_hash
  sha256:87f0ad15a76bc01561e0347f59a720e26b657829198774bf14893df7ef4fe846
instrument_union_hash
  sha256:25d69f75295afe13549269e96d9fbeb726605ac5c93e78d9cfe46ecf48f30ab0
expected_pairs_hash
  sha256:336efc4e947062036b1c98add7977653c48abdab8f33350516626a521b9b2b3e
expected_member_keys_hash
  sha256:0269e22c9f45b24b827e98a91515ac31ae5486ba0fda668f69112400b088e44b
```

Per-screen counts and eligible-ID hashes remain exactly those frozen in the S1 plan, from `1,995 / 277ce5c2…` through `2,667 / 5a0686e1…`.

## S2B closure and immutable bytes

```text
96537 = 96515 P + 1 O + 21 N
missing = 0
coverage extras = 0
all P/O/N overlaps = 0
```

Preserved members:

| Member | Bytes | SHA-256 |
|---|---:|---|
| `provisional-expected-set.json` | 6,587,372 | `55c4ecdee60e77feec3d2ee8c4d8da5b16a4e6a1e07bf2acc49a08669b8d1a29` |
| `provider-rows.jsonl` | 90,363,445 | `f4ed00c232930e1067c2796f7e5c3622397e8649e1afa0d5ae8730c964cf7abe` |
| `official-coverage.json` | 17,755 | `a0971482128b6e4e2f0bcdbdbb10f1102211974fd98157c0185ec25fc08e5b3b` |
| `extraction-manifest.json` | 62,418 | `74c60758f4b6eb9534900f868bdef444e5891ad6b4eee996e6713eb2e8ea876f` |

Additional preservation identities:

```text
provider row count = 150909
provider row IDs hash =
  sha256:04e8a893976e36fbdf3a186ea42d51897e03f09d6f849337a214d87f86c531c6
O member-keys hash =
  sha256:2b053ca7962d49a950bf22bed1f2ec6906b0f7223fc76cc20de2d3b28c045853
N member-keys hash =
  sha256:a68c15fe52bbea92d0049092843efd339dffe6b3bd52266e537fa5e4fb8e9534
```

Provider rows are stream-hashed, never parsed, copied or rewritten. Whole-file `official-coverage.json` identity preserves O/N evidence bytes.

## Exact flags

```text
owner_approved_tushare_authority = true
formal_s1_qualified = true
provider_scope_exact = true
s2b_exact_cover_complete = true

formal_s2_qualified = false
financial_payload_complete = false
financial_scope_qualified = false
official_exchange_authority = false
official_csrc_industry_authority = false
market_truth_completeness_claimed = false
survivorship_bias_safe_beyond_tushare_scope = false
decision_grade_eligible = false
strategy_authorized = false
strategy_target_authorized = false
backtest_authorized = false
validation_authorized = false
deployment_authorized = false
```

Exact sorted limitations:

```text
FINANCIAL_PAYLOAD_AND_SCOPE_NOT_QUALIFIED
FORMAL_S2_FALSE
NO_STRATEGY_BACKTEST_VALIDATION_OR_DEPLOYMENT_AUTHORITY
OFFICIAL_CSRC_INDUSTRY_AUTHORITY_FALSE
OFFICIAL_EXCHANGE_AUTHORITY_FALSE
ORIGINAL_S1_AND_S2B_ARTIFACT_BYTES_UNCHANGED
OWNER_APPROVED_TUSHARE_SCOPE_ONLY
STAGE_BINDING_REPLACES_INPUT_AUTHORITY_CLASSIFICATION_ONLY
SURVIVORSHIP_SAFETY_BEYOND_TUSHARE_SCOPE_FALSE
```

## Failure precedence

| Priority | Code | Condition |
|---:|---|---|
| 1 | `INPUT_TYPE_SCHEMA_OR_PATH` | Wrong path type, root shape, exact file set, symlink/nonregular member, strict JSON or schema failure. |
| 2 | `ARTIFACT_IDENTITY_MISMATCH` | Byte count, file SHA, body ID, manifest ID or expected-set ID mismatch. |
| 3 | `AUTHORITY_REBINDING_MISMATCH` | S1 owner/formal flags or original S2B provisional/formal-false classifications differ. |
| 4 | `SHARED_SOURCE_BINDING_MISMATCH` | S0 or annual-roster identities differ across S1 and S2B. |
| 5 | `EXPECTED_SET_EQUIVALENCE_MISMATCH` | Any eligible, period, union, pair or derived member array/count/hash differs. |
| 6 | `S2B_CLOSURE_OR_PAYLOAD_MISMATCH` | Closure, overlaps, P/O/N counts, O/N hashes or preserved output-member identity differs. |
| 7 | `FROZEN_OUTPUT_MISMATCH` | Constructed manifest ID, byte count or file SHA differs from the frozen output. |
| 8 | `PUBLICATION_INTEGRITY_FAILURE` | Staging, no-clobber rename, fsync, readback or inode/parent verification fails. |

Failure selection is global: both inputs are inspected before choosing the lowest-priority-number failure. Every failure publishes no builder-accepted destination and emits no empty universe, Target, Strategy terminal or execution request. Race-created or ownership-ambiguous pathnames are never deleted merely to make the visible destination absent, so failed races may leave quarantined staging/output paths for manual inspection.

## Security and atomic publication

- Open both roots and members FD-relatively with `O_NOFOLLOW`.
- Require exact root file sets: S1 one file; S2B four files.
- Require regular files and exact sizes before accepting bytes.
- No network, credentials, environment authority or dynamic discovery.
- Output must not exist or be inside either input root.
- Traverse and, when required, create every output-parent component FD-relatively from a pinned `/` or `.` descriptor; reject `..` and symlink components.
- Pin output parent FD.
- Create hidden staging directory FD-relatively.
- Write only `stage-binding-manifest.json` with `O_CREAT|O_EXCL`, retain its inode identity, and never unlink a substituted member.
- Fsync file and staging directory.
- Verify the staged member pathname still resolves to the pinned file inode before rename.
- Publish with `renameat2(RENAME_NOREPLACE)`.
- Verify the published directory inode equals the pinned staging inode and the published member inode/content equal the pinned staged file.
- Verify pathname still resolves through the pinned parent.
- Fsync parent directory.

## Forbidden paths

| Clause | Forbidden | Required route |
|---|---|---|
| C1/C8 | Modify existing S1/S2B builders or runtime packages | New artifact-only tool. |
| C5/C7 | Rewrite or copy S1/S2B artifacts | Reference exact immutable hashes. |
| C3/C4 | Accept matching hashes/counts while arrays differ | Full deep-array comparison. |
| C7 | Re-run provider extraction or parse 90 MB provider rows | Bind accepted file identity and manifest closure. |
| C2 | Promote formal S2, Strategy, Backtest or deployment | Keep every corresponding flag false. |
| C1 | Import private S1/S2B builder helpers | Self-contained stdlib-only stage tool. |
| C1 | Select “latest” candidate or fallback candidate | Explicit three-path API only. |

## Sentinel and validation

| Clause | Cheapest failing sentinel |
|---|---|
| C1 | Architecture test asserts base ancestry, exact three-file diff, three CLI paths and no network imports. |
| C2 | Test asserts exact true/false flag map and effective classification overlay. |
| C3 | Mutate one screen member while retaining frozen metadata; deep-equivalence check must fail. |
| C4 | Reorder one pair or API; pair/member-array check must fail. |
| C5 | Alter one S1 byte or manifest flag; identity/authority failure must precede equivalence. |
| C6 | Change expected-set authority or ID; rebinding must fail. |
| C7 | Alter provider SHA, O/N key, count or overlap; closure/payload check must fail. |
| C8 | Destination race, ancestor/parent replacement, mkdir→open staging substitution, directory substitution and member substitution must fail without clobber or attacker-path deletion. |

Validation allocation:

```text
Writer:
  uv run pytest -q tests/tools/acquisition/test_cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py

Candidate:
  uv run pytest -q \
    tests/tools/acquisition/test_cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py \
    tests/architecture/test_quality_bband_tushare_s1_s2b_stage_binding_v1_boundary.py
  uv run python -m compileall -q \
    tools/acquisition/cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py
  QB_TUSHARE_S1_S2B_REAL_ARTIFACT_SENTINEL=1 uv run pytest -q \
    tests/tools/acquisition/test_cn_a_share_quality_bband_tushare_s1_s2b_stage_binding_v1.py

Shared-node gate, once:
  uv run pytest -q
```

## Readiness evidence and disposition

Read-only inspection confirmed:

- both candidate roots have exact regular-file sets and no symlinks;
- all supplied manifest/file IDs and byte counts match;
- all JSON body IDs validate;
- all nine S1 eligible arrays equal S2B screen arrays;
- period, union, pair and derived member-key arrays equal;
- all five shared hashes equal;
- closure and O/N hashes equal the frozen values;
- Backtest base `0d373b7…` is available and is the merged S2B commit.

No blocker remains. Next owner is the single Backtest writer. No implementation diff, candidate commit or output artifact was created due the read-only constraint.
