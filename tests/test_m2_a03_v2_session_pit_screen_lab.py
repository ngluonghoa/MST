"""MST A03 V2 session/PIT screening untrusted fixture contracts only."""
from dataclasses import replace
from datetime import timedelta
from unittest import TestCase

from scripts import m2_a03_v2_session_pit_screen_lab as m
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    FixtureRevision, RevisionKind,
)


class V2SyntheticSessionPitScreenTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope,cls.slot,cls.rows,cls.late,cls.wrong=m.fixtures()
        cls.report=m.build()

    def decision(self,rows=None,slot=None,at=None,scope=None):
        return m.screen(scope if scope is not None else self.scope,
            slot if slot is not None else self.slot,
            rows if rows is not None else self.rows,
            as_of_utc=self.late if at is None else at)

    def test_01_sixteen_actual_original_and_screen_assertions(self):
        self.assertEqual(self.report["assertion_count"],16)

    def test_02_r1_until_late_first_known(self):
        self.assertEqual(self.decision(at=self.late-timedelta(microseconds=1))["candidate_revision_id"],"r1")

    def test_03_r2_at_exact_first_known(self):
        self.assertEqual(self.decision()["candidate_revision_id"],"r2")

    def test_04_no_future_revision_in_early_view(self):
        self.assertEqual(self.decision(at=m.instant(10))["visible_revision_count"],1)

    def test_05_closed_candle_unavailable_before_first_known(self):
        self.assertEqual(self.decision(at=m.instant(0))["candidate_revision_id"],None)

    def test_06_late_correction_past_session_end_structurally_allowed(self):
        self.assertGreater(self.late,self.slot.ends_at_utc)

    def test_07_v1_full_policy_binding_preserved(self):
        self.assertEqual(self.decision()["legacy_full_policy_binding_digest"],
                         self.scope.binding_sha256)

    def test_08_partition_exact_match(self):
        self.assertEqual(self.decision()["candidate_partition_digest"],self.scope.candidate.digest)

    def test_09_wrong_partition_slot_rejected(self):
        s=replace(self.slot,partition=replace(self.scope.candidate,price_basis="ADJUSTED"))
        with self.assertRaisesRegex(ValueError,"PARTITION_GRID_SCOPE"):
            self.decision(slot=s)

    def test_10_unknown_session_grid_cannot_self_prove_calendar(self):
        with self.assertRaises(PermissionError):
            replace(self.slot,independently_calendar_verified=True)

    def test_11_cross_session_start_rejected(self):
        from swing_trading.incremental_cache import FixtureBar
        b=self.wrong
        r=FixtureRevision(m.partition_from_scope(self.scope),"B0","b1",1,
            RevisionKind.UPSERT,b.start_utc,b.first_known_utc,
            payload_sha256=b.normalized_digest)
        item=m.UntrustedVersionedBar(r,replace(b,revision="b1"),self.scope.candidate)
        with self.assertRaisesRegex(ValueError,"SESSION_MEMBERSHIP_REJECTED"):
            self.decision(rows=(item,))

    def test_12_wrong_revision_digest_rejected(self):
        with self.assertRaisesRegex(ValueError,"BINDING_MISMATCH"):
            replace(self.rows[0],revision=replace(
                self.rows[0].revision,payload_sha256="f"*64))

    def test_13_wrong_revision_first_known_rejected(self):
        with self.assertRaisesRegex(ValueError,"BINDING_MISMATCH"):
            replace(self.rows[1],revision=replace(
                self.rows[1].revision,first_known_utc=self.late+timedelta(minutes=1)))

    def test_14_wrong_revision_identifier_rejected(self):
        with self.assertRaisesRegex(ValueError,"BINDING_MISMATCH"):
            replace(self.rows[1],revision=replace(
                self.rows[1].revision,revision_id="not-r2"))

    def test_15_missing_root_denied(self):
        with self.assertRaisesRegex(ValueError,"REVISION_PREFIX"):
            self.decision(rows=(self.rows[1],))

    def test_16_reversed_input_not_accepted(self):
        with self.assertRaisesRegex(ValueError,"REVISION_PREFIX"):
            self.decision(rows=self.rows[::-1])

    def test_17_no_retained_history_denied(self):
        with self.assertRaisesRegex(ValueError,"RETAINED_IMMUTABLE"):
            self.decision(rows=())

    def test_18_list_instead_of_immutable_tuple_denied(self):
        with self.assertRaisesRegex(ValueError,"RETAINED_IMMUTABLE"):
            self.decision(rows=list(self.rows))

    def test_19_untyped_scope_denied(self):
        with self.assertRaises(TypeError):
            self.decision(scope="fixture-caller-not-v2")

    def test_20_naive_asof_rejected(self):
        with self.assertRaisesRegex(ValueError,"EXPLICIT_EXACT_UTC"):
            self.decision(at=self.late.replace(tzinfo=None))

    def test_21_future_revision_metadata_still_not_source_verified(self):
        self.assertFalse(self.decision(at=self.late)["source_first_known_issuer_authenticated"])

    def test_22_no_official_exchange_calendar(self):
        self.assertFalse(self.decision()["external_exchange_calendar_authenticated"])

    def test_23_no_legal_market_cache(self):
        self.assertFalse(self.decision()["licensed_historical_data_authorized"])

    def test_24_no_real_drive_adapter(self):
        self.assertFalse(self.decision()["real_google_drive_cache_implemented"])

    def test_25_no_external_cas(self):
        self.assertFalse(self.decision()["external_floor_or_cas_verified"])

    def test_26_no_v1_v2_runtime_source_modification(self):
        self.assertFalse(self.report["existing_v1_or_v2_module_modified"])

    def test_27_no_owner_approvals(self):
        for k in ("owner_a02_63_approved","owner_a03_v2_8_approved",
                  "owner_a03_14_choices_approved"):
            self.assertFalse(self.decision()[k])

    def test_28_no_trade_or_release(self):
        self.assertFalse(self.decision()["trading_authorized"])
        self.assertFalse(self.decision()["production_release_authorized"])

    def test_29_screen_is_untrusted_even_when_r2_selected(self):
        self.assertEqual(self.decision()["source_truth_status"],
                         "UNVERIFIED_UNTRUSTED_FIXTURE_CANDIDATE_ONLY")

    def test_30_duplicate_sequence_denied(self):
        second=replace(self.rows[1],revision=replace(
            self.rows[1].revision,sequence=1,supersedes_revision_id=None))
        with self.assertRaisesRegex(ValueError,"REVISION_PREFIX"):
            self.decision(rows=(self.rows[0],second))

    def test_31_wrong_revision_parent_denied(self):
        second=replace(self.rows[1],revision=replace(
            self.rows[1].revision,supersedes_revision_id="wrong"))
        with self.assertRaisesRegex(ValueError,"UNPROVEN_OR_WRONG_PREDECESSOR"):
            self.decision(rows=(self.rows[0],second))

    def test_32_regressed_first_known_denied(self):
        b=replace(self.rows[1].bar,first_known_utc=self.rows[0].bar.first_known_utc)
        r=replace(self.rows[1].revision,first_known_utc=b.first_known_utc)
        item=m.UntrustedVersionedBar(replace(r,payload_sha256=b.normalized_digest),b,self.scope.candidate)
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS_OR_REGRESSED_REVISION"):
            self.decision(rows=(self.rows[0],item))

    def test_33_report_checksum_is_not_signer(self):
        self.assertEqual(len(self.report["synthetic_sha256"]),64)
        self.assertFalse(self.report["provider_session_membership_authenticated"])

    def test_34_deterministic_fixtures(self):
        self.assertEqual(self.report["synthetic_sha256"],m.build()["synthetic_sha256"])
