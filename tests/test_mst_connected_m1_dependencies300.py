"""§300 fictional-only connected M1 revision and dependency tests."""
from datetime import date, datetime, timezone, timedelta
from copy import deepcopy
import json
import unittest

from scripts.mst_connected_m1_dependencies300 import (
    compare_private_connected_m1, M1DependencyDenied,
)

DAY = date(2020, 1, 17)
START = datetime(2020, 1, 17, 9, tzinfo=timezone.utc)


def fixture():
    rows = [
        {"symbol": "AAA", "trading_date": f"17/01/2020 09:{m:02}:00",
         "open": "100", "high": "110", "low": "90", "close": "100",
         "volume": "10", "avg_price": "100"}
        for m in reversed(range(15, 26))
    ]
    return {"status": "ok", "data": {"ticks": rows}}


def compare(a, b, **kw):
    args = dict(symbol="AAA", trading_day=DAY, old_started=START,
                old_finished=START+timedelta(seconds=1),
                new_started=START+timedelta(seconds=2),
                new_finished=START+timedelta(seconds=3))
    args.update(kw)
    return compare_private_connected_m1(a, b, **args)


class ConnectedM1Dependencies300(unittest.TestCase):
    def test_retrieval_change_not_content_change(self):
        a = fixture()
        r = compare(a, deepcopy(a))
        self.assertFalse(r["payload_changed"])
        self.assertNotEqual(r["old_capture"]["capture_sha256"],
                            r["new_capture"]["capture_sha256"])
        self.assertFalse(any(w["input_changed"] for w in r["windows"]))
        self.assertEqual(len(r["windows"]), 140)
        self.assertFalse(r["signal_eligible"])

    def test_same_aggregate_can_have_changed_input_dependencies(self):
        a = fixture()
        b = deepcopy(a)
        # 09:17 interior open: aggregate boundary/extrema/volume unchanged.
        b["data"]["ticks"][-3]["open"] = "101"
        r = compare(a, b)
        self.assertTrue(r["payload_changed"])
        self.assertEqual(r["changed_labels"], 1)
        changed = [w for w in r["windows"] if w["input_changed"]]
        self.assertTrue(changed)
        full = [w for w in changed if w["both_full_labels"]]
        self.assertTrue(full)
        self.assertTrue(all(w["aggregate_changed"] is False for w in full))

    def test_boundary_change_differs_by_clock(self):
        a = fixture()
        b = deepcopy(a)
        b["data"]["ticks"][-2]["open"] = "101"  # 09:16 END window opening
        r = compare(a, b)
        changed = [w for w in r["windows"] if w["aggregate_changed"] is True]
        self.assertEqual([(w["clock"], w["tf"]) for w in changed],
                         [("MINUTE_END_UNVERIFIED", "M5")])
        self.assertIsNone(r["clock_selected"])

    def test_missing_labels_are_not_deletion_or_zero(self):
        a = fixture()
        b = deepcopy(a)
        b["data"]["ticks"].pop(-3)
        r = compare(a, b)
        self.assertEqual(r["absent_labels"], 1)
        self.assertFalse(r["absence_is_deletion"])
        self.assertTrue(any(w["input_changed"] and w["aggregate_changed"] is None
                            for w in r["windows"]))

    def test_metadata_only_revision_is_preserved(self):
        a = fixture()
        b = deepcopy(a)
        b["data"]["ticks"][-3]["avg_price"] = "102"
        r = compare(a, b)
        self.assertEqual(r["changed_labels"], 1)
        self.assertTrue(any(w["input_changed"] for w in r["windows"]))
        self.assertFalse(any(w["aggregate_changed"] is True for w in r["windows"]))
        self.assertNotIn('"avg_price"', json.dumps(r))
        self.assertNotIn('"open"', json.dumps(r))

    def test_scope_order_authority_and_field_fail_closed(self):
        a = fixture()
        for field, value in (("symbol", "BBB"), ("trading_date", "18/01/2020 09:25:00"),
                             ("open", "NaN"), ("close", True), ("token", "SECRET"),
                             ("volume", -1)):
            b = deepcopy(a)
            b["data"]["ticks"][0][field] = value
            with self.subTest(field=field), self.assertRaises(M1DependencyDenied):
                compare(a, b)
        with self.assertRaises(M1DependencyDenied):
            compare(a, {"status": "ok", "data": {"ticks": []}})
        with self.assertRaises(M1DependencyDenied):
            compare(a, a, new_started=START)
        with self.assertRaises(M1DependencyDenied):
            compare(a, a, old_started=START.replace(tzinfo=None))

    def test_auction_never_enters_continuous_windows(self):
        a = fixture()
        a["data"]["ticks"].insert(0, {**a["data"]["ticks"][0],
                                    "trading_date": "17/01/2020 14:45:00"})
        b = deepcopy(a)
        b["data"]["ticks"][0]["close"] = "101"
        r = compare(a, b)
        self.assertTrue(r["payload_changed"])
        self.assertEqual(r["changed_labels"], 1)
        self.assertFalse(any(w["input_changed"] for w in r["windows"]))
