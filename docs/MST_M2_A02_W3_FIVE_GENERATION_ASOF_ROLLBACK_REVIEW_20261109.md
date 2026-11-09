# MST M2/A02 W3 — Five-generation point-in-time replay, custody, and high-generation rollback counterexample

**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Status:** Scoped, source-locked synthetic QA; **NOT** authenticated market history or production approval.  
**Branch:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), never merged to `main`.

## Source locks and distinct contracts

Original Swing Trading 1.8 baseline commit `cd90c1babae8912db31490ad614fc2ad2f868042`, MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` and all **63 original Python source blob SHAs unchanged**. No modification of `pyproject.toml` or local runtime.

Manually inspected legacy modules and related existing tests before adding the new fixture-only test file:

| Module | Verified Git blob SHA-1 | Critical function |
| --- | --- | --- |
| `src/swing_trading/segmented_cache.py` | `b2f55a6fc3061114df5b46ea6b53439378aeba0f` | `SyntheticWeeklyChunkStore.commit`, `_lineage`, `load`, `restore_full` |
| `src/swing_trading/incremental_cache.py` | `db06f6f0d63523d80ef3826c0f49a24c02d60be8` | `apply_fixture_window`, `_persist_fixture_cursor`, `full_recompute` |
| `src/swing_trading/cache_snapshot_bundle.py` | `f4802272197dae16ccd96b88b7728a0df88cfad5` | `create_fixture_snapshot`, `verify_fixture_snapshot`, `restore_fixture_snapshot` |

Existing tests include `tests/test_segmented_cache.py`, `tests/test_cache_snapshot_bundle.py`, `tests/test_m2_a02_w3_snapshot_lineage_recovery.py`. Previous closely related issues: [#11 — first-known rewind](https://github.com/ngluonghoa/MST/issues/11), [#12 — historical audit/as-of custody](https://github.com/ngluonghoa/MST/issues/12), [#10 — M4 Cloud storage](https://github.com/ngluonghoa/MST/issues/10).

## Exact fixture timeline (five increasing publication clocks)

21 fabricated closed D1 fixture bars (January 5–25, 2026 UTC); five *synthetic observed publish times* January 29, January 30, January 31, February 1, February 2, 2026 UTC. These are **not** exchange-session calendars or provider first-known attestations.

| Generation | Synthetic event applied | Expected current-state bars | Persistent C3A receipt |
| --- | --- | --- | --- |
| G1 | Initialize 21 bars, full session reconcile | 21 initial bars | SQLite snapshot 1, digest, no parent |
| G2 | REVISE historical bar index 3, first-known = G2 | 21, one changed OHLCV | Snapshot 2, parent = G1 manifest digest |
| G3 | Complete-scope DELETE bar index 10 | 20 (day 10 missing) | Snapshot 3, parent = G2 |
| G4 | BACKFILL bar index 10 with different OHLCV, first-known = G4 | 21 (new day 10) | Snapshot 4, parent = G3 |
| G5 | REVISE bar index 20, first-known = G5 | 21, revised historical tail | Snapshot 5, parent = G4 |

Independent [new six-case regression test](https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/tests/test_m2_a02_w3_five_generation_asof_custody.py):

1. **Five fully restorable C3A generations:** every retained snapshot restores the exact expected `FixtureBar` state, full-history EMA20/ATR14 checkpoints and last-checked observation clock at its generation.
2. **As-of publication boundary:** retained snapshots chosen by an explicit synthetic publish timestamp return G1 just before G2, G2 at G2, G2 just before G3, G3 at G3, G4 at G4 and G5 at G5. This is only a test oracle using retained snapshots, **not** native historical vendor-verified `as_of` functionality.
3. **Five structurally valid C4A ancestors:** each in-process weekly index has expected generation, parent hash and publish time, and its retained private chunk bytes decode back to each generation's fabricated bars. However C4A's public `load` rejects old pinned heads after G5. Private objects retained within the test double do not imply independently protected or durably retained Google Drive payloads.
4. **Latest-only C4A restore loses prior event types:** G5 weekly restore has correct 21 latest bars/global indicators but 21 reconstructed APPEND events. The existing SQLite history has 25 original event rows (21 APPEND + REVISE + DELETE + BACKFILL + REVISE) and a prior full-reconciliation timestamp that latest-weekly restore does not restore.
5. **C3A parent/hash/floor are caller-scoped, not external witness:** G5 manifest verifies against its supplied G4 digest and minimum generation 5, and rejects incorrect parent. G1 is rejected when supplied minimum generation 5, but remains internally valid when caller instead supplies a weak floor 1. A checksum/hash or self-selected floor does not guarantee independent anti-rollback custody.
6. **NEW material counterexample: G6 can be created with G1 time *and* G1 bars after G5.** The unchanged legacy `SyntheticWeeklyChunkStore.commit` accepts a brand-new generation 6 whose manifest parent is G5 but whose `created_at_utc` regresses from February 2 to January 29 and whose partition contents replay G1 stale fixture bars. The latest public `load` then returns stale G1 data under an apparently advanced generation. The existing SQLite incremental store **rejects** an analogous old-clock update and retains its G5 bars and cursor. This is a precise **synthetic clock/data rollback acceptance gap** even when local manifest parent ancestry passes. It does **not** prove an exploit against authenticated real Google Drive or live vendor systems, neither of which is present.

## Proposed acceptance gates (all OPEN / require explicit owner decision)

- **W3-ASOF-G01 — Clock and data monotonicity:** every candidate new head must carry independently attested publish/source-observed time at least as new as an independently protected accepted head, with explicit legitimate revision exceptions and the original source-clock meaning. A higher generation number is insufficient; forbid an older snapshot silently resurrected as a new generation.
- **W3-ASOF-G02 — Immutable history with payloads:** persist complete normalized OHLCV and correction/deletion/backfill payloads per accepted revision, not just old SHA digests; document retention/licensing and purge/erasure rules; link data to its original observation, source, and verified first-known clocks.
- **W3-ASOF-G03 — Point-in-time query correctness:** select only revisions visible at authenticated `as_of` with deterministic exact-boundary behavior, conflict/quarantine and calendar coverage; prohibit newer revisions or later correction metadata from leaking into prior backtests. Differentiate *source first-known*, *retrieved*, *verified*, *published*, and *restored* clocks.
- **W3-ASOF-G04 — Durability, CAS and recovery:** protect signer/key/rollback floor outside the replaceable index + chunks and outside caller-controlled state, enforce distributed writer fencing, audit append-only sequence and crash/retry-safe idempotency, verify on actual Google Drive with rights approval.
- **W3-ASOF-G05 — Restore levels and indicator seed:** explicit `CURRENT_STATE_ONLY` vs `TRANSACTION_AUDIT_PRESERVED` vs `HISTORICAL_ASOF_CERTIFIED` status; distinguish weekly chunk-local indicators, global incremental EMA/ATR and D1 causal ATR14 seed profiles and preserve historical prefix.
- **W3-ASOF-G06 — Cross-provider/policy invariants:** prove each source/end-point/instrument/timeframe/price-basis/rights-policy namespace independently, including revocation and clock skew/replay test matrix, without turning self-reported provider flags into permissions.

## CI evidence and release blockers

Code-only candidate HEAD `fc5970fc5af035042b5baee9ad846271c8e02afa`: [GitHub Actions #42577970757](https://github.com/ngluonghoa/MST/actions/runs/42577970757) **SUCCESS 3/3**: Python 3.11 **1,572/1,572**, Python 3.12 **1,572/1,572**, engineering **63/63** and H2/H3/lint/wheel PASS. A new CI run on the final report-containing HEAD is needed before calling it final checked.

**NOT SATISFIED:** 63 A02 final owner-reviewed per-module dispositions; A03 V2 ABI/release approval; M3 vendor entitlement, source-clock authenticated proof and legal Google Drive retention; M4 actual signed protected publisher, independent durable monotonic floor, real physical Drive chunks, multiple independent accounts/CAS/fencing, disaster recovery and historical as-of; M5 source-backed detector and OOS/backtesting; M8 production release. All test SQLite files are ephemeral on GitHub-hosted CI, not on Mac/MOCHI/local or production Drive. Keep Draft PR #8 unmerged; do not alter `main`.
