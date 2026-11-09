"""M4 review packet cannot convert GitHub readback into owner authority."""
from copy import deepcopy
import re
import unittest

from scripts.m4_reader_readiness_preflight import _BASE, _GATES, _DENIED, _REF
from scripts.m4_owner_gate_dossier import (
    _AUDIT_CLASS, _AUDIT_SCHEMA, _AUDIT_STATUS, _REQUIREMENTS,
    build_dossier,
)


def blocking_audit(*, witness=False, ruleset=False):
    return {
        "schema": _AUDIT_SCHEMA,
        "status": _AUDIT_STATUS,
        "evidence_class": _AUDIT_CLASS,
        "main_baseline_verified_for_this_read": True,
        "main_head_sha": _BASE,
        "witness_ref_name": _REF,
        "witness_ref_exists_for_this_read": witness,
        "witness_ref_head_sha_for_this_read": "a" * 40 if witness else None,
        "witness_ruleset_visible_for_this_token": ruleset,
        "witness_ruleset_scope_visible_for_this_token": ruleset,
        "witness_ruleset_metadata_matches_for_this_token": ruleset,
        "witness_bypass_list_visible_for_this_token": ruleset,
        "witness_actual_owner_authorization": False,
        "witness_active_protection_effective_end_to_end_verified": False,
        "owner_gates_still_open": list(_GATES),
        **_DENIED,
    }


