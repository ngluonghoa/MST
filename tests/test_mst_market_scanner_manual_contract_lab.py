"""MST Market Scanner negative QA: fictional fixture, zero cloud/provider access."""

import math
from dataclasses import replace
from pathlib import Path
import unittest

from scripts.mst_market_scanner_manual_contract_lab import (
    MAX_SHORTLIST,
    MAX_UNIVERSE_ROWS,
    SCANNER_NAMESPACE,
    WATCHLIST_NAMESPACE,
    ScannerContractError,
    freeze_manual_universe,
    rank_fictional_probe_scores,
    synthetic_demo,
    synthetic_scanner_cache_key,
)


def listing(symbol="MOCKA", venue="HOSE", **changes):
    row = {
        "venue": venue, "symbol": symbol, "first_listed": "2024-01-01",
        "delisted": None, "suspended": False,
    }
    row.update(changes)
    return row


def freeze(**changes):
    args = {
        "trigger": "manual",
        "source_revision": "synthetic-v1",
        "as_of": "2026-11-11",
        "exchanges": ["HOSE", "HNX", "UPCOM"],
        "listings": [listing(), listing("MOCKB", "HNX")],
        "candidate_limit": 2,
    }
    args.update(changes)
    return freeze_manual_universe(**args)


class ManualOnlyUniverseContractTests(unittest.TestCase):
    def assert_denied(self, **kwargs):
        with self.assertRaises(ScannerContractError):
            freeze(**kwargs)

    def test_01_manual_explicit_synthetic_scope(self):
        result = freeze()
        self.assertEqual(len(result.eligible), 2)
        self.assertEqual(result.scanner_cache_namespace, SCANNER_NAMESPACE)

    def test_02_same_revision_different_listing_order_same_digest(self):
        first = freeze()
        second = freeze(listings=list(reversed([listing(), listing("MOCKB", "HNX")])))
        self.assertEqual(first.scan_id, second.scan_id)

    def test_03_revision_changes_digest(self):
        self.assertNotEqual(freeze().scan_id, freeze(source_revision="synthetic-v2").scan_id)

    def test_04_asof_changes_digest(self):
        self.assertNotEqual(freeze().scan_id, freeze(as_of="2026-11-10").scan_id)

    def test_05_exchange_scope_changes_digest(self):
        self.assertNotEqual(freeze().scan_id, freeze(exchanges=["HOSE"]).scan_id)

    def test_06_manual_trigger_required(self):
        self.assert_denied(trigger="schedule")

    def test_07_wildcard_trigger_denied(self):
        self.assert_denied(trigger="*")

    def test_08_automatic_trigger_denied(self):
        self.assert_denied(trigger="automatic")

    def test_09_empty_scope_denied(self):
        self.assert_denied(exchanges=[])

    def test_10_wildcard_exchange_denied(self):
        self.assert_denied(exchanges=["*"])

    def test_11_exchange_string_not_accepted(self):
        self.assert_denied(exchanges="HOSE")

    def test_12_duplicate_exchange_denied(self):
        self.assert_denied(exchanges=["HOSE", "HOSE"])

    def test_13_unknown_exchange_denied(self):
        self.assert_denied(exchanges=["NYSE"])

    def test_14_empty_listing_universe_denied(self):
        self.assert_denied(listings=[])

    def test_15_oversized_listing_universe_denied(self):
        self.assert_denied(listings=[listing()] * 3, max_rows=2)

    def test_16_no_valid_symbols_denied(self):
        self.assert_denied(listings=[listing("MOCKA", suspended=True)])

    def test_17_duplicate_security_denied(self):
        self.assert_denied(listings=[listing(), listing()])

    def test_18_same_symbol_different_venue_denied(self):
        self.assert_denied(listings=[listing(), listing(venue="HNX")])

    def test_19_invalid_symbol_denied(self):
        self.assert_denied(listings=[listing(symbol="../x")])

    def test_20_lowercase_symbol_denied(self):
        self.assert_denied(listings=[listing(symbol="fpt")])

    def test_21_invalid_symbol_length_denied(self):
        self.assert_denied(listings=[listing(symbol="ABCDEFGHI")])

    def test_22_missing_lifecycle_field_denied(self):
        row = listing()
        row.pop("first_listed")
        self.assert_denied(listings=[row])

    def test_23_extra_schema_field_denied(self):
        self.assert_denied(listings=[listing(secret="x")])

    def test_24_non_boolean_suspension_denied(self):
        self.assert_denied(listings=[listing(suspended="false")])

    def test_25_listing_in_future_excluded(self):
        result = freeze(listings=[listing(), listing("MOCKB", "HNX", first_listed="2027-01-01")])
        self.assertEqual([x.symbol for x in result.eligible], ["MOCKA"])

    def test_26_delisted_asof_excluded(self):
        result = freeze(listings=[listing(), listing("MOCKB", "HNX", delisted="2026-11-11")])
        self.assertEqual(len(result.eligible), 1)

    def test_27_suspended_excluded(self):
        result = freeze(listings=[listing(), listing("MOCKB", "HNX", suspended=True)])
        self.assertEqual(result.ignored_count, 1)

    def test_28_invalid_lifecycle_order_denied(self):
        self.assert_denied(listings=[listing(delisted="2023-12-31")])

    def test_29_invalid_lifecycle_date_denied(self):
        self.assert_denied(listings=[listing(first_listed="2026-02-30")])

    def test_30_bad_asof_denied(self):
        self.assert_denied(as_of="11/11/2026")

    def test_31_bad_revision_denied(self):
        self.assert_denied(source_revision="")

    def test_32_candidate_limit_zero_denied(self):
        self.assert_denied(candidate_limit=0)

    def test_33_candidate_limit_above_cap_denied(self):
        self.assert_denied(candidate_limit=MAX_SHORTLIST + 1)

    def test_34_boolean_candidate_limit_denied(self):
        self.assert_denied(candidate_limit=True)

    def test_35_max_rows_above_cap_denied(self):
        self.assert_denied(max_rows=MAX_UNIVERSE_ROWS + 1)

    def test_36_boolean_max_rows_denied(self):
        self.assert_denied(max_rows=True)


