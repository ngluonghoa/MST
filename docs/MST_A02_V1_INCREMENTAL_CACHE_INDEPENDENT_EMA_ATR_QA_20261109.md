# MST A02 — V1 incremental SQLite cache / independent EMA20 + Wilder ATR14 oracle

**QA-ID:** MST-A02-INCREMENTAL-ORACLE-001  
**Date:** 2026-11-09 Asia/Ho_Chi_Minh  
**Verdict:** **PASS for inherited V1 synthetic incremental SQLite state, cold/warm/revision/transaction invariants against a separate reference implementation of EMA20/ATR14.**  
**Not authorized:** V2 Google Drive cache parity, live SSI/DNSE/VCBS storage, authenticated provider source/rights, two-writer CAS, production delivery, real signal or trade.

## 1. Source lock and scope

Original `ngluonghoa/swing-trading-1-8@cd90c1babae8912db31490ad614fc2ad2f868042`; protected MST `main@4048f91beaaa3410116d97e35896c8b688384e19` has identical Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` (216 entries, 208 blobs). The 63 inherited V1 Python modules and eight already-present V2 opt-in sidecars on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8) were not modified. Only independent script, tests, read-only workflow and QA/docs added.

User-selected **Option A GitHub + Google Drive only**. Real test execution occurs in GitHub Actions ephemeral runner using **manufactured prices in disposable SQLite**, not a developer's Mac/MOCHI/local computer. The runner does not connect to SSI/DNSE/VCBS or Google Drive market data; no new external Cloud service, secrets, API write/real market cache, broker or witness/ref/ruleset administration.

## 2. Executed contracts and independent numerical oracle

Original inherited `src/swing_trading/incremental_cache.py` functions and data classes used unchanged:
- `CacheIdentity`, `FixtureBar`, `SyntheticIncrementalStore.initialize/apply_fixture_window/read_bars/read_checkpoints/cursor`
- `advance_checkpoint` and `full_recompute` on V1 source side
- Separate `independent_ema_atr_oracle` in `scripts/m2_a02_incremental_cache_oracle_lab.py` calculates EMA20 and Wilder ATR14 by independently iterating fabricated closed bars. It **does not call** `advance_checkpoint` or `full_recompute`.

Reference math: EMA20 starts with first close then recurses `(2×close + 19×previous_EMA)/21`; true range includes high–low and two gaps to the previous close; Wilder ATR14 seeds with the sum of first 14 TRs divided by 14, then recurses `(13×previous_ATR + TR)/14`. Decimal is used throughout. **This is an independent implementation of the same specified formulas, not independently authenticated financial data**.

On every successful transaction **and** after a deliberately rejected transactional update, compare persisted SQLite checkpoints against **both** inherited V1 `full_recompute(read_bars)` and independent EMA20/ATR14 reference, using exact Decimal/checkpoint equality. First valid ATR14 point is bar **14**; a zero-volume synthetic candle is not confused with missing volume.

## 3. Ten-step real transactional scenario (all synthetic)

| Stage | Data change | Observed original SQLite behavior | Independent oracle |
| --- | --- | --- | --- |
| COLD_36 | 36 manufactured closed M5 candles | 36 inserts, 36 indicator checkpoints computed | Exact match |
| REOPEN_WARM_REUSE | Create a fresh store object pointing to same CI SQLite file; refetch 2 identical candles | 2 unchanged, 0 recomputation | Exact match |
| METADATA_ONLY_R8 | Revise revision label without changing OHLCV | 1 lineage-only event, 0 recomputation | Exact match |
| APPEND_BAR36 | Append one closed candle | 1 insert, exactly 1 checkpoint recomputed | Exact match |
| OLD_CORRECTION_R5_REPLAY_TAIL | Change earlier fabricated close | 1 revision, **32** dirty-tail checkpoints recomputed | Exact match |
| INCOMPLETE_PAGE_NO_DELETE | Source reports a partial bounded page | 0 deletion, 0 recomputation | Exact match |
| COMPLETE_SCOPE_DELETE_BAR11 | Authoritatively mark one bounded fixture window complete and omit bar 11 | 1 deletion, **25** affected checkpoint rows recomputed | Exact match |
| BACKFILL_BAR11 | Restore the deleted time with revised content | 1 insert, **26** affected checkpoints recomputed | Exact match |
| OPEN_BAR_IGNORED | Present an explicitly open candle | 1 ignored, 0 recomputation | Exact match |
| REJECT_AND_ROLLBACK_ALL_TABLES | Valid candidate update followed by a stale first-known time inside the same transaction | `ValueError`, **zero commit**; full SQL state snapshot and cursor unchanged | Exact match |

There is **no implied historical as-of market truth** from mutable SQLite rows: the lab tests the engine’s current materialized fixture state and its update/lineage mechanics; real append-only independent source custody remains unproved.

Additional negative and isolation checks:
- Provider namespace separation: distinct `SSI` and `DNSE` identities cannot see each other’s fixture bars/checkpoints; `RIGHTS.REVOKED` identity version has a different cache fingerprint. **Names do not prove vendor permissions.**
- Expected SSI lineage sequence: 36 `APPEND` records, then `LINEAGE_ONLY`, `APPEND`, `REVISE`, `DELETE`, `BACKFILL`.
- A *separate disposable* SQLite database is altered to a **valid OHLC close but mismatching original content digest**. `read_bars` rejects it with `digest mismatch` (no signed source attestation).
- Explicit `environment="PRODUCTION"` on inherited cache identity raises `PermissionError`. Every receipt retains `fixture_only=true` and `market_authorized=false`.
- Temporary SQLite is discarded after hosted run; the GitHub Actions artifact is just a 14-day review trace, **not** real Drive object retention or WORM rollback floor.

## 4. New files, tests and observed CI

- `scripts/m2_a02_incremental_cache_oracle_lab.py`: structured 10-step scenario, separate Decimal EMA20/ATR14 implementation, complete SQLite snapshot rollback verification, rights-isolation checks, time-bounded test evidence and synthetic SHA256.
- `tests/test_m2_a02_incremental_cache_oracle_lab.py`: **31 new test methods** covering every step, dirty-tail counts, indicator seed boundary, gap true range, independent oracle recompute, original metadata/no-op, rejected open rows, staged rollback, provider/rights separation, tamper and rights gating.
- `.github/workflows/m2-a02-incremental-cache-independent-oracle.yml`: same-repo PR #8 read-only GitHub Actions, `contents:read`; no secrets/real market I/O, produces temporary synthetic JSON audit.

**Code HEAD before QA file:** `ca31a4489ff1b338cfbecd7fd8caaa10f9d6b1e1`.

- [Independent EMA20/ATR14 hosted CI #42653070408](https://github.com/ngluonghoa/MST/actions/runs/42653070408) **SUCCESS**, receipt `V1_INCREMENTAL_COLD_WARM_CORRECTION_ROLLBACK_EQUALS_INDEPENDENT_ORACLE`, ten steps, original count 36 final count 37, `failed_transaction_all_sqlite_tables_rollback=true`, `vendor_rights_or_source_verified=false`, `licensed_drive_cache_read_or_written=false`, `v2_google_drive_cache_parity_implemented=false`, `trading_authorized=false`.
- Temporary GitHub review [artifact 13689803779](https://github.com/ngluonghoa/MST/actions/runs/42653070408/artifacts/13689803779), 14-day retention. **It is not an independently protected high-water receipt.**
- [Foundation CI #42653070030](https://github.com/ngluonghoa/MST/actions/runs/42653070030) **SUCCESS 3/3**: Python 3.11 **2,066/2,066**, Python 3.12 **2,066/2,066**, engineering **63/63**, source H2/H3/lint/wheel PASS.
- The other eleven read-only/synthetic workflows were also SUCCESS on the same code SHA: **13/13** exact code-head workflow types successful.
- Initial [#42652944236](https://github.com/ngluonghoa/MST/actions/runs/42652944236) **FAILED**: test deliberately mutated a fabricated database close to 999, which violated OHLC ordering and caused the *existing inherited V1 schema validator* to reject the row before the digest check. Corrected ONLY the test fixture mutation to close=101, an OHLC-valid but digest-different value, to exercise the intended digest integrity layer. No V1/V2 production source/policy was changed.
- **The QA commit creates a new PR HEAD**; all its workflows must be verified again before presenting that as final green.

## 5. Important gaps not to paper over

1. **Numerical parity here is V1 incremental vs independent recomputation**, not V1 vs a finished V2 Google Drive cache adapter. V2 cache partition, metadata refresh, single-memory fencing and proposed GitHub witness are still *synthetic planning layers*; no real Drive physical CAS, two authenticated writers or independent floor.
2. An independently coded oracle shares the explicit *mathematical specification* of EMA20/Wilder ATR14, but does not independently verify actual prices, corporate action policy, regulated feed provenance, market sessions or provider timestamp semantics.
3. The original V1 SQLite materialized bars have a lineage event table, but reconstructing independently certified historical market state and detecting privileged storage rollback across platforms remains unsolved. V1 `read_checkpoints` has no independently signed authority guarantee.
4. No 63-module owner A02 disposition, V2 A03 ABI owner approval, G01–G08 independent custody, M3 vendor rights, M4 physical Google Drive market bytes or M5/M8 production release has been obtained.

**Next safe work:** define *versioned opt-in V2 cache consumer parity specification* using this reference oracle, accounting for provider scope, partition/rights epoch, source correction, invalidation, first-known timestamps and Google Drive manifest links. Do not implement or claim real production publisher without independent owner-approved data rights, authenticated writers, protected witness and non-resettable floor evidence.

**Disposition:** `A02_V1_INCREMENTAL_NUMERIC_AND_TRANSACTIONAL_REFERENCE_PASS; A03_V2_DRIVE_ADAPTER_EQUIVALENCE_OPEN; ALL_PRODUCTION_GATES_BLOCKED`.
