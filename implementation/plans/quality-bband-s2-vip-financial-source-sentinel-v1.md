# QB-S2A-SRC-01 — Tushare VIP annual financial source-superset sentinel v1

- **Status:** `IMPLEMENTATION_PACKET_FROZEN / USER_APPROVED / SOURCE_SUPERSET / PLAN_ONLY`
- **Owner:** Backtest acquisition tooling
- **Purpose:** efficient full-market raw annual financial candidate capture for later exact S1 extraction; not an S2 stage publication or qualification
- **Implementation base:** Backtest PR #11 head `1ba50ff69d1cdf37132e6e20ac1695bed0fbf685`

## 1. Root request matrix

API order:

```text
income_vip
balancesheet_vip
cashflow_vip
```

Period order:

```text
20121231..20241231
```

For each API/period, root announcement interval is inclusive:

```text
start_date = period
end_date = 20260826
params = {
  period,
  comp_type:"1",
  report_type:"1",
  start_date,
  end_date
}
```

Thirty-nine roots are traversed in API order, then period order.

## 2. Exact minimal fields

### income_vip

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
revenue,operate_profit,total_profit,income_tax,n_income,n_income_attr_p,
minority_gain,fin_exp_int_exp,ebit,ebitda,update_flag
```

### balancesheet_vip

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
money_cap,total_assets,total_liab,total_hldr_eqy_inc_min_int,
total_hldr_eqy_exc_min_int,minority_int,total_liab_hldr_eqy,
st_borr,non_cur_liab_due_1y,lt_borr,bond_payable,
st_bonds_payable,update_flag
```

`lease_liab` is deliberately absent because the VIP endpoint omitted it when requested. This capture cannot exact-close canonical debt/leverage.

### cashflow_vip

```text
ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,
n_cashflow_act,c_pay_acq_const_fiolta,depr_fa_coga_dpba,
use_right_asset_dep,amort_intang_assets,lt_amort_deferred_exp,
c_cash_equ_end_period,free_cashflow,update_flag
```

Provider `ebit`, `ebitda` and `free_cashflow` remain advisory; later formulas use frozen raw inputs where complete.

## 3. Deterministic recursive slicing

The provider returns endpoint-specific `has_more=true` pages without pagination tokens. For each root interval:

1. request the current inclusive `[start_date,end_date]` page;
2. retain the raw page regardless of terminal status;
3. if `has_more=false`, record one terminal leaf;
4. if `has_more=true`, split by calendar midpoint:
   - `mid = start + floor((end-start)/2)`;
   - left `[start,mid]`;
   - right `[mid+1,end]`;
5. recurse depth-first left then right.

Guards:

```text
MAX_SPLIT_DEPTH = 16
MAX_TOTAL_REQUESTS = 4096
MAX_TOTAL_RESPONSE_BYTES = 536870912
```

`has_more=true` on a one-day interval, depth overflow or request ceiling returns a structured acquisition failure with no publication.

Terminal leaves for one root must form one exact disjoint gap-free cover of the root interval. Provider row order never drives splitting.

## 4. Source-superset boundary

The capture intentionally retains full-market rows. It is an approved `SOURCE_SUPERSET`, not the exact `2,845`-issuer S1 scope.

A later S2B extraction manifest must:

- exact-bind the immutable S1 expected Instrument/period set;
- select rows only by canonical identity/period;
- preserve all duplicate/revision candidates for expected members;
- count every extra source row/Instrument;
- fail on every missing expected member;
- never let extras define eligibility.

Expected coverage identity is exactly `(api_name, canonical InstrumentId, period)` for all three endpoints. `.BJ` and other non-S1 rows are retained source extras; extraction excludes them only against the immutable S1 expected set.

## 5. Output/member identity

One absent output directory contains variable raw page files plus:

```text
source-snapshot.json
acquisition-receipt.json
```

Raw member key:

```text
response/tushare/<api>/<period>/<start_date>-<end_date>-v1.json
```

Intervals make keys unique. Every requested parent and child page is a SourceSnapshot member with logical `0644`, immediate post-response timestamp and null declared hash. Metadata files are not members; disk mode is `0600`.

Exact provenance:

```text
vendor_key = tushare.pro
source_key = tushare.pro.via.xiaodefa.approved-proxy.s2a-vip-financial.2012-2024.20260826
license_ref = tushare.pro.terms
retention_policy_ref = backtest.acquisition.candidate
```

## 6. Parsing and validation

Reuse `_provider_response` from the financial sentinel because it preserves `has_more/count`. Wrap its typed failures into generic acquisition errors without leaking source/token text.

Every page requires:

