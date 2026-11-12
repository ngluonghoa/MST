"""Contract-only QA for two real GitHub test-ref readbacks.

All fixtures are invented REST-shaped observations; the live read occurs in a
separate contents:read-only GitHub Actions job. Never authorize trading/Drive.
"""
from copy import deepcopy
import unittest

from scripts.m4_github_parallel_ref_readback import _PARENT, _TRIALS, verify_trial


def fake(trial):
    c = _TRIALS[trial]
    return (
        {"ref": "refs/heads/" + c["branch"],
         "object": {"sha": c["winner"], "type": "commit"}},
        {"sha": c["winner"], "parents": [{"sha": _PARENT}],
         "tree": {"sha": c["winner_tree"]}},
        {"sha": c["loser"], "parents": [{"sha": _PARENT}],
         "tree": {"sha": c["loser_tree"]}},
    )


class ParallelAttemptReadbackContractTests(unittest.TestCase):
    def test_both_trials_validate_only_unattested_git_ref(self):
        for trial in _TRIALS:
            with self.subTest(trial=trial):
                value = verify_trial(trial, *fake(trial))
                self.assertEqual(value["status"],
                    "REMOTE_GITHUB_PARALLEL_ATTEMPT_REF_READBACK_VERIFIED_UNATTESTED")
                self.assertTrue(value["remote_git_ref_read_verified"])
                self.assertEqual(value["shared_parent"], _PARENT)
                for k in (
                    "distributed_multiaccount_cas_proven",
                    "simultaneous_server_arrival_proven",
                    "connector_requests_were_different_authenticated_accounts",
                    "server_http_422_proven_by_readback_alone",
                    "independently_protected_rollback_floor",
                    "real_google_drive_payload_verified",
                    "provider_rights_verified", "trading_authorized",
                ):
                    self.assertIs(value[k], False)

    def test_unknown_trial_denied(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_TEST_TRIAL"):
            verify_trial("r3", *fake("r1"))

    def test_wrong_branch_denied(self):
        a = list(fake("r1"))
        a[0]["ref"] = "refs/heads/main"
        with self.assertRaisesRegex(ValueError, "CROSS_BRANCH"):
            verify_trial("r1", *a)

    def test_unexpected_remote_head_denied(self):
        for bad in (_PARENT, _TRIALS["r1"]["loser"]):
            with self.subTest(bad=bad):
                a = list(fake("r1"))
                a[0]["object"]["sha"] = bad
                with self.assertRaisesRegex(ValueError, "FINAL_HEAD"):
                    verify_trial("r1", *a)

    def test_non_commit_ref_denied(self):
        a = list(fake("r1"))
        a[0]["object"]["type"] = "tag"
        with self.assertRaisesRegex(ValueError, "FINAL_HEAD"):
            verify_trial("r1", *a)

    def test_winner_sha_tamper_denied(self):
        a = list(fake("r1"))
        a[1]["sha"] = _PARENT
        with self.assertRaisesRegex(ValueError, "WINNER_COMMIT"):
            verify_trial("r1", *a)

    def test_losing_sha_tamper_denied(self):
        a = list(fake("r1"))
        a[2]["sha"] = _PARENT
        with self.assertRaisesRegex(ValueError, "LOSER_COMMIT"):
            verify_trial("r1", *a)

    def test_wrong_parent_for_each_sibling_denied(self):
        for trial in _TRIALS:
            for which in (1, 2):
                with self.subTest(trial=trial, which=which):
                    a = list(fake(trial))
                    a[which]["parents"][0]["sha"] = "0" * 40
                    with self.assertRaisesRegex(ValueError, "SINGLE_PARENT"):
                        verify_trial(trial, *a)

    def test_multiple_parents_and_missing_parent_denied(self):
        for x in ([], None, [{"sha": _PARENT}, {"sha": "0" * 40}]):
            with self.subTest(x=x):
                a = list(fake("r2"))
                a[2]["parents"] = x
                with self.assertRaisesRegex(ValueError, "SINGLE_PARENT"):
                    verify_trial("r2", *a)

    def test_winner_or_loser_tree_tamper_denied(self):
        for which in (1, 2):
            with self.subTest(which=which):
                a = list(fake("r2"))
                a[which]["tree"]["sha"] = "0" * 40
                with self.assertRaisesRegex(ValueError, "TREE_SHA"):
                    verify_trial("r2", *a)

    def test_wrong_shape_denied(self):
        for which in range(3):
            with self.subTest(which=which):
                a = list(fake("r2"))
                a[which] = ["not", "a", "git", "object"]
                with self.assertRaises(TypeError):
                    verify_trial("r2", *a)


if __name__ == "__main__":
    unittest.main()
