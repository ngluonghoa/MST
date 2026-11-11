# MST Cache V2.1 P0 — 16 invented sessions, real inherited V1 Decimal EMA20/Wilder ATR14 numerical parity on all 6 TFs

Date: 2026-11-11 Asia/Ho_Chi_Minh
Status: 100% TEST-ONLY GitHub Actions synthetic and independent V1 numerical reference; no licensed market-source/Google Drive OHLCV/production/trading authorization.

## Material advancement
Previous two-segment one-day fixture (46 tests) verified actual V1 EMA20 numeric and actual ATR14 only at M5/M15. Higher M30/H1/H4/D1 had fewer than 14 observations, so ATR14 was NULL. New **54-test additive synthetic suite** extends to **16 entirely fictional consecutive calendar days (weekends included on purpose)**, repeating the prior fake 09:00–11:00 and 13:00–15:00 AM/PM slots with a 2-hour break. This is NOT a claimed HOSE/HNX/UPCOM trading calendar, holiday, settlement, auction, published historical as-of, official H4/D1 provider policy, venue authority or legitimate market-data retention basis.

Every fake day has 48 precisely declared closed M5 candles; total 768 source M5; six derived test-only grids M5=768, M15=256, M30=128, H1=64, H4=16, D1=16 (1248 materialized candle windows). M15/M30/H1 never cross the declared break. H4/D1 are deliberately not official: fictitious stitched trading-minute/AM-PM groups whose timeline spans the break, and multi-day partitions are a SINGLE fake cache scope, not production per-day physical partitions.

## Real original-V1 numeric indicator checks on fabricated OHLCV
- Implements scripts/m4_v21_multiday_all_tf_atr14_oracle_lab.py and tests/test_m4_v21_multiday_all_tf_atr14_oracle_lab.py only. The untouched original Swing Trading V1 SyntheticIncrementalStore is used for incremental operations in ephemeral GitHub Actions SQLite. Its persisted EMA20/Wilder ATR14 checkpoints are compared to both inherited full_recompute and the independently coded Decimal oracle.
- Cold build of 16 toy days per TF must have precisely its declared windows and a valid numerical ATR14 starting at zero-based ordinal 13 (the 14th closed bar) across **all six TFs**, including H4/D1. Verify ordinal12 ATR14=None, ordinal13 ATR14 Decimal, and final ATR14 Decimal.
- Reopen the synthetic SQLite file and verify persisted checkpoints are identical; no assertion of Google Drive custody or cross-run distributed durability.
- Invent a late price/high correction to the toy 14th-day AM M5 index20 (day ordinal13; first-known only after all 16 toy days closed), forcing one price/volume group per TF to change and the exact causal suffix sizes **124 M5 +42 M15 +21 M30 +11 H1 +3 H4 +3 D1 =204** actual V1 checkpoint recalculations. Earlier unaffected prefixes must remain byte-identical to the original persisted checkpoints. Corrected suffix values must equal both full V1 cold recomputation and independent Decimal oracle.
- Invent an independent metadata-only source revision on toy day ordinal14 PM M5 index30. OHLCV SHA stays the same while revision and first-known update. Every TF records lineage but recomputes zero numeric EMA20/ATR14 checkpoints and continues to equal both oracles.
- Deny duplicate, reordered, open, out-of-slot, missing bars or days, first-known-before-bar-close, false calendar authority, wrong provider or full V1 rights/calendar/indicator policy, and future-known input masquerading as previously observed.

## Science/governance constraints
This is genuine original V1 arithmetic **on entirely fabricated source rows**, not market feed verification. It validates EMA20/ATR14 across all six TFs under ONE artificial schedule and one seeded ATR14 example. It does not prove authentic real historical H4 or D1 closure, auction bar aggregation, holidays, halts, corporate action adjustment, licensed vendor retention, true as-of issuer revision/correction, Google Drive market cache read/write, independent protected witness/signer/floor, two-authorized-writer conditional CAS, deployment, signal execution or trading. Such cases still require separate M3 vendor evidence and M4 owner/live custody acceptance. No modification to any 63 inherited V1 / eight existing opt-in V2 source files or protected MST main. PR #8 Draft/unmerged.

## CI and traceability
54 new focused unit test methods, prior 335, expected cumulative 389 targeted **only after remote CI PASS**. Reuses .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml; no new workflow. GitHub full workflow and report-containing SHA must be independently checked before acceptance. Do not claim a % performance improvement; current tests check correctness, not production speed.

MST PR8 https://github.com/ngluonghoa/MST/pull/8
M4 Issue10 https://github.com/ngluonghoa/MST/issues/10
M3 Issue9 https://github.com/ngluonghoa/MST/issues/9
Swing source pin cd90c1babae8912db31490ad614fc2ad2f868042 ; MST main protected 4048f91beaaa3410116d97e35896c8b688384e19 .
