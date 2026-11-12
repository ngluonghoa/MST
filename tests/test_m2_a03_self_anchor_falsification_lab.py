"""A03: self-rebasing reviewed public text/hash does not prove independent roots."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest import TestCase

from scripts import m2_a03_self_anchor_falsification_lab as lab
from scripts import m2_a03_supplier_owner_proof_packet as m


class SelfAnchorFalsificationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(m.PACKET_PATH.read_text(encoding="utf-8"))
        cls.intake = json.loads(m.M4_PATH.read_text(encoding="utf-8"))
        cls.report = lab.build(cls.packet, cls.intake)

    def test_01_schema(self):
        self.assertEqual(self.report["schema"], lab.SCHEMA)

    def test_02_exact_three_counterexamples(self):
        self.assertEqual(self.report["case_count"], 3)

    def test_03_each_expected_case_id(self):
        self.assertEqual([r["case"] for r in self.report["cases"]],
                         list(lab.CASES))

    def test_04_original_validator_blocks_unilateral_mutation(self):
        self.assertTrue(all(r["unmodified_validator_rejects"]
                            for r in self.report["cases"]))

    def test_05_joint_rebase_passes_local_validator(self):
        self.assertTrue(all(r["co_modified_public_validator_accepts"]
                            for r in self.report["cases"]))

    def test_06_original_coarse_index_still_matches(self):
        self.assertTrue(all(r["legacy_coarse_index_still_matches"]
                            for r in self.report["cases"]))

    def test_07_new_semantic_fingerprint_changes(self):
        self.assertTrue(all(r["recomputed_semantic_index_differs"]
                            for r in self.report["cases"]))

    def test_08_every_rebased_case_denies_external_authority(self):
        self.assertTrue(all(not r["independent_root_or_owner_authority_proven"]
                            for r in self.report["cases"]))

    def test_09_all_cases_refuse_production(self):
        self.assertTrue(all(not r["production_or_trading_authorized"]
                            for r in self.report["cases"]))

    def test_10_digest_of_cases_is_only_local_consistency(self):
        s = json.dumps(self.report["cases"], sort_keys=True,
                       separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        self.assertEqual(self.report["case_only_digest_sha256"],
                         sha256(s.encode()).hexdigest())

    def test_11_existing_semantic_digest_unchanged(self):
        orig = m.validate_packet(self.packet, self.intake)
        self.assertEqual(self.report["reviewer_reference_index_sha256"],
                         orig["reviewed_semantic_contract_sha256"])

    def test_12_no_modification_leaks_from_patch_dict(self):
        self.assertEqual(
            m.validate_packet(self.packet, self.intake)["status"],
            "PUBLIC_REQUIREMENTS_PREFLIGHT_PASS_ALL_REAL_EVIDENCE_ABSENT_OWNER_NO_GO")

    def test_13_external_attestation_is_not_claimed(self):
        self.assertFalse(self.report["independent_protected_commit_or_signer_attestation"])
        self.assertFalse(self.report["real_independent_actor_control_proven"])

    def test_14_real_provider_entitlement_absent(self):
        self.assertFalse(self.report["provider_entitlement_or_issuer_proven"])
        self.assertFalse(self.report["licensed_drive_market_cache_authorized"])

    def test_15_no_owner_dispositions_implicitly_added(self):
        self.assertEqual(self.report["owner_gates_approved"], 0)
        self.assertEqual(self.report["a02_63_owner_signed"], 0)
        self.assertEqual(self.report["a03_v2_8_owner_signed"], 0)

    def test_16_no_trading(self):
        self.assertFalse(self.report["trading_authorized"])
        self.assertFalse(self.report["public_github_repo_review_required_proven"])
