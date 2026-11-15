"""§202 fake owner-repository inventory and GitHub ruleset provenance tests.

No provider token, independent owner signer, real private highwater repo,
branch mutation, price data, production publisher or trading.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.mst_github_highwater_owner_trust_preflight import (
    REPOSITORY_SCHEMA, RULESET_SCHEMA, TRUST_SCHEMA,
    OwnerTrustPreflightDenied, _digest,
    review_accessible_owner_repo_inventory,
    review_owner_highwater_trust_boundary,
)
from test_mst_github_highwater_ref_proposal import example, make

OWNER = "fake-owner"
OWNER_REPO = "fake-owner/highwater-custody-test"
REPO_ID = 123456789
WITNESS = "independent-owner-review/PENDING-0001"


def test_record():
    _, anchor, _, intent, ref, commit = example()
    proposal = make(intent, anchor, ref, commit)
    repo = {
        "schema": REPOSITORY_SCHEMA,
        "id": REPO_ID, "full_name": OWNER_REPO,
        "visibility": "private", "owner_login": OWNER,
        "archived": False,
    }
    rule = {
        "schema": RULESET_SCHEMA,
        "repository_id": REPO_ID,
        "ref": proposal["ref"],
        "source_type": "Repository", "target": "branch",
        "enforcement": "active",
        "include": [proposal["ref"]], "exclude": [],
        "bypass_actors": [],
        "rules": ["deletion", "non_fast_forward", "required_linear_history"],
        "observed_read_only": True,
        "provider_origin_authenticated": False,
    }
    floor = {
        "schema": TRUST_SCHEMA,
        "repository_id": REPO_ID,
        "ref": proposal["ref"],
        "external_witness_id": WITNESS,
        "owner_key_sha256": "c" * 64,
        "key_epoch": 7,
        "old_ref_sha": proposal["expected_parent_sha"],
        "old_checkpoint_tip_sha256":
            proposal["expected_tip_checkpoint_sha256"],
        "review_status": "PENDING_EXTERNAL_AUTHENTICATION",
        "owner_verified": False,
    }
    return {
        "proposal": proposal,
        "pinned_proposal_sha256": proposal["proposal_sha256"],
        "expected_old_ref_observation": ref,
        "owner_repo_observation": repo,
        "effective_ruleset_observation": rule,
        "external_trust_floor_candidate": floor,
        "pinned_ruleset_sha256": _digest(rule),
        "pinned_external_floor_sha256": _digest(floor),
    }


def check(x, **overrides):
    return review_owner_highwater_trust_boundary(**dict(x, **overrides))


class HighwaterOwnerRepositoryInventoryTests(unittest.TestCase):
    def test_only_public_accessible_repos_are_no_private_backend_evidence(self):
        entries = [
            {"id": i + 1, "full_name": "ngluonghoa/" + name,
             "visibility": "public"}
            for i, name in enumerate([
                "swing-trading-1-8", "forex-trading-1-0",
                "MOCHIVNST", "MOCHIFX", "MST", "MFX",
                "ngluonghoa.github.io",
            ])
        ]
        r = review_accessible_owner_repo_inventory(
            owner_login="ngluonghoa", entries=entries,
            claimed_complete=True,
        )
        self.assertEqual(r["observed_visible_repo_count"], 7)
        self.assertEqual(r["observed_private_custody_repo_count"], 0)
        self.assertFalse(r["private_backend_candidate_visible"])
        self.assertFalse(r["inventory_verified_against_authenticated_provider"])
        self.assertFalse(r["separate_owner_highwater_backend_provisioned"])
        self.assertFalse(r["highwater_write_authorized"])

    def test_private_non_source_repository_only_a_candidate_not_authority(self):
        entries = [
            {"id": 45, "full_name": OWNER_REPO, "visibility": "private"},
        ]
        r = review_accessible_owner_repo_inventory(
            owner_login=OWNER, entries=entries, claimed_complete=True,
        )
        self.assertEqual(r["observed_private_custody_repo_count"], 1)
        self.assertTrue(r["private_backend_candidate_visible"])
        self.assertFalse(r["separate_owner_highwater_backend_provisioned"])
        self.assertFalse(r["highwater_write_authorized"])

    def test_inventory_duplicate_ids_names_and_wrong_owner_fail_closed(self):
        valid = {"id": 45, "full_name": OWNER_REPO, "visibility": "private"}
        for bad in (
            [valid, valid],
            [valid, dict(valid, id=46)],
            [valid, dict(valid, full_name="fake-owner/other")],
            [dict(valid, full_name="different/owner")],
            [dict(valid, id=True)],
            [dict(valid, visibility="secret")],
        ):
            with self.subTest(bad=bad), self.assertRaises(
                OwnerTrustPreflightDenied,
            ):
                review_accessible_owner_repo_inventory(
                    owner_login=OWNER, entries=bad, claimed_complete=True,
                )

    def test_inventory_missing_completeness_or_large_list_denied(self):
        valid = {"id": 45, "full_name": OWNER_REPO, "visibility": "private"}
        for data, claim in (([], False), ({}, True),
                            ([valid] * 501, True), ([], 1), (None, True)):
            with self.subTest(data_type=type(data).__name__), self.assertRaises(
                OwnerTrustPreflightDenied,
            ):
                review_accessible_owner_repo_inventory(
                    owner_login=OWNER, entries=data, claimed_complete=claim,
                )

    def test_inventory_cannot_promote_public_mst_to_private_custody(self):
        r = review_accessible_owner_repo_inventory(
            owner_login="ngluonghoa", claimed_complete=True,
            entries=[{"id": 1, "full_name": "ngluonghoa/MST",
                      "visibility": "private"}],
        )
        self.assertFalse(r["private_backend_candidate_visible"])
        self.assertFalse(r["highwater_write_authorized"])


class PrivateHighwaterOwnerTrustBoundaryTests(unittest.TestCase):
    def test_fictional_good_custody_ruleset_is_still_not_verified(self):
        r = check(test_record())
        self.assertEqual(r["candidate_repository_id"], REPO_ID)
        self.assertEqual(
            r["ruleset_types_observed_in_supplied_claim"],
            ["deletion", "non_fast_forward", "required_linear_history"],
        )
        self.assertTrue(r["no_bypass_actors_in_supplied_claim"])
        for k in (
            "provider_authenticated_ruleset_readback",
            "owner_witness_proven_independent",
            "owner_signer_tip_epoch_proven_monotone",
            "administrator_override_prevented",
            "real_private_repo_access_confirmed",
            "real_remote_ref_update_or_cas_proven",
            "highwater_write_authorized", "cache_published",
            "signals_eligible",
        ):
            self.assertIs(r[k], False, k)

    def test_proposal_tampering_and_stale_ref_fails(self):
        x = test_record()
        with self.assertRaisesRegex(
            OwnerTrustPreflightDenied, "PRIOR_PROPOSAL_INVALID"
        ):
            check(x, pinned_proposal_sha256="f" * 64)
        with self.assertRaisesRegex(
            OwnerTrustPreflightDenied, "PRIOR_PROPOSAL_INVALID"
        ):
            check(x, expected_old_ref_observation=dict(
                x["expected_old_ref_observation"], sha="9" * 40,
            ))

    def test_no_public_archived_different_repository_or_owner(self):
        x = test_record()
        repo = x["owner_repo_observation"]
        for key, val in (
            ("visibility", "public"),
            ("visibility", "internal"),
            ("archived", True),
            ("archived", 0),
            ("full_name", "fake-owner/not-the-proposed-repo"),
            ("full_name", "ngluonghoa/MST"),
            ("owner_login", "different"),
            ("id", True),
            ("id", 0),
            ("schema", "invalid"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerTrustPreflightDenied, "PRIVATE_OWNER_REPO_INVALID"
            ):
                check(x, owner_repo_observation=dict(repo, **{key: val}))

    def test_ruleset_must_be_active_and_on_exact_branch(self):
        x = test_record()
        rule = x["effective_ruleset_observation"]
        for key, val in (
            ("enforcement", "disabled"), ("enforcement", "evaluate"),
            ("enforcement", "enabled"),
            ("ref", "refs/heads/main"),
            ("target", "tag"),
            ("source_type", "Unknown"),
            ("repository_id", 999),
            ("repository_id", True),
            ("observed_read_only", False),
            ("provider_origin_authenticated", True),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerTrustPreflightDenied, "RULESET_SCOPE_OR_ENFORCEMENT"
            ):
                check(x, effective_ruleset_observation=dict(rule, **{key: val}))

    def test_no_bypass_and_only_exact_ref_conditions(self):
        x = test_record()
        rule = x["effective_ruleset_observation"]
        for key, val in (
            ("include", ["~ALL"]),
            ("include", ["refs/heads/highwater/*"]),
            ("include", ["refs/heads/main"]),
            ("include", []),
            ("exclude", [x["proposal"]["ref"]]),
            ("bypass_actors", [{"actor_type": "RepositoryRole",
                                "bypass_mode": "always"}]),
            ("bypass_actors", [{"actor_type": "Integration",
                                "bypass_mode": "pull_request"}]),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerTrustPreflightDenied, "RULESET_NOT_STRICT_ENOUGH"
            ):
                check(x, effective_ruleset_observation=dict(rule, **{key: val}))

    def test_rule_coverage_require_exact_deletion_nonfastforward_linear(self):
        x = test_record()
        rule = x["effective_ruleset_observation"]
        for choices in (
            [], ["deletion"],
            ["non_fast_forward", "required_linear_history"],
            ["deletion", "non_fast_forward"],
            ["deletion", "non_fast_forward", "required_signatures"],
            ["deletion", "non_fast_forward", "required_linear_history",
             "update"],
            ["deletion", "deletion", "non_fast_forward"],
        ):
            with self.subTest(choices=choices), self.assertRaisesRegex(
                OwnerTrustPreflightDenied, "RULESET_NOT_STRICT_ENOUGH"
            ):
                check(x, effective_ruleset_observation=dict(rule, rules=choices))

    def test_self_claimed_signed_or_verified_witness_denied(self):
        x = test_record()
        floor = x["external_trust_floor_candidate"]
        for key, val in (
            ("review_status", "VERIFIED"),
            ("review_status", "ACTIVE"),
            ("owner_verified", True),
            ("owner_verified", 1),
            ("external_witness_id", "x"),
            ("key_epoch", 0),
            ("key_epoch", True),
            ("owner_key_sha256", "BAD"),
            ("old_ref_sha", "a" * 40),
            ("old_checkpoint_tip_sha256", "b" * 64),
            ("repository_id", 777),
            ("ref", "refs/heads/main"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                OwnerTrustPreflightDenied, "OWNER_FLOOR_INVALID"
            ):
                check(x, external_trust_floor_candidate=dict(
                    floor, **{key: val},
                ))

    def test_rehashed_floor_or_ruleset_requires_original_pin(self):
        x = test_record()
        rule = deepcopy(x["effective_ruleset_observation"])
        rule["rules"] = list(reversed(rule["rules"]))
        with self.assertRaisesRegex(
            OwnerTrustPreflightDenied, "CANDIDATE_PIN_DRIFT"
        ):
            check(x, effective_ruleset_observation=rule)
        floor = dict(x["external_trust_floor_candidate"], key_epoch=8)
        with self.assertRaisesRegex(
            OwnerTrustPreflightDenied, "CANDIDATE_PIN_DRIFT"
        ):
            check(x, external_trust_floor_candidate=floor)

    def test_entirely_replaced_rule_and_pin_is_still_not_owner_proof(self):
        x = test_record()
        rule = deepcopy(x["effective_ruleset_observation"])
        rule["rules"] = list(reversed(rule["rules"]))
        result = check(x, effective_ruleset_observation=rule,
                       pinned_ruleset_sha256=_digest(rule))
        self.assertFalse(result["provider_authenticated_ruleset_readback"])
        self.assertFalse(result["owner_witness_proven_independent"])
        self.assertFalse(result["highwater_write_authorized"])

    def test_extra_unknown_fields_and_missing_scope_denied(self):
        x = test_record()
        for field, payload in (
            ("owner_repo_observation", dict(
                x["owner_repo_observation"], bypass_admin=True,
            )),
            ("effective_ruleset_observation", dict(
                x["effective_ruleset_observation"], force_push_allowed=True,
            )),
            ("external_trust_floor_candidate", dict(
                x["external_trust_floor_candidate"], authorized=True,
            )),
        ):
            with self.subTest(field=field), self.assertRaises(
                OwnerTrustPreflightDenied,
            ):
                check(x, **{field: payload})

    def test_caller_supplied_witness_id_does_not_prove_independence(self):
        x = test_record()
        r = check(x)
        self.assertEqual(r["repository_name"], OWNER_REPO)
        self.assertFalse(r["owner_witness_proven_independent"])
        self.assertFalse(r["owner_signer_tip_epoch_proven_monotone"])


if __name__ == "__main__":
    unittest.main()
