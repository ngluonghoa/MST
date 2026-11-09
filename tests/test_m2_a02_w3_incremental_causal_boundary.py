"""MST M2/A02 W3 source-locked incremental cache transaction edge evidence.

All bars are manufactured fixtures; no real market data, vendor credentials,
Google Drive calls, trading permission or local user runtime.
This test file adds coverage without modifying any of the 63 v1 source blobs.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from swing_trading.incremental_cache import (
    CacheIdentity, FixtureBar, Provider, SyntheticIncrementalStore, full_recompute,
)

START = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)


def identity(provider=Provider.SSI):
    return CacheIdentity(
        provider=provider, endpoint_id="fixture.ohlc", instrument_id="SYN_A02",
        exchange="HOSE", timeframe="M5", session_id="2026-11-09.CONTINUOUS",
        price_basis="RAW", adjustment_revision="ADJ1",
        calendar_version="CAL1", aggregation_policy_version="AG1",
        indicator_version="EMA_ATR1",
    )


def bar(i, *, close=None, revision="r1", known=None):
    price = Decimal(100 + i) if close is None else Decimal(close)
    return FixtureBar(
        START + STEP*i, START + STEP*(i+1),
        price-1, price+2, price-2, price,
        100 + i, revision,
        START + STEP*(i+1) if known is None else known,
    )


class IncrementalCausalBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "fixture.sqlite"
        self.store = SyntheticIncrementalStore(self.path)
        self.store.initialize()
        self.key = identity()
        self.apply(tuple(bar(i) for i in range(30)),
                   at=30, start=0, end=30, complete=True, full=True)

    def apply(self, rows, *, at=40, start=0, end=30, complete=False,
              full=False, key=None):
        return self.store.apply_fixture_window(
            self.key if key is None else key, tuple(rows),
            observed_at_utc=START + STEP*at,
            scope_start_utc=START + STEP*start,
            scope_end_utc=START + STEP*end,
            complete_scope=complete, full_session_reconciled=full,
        )

    def assert_cold_parity(self, key=None):
        scoped = self.key if key is None else key
        stored_bars = self.store.read_bars(scoped)
        self.assertEqual(
            self.store.read_checkpoints(scoped),
            full_recompute(stored_bars),
        )

    def source_state(self):
        """All mutable rows, including append-only lineage and cursor."""
        tables = (
            "fixture_bars", "fixture_checkpoints", "fixture_lineage",
            "fixture_cursor",
        )
        with sqlite3.connect(self.path) as connection:
            return tuple(
                tuple(connection.execute(f"SELECT * FROM {name} ORDER BY rowid"))
                for name in tables
            )

    def test_old_correction_replays_only_dirty_tail_through_atr_seed(self):
        update = self.apply(
            (bar(5, close="233", revision="r2"),),
            start=5, end=6,
        )
        self.assertEqual((update.revised, update.inserted, update.deleted), (1, 0, 0))
        self.assertEqual(update.indicator_bars_recomputed, 25)
        self.assertEqual(update.first_dirty_utc, bar(5).start_utc)
        self.assertFalse(update.market_authorized)
        self.assert_cold_parity()

    def test_complete_scope_deletes_seed_bar_and_reseeds_atr(self):
        update = self.apply((), start=13, end=14, complete=True)
        self.assertEqual(update.deleted, 1)
        self.assertEqual(update.indicator_bars_recomputed, 16)
        observed = self.store.read_bars(self.key)
        self.assertEqual(len(observed), 29)
        self.assertNotIn(bar(13).start_utc, (b.start_utc for b in observed))
        checkpoints = self.store.read_checkpoints(self.key)
        self.assertIsNone(checkpoints[12].atr14)
        self.assertEqual(checkpoints[13].atr_seen, 14)
        self.assertIsNotNone(checkpoints[13].atr14)
        self.assert_cold_parity()

    def test_backfill_after_deletion_restores_causal_reference(self):
        self.apply((), start=6, end=7, complete=True)
        update = self.apply(
            (bar(6, close="248", revision="r2"),),
            at=41, start=6, end=7,
        )
        self.assertEqual((update.inserted, update.revised), (1, 0))
        self.assertEqual(update.indicator_bars_recomputed, 24)
        self.assertEqual(len(self.store.read_bars(self.key)), 30)
        self.assert_cold_parity()
        with sqlite3.connect(self.path) as connection:
            events = tuple(
                row[0] for row in connection.execute(
                    "SELECT event_type FROM fixture_lineage ORDER BY id"
                )
            )
        self.assertEqual(events[-2:], ("DELETE", "BACKFILL"))

    def test_metadata_only_revision_retains_exact_indicator_checkpoints(self):
        before = self.store.read_checkpoints(self.key)
        update = self.apply(
            (bar(8, revision="r2", known=START+STEP*39),),
            start=8, end=9,
        )
        self.assertEqual(update.lineage_only, 1)
        self.assertEqual(update.indicator_bars_recomputed, 0)
        self.assertEqual(self.store.read_checkpoints(self.key), before)
        self.assertEqual(self.store.read_bars(self.key)[8].revision, "r2")
        self.assertEqual(self.store.cursor(self.key).last_checked_utc,
                         START+STEP*40)
        self.assert_cold_parity()

    def test_incomplete_page_does_not_delete_unreturned_bars(self):
        before = self.store.read_bars(self.key)
        update = self.apply((bar(29),), start=0, end=30, complete=False)
        self.assertEqual((update.unchanged, update.deleted), (1, 0))
        self.assertEqual(update.indicator_bars_recomputed, 0)
        self.assertEqual(self.store.read_bars(self.key), before)
        self.assert_cold_parity()

    def test_later_invalid_observation_rolls_back_prior_write_and_cursor(self):
        before = self.source_state()
        old_known = START + STEP*7  # Older than the stored bar 7 first-known.
        invalid = replace(bar(7, revision="r2"), first_known_utc=old_known)
        with self.assertRaisesRegex(ValueError, "move backwards"):
            self.apply(
                (bar(4, close="233", revision="r2"), invalid),
                start=4, end=8,
            )
        self.assertEqual(self.source_state(), before)
        self.assert_cold_parity()

    def test_provider_and_rights_policy_namespaces_isolate_checkpoints(self):
        original = self.store.read_checkpoints(self.key)
        dnse = identity(Provider.DNSE)
        revoked_claim = replace(
            self.key, source_rights_policy_version="RIGHTS.REVOKED",
        )
        self.assertEqual(self.store.read_bars(dnse), ())
        self.assertEqual(self.store.read_bars(revoked_claim), ())
        self.apply((bar(0, close="521"),), at=40, start=0, end=1,
                   complete=True, full=True, key=dnse)
        self.assertEqual(len(self.store.read_bars(dnse)), 1)
        self.assertEqual(self.store.read_checkpoints(self.key), original)
        self.assertEqual(self.store.read_bars(revoked_claim), ())
        self.assert_cold_parity()
        self.assert_cold_parity(dnse)


if __name__ == "__main__":
    unittest.main()
