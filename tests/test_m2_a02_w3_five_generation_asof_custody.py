"""MST M2/A02 W3: five-generation synthetic as-of and custody reference matrix.

This deliberately tests inherited C3A/C4A boundaries, including *accepted*
regressions, without patching any of the 63 source-locked legacy modules.
An archive retained by a GitHub CI fixture is not an independently trusted
vendor source, a permitted Google Drive cache, or a production as-of reader.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from swing_trading.cache_snapshot_bundle import (
    create_fixture_snapshot, restore_fixture_snapshot, verify_fixture_snapshot,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore, full_recompute
from swing_trading.partition_chunk_cache import decode_fixture_chunk
from swing_trading.segmented_cache import SyntheticWeeklyChunkStore
from test_segmented_cache import NOW, fake, key


class FiveGenerationCustodyTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.identity = key("SYN_5GEN_ASOF")
        self.times = tuple(NOW - timedelta(days=4-i) for i in range(5))
        self.initial = tuple(fake(i) for i in range(21))
        revised_3 = fake(3, price=Decimal("333"), revision="r2",
                         known=self.times[1])
        self.changed = self.initial[:3] + (revised_3,) + self.initial[4:]
        self.without_10 = self.changed[:10] + self.changed[11:]
        backfill_10 = fake(10, price=Decimal("444"), revision="r3",
                           known=self.times[3])
        self.backfilled = tuple(sorted(
            self.without_10 + (backfill_10,),
            key=lambda row: row.start_utc,
        ))
        revised_20 = fake(20, price=Decimal("555"), revision="r2",
                          known=self.times[4])
        self.final = self.backfilled[:-1] + (revised_20,)
        self.versions = (
            self.initial, self.changed, self.without_10,
            self.backfilled, self.final,
        )
        self.db = SyntheticIncrementalStore(self.root / "working.sqlite")
        self.db.initialize()
        self.weekly = SyntheticWeeklyChunkStore()
        self.receipts = []
        self.heads = []
        self._initial_publish()
        self._advance(2, (revised_3,), revised_3)
        self._advance(3, (), fake(10), complete=True)
        self._advance(4, (backfill_10,), backfill_10)
        self._advance(5, (revised_20,), revised_20)

    def _initial_publish(self):
        start = self.initial[0].start_utc
        end = self.initial[-1].end_utc
        self.db.apply_fixture_window(
            self.identity, self.initial, observed_at_utc=self.times[0],
            scope_start_utc=start, scope_end_utc=end, complete_scope=True,
            full_session_reconciled=True,
        )
        self.weekly.commit(
            self.identity, self.initial, expected_head=None,
            observed_at_utc=self.times[0],
        )
        self._capture(1)

    def _advance(self, generation, observations, scope_bar, complete=False):
        now = self.times[generation-1]
        self.db.apply_fixture_window(
            self.identity, tuple(observations), observed_at_utc=now,
            scope_start_utc=scope_bar.start_utc,
            scope_end_utc=scope_bar.end_utc, complete_scope=complete,
        )
        self.weekly.commit(
            self.identity, self.versions[generation-1],
            expected_head=self.weekly.head(self.identity),
            observed_at_utc=now,
        )
        self._capture(generation)

    def _capture(self, generation):
        snapshot = self.root / f"gen{generation:02d}.sqlite"
        manifest_path = self.root / f"gen{generation:02d}.json"
        parent = self.receipts[-1][2].digest if self.receipts else None
        manifest = create_fixture_snapshot(
            self.db, snapshot, manifest_path,
            snapshot_id=f"gen{generation:02d}",
            generation=generation, previous_manifest_sha256=parent,
            created_at_utc=self.times[generation-1],
        )
        self.receipts.append((snapshot, manifest_path, manifest))
        self.heads.append(self.weekly.head(self.identity))

    def _restore(self, index, label):
        snapshot, manifest_path, manifest = self.receipts[index]
        previous = self.receipts[index-1][2].digest if index else None
        return restore_fixture_snapshot(
            snapshot, self.root / f"{label}-g{index+1}.sqlite",
            manifest_path.read_text(), pinned_manifest_sha256=manifest.digest,
            expected_parent_sha256=previous, minimum_generation=index+1,
        )

    @staticmethod
    def _event_types(path):
        with sqlite3.connect(path) as db:
            return tuple(row[0] for row in db.execute(
                "SELECT event_type FROM fixture_lineage ORDER BY id"
            ))

    def test_each_c3a_generation_is_independently_restorable_to_golden_bars(self):
        for index, bars in enumerate(self.versions):
            with self.subTest(generation=index+1):
                restored = self._restore(index, "golden")
                self.assertEqual(restored.read_bars(self.identity), bars)
                self.assertEqual(
                    restored.read_checkpoints(self.identity),
                    full_recompute(bars),
                )
                self.assertEqual(
                    restored.cursor(self.identity).last_checked_utc,
                    self.times[index],
                )
                self.assertFalse(
                    self.receipts[index][2].live_market_data_authorized,
                )

    def test_asof_publication_boundaries_require_retained_pinned_generations(self):
        # This fixture oracle chooses a retained, observed publication generation.
        # It is NOT vendor-authenticated first-known, source availability,
        # exchange calendar, correction eligibility, or historical trading truth.
        cases = (
            (self.times[0], 0),
            (self.times[1] - timedelta(microseconds=1), 0),
            (self.times[1], 1),
            (self.times[2] - timedelta(microseconds=1), 1),
            (self.times[2], 2),
            (self.times[3], 3),
            (self.times[4], 4),
        )
        for asof, expected in cases:
            with self.subTest(asof=asof):
                index = max(i for i, publication in enumerate(self.times)
                            if publication <= asof)
                self.assertEqual(index, expected)
                restored = self._restore(index, "asof-" + str(len(str(asof))))
                # Distinct subtest writes require unique destination names:
                # this helper uses generation+date length, and is invoked
                # once per generation except boundary duplicates.
                self.assertEqual(restored.read_bars(self.identity),
                                 self.versions[expected])

    def test_c4a_old_generation_payload_objects_remain_but_public_load_is_latest(self):
        ancestry = self.weekly._lineage(self.identity)
        self.assertEqual(
            tuple(item.digest for item in ancestry), tuple(self.heads),
        )
        for index, manifest in enumerate(ancestry):
            with self.subTest(generation=index+1):
                self.assertEqual(manifest.generation, index+1)
                self.assertEqual(manifest.created_at_utc, self.times[index])
                self.assertEqual(
                    manifest.parent_sha256,
                    None if index == 0 else self.heads[index-1],
                )
                retained = tuple(
                    bar
                    for ref in manifest.windows
                    for bar in decode_fixture_chunk(
                        self.weekly._chunks[ref.name],
                        expected_identity=self.identity,
                    )
                )
                self.assertEqual(retained, self.versions[index])
                if index < 4:
                    with self.assertRaisesRegex(
                        ValueError, "Stale or rolled-back fixture index"
                    ):
                        self.weekly.load(
                            self.identity, pinned_head=self.heads[index],
                        )
        self.assertEqual(
            self.weekly.load(self.identity, pinned_head=self.heads[-1]),
            self.final,
        )
        # Private in-process objects are NOT an authenticated historical API.

    def test_latest_c4a_restore_rebuilds_bars_but_loses_prior_event_kinds(self):
        recovered = SyntheticIncrementalStore(self.root / "weekly-restored.sqlite")
        recovered.initialize()
        self.assertEqual(
            self.weekly.restore_full(
                recovered, self.identity, pinned_head=self.heads[-1],
            ), 21,
        )
        self.assertEqual(recovered.read_bars(self.identity), self.final)
        self.assertEqual(
            recovered.read_checkpoints(self.identity),
            self.db.read_checkpoints(self.identity),
        )
        source_events = self._event_types(self.db.path)
        reconstructed_events = self._event_types(recovered.path)
        self.assertEqual(
            source_events[-4:], ("REVISE", "DELETE", "BACKFILL", "REVISE"),
        )
        self.assertEqual(len(source_events), 25)
        self.assertEqual(reconstructed_events, ("APPEND",)*21)
        self.assertIsNone(
            recovered.cursor(self.identity).last_full_reconciled_utc,
        )
        self.assertEqual(
            self.db.cursor(self.identity).last_full_reconciled_utc,
            self.times[0],
        )

    def test_parent_pin_and_minimum_generation_check_only_caller_provided_floor(self):
        snapshot, manifest_path, m = self.receipts[4]
        self.assertEqual(
            verify_fixture_snapshot(
                snapshot, manifest_path.read_text(),
                pinned_manifest_sha256=m.digest, minimum_generation=5,
                expected_parent_sha256=self.receipts[3][2].digest,
            ), m,
        )
        with self.assertRaises(ValueError):
            verify_fixture_snapshot(
                snapshot, manifest_path.read_text(),
                pinned_manifest_sha256=m.digest,
                expected_parent_sha256=self.receipts[2][2].digest,
            )
        first, first_manifest_path, first_manifest = self.receipts[0]
        with self.assertRaises(ValueError):
            verify_fixture_snapshot(
                first, first_manifest_path.read_text(),
                pinned_manifest_sha256=first_manifest.digest,
                minimum_generation=5,
            )
        # This older snapshot is internally valid if caller supplies a
        # weaker floor: actual anti-rollback requires independent custody.
        self.assertEqual(
            verify_fixture_snapshot(
                first, first_manifest_path.read_text(),
                pinned_manifest_sha256=first_manifest.digest,
                minimum_generation=1,
            ), first_manifest,
        )

    def test_weekly_manifest_generation_accepts_backdated_time_and_old_payload(self):
        """A higher generation alone cannot prove source clock monotonicity."""
        final_head = self.heads[-1]
        before = self.db.read_bars(self.identity)
        before_cursor = self.db.cursor(self.identity)
        result = self.weekly.commit(
            self.identity, self.initial, expected_head=final_head,
            observed_at_utc=self.times[0],  # older than current gen5 creation
        )
        self.assertTrue(result.manifest_changed)
        regressed_head = self.weekly.head(self.identity)
        regressed = self.weekly._indexes[regressed_head]
        self.assertEqual(regressed.generation, 6)
        self.assertEqual(regressed.parent_sha256, final_head)
        self.assertLess(regressed.created_at_utc, self.times[4])
        self.assertEqual(
            self.weekly.load(self.identity, pinned_head=regressed_head),
            self.initial,
        )
        with self.assertRaises(ValueError):
            self.db.apply_fixture_window(
                self.identity, self.initial,
                observed_at_utc=self.times[0],
                scope_start_utc=self.initial[0].start_utc,
                scope_end_utc=self.initial[-1].end_utc,
                complete_scope=False,
            )
        self.assertEqual(self.db.read_bars(self.identity), before)
        self.assertEqual(self.db.cursor(self.identity), before_cursor)
        # This is an IN-PROCESS SYNTHETIC replay counterexample, not an
        # authenticated Google Drive attack demonstration.
