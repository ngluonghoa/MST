"""§199 all-fake GitHub highwater fast-forward proposal safety tests.

No GitHub API mutation, keys, price data, permission or production repo used.
The test-only fake ref implements a *local simulation* of Git's
non-forced fast-forward parent rule; this is NOT proof about a remote repo.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.mst_github_highwater_ref_proposal import (
    COMMIT_SCHEMA, REF_SCHEMA, GithubRefProposalDenied, _hash,
    prepare_github_highwater_ff_proposal, verify_github_highwater_ff_reread,
)
from test_mst_highwater_cas_intent import anchor, prepare, proposed
from test_mst_signed_highwater_diagnostic import snapshots

OWNER_PRIVATE_REPO = "fake-owner/highwater-custody-test"
OLD_SHA = "1" * 40
NEW_A_SHA = "2" * 40
NEW_B_SHA = "3" * 40
TREE_SHA = "4" * 40


def example(*, run="43270010004", request="FAKE_FF_OWNER_REQ_0001",
            sha=NEW_A_SHA):
    _, chain = snapshots()
    old_anchor = anchor(chain)
    checkpoint = proposed(chain, run=run)
    intent = prepare(chain, checkpoint, old_anchor, request_id=request)
    ref = {
        "schema": REF_SCHEMA,
        "repository": OWNER_PRIVATE_REPO,
        "visibility": "private",
        "ref": "refs/heads/highwater/" + intent["series_id"],
        "sha": OLD_SHA,
    }
    commit = {
        "schema": COMMIT_SCHEMA, "sha": sha, "tree_sha": TREE_SHA,
        "parents": [OLD_SHA],
    }
    return chain, old_anchor, checkpoint, intent, ref, commit


def make(intent, old_anchor, ref, commit, expected=OLD_SHA):
    return prepare_github_highwater_ff_proposal(
        prepared_intent=intent,
        original_intent_sha256=intent["intent_sha256"],
        original_anchor=old_anchor,
        observed_ref=ref,
        expected_observed_ref_sha=expected,
        candidate_commit=commit,
    )


def check(proposal, ref, digest=None):
    return verify_github_highwater_ff_reread(
        proposal, originally_prepared_proposal_sha256=(
            digest or proposal["proposal_sha256"]
        ), current_ref_observation=ref,
    )


class FakeFastForwardRef:
    """Test-only one-parent Git DAG simulation, not GitHub API authority."""
    def __init__(self, sha):
        self.sha = sha
        self.writes = 0

    def try_fast_forward(self, candidate, *, force=False):
        if force:
            raise AssertionError("force=True prohibited by §199 contract")
        if (candidate["parents"] != [self.sha]
                or candidate["sha"] == self.sha):
            return False
        self.sha = candidate["sha"]
        self.writes += 1
        return True


class GithubHighwaterRefProposalTests(unittest.TestCase):
    def data(self):
        return example()

    def test_valid_separate_private_single_parent_proposal_is_no_write(self):
        _, a, _, i, ref, commit = self.data()
        p = make(i, a, ref, commit)
        self.assertEqual(p["repository"], OWNER_PRIVATE_REPO)
        self.assertEqual(p["ref"], ref["ref"])
        self.assertEqual(p["expected_parent_sha"], OLD_SHA)
        self.assertEqual(p["proposed_commit_sha"], NEW_A_SHA)
        self.assertEqual(p["proposed_tree_sha"], TREE_SHA)
        self.assertEqual(p["intent_sha256"], i["intent_sha256"])
        self.assertEqual(p["observed_generation"], 3)
        self.assertEqual(p["proposed_generation"], 4)
        self.assertFalse(p["force"])
        for k in ("remote_write_executed", "atomic_cas_independently_proven",
                  "cache_published", "signals_eligible"):
            self.assertFalse(p[k], k)
        self.assertTrue(p["external_owner_controls_required"])

    def test_reread_is_observation_only_and_not_atomic_authority(self):
        _, a, _, i, ref, commit = self.data()
        diagnostic = check(make(i, a, ref, commit), ref)
        self.assertEqual(diagnostic["observed_ref_sha"], OLD_SHA)
        self.assertEqual(diagnostic["proposed_commit_sha"], NEW_A_SHA)
        for k in ("owner_principal_and_permissions_verified",
                  "candidate_commit_body_independently_verified",
                  "remote_fast_forward_update_executed",
                  "monotone_highwater_independently_verified",
                  "atomic_cas_independently_proven",
                  "cache_published", "signals_eligible"):
            self.assertFalse(diagnostic[k], k)

    def test_two_siblings_share_old_parent_then_fake_only_one_wins(self):
        _, a, _, ia, ref, ca = self.data()
        _, _, _, ib, _, cb = example(
            run="43270010005", request="FAKE_FF_OWNER_REQ_0002",
            sha=NEW_B_SHA,
        )
        pa = make(ia, a, ref, ca)
        pb = make(ib, a, ref, cb)
        store = FakeFastForwardRef(OLD_SHA)
        # Both readers observe old ref, neither reread grants atomic CAS.
        check(pa, ref)
        check(pb, ref)
        self.assertTrue(store.try_fast_forward(ca, force=pa["force"]))
        self.assertFalse(store.try_fast_forward(cb, force=pb["force"]))
        self.assertEqual(store.writes, 1)
        moved = dict(ref, sha=store.sha)
        with self.assertRaisesRegex(
            GithubRefProposalDenied, "REF_MOVED_REPREPARE_REQUIRED"
        ):
            check(pb, moved)

    def test_replay_after_lost_ack_does_not_create_second_fake_commit(self):
        _, a, _, i, ref, commit = self.data()
        p = make(i, a, ref, commit)
        store = FakeFastForwardRef(OLD_SHA)
        self.assertTrue(store.try_fast_forward(commit, force=p["force"]))
        self.assertFalse(store.try_fast_forward(commit, force=p["force"]))
        self.assertEqual(store.writes, 1)
        with self.assertRaisesRegex(GithubRefProposalDenied, "REF_MOVED"):
            check(p, dict(ref, sha=store.sha))

    def test_loser_must_use_new_parent_and_new_signed_cas_intent(self):
        chain, a, cp, i, ref, ca = self.data()
        store = FakeFastForwardRef(OLD_SHA)
        pa = make(i, a, ref, ca)
        self.assertTrue(store.try_fast_forward(ca, force=pa["force"]))
        _, _, _, old_loser, _, cb = example(
            run="43270010005", request="FAKE_FF_OWNER_REQ_0002",
            sha=NEW_B_SHA,
        )
        self.assertFalse(store.try_fast_forward(cb))
        moved = dict(ref, sha=store.sha)
        with self.assertRaisesRegex(GithubRefProposalDenied, "REF_HEAD_MISMATCH"):
            make(old_loser, a, moved, cb)
        # A fresh signed successor after winner, new anchor AND a new
        # candidate Git commit with parent=winner are all required.
        new_chain = [*chain, cp]
        from test_mst_highwater_cas_intent import FakeAuthoritativeAtomicStore
        anchor_store = FakeAuthoritativeAtomicStore(a)
        self.assertTrue(anchor_store.atomic_compare_and_swap(i))
        new_anchor = anchor_store.read()
        next_cp = proposed(new_chain, run="43270010006")
        next_intent = prepare(
            new_chain, next_cp, new_anchor,
            request_id="FAKE_FF_OWNER_REQ_0003",
        )
        next_commit = dict(cb, parents=[NEW_A_SHA])
        pnext = make(next_intent, new_anchor, moved, next_commit,
                     expected=NEW_A_SHA)
        self.assertTrue(store.try_fast_forward(next_commit))
        self.assertEqual(store.writes, 2)
        self.assertEqual(pnext["expected_parent_sha"], NEW_A_SHA)
        self.assertEqual(pnext["proposed_generation"], 5)

    def test_never_use_main_repo_or_public_owner_ref(self):
        _, a, _, i, ref, commit = self.data()
        for field, val in (
            ("repository", "ngluonghoa/MST"),
            ("repository", "ngluonghoa/mSt"),
            ("visibility", "public"),
            ("visibility", "internal"),
            ("ref", "refs/heads/main"),
            ("ref", "refs/tags/highwater/" + i["series_id"]),
            ("ref", "refs/heads/highwater/OTHER_FAKE_SERIES"),
        ):
            with self.subTest(field=field, value=val):
                with self.assertRaisesRegex(
                    GithubRefProposalDenied, "REF_SCOPE_INVALID"
                ):
                    make(i, a, dict(ref, **{field: val}), commit)

    def test_invalid_repo_names_and_ref_path_injection(self):
        _, a, _, i, ref, commit = self.data()
        for bad in ("", "bad", "/repo", "owner/repo/extra",
                    "owner/repo\\nadmin", "owner@bad/repo", 42):
            with self.subTest(bad=bad), self.assertRaises(
                GithubRefProposalDenied
            ):
                make(i, a, dict(ref, repository=bad), commit)
        for bad in (None, [], "refs/heads/highwater/../main",
                    "refs/heads/highwater/" + i["series_id"] + "/extra"):
            with self.subTest(bad=bad), self.assertRaises(
                GithubRefProposalDenied
            ):
                make(i, a, dict(ref, ref=bad), commit)

    def test_missing_or_invalid_ref_and_git_sha_fail_closed(self):
        _, a, _, i, ref, commit = self.data()
        for field, val in (
            ("sha", ""),
            ("sha", "0" * 40),
            ("sha", "A" * 40),
            ("sha", True),
            ("sha", None),
            ("schema", "wrong"),
        ):
            with self.subTest(field=field), self.assertRaises(
                GithubRefProposalDenied
            ):
                make(i, a, dict(ref, **{field: val}), commit)
        with self.assertRaisesRegex(GithubRefProposalDenied, "REF_SCHEMA"):
            make(i, a, dict(ref, injected=True), commit)

    def test_second_independently_supplied_ref_pin_is_mandatory(self):
        _, a, _, i, ref, commit = self.data()
        for old in ("5" * 40, "", None, "Z" * 40):
            with self.subTest(old=old), self.assertRaisesRegex(
                GithubRefProposalDenied, "REF_HEAD_MISMATCH"
            ):
                make(i, a, ref, commit, expected=old)

    def test_commit_requires_exactly_one_old_parent(self):
        _, a, _, i, ref, commit = self.data()
        for parents in ([], [OLD_SHA, "5" * 40],
                        ["5" * 40], [NEW_A_SHA], [None], OLD_SHA):
            with self.subTest(parents=parents), self.assertRaisesRegex(
                GithubRefProposalDenied, "NOT_SINGLE_PARENT_SUCCESSOR"
            ):
                make(i, a, ref, dict(commit, parents=parents))
        with self.assertRaisesRegex(GithubRefProposalDenied, "COMMIT_SCHEMA"):
            make(i, a, ref, dict(commit, forced=True))

    def test_commit_identity_and_tree_must_be_strict_sha(self):
        _, a, _, i, ref, commit = self.data()
        for field, val in (
            ("sha", OLD_SHA), ("sha", ""), ("sha", "Z" * 40),
            ("sha", "0" * 40), ("sha", None),
            ("tree_sha", "0" * 40), ("tree_sha", "no-tree"),
            ("tree_sha", True),
        ):
            with self.subTest(field=field, val=val), self.assertRaises(
                GithubRefProposalDenied
            ):
                make(i, a, ref, dict(commit, **{field: val}))

    def test_bad_cas_intent_and_original_fingerprint_are_rejected(self):
        _, a, _, i, ref, commit = self.data()
        with self.assertRaisesRegex(GithubRefProposalDenied, "CAS_INTENT"):
            prepare_github_highwater_ff_proposal(
                prepared_intent=i,
                original_intent_sha256="f" * 64,
                original_anchor=a, observed_ref=ref,
                expected_observed_ref_sha=OLD_SHA,
                candidate_commit=commit,
            )
        changed = deepcopy(a)
        changed["revision"] += 1
        with self.assertRaisesRegex(GithubRefProposalDenied, "CAS_INTENT"):
            prepare_github_highwater_ff_proposal(
                prepared_intent=i,
                original_intent_sha256=i["intent_sha256"],
                original_anchor=changed, observed_ref=ref,
                expected_observed_ref_sha=OLD_SHA,
                candidate_commit=commit,
            )

    def test_reread_fails_on_changed_repo_scope_visibility_and_head(self):
        _, a, _, i, ref, commit = self.data()
        p = make(i, a, ref, commit)
        for field, val in (
            ("sha", "5" * 40),
            ("repository", "different-owner/other-custody"),
            ("ref", "refs/heads/highwater/OTHER_FAKE_SERIES"),
            ("visibility", "public"),
        ):
            with self.subTest(field=field), self.assertRaises(
                GithubRefProposalDenied
            ):
                check(p, dict(ref, **{field: val}))

    def test_proposal_mutations_and_rehashed_replacement_deny(self):
        _, a, _, i, ref, commit = self.data()
        p = make(i, a, ref, commit)
        for field, val in (
            ("force", True), ("force", 0),
            ("remote_write_executed", True),
            ("external_owner_controls_required", False),
            ("atomic_cas_independently_proven", True),
            ("cache_published", True), ("signals_eligible", True),
            ("proposed_commit_sha", "5" * 40),
            ("intent_sha256", "a" * 64),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                GithubRefProposalDenied, "PROPOSAL_INTEGRITY"
            ):
                check(dict(p, **{field: val}), ref, p["proposal_sha256"])
        with self.assertRaisesRegex(
            GithubRefProposalDenied, "PREPARED_PROPOSAL_SCHEMA"
        ):
            check(dict(p, override="false"), ref, p["proposal_sha256"])
        changed = dict(p, proposed_commit_sha="5" * 40)
        changed["proposal_sha256"] = _hash({
            k: v for k, v in changed.items() if k != "proposal_sha256"
        })
        with self.assertRaisesRegex(
            GithubRefProposalDenied, "PREPARED_PROPOSAL_REPLACED"
        ):
            check(changed, ref, p["proposal_sha256"])

    def test_no_browser_cloud_api_or_real_github_owner_ref_is_touched(self):
        _, a, _, i, ref, commit = self.data()
        p = make(i, a, ref, commit)
        self.assertEqual(p["remote_write_executed"], False)
        self.assertEqual(ref["repository"], OWNER_PRIVATE_REPO)
        self.assertFalse(check(p, ref)["remote_fast_forward_update_executed"])


if __name__ == "__main__":
    unittest.main()
