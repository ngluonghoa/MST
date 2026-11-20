"""MST §247 fiction-only owner-private GitHub FF candidate, NO API write."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from scripts import mst_github_highwater_ref_proposal as g
from test_mst_highwater_cas_intent import examples, prepare

OLD = "1"*40
NEW = "2"*40
TREE = "3"*40
PRIVATE_REPO = "fake-owner/private-highwater"


def observed(*, repo=PRIVATE_REPO, visibility="private", sha=OLD,
             series="FPT_D1_SSI_FAKE"):
    return {
        "schema": g.REF_SCHEMA, "repository": repo,
        "visibility": visibility, "ref": "refs/heads/highwater/"+series,
        "sha": sha,
    }


def commit(*, sha=NEW, parent=OLD, tree=TREE):
    return {
        "schema": g.COMMIT_SCHEMA, "sha": sha,
        "parents": [parent], "tree_sha": tree,
    }


def proposal(*, ref=None, head=None, intent=None, anchor=None,
             old_sha=OLD, original_intent_sha=None):
    _,_,prior=examples()
    current=prior if anchor is None else anchor
    ready=prepare() if intent is None else intent
    expected=(ready["intent_sha256"] if original_intent_sha is None
              else original_intent_sha)
    return g.prepare_github_highwater_ff_proposal(
        prepared_intent=ready,
        original_intent_sha256=expected,
        original_anchor=current,
        observed_ref=observed() if ref is None else ref,
        expected_observed_ref_sha=old_sha,
        candidate_commit=commit() if head is None else head,
    )


class GithubHighwaterRefNoWrite247(unittest.TestCase):
    def test_source_locked_ff_proposal_is_never_remote_write(self):
        p=proposal()
        self.assertEqual(p["schema"], g.PROPOSAL_SCHEMA)
        self.assertEqual(p["repository"], PRIVATE_REPO)
        self.assertEqual(p["ref"], "refs/heads/highwater/FPT_D1_SSI_FAKE")
        self.assertEqual(p["expected_parent_sha"], OLD)
        self.assertEqual(p["proposed_commit_sha"], NEW)
        self.assertEqual(p["proposed_tree_sha"], TREE)
        self.assertFalse(p["force"])
        self.assertTrue(p["external_owner_controls_required"])
        for flag in (
            "remote_write_executed", "atomic_cas_independently_proven",
            "cache_published", "signals_eligible",
        ):
            self.assertIs(p[flag], False)
        self.assertEqual(
            p["proposal_sha256"],
            g._hash({k:v for k,v in p.items() if k!="proposal_sha256"})
        )
        checked=g.verify_github_highwater_ff_reread(
            p, originally_prepared_proposal_sha256=p["proposal_sha256"],
            current_ref_observation=observed(),
        )
        self.assertIs(checked["remote_fast_forward_update_executed"],False)
        self.assertIs(checked["monotone_highwater_independently_verified"],False)
        self.assertIs(checked["atomic_cas_independently_proven"],False)

    def test_deterministic_prepare_identical_fictional_inputs(self):
        self.assertEqual(proposal(),proposal())

    def test_public_mst_repo_cannot_host_independent_ref(self):
        for repo in ("ngluonghoa/MST", "ngluonghoa/mst", "not-legal//", "", True):
            with self.subTest(repo=repo),self.assertRaises(g.GithubRefProposalDenied):
                proposal(ref=observed(repo=repo))

    def test_public_repo_or_wrong_ref_scope_denied(self):
        variants=[
            observed(visibility="public"),
            observed(visibility="internal"),
            observed(series="OTHER_SERIES_1"),
            observed(sha="0"*40),
        ]
        for item in variants:
            with self.subTest(item=item),self.assertRaises(g.GithubRefProposalDenied):
                proposal(ref=item)

    def test_bad_ancestor_or_merge_commit_denied(self):
        for entry in (
            commit(parent="4"*40),
            {**commit(),"parents":[OLD,"5"*40]},
            {**commit(),"parents":[]},
            commit(sha=OLD),
            commit(sha="0"*40),
            commit(tree="0"*40),
        ):
            with self.subTest(entry=entry),self.assertRaisesRegex(
                g.GithubRefProposalDenied, "NOT_SINGLE_PARENT_SUCCESSOR"
            ):
                proposal(head=entry)

    def test_wrong_expected_old_sha_rejected(self):
        with self.assertRaisesRegex(
            g.GithubRefProposalDenied,"OBSERVED_REF_HEAD_MISMATCH"
        ):
            proposal(old_sha="5"*40)

    def test_prior_signed_intent_not_resealed_around_modified_anchor(self):
        p=prepare()
        original=p["intent_sha256"]
        bad=deepcopy(p)
        bad["signals_eligible"]=True
        with self.assertRaisesRegex(g.GithubRefProposalDenied,"CAS_INTENT_UNVERIFIED"):
            proposal(intent=bad,original_intent_sha=original)

    def test_missing_or_extra_observation_fields_denied(self):
        for key,value in (
            ("schema","invalid"),("ref","refs/tags/test"),
            ("visibility","private"),
        ):
            bad=observed()
            bad[key]=value
            if key=="visibility":
                bad["junk"]="extra"
            with self.subTest(key=key),self.assertRaises(g.GithubRefProposalDenied):
                proposal(ref=bad)

    def test_proposal_pinned_hash_prevents_mutated_field(self):
        p=proposal()
        for key,value in (
            ("force",True),("cache_published",True),
            ("remote_write_executed",True),
            ("atomic_cas_independently_proven",True),
            ("signals_eligible",True),
            ("expected_parent_sha","f"*40),
            ("proposed_commit_sha","f"*40),
        ):
            bad=deepcopy(p)
            bad[key]=value
            with self.subTest(key=key),self.assertRaises(g.GithubRefProposalDenied):
                g.verify_github_highwater_ff_reread(
                    bad,
                    originally_prepared_proposal_sha256=p["proposal_sha256"],
                    current_ref_observation=observed(),
                )

    def test_changed_ref_even_if_proposal_unchanged_fails_closed(self):
        p=proposal()
        with self.assertRaisesRegex(
            g.GithubRefProposalDenied,"REF_MOVED_REPREPARE_REQUIRED"
        ):
            g.verify_github_highwater_ff_reread(
                p,
                originally_prepared_proposal_sha256=p["proposal_sha256"],
                current_ref_observation=observed(sha="5"*40),
            )

    def test_private_repos_are_not_authenticated_by_supplied_records(self):
        p=proposal()
        receipt=g.verify_github_highwater_ff_reread(
            p,originally_prepared_proposal_sha256=p["proposal_sha256"],
            current_ref_observation=observed(),
        )
        for flag in (
            "owner_principal_and_permissions_verified",
            "candidate_commit_body_independently_verified",
            "remote_fast_forward_update_executed",
            "monotone_highwater_independently_verified",
            "atomic_cas_independently_proven",
            "cache_published", "signals_eligible",
        ):
            self.assertIs(receipt[flag],False)

    def test_fake_external_store_could_show_same_stale_ref_to_two_writers(self):
        a=proposal()
        b=proposal()
        for candidate in (a,b):
            check=g.verify_github_highwater_ff_reread(
                candidate,originally_prepared_proposal_sha256=candidate["proposal_sha256"],
                current_ref_observation=observed(),
            )
            self.assertFalse(check["atomic_cas_independently_proven"])

    def test_no_external_transport_or_write_in_module(self):
        src=(Path(__file__).resolve().parents[1] /
             "scripts/mst_github_highwater_ref_proposal.py").read_text()
        for forbidden in (
            "requests.patch(", "urlopen(", "GithubClient", "update_ref(",
            "os.environ", "subprocess.", "session.post(", "MST_SEND_ORDER",
        ):
            self.assertNotIn(forbidden, src)


if __name__=="__main__":
    unittest.main()
