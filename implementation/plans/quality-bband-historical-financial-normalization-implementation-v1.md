# QB-FIN-HISTORY-NORM-IMPL-01 — Gree historical financial normalization packet

- **Status:** `STACKED_CANDIDATE_PUBLISHED / REAL_CANDIDATE_PUBLISHED / NOT_ACCEPTED`
- **Owner:** Backtest Market Bundle Builder
- **Base:** stacked PR #7 commit `25b8dd12a8a62530ce2467e13d1bd0b55b34b0cf`
- **Candidate:** Backtest PR [#8](https://github.com/YungeG/quant-backtest/pull/8), commit `bac94d56272d3d3aa1172c052c855d4fb46a4356`
- **SourceSnapshot:** `sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b`
- **Declaration candidate:** manifest file `sha256:a424edd19abc9b17d54f40bfc0e1c6f90e04690d7ba4c6bb10a99982e9531726`
- **Calendar authority:** [`research/quality-bband-szse-calendar-session-authority-v1.md`](../../research/quality-bband-szse-calendar-session-authority-v1.md)

## 1. Outcome

Purely normalize the fixed real Gree historical provider members into source-bounded statement revisions and one period observation set per supported period.

- `20181231`: one balance revision plus declared debt/D&A supplements.
- `20191231`, `20201231`, `20221231`: one income, balance and cash-flow revision plus declared debt/D&A supplements.
- `20211231`: preserve the canonical declaration failure as `DEBT_SCOPE_INCOMPLETE`; emit no revision or observation set.

The operation emits no presentation selection, formula, ratio, feature, MarketEvent, MarketBundle, Strategy, Backtest request, Validation or deployment authority.

## 2. Minimal seam

```python
class GreeHistoricalFinancialStatementKind(str, Enum): ...
class GreeHistoricalFinancialNormalizationFailureCode(str, Enum): ...
class GreeHistoricalFinancialAdvisoryObservationV1: ...
class GreeHistoricalFinancialAdvisoryConflictV1: ...
class GreeHistoricalFinancialNormalizationFailure: ...
class GreeHistoricalFinancialStatementObservationRevisionV1: ...
class GreeHistoricalFinancialPeriodObservationSetV1: ...
class GreeHistoricalFinancialNormalizationOutcome: ...


def normalize_gree_historical_financial_period_v1(
    source_snapshot: SourceSnapshot,
    declaration_outcome: GreeHistoricalFinancialDeclarationOutcome,
) -> GreeHistoricalFinancialNormalizationOutcome: ...
```

Both arguments are exact in-memory values. The declaration **outcome**, not a bare declaration, is consumed so the 2021 typed conflict cannot be skipped or converted to input mismatch.

No filesystem, network, environment, PDF parsing, Calendar lookup, clock, Runtime, Trading or Market Data access.

## 3. Exact period behavior

| Period | Declaration input | Required statements | Result |
| --- | --- | --- | --- |
| `20181231` | declaration `sha256:51b1ae41791336ead0487148e721c530ff0de8b5a718d81d4b3d2fe63a55a575` | `BALANCE` only | one-revision observation set |
| `20191231` | declaration `sha256:0f52ca93b04c25d2135a584d853198ad2655f0cec31cc161867c22010927aa96` | `INCOME`, `BALANCE`, `CASH_FLOW` | three-revision observation set |
| `20201231` | declaration `sha256:14143974d80d622721ecf78e3eae1e3467815366dc9bd90657774bd8473ee099` | `INCOME`, `BALANCE`, `CASH_FLOW` | three-revision observation set |
| `20211231` | declaration failure `sha256:2c5b90d0cbd89ccd584c0a33234d796ec9b039abe683ad897b7a5fe61cac5792` | none inspected | normalization failure `DEBT_SCOPE_INCOMPLETE` |
| `20221231` | declaration `sha256:1124c88497385f9233df6c4f8c6ece397379d382a18d27aeacead31b82539aba` | `INCOME`, `BALANCE`, `CASH_FLOW` | three-revision observation set |

No writer-selected period list, missing-trio fallback or generic partial-period mode is allowed.

## 4. Fixed source authority

```text
source_snapshot_id = sha256:aee2ea78f3d51185110bc927836ce77ed51f590a9c7b4c26ee7ecd951cbf8d4b
content_tree_hash = sha256:d5375befd81c5fb1ab2832a48bb7c3d0b4fc7dcf9b4ea64700f837dc624ce3d9
provenance_hash = sha256:5495fbee8d8668e324be8263f49f9f556ea6a4324b5f530c13a2176f148ad2e5
publication_metadata_hash = sha256:3292c3b1bd89f01cb41e09401ad306b6ec8e769cac402317817fe395ff0e918e
instrument_id = xshe:000651
period_kind = ANNUAL
consolidation_scope = CONSOLIDATED
accounting_currency = CNY
accounting_unit = yuan
presentation_basis = CURRENT_CONSOLIDATED
```

`verify_source_snapshot()` must succeed before period source members are inspected. Nested snapshot values are exact-reconstructed; coherent subclass/field forgery must fail.

## 5. Exact provider members and row identities

JSON parsing uses the 2023 normalization rules unchanged:

- UTF-8;
- duplicate-key rejection;
- non-finite rejection;
- exact envelope/field tuple;
- JSON numeric tokens converted directly to canonical decimal strings, never binary float;
- context fields exact strings;
- line items number-or-null only;
- canonical row hash is `canonical_sha256(tuple(parsed_row_values))`;
- row evidence is sorted by row hash and stored as aligned immutable `(row_hash, update_flag)` evidence;
- row/member order cannot alter identity.

| Period | Kind | Member | Member content hash | Rows | Sorted row hashes |
| --- | --- | --- | --- | ---: | --- |
| `20181231` | `BALANCE` | `response/tushare/balancesheet/000651.SZ-20181231-20190429-v3.json` | `sha256:d412a0972630ba642aa06f162885cc06ba9d1310b5e40a604169c3cecc8355e1` | 2 | `sha256:0c8f5e8a8c6107573be52e29afcf5d03adf544c55a7f705a2d37dc41cdbbadf1`, `sha256:436143a5f528e7c61ff71a43486258f5efe6121b5b810b61a9d769188d576456` |
| `20191231` | `INCOME` | `response/tushare/income/000651.SZ-20191231-20200430-v3.json` | `sha256:982a5d65674e8f58f6277bc9c89aa0f894281f49fa5769b84ac67760faafd586` | 2 | `sha256:2d74a71e7390fac916705537f15f1cd29aeaa4aed4b9f4724d9ec7a0625c3d12`, `sha256:cff83cb7e3ea02f44ad667e1baf2748c0e9d434f74d8096f04116e7fc4410b2e` |
| `20191231` | `BALANCE` | `response/tushare/balancesheet/000651.SZ-20191231-20200430-v3.json` | `sha256:cd4a19de67c30837df4546abbb87f0bfeef97d1c2359a25fce29ee0a6d1631b8` | 2 | `sha256:0eede15c1f9033a38ee0b41ef3a279d3fd24dfb84bff78c91795b684c2fdad54`, `sha256:3e82d2ec45dd7e9afc931f7e80c14b39da7cc5026db11705e091eb151b253a2a` |
| `20191231` | `CASH_FLOW` | `response/tushare/cashflow/000651.SZ-20191231-20200430-v3.json` | `sha256:9d2837a0897cb25e40e428d037ed276ea03b19508159251f510bd21f08b1b305` | 2 | `sha256:125f686ad284aaec663439be6369e4ae2ca112d225d109abe3a212368a638a28`, `sha256:fedce59f03b3958c7fdb4d01851b2189245cba5ebd2d44ba3cfef1bbd1ee8f3d` |
| `20201231` | `INCOME` | `response/tushare/income/000651.SZ-20201231-20210429-v3.json` | `sha256:c90bf9ceaca99e6246544e7a3d5b9ce18f6010ce5dd46f8fdf19b6670f439f8a` | 2 | `sha256:526c9a14945d0ec256f6b521ce2b13ba4a942e60f0a8d9b39f27cd5e77a0b249`, `sha256:76d72b36d08d121b5ef12b037c723d4e70c79450804defce13191cf6cddbcde3` |
| `20201231` | `BALANCE` | `response/tushare/balancesheet/000651.SZ-20201231-20210429-v3.json` | `sha256:967469a431b76e6f3af5d2d2af5abe8c726951c7742cb8b2ec7f0804bfd5238c` | 2 | `sha256:3e1c1256838e8e1e03bad1e19fba81134bf1376896a39907e5fe58cb83638adb`, `sha256:dccef36e8378b78c76efea167a8354bba0f520403c58ff33de3c43b86e988069` |
| `20201231` | `CASH_FLOW` | `response/tushare/cashflow/000651.SZ-20201231-20210429-v3.json` | `sha256:0bad70737efd1091934524b4a8022d24f7dbc4f0935ddb0fde67013223bc7ccb` | 2 | `sha256:1b1c7295f057a39d7c8d0ffc18e719381b8857d2526daa9fbb246caa81484037`, `sha256:f2441ea67e9231a4b612f9deef05825d71d2c3ff7ce299add0ae26cb35f62e11` |
| `20221231` | `INCOME` | `response/tushare/income/000651.SZ-20221231-20230429-v3.json` | `sha256:51f6ad53f20172cbeacd10e928d41682f46810c4bec0ba6f954831770c6c3e65` | 1 | `sha256:d9b6c258c86cd517d0174a6e2c45ef6c9835310c78735df0d08a728ed6329be4` |
| `20221231` | `BALANCE` | `response/tushare/balancesheet/000651.SZ-20221231-20230429-v3.json` | `sha256:9c5f870bbf1601964801223019af51ab281fabb671a83c78b582bb28ea615fe5` | 2 | `sha256:62a2c5212905023399073dd0ea8fecdf92d00e86e59bc2a80ad18308ea2d24fe`, `sha256:fb4471d6a17c7184eb39834d04f6606c4c95ef94b7d0b3fbf651b0fab3b606b2` |
| `20221231` | `CASH_FLOW` | `response/tushare/cashflow/000651.SZ-20221231-20230429-v3.json` | `sha256:c81e36321dc7b64412789deab14f6a43ec465bd7c15f3b937594556ceeac6e54` | 2 | `sha256:336f90eb45f8cc80df7da6968751d7ec503e2bea203557ecfc1a0a841d94914b`, `sha256:9dc0456482960fa746c74c6e693d5497ecaa01e6a972a2c56f92f98794614438` |

The 2021 provider members remain retained in the SourceSnapshot but are never parsed by this operation after the canonical declaration conflict is recognized.

## 6. Duplicate collapse and the 2022 advisory conflict

`source_row_evidence` is an exact tuple of immutable `(source_row_hash, provider_update_flag)` pairs sorted by row hash:

```text
20181231 BALANCE = ((0c8f...badf1,"0"),(4361...6456,"1"))
20191231 INCOME = ((2d74...3d12,"1"),(cff8...0b2e,"0"))
20191231 BALANCE = ((0eed...ad54,"1"),(3e82...3a2a,"0"))
20191231 CASH_FLOW = ((125f...a28,"1"),(fedc...8f3d,"0"))
20201231 INCOME = ((526c...b249,"0"),(76d7...cde3,"1"))
20201231 BALANCE = ((3e1c...8adb,"1"),(dcce...8069,"0"))
20201231 CASH_FLOW = ((1b1c...4037,"1"),(f244...2e11,"0"))
20221231 INCOME = ((d9b6...9be4,"1"),)
20221231 BALANCE = ((62a2...24fe,"0"),(fb44...06b2,"1"))
20221231 CASH_FLOW = ((336f...914b,"0"),(9dc0...4438,"1"))
```

The full row hashes are those in section 5; ellipses are documentation abbreviations only. Constructor constants pair those exact full hashes with the flags shown above.

For every duplicate set:

1. retain every row-hash/flag pair in exact row-hash order;
2. never treat `update_flag=1` as revision/finality authority;
3. remove `update_flag` and require one economic row;
4. for `20221231/CASH_FLOW` only, also remove `free_cashflow` from the equality comparison;
5. any other difference returns `PRESENTATION_CONFLICT`.

Advisory evidence uses exact immutable values:

```python
@dataclass(frozen=True, slots=True)
class GreeHistoricalFinancialAdvisoryObservationV1:
    source_row_hash: str
    provider_update_flag: str
    value: str

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "source_row_hash": self.source_row_hash,
            "provider_update_flag": self.provider_update_flag,
            "value": self.value,
        }

@dataclass(frozen=True, slots=True)
class GreeHistoricalFinancialAdvisoryConflictV1:
    field: str
    observations: tuple[GreeHistoricalFinancialAdvisoryObservationV1, ...]

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "field": self.field,
            "observations": tuple(value.to_canonical_dict() for value in self.observations),
        }
```

Constructors exact-reconstruct every nested observation and the conflict tuple; mutable dictionaries are never stored.

The exact 2022 cash-flow value is:

```python
advisory_conflicts = (
  GreeHistoricalFinancialAdvisoryConflictV1(
    field="free_cashflow",
    observations=(
      GreeHistoricalFinancialAdvisoryObservationV1(
        source_row_hash="sha256:336f90eb45f8cc80df7da6968751d7ec503e2bea203557ecfc1a0a841d94914b",
        provider_update_flag="0",
        value="27066951494.8798",
      ),
      GreeHistoricalFinancialAdvisoryObservationV1(
        source_row_hash="sha256:9dc0456482960fa746c74c6e693d5497ecaa01e6a972a2c56f92f98794614438",
        provider_update_flag="1",
        value="30735381659.7498",
      ),
    ),
  ),
)
```

The normalized 2022 cash-flow line item is `free_cashflow=None`, `unresolved_fields=("free_cashflow",)`. Both raw values remain evidence and neither can affect canonical FCF formula identity.

All other revisions have `advisory_conflicts=()` and `unresolved_fields=()`.

## 7. Exact normalized line items

Raw nulls remain null. Historical normalization introduces no generic null-to-zero substitution; declared debt and D&A are separate observation-set supplements.

### `20181231 / BALANCE`

```text
money_cap=113079030368.11; total_assets=251234157276.81; total_liab=158519445549.35
total_hldr_eqy_inc_min_int=92714711727.46; total_hldr_eqy_exc_min_int=91327095069.1
minority_int=1387616658.36; total_liab_hldr_eqy=251234157276.81
st_borr=22067750002.7; non_cur_liab_due_1y=null; lt_borr=null
bond_payable=null; st_bonds_payable=null; lease_liab=null
```

### `20191231`

```text
INCOME: revenue=198153027540.35; operate_profit=29605107122.4; total_profit=29352707228.7;
income_tax=4525463624.73; n_income=24827243603.97; n_income_attr_p=24696641368.84;
minority_gain=130602235.13; fin_exp_int_exp=1598276258.59; ebit=27947212725.83;
ebitda=31141631965.48

BALANCE: money_cap=125400715267.64; total_assets=282972157415.28; total_liab=170924500892.2;
total_hldr_eqy_inc_min_int=112047656523.08; total_hldr_eqy_exc_min_int=110153573282.67;
minority_int=1894083240.41; total_liab_hldr_eqy=282972157415.28; st_borr=15944176463.01;
non_cur_liab_due_1y=null; lt_borr=46885882.86; bond_payable=null; st_bonds_payable=null; lease_liab=null

CASH_FLOW: n_cashflow_act=27893714093.59; c_pay_acq_const_fiolta=4713187965.97;
depr_fa_coga_dpba=2977103353.04; use_right_asset_dep=null; amort_intang_assets=215796437.95;
lt_amort_deferred_exp=1519448.66; c_cash_equ_end_period=26372571821.49;
free_cashflow=38794013433.0428
```

### `20201231`

```text
INCOME: revenue=168199204404.53; operate_profit=26043517837.7; total_profit=26308937428.79;
income_tax=4029695233.52; n_income=22279242195.27; n_income_attr_p=22175108137.32;
minority_gain=104134057.95; fin_exp_int_exp=1088369394.87; ebit=23318957276.21;
ebitda=26907663609.99

BALANCE: money_cap=136413143859.81; total_assets=279217923628.27; total_liab=162337436540.13;
total_hldr_eqy_inc_min_int=116880487088.14; total_hldr_eqy_exc_min_int=115190211206.76;
minority_int=1690275881.38; total_liab_hldr_eqy=279217923628.27; st_borr=20304384742.34;
non_cur_liab_due_1y=null; lt_borr=1860713816.09; bond_payable=null; st_bonds_payable=null; lease_liab=null

CASH_FLOW: n_cashflow_act=19238637309.16; c_pay_acq_const_fiolta=4528646805.03;
depr_fa_coga_dpba=3377378887.04; use_right_asset_dep=null; amort_intang_assets=211327446.74;
lt_amort_deferred_exp=null; c_cash_equ_end_period=24225049638.15; free_cashflow=14100983784.043
```

### `20221231`

```text
INCOME: revenue=188988382706.68; operate_profit=27284097086.18; total_profit=27217384842.61;
income_tax=4206040489.5; n_income=23011344353.11; n_income_attr_p=24506623782.46;
minority_gain=-1495279429.35; fin_exp_int_exp=2836743431.08; ebit=25617870403.76;
ebitda=30587816420.11

BALANCE: money_cap=157484332251.39; total_assets=355024758878.82; total_liab=253148710864.63;
total_hldr_eqy_inc_min_int=101876048014.19; total_hldr_eqy_exc_min_int=96758734892.25;
minority_int=5117313121.94; total_liab_hldr_eqy=355024758878.82; st_borr=52895851287.92;
non_cur_liab_due_1y=255342537.57; lt_borr=30784241211.21; bond_payable=null;
st_bonds_payable=null; lease_liab=146836620.66

CASH_FLOW: n_cashflow_act=28668435921.27; c_pay_acq_const_fiolta=6036136315.75;
depr_fa_coga_dpba=4597938791.84; use_right_asset_dep=null; amort_intang_assets=372007224.51;
lt_amort_deferred_exp=null; c_cash_equ_end_period=31754656695.61; free_cashflow=null
```

Raw null fields are the exact null names above in provider field order.

## 8. Availability authority

The operation exact-requires the fixed source hashes and `UtcInstant` for each success period:

| Period | `available_at_utc` | Ordered `availability_source_hashes` |
| --- | --- | --- |
| `20181231` | `UtcInstant(1556587800000000000)` | 2016 rule `sha256:888302b...ff4b`, 2019-04-30 market overview `sha256:e7d30c...40b3` |
| `20191231` | `UtcInstant(1588728600000000000)` | 2020 notice `sha256:f386cf...18af`, 2020 rule `sha256:348218...3215`, 2020-05-06 market overview `sha256:bc75da...d835` |
| `20201231` | `UtcInstant(1619746200000000000)` | 2020 rule `sha256:348218...3215`, 2021-04-30 market overview `sha256:57cda1...2ad7` |
| `20221231` | `UtcInstant(1683163800000000000)` | 2023 notice `sha256:a56a10...dab8`, 2023 rule announcement `sha256:58ea09...dea9`, 2023 rules `sha256:701811...722`, 2023 events `sha256:a52882...cf83`, 2023-05-04 market overview `sha256:d668be...68d5` |

Exact ordered tuples:

```python
_AVAILABILITY_SOURCE_HASHES = {
  "20181231": (
    "sha256:888302b51ee0f22713c20ac9afb08b72ba7d3fb01945c9f181eede1e4385ff4b",
    "sha256:e7d30c906216ebd7b2f0308c9ee0b609192fb3f9462c12ab938c64ff33be40b3",
  ),
  "20191231": (
    "sha256:f386cf8cb0f9e3e9c288b231e3a07b190464917c191687026a29b07ab3ef18af",
    "sha256:348218aab3164083e52057f7313d7d9d7e29f3701b464bc3cc030b600fc23215",
    "sha256:bc75da295c9857ed8d8fa50f00f3e783307649d548fbc2660bad227a11b0d835",
  ),
  "20201231": (
    "sha256:348218aab3164083e52057f7313d7d9d7e29f3701b464bc3cc030b600fc23215",
    "sha256:57cda17f2cdbfba82ddb10cbf595806cc34a498b22b9edc6d50da38dfe232ad7",
  ),
  "20221231": (
    "sha256:a56a1050b2d516ad287ac1aa5edb7b9cde3e1e007a4e3d3917056bba24cedab8",
    "sha256:58ea091197cc7c95eae9c3a0dab2ae80f45a4d54f26a3755810b8672517cdea9",
    "sha256:7018114a6e11deb239c2a72e71e49defc6e8841b3e2c093b3bbf809282c67222",
    "sha256:a5288222974e04cb25c52f1d2c04059217eee552cbce6e4e91fa7a792f07cf83",
    "sha256:d668beafd3aa475345e9c8f60210c9793de3868ef9da11312f1b1316c5b068d5",
  ),
}
```

`availability_source_hashes` is part of every revision and observation-set identity. No URL refetch, natural-day arithmetic, weekday calculation or same-day open is permitted.

## 9. Observation identity

Economic key:

```python
canonical_sha256({
  "instrument_id": "xshe:000651",
  "statement_kind": kind.value,
  "report_period_end": period,
  "period_kind": "ANNUAL",
  "consolidation_scope": "CONSOLIDATED",
  "accounting_currency": "CNY",
  "accounting_unit": "yuan",
})
```

Observation lineage key adds `presentation_basis="CURRENT_CONSOLIDATED"`.

Revision body exact-binds:

- period/kind/economic/lineage identity;
- official and actual announcement date from the declaration;
- `available_at_utc` and ordered availability source hashes;
- SourceSnapshot/tree/provenance;
- exact provider member/content/row hashes and update flags;
- `official_document_hash = declaration.statement_unit.source_document_hash`;
- `publication_metadata_hash = declaration.publication_evidence.source_content_hash`;
- declaration hash;
- raw nulls, unresolved fields and advisory conflicts;
- exact normalized line items and hash;
- `provider_revision_id=None` and `supersedes_revision_id=None`;
- source-bounded true; closure/decision-grade/deployment false.

`revision_id = canonical_sha256(revision body without revision_id)`.

## 10. Proposed values

```python
GreeHistoricalFinancialNormalizationFailure = {
  schema_version,
  code,
  report_period: str | None,
  declaration_failure: GreeHistoricalFinancialDeclarationFailure | None,
  failure_hash,
}

GreeHistoricalFinancialStatementObservationRevisionV1 = {
  schema_version,
  statement_kind,
  economic_statement_key,
  observation_lineage_key,
  instrument_id,
  report_period_end,
  period_kind,
  consolidation_scope,
  accounting_currency,
  accounting_unit,
  presentation_basis,
  announcement_date,
  actual_announcement_date,
  available_at_utc,
  availability_source_hashes,
  source_snapshot_id,
  source_content_tree_hash,
  source_provenance_hash,
  source_member_key,
  source_member_content_hash,
  source_row_evidence: tuple[tuple[str, str], ...],
  official_document_hash,
  publication_metadata_hash,
  declaration_hash,
  raw_null_fields,
  unresolved_fields,
  advisory_conflicts,
  line_items,
  line_items_hash,
  provider_revision_id=None,
  supersedes_revision_id=None,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  revision_id,
}

GreeHistoricalFinancialPeriodObservationSetV1 = {
  schema_version,
  report_period_end,
  source_snapshot_id,
  declaration_hash,
  available_at_utc,
  availability_source_hashes,
  revisions,
  ending_interest_bearing_debt,
  ending_depreciation_and_amortization,
  source_bounded=true,
  revision_closure_complete=false,
  decision_grade_eligible=false,
  deployment_authorized=false,
  observation_set_hash,
}
```

Literal canonical bodies are exactly:

```python
# GreeHistoricalFinancialNormalizationFailure._body()
{
  "type": "gree_historical_financial_normalization_failure",
  "schema_version": self.schema_version,
  "code": self.code.value,
  "report_period": self.report_period,
  "declaration_failure": None if self.declaration_failure is None
      else self.declaration_failure.to_canonical_dict(),
}

# GreeHistoricalFinancialStatementObservationRevisionV1._body()
{
  "type": "gree_historical_financial_statement_observation_revision",
  "schema_version": self.schema_version,
  "statement_kind": self.statement_kind.value,
  "economic_statement_key": self.economic_statement_key,
  "observation_lineage_key": self.observation_lineage_key,
  "instrument_id": self.instrument_id,
  "report_period_end": self.report_period_end,
  "period_kind": self.period_kind,
  "consolidation_scope": self.consolidation_scope,
  "accounting_currency": self.accounting_currency,
  "accounting_unit": self.accounting_unit,
  "presentation_basis": self.presentation_basis,
  "announcement_date": self.announcement_date,
  "actual_announcement_date": self.actual_announcement_date,
  "available_at_utc": self.available_at_utc,
  "availability_source_hashes": self.availability_source_hashes,
  "source_snapshot_id": self.source_snapshot_id,
  "source_content_tree_hash": self.source_content_tree_hash,
  "source_provenance_hash": self.source_provenance_hash,
  "source_member_key": self.source_member_key,
  "source_member_content_hash": self.source_member_content_hash,
  "source_row_evidence": tuple(
    {"source_row_hash": row_hash, "provider_update_flag": update_flag}
    for row_hash, update_flag in self.source_row_evidence
  ),
  "official_document_hash": self.official_document_hash,
  "publication_metadata_hash": self.publication_metadata_hash,
  "declaration_hash": self.declaration_hash,
  "raw_null_fields": self.raw_null_fields,
  "unresolved_fields": self.unresolved_fields,
  "advisory_conflicts": tuple(
    value.to_canonical_dict() for value in self.advisory_conflicts
  ),
  "line_items": _line_item_dict(self.line_items),
  "line_items_hash": self.line_items_hash,
  "provider_revision_id": self.provider_revision_id,
  "supersedes_revision_id": self.supersedes_revision_id,
  "source_bounded": self.source_bounded,
  "revision_closure_complete": self.revision_closure_complete,
  "decision_grade_eligible": self.decision_grade_eligible,
  "deployment_authorized": self.deployment_authorized,
}

# GreeHistoricalFinancialPeriodObservationSetV1._body()
{
  "type": "gree_historical_financial_period_observation_set",
  "schema_version": self.schema_version,
  "report_period_end": self.report_period_end,
  "source_snapshot_id": self.source_snapshot_id,
  "declaration_hash": self.declaration_hash,
  "available_at_utc": self.available_at_utc,
  "availability_source_hashes": self.availability_source_hashes,
  "revisions": tuple(value.to_canonical_dict() for value in self.revisions),
  "ending_interest_bearing_debt": self.ending_interest_bearing_debt,
  "ending_depreciation_and_amortization": self.ending_depreciation_and_amortization,
  "source_bounded": self.source_bounded,
  "revision_closure_complete": self.revision_closure_complete,
  "decision_grade_eligible": self.decision_grade_eligible,
  "deployment_authorized": self.deployment_authorized,
}

# GreeHistoricalFinancialNormalizationOutcome.to_canonical_dict()
{
  "type": "gree_historical_financial_normalization_outcome",
  "schema_version": 1,
  "observation_set": None if self.observation_set is None
      else self.observation_set.to_canonical_dict(),
  "failure": None if self.failure is None else self.failure.to_canonical_dict(),
}
```

`to_canonical_dict()` adds `failure_hash`, `revision_id` or `observation_set_hash` only to the corresponding three hashed values. Constructors exact-reconstruct nested `UtcInstant`, declaration failure, advisory values, revisions and sets before storing them.

Revision order is exact:

```text
20181231 = (BALANCE,)
20191231/20201231/20221231 = (INCOME, BALANCE, CASH_FLOW)
```

## 11. Declaration supplements

Observation sets exact-copy only the already reconstructed declaration values:

| Period | Ending interest-bearing debt | Ending D&A |
| --- | ---: | ---: |
| `20181231` | `22383629781.83` | `3110329271.82` |
| `20191231` | `17344021324.26` | `3194419239.65` |
| `20201231` | `23201159352.29` | `3588706333.78` |
| `20221231` | `86027130079.25` | `4997685416.88` |

2018 D&A is retained as exact declaration evidence but does not create an income/cash-flow revision and is not a formula-year input.

The operation verifies the period declaration hash, publication date, source snapshot/tree/provenance, official report hash, debt value and D&A value. It does not recompute debt from the limited provider balance fields or substitute raw nulls.

## 12. Frozen output identities

The canonical bodies above produce:

| Period | Kind | Revision ID |
| --- | --- | --- |
| `20181231` | `BALANCE` | `sha256:c3be5c3de8b458180a350e8e0c84ba3618fc23393c51817e1c2fd823f9cf4148` |
| `20191231` | `INCOME` | `sha256:176122a6db10c8ee7ec20eb2862632dc19cbdae9d1e1537c0a98708d3ac5b231` |
| `20191231` | `BALANCE` | `sha256:c898675a1b7b5db86cf7d4db1cace6fb27045f4214ea351a3ef4974523f0e7b3` |
| `20191231` | `CASH_FLOW` | `sha256:22438762ffb7532e9653d354686eae61b3812172e4868825f87691ccc5cd1349` |
| `20201231` | `INCOME` | `sha256:35d35b0856b6cecb8d8bb79c21d48058e44fcc51f6a7bd6c9c23a73a26b4a0ca` |
| `20201231` | `BALANCE` | `sha256:f883c487f930e3a58706965678bebabbb3fc5f200e2304fc521d3d4ace2ed7b6` |
| `20201231` | `CASH_FLOW` | `sha256:7d991e01d78363478e53a95401156a9f035120ae393c96cfcbccd680d80393b1` |
| `20221231` | `INCOME` | `sha256:ad1037c494eb4e79f215c4a342d814a5f3478ffcc1042bce61cc570b16ce761f` |
| `20221231` | `BALANCE` | `sha256:b3b9a5f5bf4dcdbfdeed4e9a2f53a6bfdc5f72655c7cbe3bdb521364bee5c396` |
| `20221231` | `CASH_FLOW` | `sha256:7812b0f8fd492e70a6a4aaa23dff33dbd0a4db9bf347b19e403bc3d55eb0387b` |

| Period | Outcome identity |
| --- | --- |
| `20181231` observation set | `sha256:20638846aa5eb0c98e30efcae5693114553ef8794a2697783d740ec658d38c68` |
| `20191231` observation set | `sha256:02bb2571ea9cef06465f0151b747004c34f4baa35b5d59b63e71f65c707fd7d1` |
| `20201231` observation set | `sha256:2c6110a07d2a7c80745a3cabf35b84b4aeb13f1cd4901d53c24cca619c40f4ce` |
| `20211231` normalization failure | `sha256:2cedd67871396e99f324623540ac66f1b254d31020d0e81ba075c6b5876bbc82` |
| `20221231` observation set | `sha256:92d196719be464dc79938db432f442e2d56891effd04adb7e11031f6e31fe736` |

Any body-field, tuple-order, null/conflict, availability-source or nested-identity change must change these hashes or fail reconstruction.

## 13. Failure precedence

Exact normalization codes:

```text
INPUT_MISMATCH
DECLARATION_MISMATCH
SOURCE_IDENTITY_MISMATCH
DEBT_SCOPE_INCOMPLETE
SOURCE_RESPONSE_INVALID
SOURCE_ROW_SET_MISMATCH
STATEMENT_CONTEXT_MISMATCH
PRESENTATION_CONFLICT
DECLARATION_SUPPLEMENT_MISMATCH
AVAILABILITY_MISMATCH
RESULT_RECONSTRUCTION_MISMATCH
```

`SourceSnapshotFailureCode` is preserved unchanged.

| Priority | Predicate | Result |
| ---: | --- | --- |
| 1 | either argument is not its exact declared class | `INPUT_MISMATCH`, period `None` |
| 2 | exact-class SourceSnapshot nested member/provenance reconstruction fails | `INPUT_MISMATCH`, period `None` |
| 3 | exact-class declaration outcome cannot be reconstructed | `DECLARATION_MISMATCH`, period `None` |
| 4 | reconstructed SourceSnapshot verification failure | nested `SourceSnapshotFailureCode`, preserving the period from the reconstructed outcome |
| 5 | snapshot/tree/provenance mismatch | `SOURCE_IDENTITY_MISMATCH` |
| 6 | exact canonical 2021 declaration conflict | `DEBT_SCOPE_INCOMPLETE` with reconstructed declaration failure |
| 7 | noncanonical declaration failure/success binding or unsupported period | `DECLARATION_MISMATCH` |
| 8 | member/envelope/field/primitive shape mismatch | `SOURCE_RESPONSE_INVALID` |
| 9 | member hash, row hash or cardinality mismatch | `SOURCE_ROW_SET_MISMATCH` |
| 10 | issuer/announcement/period/report/company context mismatch | `STATEMENT_CONTEXT_MISMATCH` |
| 11 | duplicate rows differ outside exact allowed fields or 2022 advisory tuple mismatches | `PRESENTATION_CONFLICT` |
| 12 | declaration date/report/debt/D&A binding mismatch | `DECLARATION_SUPPLEMENT_MISMATCH` |
| 13 | period availability instant/source tuple mismatch | `AVAILABILITY_MISMATCH` |
| 14 | revision/set/outcome reconstruction or hash mismatch | `RESULT_RECONSTRUCTION_MISMATCH` |

Every failure returns no partial revision/set.

Only `DEBT_SCOPE_INCOMPLETE` stores the exact nested declaration failure. Every other normalization failure stores `declaration_failure=None`.

## 14. Exact write set

Create one Backtest worktree stacked on PR #7 and add only:

- `packages/market-bundle-builder/src/crypto_quant_bundle_builder/gree_historical_financial_statement_normalization_v1.py`;
- `tests/bundle_builder/providers/tushare/test_gree_historical_financial_statement_normalization_v1.py`;
- `tests/architecture/test_gree_historical_financial_statement_normalization_v1_boundary.py`.

No root export, lock, dependency or existing file change. Every base file at `25b8dd12a8a62530ce2467e13d1bd0b55b34b0cf` remains byte/mode identical.

The architecture test reuses PR #7's exact base-tree and write-set algorithm and changes only the base commit plus the three allowed new paths.

## 15. Acceptance

1. four exact success sets and frozen revision/set hashes;
2. exact 2021 nested conflict/failure hash and no revision/set;
3. exact 2018 balance-only shape and no fabricated statement trio;
4. duplicate collapse for every exact update-flag pair;
5. 2022 `free_cashflow` conflict retained with row-hash/flag/value mapping and normalized null;
6. any other duplicate economic difference fails `PRESENTATION_CONFLICT`;
7. decimal-token versus quoted-string distinction preserved;
8. exact member/envelope/field/row/context/cardinality mutation coverage;
9. exact raw null/unresolved/advisory tuples and line-item hashes;
10. exact declaration debt/D&A/publication/report binding;
11. exact availability instant/source-hash tuples;
12. forged nested SourceSnapshot/declaration outcome/advisory observation/conflict/revision/set/failure rejected;
13. input/member/row order noninterference;
14. no I/O/PDF/Calendar/provider/Runtime/Trading/Market Data import;
15. PRs #1–#7 files plus 2023 declaration/normalization/selection identities unchanged;
16. focused + opt-in real artifact + Builder-wide + broad regression;
17. independent review before commit/push;
18. real publication writes four observation sets, one canonical 2021 failure and one manifest to a fresh directory.

## 16. Validation commands

Focused:

```bash
uv run --project packages/market-bundle-builder pytest -q \
  tests/bundle_builder/providers/tushare/test_gree_historical_financial_statement_normalization_v1.py \
  tests/architecture/test_gree_historical_financial_statement_normalization_v1_boundary.py
```

Real opt-in:

```bash
QB_GREE_HISTORICAL_SOURCE_ROOT=/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/source-snapshots/000651.SZ/2018-2022/v3-candidate-01 \
uv run --project packages/market-bundle-builder pytest -q \
  tests/bundle_builder/providers/tushare/test_gree_historical_financial_statement_normalization_v1.py \
  -k real
```

Builder-wide without incompatible predecessor write-set guards:

```bash
uv run --project packages/market-bundle-builder pytest -q \
  tests/bundle_builder \
  tests/architecture/test_gree_historical_financial_statement_normalization_v1_boundary.py
```

Broad regression temporarily links the Platform consumer fixture at `/home/ygguo/agent-projs/ai-crypt/tests/contracts/backtest-consumer-port-v1.json`, removes the link after the run, and deselects exactly thirteen incompatible historical candidate write-set guards: the eight repository-global guards plus the five PR #3–#7 guards. The new PR #8 guard remains enabled.

The accepted run produced `2579 passed, 5 skipped, 13 deselected`. An earlier retry terminated in unrelated Python 3.13 garbage collection with exit `139`; the clean rerun is controlling. No guard was edited or deleted.

Run LSP/lens on the exact three-file write set before commit.

## 17. Real publication target

Fresh root only:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  normalized-observation-sets/000651.SZ/2018-2022/v1-candidate-02
```

Exact files:

```text
20181231-observation-set.json
20191231-observation-set.json
20201231-observation-set.json
20211231-failure.json
20221231-observation-set.json
manifest.json
```

Publication is atomic. Existing 2023 observation set and historical declaration roots are read-only predecessors. Credential strings and token paths must be absent from all bytes.

`v1-candidate-01` is noncanonical and must never be consumed: its data files matched the frozen outputs, but its manifest bound an incorrect implementation commit. It remains preserved as failed evidence. `v1-candidate-02` is the first valid candidate.

## 18. Forbidden paths

- no 2021 declaration or normalization success;
- no selection of update-flag `1` as latest/final;
- no selection of either 2022 provider `free_cashflow` value;
- no raw null-to-zero rule;
- no recomputation of official debt from incomplete provider fields;
- no generic SZSE Calendar claim;
- no private formula/PnL/Strategy work;
- no modification of predecessor modules/tests/locks;
- no merge, acceptance, deployment or real-trading authority.

## 19. Implementation evidence

Stacked Backtest PR [#8](https://github.com/YungeG/quant-backtest/pull/8):

- commit `bac94d56272d3d3aa1172c052c855d4fb46a4356`;
- exact three-file additive write set; PR #7 base tree byte/mode identical;
- focused `16 passed, 1 skipped`;
- real opt-in `2 passed`;
- Builder-wide `377 passed, 5 skipped`;
- broad `2579 passed, 5 skipped, 13 deselected`;
- LSP/lens clean;
- independent implementation review accepted after exact nested-failure and member-hash mutation blockers were fixed.

Published valid candidate:

```text
/srv/bcache-8t/ygguo/quant/artifacts/a-share-quality-bband/
  normalized-observation-sets/000651.SZ/2018-2022/v1-candidate-02
```

- 2018 set file `sha256:0f327ffaa9330260f953280f524fcbce65d6900e2938aba18ce270513f54b720`;
- 2019 set file `sha256:09dfb83c3f7a850d31e7ae4989936f0466fb1a27b50a75676326738c151ff560`;
- 2020 set file `sha256:5fb6d3c1697578bc9d3efa65800ca31ab5436d877f7700c94d196c34e675df0d`;
- 2021 failure file `sha256:a8c964c65c967bef8a07a1a1dd0d2114edb63ccd87d6aded1e0b566f6e0a5f0f`;
- 2022 set file `sha256:a632b01e64dc34c0ba6e216775bd5ac77f223f7f1ae25f3fb98d2bb29e3f3566`;
- manifest file `sha256:ff3cd00543d961721f8fd1fa3358950a7e7027bb4e37c1b4e10c3eff2326be98`;
- canonical regeneration/readback, mode `0600`, directory `0700` and credential-exclusion checks passed.

## 20. Next handoff

[`research/quality-bband-historical-formula-coverage-v1.md`](../../research/quality-bband-historical-formula-coverage-v1.md) proves that only 2019/2020/2023 ROIC inputs are complete and that 2022 also loses its prior capital endpoint. Further selector/formula code is deferred until competent authority resolves 2021 debt scope. PR #8 and all predecessors remain unaccepted; no Strategy, Validation or deployment authority is granted.
