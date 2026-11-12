"""A03 private proof acceptance: requirements pass; self-declared authority FAILS."""
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase

from scripts import m2_a03_supplier_owner_proof_packet as m


class SupplierProofPacketTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(m.PACKET_PATH.read_text(encoding="utf-8"))
        cls.m4 = json.loads(m.M4_PATH.read_text(encoding="utf-8"))
        cls.result = m.validate_packet(cls.packet, cls.m4)

    def with_change(self, change, error=(ValueError, PermissionError, TypeError)):
        packet=deepcopy(self.packet)
        change(packet)
        with self.assertRaises(error):
            m.validate_packet(packet,self.m4)

    def test_01_schema_and_source_pins(self):
        self.assertEqual(self.result["schema"],m.SCHEMA)
        self.assertEqual(self.packet["source_pin"],m.SOURCE)
        self.assertEqual(self.packet["protected_main_pin"],m.MAIN)

    def test_02_exact_four_existing_owner_gates(self):
        self.assertEqual([x["gate"] for x in self.packet["requirements"]],list(m.CROSSWALK))
        self.assertEqual(self.result["owner_gate_count"],4)

    def test_03_twelve_concrete_acceptance_checks(self):
        self.assertEqual(self.result["acceptance_check_count"],12)

    def test_04_six_existing_m4_proof_requirements(self):
        self.assertEqual(self.result["m4_existing_requirement_ids"],
                         ["E03","E08","E11","E12","E13","E14"])

    def test_05_all_private_m4_proofs_still_not_received(self):
        for item in self.m4["evidence_requirements"]:
            self.assertEqual(item["state"],"NOT_RECEIVED")
            self.assertFalse(item["independently_verified"])

    def test_06_owner_choices_and_modules_not_approved(self):
        self.assertEqual(self.result["a03_owner_choices_approved"],0)
        self.assertEqual(self.result["a02_original_module_owner_approved"],0)
        self.assertEqual(self.result["a03_v2_owner_approved"],0)

    def test_07_all_authority_fields_false(self):
        for key in ("externally_authenticated_supplier","independently_proven_custody",
                    "nonresettable_floor_and_real_cas","licensed_google_drive_cache",
                    "real_source_qualified_signal","production_release","trading"):
            self.assertIs(self.result[key],False,key)

    def test_08_sixteen_untrusted_scenarios(self):
        self.assertEqual(self.result["untrusted_negative_case_count"],16)
        self.assertEqual(self.result["negative_case_ids"],list(m.SCENARIOS))

    def test_09_all_self_declarations_are_non_authorizing(self):
        for value in (False,True):
            claim=dict.fromkeys((
                "claims_vendor_issuer_authentic","claims_separate_custody",
                "claims_durable_floor","claims_licensed_drive_cache",
                "claims_owner_approved"),value)
            result=m.evaluate_untrusted_claim(claim)
            self.assertFalse(result["provider_verified"])
            self.assertFalse(result["owner_approved"])
            self.assertFalse(result["production_release"])
            self.assertFalse(result["trading"])

    def test_10_malicious_approval_field_in_claim_is_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_untrusted_claim({"claims_owner_approved":True,"secret_proof":"none"})

    def test_11_wrong_claim_value_type_rejected(self):
        claim=dict.fromkeys(("claims_vendor_issuer_authentic","claims_separate_custody",
            "claims_durable_floor","claims_licensed_drive_cache","claims_owner_approved"),True)
        claim["claims_owner_approved"]=1
        with self.assertRaises(TypeError):
            m.evaluate_untrusted_claim(claim)

    def test_12_external_authority_bit_cannot_be_self_set(self):
        self.with_change(lambda x:x["admissions"].__setitem__(
            "provider_issued_root_authenticated",True))

    def test_13_licensing_bit_cannot_be_self_set(self):
        self.with_change(lambda x:x["admissions"].__setitem__(
            "licensed_market_data_and_drive_retention_authorized",True))

    def test_14_trading_bit_cannot_be_self_set(self):
        self.with_change(lambda x:x["admissions"].__setitem__("trading_authorized",True))

    def test_15_owner_approval_false_cannot_change(self):
        self.with_change(lambda x:x["requirements"][0].__setitem__("owner_approved",True))

    def test_16_provider_evidence_not_received_cannot_flip(self):
        self.with_change(lambda x:x["requirements"][0].__setitem__("proof_state","VERIFIED"))

    def test_17_crosswalk_identity_lock(self):
        self.with_change(lambda x:x["requirements"][1].__setitem__(
            "existing_m4_requirement_ids",["E03","E13"]))

    def test_18_missing_acceptance_check_denied(self):
        self.with_change(lambda x:x["requirements"][2]["acceptance_checks"].pop())

    def test_19_secret_or_url_in_acceptance_check_denied(self):
        self.with_change(lambda x:x["requirements"][3]["acceptance_checks"].__setitem__(
            0,"A supposedly independent proof using https://external.invalid/secret as a publicly embedded private evidence URL"))

    def test_20_missing_admission_flag_denied(self):
        self.with_change(lambda x:x["admissions"].pop("production_release_authorized"))

    def test_21_rogue_scenario_promotion_denied(self):
        self.with_change(lambda x:x["untrusted_claim_scenarios"][0].__setitem__(
            "expected","PROMOTE_APPROVED"))

    def test_22_unreviewed_extra_owner_gate_denied(self):
        self.with_change(lambda x:x["requirements"].append(deepcopy(x["requirements"][0])))

    def test_23_third_cloud_not_allowed(self):
        self.with_change(lambda x:x.__setitem__("architecture","GITHUB_DRIVE_THIRD_CLOUD"))

    def test_24_m4_old_requirements_cannot_claim_received(self):
        changed=deepcopy(self.m4)
        next(x for x in changed["evidence_requirements"] if x["id"]=="E11")["state"]="RECEIVED"
        with self.assertRaises(PermissionError):
            m.validate_packet(self.packet,changed)

    def test_25_owner_count_not_overrideable(self):
        self.with_change(lambda x:x.__setitem__("owner_choices_approved",1))

    def test_26_public_data_handling_cannot_be_weakened(self):
        self.with_change(lambda x:x["handling"].__setitem__(
            "no_private_principal_or_key_or_evidence_url",False))

    def test_27_approved_texts_are_exact_reviewed_contract(self):
        self.assertEqual({r["gate"]: r["acceptance_checks"]
                          for r in self.packet["requirements"]},
                         m.REVIEWED_ACCEPTANCE_CHECKS)

    def test_28_exact_16_risk_gate_reason_pairs(self):
        self.assertEqual(
            {r["id"]: [r["gate"], r["missing_independent_proof"]]
             for r in self.packet["untrusted_claim_scenarios"]},
            m.REVIEWED_SCENARIO_GATE_REASON)

    def test_29_existing_m4_kind_contract(self):
        evidence={x["id"]:x["kind"] for x in self.m4["evidence_requirements"]}
        self.assertEqual({k:evidence[k] for k in m.REVIEWED_M4_EVIDENCE_KINDS},
                         m.REVIEWED_M4_EVIDENCE_KINDS)

    def test_30_no_semantically_empty_acceptance_replacement(self):
        self.with_change(lambda p:p["requirements"][0]["acceptance_checks"].__setitem__(
            0, "This long filler appears adequate for a naive length-based check but it removes the whole independent supplier enrollment requirement."))

    def test_31_genuine_gate_semantic_change_requires_explicit_review(self):
        self.with_change(lambda p:p["requirements"][2]["acceptance_checks"].__setitem__(
            1, p["requirements"][2]["acceptance_checks"][1].replace(
                "exactly one server-serialized compare-and-swap winner",
                "two independent winners accepted")))

    def test_32_acceptance_check_order_cannot_silently_change(self):
        def mutate(p):
            a=p["requirements"][1]["acceptance_checks"]
            a[0],a[1]=a[1],a[0]
        self.with_change(mutate)

    def test_33_unknown_risk_cannot_be_mapped_to_other_gate(self):
        self.with_change(lambda p:p["untrusted_claim_scenarios"][1].__setitem__(
            "gate","A03-OWNER-DURABLE-FLOOR-13"))

    def test_34_valid_gate_but_wrong_risk_reason_denied(self):
        self.with_change(lambda p:p["untrusted_claim_scenarios"][4].__setitem__(
            "missing_independent_proof",
            "A structurally long and plausible but different explanation is substituted for the reviewed reason."))

    def test_35_all_six_m4_evidence_categories_cannot_be_relabelled(self):
        for evidence_id in m.REVIEWED_M4_EVIDENCE_KINDS:
            intake=deepcopy(self.m4)
            next(x for x in intake["evidence_requirements"]
                 if x["id"]==evidence_id)["kind"]="FAKE_OTHER_KIND"
            with self.subTest(evidence=evidence_id),self.assertRaises(PermissionError):
                m.validate_packet(self.packet,intake)

    def test_36_reviewed_contract_sha256_receipt_present(self):
        self.assertEqual(len(self.result["reviewed_semantic_contract_sha256"]),64)
        self.assertNotEqual(self.result["public_requirement_index_sha256"],
                            self.result["reviewed_semantic_contract_sha256"])
