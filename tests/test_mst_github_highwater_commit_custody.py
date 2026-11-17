"""§200 fake-only raw Git commit/tree/blob custody and owner-control intake QA.

All Git object bytes and source history are deterministic fictitious fixtures.
No GitHub highwater ref is fetched or updated, no credentials or actual
GitHub backend/market data/signer owner are supplied or certified.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.mst_github_highwater_commit_custody import (
    BLOB_NAME, CONTROL_SCHEMA, PAYLOAD_SCHEMA, REQUIRED_CONTROLS,
    TREE_PREFIX, GitObjectCustodyDenied, _git_sha,
    review_owner_highwater_control_evidence,
    verify_supplied_highwater_git_objects,
)
from scripts.mst_signed_highwater_diagnostic import checkpoint_digest
from test_mst_github_highwater_ref_proposal import (
    NEW_A_SHA, OLD_SHA, OWNER_PRIVATE_REPO, example, make,
)
from test_mst_signed_highwater_diagnostic import (
    KEY_ID, OTHER_PUBLIC, PUBLIC, snapshots,
)
from test_mst_highwater_cas_intent import anchor, prepare, proposed

FAKE_ACTOR = "Fake Custody <fake@example.invalid> 1700000000 +0000"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")


def commit_bytes(tree_sha, parent_sha=OLD_SHA, *,
                 message="MST highwater candidate (UNPUBLISHED)\n"):
    return (
        "tree " + tree_sha + "\nparent " + parent_sha +
        "\nauthor " + FAKE_ACTOR + "\ncommitter " + FAKE_ACTOR +
        "\n\n" + message
    ).encode("utf-8")


def sample(*, provider="DNSE", tf="D1"):
    if provider == "DNSE" and tf == "D1":
        chain, a, next_signed, intent, ref, _ = example()
    else:
        _, chain = snapshots(provider, tf)
        a = anchor(chain)
        next_signed = proposed(chain, provider=provider, tf=tf)
        intent = prepare(chain, next_signed, a,
                         request_id="FAKE_GIT_CUSTODY_REQUEST_0001")
        _, _, _, _, ref, _ = example()
        ref = dict(ref, ref="refs/heads/highwater/" + intent["series_id"])
    payload = {
        "schema": PAYLOAD_SCHEMA,
        "series_id": intent["series_id"],
        "request_id": intent["request_id"],
        "intent_sha256": intent["intent_sha256"],
        "checkpoint_sha256": checkpoint_digest(next_signed),
        "signed_checkpoint": next_signed,
        "cache_published": False,
        "signals_eligible": False,
    }
    raw_blob = canonical(payload)
    blob_sha = _git_sha(b"blob", raw_blob)
    raw_tree = TREE_PREFIX + bytes.fromhex(blob_sha)
    tree_sha = _git_sha(b"tree", raw_tree)
    raw_commit = commit_bytes(tree_sha)
    commit_sha = _git_sha(b"commit", raw_commit)
    candidate = {
        "schema": "mst.cloud.github_highwater_commit_observation.v0.1",
        "sha": commit_sha, "parents": [OLD_SHA], "tree_sha": tree_sha,
    }
    proposal = make(intent, a, ref, candidate)
    return {
        "proposal": proposal, "pinned_proposal_sha256": proposal["proposal_sha256"],
        "ref_observation": ref, "prepared_intent": intent,
        "pinned_intent_sha256": intent["intent_sha256"],
        "old_anchor": a, "signed_checkpoint_history": chain,
        "trusted_key_id": KEY_ID, "supplied_ed25519_public_key": PUBLIC,
        "raw_commit": raw_commit, "raw_tree": raw_tree, "raw_blob": raw_blob,
    }


def check(fixture, **replace):
    return verify_supplied_highwater_git_objects(**dict(fixture, **replace))


class GitHighwaterCustodyTests(unittest.TestCase):
    def test_valid_fictional_git_objects_and_signed_payload_still_no_go(self):
        for provider, tf in (("DNSE", "D1"), ("SSI", "M5")):
            with self.subTest(provider=provider, tf=tf):
                fixture = sample(provider=provider, tf=tf)
                result = check(fixture)
                self.assertTrue(result["supplied_git_objects_hash_consistent"])
                self.assertTrue(result["ed25519_valid_for_supplied_key"])
                self.assertEqual(result["candidate_commit_sha"],
                                 fixture["proposal"]["proposed_commit_sha"])
                self.assertEqual(result["signed_tip_sha256"],
                                 fixture["proposal"]["proposed_tip_checkpoint_sha256"])
                for key in (
                    "git_sha1_collision_resistance_upgraded",
                    "remote_git_object_fetch_authenticated",
                    "owner_repo_iam_and_ref_protection_verified",
                    "trusted_signer_and_external_tip_authenticated",
                    "remote_ref_update_executed", "atomic_cas_proven",
                    "production_cache_published", "signals_eligible",
                ):
                    self.assertIs(result[key], False, key)

    def test_fake_git_object_sha_is_type_and_length_domain_separated(self):
        fixture = sample()
        self.assertNotEqual(_git_sha(b"blob", fixture["raw_blob"]),
                            _git_sha(b"tree", fixture["raw_blob"]))
        self.assertNotEqual(_git_sha(b"blob", fixture["raw_blob"]),
                            _git_sha(b"blob", fixture["raw_blob"] + b"x"))
        self.assertEqual(len(_git_sha(b"commit", fixture["raw_commit"])), 40)

    def test_modified_blob_bytes_no_longer_bind_to_tree(self):
        fixture = sample()
        payload = json.loads(fixture["raw_blob"])
        payload["request_id"] = "FAKE_CHANGED_BLOB_REQUEST_0001"
        with self.assertRaises(GitObjectCustodyDenied):
            check(fixture, raw_blob=canonical(payload))

    def test_noncanonical_json_whitespace_and_duplicate_key_denied(self):
        fixture = sample()
        padded = b" " + fixture["raw_blob"]
        with self.assertRaisesRegex(GitObjectCustodyDenied, "NONCANONICAL"):
            check(fixture, raw_blob=padded)
        duplicate = fixture["raw_blob"].replace(
            b'"schema":', b'"schema":"fake","schema":', 1,
        )
        with self.assertRaisesRegex(GitObjectCustodyDenied, "DUPLICATE_JSON_KEY"):
            check(fixture, raw_blob=duplicate)

    def test_forged_market_authority_or_extra_payload_key_rejected(self):
        fixture = sample()
        payload = json.loads(fixture["raw_blob"])
        for k, value in (
            ("cache_published", True),
            ("signals_eligible", True),
            ("other_claim", "full_signal"),
        ):
            with self.subTest(field=k), self.assertRaisesRegex(
                GitObjectCustodyDenied, "FALSE_AUTHORITY|SCHEMA_INVALID"
            ):
                changed = dict(payload, **{k: value})
                check(fixture, raw_blob=canonical(changed))

    def test_wrong_json_value_types_fail(self):
        fixture = sample()
        for raw in (b"[]", b'{"schema":null}', b"not json",
                    b"", None, "json", b" " * 9000):
            with self.subTest(raw=repr(raw)[:40]), self.assertRaises(
                GitObjectCustodyDenied,
            ):
                check(fixture, raw_blob=raw)

    def test_wrong_signer_rejected_even_with_matching_git_object_hashes(self):
        fixture = sample()
        with self.assertRaisesRegex(GitObjectCustodyDenied, "ED25519_CHAIN"):
            check(fixture, supplied_ed25519_public_key=OTHER_PUBLIC)

    def test_truncated_signed_history_cannot_validate_tip(self):
        fixture = sample()
        history = fixture["signed_checkpoint_history"]
        with self.assertRaisesRegex(GitObjectCustodyDenied, "ED25519_CHAIN"):
            check(fixture, signed_checkpoint_history=history[:-1])

    def test_wrong_checkpoint_envelope_digest_cannot_be_promoted(self):
        fixture = sample()
        payload = json.loads(fixture["raw_blob"])
        payload["checkpoint_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            GitObjectCustodyDenied, "SIGNED_TIP_OR_HEAD_MISMATCH"
        ):
            check(fixture, raw_blob=canonical(payload))

    def test_changed_blob_intent_is_rejected_before_git_hash(self):
        fixture = sample()
        payload = json.loads(fixture["raw_blob"])
        payload["intent_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            GitObjectCustodyDenied, "BLOB_INTENT_SCOPE_MISMATCH"
        ):
            check(fixture, raw_blob=canonical(payload))

    def test_tree_wrong_mode_path_or_extra_entry_fail(self):
        fixture = sample()
        tree = fixture["raw_tree"]
        changes = (
            b"100755 " + BLOB_NAME + b"\x00" + tree[-20:],
            b"100644 evil.json\x00" + tree[-20:],
            tree + tree,
            tree[:-1],
            b"100644 ../highwater.json\x00" + tree[-20:],
        )
        for bad in changes:
            with self.subTest(length=len(bad)), self.assertRaises(
                GitObjectCustodyDenied,
            ):
                check(fixture, raw_tree=bad)

    def test_tree_hash_must_match_original_proposal(self):
        fixture = sample()
        # Guaranteed one-bit mutation: appending a fixed byte is flaky when
        # the original Git object SHA happens to end with that same byte.
        changed = fixture["raw_tree"][:-1] + bytes([fixture["raw_tree"][-1] ^ 0x01])
        with self.assertRaisesRegex(GitObjectCustodyDenied, "TREE_SINGLE_BLOB"):
            check(fixture, raw_tree=changed)
        # A valid other single-blob tree cannot match old proposed tree SHA.
        altered_blob = fixture["raw_blob"] + b" "
        altered_tree = TREE_PREFIX + bytes.fromhex(_git_sha(b"blob", altered_blob))
        # The payload parser refuses the new noncanonical blob first;
        # so check a valid alternate JSON contract with unchanged flags.
        payload = json.loads(fixture["raw_blob"])
        payload["request_id"] = "FAKE_ANOTHER_CUSTODY_REQUEST"
        valid_other_blob = canonical(payload)
        valid_other_tree = TREE_PREFIX + bytes.fromhex(
            _git_sha(b"blob", valid_other_blob)
        )
        self.assertNotEqual(_git_sha(b"tree", valid_other_tree),
                            fixture["proposal"]["proposed_tree_sha"])
        self.assertNotEqual(altered_tree, fixture["raw_tree"])

    def test_commit_parent_tamper_rejected_before_object_identity(self):
        fixture = sample()
        commit = fixture["raw_commit"].replace(
            ("parent " + OLD_SHA).encode(),
            ("parent " + NEW_A_SHA).encode(), 1,
        )
        with self.assertRaisesRegex(
            GitObjectCustodyDenied, "PARENT_OR_TREE_MISMATCH"
        ):
            check(fixture, raw_commit=commit)

    def test_commit_tree_tamper_rejected(self):
        fixture = sample()
        bad_tree_sha = "9" * 40
        commit = fixture["raw_commit"].replace(
            ("tree " + fixture["proposal"]["proposed_tree_sha"]).encode(),
            ("tree " + bad_tree_sha).encode(), 1,
        )
        with self.assertRaisesRegex(
            GitObjectCustodyDenied, "PARENT_OR_TREE_MISMATCH"
        ):
            check(fixture, raw_commit=commit)

    def test_commit_sha_covers_actor_and_message_bytes(self):
        fixture = sample()
        commit = fixture["raw_commit"].replace(
            b"Fake Custody", b"Fake CUSTODY", 1,
        )
        with self.assertRaisesRegex(GitObjectCustodyDenied, "COMMIT_SHA_MISMATCH"):
            check(fixture, raw_commit=commit)

    def test_merge_commit_and_extra_header_fail_closed(self):
        fixture = sample()
        more_parent = fixture["raw_commit"].replace(
            b"\nauthor ", b"\nparent " + NEW_A_SHA.encode() + b"\nauthor ", 1
        )
        with self.assertRaisesRegex(
            GitObjectCustodyDenied, "COMMIT_NOT_SINGLE_PARENT"
        ):
            check(fixture, raw_commit=more_parent)
        gpg_header = fixture["raw_commit"].replace(
            b"\ncommitter ", b"\ngpgsig FAKE\ncommitter ", 1
        )
        with self.assertRaises(GitObjectCustodyDenied):
            check(fixture, raw_commit=gpg_header)

    def test_wrong_commit_message_cannot_promote(self):
        fixture = sample()
        commit = fixture["raw_commit"].replace(
            b"MST highwater candidate (UNPUBLISHED)",
            b"MST highwater production RELEASE", 1,
        )
        with self.assertRaisesRegex(GitObjectCustodyDenied, "COMMIT_MESSAGE"):
            check(fixture, raw_commit=commit)

    def test_wrong_supplied_proposal_pin_or_old_ref_no_authority(self):
        fixture = sample()
        with self.assertRaisesRegex(GitObjectCustodyDenied, "PRIOR_INTENT_OR_REF"):
            check(fixture, pinned_proposal_sha256="a" * 64)
        with self.assertRaisesRegex(GitObjectCustodyDenied, "PRIOR_INTENT_OR_REF"):
            check(fixture, ref_observation=dict(fixture["ref_observation"],
                                                sha="7" * 40))
        with self.assertRaisesRegex(GitObjectCustodyDenied, "PRIOR_INTENT_OR_REF"):
            check(fixture, pinned_intent_sha256="b" * 64)

    def test_untrusted_complete_owner_control_checklist_does_not_grant_access(self):
        fixture = sample()
        entries = [
            {"control": k, "status": "OWNER_REVIEW_PENDING",
             "evidence_reference": "owner-review/placeholder-20261115"}
            for k in sorted(REQUIRED_CONTROLS)
        ]
        result = review_owner_highwater_control_evidence(
            proposal=fixture["proposal"], entries=entries,
        )
        self.assertEqual(result["schema"], CONTROL_SCHEMA)
        self.assertEqual(result["missing_controls"], [])
        self.assertEqual(len(result["pending_unverified_controls"]), 8)
        for k in ("owner_approval_and_independent_review_proven",
                  "real_private_repo_or_permissions_provisioned",
                  "independent_signer_and_monotone_tip_verified",
                  "remote_ref_write_authorized",
                  "production_cache_published", "signals_eligible"):
            self.assertFalse(result[k], k)

    def test_missing_owner_controls_and_false_verification_denied(self):
        fixture = sample()
        proposal = fixture["proposal"]
        r = review_owner_highwater_control_evidence(proposal=proposal,
                                                     entries=[])
        self.assertEqual(len(r["missing_controls"]), 8)
        control = sorted(REQUIRED_CONTROLS)[0]
        good = {"control": control, "status": "OWNER_REVIEW_PENDING",
                "evidence_reference": "owner-pending/placeholder"}
        for bad in (
            [good, good],
            [dict(good, status="VERIFIED")],
            [dict(good, status=True)],
            [dict(good, evidence_reference="https://bad?token=x")],
            [dict(good, control="source_repository_is_enough")],
            [dict(good, published=True)],
            [dict(good, status="MISSING")],
        ):
            with self.subTest(bad=str(bad)[:60]), self.assertRaises(
                GitObjectCustodyDenied,
            ):
                review_owner_highwater_control_evidence(
                    proposal=proposal, entries=bad,
                )
        with self.assertRaisesRegex(GitObjectCustodyDenied, "PROPOSAL_INVALID"):
            review_owner_highwater_control_evidence(
                proposal={"fake": True}, entries=[],
            )


if __name__ == "__main__":
    unittest.main()
