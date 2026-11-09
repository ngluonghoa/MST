# MST M2/A02 W3 — C4A weekly chunk / full-history checkpoint / ATR seed contract ADR

**2026-11-09 · Cloud-only · Scoped manual engineering review · Draft PR #8 · NOT approved for production.**

## Baseline and source review

MST exact pinned legacy reference remains `main@4048f91beaaa3410116d97e35896c8b688384e19` and tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`, cloned from Swing Trading 1.8 source commit `cd90c1babae8912db31490ad614fc2ad2f868042`. **None of the 63 inherited modules nor `pyproject.toml` is modified.**

| Source | Pinned Git blob | Reviewed boundary |
| --- | --- | --- |
| `segmented_cache.py` | `b2f55a6fc3061114df5b46ea6b53439378aeba0f` | `SyntheticWeeklyChunkStore.commit`, `load`, `restore_full`, `_lineage`, window re-use |
| `partition_chunk_cache.py` | `30f4dd112a42c91905bf9abe95114dc7c58f70d9` | `encode_fixture_chunk` writes chunk-local `full_recompute` checkpoints; decoder validates their **local** parity |
| `incremental_cache.py` | `db06f6f0d63523d80ef3826c0f49a24c02d60be8` | Transactional `first_known_utc` non-regression for revisions; global EMA20/ATR14 seed; full-history replay |
| `causal_indicators.py` | `6dce942bcf4bdcd512659a962ffaf571c69db967` | D1 Wilder ATR14 requires 15 ordered bars and uses the 14 subsequent true ranges, not the initial bar's range |

Reviewed existing tests `tests/test_segmented_cache.py`, `tests/test_partition_chunk_cache.py`, `tests/test_incremental_cache.py`, `tests/test_causal_indicators.py`, and the preceding scoped A02 W3/W7 report. Five new tests live only at `tests/test_m2_a02_w3_c4a_weekly_atr_contract.py`.

## Validated counterexamples

1. **Chunk-local checkpoints are not global checkpoints.** C4A's week-two JSON chunk starts its own `ema20` from its first bar and counts ATR from 1. The global full-history checkpoint for the same date has already absorbed the preceding week. A local checkpoint is a serialization fixture, **not** a globally valid indicator value.

2. **Whole-partition restore correctly recovers global parity.** `SyntheticWeeklyChunkStore.restore_full` reassembles all 21 daily fake bars into a new SQLite store. The recovered 21 global `IndicatorCheckpoint` objects exactly match `full_recompute` and the last ATR14 is seeded.

3. **Immutable later chunks can remain byte-identical while global indicators change.** Revising a first-week bar changes exactly one physical synthetic chunk, reuses two later chunks, but changes downstream global EMA. Full restore correctly rebuilds the impacted later indicator history; never read the reused later chunk's serialized local checkpoints as the global answer.

4. **Material cross-path `first_known` non-regression mismatch (A02 action required).** In a 21-bar weekly fixture, replace a week-one record whose original `first_known` was bar end with a valid later *revision* claiming `first_known` only one hour after start. C4A `commit` accepts and publishes a new *local synthetic* manifest because it only checks future-known against publish time. For the **same revised bar**, the already-populated SQLite incremental `apply_fixture_window` rejects `Source observation first-known cannot move backwards` and leaves its existing state unchanged. This is a reproducible difference in v1 accepted inputs, **not proof that either pathway has live source authenticity**. The weekly model must not be silently used as a drop-in replacement for the stricter incremental revision logic; qualify rewind policy and independent source timestamp provenance before any production adapter.

5. **ATR14 seed conventions produce numerically different results.** On 15 manufactured D1 bars, the first bar has high=40/low=0/close=10, while the remaining 14 have high=12/low=8/close=10. Incremental checkpoint's 14th-bar ATR equals `92/14` (the first 40-point range plus thirteen 4-point ranges), and its 15th-bar ATR is still different from 4. The separate D1 `calculate_wilder_atr14` excludes the first bar's range when seeding its 14 true ranges, therefore returns exactly **4**, `COMPUTED_UNCALIBRATED` with all authorization flags false. Do not silently call the two implementations interchangeable.

## Proposed design/acceptance gates (no v1 modification)

- **W3-C4A-G01:** Create an explicit versioned indicator-domain contract distinguishing **partition-local serialized checkpoints**, **global incremental EMA/ATR**, and **D1 causal ATR14**. Consumers must request an exact profile; no implicit type/seed normalization, no automatic use of local checkpoint as global.
- **W3-C4A-G02:** A future v2 Cloud publish adapter must compare a revision's `first_known`/source revision lineage against a *trusted existing partition head and authenticated source evidence*, rejecting/explicitly resolving rewinds before publish. Distinguish legitimate vendor correction/dissemination from forged historical timestamps. No silent rewriting of frozen v1 methods.
- **W3-C4A-G03:** Cross-week revisions must invalidate global derived L2–L5 work from the earliest affected bar, even if L1 weekly chunk bytes for later weeks remain unchanged.
- **W3-C4A-G04:** Select-window reads may be used for source bar data only; no certification of full global indicators or chronology without verifiable complete preceding history/seed and externally authenticated calendar, source clock and product rights.
- **W3-C4A-G05:** M4 must still supply real Google Drive L1–L5 transport, private authorized writer, independently protected monotonic rollback floor, multi-account concurrency/fencing/physical readback, licensed vendor retention rights and cold/warm/rollback integration. The synthetic weekly store supplies none of these guarantees.

## QA receipt and limits

Prior PR branch had 1,556 Python tests on each of Python 3.11 and 3.12. This slice adds five; exact code-head [GitHub Actions #42574266231](https://github.com/ngluonghoa/MST/actions/runs/42574266231), commit `8d8bd92817de998a1b155950b487cec3dd39dfef`, **SUCCESS 3/3**: 1,561/1,561 Python 3.11, 1,561/1,561 Python 3.12, 63 engineering; H2/H3/lint/wheel pass. Recheck CI again on the final report-containing HEAD before claiming a final checkpoint. All fixtures run inside ephemeral GitHub-hosted CI and are fabricated; no real provider or Drive market data, credentials, Mac/MOCHI/local runtime, or authorized trading.

**Unresolved:** M2/A02 per-module owner dispositions for 63 legacy source files remain open; A03 v2 ABI/release-owner approval open. M3 source rights + first-known auth and permitted Drive retention open. M4 production publish/antirollback/fencing/open. M5 detector+backtest and M8 production release blocked. GitHub PR #8 remains DRAFT, UNMERGED. Nothing in this review certifies live market outcomes.
