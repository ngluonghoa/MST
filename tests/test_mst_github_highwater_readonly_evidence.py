"""§201 synthetic signed-CLAIM read-only GitHub custody regression tests.

All REST observations, Git bytes, signing keys and external pins are FAKE.
No GitHub highwater object/ref is fetched, written, locked or released.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from scripts.mst_github_highwater_readonly_evidence import (
    CLAIM_BODY_SCHEMA, CLAIM_SCHEMA, OBJECT_OBS_SCHEMA,
    REF_OBS_SCHEMA, ROTATION_BODY_SCHEMA, ROTATION_SCHEMA,
    GitReadEvidenceDenied, _canonical, _digest,
    review_dual_signed_owner_key_rotation_candidate,
    verify_signed_readonly_git_evidence_claim,
)
from scripts.mst_github_highwater_commit_custody import (
    verify_supplied_highwater_git_objects,
)
from test_mst_github_highwater_commit_custody import sample

FAKE_OWNER_ID = "FAKE_UNTRUSTED_OWNER_SIGNER_2026"
FAKE_NEXT_OWNER_ID = "FAKE_UNTRUSTED_NEXT_OWNER_2026"
OWNER_PRIVATE = Ed25519PrivateKey.from_private_bytes(bytes(range(129, 161)))
NEXT_PRIVATE = Ed25519PrivateKey.from_private_bytes(bytes(range(161, 193)))
OWNER_PUBLIC = OWNER_PRIVATE.public_key().public_bytes(
    Encoding.Raw, PublicFormat.Raw,
)
NEXT_PUBLIC = NEXT_PRIVATE.public_key().public_bytes(
    Encoding.Raw, PublicFormat.Raw,
)


def sign(private, body):
    return base64.b64encode(private.sign(_canonical(body, limit=4096))).decode()


def fake_signed_claim(*, provider="DNSE", tf="D1"):
    custody_inputs = sample(provider=provider, tf=tf)
    p = custody_inputs["proposal"]
    previous_ref = p["expected_parent_sha"]
    ref = {
        "schema": REF_OBS_SCHEMA,
        "repository": p["repository"],
        "ref": p["ref"],
        "sha": previous_ref,
        "host": "api.github.com",
        "method": "GET",
    }
    refs = [deepcopy(ref), deepcopy(ref)]
    object_result = verify_supplied_highwater_git_objects(**custody_inputs)
    objects = {
        "schema": OBJECT_OBS_SCHEMA,
        "repository": p["repository"],
        "host": "api.github.com",
        "method": "GET",
        "commit_sha": object_result["candidate_commit_sha"],
        "tree_sha": object_result["candidate_tree_sha"],
        "blob_git_sha1": object_result["candidate_blob_git_sha1"],
        "blob_sha256": object_result["candidate_blob_sha256"],
    }
    body = {
        "schema": CLAIM_BODY_SCHEMA,
        "repository": p["repository"],
        "ref": p["ref"],
        "series_id": p["series_id"],
        "request_id": p["request_id"],
        "owner_key_epoch": 8,
        "expected_old_ref_sha": previous_ref,
        "candidate_commit_sha": object_result["candidate_commit_sha"],
        "candidate_tree_sha": object_result["candidate_tree_sha"],
        "candidate_blob_sha256": object_result["candidate_blob_sha256"],
        "previous_checkpoint_tip_sha256":
            p["expected_tip_checkpoint_sha256"],
        "proposed_checkpoint_tip_sha256":
            p["proposed_tip_checkpoint_sha256"],
        "intent_sha256": p["intent_sha256"],
        "proposal_sha256": p["proposal_sha256"],
        "ref_read_one_sha256": _digest(refs[0]),
        "ref_read_two_sha256": _digest(refs[1]),
        "object_read_sha256": _digest(objects),
        "remote_transport_authenticated": False,
        "owner_iam_proven": False,
        "remote_atomic_cas_proven": False,
        "cache_published": False,
        "signals_eligible": False,
    }
    signed = {
        "schema": CLAIM_SCHEMA,
        "key_id": FAKE_OWNER_ID,
        "body": body,
        "signature_b64": sign(OWNER_PRIVATE, body),
    }
    return {
        "custody_inputs": custody_inputs,
        "readonly_ref_observations": refs,
        "readonly_object_observation": objects,
        "signed_owner_claim": signed,
        "trusted_owner_key_id": FAKE_OWNER_ID,
        "supplied_owner_public_key": OWNER_PUBLIC,
        "pinned_owner_public_key_sha256": sha256(OWNER_PUBLIC).hexdigest(),
        "pinned_signed_claim_sha256": _digest(signed),
        "pinned_external_old_ref_sha": previous_ref,
        "pinned_external_old_checkpoint_tip_sha256":
            p["expected_tip_checkpoint_sha256"],
        "pinned_owner_key_epoch": 8,
    }


def review(f, **changes):
    return verify_signed_readonly_git_evidence_claim(**dict(f, **changes))


def fake_rotation(f=None):
    if f is None:
        f = fake_signed_claim()
    p = f["custody_inputs"]["proposal"]
    body = {
        "schema": ROTATION_BODY_SCHEMA,
        "repository": p["repository"],
        "ref": p["ref"],
        "series_id": p["series_id"],
        "old_key_id": FAKE_OWNER_ID,
        "new_key_id": FAKE_NEXT_OWNER_ID,
        "old_key_sha256": sha256(OWNER_PUBLIC).hexdigest(),
        "new_key_sha256": sha256(NEXT_PUBLIC).hexdigest(),
        "old_epoch": 8,
        "new_epoch": 9,
        "old_ref_sha": p["expected_parent_sha"],
        "old_checkpoint_tip_sha256":
            p["expected_tip_checkpoint_sha256"],
        "status": "PROPOSED_NOT_ACTIVATED",
        "activated": False,
        "owner_iam_verified": False,
        "cache_published": False,
    }
    envelope = {
        "schema": ROTATION_SCHEMA,
        "body": body,
        "old_signature_b64": sign(OWNER_PRIVATE, body),
        "new_signature_b64": sign(NEXT_PRIVATE, body),
    }
    return {
        "rotation": envelope,
        "old_owner_public_key": OWNER_PUBLIC,
        "new_owner_public_key": NEXT_PUBLIC,
        "old_owner_key_id": FAKE_OWNER_ID,
        "new_owner_key_id": FAKE_NEXT_OWNER_ID,
        "pinned_old_owner_key_sha256": sha256(OWNER_PUBLIC).hexdigest(),
        "pinned_rotation_sha256": _digest(envelope),
        "expected_old_epoch": 8,
        "expected_repository": p["repository"],
        "expected_ref": p["ref"],
        "expected_series_id": p["series_id"],
        "pinned_old_ref_sha": p["expected_parent_sha"],
        "pinned_old_tip_sha256": p["expected_tip_checkpoint_sha256"],
    }


def rotate(f, **changes):
    return review_dual_signed_owner_key_rotation_candidate(**dict(f, **changes))


class ReadonlyGitProvenanceClaimTests(unittest.TestCase):
    def test_two_source_scopes_signed_fake_claim_still_no_owner_authority(self):
        for provider, tf in (("DNSE", "D1"), ("SSI", "M5")):
            with self.subTest(provider=provider, tf=tf):
                f = fake_signed_claim(provider=provider, tf=tf)
                result = review(f)
                self.assertTrue(result["supplied_ref_reads_consistent"])
                self.assertTrue(result["supplied_object_readback_consistent"])
                self.assertTrue(result["supplied_checkpoint_ed25519_verified"])
                self.assertTrue(
                    result["owner_evidence_signature_valid_for_supplied_key"]
                )
                self.assertTrue(result["separate_owner_evidence_key_bytes"])
                for key in (
                    "independent_owner_key_and_external_floor_authenticated",
                    "github_rest_response_origin_authenticated",
                    "git_sha1_collision_protected",
                    "owner_repo_ref_rules_and_iam_verified",
                    "owner_key_rotation_or_revocation_activated",
                    "remote_ref_update_or_atomic_cas_proven",
                    "production_cache_published", "signals_eligible",
                ):
                    self.assertIs(result[key], False, key)

    def test_two_equal_ref_reads_do_not_mean_provider_atomicity(self):
        f = fake_signed_claim()
        self.assertEqual(f["readonly_ref_observations"][0],
                         f["readonly_ref_observations"][1])
        result = review(f)
        self.assertIs(result["remote_ref_update_or_atomic_cas_proven"], False)

    def test_stale_first_or_second_ref_read_denied(self):
        f = fake_signed_claim()
        for index in (0, 1):
            with self.subTest(index=index), self.assertRaisesRegex(
                GitReadEvidenceDenied, "REF_DRIFT_OR_SCOPE"
            ):
                refs = deepcopy(f["readonly_ref_observations"])
                refs[index]["sha"] = "e" * 40
                review(f, readonly_ref_observations=refs)

    def test_unsupported_ref_read_count_and_type_denied(self):
        f = fake_signed_claim()
        for refs in ([], None, {}, [f["readonly_ref_observations"][0]] * 3):
            with self.subTest(refs_type=type(refs).__name__), self.assertRaisesRegex(
                GitReadEvidenceDenied, "TWO_REF_READS_REQUIRED"
            ):
                review(f, readonly_ref_observations=refs)

    def test_provider_claim_does_not_allow_wrong_host_method_or_ref(self):
        f = fake_signed_claim()
        for key, value in (
            ("host", "attacker.example.com"), ("method", "PATCH"),
            ("repository", "another-owner/private"), ("ref", "refs/heads/main"),
        ):
            refs = deepcopy(f["readonly_ref_observations"])
            refs[0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "REF_DRIFT_OR_SCOPE"
            ):
                review(f, readonly_ref_observations=refs)

    def test_readonly_object_observation_cannot_change_github_ids(self):
        f = fake_signed_claim()
        obj = f["readonly_object_observation"]
        for field, value in (
            ("commit_sha", "f" * 40), ("tree_sha", "f" * 40),
            ("blob_git_sha1", "f" * 40), ("blob_sha256", "f" * 64),
            ("host", "not-github.example"), ("method", "POST"),
            ("repository", "wrong/private"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                GitReadEvidenceDenied, "OBJECT_DRIFT_OR_SCOPE"
            ):
                review(f, readonly_object_observation=dict(obj, **{field: value}))

    def test_unexpected_ref_and_object_fields_denied(self):
        f = fake_signed_claim()
        refs = deepcopy(f["readonly_ref_observations"])
        refs[1]["http_status_claim"] = 200
        with self.assertRaisesRegex(GitReadEvidenceDenied, "REF_DRIFT_OR_SCOPE"):
            review(f, readonly_ref_observations=refs)
        obj = dict(f["readonly_object_observation"], role="certified_owner")
        with self.assertRaisesRegex(GitReadEvidenceDenied, "OBJECT_DRIFT_OR_SCOPE"):
            review(f, readonly_object_observation=obj)

    def test_stale_external_ref_pin_denied(self):
        f = fake_signed_claim()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_FLOOR_MISMATCH"):
            review(f, pinned_external_old_ref_sha="f" * 40)

    def test_stale_external_checkpoint_pin_denied(self):
        f = fake_signed_claim()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_FLOOR_MISMATCH"):
            review(f, pinned_external_old_checkpoint_tip_sha256="f" * 64)

    def test_owner_public_key_fingerprint_cannot_be_forged(self):
        f = fake_signed_claim()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, pinned_owner_public_key_sha256="f" * 64)
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, supplied_owner_public_key=NEXT_PUBLIC)

    def test_fake_owner_key_must_be_distinct_from_checkpoint_signer(self):
        f = fake_signed_claim()
        pub = f["custody_inputs"]["supplied_ed25519_public_key"]
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, supplied_owner_public_key=pub,
                   pinned_owner_public_key_sha256=sha256(pub).hexdigest())

    def test_owner_claim_rollback_epoch_or_boolean_epoch_denied(self):
        f = fake_signed_claim()
        for epoch in (7, 9):
            with self.subTest(epoch=epoch), self.assertRaisesRegex(
                GitReadEvidenceDenied, "CLAIM_MISMATCH"
            ):
                review(f, pinned_owner_key_epoch=epoch)
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, pinned_owner_key_epoch=True)

    def test_changed_signed_owner_claim_digest_denied(self):
        f = fake_signed_claim()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "SIGNED_CLAIM_PIN_MISMATCH"):
            review(f, pinned_signed_claim_sha256="c" * 64)

    def test_wrong_owner_signature_is_denied_even_with_matching_claim_hash(self):
        f = fake_signed_claim()
        envelope = deepcopy(f["signed_owner_claim"])
        envelope["signature_b64"] = sign(NEXT_PRIVATE, envelope["body"])
        with self.assertRaisesRegex(GitReadEvidenceDenied, "SIGNATURE_INVALID"):
            review(f, signed_owner_claim=envelope,
                   pinned_signed_claim_sha256=_digest(envelope))

    def test_changed_or_re_signed_authority_flags_denied(self):
        f = fake_signed_claim()
        for key in (
            "remote_transport_authenticated", "owner_iam_proven",
            "remote_atomic_cas_proven", "cache_published", "signals_eligible",
        ):
            claim = deepcopy(f["signed_owner_claim"])
            claim["body"][key] = True
            claim["signature_b64"] = sign(OWNER_PRIVATE, claim["body"])
            with self.subTest(key=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "CLAIM_MISMATCH"
            ):
                review(f, signed_owner_claim=claim,
                       pinned_signed_claim_sha256=_digest(claim))

    def test_request_id_proposal_digest_and_observation_digests_bound(self):
        f = fake_signed_claim()
        for key, value in (
            ("request_id", "FAKE_UNRELATED_REQUEST_0001"),
            ("proposal_sha256", "f" * 64),
            ("object_read_sha256", "f" * 64),
            ("ref_read_one_sha256", "f" * 64),
            ("ref_read_two_sha256", "f" * 64),
        ):
            claim = deepcopy(f["signed_owner_claim"])
            claim["body"][key] = value
            claim["signature_b64"] = sign(OWNER_PRIVATE, claim["body"])
            with self.subTest(field=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "CLAIM_MISMATCH"
            ):
                review(f, signed_owner_claim=claim,
                       pinned_signed_claim_sha256=_digest(claim))

    def test_owner_claim_envelope_must_have_exact_schema(self):
        f = fake_signed_claim()
        for altered in (
            dict(f["signed_owner_claim"], claimed_repo_owner=True),
            dict(f["signed_owner_claim"], schema="unknown"),
            dict(f["signed_owner_claim"], key_id="OTHER_KEY"),
        ):
            with self.assertRaisesRegex(GitReadEvidenceDenied, "CLAIM_SCHEMA"):
                review(f, signed_owner_claim=altered)

    def test_noncanonical_b64_signature_rejected(self):
        f = fake_signed_claim()
        claim = deepcopy(f["signed_owner_claim"])
        claim["signature_b64"] = "!" * 88
        with self.assertRaisesRegex(GitReadEvidenceDenied, "SIGNATURE_ENCODING"):
            review(f, signed_owner_claim=claim,
                   pinned_signed_claim_sha256=_digest(claim))

    def test_custody_sha_and_signature_must_still_be_verified(self):
        f = fake_signed_claim()
        changed = dict(f["custody_inputs"], raw_blob=b"tamper")
        with self.assertRaisesRegex(GitReadEvidenceDenied, "GIT_CUSTODY_INVALID"):
            review(f, custody_inputs=changed)

    def test_bad_pins_and_raw_unexpected_types_fail_closed(self):
        f = fake_signed_claim()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, pinned_external_old_ref_sha=True)
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_PINS_INVALID"):
            review(f, trusted_owner_key_id=[])
        with self.assertRaisesRegex(GitReadEvidenceDenied, "CUSTODY_INPUT_INVALID"):
            review(f, custody_inputs=None)


class OwnerRotationCandidateTests(unittest.TestCase):
    def test_valid_dual_signature_is_not_owner_approved_rotation(self):
        f = fake_rotation()
        result = rotate(f)
        self.assertTrue(result["dual_signatures_valid_for_supplied_keys"])
        self.assertEqual(result["previous_epoch"], 8)
        self.assertEqual(result["proposed_epoch"], 9)
        for key in (
            "independent_old_key_pin_authenticated",
            "new_key_owner_iam_authorized",
            "key_rotation_activated",
            "old_key_revoked",
            "external_monotone_key_epoch_verified",
            "remote_ref_update_or_atomic_cas_proven",
            "production_cache_published", "signals_eligible",
        ):
            self.assertIs(result[key], False, key)

    def test_same_key_as_old_or_same_key_id_denied(self):
        f = fake_rotation()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_INPUT_INVALID"):
            rotate(f, new_owner_public_key=OWNER_PUBLIC)
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_INPUT_INVALID"):
            rotate(f, new_owner_key_id=FAKE_OWNER_ID)

    def test_old_external_key_pin_replaced_denied(self):
        f = fake_rotation()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_INPUT_INVALID"):
            rotate(f, pinned_old_owner_key_sha256="f" * 64)

    def test_old_epoch_replay_and_epoch_type_denied(self):
        f = fake_rotation()
        for epoch in (7, 9):
            with self.subTest(epoch=epoch), self.assertRaisesRegex(
                GitReadEvidenceDenied, "SCOPE_OR_EPOCH"
            ):
                rotate(f, expected_old_epoch=epoch)
        with self.assertRaisesRegex(GitReadEvidenceDenied, "EXTERNAL_INPUT_INVALID"):
            rotate(f, expected_old_epoch=True)

    def test_forged_claim_of_activated_rotation_fails(self):
        f = fake_rotation()
        for key, value in (
            ("activated", True), ("owner_iam_verified", True),
            ("cache_published", True), ("status", "ACTIVE"),
        ):
            rotation = deepcopy(f["rotation"])
            rotation["body"][key] = value
            rotation["old_signature_b64"] = sign(OWNER_PRIVATE, rotation["body"])
            rotation["new_signature_b64"] = sign(NEXT_PRIVATE, rotation["body"])
            with self.subTest(key=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "SCOPE_OR_EPOCH"
            ):
                rotate(f, rotation=rotation,
                       pinned_rotation_sha256=_digest(rotation))

    def test_single_old_or_new_signer_not_enough(self):
        f = fake_rotation()
        for key in ("old_signature_b64", "new_signature_b64"):
            rotation = deepcopy(f["rotation"])
            rotation[key] = sign(
                NEXT_PRIVATE if key == "old_signature_b64" else OWNER_PRIVATE,
                rotation["body"],
            )
            with self.subTest(key=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "SIGNATURE_INVALID"
            ):
                rotate(f, rotation=rotation,
                       pinned_rotation_sha256=_digest(rotation))

    def test_key_rotation_commitment_digest_pin_cannot_move(self):
        f = fake_rotation()
        with self.assertRaisesRegex(GitReadEvidenceDenied, "PIN_MISMATCH"):
            rotate(f, pinned_rotation_sha256="f" * 64)

    def test_rotation_ref_tip_scope_and_issuer_replacement_denied(self):
        f = fake_rotation()
        for key, value in (
            ("old_ref_sha", "d" * 40),
            ("old_checkpoint_tip_sha256", "d" * 64),
            ("repository", "not-owner/highwater"),
            ("ref", "refs/heads/main"),
            ("new_key_id", "INTRUDER_FAKE_KEY"),
            ("new_epoch", 10),
        ):
            rotation = deepcopy(f["rotation"])
            rotation["body"][key] = value
            rotation["old_signature_b64"] = sign(OWNER_PRIVATE, rotation["body"])
            rotation["new_signature_b64"] = sign(NEXT_PRIVATE, rotation["body"])
            with self.subTest(key=key), self.assertRaisesRegex(
                GitReadEvidenceDenied, "SCOPE_OR_EPOCH"
            ):
                rotate(f, rotation=rotation,
                       pinned_rotation_sha256=_digest(rotation))

    def test_rotation_missing_signature_or_extra_fields_denied(self):
        f = fake_rotation()
        for rotation in (
            dict(f["rotation"], override="yes"),
            dict(f["rotation"], old_signature_b64=None),
            dict(f["rotation"], schema="different"),
        ):
            with self.subTest(rotation_keys=list(rotation)), self.assertRaises(
                GitReadEvidenceDenied,
            ):
                rotate(f, rotation=rotation,
                       pinned_rotation_sha256=_digest(rotation))


if __name__ == "__main__":
    unittest.main()
