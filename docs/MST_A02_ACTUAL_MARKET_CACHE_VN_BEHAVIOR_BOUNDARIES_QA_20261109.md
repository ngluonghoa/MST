# MST A02 — Real inherited candle / source-revision / cache-refresh / VN execution fixture boundaries

**QA ID:** MST-A02-REAL-BUSINESS-GUARD-001 · **Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**Verdict:** **PASS: actual inherited V1 and V1.2 guard execution, plus explicit V2 cache-planner semantic gap.**  
**NOT accepted:** Full Swing Trading 1:1 trading behavior, V1/V2 market-data equivalence, external provider rights, Vietnamese settlement calendar, broker fills, Drive production cache, owner A02/A03/M3/M4/M8 signoff.

## 1. Exact immutable source scope and changes

Pinned Swing Trading 1.8 commit `cd90c1babae8912db31490ad614fc2ad2f868042` and MST protected `main@4048f91beaaa3410116d97e35896c8b688384e19` point to identical Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` (216 tree entries, 208 blobs, 63 original `src/swing_trading/` Python modules). Draft [PR #8](https://github.com/ngluonghoa/MST/pull/8) leaves **all original V1 blobs and existing eight V2 source files unchanged**. Added only:
- `scripts/m2_a02_market_cache_execution_boundary_lab.py` — executable structured deterministic matrix invoking **real inherited V1/V1.2 domain code** and actual opt-in V2 cache hint planner, explicitly declining to claim that their semantics are interchangeable.
- `tests/test_m2_a02_market_cache_execution_boundary_lab.py` — **27 tests** across temporal bar eligibility, quality/rights claims, source revision conflicts, cache planning and VN equity economic/settlement/ambiguous-bar guards.
- `.github/workflows/m2-a02-market-cache-vn-boundaries.yml` — same-repo Draft PR #8-only GitHub-hosted read-only workflow, `permissions: contents: read`; produces one temporary JSON fixture matrix, no GitHub admin/Drive writes or live provider secrets.
- This technical QA report, Google Drive QA copy and canonical docs.

**Platform:** User-selected Option A **GitHub + Google Drive only**. Absolutely no Mac, MOCHI/local project run, other Cloud service, SSI/DNSE/VCBS live OHLCV, broker integration, key issuance, real market-cache writes or trading actions.

## 2. Actual V1 vs V1.2 candle semantics: necessary predicate is NOT external authority

Executed real inherited `market_data.CanonicalCandle.eligible_for_confirmed_signals`, `source_quality.CanonicalCandleV12.confirmation_prerequisites` and `replay_batch.replay_frame(...).source_prerequisites_at` on the *same fabricated 15-minute bar*:
- bar start 2026-11-06T02:00Z; bar closes minute 15; source revision first known minute 15; fetched minute 20; verified minute 25.
- source `SourceEvidence` flags deliberately set `True` as **synthetic caller claims** solely to exercise all predicates. They do **NOT** prove provider rights, actual provider timestamp semantics, verified market quality or release authority.
- verified `volume=0` is a valid non-missing volume; `None` blocks. OPEN, unknown price basis, incomplete minutes, quality flags, failed cutoff or insufficient evidence block conservative predicates.

| As-of minute | Original V1 simplified necessary candle check | Rich V1.2 source prerequisites | Revision visible in V1.2 replay |
| ---: | --- | --- | --- |
| 14 | false | false | false |
| 15 | true | false | true |
| 20 | true | false | true |
| 24 | true | false | true |
| 25 | true | true | true |
| 30 | true | true | true |

**Confirmed contract distinction:** original V1 simplified candle check can return true at close / first-known, even while the richer V1.2 source observation still awaits verification. **Neither true flag authorizes trade**, and treating those distinct predicates as 1:1 equivalent would be incorrect. The V2 sidecars do not currently implement a production-grade equivalent of all source/candle contracts.

## 3. Source-revision replay, corrections and cache planner scope

- `replay_frame` collapses **2 exact retransmissions** of the same signed-by-no-one *synthetic* candle into one selected revision. This is data deduplication, not cryptographic source authentication.
- Equal observation/revision identity with different fabricated payload: **revision_identity_collision=true; no selected revision; source prerequisites false**. It never silently prefers a latest quote.
- A synthetic correction first-known at minute 40 and retrieved minute 41 **cannot rewrite the minute-30 as-of result**. By minute 50, two independently named revisions remain a conflict requiring an explicit source resolution policy, not automatic winner.
- Inherited `cache_fetch_planner.plan_refresh` with an actually closed M15 fixture returns `REUSE_CLOSED` within cadence at minute 28, `REQUEST_WINDOW` when interval is due at minute 30, and `REQUEST_FULL_SESSION` for correction reconciliation at minute 55. This is a **read-only request planner**; neither `certified_source_freshness` nor `data_authorized` can be promoted.
- V2 `v2_cache_partition_plan.plan_fixture_refresh` only yields `RECENT_METADATA` and `NEEDS_PROVIDER_REVALIDATION` based on *caller-supplied untrusted metadata*. It has no data fetch, approved Drive cache read/write, signed provider head, source freshness certification or trading rights. **The V1 and V2 planner outputs are not behaviorally equivalent** — the matrix records this as an explicit A03 gap, not as a falsely passed V2 migration.

## 4. Real inherited VN synthetic equity backtest guards

Executed `vn_backtest_execution_fixture.calculate_fixture_vn_trade`, `inspect_fixture_vn_long_exit_bar` and `require_vn_backtest_release`:
- Fake symbol FAKE001, HOSE fixture venue, 100 shares, manually injected tick/lots/fee rates/tax rates; entry at 10 and exit at 12 in *fabricated* units yields **gross 200, net 196.600** with fee and sell-tax deductions.
- A synthetic exit is allowed only when the *caller supplies* explicit release session index 3 and the exit is session 4. A release index beyond session 4 or an unspecified index is rejected. **This does not certify Vietnam T+2 or a real exchange calendar**.
- A bar whose low crosses a fabricated stop and whose high crosses target simultaneously returns `AMBIGUOUS_BOTH`; no assumption of which order was filled, no verified execution, no broker receipt.
- Future-known exit fills, wrong symbol, oversold shares and future-known bar observations are rejected; `require_vn_backtest_release()` always raises `PermissionError`.

This is meaningful inherited contract behavior, but it is **not an actual backtest accuracy score**, P&L forecast or fill evidence.

## 5. Cloud CI evidence and transparent correction

**Code/workflow HEAD before this report:** `83c68b6fcc086ce6a4cd10bc8ab26d39584a699a`.

- [Dedicated hosted V1/market/VN fixture audit #42646121144](https://github.com/ngluonghoa/MST/actions/runs/42646121144) **SUCCESS**. Machine status: `ACTUAL_INHERITED_MARKET_CACHE_AND_VN_GUARDS_VERIFIED_WITH_EXPLICIT_V2_SCOPE_GAP`. 6 as-of candle snapshots, V1→V1.2 conditions listed above, exact retransmission count 2, revision collision blocked, late correction no past rewrites, V1 three refresh actions, V2 two untrusted hints, VN net `196.600` and `AMBIGUOUS_BOTH`. Every production/rights/calendar/fills flag false.
- Temporary read-only Actions [artifact 13686654728](https://github.com/ngluonghoa/MST/actions/runs/42646121144/artifacts/13686654728), 14-day retention, **not** independent source attestation or durable owner-approved floor.
- [Foundation CI #42646121085](https://github.com/ngluonghoa/MST/actions/runs/42646121085) **SUCCESS 3/3**: Python3.11 **2035/2035**; Python3.12 **2035/2035**; engineering **63/63**, H2/H3 exact source boundary, lint and wheel PASS.
- [Cross-repo Git tree parity #42646120822](https://github.com/ngluonghoa/MST/actions/runs/42646120822) SUCCESS on same code head. The other 9 M4/A03 review/test-only workflows also succeeded: **12/12** exact code-head runs SUCCESS.

**Failure and remedy, fully disclosed:** Initial new workflow [#42645938350](https://github.com/ngluonghoa/MST/actions/runs/42645938350) and corresponding Foundation [#42645938250](https://github.com/ngluonghoa/MST/actions/runs/42645938250) correctly failed, because test data claimed a M15 candle starting minute 15 was closed at minute 28. The inherited planner raised `ValueError: Latest closed bar must be in session and actually closed at clock` (a **correct** lookahead guard). The **fixture only** was corrected so latest closed bar starts minute 0, ends minute 15 and can be observed at minute 28; no production source code, calendar policy or guard was relaxed. On corrected code head all 2035 tests per interpreter and hosted business boundary audit PASS.

**Documentation-bearing final commit must be rechecked separately** before declaring the complete checkpoint green.

Synthetic matrix SHA256 `d32ea8426d6cbb8cd11549c02872980c19c9e2a8bf08d8a987a9ff3449a28cf5` is deterministic test output, **not** vendor source authorization, cryptographic owner signature or rollback-floor custody.

## 6. A02/A03 disposition and next engineering frontier

| Module / interface | This evidence | A02/A03 status |
| --- | --- | --- |
| `market_data.CanonicalCandle` | Original simplified necessary predicate executed and time-bounded | **TESTED SUBSET**, owner dispositions OPEN |
| `source_quality.CanonicalCandleV12` | Distinct verified-at and multi-axis source prerequisites executed | **TESTED SUBSET**, real provider attestation OPEN |
| `replay_batch` | Exact dedup, conflict, later correction as-of isolation tested | **TESTED SUBSET**, source revisions unresolved by design |
| `cache_fetch_planner` | Cadence/window/full-session reconciliation read-only policy executed | **TESTED SUBSET**, source-head freshness not externally attested |
| `v2_cache_partition_plan` | Opt-in untrusted metadata hint / partition isolation only | **SEMANTIC GAP** vs V1 fetching plan, not an equivalent adapter |
| `vn_backtest_execution_fixture` | Fabricated fee/tax/settlement and ambiguous OHLC touched | **TESTED SUBSET**, real T+2/fill release never certified |

No new production implementation, new source byte, real OHLCV/cache or licensed data. The 63 individual owner acceptance decisions for A02 remain **OPEN**; V2 real ABI, transition and behavior acceptance remains **OPEN**; security [G01–G08 #16](https://github.com/ngluonghoa/MST/issues/16), [A03 #6](https://github.com/ngluonghoa/MST/issues/6) and [A02 #4](https://github.com/ngluonghoa/MST/issues/4) remain **OPEN**.

**Next safe work:** choose one actual V1 subdomain for further consumer-driven goldens (e.g. incremental SQLite indicator/checkpoint cache with cold/warm/revision equivalence) and design *opt-in* V2 adapter parity assertions without modifying V1 or claiming physical Google Drive CAS. M5/M8 trading/release stays **BLOCKED**, and PR #8 stays Draft and unmerged.
