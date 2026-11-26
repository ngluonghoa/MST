"""§380 private same-input HTML; fictional fixtures, not visual acceptance."""
import re
import unittest

from swing_trading.contracts import Strategy
from swing_trading.baseline_ui10_runtime379 import build_baseline_ui10_runtime
from swing_trading.locked_ui10_binding import LockedUi10Denied
from swing_trading.locked_ui10_renderer import (
    render_baseline_ui10_incomplete_html, render_ui10_incomplete_html,
)
from test_locked_ui10_renderer import GOLDEN, InventoryParser, build
import test_baseline_engine375 as prev


class BaselineUi10Html380Tests(unittest.TestCase):
    def test_locked_semantic_golden_and_counts(self):
        doc = render_baseline_ui10_incomplete_html(prev.b2.model("B2"))
        parser = InventoryParser()
        parser.feed(doc)
        parser.close()
        self.assertEqual(parser.sections, list("ABCDEFGHI"))
        self.assertEqual(parser.heading_text, GOLDEN["section_heading_order"])
        self.assertEqual(parser.zone_rows, [f"B{i}" for i in range(1,9)] +
                         [f"S{i}" for i in range(1,9)])
        self.assertEqual(parser.step_rows, [str(i) for i in range(1,9)])
        self.assertEqual(parser.audit_rows, [str(i) for i in range(1,9)])
        for label in GOLDEN["locked_legend"]:
            self.assertEqual(doc.count(label), 2)
        self.assertEqual(doc.count('scope="col"'), 18)

    def test_real_phase_diagnostics_in_existing_reason_column(self):
        inputs = prev.b2.model("B2", missing_h1=True)
        req = prev.request("B2", prev.b2.config(), Strategy.SHORT)
        doc = render_baseline_ui10_incomplete_html(inputs, requests=(req,))
        row = re.search(r'<tr data-zone-id="B2">.*?</tr>', doc).group()
        self.assertIn("SHORT: R0=GEOMETRY_MATCH_ONLY/", row)
        self.assertIn("R_F=MISSING_INPUT/MISSING_REQUIRED_INPUT", row)
        self.assertIn("SWING: R0=NOT_CONFIGURED/NOT_ROUTED", row)
        self.assertEqual(doc.count('data-zone-id="'), 16)
        self.assertIn("UNVERIFIED", row)

    def test_redacted_fail_closed_deterministic(self):
        inputs = prev.b2.model("B2")
        req = prev.request("B2", prev.b2.config())
        doc = render_baseline_ui10_incomplete_html(inputs, requests=(req,))
        self.assertEqual(doc, render_baseline_ui10_incomplete_html(inputs, requests=(req,)))
        for phrase in GOLDEN["forbidden_promotions"]:
            self.assertNotIn(phrase, doc)
        for phrase in (inputs.instrument_id, "raw_digest", "preview_id", "candidate_epsilon",
                       "D1 (tham khảo riêng tư)", "<script", "<form", "<button", "https://"):
            self.assertNotIn(phrase, doc)
        for phrase in ("INCOMPLETE_REPORT", "NO_TRADE", "M5: NOT_ARMED",
                       "Chưa đo", "script-src &#39;none&#39;", "role=\"alert\"",
                       "role=\"status\"", "@media(max-width:680px)"):
            self.assertIn(phrase, doc)

    def test_both_boundaries_reject_detached_or_wrong_type(self):
        inputs = prev.b2.model("B2")
        runtime = build_baseline_ui10_runtime(inputs)
        with self.assertRaises(TypeError):
            render_baseline_ui10_incomplete_html(runtime)
        with self.assertRaises(TypeError):
            render_baseline_ui10_incomplete_html(build())
        with self.assertRaises(LockedUi10Denied):
            render_ui10_incomplete_html(runtime)

    def test_legacy_d1_source_wording_remains_separate(self):
        for provider in ("SSI", "DNSE", "VCBS"):
            model = build(provider)
            doc = render_ui10_incomplete_html(model)
            self.assertIn("D1 (tham khảo riêng tư)", doc)
            self.assertNotIn("Baseline đa khung", doc)
            self.assertNotIn("NOT_CONFIGURED/NOT_ROUTED", doc)
