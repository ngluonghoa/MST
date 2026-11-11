# MST M3/M4 Cache V2.1 P0 — Synthetic Source Revision / First-Known / As-Of Custody

Date: 2026-11-11 Asia/Ho_Chi_Minh
Status: DESIGN + GITHUB-HOSTED SYNTHETIC QA ONLY. ALL LIVE DATA RIGHTS, REAL DRIVE MARKET CACHE, RELEASE AND TRADING NO-GO.

## Scope and risk addressed

Previous P0 checkpoint proved 96 separately dated candidate V2 partitions over 16 invented days and six TFs, including original V1 EMA20 / ATR14 carry. It **did not prove genuine history first-known**, official HOSE/HNX/UPCOM trading calendar or source revision issuer custody. A deterministic SHA chain built by code is NOT a vendor signature or independently protected rollback floor.

New additive Python module scripts/m4_v21_source_revision_asof_ledger_lab.py explicitly distinguishes a toy M5 bar's market-valid slot from its first-known observation time; it records generations and revisions, chained local hashes, content vs metadata-only changes and tombstones. All versions are entirely fabricated. No vendor endpoints, real quotes, credentials or network. It preserves the existing strict one-day FixtureV2ConsumerScope and policy binding without altering source modules.

## Synthetic invariants

- Input: 16 wholly fabricated days including weekends; 48 M5 rows/day, two 2h segments separated by 2h artificial gap, 768 fake source rows total.
- Observation events: 768 initial events, a late price/high correction and a later metadata-only revision: 770 untrusted ledger events. Each event preserves its declared M5 time slot, exact per-date V1→V2 scope, policy SHA, generation, revision, first-known UTC time and previous local SHA.
- Three time-specific snapshots: before the price correction, after price, after metadata. A revision is not visible in a historical as-of read until its first-known timestamp. Missing, open, retracted or future-unknown rows cannot be promoted to a falsely complete history.
- The price correction changes numerical OHLCV, metadata-only does not change numeric OHLCV. Results across six TFs continue to match inherited V1 full_recompute and independent Decimal EMA20/ATR14 oracle. H4/D1 artificial grouping is NOT exchange-authenticated.
- Strict candidate rejection of source/generation replay, first-known time rewind, invalid M5 slot, mixed provider/basis/rights scope, incorrect event kind, forged local SHA, tombstones and caller attempts to self-assert official calendar, vendor entitlement or issuer authentication.
- All positive results mean only that synthetic fixture logic is internally consistent, NOT that any actual exchange/provider correction was ever authenticated or cached.

## Files and CI

- scripts/m4_v21_source_revision_asof_ledger_lab.py
- tests/test_m4_v21_source_revision_asof_ledger_lab.py (47 focused synthetic tests)
- .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml (existing workflow extension)
- docs/MST_M4_V21_BITEMPORAL_SOURCE_CUSTODY_QA_20261111.md (this report)
- Expected focused methods: previous 425 + 47 = **472 only if exact-head dedicated QA PASS**; not the repository-wide test total.

## Governance / explicit NO-GO

All toy claims of authenticated official calendar, market license, issuer signatures, permitted cloud retention, independent monotonic rollback floor, cross-run two-writer CAS, Google Drive quote-cache read/write, production ABI, release and trading remain **FALSE**.

M3 Issue #9 requires independently documented SSI/DNSE/VCBS real endpoint entitlements, format and historical calendar/source correction policy. M4 Issue #10 requires source-approved Google Drive retention, physically verified read/write, protected external signer/floor and independently authenticated multiwriter CAS before production. ChatGPT account connectivity or client-reported metadata alone proves none of these.

The pinned Swing Trading original code, MST protected main and original 63 V1 + eight pre-existing opt-in V2 Python sources must be byte-preserved. Draft PR #8 stays unmerged. Do not reinterpret a green synthetic test as approval to connect live feeds or publish licensed OHLCV.

## Verification checkpoint

GitHub PR: https://github.com/ngluonghoa/MST/pull/8
M3: https://github.com/ngluonghoa/MST/issues/9
M4: https://github.com/ngluonghoa/MST/issues/10

Record implementation and final report-containing exact SHA, independent full GitHub PR Actions outcomes (expected 47 workflows), new 47-test job result, Foundation Python 3.11/3.12, and compare diff to the previous accepted 6a7e69add6ff7389635722efcd826826dcf95c1e. Do NOT claim PASS while pending, failed or missing.

Next P0: review external vendor contracts and genuine venue trading calendar/auction/holiday/correction rules; thereafter specify actual issuer-authenticated source revisions and protected Cloud persistence/CAS in separately approved ABI. No live capture pending licensing proof.
