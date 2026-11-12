# MST Cache V2.1 P0 — Multi-segment artificial trading day + actual inherited V1 numerical EMA20/ATR14 parity

Date: 2026-11-11 Asia/Ho_Chi_Minh
Scope: opt-in Cloud-only synthetic tests; user-approved V2.1 P0/P1/P2 design backlog. NO provider market-data licence, official calendar, real Google Drive OHLCV cache, merger or trading.

## Why this is materially different from previous 44-test six-TF mapping
Existing tests/test_m4_v21_six_tf_causal_slices.py proved which six-TF windows/indicator suffixes **would** change in a fictional no-break 8h session. The new suite actually invokes **original unmodified Swing Trading V1 SyntheticIncrementalStore** on GitHub Actions ephemeral SQLite, verifies its incremental EMA20 and Wilder ATR14 against BOTH inherited full_recompute and the **independently coded** Decimal oracle. It combines an existing A03 candidate multi-segment session screen with strict toy AM/PM source slots and tests source M5 corrections, numeric indicator tails and metadata-only provenance.

## Explicit test-only 2h + gap + 2h topology
Fabricated single local day 2026-11-09:
- Continuous AM: 09:00–11:00 Asia/Ho_Chi_Minh, **24** made-up M5 candles.
- Nontrading gap: 11:00–13:00, **no** M5 candles; a noon candle cannot be admitted.
- Continuous PM: 13:00–15:00, **24** made-up M5 candles.
- 48 source M5 records, 16 M15, 8 M30, 4 H1, 1 H4 and 1 D1 **toy** higher-TF group = 78 candidate windows total.
- M15/M30/H1 constituent M5 groups MUST stay strictly within AM or PM; H4 and D1 are deliberately called **fictitious stitched trading-minute groups across the gap**. These are neither official H4 closing/aggregation nor actual HOSE/HNX/UPCOM D1 shapes, and must never be promoted as source-provider bars.
- All 6 TF identities use inherited V1 full policy versions; standalone candidate V2 partition hash cannot approve reuse after rights, calendar or indicator policy change. No cross-provider storage.
- The officially documented HNX market schedule includes different market/venue phases (listed vs UPCoM, including auction) and exchange publications may change. Public hours alone cannot sign historical issuer-as-of data or source-specific bar semantics. For information, see https://www.gov.hnx.vn/vi-vn/hoi-dap.html ; this test NEVER marks a calendar as authenticated.

## Actual numerical QA (not just planned invalidation)
1. COLD: insert manufactured full closed sequence per TF into six separate V1 synthetic SQLite partitions, confirm all EMA20 and ATR14 checkpoints match inherited full recompute and independent Decimal oracle.
2. PRICE CORRECTION: after the toy session closes, amend fabricated source M5 index 20 with a clearly artificial +150 Decimal close/high change, first-known after prior checkpoint. This changes exactly one grouped source bar on each of six TFs; original V1 transactional incremental write recomputes exactly 28 M5 +10 M15 +5 M30 +3 H1 +1 H4 +1 D1 = **48** causally affected indicator checkpoints. Verify identical unchanged prefix and exact equality of all recalculated values to independent EMA/ATR oracle.
3. METADATA ONLY: amend fake M5 index30 revision/first-known (unchanged OHLCV); inherited V1 persists lineage but recomputes **zero** numerical checkpoints on all six TFs. Verify all persisted numeric checkpoints still equal both cold and independent references.
4. Expected ATR14 activation is at **bar #14** of a TF. In this single toy day, ATR14 becomes defined on M5 and M15 only (48 and 16 groups). It remains undefined on M30 (8), H1 (4), H4 (1), D1 (1). Do NOT claim numeric ATR14 was exercised on TFs with under 14 bars; EMA20 recursion and expected ATR14 None are compared there.
5. 46 negative/positive unit methods additionally reject missing, duplicated, open, gap or cross-break M5 data, wrong window membership, missing or partial higher TFs, wrong provider/policy/calendar binding, auction treated as continuous, caller self-proclaimed official calendar and unauthorized trade flags.
6. Actual SQLite state exists only on ephemeral GitHub Actions runner. No licensed provider records, no Google Drive market payload, no official exchange as-of/first-known ledger, external signed witness/floor or production trading.

## Implementation and governance
Add scripts/m4_v21_gap_v1_numeric_parity_lab.py and tests/test_m4_v21_gap_v1_numeric_parity_lab.py and this document. Extend existing .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml (do not create workflow). Preserve exact upstream source pin cd90c1babae8912db31490ad614fc2ad2f868042 and MST main 4048f91beaaa3410116d97e35896c8b688384e19; 63 V1 and 8 existing opt-in V2 source modules untouched; Draft PR #8 unmerged.

Canonical upstream SHA verified: `cd90c1babae8912db31490ad614fc2ad2f868042`; the original V1 modules remain untouched.

## Pending CI and next gate
New tests: 46; prior focused tests: 289. Expected targeted count after successful CI: 335. No PASS claim until exact PR code/report HEAD CI readback. Actual historical exchange calendar by venue/source, corporate action adjustment, correction issuer as-of record and legal Drive market data retention remain pending M3. Physical Drive test only after M4 protected independent witness/high-water/CAS and owner signoff, not by unit tests.

PR https://github.com/ngluonghoa/MST/pull/8
M3 https://github.com/ngluonghoa/MST/issues/9
M4 https://github.com/ngluonghoa/MST/issues/10

## Remote implementation-head verification — 2026-11-11

Code commit `97c267f4155c7917839e5780beb5251a5850fe2a` independently has **47/47 pull-request workflows COMPLETED SUCCESS**, including [dedicated P0 gap + actual inherited-V1 numerical parity CI #42948700215](https://github.com/ngluonghoa/MST/actions/runs/42948700215), which ran **46/46 new test methods PASS** and executed the actual_v1_numeric_fixture() report validation. [Foundation CI #42948700242](https://github.com/ngluonghoa/MST/actions/runs/42948700242) finished SUCCESS on Python 3.11, Python 3.12, engineering/contract/wheel. Prior **289** targeted tests unchanged, cumulative **335 targeted** (not the whole repository test count). The submitted full-policy original-source 63 V1 / 8 prior opt-in V2 bytes and protected main stayed unchanged.

Important scientific scope: original V1 fixture-generated M5/M15 EMA20/ATR14 numeric checkpoint output matches an independent Decimal oracle, with 48 causal checkpoints across six TFs. ATR14 is seeded on M5/M15 only in this tiny synthetic day; M30/H1/H4/D1 have fewer than 14 observations and preserve the correct `None` (not validated numerical ATR values). H4/D1 cross-gap groups are explicitly fictional, not official market bars. No source license/calendar/issuer, real Drive persistence, external monotonic signer/CAS or production rights. **This report-containing follow-on commit requires separate exact-head 47/47 readback before it is independently accepted.**