- HTTP/provider success and exact field order/row width;
- exact `count=0` and boolean `has_more`;
- nonempty string `ts_code`;
- real `ann_date` inside the requested page interval;
- real `f_ann_date`;
- `end_date` equals requested period;
- `report_type="1"`, `comp_type="1"`, `update_flag` in `{"0","1"}`;
- every remaining value is finite JSON number or null, never quoted numeric;
- `ts_code` satisfies the reused canonical Tushare stock-code validator; source-superset `.BJ` rows are allowed;
- exact duplicate and revision rows are retained and counted, never rejected or deduplicated in acquisition.

Only terminal-leaf members form the later S2B row union. Nonterminal parent pages are audit/split evidence and must never enter extraction, coverage counts or qualification.

## 7. Exact write set and symbols

Three files only:

1. `tools/acquisition/cn_a_share_tushare_s2a_vip_financial_source_bounded_v1.py`
2. `tests/tools/acquisition/test_cn_a_share_tushare_s2a_vip_financial_source_bounded_v1.py`
3. `tests/architecture/test_g12a_s2a_vip_financial_source_bounded_v1_boundary.py`

Predecessor: `1ba50ff69d1cdf37132e6e20ac1695bed0fbf685`.

Production symbols:

```text
TushareS2aVipFinancialSourceBoundedRequestV1
_PageCaptureState
_timestamp
_midpoint
_parse_page
_validate_rows
_capture_page_tree
acquire_tushare_s2a_vip_financial_source_bounded_v1
_parser
main
```

Exact internal contracts:

```python
_midpoint(start_date: str, end_date: str) -> tuple[str, str]
_parse_page(source_bytes: bytes, expected_fields: tuple[str, ...], token: str) -> tuple[list[list[object]], bool, int]
_validate_rows(rows: list[list[object]], *, api_name: str, period: str, start_date: str, end_date: str) -> None
_capture_page_tree(*, api_name: str, period: str, fields: tuple[str, ...], start_date: str, end_date: str, parent_member_key: str | None, depth: int, state: _PageCaptureState, token: str, endpoint: str, post: ProxyPost, sleep: Callable[[float], object], time_ns: Callable[[], int]) -> str
```

`_PageCaptureState` is mutable `@dataclass(slots=True)` with exact fields:

```text
pages: list[dict[str, object]]
request_count: int
total_response_bytes: int
request_started: bool
```

`acquire...` constructs it as `([],0,0,False)` and `_capture_page_tree` mutates it in deterministic traversal order, returning the current root member-key `str`. Use generic `AcquisitionError`, not a new public enum/failure type.

Reuse approved proxy helpers, `_provider_response`, `_TS_CODE`, `_require_safe_output`, SourceSnapshot types, `freeze_source_snapshot`, `verify_source_snapshot` and `_common.publish_directory`. No direct HTTP dependency, endpoint failover, prior-artifact reads or financial normalization belongs here.

## 8. Flow and spacing

1. exact request/`_require_safe_output`/token/endpoint/callback validation;
2. traverse roots and recursive pages deterministically;
3. `0.5` second normal delay before every request after the first;
4. bounded retry delays remain additional;
5. immediate post-response clock;
6. immediately apply decoded-response byte ceiling, then per-page credential scan, then parse/row validation before retention;
7. after all roots: validate terminal-leaf covers and root-tree identities;
8. snapshot freeze → `verify_source_snapshot` exact success → full publication credential scan → publication.

Transport, retry, delay and time exceptions are generic-redacted. Clock is nonnegative non-boolean integer. Receipt acquisition time is maximum member timestamp.

Failure precedence:

1. request type/output safety/token/endpoint/callback mismatch;
2. logical request ceiling;
3. transport/retry/delay failure;
4. response timestamp failure;
5. total decoded response-byte ceiling;
6. per-page credential detection;
7. response JSON/envelope/field/count failure;
8. row semantic/type/domain failure;
9. unsplittable one-day interval, then depth guard;
10. terminal-leaf cover/root-tree mismatch;
11. snapshot freeze/verification failure;
12. final credential scan/publication failure.

## 9. Request and receipt

The zero-scope-field request canonical body contains exactly:

```text
type = tushare_s2a_vip_financial_source_bounded_request_v1
schema_version = 1
capture_key = 20260826-s2a-vip-financial-candidate-01
api_order = [income_vip,balancesheet_vip,cashflow_vip]
period_order = [20121231,...,20241231]
root_end_date = 20260826
field_sets = {income_vip:[...],balancesheet_vip:[...],cashflow_vip:[...]}
max_split_depth = 16
max_total_requests = 4096
max_total_response_bytes = 536870912
```

CLI accepts only approved `--endpoint` and required `--output-dir`; token is environment-only. Exact public acquisition signature:

```python
acquire_tushare_s2a_vip_financial_source_bounded_v1(
    request: TushareS2aVipFinancialSourceBoundedRequestV1,
    *, token: str, endpoint: str, output_dir: str | Path,
    post: ProxyPost, sleep: Callable[[float], object] = time.sleep,
    time_ns: Callable[[], int] = time.time_ns,
) -> dict[str, object]
```

