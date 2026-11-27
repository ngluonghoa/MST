"""Dynamic Watchlist: 50 fictional, cloud-free, fail-closed contract tests."""

from dataclasses import replace
import math
from pathlib import Path
import unittest

from scripts.mst_dynamic_watchlist_contract_lab import (
    ALLOWED_VENUES,
    MAX_WATCHLIST_ROWS,
    SCANNER_NAMESPACE,
    SHEET_HEADERS,
    WATCHLIST_NAMESPACE,
    WatchSecurity,
    WatchlistContractError,
    freeze_sheet_values,
    plan_incremental_refresh,
    synthetic_example,
)


def snapshot(rows=None, generation=1, revision="fake-revision-one", **extra):
    if rows is None:
        rows = [
            ["MOCKA", "HOSE", "TRUE"],
            ["MOCKB", "HNX", "FALSE"],
            ["MOCKC", "UPCOM", "TRUE"],
        ]
    return freeze_sheet_values(
        headers=SHEET_HEADERS,
        rows=rows,
        source_revision=revision,
        generation=generation,
        **extra,
    )


class SheetSnapshotTests(unittest.TestCase):
    def deny(self, **changes):
        with self.assertRaises(WatchlistContractError):
            snapshot(**changes)

    def test_01_default_three_venue_contract(self):
        s = snapshot()
        self.assertEqual(set(ALLOWED_VENUES), {"HOSE", "HNX", "UPCOM"})
        self.assertEqual(len(s.enabled), 2)

    def test_02_paused_separate_from_enabled(self):
        s = snapshot()
        self.assertEqual(s.paused, (WatchSecurity("HNX", "MOCKB"),))

    def test_03_no_fixed_watchlist_symbols(self):
        s = snapshot(rows=[["FAKEX", "HOSE", "TRUE"]])
        self.assertEqual(s.enabled, (WatchSecurity("HOSE", "FAKEX"),))

    def test_04_empty_watchlist_is_valid(self):
        s = snapshot(rows=[])
        self.assertEqual(s.enabled, ())
        self.assertEqual(s.paused, ())

    def test_05_all_paused_valid(self):
        s = snapshot(rows=[["MOCKA", "HOSE", "FALSE"]])
        self.assertFalse(s.enabled)

    def test_06_normalize_user_casing_and_spaces(self):
        s = snapshot(rows=[[" mocka ", " hose ", " true "]])
        self.assertEqual(s.enabled, (WatchSecurity("HOSE", "MOCKA"),))

    def test_07_ignore_blank_three_cell_row(self):
        s = snapshot(rows=[[" ", "", ""], ["MOCKA", "HOSE", "TRUE"]])
        self.assertEqual(len(s.enabled), 1)

    def test_08_order_independent_membership_digest(self):
        a = snapshot()
        b = snapshot(rows=list(reversed([
            ["MOCKA", "HOSE", "TRUE"], ["MOCKB", "HNX", "FALSE"],
            ["MOCKC", "UPCOM", "TRUE"],
        ])))
        self.assertEqual(a.membership_digest, b.membership_digest)
        self.assertEqual(a.snapshot_digest, b.snapshot_digest)

    def test_09_casing_independent_digest(self):
        a = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        b = snapshot(rows=[["mocka", "hose", "true"]])
        self.assertEqual(a.membership_digest, b.membership_digest)

    def test_10_toggle_changes_membership_digest(self):
        a = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        b = snapshot(rows=[["MOCKA", "HOSE", "FALSE"]])
        self.assertNotEqual(a.membership_digest, b.membership_digest)

    def test_11_generation_changes_snapshot_not_membership(self):
        a = snapshot()
        b = snapshot(generation=2, revision="fake-revision-two")
        self.assertEqual(a.membership_digest, b.membership_digest)
        self.assertNotEqual(a.snapshot_digest, b.snapshot_digest)

    def test_12_missing_header_denied(self):
        with self.assertRaises(WatchlistContractError):
            freeze_sheet_values(headers=[], rows=[], source_revision="fake-rev1", generation=1)

    def test_13_reordered_header_denied(self):
        with self.assertRaises(WatchlistContractError):
            freeze_sheet_values(
                headers=("Exchange", "Symbol", "Enabled"), rows=[],
                source_revision="fake-rev1", generation=1,
            )

    def test_14_extra_header_denied(self):
        with self.assertRaises(WatchlistContractError):
            freeze_sheet_values(
                headers=(*SHEET_HEADERS, "Notes"), rows=[],
                source_revision="fake-rev1", generation=1,
            )

    def test_15_missing_source_revision_denied(self):
        self.deny(revision="")

    def test_16_newline_source_revision_denied(self):
        self.deny(revision="fake-rev\nforged")

    def test_17_invalid_generation_zero_denied(self):
        self.deny(generation=0)

    def test_18_boolean_generation_denied(self):
        self.deny(generation=True)

    def test_19_fractional_generation_denied(self):
        self.deny(generation=1.1)

    def test_20_oversized_rows_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", "TRUE"]]*3, max_rows=2)

    def test_21_max_rows_above_global_limit_denied(self):
        self.deny(max_rows=MAX_WATCHLIST_ROWS+1)

    def test_22_boolean_max_rows_denied(self):
        self.deny(max_rows=True)

    def test_23_duplicate_row_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", "TRUE"], ["MOCKA", "HOSE", "TRUE"]])

    def test_24_cross_exchange_symbol_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", "TRUE"], ["MOCKA", "HNX", "FALSE"]])

    def test_25_duplicate_casing_denied(self):
        self.deny(rows=[["mocka", "HOSE", "TRUE"], ["MOCKA", "HOSE", "TRUE"]])

    def test_26_invalid_wildcard_symbol_denied(self):
        self.deny(rows=[["*", "HOSE", "TRUE"]])

    def test_27_invalid_symbol_traversal_denied(self):
        self.deny(rows=[["../STOCKS", "HOSE", "TRUE"]])

    def test_28_invalid_symbol_formula_denied(self):
        self.deny(rows=[["=IMPORTXML()", "HOSE", "TRUE"]])

    def test_29_invalid_symbol_whitespace_denied(self):
        self.deny(rows=[["MOCK A", "HOSE", "TRUE"]])

    def test_30_unrecognized_venue_denied(self):
        self.deny(rows=[["MOCKA", "VNX", "TRUE"]])

    def test_31_venue_wildcard_denied(self):
        self.deny(rows=[["MOCKA", "*", "TRUE"]])

    def test_32_missing_enabled_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", ""]])

    def test_33_arbitrary_enabled_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", "YES"]])

    def test_34_boolean_enabled_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", True]])

    def test_35_short_row_denied(self):
        self.deny(rows=[["MOCKA", "HOSE"]])

    def test_36_row_with_extra_column_denied(self):
        self.deny(rows=[["MOCKA", "HOSE", "TRUE", "unknown"]])

    def test_37_bad_row_container_denied(self):
        self.deny(rows=["MOCKA,HOSE,TRUE"])

    def test_38_bad_rows_container_denied(self):
        self.deny(rows="MOCKA,HOSE,TRUE")

    def test_39_receipt_never_claims_production(self):
        r = snapshot().public_safety_receipt()
        self.assertFalse(r["production_ready"])
        for k in ("provider_requests", "drive_reads", "drive_writes", "scanner_cache_writes"):
            self.assertEqual(r[k], 0)
        self.assertNotIn("symbols", r)

    def test_40_watchlist_namespace_not_scanner_namespace(self):
        self.assertNotEqual(WATCHLIST_NAMESPACE, SCANNER_NAMESPACE)
        self.assertFalse(WATCHLIST_NAMESPACE.startswith(SCANNER_NAMESPACE + "/"))


