"""MST M2/A02 W3-C4A: weekly cache / global ATR / source-time parity probes.

Source-locked original modules remain untouched. These are synthetic boundary
counterexamples, not provider data rights, production persistence, or trading.
"""
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.incremental_cache import (
    FixtureBar, SyntheticIncrementalStore, full_recompute,
)
from swing_trading.partition_chunk_cache import MAGIC
from swing_trading.segmented_cache import SyntheticWeeklyChunkStore
from swing_trading.causal_indicators import (
    IndicatorState, calculate_wilder_atr14,
)
from test_segmented_cache import T0, NOW, fake, key
from test_causal_indicators import AS_OF, make_bar, snap


class WeeklyAndATRContractTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.identity = key()
        self.weekly = SyntheticWeeklyChunkStore()
        self.bars = tuple(fake(i) for i in range(21))

    def publish(self, rows=None, head=None):
        return self.weekly.commit(
            self.identity, self.bars if rows is None else rows,
            expected_head=head, observed_at_utc=NOW,
        )

    def new_store(self, name):
        store = SyntheticIncrementalStore(self.folder / name)
        store.initialize()
        return store

    def test_chunk_local_ema_checkpoint_is_not_global_checkpoint(self):
        """Week-two checkpoint restarts EMA at first bar; do not expose as global."""
        self.publish()
        head = self.weekly.head(self.identity)
        index = self.weekly._indexes[head]
        self.assertEqual(len(index.windows), 3)
        week_two = index.windows[1]
        raw = self.weekly._chunks[week_two.name]
        encoded = json.loads(raw[len(MAGIC):])
        global_checkpoints = full_recompute(self.bars)
        self.assertEqual(encoded["checkpoints"][0]["ema20"], str(self.bars[7].close))
        self.assertNotEqual(
            Decimal(encoded["checkpoints"][0]["ema20"]),
            global_checkpoints[7].ema20,
        )
        self.assertIsNone(encoded["checkpoints"][0]["atr14"])
        self.assertEqual(global_checkpoints[7].atr_seen, 8)
        self.assertNotEqual(
            encoded["checkpoints"][0]["atr_seen"],
            global_checkpoints[7].atr_seen,
        )

    def test_global_full_restore_rebuilds_cross_week_checkpoint_state(self):
        self.publish()
        recovered = self.new_store("recovered.sqlite")
        head = self.weekly.head(self.identity)
        self.assertEqual(
            self.weekly.restore_full(recovered, self.identity, pinned_head=head),
            21,
        )
        expected = full_recompute(self.bars)
        self.assertEqual(recovered.read_checkpoints(self.identity), expected)
        self.assertEqual(expected[-1].atr_seen, 21)
        self.assertIsNotNone(expected[-1].atr14)
        self.assertFalse(hasattr(self.weekly, "live_market_data_authorized"))

    def test_old_week_revision_reuses_later_week_chunks_but_changes_global_ema(self):
        self.publish()
        old_head = self.weekly.head(self.identity)
        old_windows = self.weekly._indexes[old_head].windows
        edited = tuple(
            fake(i, price=Decimal("233"), revision="r2", known=NOW)
            if i == 3 else fake(i)
            for i in range(21)
        )
        result = self.publish(edited, head=old_head)
        new_head = self.weekly.head(self.identity)
        new_windows = self.weekly._indexes[new_head].windows
        self.assertEqual((result.created_windows, result.reused_windows), (1, 2))
        self.assertEqual(
            tuple(x.sha256 for x in old_windows[1:]),
            tuple(x.sha256 for x in new_windows[1:]),
        )
        self.assertNotEqual(full_recompute(self.bars)[-1].ema20,
                            full_recompute(edited)[-1].ema20)
        restored = self.new_store("revised.sqlite")
        self.weekly.restore_full(restored, self.identity, pinned_head=new_head)
        self.assertEqual(restored.read_checkpoints(self.identity),
                         full_recompute(edited))

    def test_weekly_replacement_can_rewind_first_known_while_incremental_refuses(self):
        """Concrete contract mismatch: fresh weekly fork vs established SQLite."""
        self.publish()
        old_head = self.weekly.head(self.identity)
        original = self.bars[3]
        rewound = replace(
            fake(3, price=Decimal("177"), revision="r2"),
            first_known_utc=original.start_utc + timedelta(hours=1),
        )
        self.assertLess(rewound.first_known_utc, original.first_known_utc)
        revised = self.bars[:3] + (rewound,) + self.bars[4:]
        accepted = self.publish(revised, head=old_head)
        self.assertTrue(accepted.manifest_changed)
        self.assertEqual(
            self.weekly.load(self.identity, pinned_head=self.weekly.head(self.identity))[3],
            rewound,
        )
        prior_store = self.new_store("original.sqlite")
        prior_store.apply_fixture_window(
            self.identity, self.bars, observed_at_utc=NOW,
            scope_start_utc=self.bars[0].start_utc,
            scope_end_utc=self.bars[-1].end_utc,
            complete_scope=True, full_session_reconciled=True,
        )
        before = prior_store.read_bars(self.identity)
        with self.assertRaisesRegex(ValueError, "first-known cannot move backwards"):
            prior_store.apply_fixture_window(
                self.identity, (rewound,), observed_at_utc=NOW + timedelta(hours=1),
                scope_start_utc=rewound.start_utc, scope_end_utc=rewound.end_utc,
                complete_scope=False,
            )
        self.assertEqual(prior_store.read_bars(self.identity), before)
        # The weekly blob is locally valid, but lacked the old-source clock check.

    def test_two_atr14_seed_conventions_have_distinct_numeric_results(self):
        """Legacy cache seeds first range; D1 feature seeds 14 subsequent TRs."""
        fixture_bars = []
        for i in range(15):
            start = T0 + timedelta(days=i)
            first = i == 0
            fixture_bars.append(FixtureBar(
                start, start+timedelta(days=1),
                Decimal("10"), Decimal("40" if first else "12"),
                Decimal("0" if first else "8"), Decimal("10"),
                100, "r1", start+timedelta(days=1),
            ))
        checkpoints = full_recompute(tuple(fixture_bars))
        self.assertIsNone(checkpoints[12].atr14)
        self.assertEqual(checkpoints[13].atr14, Decimal(92) / Decimal(14))
        self.assertNotEqual(checkpoints[14].atr14, Decimal("4"))
        d1_history = tuple(snap(make_bar(
            i, high=Decimal("40") if i == 0 else Decimal("12"),
            low=Decimal("0") if i == 0 else Decimal("8"),
            open_price=Decimal("10"), close=Decimal("10"),
        )) for i in range(15))
        observed = calculate_wilder_atr14(d1_history, as_of_utc=AS_OF)
        self.assertEqual(observed.value, Decimal("4"))
        self.assertEqual(observed.state, IndicatorState.COMPUTED_UNCALIBRATED)
        self.assertFalse(observed.data_certified)
        self.assertFalse(observed.actionable)
