"""Owner architecture ADR G01/G02 must never self-approve a PR proposal."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.m4_owner_architecture_preflight import (
    _DECISIONS, _FALSE, _OPTIONS, _TESTS, _TRUE_INVARIANTS,
    validate_owner_architecture_draft,
)

DRAFT = json.loads(Path(
    "docs/MST_M4_G01_G02_OWNER_DECISIONS_20261109.json"
).read_text(encoding="utf-8"))


class OwnerArchitectureProposalContracts(unittest.TestCase):
    def validate(self, change=None):
        data = deepcopy(DRAFT)
        if change is not None:
            change(data)
        return validate_owner_architecture_draft(data)

    def test_g01_g02_all_options_are_unselected(self):
        receipt = self.validate()
        self.assertEqual(receipt["owner_options_unselected"], 3)
        self.assertEqual(receipt["owner_decisions_open"], 8)
        self.assertEqual(receipt["independent_witness_tests_required"], 13)
        self.assertIn("BLOCKED", receipt["status"])
        self.assertTrue(receipt["source_main_pinned"])
        for key in ("g01_verified", "g02_verified", "new_cloud_services_authorized",
                    "production_cache_read_authorized",
                    "production_cache_write_authorized", "trading_authorized"):
            self.assertIs(receipt[key], False)

    def test_proposal_has_eight_owner_decisions_with_no_chosen_outcome(self):
        self.assertEqual(len(_DECISIONS), 8)
        self.assertEqual([d["id"] for d in DRAFT["owner_decisions"]], list(_DECISIONS))
        for d in DRAFT["owner_decisions"]:
            self.assertEqual(d["state"], "OPEN")
            self.assertIsNone(d["chosen"])
            self.assertIsNone(d["owner_evidence_uri"])

    def test_github_drive_stays_conditional_not_approved(self):
        option = DRAFT["options"][0]
        self.assertEqual(option["id"], "A_GITHUB_DRIVE_ONLY")
        self.assertEqual(option["status"], "CONDITIONAL_UNPROVEN")
        self.assertFalse(option["is_selected"])
        self.assertTrue(option["owner_approval_required"])

    def test_gcp_extension_is_explicitly_not_authorized(self):
        option = DRAFT["options"][1]
        self.assertEqual(option["id"], "B_CLOUD_KMS_FIRESTORE")
        self.assertEqual(option["status"], "REQUIRES_EXPLICIT_SCOPE_EXTENSION")
        self.assertFalse(option["is_selected"])
        self.assertFalse(self.validate()["new_cloud_services_authorized"])

    def test_actions_cache_as_trust_root_is_rejected(self):
        option = DRAFT["options"][2]
        self.assertEqual(option["status"], "REJECTED_UNSAFE")
        self.assertFalse(option["is_selected"])

    def test_source_lock_mismatch_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_V1_SOURCE_LOCK_CHANGED"):
            self.validate(lambda d: d["source_lock"].update(
                mst_main_commit="f" * 40,
            ))

    def test_changed_v1_module_count_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_V1_SOURCE_LOCK_CHANGED"):
            self.validate(lambda d: d["source_lock"].update(inherited_v1_modules=62))

    def test_self_approved_flags_denied(self):
        for key in _FALSE:
            with self.subTest(key=key), self.assertRaisesRegex(
                PermissionError, "UNAUTHORIZED_OWNER_GATE_SELF_APPROVAL"
            ):
                self.validate(lambda d, k=key: d.__setitem__(k, True))

    def test_missing_false_flags_denied(self):
        for key in _FALSE:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(lambda d, k=key: d.pop(k))

    def test_unknown_boolean_owner_approval_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_ARCHITECTURE"):
            self.validate(lambda d: d.update(owner_authorized=True))

    def test_schema_promotion_denied(self):
        with self.assertRaisesRegex(ValueError, "UNAPPROVED_OR_MODIFIED"):
            self.validate(lambda d: d.update(schema="mst.m4.production.v1"))

    def test_status_promotion_denied(self):
        with self.assertRaisesRegex(ValueError, "UNAPPROVED_OR_MODIFIED"):
            self.validate(lambda d: d.update(status="OWNER_APPROVED"))

    def test_operational_status_promotion_denied(self):
        with self.assertRaisesRegex(PermissionError, "UNAUTHORIZED_ARCHITECTURE_PROMOTION"):
            self.validate(lambda d: d.update(operational_status="PRODUCTION"))

    def test_wrong_repository_denied(self):
        with self.assertRaisesRegex(ValueError, "WRONG_ARCHITECTURE_REPOSITORY"):
            self.validate(lambda d: d.update(repository="ngluonghoa/swing-trading-1-8"))

    def test_changed_adr_ref_denied(self):
        with self.assertRaisesRegex(ValueError, "INVALID_OWNER_ADR_REFERENCE"):
            self.validate(lambda d: d.update(adr="docs/other.md"))

    def test_one_architecture_selected_denied(self):
        with self.assertRaisesRegex(PermissionError, "ARCHITECTURE_CHOSEN_WITHOUT_OWNER"):
            self.validate(lambda d: d["options"][0].update(is_selected=True))

    def test_out_of_scope_cloud_selected_denied(self):
        with self.assertRaisesRegex(PermissionError, "ARCHITECTURE_CHOSEN_WITHOUT_OWNER"):
            self.validate(lambda d: d["options"][1].update(is_selected=True))

    def test_unsafe_cache_root_selected_denied(self):
        with self.assertRaisesRegex(PermissionError, "ARCHITECTURE_CHOSEN_WITHOUT_OWNER"):
            self.validate(lambda d: d["options"][2].update(is_selected=True))

    def test_false_scope_expansion_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "ARCHITECTURE_OPTION_STATUS_OR_SCOPE_DRIFT"):
            self.validate(lambda d: d["options"][1].update(
                scope="EXISTING_GITHUB_DRIVE_ONLY",
            ))

    def test_rejected_option_status_rewritten_denied(self):
        with self.assertRaisesRegex(ValueError, "ARCHITECTURE_OPTION_STATUS_OR_SCOPE_DRIFT"):
            self.validate(lambda d: d["options"][2].update(status="APPROVED"))

    def test_architecture_option_order_mutated_denied(self):
        with self.assertRaisesRegex(ValueError, "ARCHITECTURE_OPTIONS_CHANGED"):
            self.validate(lambda d: d["options"].reverse())

    def test_architecture_option_dropped_denied(self):
        with self.assertRaisesRegex(ValueError, "THREE_OWNER_ARCHITECTURE_OPTIONS_REQUIRED"):
            self.validate(lambda d: d["options"].pop())

    def test_option_extra_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_ARCHITECTURE_OPTION_FIELDS"):
            self.validate(lambda d: d["options"][0].update(owner_authorized=True))

    def test_removed_architecture_risk_denied(self):
        with self.assertRaisesRegex(ValueError, "MISSING_UNRESOLVED_ARCHITECTURE_BLOCKERS"):
            self.validate(lambda d: d["options"][0].update(blocks=[]))

    def test_missing_option_description_denied(self):
        with self.assertRaisesRegex(ValueError, "MISSING_ARCHITECTURE_TRADEOFF_DESCRIPTION"):
            self.validate(lambda d: d["options"][0].update(description=""))

    def test_owner_decision_marked_closed_denied(self):
        with self.assertRaisesRegex(PermissionError, "OWNER_DECISION_CLOSED_WITHOUT_PROOF"):
            self.validate(lambda d: d["owner_decisions"][0].update(state="CLOSED"))

    def test_owner_decision_self_choice_denied(self):
        with self.assertRaisesRegex(PermissionError, "OWNER_DECISION_SELF_ATTESTATION"):
            self.validate(lambda d: d["owner_decisions"][0].update(chosen="A_GITHUB_DRIVE_ONLY"))

    def test_owner_decision_fake_proof_uri_denied(self):
        with self.assertRaisesRegex(PermissionError, "OWNER_DECISION_SELF_ATTESTATION"):
            self.validate(lambda d: d["owner_decisions"][0].update(owner_evidence_uri="https://example.com"))

    def test_owner_decision_adds_unreviewed_field_denied(self):
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_OWNER_DECISION_FIELDS"):
            self.validate(lambda d: d["owner_decisions"][0].update(authorized=True))

    def test_owner_decision_gate_swapped_denied(self):
        with self.assertRaisesRegex(ValueError, "OWNER_DECISION_TAXONOMY_DRIFT"):
            self.validate(lambda d: d["owner_decisions"][0].update(gate="SIGNED-G08"))

    def test_owner_decision_removed_denied(self):
        with self.assertRaisesRegex(ValueError, "EIGHT_OWNER_DECISIONS_REQUIRED"):
            self.validate(lambda d: d["owner_decisions"].pop())

    def test_acceptance_witness_test_deleted_denied(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_WITNESS_ACCEPTANCE_TESTS_REMOVED"):
            self.validate(lambda d: d["required_witness_tests"].pop())
        self.assertEqual(len(_TESTS), 13)

    def test_invariants_are_all_true_in_draft(self):
        self.assertEqual(set(DRAFT["security_invariants"]), set(_TRUE_INVARIANTS))
        self.assertTrue(all(DRAFT["security_invariants"].values()))

    def test_deny_false_security_invariant(self):
        for key in _TRUE_INVARIANTS:
            with self.subTest(key=key), self.assertRaisesRegex(
                ValueError, "MANDATORY_SECURITY_INVARIANT_FALSE"
            ):
                self.validate(lambda d, k=key: d["security_invariants"].update({k: False}))

    def test_invariant_dropped_denied(self):
        with self.assertRaisesRegex(ValueError, "SECURITY_INVARIANT_LIST_CHANGED"):
            self.validate(lambda d: d["security_invariants"].pop(
                "root_admin_reset_risk_must_be_reviewed"
            ))

    def test_untyped_owner_record_denied(self):
        for value in (None, [], "APPROVED", True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                validate_owner_architecture_draft(value)


if __name__ == "__main__":
    unittest.main()