class SyntheticCandidateBoundaryTests(unittest.TestCase):
    def test_37_fictional_scores_rank_deterministically(self):
        result = rank_fictional_probe_scores(freeze(), {
            ("HOSE", "MOCKA"): 40, ("HNX", "MOCKB"): 90,
        })
        self.assertEqual([x["symbol"] for x in result], ["MOCKB", "MOCKA"])
        self.assertTrue(all("FICTIONAL" in x["status"] for x in result))

    def test_38_empty_scores_yield_no_candidates(self):
        self.assertEqual(rank_fictional_probe_scores(freeze(), {}), ())

    def test_39_shortlist_bounded(self):
        result = rank_fictional_probe_scores(freeze(candidate_limit=1), {
            ("HOSE", "MOCKA"): 40, ("HNX", "MOCKB"): 90,
        })
        self.assertEqual(len(result), 1)

    def test_40_outside_universe_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "OTHER"): 90})

    def test_41_cross_venue_candidate_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("UPCOM", "MOCKA"): 90})

    def test_42_non_numeric_score_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): "90"})

    def test_43_boolean_score_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): True})

    def test_44_nan_score_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): math.nan})

    def test_45_infinite_score_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): math.inf})

    def test_46_negative_score_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): -1})

    def test_47_score_over_cap_denied(self):
        with self.assertRaises(ScannerContractError):
            rank_fictional_probe_scores(freeze(), {("HOSE", "MOCKA"): 100.01})

    def test_48_ties_use_venue_symbol_order(self):
        ranked = rank_fictional_probe_scores(freeze(), {
            ("HOSE", "MOCKA"): 50, ("HNX", "MOCKB"): 50,
        })
        self.assertEqual([row["venue"] for row in ranked], ["HNX", "HOSE"])

    def test_49_receipt_is_nonprod_and_zero_issuer_access(self):
        receipt = freeze().receipt()
        for field in ("vendor_fetches", "drive_writes", "watchlist_writes"):
            self.assertEqual(receipt[field], 0)
        self.assertFalse(receipt["cloud_access"])
        self.assertFalse(receipt["production_ready"])
        self.assertNotIn("prices", receipt)

    def test_50_demo_uses_only_synthetic_inputs(self):
        result = synthetic_demo()
        self.assertEqual(result["eligible_count"], 2)
        self.assertEqual(result["fictional_candidate_count"], 2)
        self.assertEqual(result["watchlist_writes"], 0)

    def test_51_scanner_and_watchlist_namespaces_not_equal(self):
        self.assertNotEqual(SCANNER_NAMESPACE, WATCHLIST_NAMESPACE)
        self.assertFalse(SCANNER_NAMESPACE.startswith(WATCHLIST_NAMESPACE + "/"))

    def test_52_workflow_has_only_manual_trigger(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/mst-market-scanner-synthetic-manual.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("pull_request:", workflow)

    def test_53_workflow_no_source_or_cloud_identity_permissions(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/mst-market-scanner-synthetic-manual.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("google-github-actions/auth", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("curl ", workflow)

    def test_54_workflow_scoped_to_owner_main_manual(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/mst-market-scanner-synthetic-manual.yml").read_text()
        for guard in (
            "github.repository == 'ngluonghoa/MST'",
            "github.repository_id == '1450356304'",
            "github.repository_owner_id == '353049266'",
            "github.ref == 'refs/heads/main'",
            "github.event_name == 'workflow_dispatch'",
        ):
            self.assertIn(guard, workflow)

    def test_55_workflow_uses_synthetic_test_entrypoint_only(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/mst-market-scanner-synthetic-manual.yml").read_text()
        self.assertIn("--synthetic-self-test", workflow)
        self.assertIn("test_mst_market_scanner_manual_contract_lab.py", workflow)
        self.assertNotIn("mst/watchlist", workflow)


    def test_56_scanner_key_contains_immutable_digest(self):
        frozen = freeze()
        key = synthetic_scanner_cache_key(frozen, "universe")
        self.assertEqual(key, f"{SCANNER_NAMESPACE}/{frozen.scan_id}/universe.json")

    def test_57_scanner_key_is_not_watchlist_path(self):
        key = synthetic_scanner_cache_key(freeze(), "candidates")
        self.assertFalse(key.startswith(WATCHLIST_NAMESPACE + "/"))

    def test_58_scanner_key_rejects_path_traversal(self):
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key(freeze(), "../watchlist")

    def test_59_scanner_key_rejects_unapproved_kind(self):
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key(freeze(), "provider_live_data")

    def test_60_scanner_key_rejects_nonstring_kind(self):
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key(freeze(), None)

    def test_61_scanner_key_rejects_wrong_descriptor(self):
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key({}, "audit")

    def test_62_scanner_key_rejects_forged_namespace(self):
        altered = replace(freeze(), scanner_cache_namespace=WATCHLIST_NAMESPACE)
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key(altered, "audit")

    def test_63_scanner_key_rejects_forged_digest(self):
        altered = replace(freeze(), scan_id="../../watchlist")
        with self.assertRaises(ScannerContractError):
            synthetic_scanner_cache_key(altered, "audit")



if __name__ == "__main__":
    unittest.main()
