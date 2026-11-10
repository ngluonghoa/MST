"""23 source-boundary-only DNSE REST M5 nextTime tests; all values fabricated."""
from copy import deepcopy
from dataclasses import replace
from unittest import TestCase
from scripts import m2_a03_dnse_rest_m5_backfill_contract_lab as m
from scripts.m2_a03_documented_ohlc_transport_boundary_lab import fabricated, DocumentedTransport

class DnseRestM5NextTimeTests(TestCase):
    def setUp(self):
        self.req,self.pages,self.single=m.fake_fixture()
        self.base=self.req.from_seconds
    def test_01_documented_fields_m5(self):
        x=m.build()["documentation"]
        self.assertEqual(x["resolution"],"5")
        self.assertEqual(x["historical_response_fields"],["t","o","h","l","c","v","nextTime"])
    def test_02_two_fake_pages_three_rows(self):
        r=m.inspect_fake_pages(self.req,self.pages)
        self.assertEqual((r["synthetic_pages_observed"],r["synthetic_rows_observed"]),(2,3))
    def test_03_nexttime_zero_is_not_vendor_firstknown(self):
        r=m.inspect_fake_pages(self.req,self.pages)
        self.assertTrue(r["nexttime_zero_claimed_at_end"])
        self.assertFalse(r["publisher_first_known_history_verified"])
    def test_04_positive_cursor_is_untrusted(self):
        r=m.inspect_fake_pages(self.req,self.pages[:1])
        self.assertEqual(r["remaining_cursor_is_untrusted"],self.base+600)
    def test_05_parallel_array_length_mismatch(self):
        p=deepcopy(self.single);p["v"]=[]
        with self.assertRaisesRegex(ValueError,"PARALLEL_ARRAY"):m.decode_page(p,self.req)
    def test_06_missing_required_field(self):
        p=deepcopy(self.single);p.pop("nextTime")
        with self.assertRaisesRegex(ValueError,"EXACT_DOCUMENTED"):m.decode_page(p,self.req)
    def test_07_millisecond_timestamp_denied(self):
        p=deepcopy(self.single);p["t"]=[self.base*1000]
        with self.assertRaisesRegex(ValueError,"UNIX_SECOND"):m.decode_page(p,self.req)
    def test_08_boolean_timestamp_denied(self):
        p=deepcopy(self.single);p["t"]=[True]
        with self.assertRaisesRegex(ValueError,"UNIX_SECOND"):m.decode_page(p,self.req)
    def test_09_duplicate_timestamp_denied(self):
        p=deepcopy(self.single)
        for k in m.FIELDS:p[k]=p[k]*2
        with self.assertRaisesRegex(ValueError,"STRICTLY_INCREASING"):m.decode_page(p,self.req)
    def test_10_outside_window_bar_rejected(self):
        p=deepcopy(self.single);p["t"]=[self.base-300]
        with self.assertRaisesRegex(ValueError,"UNIX_SECOND"):m.decode_page(p,self.req)
    def test_11_negative_volume_denied(self):
        p=deepcopy(self.single);p["v"]=[-1]
        with self.assertRaisesRegex(ValueError,"NONNEGATIVE"):m.decode_page(p,self.req)
    def test_12_boolean_volume_denied(self):
        p=deepcopy(self.single);p["v"]=[True]
        with self.assertRaisesRegex(ValueError,"NONNEGATIVE"):m.decode_page(p,self.req)
    def test_13_impossible_ohlc_geometry_denied(self):
        p=deepcopy(self.single);p["h"]=[90]
        with self.assertRaisesRegex(ValueError,"GEOMETRY"):m.decode_page(p,self.req)
    def test_14_nonfinite_price_denied(self):
        p=deepcopy(self.single);p["o"]=[float("nan")]
        with self.assertRaisesRegex(ValueError,"FINITE_POSITIVE"):m.decode_page(p,self.req)
    def test_15_no_repeated_cursor(self):
        p=deepcopy(self.single);p["nextTime"]=self.base
        with self.assertRaisesRegex(ValueError,"STUCK_OR_ROLLBACK"):
            m.inspect_fake_pages(self.req,(m.FakePage(self.base,p),))
    def test_16_no_page_after_nexttime_zero(self):
        with self.assertRaisesRegex(ValueError,"NO_NEXTTIME"):
            m.inspect_fake_pages(self.req,(self.pages[0],self.pages[1],self.pages[1]))
    def test_17_wrong_requested_from_denied(self):
        with self.assertRaisesRegex(ValueError,"EXPLICIT_DOCUMENTED_CURSOR"):
            m.inspect_fake_pages(self.req,(replace(self.pages[0],requested_from=self.base+1),))
    def test_18_no_auto_fetch_outside_range(self):
        p=deepcopy(self.single);p["nextTime"]=self.req.to_seconds
        r=m.inspect_fake_pages(self.req,(m.FakePage(self.base,p),))
        self.assertTrue(r["nexttime_outside_window_requires_vendor_semantics"])
        self.assertIsNone(r["remaining_cursor_is_untrusted"])
    def test_19_equal_numeric_ws_rest_not_issuer(self):
        x=m.compare_fake_ws_closed_and_rest(self.single,self.req,fabricated())
        self.assertEqual(x["status"],"IDENTICAL_NUMERIC_SHAPE_NOT_SOURCE_PROOF")
        self.assertFalse(x["closed_m5_issuer_authenticated"])
    def test_20_conflicting_fake_ohlc_quarantined(self):
        p=deepcopy(self.single);p["c"]=[100]
        r=m.compare_fake_ws_closed_and_rest(p,self.req,fabricated())
        self.assertEqual(r["status"],"CONFLICTING_NUMERIC_SHAPE_QUARANTINE")
        self.assertFalse(r["can_emit_signal"])
    def test_21_forming_not_closed(self):
        b=replace(fabricated(),transport=DocumentedTransport.DNSE_WS_FORMING)
        with self.assertRaises(TypeError):
            m.compare_fake_ws_closed_and_rest(self.single,self.req,b)
    def test_22_no_qualified_source_cache_or_trade(self):
        r=m.build()
        self.assertFalse(r["source_lawful_entitlement_verified"])
        self.assertFalse(r["issuer_first_known_or_revision_ledger_verified"])
        self.assertFalse(r["real_drive_market_cache_enabled"])
        self.assertFalse(r["production_or_trading_allowed"])
    def test_23_deterministic_synthetic_checksum(self):
        a=m.build()
        self.assertEqual(a["synthetic_receipt_sha256"],m.build()["synthetic_receipt_sha256"])
        self.assertEqual(len(a["synthetic_receipt_sha256"]),64)
