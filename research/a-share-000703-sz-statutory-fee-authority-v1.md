# 000703.SZ statutory fee/tax authority — source audit v1

> Archive note (2026-09-22): Preserved research/probe record, not a fresh authority or readiness assessment. “Current/now” and reported passes refer to the original task; external sources, entitlements, retained artifacts and historical availability were not revalidated for this archival commit. Referenced `backtest/evidence/` files are local and are not published here. No new sample consumption, capture, Backtest, qualification or trading authorization follows.

**Research date:** 2026-09-02\
**Scope:** ordinary Shenzhen A-share cash trades in `000703.SZ` for the planned research windows: discovery `[2024-01-02, 2026-01-01)` and OOS `[2026-01-01, 2026-09-01)`. This is a source-authority audit, not a fee-model implementation or a live-trading instruction.

## Decision

The official rate sources now support a **development-only statutory charge matrix** for ordinary Shenzhen A-share trades. It remains **NOT READY for an account-accurate total-cost/PnL rule**: broker pass-through, aggregation, and rounding are still unbound, and neither the ChinaClear nor SZSE schedule is an explicit non-amendment certificate through 2026-09-01.

Do not infer any component as zero, and do not combine the user-provided commission scenarios with an account-accurate statutory total until the broker schedule is captured.

## Source-authorized components

| Component | Side / base | Rate and effective interval supported by primary source | Evidence | Backtest status |
| --- | --- | --- | --- | --- |
| Securities transaction stamp duty | **Sell only**; transaction amount/proceeds | The Stamp Tax Law defines the tax base as transaction amount and levies securities-transaction stamp duty on the transferor, not the transferee. The statutory rate table is `1‰`; MOF/STA Announcement 2023 No. 39 halves the securities-transaction stamp duty from **2023-08-28**, yielding **`0.5‰` sell-side** for all dates in scope absent a later change. | [1], [2] | Source-authorized component; do not silently round. |
| SZSE securities transaction handling fee (`证券交易经手费`) | Both buy and sell; trade value | CSRC says that, from **2023-08-28**, Shanghai/Shenzhen A/B-share handling moved from `0.00487%` to **`0.00341%`** on both sides. SZSE’s investor fee table independently lists A-share handling at **`0.0341‰`** on both sides and repeats the 2023-08-28 effective date. | [3], [4] | Source-authorized component; no duration/end date is stated in either source. |
| Securities transaction regulatory levy (`证券交易监管费`) | Both buy and sell; trade value | NDRC/MOF Notice `发改价格规〔2018〕917号` sets the charge for Shanghai/Shenzhen exchanges at **`0.02‰` of stock transaction value**, effective **2018-01-01**. SZSE’s investor table separately lists A shares at `0.02‰` on both sides and says it is collected for CSRC. | [4], [5] | Source-authorized development component. The 2018 rate notice does not itself specify the investor-side pass-through or a 2026 expiry. |
| ChinaClear transaction transfer fee (`交易过户费`) | Both buy and sell; trade value | ChinaClear’s 2022-04-28 notice reduces Shanghai/Shenzhen A-share transaction-transfer fee to **`0.01‰`** on both sides from **2022-04-29**. ChinaClear’s Shenzhen schedule updated 2026-01-01 repeats the ordinary A-share `0.01‰` bilateral entry. | [6], [7] | Source-authorized development component for ordinary on-exchange Shenzhen A shares; exclude the separately priced comprehensive-agreement-platform case. |

### Arithmetic notation only (not an approved complete fee rule)

For a sell notional `N` during either requested window, the source-authorized development components sum to:

`N × (0.5‰ + 0.0341‰ + 0.02‰ + 0.01‰) = N × 0.0005641`

For a buy notional `N`, those components sum to:

`N × (0.0341‰ + 0.02‰ + 0.01‰) = N × 0.0000641`

These expressions intentionally exclude the user-provided commission scenario, broker-specific pass-through/aggregation, minimums, and rounding. They are not an account-accurate total simulated cost.

## Unresolved items that block a complete statutory rule

