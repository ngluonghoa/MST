"""§339 fictional source envelope / interval-boundary tests."""
from copy import deepcopy
from datetime import date, datetime, timezone
import unittest

from scripts.mst_algolab_intraday_scope339 import (
    AlgolabIngressDenied, COLUMNS, SOURCE, UNITS,
    inspect_algolab_stock_intraday,
)

DAY = date(2000, 1, 3)
STARTED = datetime(2000, 1, 4, tzinfo=timezone.utc)


def fixture(interval="1m", labels=("09:15", "09:17", "14:45")):
    return {"status": "ok", "data": {
        "symbol": "AAA", "kind": "stock", "interval": interval,
        "bars": {"columns": list(COLUMNS), "rows": [
            [f"{DAY.isoformat()}T{label}+07:00", 100, 110, 90, 100, 10, 1000]
            for label in labels]}},
        "meta": {"function": "get_price_history", "source": SOURCE,
                 "units": dict(UNITS), "as_of": f"{DAY.isoformat()}T14:45+07:00",
                 "count": len(labels), "next_cursor": None, "truncated": False}}


def inspect(response, **kw):
    args = dict(response=response, symbol="AAA", day=DAY,
                interval=response["data"]["interval"], started=STARTED,
                finished=STARTED)
    args.update(kw)
    return inspect_algolab_stock_intraday(**args)


class AlgolabIntradayScope339(unittest.TestCase):
    def test_sparse_source_is_not_zero_or_qualified(self):
        r = inspect(fixture())
        self.assertEqual(r["observed_bucket_count"], 3)
        self.assertEqual(r["missing_expected_wall_clock_buckets"], 223)
        self.assertEqual(r["source_reported_zero_volume_rows"], 0)
        self.assertFalse(r["missing_is_zero"])
        self.assertFalse(r["native_tf_qualified"])
        self.assertFalse(r["signal_eligible"])
        self.assertFalse(r["source_clock_independently_attested"])

    def test_m5_m15_presence_does_not_prove_coverage(self):
        for tf in ("5m", "15m"):
            r = inspect(fixture(tf, ("09:15", "14:45")))
            self.assertTrue(r["higher_tf_derived_product"])
            self.assertFalse(r["bucket_presence_proves_minute_coverage"])
            self.assertFalse(r["auction_bucket_may_mix_continuous"])

    def test_m30_wall_clock_and_h1_auction_collision(self):
        r = inspect(fixture("30m", ("09:00", "14:30")))
        self.assertTrue(r["session_anchor_incompatible"])
        self.assertTrue(r["auction_bucket_observed"])
        self.assertFalse(r["auction_bucket_may_mix_continuous"])
        r = inspect(fixture("1h", ("09:00", "14:00")))
        self.assertTrue(r["session_anchor_incompatible"])
        self.assertTrue(r["auction_bucket_may_mix_continuous"])
        self.assertFalse(r["production_cache_eligible"])

    def test_daily_or_wrong_declared_basis_rejected(self):
        with self.assertRaises(AlgolabIngressDenied):
            inspect(fixture(), interval="1d")
        r = fixture()
        r["meta"]["units"]["price"] = "ADJUSTED"
        with self.assertRaises(AlgolabIngressDenied):
            inspect(r)

    def test_exact_source_scope_and_no_pagination(self):
        for key, bad in (("source", "SSI"), ("next_cursor", "other"),
                         ("truncated", True), ("count", 0)):
            r = fixture()
            r["meta"][key] = bad
            with self.subTest(key=key), self.assertRaises(AlgolabIngressDenied):
                inspect(r)
        with self.assertRaises(AlgolabIngressDenied):
            inspect(fixture(), symbol="BBB")

    def test_label_scope_and_order(self):
        for labels in (("09:15", "09:15"), ("13:00", "09:15"),
                       ("12:00",), ("14:30",), ("09:00",)):
            with self.subTest(labels=labels), self.assertRaises(AlgolabIngressDenied):
                inspect(fixture(labels=labels))

    def test_future_and_wrong_date_rejected(self):
        with self.assertRaises(AlgolabIngressDenied):
            inspect(fixture(), finished=datetime(2000, 1, 3, tzinfo=timezone.utc),
                    started=datetime(2000, 1, 3, tzinfo=timezone.utc))
        r = fixture()
        r["data"]["bars"]["rows"][0][0] = "2000-01-02T09:15+07:00"
        with self.assertRaises(AlgolabIngressDenied):
            inspect(r)

    def test_ohlcv_validation_and_zero_not_attestation(self):
        r = fixture()
        r["data"]["bars"]["rows"][0][5] = 0
        r["data"]["bars"]["rows"][0][6] = 0
        self.assertEqual(inspect(r)["source_reported_zero_volume_rows"], 1)
        r["data"]["bars"]["rows"][0][5] = True
        with self.assertRaises(AlgolabIngressDenied):
            inspect(r)

    def test_capture_revision_changes_digest(self):
        r = fixture()
        changed = deepcopy(r)
        changed["data"]["bars"]["rows"][0][4] = 101
        self.assertNotEqual(inspect(r)["capture_sha256"],
                            inspect(changed)["capture_sha256"])
        self.assertFalse(inspect(changed)["first_known_attested"])