class OwnerGateDossierUntrustedContract(unittest.TestCase):
    def setUp(self):
        self.audit = blocking_audit()
        self.head = "b" * 40

    def compile(self, changes=None, *, run=1234, head=None):
        value = deepcopy(self.audit)
        if changes:
            value.update(changes)
        return build_dossier(value, workflow_run_id=run,
                             candidate_head_sha=self.head if head is None else head)

    def test_all_eight_gates_frozen_open_and_review_only(self):
        d = self.compile()
        self.assertEqual(len(d["owner_decision_gates"]), 8)
        self.assertEqual(
            [g["gate"] for g in d["owner_decision_gates"]], list(_GATES),
        )
        self.assertEqual([r[0] for r in _REQUIREMENTS],
                         [f"G{i:02d}" for i in range(1, 9)])
        self.assertTrue(re.fullmatch(r"[a-f0-9]{64}",
                                      d["readiness_audit_sha256_untrusted"]))
        self.assertIn("PRODUCTION_BLOCKED", d["status"])
        self.assertFalse(d["owner_decisions_accepted"])
        self.assertFalse(d["production_cache_read_authorized"])
        self.assertFalse(d["production_cache_write_authorized"])
        self.assertFalse(d["trading_authorized"])
        for g in d["owner_decision_gates"]:
            self.assertEqual(g["status"], "OPEN_OWNER_EVIDENCE_REQUIRED")
            self.assertTrue(g["required_independent_evidence"])
            self.assertFalse(g["externally_attested"])
            self.assertFalse(g["release_authorized"])

    def test_stable_json_fingerprint_for_identical_readiness(self):
        a = self.compile()
        b = self.compile()
        self.assertEqual(a, b)

    def test_snapshot_changes_fingerprint_not_permissions(self):
        a = self.compile()
        b = build_dossier(blocking_audit(witness=True), workflow_run_id=1234,
                          candidate_head_sha=self.head)
        self.assertNotEqual(a["readiness_audit_sha256_untrusted"],
                            b["readiness_audit_sha256_untrusted"])
        self.assertFalse(b["production_cache_read_authorized"])
        self.assertFalse(b["owner_decisions_accepted"])

    def test_appearance_of_witness_and_ruleset_still_blocked(self):
        d = build_dossier(blocking_audit(witness=True, ruleset=True),
                          workflow_run_id=1234, candidate_head_sha=self.head)
        self.assertTrue(d["witness_ref_exists_in_readback"])
        self.assertTrue(d["witness_ruleset_visible_for_this_token"])
        self.assertFalse(d["independent_root_evidence_accepted"])
        self.assertFalse(d["external_protected_floor_evidence_accepted"])

    def test_production_ready_status_cannot_enter_review_packet(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AUDIT"):
            self.compile({"status": "PRODUCTION_AUTHORIZED"})

    def test_self_declared_owner_approval_denied(self):
        for key in (
            "witness_actual_owner_authorization",
            "owner_approval_verified",
            "protected_external_monotonic_floor_verified",
            "authenticated_two_principal_cas_verified",
            "global_signer_revocation_verified",
            "licensed_vendor_first_known_verified",
            "real_google_drive_bytes_verified",
            "cache_read_authorized", "cache_write_authorized",
            "trading_authorized",
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                PermissionError, "SELF_ATTESTED_PRODUCTION_RIGHT"
            ):
                self.compile({key: True})

    def test_missing_gate_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "OWNER_GATES_CHANGED"):
            self.compile({"owner_gates_still_open": list(_GATES)[:-1]})

    def test_reordered_gate_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "OWNER_GATES_CHANGED"):
            self.compile({"owner_gates_still_open": list(reversed(_GATES))})

    def test_untyped_gate_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "OWNER_GATES_CHANGED"):
            self.compile({"owner_gates_still_open": "ALL_OPEN"})

    def test_wrong_main_sha_denied(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AUDIT"):
            self.compile({"main_head_sha": "c" * 40})

    def test_false_main_verified_denied(self):
        with self.assertRaisesRegex(ValueError, "PINNED_MAIN_NOT_VERIFIED"):
            self.compile({"main_baseline_verified_for_this_read": False})

    def test_wrong_remote_witness_namespace_denied(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AUDIT"):
            self.compile({"witness_ref_name": "refs/heads/main"})

    def test_untrusted_evidence_class_denied(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AUDIT"):
            self.compile({"evidence_class": "OWNER_SIGNED_AUTHORIZED"})

    def test_untyped_run_ids_denied(self):
        for v in (0, -1, True, "1234", None):
            with self.subTest(v=v), self.assertRaises(ValueError):
                self.compile(run=v)

    def test_untyped_and_malformed_candidate_head_denied(self):
        for v in (True, "z" * 40, "a" * 39, "A" * 40):
            with self.subTest(v=v), self.assertRaises(ValueError):
                self.compile(head=v)
        # None bypasses the convenience method's default; call the API itself.
        with self.assertRaises(ValueError):
            build_dossier(self.audit, workflow_run_id=1234,
                          candidate_head_sha=None)

    def test_malformed_witness_presence_denied(self):
        for v in (None, 1, "yes"):
            with self.subTest(v=v), self.assertRaisesRegex(
                ValueError, "UNVERIFIABLE_GITHUB"
            ):
                self.compile({"witness_ref_exists_for_this_read": v})

    def test_malformed_witness_head_denied(self):
        for v in (None, True, "a" * 39, "A" * 40):
            with self.subTest(v=v), self.assertRaisesRegex(
                ValueError, "MISSING_OR_INVALID_WITNESS"
            ):
                self.compile({"witness_ref_exists_for_this_read": True,
                              "witness_ref_head_sha_for_this_read": v})

    def test_ref_absent_but_sha_present_denied(self):
        with self.assertRaisesRegex(ValueError, "UNEXPLAINED_WITNESS"):
            self.compile({"witness_ref_head_sha_for_this_read": "a" * 40})

    def test_ruleset_metadata_matches_without_scope_denied(self):
        with self.assertRaisesRegex(ValueError, "IMPOSSIBLE_RULESET"):
            self.compile({"witness_ruleset_metadata_matches_for_this_token": True})

    def test_ruleset_scope_only_does_not_grant_read_authority(self):
        d = self.compile({
            "witness_ruleset_visible_for_this_token": True,
            "witness_ruleset_scope_visible_for_this_token": True,
            "witness_ruleset_metadata_matches_for_this_token": True,
            "witness_bypass_list_visible_for_this_token": False,
        })
        self.assertFalse(d["production_cache_read_authorized"])
        self.assertFalse(d["owner_decisions_accepted"])

    def test_boolean_metadata_field_drift_denied(self):
        for field in (
            "witness_ruleset_visible_for_this_token",
            "witness_ruleset_scope_visible_for_this_token",
            "witness_ruleset_metadata_matches_for_this_token",
            "witness_bypass_list_visible_for_this_token",
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "UNVERIFIABLE_GITHUB_READBACK"
            ):
                self.compile({field: 1})

    def test_absent_owner_attestation_flag_is_not_false(self):
        value = deepcopy(self.audit)
        value.pop("independent_owner_signer_verified")
        with self.assertRaisesRegex(PermissionError, "SELF_ATTESTED_PRODUCTION_RIGHT"):
            build_dossier(value, workflow_run_id=3, candidate_head_sha=self.head)

    def test_absent_cas_evidence_flag_is_not_false(self):
        value = deepcopy(self.audit)
        value.pop("authenticated_two_principal_cas_verified")
        with self.assertRaisesRegex(PermissionError, "SELF_ATTESTED_PRODUCTION_RIGHT"):
            build_dossier(value, workflow_run_id=3, candidate_head_sha=self.head)

    def test_future_owner_approved_schema_needs_separate_protocol(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AUDIT"):
            self.compile({"schema": "mst.m4.production-authorized.v99"})

    def test_audit_list_is_copy_not_mutated(self):
        src = deepcopy(self.audit)
        self.compile()
        self.assertEqual(src, self.audit)

    def test_nonstrict_input_type_denied(self):
        for value in ([], "", None, 1, True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                build_dossier(value, workflow_run_id=3,
                              candidate_head_sha=self.head)


if __name__ == "__main__":
    unittest.main()
