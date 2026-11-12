"""A03 versioned synthetic publication barrier and stale-read negative tests.

These checks never authenticate Google Drive bytes, GitHub witness protection,
vendor first-known timestamps or a nonresettable cross-run high-water mark.
"""
from dataclasses import replace
import unittest

from scripts.m2_a03_reader_visibility_barrier_lab import (
    SCHEMA, Committed, Observed, Prepared, SyntheticPublisher,
    SyntheticReader, Visible, real_v1_synthetic_frames, run_lab,
)


class SyntheticReaderBarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = real_v1_synthetic_frames()

    def new(self):
        p = SyntheticPublisher(self.frames[0])
        r = SyntheticReader(self.frames[0].digest, self.frames[0].scope_binding_sha256)
        return p, r

    def advance(self, p, frame):
        p.prepare(frame)
        p.materialize()
        p.commit()
        p.publish_visible()

    def denied(self, callback, pattern):
        with self.assertRaisesRegex((PermissionError, ValueError, TypeError), pattern):
            callback()

    def test_synthetic_oracle_chain_has_four_generations(self):
        self.assertEqual([f.generation for f in self.frames], [1, 2, 3, 4])
        self.assertEqual([len(f.revisions) for f in self.frames], [20, 19, 20, 20])

    def test_genesis_read_is_explicitly_review_only(self):
        p, r = self.new()
        proof = r.admit(p.observe())
        self.assertEqual(proof["generation"], 1)
        self.assertFalse(proof["production_reader_authorized"])
        self.assertFalse(proof["durable_cross_run_rollback_floor"])

    def test_prepare_does_not_make_candidate_visible(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        self.denied(lambda: r.admit(p.observe(), require_generation=2),
                    "REQUIRED_READER_VISIBLE")
        self.assertEqual(r.admit(p.observe())["generation"], 1)

    def test_payload_materialization_not_visibility(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        self.denied(lambda: r.admit(p.observe(), require_generation=2),
                    "REQUIRED_READER_VISIBLE")

    def test_committed_not_reader_visible(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        p.commit()
        self.denied(lambda: r.admit(p.observe(), require_generation=2),
                    "REQUIRED_READER_VISIBLE")
        self.assertEqual(p.visible.generation, 1)

    def test_visible_after_exact_commit_and_payload(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        self.assertEqual(r.admit(p.observe(), require_generation=2)["generation"], 2)

    def test_all_four_stages_reach_reader_visible(self):
        p, r = self.new()
        for frame in self.frames[1:]:
            self.advance(p, frame)
            self.assertEqual(r.admit(p.observe())["generation"], frame.generation)

    def test_stale_snapshot_after_advancement_denied(self):
        p, r = self.new()
        original = p.observe()
        r.admit(original)
        self.advance(p, self.frames[1])
        r.admit(p.observe())
        self.denied(lambda: r.admit(original), "STALE_READ")

    def test_stale_snapshot_with_explicit_required_generation_denied(self):
        p, r = self.new()
        self.denied(lambda: r.admit(p.observe(), require_generation=3),
                    "REQUIRED_READER_VISIBLE")

    def test_reader_missing_visible_marker_denied(self):
        p, r = self.new()
        self.denied(lambda: r.admit(replace(p.observe(), visible=None)), "NO_READER_VISIBLE")

    def test_visible_marker_ahead_of_commit_denied(self):
        p, r = self.new()
        fake = Visible(2, self.frames[1].digest, "a" * 64)
        self.denied(lambda: r.admit(replace(p.observe(), visible=fake)),
                    "INCOMPLETE_VISIBLE_CHAIN")

    def test_committed_receipt_ahead_of_marker_not_promoted(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        p.commit()
        self.assertEqual(r.admit(p.observe())["generation"], 1)

    def test_missing_last_payload_with_visible_marker_denied(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        observed = p.observe()
        bad = replace(observed, frames=observed.frames[:-1])
        self.denied(lambda: r.admit(bad), "INCOMPLETE_VISIBLE_CHAIN")

    def test_missing_last_receipt_with_visible_marker_denied(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        observed = p.observe()
        self.denied(lambda: r.admit(replace(observed, commits=observed.commits[:-1])),
                    "INCOMPLETE_VISIBLE_CHAIN")

    def test_tampered_visible_pointer_frame_denied(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        observed = p.observe()
        bad = replace(observed.visible, frame_sha256="f" * 64)
        self.denied(lambda: r.admit(replace(observed, visible=bad)),
                    "VISIBLE_POINTER_WITHOUT_EXACT_COMMIT")

    def test_tampered_visible_pointer_receipt_denied(self):
        p, r = self.new()
        observed = p.observe()
        bad = replace(observed.visible, commit_sha256="f" * 64)
        self.denied(lambda: r.admit(replace(observed, visible=bad)),
                    "VISIBLE_POINTER_WITHOUT_EXACT_COMMIT")

    def test_tampered_commit_receipt_digest_denied(self):
        p, r = self.new()
        observed = p.observe()
        wrong = replace(observed.commits[0].prepared, frame_sha256="f" * 64)
        self.denied(lambda: r.admit(replace(observed, commits=(Committed(wrong),))),
                    "COMMIT_RECEIPT_DOES_NOT_BIND_FRAME")

    def test_tampered_commit_rights_denied(self):
        p, r = self.new()
        observed = p.observe()
        wrong = replace(observed.commits[0].prepared, rights_scope_sha256="e" * 64)
        self.denied(lambda: r.admit(replace(observed, commits=(Committed(wrong),))),
                    "COMMIT_RECEIPT_DOES_NOT_BIND_FRAME")

    def test_tampered_commit_generation_denied(self):
        p, r = self.new()
        observed = p.observe()
        wrong = replace(observed.commits[0].prepared, generation=2)
        self.denied(lambda: r.admit(replace(observed, commits=(Committed(wrong),))),
                    "COMMIT_RECEIPT_DOES_NOT_BIND_FRAME")

    def test_wrong_pinned_genesis_denied(self):
        p, _ = self.new()
        wrong = SyntheticReader("f" * 64, self.frames[0].scope_binding_sha256)
        self.denied(lambda: wrong.admit(p.observe()), "PINNED_GENESIS")

    def test_wrong_rights_scope_denied(self):
        p, _ = self.new()
        wrong = SyntheticReader(self.frames[0].digest, "e" * 64)
        self.denied(lambda: wrong.admit(p.observe()), "RIGHTS_SCOPE")

    def test_invalid_required_generation_denied(self):
        p, r = self.new()
        for generation in (0, -1, 1.5, True):
            with self.subTest(generation=generation):
                self.denied(lambda: r.admit(p.observe(), require_generation=generation),
                            "INVALID_REQUIRED_GENERATION")

    def test_prepared_without_object_cannot_commit(self):
        p, _ = self.new()
        p.prepare(self.frames[1])
        self.denied(p.commit, "MATERIALIZED_PAYLOAD_MISSING")

    def test_materialized_object_tamper_before_commit_denied(self):
        p, _ = self.new()
        prepared = p.prepare(self.frames[1])
        p.materialize()
        p.objects[prepared.frame_sha256] = self.frames[0]
        self.denied(p.commit, "MATERIALIZED_PAYLOAD_MISSING_OR_TAMPERED")

    def test_visible_without_commit_denied(self):
        p, _ = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        self.denied(p.publish_visible, "VISIBLE_REQUIRES_MATCHING_COMMIT")

    def test_visible_without_readback_denied(self):
        p, _ = self.new()
        pending = p.prepare(self.frames[1])
        p.materialize()
        p.commit()
        del p.objects[pending.frame_sha256]
        self.denied(p.publish_visible, "VISIBLE_REQUIRES_EXACT_PAYLOAD")

    def test_duplicate_prepare_denied(self):
        p, _ = self.new()
        p.prepare(self.frames[1])
        self.denied(lambda: p.prepare(self.frames[1]), "ONLY_ONE_PREPARED")

    def test_wrong_parent_prepare_denied(self):
        p, _ = self.new()
        self.denied(lambda: p.prepare(replace(self.frames[1], parent_digest="f" * 64)),
                    "PARENT_DIGEST")

    def test_wrong_generation_prepare_denied(self):
        p, _ = self.new()
        self.denied(lambda: p.prepare(self.frames[2]), "GENERATION_SKIP")

    def test_cannot_publish_without_prepared_candidate(self):
        p, _ = self.new()
        self.denied(p.publish_visible, "NO_ACTIVE_PREPARED")

    def test_uncommitted_crash_keeps_old_visible_head(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        p.simulated_crash()
        self.assertEqual(r.admit(p.observe())["generation"], 1)
        self.denied(p.publish_visible, "NO_ACTIVE_PREPARED")
        self.assertFalse(p.in_doubt)

    def test_uncommitted_crash_can_reprepare_review_only(self):
        p, _ = self.new()
        p.prepare(self.frames[1])
        p.simulated_crash()
        self.advance(p, self.frames[1])
        self.assertEqual(p.visible.generation, 2)

    def test_commit_crash_quarantines_and_does_not_promote(self):
        p, r = self.new()
        p.prepare(self.frames[1])
        p.materialize()
        p.commit()
        p.simulated_crash()
        self.assertTrue(p.in_doubt)
        self.assertEqual(r.admit(p.observe())["generation"], 1)
        self.denied(p.publish_visible, "NO_ACTIVE_PREPARED")
        self.denied(lambda: p.prepare(self.frames[1]), "UNRESOLVED_COMMITTED")

    def test_commit_without_pending_denied(self):
        p, _ = self.new()
        self.denied(p.commit, "NO_PREPARED")

    def test_crash_after_successful_publication_does_not_reset_head(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        p.simulated_crash()
        self.assertEqual(r.admit(p.observe())["generation"], 2)

    def test_forged_visible_without_complete_chain_denied(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        observed = p.observe()
        self.denied(lambda: r.admit(replace(observed, frames=(self.frames[1], self.frames[0]))),
                    "PINNED_GENESIS")

    def test_forked_chain_with_matching_visible_receipt_denied(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        observed = p.observe()
        forged = replace(self.frames[1], parent_digest="f" * 64)
        wrong_receipt = Committed(Prepared(2, forged.digest, "f" * 64,
                                            self.frames[0].scope_binding_sha256))
        view = Observed(Visible.from_commit(wrong_receipt),
                        (self.frames[0], forged),
                        (observed.commits[0], wrong_receipt))
        self.denied(lambda: r.admit(view), "VISIBLE_SOURCE_LINEAGE_INVALID")

    def test_resettable_session_floor_explicitly_not_external(self):
        p, r = self.new()
        self.advance(p, self.frames[1])
        r.admit(p.observe())
        reset = SyntheticReader(self.frames[0].digest, self.frames[0].scope_binding_sha256)
        stale = SyntheticPublisher(self.frames[0]).observe()
        self.assertEqual(reset.admit(stale)["generation"], 1)
        self.assertFalse(reset.admit(stale)["durable_cross_run_rollback_floor"])

    def test_run_lab_is_deterministic_and_no_go(self):
        one = run_lab()
        self.assertEqual(one, run_lab())
        self.assertEqual(one["schema"], SCHEMA)
        self.assertEqual(one["final_review_only_generation"], 4)
        self.assertFalse(one["real_google_drive_cas_or_bytes"])
        self.assertFalse(one["owner_release_or_trading"])


if __name__ == "__main__":
    unittest.main()
