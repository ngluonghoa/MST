"""A03 cross-contract crypto integrity ≠ SSI/DNSE/VCBS source authority."""
from dataclasses import replace
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_signed_supplier_boundary_lab as m
from scripts.m2_a03_revision_ledger_closure_lab import (
    claims_for, intake_untrusted_claims,
)
from scripts.m2_a03_revision_tombstone_hypothesis_lab import (
    PARTITION, UP1, UP2, TIMES,
)
from scripts.m4_signed_floor_fixture import (
    canonical, seed_floor, verify_signed_fixture,
)


class A03SignedSupplierBoundaryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=m.build()
        cls.cases={x["case"]:x for x in cls.r["cases"]}

    def case(self,name,group):
        self.assertIn(name,self.cases)
        self.assertEqual(self.cases[name]["group"],group)
        self.assertEqual(self.cases[name]["result"],
                         "PASS_CONDITIONAL_FIXTURE_NO_SOURCE_AUTHORITY")

    def test_01_exact_schema(self):
        self.assertEqual(self.r["schema"],m.SCHEMA)

    def test_02_exact_31_cases(self):
        self.assertEqual(self.r["case_count"],31)

    def test_03_no_duplicate_case_ids(self):
        self.assertEqual(len(self.cases),31)

    def test_04_synthetic_case_provenance_labeled(self):
        self.assertTrue(all(row["result"]==
            "PASS_CONDITIONAL_FIXTURE_NO_SOURCE_AUTHORITY"
            for row in self.r["cases"]))

    def test_05_case_fingerprint(self):
        canonical_cases=json.dumps(self.r["cases"],sort_keys=True,
            separators=(",",":"),ensure_ascii=True,allow_nan=False)
        self.assertEqual(self.r["case_fingerprint_sha256"],
            sha256(canonical_cases.encode()).hexdigest())

    def test_06_issuer_and_closed_head_not_authenticated(self):
        self.assertFalse(self.r["real_provider_issuer_independently_authenticated"])
        self.assertFalse(self.r["signed_provider_revision_head_completeness_proven"])

    def test_07_signer_root_not_attested(self):
        self.assertFalse(self.r["independent_signer_root_and_custody_proven"])

    def test_08_durable_floor_and_cas_unproven(self):
        self.assertFalse(self.r["durable_cross_run_floor_or_distributed_cas_proven"])

    def test_09_no_licence_cache_trading_permissions(self):
        self.assertFalse(self.r["legal_provider_market_data_and_drive_cache_authorized"])
        self.assertFalse(self.r["production_release_or_trading_authorized"])

    def test_10_existing_four_owner_gates_not_signed(self):
        self.assertEqual(self.r["owner_gate_ids"],list(m.REQUIRED_OWNER_PROOF_IDS))
        self.assertEqual(len(set(self.r["owner_gate_ids"])),4)
        self.assertEqual(self.r["owner_14_choices_signed"],0)

    def test_11_m4_private_evidence_crosswalk_six_types(self):
        self.assertEqual(self.r["existing_private_intake_requirements"],
                         ["E03","E08","E11","E12","E13","E14"])

    def test_12_zero_a02_a03_module_signoffs(self):
        self.assertEqual(self.r["a02_module_owner_signoff"],0)
        self.assertEqual(self.r["a03_v2_owner_signoff"],0)
        self.assertFalse(self.r["g01_g08_oa01_oa06_closed"])

    def test_13_ephemeral_ed25519_can_verify_bytes_only(self):
        self.case("VALID_EPHEMERAL_SIGNATURE_INTEGRITY_ONLY","positive")
        self.assertTrue(self.r["conditional_ed25519_fixture_integrity_tested"])

    def test_14_authentic_signature_not_vendor_licence(self):
        self.case("VALID_SIGNATURE_NEVER_APPROVES_SOURCE_RIGHTS","authority")

    def test_15_authentic_signature_not_drive_or_trading(self):
        self.case("VALID_SIGNATURE_NEVER_APPROVES_DRIVE_CACHE","authority")
        self.case("VALID_SIGNATURE_NEVER_APPROVES_PRODUCTION_TRADE","authority")

    def test_16_authentic_signature_not_independent_custody(self):
        self.case("VALID_SIGNATURE_NO_REAL_INDEPENDENT_CUSTODY","authority")

    def test_17_authentic_signature_not_durable_floor(self):
        self.case("VALID_SIGNATURE_NO_DURABLE_FLOOR","authority")

    def test_18_ledger_head_declarations_still_untrusted(self):
        self.case("SOURCE_CLAIM_STILL_UNTRUSTED","authority")

    def test_19_signed_wrong_source_and_partition_denied(self):
        self.case("SIGNED_REWRITTEN_PRICE_BASIS_PARTITION_BLOCKED","binding")
        self.case("SIGNED_DIFFERENT_PROVIDER_BLOCKED","binding")

    def test_20_signed_wrong_ledger_digest_denied(self):
        self.case("SIGNED_UNRELATED_LEDGER_DIGEST_BLOCKED","binding")

    def test_21_signed_wrong_asof_rejected(self):
        self.case("SIGNED_BACKDATED_SOURCE_ASOF_BLOCKED","clock")
        self.case("SIGNED_FUTURE_SOURCE_ASOF_BLOCKED","clock")

    def test_22_tamper_after_signing_denied(self):
        self.case("SIGNATURE_TAMPERED_LEDGER_ENVELOPE_BLOCKED","signature")

    def test_23_unmatched_key_or_signature_denied(self):
        self.case("UNPINNED_WRONG_PUBLIC_KEY_BLOCKED","signature")
        self.case("INVALID_SIGNATURE_BYTES_BLOCKED","signature")
        self.case("UNSIGNED_RECEIPT_BLOCKED","signature")

    def test_24_unreviewed_approval_field_denied(self):
        self.case("MALFORMED_RECEIPT_EXTRA_APPROVAL_FIELD_BLOCKED","signature")

    def test_25_rehashed_closure_no_matching_signature_denied(self):
        self.case("SOURCE_CLOSURE_REHASHED_AFTER_SIGNED_HEAD_BLOCKED","binding")

    def test_26_forged_rotation_parent_or_epoch_denied(self):
        self.case("SIGNER_EPOCH_CHANGED_WITHOUT_REPIN_BLOCKED","signature")
        self.case("SIGNED_PARENT_HEAD_WRONG_BLOCKED","rollback")
        self.case("SIGNED_GENERATION_JUMP_BLOCKED","rollback")

    def test_27_replaced_caller_anchor_still_not_real_provider_key(self):
        self.case("CALLER_REPLACED_SIGNER_ANCHOR_STILL_NOT_PROVIDER_AUTHORITY",
                  "spoofability")

    def test_28_two_signed_forks_can_both_validate_against_one_local_floor(self):
        self.case("TWO_SIGNED_FORKS_PASS_SAME_LOCAL_FLOOR","spoofability")
        self.case("TWO_SIGNED_FORKS_DO_NOT_PROVE_DISTRIBUTED_CAS","spoofability")

    def test_29_reset_floor_reaccepts_old_signed_receipt(self):
        self.case("RESET_CALLER_FLOOR_REACCEPTS_OLD_SIGNED_RECEIPT","spoofability")

    def test_30_rehashed_historical_source_can_be_resigned(self):
        self.case("FULLY_RESIGNED_TAMPER_PASSES_WITHOUT_TRUSTED_SOURCE_ROOT",
                  "spoofability")
        self.case("FULLY_RESIGNED_TAMPER_REMAINS_UNLICENSED_AND_NONTRADING",
                  "authority")

    def test_31_proof_requirements_are_not_approvals(self):
        self.case("FOUR_EXISTING_A03_OWNER_GATES_REMAIN_OPEN","owner")
        self.case("M4_PRIVATE_INTAKE_GATES_E03_E08_E11_E12_E13_E14_UNSATISFIED",
                  "owner")
        self.case("A02_AND_A03_MODULE_OWNER_SIGNOFF_REMAINS_ZERO","owner")
        self.case("NO_REAL_SIGNER_ROOT_OR_VENDOR_ENTITLEMENT_WAS_PROVISIONED",
                  "owner")

    def test_32_direct_independent_valid_signature_does_not_qualify_source(self):
        private,pub=m.fake_keypair()
        anchor=m.make_anchor(pub)
        floor=seed_floor(anchor,at="2026-11-09T07:00:00Z")
        rows=(UP1,UP2)
        closure=intake_untrusted_claims(PARTITION,"BAR1",rows,
            claims_for(rows,TIMES[2]),as_of_utc=TIMES[2])
        signed=m.make_signed_fixture(closure,anchor,floor)
        sig=private.sign(canonical(signed)).hex()
        receipt=m.verify_cross_contract(closure,signed,sig,anchor,floor)
        self.assertTrue(receipt.signed_fixture_integrity)
        self.assertFalse(receipt.trusted_provider_revision_head)
        self.assertFalse(receipt.production_release_or_trading_authorized)

    def test_33_direct_wrong_crypto_key_denied(self):
        private,pub=m.fake_keypair()
        _,foreign_pub=m.fake_keypair()
        anchor=m.make_anchor(pub)
        rows=(UP1,UP2)
        closure=intake_untrusted_claims(PARTITION,"BAR1",rows,
            claims_for(rows,TIMES[2]),as_of_utc=TIMES[2])
        floor=seed_floor(anchor,at="2026-11-09T07:00:00Z")
        signed=m.make_signed_fixture(closure,anchor,floor)
        with self.assertRaises(ValueError):
            m.verify_cross_contract(closure,signed,
                private.sign(canonical(signed)).hex(),
                m.make_anchor(foreign_pub),floor)

    def test_34_direct_signer_can_self_rehash_payload_without_source_truth(self):
        private,pub=m.fake_keypair()
        anchor=m.make_anchor(pub)
        floor=seed_floor(anchor,at="2026-11-09T07:00:00Z")
        original=(UP1,UP2)
        altered=(replace(UP1,payload_sha256="e"*64),UP2)
        original_closure=intake_untrusted_claims(PARTITION,"BAR1",original,
            claims_for(original,TIMES[2]),as_of_utc=TIMES[2])
        altered_closure=intake_untrusted_claims(PARTITION,"BAR1",altered,
            claims_for(altered,TIMES[2]),as_of_utc=TIMES[2])
        self.assertNotEqual(original_closure.ledger_digest,
                            altered_closure.ledger_digest)
        signed=m.make_signed_fixture(altered_closure,anchor,floor)
        result=m.verify_cross_contract(altered_closure,signed,
            private.sign(canonical(signed)).hex(),anchor,floor)
        self.assertTrue(result.signed_fixture_integrity)
        self.assertFalse(result.trusted_provider_revision_head)
        self.assertFalse(result.licensed_market_source_and_retention_verified)

    def test_35_direct_floor_reset_does_not_prove_global_rollback(self):
        private,pub=m.fake_keypair()
        anchor=m.make_anchor(pub)
        floor=seed_floor(anchor,at="2026-11-09T07:00:00Z")
        rows=(UP1,UP2)
        closure=intake_untrusted_claims(PARTITION,"BAR1",rows,
            claims_for(rows,TIMES[2]),as_of_utc=TIMES[2])
        signed=m.make_signed_fixture(closure,anchor,floor)
        sig=private.sign(canonical(signed)).hex()
        first=verify_signed_fixture(signed,sig,anchor,floor)
        replay=verify_signed_fixture(
            signed,sig,anchor,seed_floor(anchor,at="2026-11-09T07:00:00Z"))
        self.assertEqual(first["receipt_digest"],replay["receipt_digest"])
        self.assertFalse(replay["globally_durable_monotonic_floor_verified"])


if __name__ == "__main__":
    import unittest
    unittest.main()
