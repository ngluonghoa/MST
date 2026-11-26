"""Fictional, bounded cursor and clock regression tests."""
from copy import deepcopy
from datetime import date
import json
import unittest

from scripts.mst_algolab_intraday_cursor364 import inspect_algolab_m1_cursor_chain
from scripts.mst_algolab_intraday_scope339 import SOURCE, COLUMNS, UNITS, AlgolabIngressDenied

DAYS = (date(2000, 1, 3), date(2000, 1, 4))
BASE = dict(symbol="FPT", interval="1m", from_date="2000-01-03",
            to_date="2000-01-04", limit=2)


def fixture():
    def page(day, cursor, next_cursor, start, finish):
        req = dict(BASE)
        if cursor is not None:
            req["cursor"] = cursor
        rows = [[f"{day}T09:15+07:00", 10, 12, 9, 11, 3, 33],
                [f"{day}T09:16+07:00", 11, 12, 10, 11, 2, 23]]
        return {
            "request": req, "retrievalStartedUtc": start, "retrievalFinishedUtc": finish,
            "response": {"status": "ok", "data": {
                "symbol": "FPT", "kind": "stock", "interval": "1m",
                "bars": {"columns": list(COLUMNS), "rows": rows}},
                "meta": {"function": "get_price_history", "source": SOURCE,
                         "units": dict(UNITS), "truncated": False, "count": 2,
                         "next_cursor": next_cursor, "as_of": rows[-1][0]}},
        }
    return (page("2000-01-04", None, "opaque-fictional-cursor",
                 "2000-01-05T01:00:00Z", "2000-01-05T01:00:01Z"),
            page("2000-01-03", "opaque-fictional-cursor", None,
                 "2000-01-05T01:00:01Z", "2000-01-05T01:00:02Z"))


def inspect(pages=None, **kw):
    args = dict(symbol="FPT", observed_days=DAYS, limit=2,
                pages=fixture() if pages is None else pages)
    args.update(kw)
    return inspect_algolab_m1_cursor_chain(**args)


class CursorChain364Tests(unittest.TestCase):
    def test_exhausted_chain_keeps_asof_separate_and_redacts(self):
        result = inspect()
        self.assertEqual(result["observed_row_count"], 4)
        self.assertEqual(result["close_times_volume_equal_count"], 2)
        self.assertEqual(result["missing_continuous_label_count"], 446)
        self.assertTrue(result["cursor_exhausted"])
        self.assertTrue(result["page_as_of_equals_last_row"])
        for flag in ("historical_first_known_attested", "page_as_of_is_retrieval_clock",
                     "official_calendar_attested", "minute_coverage_attested",
                     "raw_matched_volume_independently_attested", "exact_turnover_attested",
                     "immutable_provider_snapshot_attested", "source_rights_attested",
                     "production_cache_eligible", "signal_eligible"):
            self.assertFalse(result[flag])
        self.assertNotIn("opaque-fictional-cursor", json.dumps(result))
        self.assertNotIn("2000-01-04", json.dumps(result))

    def test_truncation_and_unexhausted_cursor_denied(self):
        p = fixture()
        with self.assertRaisesRegex(AlgolabIngressDenied, "CURSOR_NOT_EXHAUSTED"):
            inspect(p[:1])
        p[0]["response"]["meta"]["truncated"] = True
        with self.assertRaisesRegex(AlgolabIngressDenied, "SOURCE_PRODUCT"):
            inspect(p)

    def test_cursor_scope_change_and_cycle_denied(self):
        p = fixture()
        p[1]["request"]["cursor"] = "wrong"
        with self.assertRaisesRegex(AlgolabIngressDenied, "REQUEST_CHAIN"):
            inspect(p)
        p = fixture()
        p[1]["response"]["meta"]["next_cursor"] = p[0]["response"]["meta"]["next_cursor"]
        with self.assertRaisesRegex(AlgolabIngressDenied, "CURSOR_CYCLE"):
            inspect(p)

    def test_no_page_after_exhaustion(self):
        p = fixture()
        p[0]["response"]["meta"]["next_cursor"] = None
        with self.assertRaisesRegex(AlgolabIngressDenied, "PAGE_AFTER_EXHAUSTION"):
            inspect(p)

    def test_duplicate_and_reordered_rows_denied(self):
        p = fixture()
        p[1]["response"]["data"]["bars"]["rows"][0] = deepcopy(
            p[0]["response"]["data"]["bars"]["rows"][0])
        with self.assertRaisesRegex(AlgolabIngressDenied, "DUPLICATE_LABEL"):
            inspect(p)
        p = fixture()
        p[1]["response"]["data"]["bars"]["rows"].reverse()
        with self.assertRaisesRegex(AlgolabIngressDenied, "PAGE_ROW_ORDER"):
            inspect(p)

    def test_wrong_asof_is_not_a_clock_or_page_boundary(self):
        p = fixture()
        p[1]["response"]["meta"]["as_of"] = p[0]["response"]["meta"]["as_of"]
        with self.assertRaisesRegex(AlgolabIngressDenied, "PAGE_AS_OF_NOT_LAST_ROW"):
            inspect(p)

    def test_capture_clock_overlap_and_naive_denied(self):
        p = fixture()
        p[1]["retrievalStartedUtc"] = "2000-01-05T01:00:00Z"
        with self.assertRaisesRegex(AlgolabIngressDenied, "CAPTURE_ORDER"):
            inspect(p)
        p = fixture()
        p[0]["retrievalStartedUtc"] = "2000-01-05T01:00:00"
        with self.assertRaisesRegex(AlgolabIngressDenied, "CAPTURE_CLOCK"):
            inspect(p)

    def test_date_scope_and_nontrading_label_denied(self):
        p = fixture()
        p[1]["response"]["data"]["bars"]["rows"][0][0] = "2000-01-02T09:15+07:00"
        with self.assertRaisesRegex(AlgolabIngressDenied, "UNEXPECTED_OBSERVED_DATE"):
            inspect(p)
        p = fixture()
        p[1]["response"]["data"]["bars"]["rows"][0][0] = "2000-01-03T12:00+07:00"
        with self.assertRaisesRegex(AlgolabIngressDenied, "ROW_SESSION_OR_FUTURE"):
            inspect(p)

    def test_mutable_pages_and_wrong_request_limit_denied(self):
        with self.assertRaisesRegex(AlgolabIngressDenied, "IMMUTABLE_BOUNDED_PAGES"):
            inspect(list(fixture()))
        p = fixture()
        p[1]["request"]["limit"] = 2.0
        with self.assertRaisesRegex(AlgolabIngressDenied, "REQUEST_CHAIN"):
            inspect(p)
