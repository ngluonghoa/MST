"""§306 private impact plan: fictional data only, no cache writes."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import unittest

from scripts.mst_connected_m1_dependencies300 import (
    IMPACT_STATES, M1DependencyDenied, plan_private_connected_m1_impact,
)

DAY = date(2020, 1, 17)
START = datetime(2020, 1, 17, 9, tzinfo=timezone.utc)


def fixture():
    rows = [{"symbol": "AAA", "trading_date": f"17/01/2020 09:{m:02}:00",
             "open": "100", "high": "110", "low": "90", "close": "100",
             "volume": "10", "avg_price": "100"}
            for m in reversed(range(15, 31))]
    return {"status": "ok", "data": {"ticks": rows}}


def update(response, minute, field, value):
    for row in response["data"]["ticks"]:
        if row["trading_date"].endswith(f"09:{minute:02}:00"):
            row[field] = value
            return
    raise AssertionError("fixture label missing")


def plan(a, b, **kw):
    args = dict(symbol="AAA", trading_day=DAY, old_started=START,
                old_finished=START+timedelta(seconds=1),
                new_started=START+timedelta(seconds=2),
                new_finished=START+timedelta(seconds=3))
    args.update(kw)
    return plan_private_connected_m1_impact(a, b, **args)


def group(result, clock, tf):
    return next(g for g in result["groups"]
                if g["clock"] == clock and g["tf"] == tf)


class PrivateM1Impact306(unittest.TestCase):
    def test_evidence_and_numeric_boundaries_are_distinct(self):
        a, b = fixture(), fixture()
        update(b, 16, "avg_price", "102")
        update(b, 21, "open", "101")
        r = plan(a, b)
        end = group(r, "MINUTE_END_UNVERIFIED", "M5")
        self.assertEqual(end["earliest_evidence_dirty_candidate_minute"], 555)
        self.assertEqual(end["earliest_numeric_candidate_minute"], 560)
        self.assertEqual(end["counts"]["EVIDENCE_REFRESH_CANDIDATE"], 1)
        self.assertEqual(end["counts"]["NUMERIC_REPLAY_CANDIDATE"], 1)
        start = group(r, "MINUTE_START_UNVERIFIED", "M5")
        self.assertIsNone(start["earliest_numeric_candidate_minute"])
        self.assertEqual(start["counts"]["EVIDENCE_REFRESH_CANDIDATE"], 2)

    def test_partial_unchanged_and_changed_are_never_reusable(self):
        a, b = fixture(), fixture()
        b["data"]["ticks"] = [r for r in b["data"]["ticks"]
                               if not r["trading_date"].endswith("09:17:00")]
        r = plan(a, b)
        start = group(r, "MINUTE_START_UNVERIFIED", "M5")
        self.assertEqual(start["counts"]["INCOMPLETE_CHANGED_REVIEW"], 1)
        self.assertGreater(start["counts"]["INCOMPLETE_UNCHANGED_REVIEW"], 0)
        first = start["windows"][0]
        self.assertIsNone(first["aggregate_changed"])
        self.assertEqual(first["state"], "INCOMPLETE_CHANGED_REVIEW")
        self.assertIsNone(start["earliest_numeric_candidate_minute"])
        self.assertFalse(r["cache_reuse_authorized"])
        self.assertFalse(r["absence_is_deletion"])

    def test_same_content_new_capture_is_not_an_authorized_noop(self):
        a = fixture()
        r = plan(a, deepcopy(a))
        self.assertFalse(r["payload_changed"])
        self.assertNotEqual(r["old_capture_sha256"], r["new_capture_sha256"])
        for g in r["groups"]:
            self.assertIsNone(g["earliest_numeric_candidate_minute"])
            self.assertIsNone(g["earliest_evidence_dirty_candidate_minute"])
            self.assertEqual(sum(g["counts"].values()), g["window_count"])
            self.assertEqual(set(g["counts"]), set(IMPACT_STATES))
        for key in ("cache_reuse_authorized", "cache_invalidation_authorized",
                    "cross_session_replay_authorized", "production_cache_eligible",
                    "source_first_known_attested", "signal_eligible"):
            self.assertIs(r[key], False)
        self.assertIsNone(r["clock_selected"])

    def test_reversion_to_older_values_retains_distinct_capture(self):
        a, b = fixture(), fixture()
        update(b, 16, "open", "101")
        ab = plan(a, b)
        ba = plan(b, a, old_started=START+timedelta(seconds=2),
                  old_finished=START+timedelta(seconds=3),
                  new_started=START+timedelta(seconds=4),
                  new_finished=START+timedelta(seconds=5))
        self.assertEqual(ab["new_capture_sha256"], ba["old_capture_sha256"])
        self.assertNotEqual(ab["old_capture_sha256"], ba["new_capture_sha256"])
        self.assertNotEqual(ab["impact_plan_sha256"], ba["impact_plan_sha256"])
        self.assertTrue(ba["payload_changed"])

    def test_plan_is_bound_to_recomputed_receipt_and_private_hashes(self):
        a, b = fixture(), fixture()
        update(b, 16, "open", "101")
        r = plan(a, b)
        self.assertEqual(r, plan(a, b))
        digest = r.pop("impact_plan_sha256")
        raw = json.dumps(r, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(digest, sha256(raw).hexdigest())
        self.assertNotIn('"open"', raw.decode())
        self.assertNotIn('"avg_price"', raw.decode())
        b["data"]["ticks"][0]["symbol"] = "BBB"
        with self.assertRaises(M1DependencyDenied):
            plan(a, b)

    def test_total_window_count_and_clock_isolation(self):
        a = fixture()
        r = plan(a, a)
        self.assertEqual(len(r["groups"]), 8)
        self.assertEqual(sum(g["window_count"] for g in r["groups"]), 140)
        for g in r["groups"]:
            self.assertIn(g["clock"], ("MINUTE_START_UNVERIFIED", "MINUTE_END_UNVERIFIED"))
            for w in g["windows"]:
                self.assertIn(w["session"], ("AM", "PM"))
                self.assertLess(w["start_minute"], w["end_minute"])
                self.assertNotEqual(w["start_minute"], 885)
