# MST A03 — VCBS / SSI true intraday clock-price observations, reference-only nonpromotion

Date: 2026-11-11 Asia/Ho_Chi_Minh (15:44+ local post-session). Source: read-only user-connected ChatGPT MCP actions, not GitHub Actions service identity. Handoff §§95–103 and §118 reread before capture. MST locked indicator/trading timeframes remain M5/M15/M30/H1/H4/D1. Native closed minute bars and provider source rights remain UNVERIFIED.

## Real connected source evidence — 11 November 2026

Read user-connected VCBS `vcbs_get_intraday_history` for FPT/DCM/HPG and SSI `marketdata_list_intraday_stock_infor` (one day only, toDate=11/11/2026) for the same three tickers. Six read-only calls completed. Compare **clock strings** HH:MM:SS in the two responses in memory only. This does NOT verify both vendors use the same start/end timestamp semantics, that the market data was first published in that minute, or that any raw tick is a complete native M1 bar.

| symbol | VCBS `series` price points | SSI intraday OHLCV-shaped rows | exact shared clock strings | price equal | price different |
|---|---:|---:|---:|---:|---:|
| FPT | 226 | 226 | 226 | 209 | 17 |
| DCM | 203 | 203 | 203 | 201 | 2 |
| HPG | 226 | 226 | 226 | 221 | 5 |
| **total** | **655** | **655** | **655** | **631** | **24** |

At VCBS, each `series` item has keys exactly `time` and `price`, NOT an intra-minute open/high/low/close/volume pair. `open`, `high`, `low`, `last` are board/session-level; `ohlcSource=price_board_live`, and `ohlcProvisional=false` merely describes session board OHLC state, NOT native individual M1/M5 closure. `totalVolume` is single whole-session cumulative volume with `recent_volume_scope=cumulative_session_matched`, NOT per-minute quantity. SSI had fields `open/high/low/close/volume/trading_date` per row, but no native timeframe enum, authenticated bar label semantics or issuer first-known. Both appeared to share clock sets for these three examples; that can still be coincidental under different data definitions. SSI `close` compared to VCBS `price` is a reference contrast only, not a certified 1-minute close cross-check.

All 655 observed clock strings matched for these three selected symbols on this specific day, yet 24 source prices differ. That immediately rejects an assumption that a common minute label means every vendor source point is the same native closed-bar price. Some intervals contain non-60-second gaps (two adjacent nonminute gaps for FPT and HPG; 20 for DCM). They are not independently proven missing native bars: no-trade intervals, break, auction and source sampling are possible; do not synthesize missing OHLCV, volume or candles from point gaps. No independent publisher-certified adjustment, correction or original publication timestamp was supplied in these connected calls.

We do not infer which source is wrong from a disagreement, nor use numeric coincidence as a right to promote a VCBS price point to M1/M5 OHLCV. Session `ohlcProvisional=false`, the passage of 15:00 market time, and timestamp agreement do not provide an M5 close event or source-first-known history.

## Strict Cloud QA change

New additive pure Python `scripts/m2_a03_vcbs_ssi_minute_reference_audit_lab.py` and `tests/test_m2_a03_vcbs_ssi_minute_reference_audit_lab.py` contain **50 completely fictional** validation/negative tests: exact source boundary, date/clock tags, absent/duplicate/unbounded price points, injected per-minute OHLCV fields, source symbol/scope mismatch, nonfinite/negative values, wrong volume/currency, SSI OHLC envelope and missing per-row volume, unmatched clock sets, 1/3 fake mismatch, and even all-equal artificial clock prices still NEVER becoming authentic VCBS OHLCV/closed M5/Cache/market trading authority. CI artifact is sanitized synthetic count receipt, no token/timestamp/source prices.

The existing Draft PR8 unprivileged `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml` gains this test and report only, with cloud-hosted GitHub CI (no Mac/MOCHI/local). Original 63 source-locked V1 and eight preexisting opt-in V2 source modules remain byte-preserved; no protected-main merge.

This new real 11 November comparison was in temporary memory; it is NOT added as raw quotes to public GitHub or to the 180 previously saved FPT/DCM/HPG × three-provider D1 private snapshot rows. Existing D1 Google Drive quarantine data remain unchanged. No VCBS M5/H4 or other intraday OHLCV source is assumed to exist.

## Gates that remain explicitly OPEN / NO-GO

Actual SSI/DNSE/VCBS native authenticated M5/M15/M30/H1/H4 candle producer capability in cloud runner, rights for automated Cloud vendor data access and off-platform retention, official historical venue calendar with lunch/ATO/ATC/no-trades/halts, per-provider source timestamp label/closure and correction-first-known, independent WIF GitHub→Google SA→Drive credential validation, source issuer and protected CAS/anti-rollback signer/floor, approved production cache/source ABI and user-authorized trading.

The live reference-only finding can be used as a **negative data quality guard**, not to bootstrap any real signal or historical Cache acceptance.

Prior green Draft PR8 checkpoint: `6e7bb969be8cd3926497e278ef224a80e9dd5a5d`, 47/47 workflows PASS, 781 cumulative focused synthetic tests. DO NOT report new 50 tests/47 green at new HEAD without exact GitHub Actions readback.

GitHub PR: https://github.com/ngluonghoa/MST/pull/8
Master Handoff: https://docs.google.com/document/d/19Dzpe0JSCm72wFx97_8IY5g-MLcJeUzO-9IxvnEI_Fw/edit
M3 issue: https://github.com/ngluonghoa/MST/issues/9
M4 issue: https://github.com/ngluonghoa/MST/issues/10
