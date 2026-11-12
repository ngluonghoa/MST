# MST Cache V2.1 — Six timeframe source-window and causal checkpoint propagation QA (synthetic only)

Date: 2026-11-11 Asia/Ho_Chi_Minh
Owner scope: eight-point V2.1 P0/P1/P2 design-development accepted, NOT owner schema/ABI release, live source, Google Drive quote cache, provider legal retention or trading.

## Why this is needed
Prior P0-2 lab proved full V1-policy-bound dependency invalidation for a nine-node abstract DAG (28 tests). A real incremental derived cache additionally needs **window-level** membership: a correction to a single M5 source window can affect its containing M15/M30/H1/H4/D1 bar and all **later** EMA/ATR checkpoints within each timeframe. Recomputing only the directly changed bar would leave indicator tails stale; recomputing every bar on every timeframe would waste cloud resources.

## Implementation in opt-in scripts and test-only QA
- scripts/m4_v21_six_tf_causal_slices.py
- tests/test_m4_v21_six_tf_causal_slices.py
- Existing .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml extended; no new workflow, no original V1 or eight pre-existing V2 source file edits.
- **44 added unittest methods**: exact M5/M15/M30/H1/H4/D1 fixture membership, explicit source-bar boundaries and monotonic UTC, source cause versus indicator checkpoint suffix, multiple simultaneous revisions, policy-rights/calendar change deny, incomplete/open windows, wrong/duplicate TF windows, future/retroactive first-known, unrelated input, unknown source quarantine and retained no-go flags.

Artificial ONLY: **one invented 8-hour, uninterrupted session** with 96 declared closed M5 root windows; from these, 32 M15, 16 M30, 8 H1, 2 H4 and one synthetic D1 session window. This gives **155** fixture windows. This day is deliberately *not* a HOSE/HNX/UPCOM trading calendar, correct D1 closure, auction normalization, automatic timestamp rounding, provider OHLCV or official source aggregation contract. The exact membership list, 5-minute periods, no missing windows and complete closed status are required in this toy grid; a holiday, halt, lunch break, ATO/ATC or venue-specific bar shape in live data is **NOT** modeled or approved.

After an invented M5 index-15 OHLCV correction, direct windows impacted: M5[15], M15[5], M30[2], H1[1], H4[0], D1[0]. A causal EMA/ATR checkpoint tail would need re-evaluation from those first changed buckets: 81 M5 + 27 M15 + 14 M30 + 7 H1 + 2 H4 + 1 D1 = **132 theoretical checkpoint positions**. Numeric EMA/ATR are not actually recomputed by this planner; inherited V1 real arithmetic and independent synthetic oracle remain the correctness baseline.

A metadata-only revision marks raw lineage/audit but does not invalidate numerical bars or indicator values; a source state that is not qualified quarantines **all 155** fixture TF windows and cannot reuse cached checks. An unchanged fixture yields no planned numerical work; it is NOT an authenticated claim the real source did not change.

## Absolute NO-GO boundaries
All results assert:
- Actual issuer-verified M5 first-known, bar finality and authorized historical correction rights: FALSE.
- Official exchange schedule, auction window and D1 session shape proof: FALSE.
- Licensed market cache or cross-provider fallback/reuse: FALSE.
- Google Drive market-data read/write performed: FALSE.
- Multiwriter remote CAS, signed independent high-water floor, production/trading/release authority: FALSE.
- Existing original Swing 63 V1/8 V2 Git hashes and protected MST main unchanged; Draft PR #8 unmerged.

Future work after approved full-policy schema and real M3 issuer/legal proof: versioned multi-segment VN exchange membership instead of this toy eight-hour grid; distinct original native higher-TF vs M5-derived basis; read actual cloud chunk then verify tail reprocessing against inherited V1 EMA/ATR; multi-session daily closure and late correction chronology; independent protected Cloud writer/floor before manifest promotion.

## Github remote CI receipt
PENDING: exact implementation HEAD remote 44/44 tests, existing 28/28 + 217 source focused checks, exact all-workflow PASS, and subsequent report-containing HEAD readback. Never claim 289 targeted or production eligibility before those checks are observed.


## 2026-11-11 — Actual CI, negative correction and exact implementation-head receipt

Initial submitted implementation SHA \`cee3f052a6a7b5d1fa31e4570bfe906fd152c0d1\` did NOT pass: 45/47 workflows successful, dedicated/Foudation red because test_20_changed_calendar_fingerprint_denied placed a class-constructor raise *before* its \`assertRaises\` context. The production-facing guard itself denied the altered calendar binding correctly. Changed ONLY the test to construct inside \`assertRaises\` at GitHub commit \`554995c9943c97399331d17791535ba79cc9abd0\`; no weakening of policy guards or change to inherited V1 or eight original opt-in V2 business source.

**Corrected implementation exact HEAD independently read:** 47/47 GitHub Actions completed SUCCESS, no failures.
- [Six-TF dedicated QA run #42892050469](https://github.com/ngluonghoa/MST/actions/runs/42892050469): **44/44** new six-TF synthetic source-window and causal-suffix tests PASS; no-go receipt PASS.
- [Foundation CI #42892050477](https://github.com/ngluonghoa/MST/actions/runs/42892050477): contract/wheel checks, unittest Python 3.11 and Python 3.12 all SUCCESS. The corresponding earlier red run had one test error among 3697 repo tests on 3.11; corrected run is green on both versions.
- All 63 inherited V1 and eight pre-existing opt-in V2 Python module byte-lock checks retain their PASS at this SHA.
- Prior 245 focused synthetic tests are unchanged. New total **289 targeted focused tests** (245 + 44), which is not all-repository unittest count.

**Important:** 132 is only the number of *candidate checkpoints* in this fictional six-TF no-break session; the code did not calculate EMA/ATR values or prove actual VN D1/4H closing. Unknown issuer state quarantines all 155 toy windows, and every live-data/Drive/trading flag remains FALSE. This report-containing commit has not yet been independently re-checked and cannot inherit the implementation-HEAD CI claim until the final exact SHA completes.
