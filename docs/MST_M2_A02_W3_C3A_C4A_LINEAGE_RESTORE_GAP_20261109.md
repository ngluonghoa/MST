# MST A02 W3 — C3A snapshot vs C4A weekly restore lineage-custody gap

**Date:** 2026-11-09 · **scope:** synthetic fixture source-locked review and regression only, NOT final A02 module disposition, licensed source acceptance, Google Drive physical transport or production release.

## Frozen provenance and source reviews

MST `main` remains Swing Trading 1.8 pinned source baseline commit `4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, sourced from original `cd90c1babae8912db31490ad614fc2ad2f868042`. Candidate changes live only on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), never in the 63 original Python source blobs.

Manually reviewed exact original source blobs:
- `cache_snapshot_bundle.py`: `f4802272197dae16ccd96b88b7728a0df88cfad5`; `create_fixture_snapshot` SQLite backup, `verify_fixture_snapshot` checksum/schema/causal parity and `restore_fixture_snapshot` exclusive copy.
- `segmented_cache.py`: `b2f55a6fc3061114df5b46ea6b53439378aeba0f`; weekly manifest genesis/parent, `load` latest-pin gate, `restore_full` replays latest bars into fresh SQLite via `apply_fixture_window`.
- `incremental_cache.py`: `db06f6f0d63523d80ef3826c0f49a24c02d60be8`; `fixture_bars` single latest row per identity/start, `fixture_lineage` event+old/new digest, `fixture_cursor` source observation and full reconciliation clock, global checkpoint series.
- Relevant previous [W3/C4A review](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_M2_A02_W3_C4A_WEEKLY_CROSS_BOUNDARY_ATR_ADR_20261109.md): weekly vs incremental `first_known` revision policy mismatch tracked in [Issue #11](https://github.com/ngluonghoa/MST/issues/11).

## New five deterministic cross-path tests

New `tests/test_m2_a02_w3_snapshot_lineage_recovery.py` creates 21 made-up daily bars and then revises one past bar, both in an existing SQLite fixture store and across two weekly manifest generations.

1. **C3A SQLite snapshot is lossless for existing event rows and cursor.** A WAL-aware snapshot/restore reproduces 22 lineage rows (21 APPEND + 1 REVISE), full-reconcile cursor, current bars, and global EMA/ATR checkpoints exactly. The manifest still has `live_market_data_authorized=False`.
2. **C4A weekly restore is latest-state numerical restore, not source event replay.** Restoring current weekly chunks into a fresh SQLite database reproduces all 21 bars and their global checkpoints, but its synthesized lineage contains 21 APPEND rows and **no old REVISE** event, while its `last_full_reconciled_utc=None` even if a prior SQLite working store had a completed reconciliation. Do not pass this restored fixture off as an audit-equivalent C3A snapshot or an independently source-verified `full_reconciled` state.
3. **Even C3A SQLite event history is digest-only, not a complete historical source archive.** Old and new bar content digests survive in `fixture_lineage`, but `fixture_bars` contains only the latest revised bar's OHLCV payload for that start timestamp. The earlier OHLCV cannot be reconstructed from a hash alone. An event list and numerical parity do not certify historical as-of replay.
4. **C4A `load` public contract is latest-head-only.** A caller pinning the old generation after a newer weekly commit gets `Stale or rolled-back fixture index`. The in-memory fixture store retains old chunk and manifest objects, but its public reader has **no independently authenticated point-in-time revision retrieval API**. Do not claim the synthetic model has destroyed those objects or treat its private dictionaries as a production archive.
5. **Warm update after C4A restore retains current numerical causality.** After restoring current bars, revising bar 19 of 21 recomputes two global checkpoints and matches cold calculation. This is a numerical guarantee only; it does not reconstruct the lost historical audit event.

## Required distinct acceptance levels

**L1 — Current-state continuity:** latest bars, EMA/ATR, correct indicator seed, provider/timeframe/rights namespace isolation, no silent reuse of chunk-local checkpoints. Existing fixture CI supports this narrowly.

**L2 — Operational transaction continuity:** exact lineage rows, last-checked/last-full-reconciled semantics, full local historical provenance. A C3A snapshot currently preserves the existing SQLite records; C4A `restore_full` **does not**. A future v2 Cloud restore must either restore certified append-only events and their audit proofs or return an explicit `AUDIT_HISTORY_UNAVAILABLE` status with consumer restrictions, never substitute reconstructed APPEND rows as original source events. A local full-reconcile timestamp may be carried only if independently authenticated or explicitly marked as an untrusted historical claim.

**L3 — Historical as-of/replay reproducibility:** preserve separately versioned original **data payloads** and authenticated first-known/retrieval/correction timestamps, not merely their digests; provide `as_of` reader against immutable revisions, independent source and calendar evidence, approved retention/license policy, and conflict/quarantine semantics. Neither single latest-row SQLite snapshot nor current public weekly read API proves this level. Explicitly detect conflicts with Issue #11's first-known rewind when reconstructing earlier generations.

**L4 — Production custody:** Google Drive real data chunks + approved vendor retention rights, independent signed publisher and durable monotonic floor, protected witness, multi-account CAS/fencing, recovery and crash/test report. None implemented or authorized by these tests.

## Proposed exit gates for owner approval (NOT yet adopted production)

- `W3-RESTORE-G01`: distinguish `CURRENT_STATE_ONLY`, `TRANSACTION_AUDIT_PRESERVED`, `HISTORICAL_ASOF_CERTIFIED` in versioned restore/read receipts, default fail-closed for provenance-dependent consumers.
- `W3-RESTORE-G02`: independent prior-event + revision payload custody and reproducible historical as-of golden tests across corrections/deletions, with correct source `first_known` policies.
- `W3-RESTORE-G03`: do not import a synthetic weekly APPEND as genuine vendor observation event; never infer full-session source reconciliation from a latest-only restore.
- `W3-RESTORE-G04`: prove cross-generation, cross-provider, cross-account and crash restart integrity on authenticated Cloud-only writer/storage; preserve independent rollback floor, per-partition boundaries and vendor entitlement receipts.
- `W3-RESTORE-G05`: treat two original ATR14 seed profiles and local weekly/global checkpoint distinction as separate versioned indicator contracts, no automatic replacement based on numerically matched latest cache alone.

## Exact CI and constraints

Test-containing commit `76f84697c952c95b7d14fc9775d18d9fce89557e`, [GitHub Actions run #42576226790](https://github.com/ngluonghoa/MST/actions/runs/42576226790) **SUCCESS 3/3**: Python 3.11 **1,566/1,566**, Python 3.12 **1,566/1,566**, engineering **63/63**, H2/H3/lint/wheel PASS. A further run is necessary for the final report-containing HEAD before final acceptance. All SQLite data uses ephemeral GitHub-hosted CI and synthetic test fixtures; **no Mac/MOCHI/local user environment, no real SSI/DNSE/VCBS payloads and no physical Google Drive market cache**.

**OPEN:** A02 63 final manual owner module dispositions, A03 explicit v2 version/ABI owner acceptance, M3 vendor rights/source-clock/Drive retention, M4 independently protected writer/CAS/antirollback/physical chunks, M5 authentic detector/BT, M8 release. Original `main` is unchanged; Draft PR #8 stays open and unmerged.
