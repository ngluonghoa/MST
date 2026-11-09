"""MST A02 — hosted synthetic incremental SQLite cache vs independent EMA/ATR oracle.

Only manufactured M5 rows in GitHub Actions temporary SQLite. No Mac/MOCHI,
licensed quotes, real Google Drive bytes, vendor rights, distributed CAS or
owner approval. Distinguish V1 code correctness from V2 cloud capability.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from swing_trading.incremental_cache import (
    CacheIdentity, FixtureBar, IndicatorCheckpoint, Provider,
    SyntheticIncrementalStore, full_recompute,
)

START = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)
BAR_COUNT = 36


def instant(i: int) -> datetime:
    return START + STEP * i


def identity(provider: Provider = Provider.SSI) -> CacheIdentity:
    return CacheIdentity(
        provider=provider, endpoint_id="synthetic.ohlcv",
        instrument_id="SYN_A02_ORACLE", exchange="HOSE",
        timeframe="M5", session_id="SYNTHETIC.20261109",
        price_basis="RAW", adjustment_revision="ADJ1",
        calendar_version="CAL1", aggregation_policy_version="AG1",
        indicator_version="EMA20_ATR14_ORACLE1",
    )


def bar(i: int, *, close: D | None = None,
        revision: str = "r1", closed: bool = True) -> FixtureBar:
    """Fabricated, monotonic 5-minute candles with genuine price movements."""
    price = (D(100 + i // 3) + D(i % 3) / D(10)
             if close is None else D(close))
    return FixtureBar(
        instant(i), instant(i + 1),
        price - 1, price + 2, price - 2, price,
        0 if i == 4 else 1000 + i,
        revision, instant(i + 1), closed=closed,
    )


def independent_ema_atr_oracle(bars: tuple[FixtureBar, ...]) -> tuple[IndicatorCheckpoint, ...]:
    """Independent state traversal; does NOT call advance_checkpoint/full_recompute.

    Matches the *defined inherited* EMA20 recursion and Wilder ATR14 seed
    formulas, including startup warm-up, Decimal order and chronological TR.
    """
    out = []
    prior_ema = prior_close = prior_atr = None
    seed = D(0)
    for number, candle in enumerate(bars, start=1):
        if not candle.closed:
            raise ValueError("ORACLE_OPEN_BAR_NOT_ALLOWED")
        current_ema = (
            candle.close if prior_ema is None
            else (D(2) * candle.close + D(19) * prior_ema) / D(21)
        )
        true_range = candle.high - candle.low
        if prior_close is not None:
            true_range = max(
                true_range,
                abs(candle.high - prior_close),
                abs(candle.low - prior_close),
            )
        if number <= 14:
            seed = seed + true_range
        if number < 14:
            atr = None
        elif number == 14:
            atr = seed / D(14)
        else:
            if prior_atr is None:
                raise AssertionError("ORACLE_MISSING_ATR_SEED")
            atr = (D(13) * prior_atr + true_range) / D(14)
        out.append(IndicatorCheckpoint(
            candle.start_utc, current_ema, atr, number, seed, candle.close,
        ))
        prior_ema, prior_close, prior_atr = current_ema, candle.close, atr
    return tuple(out)


def database_snapshot(path: Path) -> tuple:
    """Include all source/indicator/cursor/lineage state, not only price output."""
    tables = ("fixture_bars", "fixture_checkpoints", "fixture_cursor",
              "fixture_lineage", "config")
    with sqlite3.connect(path) as db:
        return tuple(
            tuple(db.execute("SELECT * FROM " + table + " ORDER BY rowid"))
            for table in tables
        )


def validate_parity(store: SyntheticIncrementalStore,
                    key: CacheIdentity, expected_bars: int) -> dict:
    candles = store.read_bars(key)
    checkpoints = store.read_checkpoints(key)
    baseline = full_recompute(candles)
    independent = independent_ema_atr_oracle(candles)
    if len(candles) != expected_bars:
        raise AssertionError("V1_INCREMENTAL_BAR_COUNT_DRIFT")
    if checkpoints != baseline:
        raise AssertionError("V1_INCREMENTAL_VS_COLD_RECOMPUTE_DRIFT")
    if checkpoints != independent:
        raise AssertionError("V1_INCREMENTAL_VS_INDEPENDENT_EMA_ATR_DRIFT")
    return {
        "bars": len(candles),
        "checkpoints": len(checkpoints),
        "ema20_atr14_independent_oracle_equal": True,
        "atr14_first_valid_bar_number": (
            next((i for i, item in enumerate(checkpoints, 1)
                  if item.atr14 is not None), None)
        ),
        "verified_zero_volume_is_present": any(c.volume == 0 for c in candles),
    }


def _apply(store: SyntheticIncrementalStore, key: CacheIdentity,
           candles: tuple[FixtureBar, ...], *, now: int,
           start: int, end: int, complete: bool = False,
           full: bool = False):
    return store.apply_fixture_window(
        key, candles, observed_at_utc=instant(now),
        scope_start_utc=instant(start), scope_end_utc=instant(end),
        complete_scope=complete, full_session_reconciled=full,
    )


def run_cache_oracle_lab() -> dict:
    steps = []
    with TemporaryDirectory(prefix="mst-github-synthetic-a02-") as tmp:
        dbpath = Path(tmp) / "synthetic-v1.sqlite"
        cache = SyntheticIncrementalStore(dbpath)
        cache.initialize()
        key = identity()

        def record(name: str, update, expected: int):
            stats = validate_parity(cache, key, expected)
            steps.append({
                "name": name,
                "inserted": update.inserted,
                "revised": update.revised,
                "deleted": update.deleted,
                "lineage_only": update.lineage_only,
                "unchanged": update.unchanged,
                "ignored_open": update.ignored_open,
                "indicator_bars_recomputed": update.indicator_bars_recomputed,
                "first_dirty_utc": (
                    update.first_dirty_utc.isoformat()
                    if update.first_dirty_utc else None
                ),
                "source_authorized": update.market_authorized,
                "fixture_only": update.fixture_only,
                **stats,
            })
            if update.market_authorized or not update.fixture_only:
                raise AssertionError("V1_FIXTURE_PROMOTED_TO_LICENSED_CACHE")

        cold = _apply(cache, key, tuple(bar(i) for i in range(BAR_COUNT)),
                      now=BAR_COUNT, start=0, end=BAR_COUNT,
                      complete=True, full=True)
        if cold.inserted != BAR_COUNT or cold.indicator_bars_recomputed != BAR_COUNT:
            raise AssertionError("V1_COLD_BUILD_COUNT_DRIFT")
        record("COLD_36", cold, 36)

        # Cold/warm equivalence persists across an actual SQLite reconnect.
        cache = SyntheticIncrementalStore(dbpath)
        warm = _apply(cache, key, (bar(34), bar(35)),
                      now=37, start=34, end=36, complete=False)
        if warm.unchanged != 2 or warm.indicator_bars_recomputed:
            raise AssertionError("V1_WARM_REUSE_RECOMPUTED_CLEAN_BARS")
        record("REOPEN_WARM_REUSE", warm, 36)

        metadata = _apply(cache, key, (bar(8, revision="r2"),),
                          now=38, start=8, end=9)
        if metadata.lineage_only != 1 or metadata.indicator_bars_recomputed:
            raise AssertionError("V1_METADATA_ONLY_REVISION_RECOMPUTED")
        record("METADATA_ONLY_R8", metadata, 36)

        append = _apply(cache, key, (bar(36),),
                        now=38, start=36, end=37)
        if append.inserted != 1 or append.indicator_bars_recomputed != 1:
            raise AssertionError("V1_SINGLE_APPEND_DID_NOT_REPLAY_ONE")
        record("APPEND_BAR36", append, 37)

        edited = _apply(cache, key, (bar(5, close=D("200"), revision="r2"),),
                        now=39, start=5, end=6)
        if (edited.revised != 1
                or edited.indicator_bars_recomputed != 32
                or edited.first_dirty_utc != instant(5)):
            raise AssertionError("V1_OLD_CORRECTION_MINIMAL_DIRTY_TAIL_DRIFT")
        record("OLD_CORRECTION_R5_REPLAY_TAIL", edited, 37)

        # A partial page cannot silently delete bars it does not return.
        partial = _apply(cache, key, (bar(10),),
                         now=40, start=9, end=13, complete=False)
        if partial.deleted or partial.indicator_bars_recomputed:
            raise AssertionError("V1_INCOMPLETE_SOURCE_PAGE_DELETED_ROWS")
        record("INCOMPLETE_PAGE_NO_DELETE", partial, 37)

        # Explicit complete bounded response may remove exactly the missing bar.
        removal = _apply(cache, key, (bar(10), bar(12)),
                         now=41, start=10, end=13, complete=True)
        if removal.deleted != 1 or removal.indicator_bars_recomputed != 25:
            raise AssertionError("V1_COMPLETE_WINDOW_DELETION_TAIL_DRIFT")
        record("COMPLETE_SCOPE_DELETE_BAR11", removal, 36)

        restored = _apply(cache, key, (bar(11, close=D("150"), revision="r2"),),
                          now=42, start=11, end=12)
        if restored.inserted != 1 or restored.indicator_bars_recomputed != 26:
            raise AssertionError("V1_BACKFILL_REBUILD_TAIL_DRIFT")
        record("BACKFILL_BAR11", restored, 37)

        preview = _apply(cache, key, (bar(37, closed=False),),
                         now=43, start=37, end=38)
        if preview.ignored_open != 1 or preview.indicator_bars_recomputed:
            raise AssertionError("V1_OPEN_BAR_CHANGED_CLOSED_INDICATORS")
        record("OPEN_BAR_IGNORED", preview, 37)

        old_state = database_snapshot(dbpath)
        old_cursor = cache.cursor(key)
        # First row is valid and would be written; second row is stale =>
        # rollback *all* rows, indicators, lineage and cursor atomically.
        stale = replace(bar(6, revision="r2"), first_known_utc=instant(6))
        try:
            _apply(cache, key, (
                bar(4, close=D("225"), revision="r2"), stale,
            ), now=44, start=4, end=7)
        except ValueError as ex:
            if "move backwards" not in str(ex):
                raise
        else:
            raise AssertionError("V1_STALE_KNOWN_TIME_WAS_ACCEPTED")
        if database_snapshot(dbpath) != old_state or cache.cursor(key) != old_cursor:
            raise AssertionError("V1_FAILED_TRANSACTION_DID_NOT_ROLLBACK_ALL_STATE")
        record("REJECT_AND_ROLLBACK_ALL_TABLES", 
               # Snapshot-only marker: no UPDATE claimed.
               type("NoCommit", (), {
                   "inserted": 0, "revised": 0, "deleted": 0,
                   "lineage_only": 0, "unchanged": 0, "ignored_open": 0,
                   "indicator_bars_recomputed": 0, "first_dirty_utc": None,
                   "market_authorized": False, "fixture_only": True,
               })(), 37)

        # A different provider / versioned rights namespace cannot see SSI.
        second = identity(Provider.DNSE)
        revoked = replace(key, source_rights_policy_version="RIGHTS.REVOKED")
        if cache.read_bars(second) or cache.read_bars(revoked):
            raise AssertionError("V1_PROVIDER_OR_RIGHTS_CROSS_PARTITION_LEAK")
        other = _apply(cache, second, (bar(0, close=D("500")),),
                       now=45, start=0, end=1, complete=True, full=True)
        if (other.inserted != 1 or len(cache.read_bars(second)) != 1
                or cache.read_checkpoints(second) != independent_ema_atr_oracle(
                    cache.read_bars(second)
                ) or cache.read_bars(revoked)):
            raise AssertionError("V1_CROSS_PROVIDER_RIGHTS_NAMESPACE_LEAK")
        if len(cache.read_bars(key)) != 37:
            raise AssertionError("V1_PROVIDER_WRITE_CHANGED_OTHER_PARTITION")
        if cache.read_checkpoints(key) != independent_ema_atr_oracle(
                cache.read_bars(key)):
            raise AssertionError("V1_PROVIDER_WRITE_CONTAMINATED_SSI_INDICATORS")

        with sqlite3.connect(dbpath) as sql:
            history = tuple(
                event for (event,) in sql.execute(
                    "SELECT event_type FROM fixture_lineage "
                    "WHERE cache_key=? ORDER BY id", (key.fingerprint,)
                )
            )
        if (len(history) != 41 or history[:36] != ("APPEND",) * 36
                or history[36:] != (
                    "LINEAGE_ONLY", "APPEND", "REVISE", "DELETE", "BACKFILL",
                )):
            raise AssertionError("V1_LINEAGE_EVENTS_MISSING_OR_REORDERED")

        try:
            replace(key, environment="PRODUCTION")
        except PermissionError:
            pass
        else:
            raise AssertionError("V1_SYNTHETIC_CACHE_REAL_MARKET_PERMISSION")

        # Tamper detection exercised on a SEPARATE disposable fixture database.
        tamperpath = Path(tmp) / "tamper.sqlite"
        tamper = SyntheticIncrementalStore(tamperpath)
        tamper.initialize()
        _apply(tamper, key, (bar(0),),
               now=1, start=0, end=1, complete=True, full=True)
        with sqlite3.connect(tamperpath) as sql:
            sql.execute("UPDATE fixture_bars SET c=? WHERE cache_key=?",
                        ("101", key.fingerprint))
        try:
            tamper.read_bars(key)
        except RuntimeError as ex:
            if "digest mismatch" not in str(ex):
                raise
        else:
            raise AssertionError("V1_TAMPERED_SQLITE_BAR_UNDETECTED")

    # The SQLite files existed only on a GitHub Actions ephemeral cloud runner.
    receipt = {
        "schema": "mst.a02.incremental-v1-independent-ema20-atr14-synthetic-oracle.v1",
        "status": "V1_INCREMENTAL_COLD_WARM_CORRECTION_ROLLBACK_EQUALS_INDEPENDENT_ORACLE",
        "scenario_steps": steps,
        "scenario_step_count": len(steps),
        "baseline_closed_bars": BAR_COUNT,
        "final_closed_bars": 37,
        "atr14_first_valid_bar_number": 14,
        "independent_oracle_does_not_call_legacy_advance_checkpoint": True,
        "failed_transaction_all_sqlite_tables_rollback": True,
        "complete_vs_incomplete_scope_isolation": True,
        "source_revision_lineage_order_verified": True,
        "two_provider_partitions_isolated": True,
        "revision_rights_namespace_isolated": True,
        "tampered_sqlite_bar_detected": True,
        "on_disk_fixture_store_is_ephemeral_ci_only": True,
        "v2_google_drive_cache_parity_implemented": False,
        "real_github_witness_cas_proven": False,
        "vendor_rights_or_source_verified": False,
        "licensed_drive_cache_read_or_written": False,
        "owner_a02_a03_signed_off": False,
        "production_cache_authorized": False,
        "trading_authorized": False,
    }
    receipt["synthetic_matrix_sha256"] = sha256(json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    receipt = run_cache_oracle_lab()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
