"""§327 fictional coverage-only fixtures, no actual prices or network."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import unittest

from scripts.mst_connected_m1_dependencies300 import M1DependencyDenied
from scripts.mst_private_tod20_prefix327 import inspect_private_tod20_prefix_coverage

DAYS = tuple(date(2000, 1, 1)+timedelta(days=i) for i in range(21))
CLOCK = datetime(2000, 2, 1, tzinfo=timezone.utc)


def fixture():
    labels = [*range(555, 690), *range(780, 870), 885]
    captures = []
    for day in DAYS:
        rows = [{"symbol": "AAA",
                 "trading_date": f"{day:%d/%m/%Y} {m//60:02d}:{m%60:02d}:00",
                 "open": "100", "high": "110", "low": "90",
                 "close": "100", "volume": "10"}
                for m in reversed(labels)]
        captures.append(dict(day=day, response={"status": "ok", "data": {"ticks": rows}},
                             started=CLOCK, finished=CLOCK+timedelta(seconds=1)))
    return tuple(captures)


def inspect(captures, **kw):
    args = dict(symbol="AAA", target_day=DAYS[-1], prior_days=DAYS[:-1],
                captures=captures)
    args.update(kw)
    return inspect_private_tod20_prefix_coverage(**args)


def group(r, clock="MINUTE_START_UNVERIFIED", tf="M5"):
    return next(g for g in r["groups"] if g["clock"] == clock and g["tf"] == tf)


def remove(capture, stamp):
    ticks = capture["response"]["data"]["ticks"]
    capture["response"]["data"]["ticks"] = [r for r in ticks if not
                                            r["trading_date"].endswith(stamp)]


class PrivateTod20Prefix327(unittest.TestCase):
    def test_complete_start_and_unselected_end_hypotheses(self):
        r = inspect(fixture())
        self.assertEqual(len(r["captures"]), 21)
        self.assertEqual(len(r["groups"]), 6)
        self.assertEqual(group(r)["prefix_21_count"], 45)
        self.assertEqual(group(r, "MINUTE_END_UNVERIFIED")["prefix_21_count"], 26)
        self.assertEqual(group(r, tf="M1")["prefix_21_count"], 225)
        self.assertEqual(group(r, tf="M15")["prefix_21_count"], 15)
        self.assertIsNone(r["clock_selected"])
        self.assertFalse(r["source_first_known_attested"])
        self.assertFalse(r["rvol_calculation_authorized"])
        self.assertFalse(r["signal_eligible"])

    def test_early_missing_label_blocks_later_prefix_not_local_window(self):
        a = fixture()
        remove(a[0], "09:17:00")
        r = group(inspect(a))
        self.assertEqual(r["local_21_count"], 44)
        self.assertEqual(r["prefix_21_count"], 0)
        afternoon = next(s for s in r["slots"] if s["start_minute"] == 780)
        self.assertEqual(afternoon["prior_local_full_count"], 20)
        self.assertEqual(afternoon["prior_prefix_full_count"], 19)
        self.assertTrue(afternoon["local_21_observations"])
        self.assertFalse(afternoon["prefix_21_observations"])

    def test_missing_target_label_not_repaired_from_prior(self):
        a = fixture()
        remove(a[-1], "13:02:00")
        r = group(inspect(a))
        self.assertEqual(r["local_21_count"], 44)
        self.assertEqual(r["prefix_21_count"], 27)
        afternoon = next(s for s in r["slots"] if s["start_minute"] == 785)
        self.assertEqual(afternoon["prior_prefix_full_count"], 20)
        self.assertFalse(afternoon["target_prefix_full"])

    def test_exact_order_and_prior_dates_no_substitution(self):
        a = fixture()
        for dates in (DAYS[:-2], DAYS[1:], (DAYS[0],)*20, DAYS[:-1][::-1]):
            with self.subTest(dates=dates), self.assertRaises(M1DependencyDenied):
                inspect(a, prior_days=dates)
        with self.assertRaises(M1DependencyDenied):
            inspect(a[:-1])
        with self.assertRaises(M1DependencyDenied):
            inspect((a[1], a[0], *a[2:]))

    def test_auction_cannot_repair_prefix_or_change_window_coverage(self):
        a = fixture()
        before = inspect(a)
        remove(a[0], "14:45:00")
        after = inspect(a)
        self.assertEqual(before["groups"], after["groups"])
        self.assertNotEqual(before["coverage_sha256"], after["coverage_sha256"])
        self.assertFalse(after["volume_definition_attested"])

    def test_metadata_only_revision_changes_receipt_not_geometry(self):
        a = fixture()
        b = deepcopy(a)
        b[0]["response"]["data"]["ticks"][0]["avg_price"] = "102"
        old, new = inspect(a), inspect(b)
        self.assertEqual(old["groups"], new["groups"])
        self.assertNotEqual(old["coverage_sha256"], new["coverage_sha256"])
        self.assertFalse(new["production_cache_eligible"])

    def test_empty_or_wrong_symbol_fails_closed(self):
        a = fixture()
        a[0]["response"]["data"]["ticks"] = []
        with self.assertRaises(M1DependencyDenied):
            inspect(a)
        a = fixture()
        a[0]["response"]["data"]["ticks"][0]["symbol"] = "BBB"
        with self.assertRaises(M1DependencyDenied):
            inspect(a)
