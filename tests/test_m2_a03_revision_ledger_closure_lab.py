"""A03 declared source/viewer ledger closure does NOT authenticate custody."""
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_revision_ledger_closure_lab as m
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    PARTITION, UP1, UP2, TOMB, TIMES,
)


class RevisionLedgerClosureTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=m.build()
        cls.cases={row["case"]:row for row in cls.report["cases"]}

    def case(self,name,group):
        self.assertIn(name,self.cases)
        self.assertEqual(self.cases[name]["group"],group)
        self.assertEqual(self.cases[name]["result"],"PASS_FIXTURE_NO_AUTHORITY")

    def test_01_schema_untrusted(self):
        self.assertEqual(self.report["schema"],m.SCHEMA)

    def test_02_exact_44_cases(self):
        self.assertEqual(self.report["case_count"],44)

    def test_03_no_duplicate_case_names(self):
        self.assertEqual(len(self.cases),44)

    def test_04_all_fixture_only(self):
        self.assertTrue(all(x["result"]=="PASS_FIXTURE_NO_AUTHORITY"
                            for x in self.report["cases"]))

    def test_05_report_hash_covers_cases_snapshots_owners(self):
        raw=json.dumps({
            "cases":self.report["cases"],
            "snapshots":self.report["snapshots"],
            "owners":tuple(self.report["new_unsigned_owner_gates"]),
        },sort_keys=True,separators=(",",":"),allow_nan=False)
        self.assertEqual(self.report["case_and_snapshot_sha256"],
                         sha256(raw.encode("ascii")).hexdigest())

    def test_06_five_historical_snapshots(self):
        self.assertEqual(len(self.report["snapshots"]),5)

    def test_07_monotone_locally_claimed_sequences(self):
        self.assertEqual([x["head_sequence"] for x in self.report["snapshots"]],
                         [1,1,2,3,3])

    def test_08_latest_head_tombstone_remains_unverified(self):
        self.assertEqual(self.report["snapshots"][-1]["head_revision_id"],"r3")
        self.assertEqual(self.report["snapshots"][-1]["candidate_status"],
                         "UNVERIFIED_TOMBSTONED")

    def test_09_each_snapshot_not_source_qualified(self):
        self.assertTrue(all(x["independently_qualified"] is False
                            for x in self.report["snapshots"]))

    def test_10_four_extra_owner_gates_unsigned(self):
        self.assertEqual(len(self.report["new_unsigned_owner_gates"]),4)
        self.assertEqual(len({x["id"] for x in
                             self.report["new_unsigned_owner_gates"]}),4)
        self.assertTrue(all(x["owner_signed"] is False for x in
                            self.report["new_unsigned_owner_gates"]))

    def test_11_a02_a03_owner_zero(self):
        self.assertEqual(self.report["owner_a02_signed"],0)
        self.assertEqual(self.report["owner_a03_signed"],0)

    def test_12_no_crypto_source_custody_rights_or_trade(self):
        for key in (
            "provider_signature_cryptographically_verified",
            "independent_trust_root_or_custody_verified",
            "cross_run_nonresettable_floor_verified",
            "source_closed_head_or_complete_history_verified",
            "real_provider_entitlement_or_google_drive_cache_authorized",
            "g01_g08_oa01_oa06_closed",
            "production_release_or_trading_authorized",
        ):
            with self.subTest(key=key):
                self.assertIs(self.report[key],False)

    def test_13_two_self_claim_failures_explicitly_demonstrated(self):
        self.assertIs(self.report[
            "fresh_run_self_claim_rollback_vulnerability_demonstrated"],True)
        self.assertIs(self.report[
            "colluding_self_claim_rehash_vulnerability_demonstrated"],True)

    def test_14_honest_single_root_consistency_no_rights(self):
        self.case("SINGLE_ROOT_NO_AUTHORITY","positive")

    def test_15_next_asof_same_head_fixture(self):
        self.case("UNCHANGED_HEAD_NEXT_ASOF_ALLOWED_STRUCTURALLY","positive")

    def test_16_new_revision_extends_prefix_fixture(self):
        self.case("NEW_REVISION_EXTENDS_PREVIOUS_PREFIX","positive")

    def test_17_tombstone_unverified(self):
        self.case("TOMBSTONE_STAYS_UNVERIFIED","positive")

    def test_18_same_head_no_repaint(self):
        self.case("NO_REPAINT_ON_SAME_HEAD","positive")

    def test_19_distinct_strings_not_independent_principals(self):
        self.case("EXPLICIT_TWO_CLAIMS_NOT_TRUE_INDEPENDENCE","authority")

    def test_20_invalid_role_or_single_claim_denied(self):
        self.case("ONLY_ONE_CLAIM_DENIED","claims")
        self.case("SWAPPED_SOURCE_VIEWER_ROLES_DENIED","claims")

    def test_21_same_actor_or_domain_disallowed(self):
        self.case("SAME_ACTOR_STRING_DENIED","claims")
        self.case("SAME_CUSTODY_DOMAIN_STRING_DENIED","claims")
        self.case("ACTOR_CUSTODY_AMBIGUITY_DENIED","claims")

    def test_22_cross_provider_and_basis_denied(self):
        self.case("CLAIMED_PROVIDER_DIFFERENT_DENIED","scope")
        self.case("CLAIMED_PRICE_BASIS_CHANGED_DENIED","scope")

    def test_23_cross_event_scope_denied(self):
        self.case("CLAIMED_DIFFERENT_EVENT_DENIED","scope")

    def test_24_asof_and_custody_clock_mismatch(self):
        self.case("CLAIMED_CLOSURE_BEFORE_SNAPSHOT_DENIED","clock")
        self.case("CLAIMED_OBSERVED_BEFORE_SNAPSHOT_DENIED","clock")
        self.case("CLAIMED_SNAPSHOT_ASOF_MISMATCH_DENIED","clock")

    def test_25_low_high_or_inconsistent_head_denied(self):
        self.case("CLAIMED_HEAD_SEQUENCE_LOWER_DENIED","head")
        self.case("CLAIMED_HEAD_SEQUENCE_GREATER_DENIED","head")
        self.case("CLAIMED_HEAD_REVISION_MISMATCH_DENIED","head")

    def test_26_both_claimed_digests_must_match(self):
        self.case("CLAIMED_VIEWER_DIGEST_MISMATCH_DENIED","head")
        self.case("CLAIMED_SOURCE_DIGEST_MISMATCH_DENIED","head")

    def test_27_bad_hex_and_boolean_sequence_denied(self):
        self.case("BAD_NONHEX_CLAIMED_DIGEST_DENIED","validation")
        self.case("BOOLEAN_HEAD_SEQUENCE_DENIED","validation")

    def test_28_no_empty_closure(self):
        self.case("EMPTY_CLOSED_SNAPSHOT_DENIED","head")

    def test_29_untyped_rows_denied(self):
        self.case("LIST_REVISION_ROWS_DENIED","validation")
        self.case("UNTYPED_REVISION_ROW_DENIED","validation")

    def test_30_no_future_row_for_historical_asof(self):
        self.case("FUTURE_ROW_IN_HISTORICAL_CLOSURE_DENIED","clock")

    def test_31_missing_root_middle_denied(self):
        self.case("MISSING_ROOT_WITH_HIGH_HEAD_DENIED","head")
        self.case("MISSING_MIDDLE_REVISION_DENIED","head")

    def test_32_duplicate_source_rows_denied(self):
        self.case("DUPLICATE_REVISION_HEAD_DENIED","head")

    def test_33_prior_head_no_downgrade(self):
        self.case("LOCAL_HIGH_WATERMARK_ROLLBACK_DENIED","rollback")

    def test_34_no_prior_snapshot clock rewind(self):
        self.case("SNAPSHOT_CLOCK_REWIND_DENIED","rollback")

    def test_35_prior_prefix rewrite denied(self):
        self.case("TAMPERED_HISTORICAL_PREFIX_DENIED","rollback")

    def test_36_without_prior_old_claim_is_still_accepted_not_trusted(self):
        self.case("FRESH_RUN_CAN_ACCEPT_ROLLED_BACK_SELF_CLAIM","authority")
        old=(UP1,)
        result=m.intake_untrusted_claims(PARTITION,"BAR1",old,
            m.claims_for(old,TIMES[4]),as_of_utc=TIMES[4])
        self.assertEqual(result.head_sequence,1)
        self.assertFalse(result.trusted_nonresettable_floor)

    def test_37_without_prior_rehashed_prefix_is_consistent_not_authentic(self):
        self.case("TWO_SELF_CLAIMS_CAN_AGREE_ON_REHASHED_TAMPER","authority")
        old=(UP1,UP2)
        bad=(replace(UP1,payload_sha256="9"*64),UP2)
        self.assertNotEqual(m.digest(old),m.digest(bad))
        result=m.intake_untrusted_claims(PARTITION,"BAR1",bad,
            m.claims_for(bad,TIMES[3]),as_of_utc=TIMES[3])
        self.assertFalse(result.verified_provider_signature)

    def test_38_different_prior_scope_not_safe(self):
        self.case("CROSS_EVENT_PRIOR_HEAD_DENIED","scope")
        self.case("CROSS_PROVIDER_PRIOR_HEAD_DENIED","scope")

    def test_39_never_promote_claim_to_signal(self):
        self.case("REPORT_CANDIDATE_IS_NOT_TRADING_SIGNAL","authority")
        self.case("NEVER_GRANTS_MARKET_RIGHTS_CACHE_OR_TRADE","authority")

    def test_40_claims_not_cryptographic_attestations(self):
        self.case("CLAIM_ROLE_DIFFERENCE_NOT_CRYPTOGRAPHIC_SIGNATURE","owner")
        self.case("FRESH_RUN_CANNOT_PROVE_PRIOR_DURABLE_FLOOR","owner")

    def test_41_owner_gate_ids_and_permission_are_stable(self):
        self.case("ALL_FOUR_NEW_OWNER_GATE_ROWS_UNSIGNED","owner")
        self.case("TRADING_CANNOT_BE_INFERRED_FROM_UNTRUSTED_CLAIMS","authority")

    def test_42_direct_malformed_evidence_rejected(self):
        good=(UP1,)
        with self.assertRaises(ValueError):
            m.claims_for(good,TIMES[0],viewer_changes={
                "ledger_digest":"ZZ"*32})

    def test_43_direct_future_known_snapshots_fail_closed(self):
        rows=(UP1,UP2)
        with self.assertRaises(ValueError):
            m.intake_untrusted_claims(PARTITION,"BAR1",rows,
                m.claims_for(rows,TIMES[0]),as_of_utc=TIMES[0])

    def test_44_exact_digest_independent_and_content_sensitive(self):
        old=(UP1,UP2)
        tampered=(replace(UP1,payload_sha256="9"*64),UP2)
        self.assertNotEqual(m.digest(old),m.digest(tampered))
        self.assertEqual(m.digest(old),m.digest(tuple(old)))


if __name__=="__main__":
    import unittest
    unittest.main()