class IncrementalControlPlaneTests(unittest.TestCase):
    def test_41_first_run_bootstraps_only_enabled(self):
        p = plan_incremental_refresh(prior=None, current=snapshot())
        self.assertEqual(len(p.to_start), 2)
        self.assertEqual(len(p.to_continue), 0)

    def test_42_unchanged_revision_is_idempotent(self):
        old = snapshot()
        p = plan_incremental_refresh(prior=old, current=old)
        self.assertEqual(len(p.to_start), 0)
        self.assertEqual(len(p.to_continue), 2)

    def test_43_new_symbol_only_is_started(self):
        old = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        new = snapshot(rows=[["MOCKA", "HOSE", "TRUE"], ["MOCKB", "HNX", "TRUE"]],
                       generation=2, revision="fake-revision-two")
        p = plan_incremental_refresh(prior=old, current=new)
        self.assertEqual(p.to_start, (WatchSecurity("HNX", "MOCKB"),))
        self.assertEqual(p.to_continue, (WatchSecurity("HOSE", "MOCKA"),))

    def test_44_pause_stops_refresh_without_deleting_cache(self):
        old = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        new = snapshot(rows=[["MOCKA", "HOSE", "FALSE"]],
                       generation=2, revision="fake-revision-two")
        p = plan_incremental_refresh(prior=old, current=new)
        self.assertEqual(p.stopped_by_pause, (WatchSecurity("HOSE", "MOCKA"),))
        self.assertFalse(p.stopped_by_removal)
        self.assertFalse(hasattr(p, "delete_cache"))

    def test_45_removal_stops_refresh_without_deleting_cache(self):
        old = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        new = snapshot(rows=[], generation=2, revision="fake-revision-two")
        p = plan_incremental_refresh(prior=old, current=new)
        self.assertEqual(p.stopped_by_removal, (WatchSecurity("HOSE", "MOCKA"),))
        self.assertFalse(p.stopped_by_pause)

    def test_46_resume_starts_only_resumed_symbol(self):
        old = snapshot(rows=[["MOCKA", "HOSE", "FALSE"]])
        new = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]],
                       generation=2, revision="fake-revision-two")
        p = plan_incremental_refresh(prior=old, current=new)
        self.assertEqual(p.to_start, (WatchSecurity("HOSE", "MOCKA"),))

    def test_47_same_generation_changed_membership_denied(self):
        old = snapshot(rows=[["MOCKA", "HOSE", "TRUE"]])
        new = snapshot(rows=[["MOCKA", "HOSE", "FALSE"]])
        with self.assertRaises(WatchlistContractError):
            plan_incremental_refresh(prior=old, current=new)

    def test_48_lower_generation_rollback_denied(self):
        old = snapshot(generation=2, revision="fake-revision-two")
        new = snapshot(generation=1, revision="fake-revision-one")
        with self.assertRaises(WatchlistContractError):
            plan_incremental_refresh(prior=old, current=new)

    def test_49_same_generation_different_source_revision_denied(self):
        old = snapshot()
        new = snapshot(revision="fake-revision-two")
        with self.assertRaises(WatchlistContractError):
            plan_incremental_refresh(prior=old, current=new)

    def test_50_no_mutation_of_original_snapshot(self):
        old = snapshot()
        p = plan_incremental_refresh(prior=old, current=snapshot(
            rows=[["MOCKC", "UPCOM", "TRUE"]], generation=2,
            revision="fake-revision-two",
        ))
        self.assertEqual(len(old.enabled), 2)
        self.assertEqual(len(p.to_stop), 1)

    def test_51_rejects_forged_scanner_namespace(self):
        current = replace(snapshot(), namespace=SCANNER_NAMESPACE)
        with self.assertRaises(WatchlistContractError):
            plan_incremental_refresh(prior=None, current=current)

    def test_52_rejects_forged_prior_namespace(self):
        old = replace(snapshot(), namespace=SCANNER_NAMESPACE)
        with self.assertRaises(WatchlistContractError):
            plan_incremental_refresh(prior=old, current=snapshot(generation=2))

    def test_53_fictional_synthetic_demo_safe(self):
        r = synthetic_example()
        self.assertEqual(r["plan_counts"]["start"], 1)
        self.assertEqual(r["plan_counts"]["paused"], 1)
        self.assertEqual(r["provider_requests"], 0)

    def test_54_source_has_no_cloud_or_provider_imports(self):
        source = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_dynamic_watchlist_contract_lab.py").read_text()
        for forbidden in (
            "import requests", "import httpx", "from google", "import boto3",
            "import subprocess", "import urllib", "def fetch_", "def write_cache",
            "github_actions.dispatch", "market_scanner",
        ):
            self.assertNotIn(forbidden, source)

    def test_55_delta_is_only_scheduling_not_network(self):
        new = snapshot(rows=[], generation=2, revision="fake-revision-two")
        p = plan_incremental_refresh(prior=snapshot(), current=new)
        self.assertEqual(p.safe_counts()["start"], 0)
        self.assertEqual(p.safe_counts()["stop"], 2)
        self.assertFalse(hasattr(p, "api_calls"))


if __name__ == "__main__":
    unittest.main()