| Item | What primary evidence establishes | Gap / required resolution |
| --- | --- | --- |
| Formal point-in-time non-amendment evidence | The NDRC notice has an explicit 2018 effective date; ChinaClear’s 2026-01-01 Shenzhen schedule repeats the transfer-fee rate; SZSE’s current investor table repeats the regulatory-levy rate. | No retrieved source expressly certifies that the schedules remain unamended through 2026-09-01. Before a decision-grade claim, capture a schedule/notice dated on or after the OOS end or a formal no-change confirmation. |
| Retail billing / rounding / aggregation | SZSE labels its schedule’s relevant rows as investor charges; CSRC also said brokers would adjust client contracts/parameters after the 2023 handling-fee cut. | Bind the actual broker/client fee schedule (whether and how the exchange/depository items are passed through, tax-inclusive treatment, per-fill vs order/day aggregation, precision and rounding). No brokerage was selected. |
| Commission | The user supplied scenario assumptions: 3/5/8 bps, CNY 5 minimum. | These are **scenario inputs**, not statutory authority; keep them distinct from this audit. |

## Sources

1. **State Taxation Administration — _Stamp Tax Law of the People’s Republic of China_** (effective 2022-07-01): defines securities transactions as exchange-traded stock/stock-based DR transfers; imposes stamp duty on the transferor; sets the transaction amount as the tax base; and refers to the attached rate table.\
   <https://fgk.chinatax.gov.cn/zcfgk/c100009/c5193058/content.html>
2. **Ministry of Finance / State Taxation Administration — Announcement 2023 No. 39, _Announcement on halving securities transaction stamp duty_** (2023-08-27): effective 2023-08-28, securities transaction stamp duty is halved.\
   <https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html>
3. **CSRC — _Shanghai, Shenzhen and Beijing exchanges further reduce securities transaction handling fees_** (2023-08-18): from 2023-08-28, Shanghai/Shenzhen A/B-share handling fee changes from `0.00487%` to `0.00341%`, both sides.\
   <http://www.csrc.gov.cn/csrc/c100028/c7426794/content.shtml>
4. **Shenzhen Stock Exchange — _Fee and taxes collected on behalf_ / investor fee table**: A-share `证券交易经手费` is `0.0341‰` on both sides; it also states the 2023-08-28 reduction. The same table lists the current `证券交易监管费` at `0.02‰` on both sides, collected for CSRC.\
   <https://www.szse.cn/marketServices/deal/payFees/index.html>
5. **NDRC / MOF — _Notice on matters including regulatory-fee standards for the securities and futures industry_ (`发改价格规〔2018〕917号`)**: sets the stock-transaction regulatory levy paid by Shanghai/Shenzhen exchanges at `0.02‰`; effective 2018-01-01.\
   <https://www.ndrc.gov.cn/xxgk/zcfb/ghxwj/201806/t20180627_960950.html?code=>
6. **ChinaClear — _Notice on reducing stock transaction-transfer-fee standards_** (2022-04-28): from 2022-04-29, Shanghai/Shenzhen A-share transfer fee is `0.01‰` of trade value on both sides.\
   <http://www.chinaclear.cn/zdjs/gszb/202204/837e3c5031104aa099d6597ba381342a.shtml>
7. **ChinaClear — _Shenzhen market securities registration and settlement business fee and taxes-collected-on-behalf schedule_** (updated 2026-01-01): repeats ordinary A-share transaction-transfer fee of `0.01‰` to both buyer and seller.\
   <http://www.chinaclear.cn/zdjs/fbzyls/202512/a59388fbfa714c5fa546784891a42e30/files/%E6%B7%B1%E5%9C%B3%E5%B8%82%E5%9C%BA%E8%AF%81%E5%88%B8%E7%99%BB%E8%AE%B0%E7%BB%93%E7%AE%97%E4%B8%9A%E5%8A%A1%E6%94%B6%E8%B4%B9%E5%8F%8A%E4%BB%A3%E6%94%B6%E7%A8%8E%E8%B4%B9%E4%B8%80%E8%A7%88%E8%A1%A8.pdf>

## Next evidence gate

Before any intraday PnL run that claims account-accurate total costs, capture the chosen broker’s pass-through/rounding schedule and a point-in-time fee schedule dated on or after the OOS end. Re-evaluate if a notice changes any charge after the research date.
