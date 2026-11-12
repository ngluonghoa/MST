# MST M2/A02 — W3/W7 incremental Cache and causal EMA20/ATR14 review

**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Status:** scoped manual source inspection, **9 new synthetic regression tests**, candidate Draft PR #8 only. **Not A02 final owner signoff**.  
**Scope:** exact 1:1 baseline `ngluonghoa/swing-trading-1-8`, MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, source tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. No edit to 63 inherited Python modules or `pyproject.toml`.

## Source-locked review and dependency boundaries

| V1 original module | Pinned Git blob SHA-1 | Actual inspected responsibilities |
| --- | --- | --- |
| `incremental_cache.py` | `db06f6f0d63523d80ef3826c0f49a24c02d60be8` | `_validate_fixture_window` source/time/scope checks; `apply_fixture_window` one SQLite transaction for insert/update/delete, lineage and cursor; `_recompute_dirty_tail` after earliest changed bar; `advance_checkpoint` and `full_recompute` EMA20/ATR14 |
| `causal_indicators.py` | `6dce942bcf4bdcd512659a962ffaf571c69db967` | `_qualified`, `_validate_ordered_bars`, `calculate_wilder_atr14` and `calculate_rvol_tf20`; mathematical feature results remain `COMPUTED_UNCALIBRATED` or `BLOCKED`, never independently data certified |
| `cache_snapshot_bundle.py` | `f4802272197dae16ccd96b88b7728a0df88cfad5` | Existing snapshot/restore tests give downstream cold/warm parity evidence; this slice does not alter snapshot code or independently prove persistence on Google Drive |

Read-path and test consumers reviewed: `cache_fetch_planner.SourceCursor`, `partition_chunk_cache.SyntheticDrivePartitionIndex` and `tests/test_incremental_cache.py`, `tests/test_h3_cache_transaction_parity.py`, `tests/test_causal_indicators.py`, `tests/test_cache_snapshot_bundle.py`. These are fixture tests, not a vendor adapter or production runtime.

## Nine new Cloud-CI negative/golden controls

Seven independent SQLite transaction tests in `tests/test_m2_a02_w3_incremental_causal_boundary.py`:

1. Revision of an old bar at index 5 of 30 closes recalculates **only 25 dirty-suffix** EMA/ATR checkpoints, exactly equal to independent cold `full_recompute`.
2. A fully reconciled scope deleting bar index 13 recalculates the **16 remaining causal suffix** checkpoints and moves the 14th ATR seed to the new 14th surviving bar, without retaining a stale ATR.
3. Backfilling a deleted historical bar index 6 restores all 30 bars, recomputes **24 suffix** checkpoints and records an append-only `DELETE` → `BACKFILL` lineage sequence.
4. A metadata-only revision / later first-known timestamp retains identical indicator checkpoints (`lineage_only=1`, recomputes zero), but advances the local cursor: content digest vs source-lineage metadata are distinct.
5. An incomplete source page omitting most bars **cannot delete** unreturned bars, even when its scope overlaps a broad time range.
6. In a single transaction, an earlier valid historical revision followed by a later invalid older-first-known revision is rejected and **all bars, checkpoints, lineage and cursor are rolled back**.
7. DNSE and an altered SSI rights-policy cache identity have distinct partition fingerprints; a DNSE fixture write cannot mutate SSI cached checkpoints and a rights-policy identity change does not reuse the old partition. Labels are **not** independent proof of actual rights or revocation.

Two more `tests/test_causal_indicators.py` tests:

8. A sequence of 15 sorted D1 fixture bars with gaps between supplied dates can still produce mathematically correct ATR14 = 4, but **no external calendar/session coverage** is independently verified, so `data_certified`, `parameter_approved`, and `actionable` remain false. This is intentionally a missing external market-history proof, **not** a claim that every date gap is a defect (weekends/holidays exist).
9. Mutating the caller-claimed provenance endpoint/snapshot on one bar can preserve a numerical ATR result. `_source_context` checks typed observation/source identities, but cannot authenticate actual vendor identity or endpoint custody without an external attestor. Again, output always `COMPUTED_UNCALIBRATED` with rights false.

**Important non-equivalence:** The `incremental_cache.advance_checkpoint` ATR is a synthetic running checkpoint that seeds from the first closed bar's own range; `causal_indicators.calculate_wilder_atr14` uses 15 daily bars and seeds 14 true ranges from the second bar using the prior close. Do not assert those two calculations are byte- or semantically interchangeable, especially across M5/D1 histories, until a specifically approved cross-timeframe indicator contract is available. No formulas were changed.

## QA expectations, release and rollback

Prior exact-head PR #8 run had **1,547** tests per Python 3.11/3.12 and engineering 63. This slice adds **9 tests**. [GitHub Actions PR #42572295558](https://github.com/ngluonghoa/MST/actions/runs/42572295558) for code-and-report HEAD `5821df1098977c29fef1f0f3a05776c590bce2fc` completed **SUCCESS 3/3**: Python 3.11 **1,556/1,556**, Python 3.12 **1,556/1,556**, engineering **63/63**, H2/H3/lint/wheel PASS. The documentation-only update containing this evidence triggers a new CI run; use that run for final latest-HEAD verification. The GitHub CI host's ephemeral `TemporaryDirectory` and SQLite fixture are allowed under Cloud-only rules; nothing runs on or depends on personal Mac/MOCHI/local. The SQLite files are not a deployed cache and no real SSI/DNSE/VCBS or Google Drive candles are accessed.

**Explicit gates still open:** 63 per-module final A02 owner dispositions, A03 version/release approval, independently authenticated market/source entitlement and first-known publication clock (M3), licensed permission to retain on Drive, authenticated private protected writer and durable monotonic floor, physical Google Drive chunks, multi-account CAS/crash recovery (M4), 16 detector predicate signoffs and actual OOS/backtest (M5+), and signed production release (M8). PR #8 must remain Draft/unmerged; `main` must preserve pinned legacy Git blobs. If a new test contradicts valid baseline semantics, revert the added test on PR #8, never silently rewrite the 63 legacy sources or force-push `main`.
