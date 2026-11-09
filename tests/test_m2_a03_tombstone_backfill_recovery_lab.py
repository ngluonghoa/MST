"""A03 tombstone/backfill event + volatile crash quarantine negative tests.

Never interpret locally consistent SHA as independently authenticated source
or a production Google Drive cache floor. Uses real inherited V1 SQLite only.
"""
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.m2_a02_incremental_cache_oracle_lab import _apply, bar, instant
from scripts.m2_a03_v2_cache_consumer_contract import _hash, fixture_scope
from scripts.m2_a03_tombstone_backfill_recovery_lab import (
    SCHEMA, LocalCrashReviewJournal, SyntheticMaterializedFrame,
    SyntheticRevisionEvent, build_synthetic_fixture, create_frame,
    verify_local_event_chain,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore


def complete_chain():
    with TemporaryDirectory(prefix="mst-gh-event-chain-unit-") as tmp:
        store = SyntheticIncrementalStore(Path(tmp) / "test.sqlite")
        store.initialize()
        scope = fixture_scope()
        key = scope.legacy
        _apply(store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        cold = create_frame(store, scope, at=instant(20), stage="COLD",
                            parent=None, event=None)
        original = cold.revisions[11]
        tomb = SyntheticRevisionEvent(
            "TOMBSTONE", original.start_utc, instant(30), original.content_sha256,
        )
        _apply(store, key, (bar(10), bar(12)), now=30,
               start=10, end=13, complete=True)
        deleted = create_frame(store, scope, at=instant(30),
                               stage="TOMBSTONE", parent=cold, event=tomb)
        restore = replace(bar(11, close=D("150"), revision="r2"),
                          first_known_utc=instant(40))
        event = SyntheticRevisionEvent(
            "BACKFILL", original.start_utc, instant(40),
            original.content_sha256, restore.normalized_digest, "r2",
        )
        _apply(store, key, (restore,), now=40, start=11, end=12)
        backfilled = create_frame(store, scope, at=instant(40),
                                  stage="BACKFILL", parent=deleted, event=event)
        warm = create_frame(store, scope, at=instant(41),
                            stage="WARM", parent=backfilled, event=None)
        return (cold, deleted, backfilled, warm)


def patch_revisions(frame, revisions):
    return replace(
        frame, revisions=tuple(revisions),
        bar_revisions_digest=_hash([x.canonical() for x in revisions]),
    )


class ActualV1TombstoneBackfillPositiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = complete_chain()
        cls.proof = verify_local_event_chain(cls.f)
        cls.report = build_synthetic_fixture()

    def test_four_generations_genesis_to_warm(self):
        self.assertEqual(self.proof["schema"], SCHEMA)
        self.assertEqual(self.proof["committed_generations"], 4)
        self.assertEqual(tuple(x.stage for x in self.f),
                         ("COLD", "TOMBSTONE", "BACKFILL", "WARM"))

    def test_counts_recover_after_deletion(self):
        self.assertEqual([len(x.revisions) for x in self.f],
                         [20, 19, 20, 20])
        self.assertEqual(self.report["v1_deleted_bars"], 1)
        self.assertEqual(self.report["v1_backfilled_bars"], 1)

    def test_real_v1_indicator_dirty_tails_8_then_9(self):
        self.assertEqual(self.report["v1_delete_indicator_tail_recomputed"], 8)
        self.assertEqual(self.report["v1_backfill_indicator_tail_recomputed"], 9)
        self.assertTrue(self.report["all_indicator_snapshots_independent_oracle_verified"])

    def test_first_known_deletion_after_prior_snapshot(self):
        original, deleted = self.f[:2]
        self.assertEqual(deleted.event.first_known_utc, instant(30))
        self.assertGreater(deleted.event.first_known_utc, original.as_of_utc)
        self.assertNotIn(instant(11), [r.start_utc for r in deleted.revisions])
        self.assertIn(instant(11), [r.start_utc for r in original.revisions])

    def test_backfill_after_tombstone_and_first_known(self):
        _, deleted, restored, _ = self.f
        self.assertEqual(restored.event.first_known_utc, instant(40))
        self.assertGreater(restored.event.first_known_utc, deleted.as_of_utc)
        self.assertEqual(restored.revisions[11].revision_id, "r2")
        self.assertEqual(restored.revisions[11].first_known_utc, instant(40))

    def test_lineage_sha_matches_each_parent(self):
        for i in (1, 2, 3):
            self.assertEqual(self.f[i].parent_digest, self.f[i-1].digest)
        self.assertRegex(self.f[-1].digest, "^[0-9a-f]{64}$")

    def test_full_legacy_rights_versions_bound_through_four_states(self):
        self.assertEqual(len(self.f[0].policy_versions), 8)
        for frame in self.f:
            self.assertEqual(frame.scope_binding_sha256,
                             self.f[0].scope_binding_sha256)
            self.assertEqual(frame.policy_versions, self.f[0].policy_versions)

    def test_no_reuse_without_explicit_event(self):
        self.assertEqual(self.f[-1].revisions, self.f[-2].revisions)
        self.assertEqual(self.f[-1].ema_atr_digest, self.f[-2].ema_atr_digest)
        self.assertEqual(self.proof["pending_tombstones"], 0)

    def test_temporary_journal_flags_no_prod_rights(self):
        self.assertTrue(self.report["uncommitted_dirty_sqlite_quarantined"])
        self.assertTrue(self.report["clean_prepared_intent_discarded"])
        for key in (
            "independently_authenticated_source_receipts",
            "independent_signer_or_remote_floor_proven",
            "real_two_writer_cas_proven",
            "physical_google_drive_market_cache_written",
            "production_recovery_approved",
            "trading_authorized",
        ):
            with self.subTest(field=key):
                self.assertFalse(self.proof[key])

    def test_report_reproducible(self):
        self.assertEqual(self.report, build_synthetic_fixture())


class V2TombstoneFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cold, cls.deleted, cls.restored, cls.warm = complete_chain()

    def denied(self, frames, pattern):
        with self.assertRaisesRegex((ValueError, TypeError, PermissionError), pattern):
            verify_local_event_chain(tuple(frames))

    def test_no_chain_denied(self):
        self.denied((), "NONEMPTY_LOCAL")

    def test_missing_genesis_denied(self):
        self.denied((self.deleted, self.restored), "FULL_LOCAL_GENESIS")

    def test_skipped_generation_denied(self):
        self.denied((self.cold, self.restored), "GENERATION_SKIP")

    def test_wrong_parent_digest_denied(self):
        bad = replace(self.deleted, parent_digest="f" * 64)
        self.denied((self.cold, bad), "PARENT_DIGEST")

    def test_time_rewind_denied(self):
        bad = replace(self.deleted, as_of_utc=self.cold.as_of_utc)
        self.denied((self.cold, bad), "LOCAL_FRAME_TIME_REWIND")

    def test_rights_scope_drift_denied(self):
        bad = replace(self.deleted, scope_binding_sha256="f" * 64)
        self.denied((self.cold, bad), "FULL_RIGHTS")

    def test_rights_policy_text_drift_denied(self):
        fields = dict(self.deleted.policy_versions)
        fields["rights"] = "RIGHTS.REVOKED"
        bad = replace(self.deleted, policy_versions=tuple(sorted(fields.items())))
        self.denied((self.cold, bad), "FULL_RIGHTS")

    def test_wrong_partition_denied(self):
        bad = replace(self.deleted, partition_sha256="f" * 64)
        self.denied((self.cold, bad), "FULL_RIGHTS")

    def test_no_tombstone_event_denied(self):
        with self.assertRaisesRegex(ValueError, "STAGED_EVENT"):
            replace(self.deleted, event=None)

    def test_tombstone_event_cannot_carry_restoration_bytes(self):
        with self.assertRaisesRegex(ValueError, "TOMBSTONE_CANNOT"):
            replace(self.deleted.event, restored_content_sha256="a" * 64)

    def test_tombstone_must_reference_exact_deleted_sha(self):
        bad = replace(self.deleted,
                      event=replace(self.deleted.event,
                                    previous_content_sha256="f" * 64))
        self.denied((self.cold, bad), "TOMBSTONE_PRIOR_CONTENT")

    def test_tombstone_must_name_removed_bar(self):
        bad = replace(self.deleted,
                      event=replace(self.deleted.event, bar_start_utc=instant(10)))
        self.denied((self.cold, bad), "DELETE_MUST_MATCH")

    def test_no_silent_historical_deletion(self):
        bad = replace(self.deleted, stage="WARM", event=None)
        self.denied((self.cold, bad), "WARM_MUST_PRESERVE")

    def test_delete_two_bars_with_one_event_denied(self):
        fewer = [x for x in self.deleted.revisions if x.start_utc != instant(12)]
        bad = patch_revisions(self.deleted, fewer)
        self.denied((self.cold, bad), "DELETE_MUST_MATCH")

    def test_tombstone_first_known_not_in_the_past(self):
        bad = replace(self.deleted, event=replace(
            self.deleted.event, first_known_utc=instant(20),
        ))
        self.denied((self.cold, bad), "RETROACTIVE_OR_FUTURE")

    def test_tombstone_future_known_denied(self):
        with self.assertRaisesRegex(ValueError, "EVENT_STAGE_OR_ASOF"):
            replace(self.deleted, event=replace(
                self.deleted.event, first_known_utc=instant(31),
            ))

    def test_backfill_requires_prior_tombstone(self):
        bad = replace(self.restored, generation=2,
                      parent_digest=self.cold.digest)
        self.denied((self.cold, bad), "RESTORE_MUST_MATCH|BACKFILL_WITHOUT")

    def test_backfill_prior_digest_must_match_tombstone(self):
        bad = replace(self.restored,
                      event=replace(self.restored.event,
                                    previous_content_sha256="a" * 64))
        self.denied((self.cold, self.deleted, bad), "BACKFILL_TOMBSTONE")

    def test_backfill_new_revision_content_digest_must_match(self):
        bad = replace(self.restored,
                      event=replace(self.restored.event,
                                    restored_content_sha256="a" * 64))
        self.denied((self.cold, self.deleted, bad), "BACKFILL_NEW_REVISION")

    def test_backfill_revision_label_must_match(self):
        bad = replace(self.restored,
                      event=replace(self.restored.event,
                                    restored_revision_id="r99"))
        self.denied((self.cold, self.deleted, bad), "BACKFILL_NEW_REVISION")

    def test_backfill_first_known_must_match_new_revision(self):
        bad = replace(self.restored, event=replace(
            self.restored.event, first_known_utc=instant(39),
        ))
        self.denied((self.cold, self.deleted, bad), "BACKFILL_NEW_REVISION")

    def test_retroactive_backfill_cannot_precede_tombstone(self):
        bad = replace(self.restored, event=replace(
            self.restored.event, first_known_utc=instant(29),
        ))
        self.denied((self.cold, self.deleted, bad), "RETROACTIVE_OR_FUTURE")

    def test_backfill_extra_unattested_bar_denied(self):
        new = replace(self.restored.revisions[0],
                      start_utc=instant(50), end_utc=instant(51),
                      first_known_utc=instant(51))
        with self.assertRaisesRegex(ValueError, "FUTURE_KNOWN"):
            patch_revisions(self.restored, tuple(self.restored.revisions) + (new,))

    def test_unversioned_price_correction_denied(self):
        b = list(self.restored.revisions)
        b[5] = replace(b[5], revision_id="r3")
        bad = patch_revisions(self.restored, b)
        self.denied((self.cold, self.deleted, bad), "UNVERSIONED_EXISTING_BAR_REWRITE")

    def test_delete_without_indicator_invalidation_denied(self):
        bad = replace(self.deleted, ema_atr_digest=self.cold.ema_atr_digest)
        self.denied((self.cold, bad), "DELETE_MUST_INVALIDATE")

    def test_restore_without_indicator_invalidation_denied(self):
        bad = replace(self.restored, ema_atr_digest=self.deleted.ema_atr_digest)
        self.denied((self.cold, self.deleted, bad), "BACKFILL_MUST_RECOMPUTE")

    def test_warm_does_not_change_indicator_digest(self):
        bad = replace(self.warm, ema_atr_digest="f" * 64)
        self.denied((self.cold, self.deleted, self.restored, bad),
                    "WARM_MUST_PRESERVE")

    def test_warm_does_not_mutate_bar(self):
        changed = list(self.warm.revisions)
        changed[5] = replace(changed[5], revision_id="r3")
        bad = patch_revisions(self.warm, changed)
        self.denied((self.cold, self.deleted, self.restored, bad),
                    "UNVERSIONED_EXISTING_BAR_REWRITE")

    def test_noncanonical_revision_digest_denied(self):
        with self.assertRaisesRegex(ValueError, "MATERIALIZED_REVISION_DIGEST"):
            replace(self.restored, bar_revisions_digest="f" * 64)

    def test_duplicate_materialized_bar_denied(self):
        with self.assertRaisesRegex(ValueError, "UNSORTED_OR_DUPLICATE"):
            replace(self.restored, revisions=(
                self.restored.revisions[0], *self.restored.revisions,
            ))

    def test_event_type_invalid_denied(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SOURCE_EVENT"):
            replace(self.deleted.event, action="AUTO_PURGE")

    def test_event_requires_utc_first_known(self):
        with self.assertRaises(TypeError):
            replace(self.deleted.event, first_known_utc=instant(30).replace(tzinfo=None))

    def test_complete_eight_policy_versions_enforced(self):
        with self.assertRaisesRegex(ValueError, "COMPLETE_EIGHT_POLICY"):
            replace(self.restored, policy_versions=self.restored.policy_versions[:-1])


class LocalCrashJournalTests(unittest.TestCase):
    def setUp(self):
        ctx = TemporaryDirectory()
        self.addCleanup(ctx.cleanup)
        self.store = SyntheticIncrementalStore(Path(ctx.name) / "journal.sqlite")
        self.store.initialize()
        self.scope = fixture_scope()
        key = self.scope.legacy
        _apply(self.store, key, tuple(bar(i) for i in range(20)),
               now=20, start=0, end=20, complete=True, full=True)
        self.cold = create_frame(self.store, self.scope, at=instant(20),
                                 stage="COLD", parent=None, event=None)
        self.journal = LocalCrashReviewJournal(self.cold)

    def test_crash_before_sqlite_mutation_discards_prepared_warm(self):
        future = create_frame(self.store, self.scope, at=instant(21),
                              stage="WARM", parent=self.cold, event=None)
        self.journal.prepare(future)
        result = self.journal.recover_review_only(
            self.store, self.scope, now=instant(21))
        self.assertEqual(result["committed_generation"], 1)
        self.assertTrue(result["uncommitted_candidate_discarded"])
        self.assertEqual(self.journal.head, self.cold)
        self.assertFalse(result["durable_cross_run_recovery_proven"])

    def test_dirty_sqlite_after_prepare_is_quarantined_not_auto_accepted(self):
        target = self.cold.revisions[11]
        event = SyntheticRevisionEvent(
            "TOMBSTONE", target.start_utc, instant(30),
            target.content_sha256,
        )
        _apply(self.store, self.scope.legacy,
               (bar(10), bar(12)), now=30,
               start=10, end=13, complete=True)
        deleted = create_frame(self.store, self.scope,
                               at=instant(30), stage="TOMBSTONE",
                               parent=self.cold, event=event)
        self.journal.prepare(deleted)
        with self.assertRaisesRegex(PermissionError, "QUARANTINED"):
            self.journal.recover_review_only(
                self.store, self.scope, now=instant(30))
        self.assertEqual(self.journal.head, self.cold)
        self.journal.commit(self.store, self.scope)
        self.assertEqual(self.journal.head, deleted)

    def test_commit_requires_prepare(self):
        with self.assertRaisesRegex(ValueError, "NO_PREPARED"):
            self.journal.commit(self.store, self.scope)

    def test_only_one_uncommitted_intent_allowed(self):
        candidate = create_frame(self.store, self.scope,
                                 at=instant(21), stage="WARM",
                                 parent=self.cold, event=None)
        self.journal.prepare(candidate)
        with self.assertRaisesRegex(ValueError, "ONE_PENDING"):
            self.journal.prepare(candidate)

    def test_commit_refuses_changed_checkpoint_after_prepare(self):
        import sqlite3
        pending = create_frame(self.store, self.scope,
                               at=instant(21), stage="WARM",
                               parent=self.cold, event=None)
        self.journal.prepare(pending)
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE fixture_checkpoints SET ema20='999' "
                       "WHERE cache_key=? AND start_utc=?",
                       (self.scope.legacy.fingerprint,
                        bar(5).start_utc.isoformat()))
        with self.assertRaises((ValueError, RuntimeError)):
            self.journal.commit(self.store, self.scope)
        self.assertEqual(self.journal.head, self.cold)


if __name__ == "__main__":
    unittest.main()