Exact receipt type is `tushare_s2a_vip_financial_source_bounded_acquisition_receipt_v1`, schema `1`. Top-level keys are exactly:

```text
type,schema_version,request,provider_key,transport_proxy_key,
transport_endpoint,provider_requests,root_trees,
acquired_at_epoch_nanoseconds,snapshot,limitations,
source_bounded,source_superset,expected_scope_extracted,
financial_payload_complete,accounting_unit_qualified,
financial_availability_qualified,presentation_selection_qualified,
financing_debt_scope_qualified,provider_completeness_qualified,
revision_closure_complete,decision_grade_eligible,
deployment_authorized,provider_revision_id
```

Receipt exact-binds:

- canonical request/root matrix/field tuples/capture date/guards;
- provider/proxy/endpoint;
- ordered `provider_requests` for every page;
- ordered `root_trees`, each with root member, all page members, terminal leaf members and maximum depth;
- maximum acquisition timestamp;
- SourceSnapshot;
- literal limitations and fixed flags.

Each provider page entry includes exactly:

```text
api_name,period,params,fields,member_key,parent_member_key,depth,
attempts,response_received_at_epoch_nanoseconds,response_byte_count,
response_sha256,returned_row_count,observed_envelope,terminal,
child_member_keys,provider_revision_id,declared_sha256
```

Each root tree contains exactly `api_name`, `period`, `root_start_date`, `root_end_date`, `root_member_key`, ordered `page_member_keys`, ordered `terminal_leaf_member_keys`, and `maximum_depth`. Root depth is exactly `0`; children increment by one. Terminal leaves must cover the root exactly.

## 10. Fixed limitations and flags

Literal ordered limitations are exactly:

1. `full-market source superset is not exact S1 or S2 scope`;
2. `provider announcement-date slicing is source-bounded, not revision or terminal authority`;
3. `lease_liab is unavailable from the captured VIP balance schema`;
4. `provider computed EBIT, EBITDA, and free_cashflow are advisory`;
5. `expected S1 extraction and missing-member closure are not performed`;
6. `financial statement revisions, supersession, and finality are not qualified`;
7. `accounting currency and unit authority are not established`;
8. `accepted financial availability is not established`;
9. `coherent presentation selection is not performed`;
10. `financing-note and debt-scope closure are not established`;
11. `no S2 qualification, Strategy, Validation, or deployment authority is granted`.

Flags:

```text
source_bounded = true
source_superset = true
expected_scope_extracted = false
financial_payload_complete = false
accounting_unit_qualified = false
financial_availability_qualified = false
presentation_selection_qualified = false
financing_debt_scope_qualified = false
provider_completeness_qualified = false
revision_closure_complete = false
decision_grade_eligible = false
deployment_authorized = false
provider_revision_id = null
```

## 11. Publication and tests

S2A is explicitly a non-stage candidate capture, so staged-funnel stage-publication atomicity does not apply yet. Reuse publisher no-clobber/receipt-last/fsync/ordinary-failure cleanup; no crash-atomicity claim.

Tests use reduced root periods/counts through monkeypatched frozen constants and cover:

- root order, recursive split order and midpoint boundaries;
- terminal/gap-free leaf cover;
- one-day/depth/request guards;
- `has_more/count`, fields, types, nonfinite/quoted numeric and duplicate-key JSON failures;
- retained duplicate rows, terminal-leaf-only union and allowed parent/child overlap;
- exact raw preservation, variable members, snapshot/receipt/tree schema;
- delays/retries/clocks/redaction/no-clobber/fsync cleanup;
- literal limitations/flags and exact three-file diff.

Safety ceilings count logical page requests, not transport retry attempts. The request ceiling is checked before each logical request; after transport, the immediate timestamp is recorded, then the response-byte ceiling and per-page credential scan run before parsing/retention. Maximum retained output is accepted as bounded by 512 MiB plus metadata.

Validation commands:

```text
uv run --locked pytest -q tests/tools/acquisition/test_cn_a_share_tushare_s2a_vip_financial_source_bounded_v1.py tests/architecture/test_g12a_s2a_vip_financial_source_bounded_v1_boundary.py
uv run --locked pytest -q tests/bundle_builder tests/tools/acquisition
uv run --locked pytest -q --ignore=tests/architecture --ignore=tests/runtime/analysis/test_analysis_contract.py --ignore=tests/runtime/publication/test_publication_refs.py
git diff --check
git status --short --untracked-files=all
```

The two ignored runtime files require the absent cross-repository fixture `/home/ygguo/agent-projs/ai-crypt/tests/contracts/backtest-consumer-port-v1.json`; they are unrelated to acquisition. Final architecture validation must prove the exact three-file committed/worktree set after all commands.

Real capture is separately authorized only after focused/regression tests and independent review.
