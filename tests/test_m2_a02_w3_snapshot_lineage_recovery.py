"""MST A02 W3: snapshot versus weekly reconstruction audit-custody probes.

Only fabricated OHLCV on ephemeral GitHub-hosted CI. Preserve the exact
63-module Swing v1 baseline. These tests do NOT attest actual Google Drive
transport, historical market replay, licensed retention or production use.
"""
import sqlite3
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from swing_trading.cache_snapshot_bundle import (
    create_fixture_snapshot, restore_fixture_snapshot,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore, full_recompute
from swing_trading.segmented_cache import SyntheticWeeklyChunkStore
from test_segmented_cache import NOW, fake, key


class SnapshotLineageRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.identity = key("AUDITFIXTURE")
        self.baseline = tuple(fake(i) for i in range(21))
        self.original = self.baseline[3]
        self.revision = fake(
            3, price=Decimal("233"), revision="r2",
            known=NOW - timedelta(days=1),
        )
        self.current = (
            self.baseline[:3] + (self.revision,) + self.baseline[4:]
        )
        self.store = SyntheticIncrementalStore(self.root / "source.sqlite")
        self.store.initialize()
        self.initial_as_of = NOW - timedelta(days=2)
        self.store.apply_fixture_window(
            self.identity, self.baseline,
            observed_at_utc=self.initial_as_of,
            scope_start_utc=self.baseline[0].start_utc,
            scope_end_utc=self.baseline[-1].end_utc,
            complete_scope=True, full_session_reconciled=True,
        )
        self.store.apply_fixture_window(
            self.identity, (self.revision,),
            observed_at_utc=NOW,
            scope_start_utc=self.revision.start_utc,
            scope_end_utc=self.revision.end_utc,
            complete_scope=False,
        )
        self.weekly = SyntheticWeeklyChunkStore()
        self.weekly.commit(
            self.identity, self.baseline, expected_head=None,
            observed_at_utc=self.initial_as_of,
        )
        self.old_head = self.weekly.head(self.identity)
        self.weekly.commit(
            self.identity, self.current, expected_head=self.old_head,
            observed_at_utc=NOW,
        )
        self.current_head = self.weekly.head(self.identity)

    def audit_rows(self, path):
        with sqlite3.connect(path) as connection:
            return tuple(connection.execute(
                "SELECT cache_key,start_utc,event_type,old_digest,new_digest,"
                "observed_at_utc FROM fixture_lineage ORDER BY id"
            ).fetchall())

    def sqlite_snapshot(self, suffix):
        snapshot = self.root / f"{suffix}-snapshot.sqlite"
        manifest_path = self.root / f"{suffix}-manifest.json"
        m = create_fixture_snapshot(
            self.store, snapshot, manifest_path, snapshot_id=suffix,
            generation=1, previous_manifest_sha256=None, created_at_utc=NOW,
        )
        recovered = restore_fixture_snapshot(
            snapshot, self.root / f"{suffix}-restored.sqlite",
            manifest_path.read_text(), pinned_manifest_sha256=m.digest,
        )
        return m, recovered

    def weekly_restore(self, suffix):
        recovered = SyntheticIncrementalStore(
            self.root / f"{suffix}-restored.sqlite"
        )
        recovered.initialize()
        count = self.weekly.restore_full(
            recovered, self.identity, pinned_head=self.current_head,
        )
        self.assertEqual(count, len(self.current))
        return recovered

    def test_sqlite_snapshot_preserves_existing_revision_audit_and_cursor(self):
        manifest, recovered = self.sqlite_snapshot("audit")
        self.assertEqual(
            self.audit_rows(recovered.path),
            self.audit_rows(self.store.path),
        )
        self.assertEqual(len(self.audit_rows(recovered.path)), 22)
        self.assertEqual(
            self.audit_rows(recovered.path)[-1][2],
            "REVISE",
        )
        self.assertEqual(
            recovered.cursor(self.identity),
            self.store.cursor(self.identity),
        )
        self.assertEqual(
            recovered.read_checkpoints(self.identity),
            self.store.read_checkpoints(self.identity),
        )
        self.assertEqual(
            recovered.read_checkpoints(self.identity),
            full_recompute(self.current),
        )
        self.assertFalse(manifest.live_market_data_authorized)

    def test_weekly_restore_rebuilds_indicators_but_not_prior_audit_events(self):
        restored = self.weekly_restore("weekly")
        source_audit = self.audit_rows(self.store.path)
        restored_audit = self.audit_rows(restored.path)
        self.assertEqual(restored.read_bars(self.identity), self.current)
        self.assertEqual(
            restored.read_checkpoints(self.identity),
            self.store.read_checkpoints(self.identity),
        )
        self.assertEqual(
            len(restored_audit), len(self.current),
        )
        self.assertTrue(all(row[2] == "APPEND" for row in restored_audit))
        self.assertEqual(source_audit[-1][2], "REVISE")
        self.assertNotEqual(restored_audit, source_audit)
        self.assertIsNone(
            restored.cursor(self.identity).last_full_reconciled_utc,
        )
        self.assertEqual(
            self.store.cursor(self.identity).last_full_reconciled_utc,
            self.initial_as_of,
        )
        # Warm numerical equivalence != lossless audit/event restore.

    def test_sqlite_snapshot_retains_prior_digest_not_old_price_payload(self):
        _, recovered = self.sqlite_snapshot("digest")
        with sqlite3.connect(recovered.path) as connection:
            old_digest, new_digest = connection.execute(
                "SELECT old_digest,new_digest FROM fixture_lineage "
                "WHERE event_type='REVISE' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            saved_close = connection.execute(
                "SELECT c FROM fixture_bars WHERE cache_key=? AND start_utc=?",
                (self.identity.fingerprint, self.original.start_utc.isoformat()),
            ).fetchone()[0]
        self.assertEqual(old_digest, self.original.normalized_digest)
        self.assertEqual(new_digest, self.revision.normalized_digest)
        self.assertNotEqual(old_digest, new_digest)
        self.assertEqual(Decimal(saved_close), self.revision.close)
        self.assertNotEqual(Decimal(saved_close), self.original.close)
        # No archived old OHLCV payload is present in the SQLite fixture
        # event table, even though its old content digest survives.

    def test_latest_only_weekly_reader_rejects_prior_manifest_asof_pin(self):
        self.assertNotEqual(self.old_head, self.current_head)
        with self.assertRaisesRegex(ValueError, "Stale or rolled-back fixture index"):
            self.weekly.load(self.identity, pinned_head=self.old_head)
        self.assertEqual(
            self.weekly.load(self.identity, pinned_head=self.current_head),
            self.current,
        )
        # Historic in-memory objects exist in this test double, but the
        # public read API is latest-only: not a qualified point-in-time feed.

    def test_post_restore_warm_revision_preserves_current_global_parity(self):
        weekly = self.weekly_restore("warm")
        next_revision = fake(
            19, price=Decimal("271"), revision="r3",
            known=NOW + timedelta(hours=1),
        )
        update = weekly.apply_fixture_window(
            self.identity, (next_revision,),
            observed_at_utc=NOW + timedelta(hours=2),
            scope_start_utc=next_revision.start_utc,
            scope_end_utc=next_revision.end_utc,
            complete_scope=False,
        )
        self.assertEqual(update.revised, 1)
        self.assertEqual(update.indicator_bars_recomputed, 2)
        self.assertEqual(
            weekly.read_checkpoints(self.identity),
            full_recompute(weekly.read_bars(self.identity)),
        )
        # A valid warm checkpoint does not recover lost historical audit.
