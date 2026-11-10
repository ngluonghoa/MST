"""MST A03 review-only two-reader/two-writer interleaving tests.

All writer labels, SHA chains and leases are self-asserted in ONE process.
Intentionally test split brain with isolated replicas and a reset reader.
"""
from dataclasses import replace
import unittest

from scripts.m2_a02_incremental_cache_oracle_lab import instant
from scripts.m2_a03_dual_reader_writer_interleaving_lab import (
    SCHEMA, SingleMemorySequencer, WriterClaim, competing_frames, run_race_lab,
)
from scripts.m2_a03_reader_visibility_barrier_lab import (
    Observed, SyntheticReader, Visible,
)
from scripts.m2_a03_tombstone_backfill_recovery_lab import verify_local_event_chain


class A03DualReaderWriterRaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames, cls.fork = competing_frames()
        cls.genesis = cls.frames[0]

    def new(self):
        sequencer = SingleMemorySequencer(self.genesis)
        return sequencer, sequencer.observe()

    def ticket(self, actor, observed, frame):
        return WriterClaim.from_observation(actor, observed, frame)

    def winner(self, sequencer, actor, observed, frame):
        claim = self.ticket(actor, observed, frame)
        sequencer.claim(claim, frame)
        sequencer.materialize(actor)
        sequencer.commit(actor)
        sequencer.expose(actor)

    def denied(self, callback, pattern):
        with self.assertRaisesRegex((PermissionError, ValueError, TypeError), pattern):
            callback()

    def test_existing_four_real_v1_frames_preserved(self):
        self.assertEqual([x.stage for x in self.frames],
                         ["COLD", "TOMBSTONE", "BACKFILL", "WARM"])
        self.assertEqual([len(x.revisions) for x in self.frames],
                         [20, 19, 20, 20])

    def test_competing_g2_has_same_parent_but_distinct_digest(self):
        self.assertEqual(self.frames[1].parent_digest, self.fork.parent_digest)
        self.assertNotEqual(self.frames[1].digest, self.fork.digest)
        self.assertEqual(self.frames[1].generation, self.fork.generation)

    def test_each_local_g2_causal_chain_is_valid_by_itself(self):
        verify_local_event_chain((self.genesis, self.frames[1]))
        verify_local_event_chain((self.genesis, self.fork))

    def test_writer_claim_captures_observed_head_and_payload(self):
        seq, start = self.new()
        claim = self.ticket("writer-A", start, self.frames[1])
        self.assertEqual(claim.expected_generation, 1)
        self.assertEqual(claim.expected_frame_sha256, self.genesis.digest)
        self.assertEqual(claim.candidate_frame_sha256, self.frames[1].digest)

    def test_blank_actor_label_denied(self):
        seq, start = self.new()
        self.denied(lambda: self.ticket("", start, self.frames[1]), "ACTOR_LABEL")

    def test_nontext_actor_denied(self):
        seq, start = self.new()
        self.denied(lambda: self.ticket(42, start, self.frames[1]), "ACTOR_LABEL")

    def test_invalid_expected_generation_denied(self):
        seq, start = self.new()
        for x in (0, -1, 1.0, True):
            with self.subTest(generation=x):
                self.denied(lambda: WriterClaim("writer-A", x,
                             self.genesis.digest, self.frames[1].digest),
                            "INVALID_EXPECTED_GENERATION")

    def test_forged_or_short_hash_in_claim_denied(self):
        self.denied(lambda: WriterClaim("A", 1, "broken", self.fork.digest),
                    "SHA|DIGEST|HASH")
        self.denied(lambda: WriterClaim("A", 1, self.genesis.digest, "bad"),
                    "SHA|DIGEST|HASH")

    def test_claim_requires_actual_visible_snapshot(self):
        seq, start = self.new()
        self.denied(lambda: self.ticket("A", replace(start, visible=None),
                                        self.frames[1]), "CLAIM_REQUIRES_VISIBLE")

    def test_claim_rejects_wrong_candidate_type(self):
        seq, start = self.new()
        self.denied(lambda: self.ticket("A", start, object()),
                    "CLAIM_REQUIRES_TYPED_FRAME")

    def test_claim_rejects_untyped_input(self):
        seq, start = self.new()
        self.denied(lambda: seq.claim(object(), self.frames[1]),
                    "TYPED_WRITER_CLAIM")

    def test_first_writer_can_claim_g2(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        self.assertEqual(seq.active_actor, "A")
        self.assertEqual(seq.observe().visible.generation, 1)

    def test_second_writer_blocked_while_first_pending(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        self.denied(lambda: seq.claim(self.ticket("B", start, self.fork),
                                      self.fork), "VOLATILE_WRITER_ALREADY_ACTIVE")

    def test_second_writer_blocked_even_after_first_commits_invisible(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.commit("A")
        self.denied(lambda: seq.claim(self.ticket("B", start, self.fork),
                                      self.fork), "VOLATILE_WRITER_ALREADY_ACTIVE")

    def test_wrong_actor_cannot_materialize(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        self.denied(lambda: seq.materialize("B"), "OWNER_MISMATCH")

    def test_wrong_actor_cannot_commit(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        self.denied(lambda: seq.commit("B"), "OWNER_MISMATCH")

    def test_wrong_actor_cannot_make_visible(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.commit("A")
        self.denied(lambda: seq.expose("B"), "OWNER_MISMATCH")

    def test_missing_payload_blocks_commit(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        self.denied(lambda: seq.commit("A"), "MATERIALIZED_PAYLOAD_MISSING")

    def test_mutated_payload_blocks_commit(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.publisher.objects[self.frames[1].digest] = self.genesis
        self.denied(lambda: seq.commit("A"), "MATERIALIZED_PAYLOAD_MISSING")

    def test_prepared_and_materialized_only_do_not_expose_g2(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        self.assertEqual(seq.observe().visible.generation, 1)
        self.assertEqual(SyntheticReader(self.genesis.digest,
                         self.genesis.scope_binding_sha256).admit(seq.observe())["generation"], 1)

    def test_committed_unpublished_g2_not_reader_visible(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.commit("A")
        reader = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.denied(lambda: reader.admit(seq.observe(), require_generation=2),
                    "REQUIRED_READER_VISIBLE")

    def test_published_g2_is_available_to_both_readers(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        for label in ("R1", "R2"):
            with self.subTest(reader=label):
                r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
                self.assertEqual(r.admit(seq.observe())["generation"], 2)

    def test_writer_ticket_stales_after_visible_head_advances(self):
        seq, start = self.new()
        stale = self.ticket("B", start, self.fork)
        self.winner(seq, "A", start, self.frames[1])
        self.denied(lambda: seq.claim(stale, self.fork),
                    "STALE_WRITER_EXPECTED_HEAD_DENIED")

    def test_previous_writer_ticket_stales_even_for_same_actor(self):
        seq, start = self.new()
        old = self.ticket("A", start, self.frames[1])
        self.winner(seq, "A", start, self.frames[1])
        self.denied(lambda: seq.claim(old, self.frames[1]), "STALE_WRITER_EXPECTED")

    def test_wrong_expected_sha_denied(self):
        seq, start = self.new()
        old = self.ticket("A", start, self.frames[1])
        forged = replace(old, expected_frame_sha256="f"*64)
        self.denied(lambda: seq.claim(forged, self.frames[1]), "STALE_WRITER_EXPECTED")

    def test_wrong_expected_generation_denied(self):
        seq, start = self.new()
        old = self.ticket("A", start, self.frames[1])
        forged = replace(old, expected_generation=2)
        self.denied(lambda: seq.claim(forged, self.frames[1]), "STALE_WRITER_EXPECTED")

    def test_candidate_payload_digest_mismatch_denied(self):
        seq, start = self.new()
        bad = replace(self.ticket("A", start, self.frames[1]),
                      candidate_frame_sha256="f"*64)
        self.denied(lambda: seq.claim(bad, self.frames[1]), "CANDIDATE_PAYLOAD")

    def test_noncontiguous_writer_generation_denied(self):
        seq, start = self.new()
        wrong = self.ticket("A", start, self.frames[2])
        self.denied(lambda: seq.claim(wrong, self.frames[2]),
                    "NONCONTIGUOUS_WRITER_GENERATION")

    def test_rights_policy_crosslineage_denied(self):
        seq, start = self.new()
        changed = replace(self.frames[1], scope_binding_sha256="f"*64)
        claim = self.ticket("A", start, changed)
        self.denied(lambda: seq.claim(claim, changed), "FULL_RIGHTS_OR_POLICY_SCOPE_DRIFT")

    def test_reader_one_after_g2_denies_prior_g1(self):
        seq, start = self.new()
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        r.admit(start)
        self.winner(seq, "A", start, self.frames[1])
        r.admit(seq.observe())
        self.denied(lambda: r.admit(start), "STALE_READ_BELOW_SESSION_FLOOR")

    def test_reader_two_without_floor_can_still_consume_g1(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.assertEqual(r.admit(start)["generation"], 1)

    def test_reader_two_requiring_g2_denies_old_g1(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.denied(lambda: r.admit(start, require_generation=2),
                    "REQUIRED_READER_VISIBLE_GENERATION_ABSENT")

    def test_reader_two_after_learning_g2_fences_g1(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        r.admit(seq.observe())
        self.denied(lambda: r.admit(start), "STALE_READ_BELOW_SESSION_FLOOR")

    def test_reader_torn_visible_pointer_and_old_body_denied(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        current = seq.observe()
        torn = replace(current, frames=start.frames, commits=start.commits)
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.denied(lambda: r.admit(torn), "INCOMPLETE_VISIBLE_CHAIN")

    def test_reader_old_marker_with_new_chain_denied(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        current = seq.observe()
        torn = replace(current, visible=start.visible)
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.denied(lambda: r.admit(torn), "INCOMPLETE_VISIBLE_CHAIN")

    def test_isolated_replica_accepts_competing_g2(self):
        seq, start = self.new()
        self.winner(seq, "B", start, self.fork)
        self.assertEqual(seq.observe().visible.frame_sha256, self.fork.digest)

    def test_two_replica_winners_demonstrate_split_brain(self):
        seq1, view1 = self.new()
        seq2, view2 = self.new()
        self.winner(seq1, "A", view1, self.frames[1])
        self.winner(seq2, "B", view2, self.fork)
        self.assertEqual(seq1.observe().visible.generation,
                         seq2.observe().visible.generation)
        self.assertNotEqual(seq1.observe().visible.frame_sha256,
                            seq2.observe().visible.frame_sha256)

    def test_session_with_known_g2_rejects_same_generation_fork(self):
        seq1, view1 = self.new()
        seq2, view2 = self.new()
        self.winner(seq1, "A", view1, self.frames[1])
        self.winner(seq2, "B", view2, self.fork)
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        r.admit(seq1.observe())
        self.denied(lambda: r.admit(seq2.observe()), "SESSION_FLOOR_FORK_OR_REWRITE")

    def test_fresh_session_accepts_self_attested_rival_fork(self):
        seq, start = self.new()
        self.winner(seq, "B", start, self.fork)
        r = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        out = r.admit(seq.observe())
        self.assertEqual(out["generation"], 2)
        self.assertFalse(out["independent_witness_or_signer"])

    def test_reset_reader_accepts_consistent_old_g1(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        old = SyntheticReader(self.genesis.digest, self.genesis.scope_binding_sha256)
        self.assertEqual(old.admit(start)["generation"], 1)
        self.assertFalse(old.admit(start)["durable_cross_run_rollback_floor"])

    def test_source_g3_cannot_follow_the_rival_g2(self):
        self.denied(lambda: verify_local_event_chain(
            (self.genesis, self.fork, self.frames[2])), "PARENT_DIGEST_MISMATCH")

    def test_backdated_event_is_denied_before_race(self):
        self.denied(lambda: replace(self.fork, as_of_utc=instant(29)),
                    "EVENT_STAGE_OR_ASOF_MISMATCH")

    def test_crash_before_commit_does_not_expose_object(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.crash()
        self.assertEqual(seq.observe().visible.generation, 1)
        self.assertFalse(seq.publisher.in_doubt)
        self.assertIsNone(seq.active_actor)

    def test_crash_after_commit_before_visibility_quarantines(self):
        seq, start = self.new()
        seq.claim(self.ticket("A", start, self.frames[1]), self.frames[1])
        seq.materialize("A")
        seq.commit("A")
        seq.crash()
        self.assertTrue(seq.publisher.in_doubt)
        self.assertEqual(seq.observe().visible.generation, 1)
        self.denied(lambda: seq.claim(self.ticket("B", start, self.fork),
                                      self.fork), "COMMITTED_INVISIBLE_HEAD_QUARANTINED")

    def test_crash_after_visible_preserves_only_inmemory_head(self):
        seq, start = self.new()
        self.winner(seq, "A", start, self.frames[1])
        seq.crash()
        self.assertEqual(seq.observe().visible.generation, 2)

    def test_full_synthetic_negative_report_is_deterministic(self):
        report = run_race_lab()
        self.assertEqual(report, run_race_lab())
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["winning_shared_generation"], 2)

    def test_report_all_external_trust_and_release_gates_false(self):
        report = run_race_lab()
        for flag in (
            "independent_external_signer_verified",
            "nonresettable_external_floor_verified",
            "real_two_principal_server_cas_verified",
            "real_drive_cache_or_atomic_cross_service_read",
            "licensed_market_source_first_known_verified",
            "production_reader_writer_or_trading_authorized",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(report[flag])

    def test_report_explicit_split_brain_and_session_reset_proven(self):
        report = run_race_lab()
        self.assertTrue(report["isolated_coordinator_split_brain_valid_local_forks"])
        self.assertTrue(report["reset_reader_accepts_old_valid_genesis"])
        self.assertTrue(report["fresh_reader_accepts_self_attested_rival_fork"])
        self.assertTrue(report["prior_reader_rejects_same_generation_fork"])


if __name__ == "__main__":
    unittest.main()
