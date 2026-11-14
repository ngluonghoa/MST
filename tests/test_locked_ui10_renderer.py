"""Semantic golden + accessibility/negative tests for offline locked UI-1.0.

All provider sources in these tests are invented, not real user source rows.
No HTML/browser rendering engine, screenshot, network or local host used.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
import json
import re
import unittest

from swing_trading.locked_ui10_binding import (
    LockedUi10Denied, LockedUi10DiagnosticViewModel,
    build_private_d1_ui10_diagnostic,
)
from swing_trading.locked_ui10_renderer import render_ui10_incomplete_html
from swing_trading.private_cache_source_bridge import (
    diagnose_private_d1_without_signals,
)
from swing_trading.contracts import Strategy
from test_private_cache_source_bridge import source, NOW

GOLDEN = json.loads(
    (Path(__file__).parent / "golden" /
     "ui10_incomplete_semantics.json").read_text(encoding="utf-8")
)


class InventoryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections=[]
        self.zone_rows=[]
        self.step_rows=[]
        self.audit_rows=[]
        self.heading_text=[]
        self.h2=False
        self.depth=0
        self.all_attrs=[]
        self.text=[]
        self.errors=[]
        self.tags=[]

    def handle_starttag(self,tag,attrs):
        att=dict(attrs)
        self.tags.append(tag)
        self.all_attrs.append((tag,att))
        if tag=="section" and "data-ui-section" in att:
            self.sections.append(att["data-ui-section"])
        if tag=="tr" and "data-zone-id" in att:
            self.zone_rows.append(att["data-zone-id"])
        if tag=="tr" and "data-pipeline-step" in att:
            self.step_rows.append(att["data-pipeline-step"])
        if tag=="tr" and "data-audit-topic" in att:
            self.audit_rows.append(att["data-audit-topic"])
        if tag=="h2":
            self.h2=True

    def handle_endtag(self,tag):
        if tag=="h2":
            self.h2=False

    def handle_data(self,text):
        self.text.append(text)
        if self.h2:
            self.heading_text.append(text)


def build(provider="SSI"):
    d=source(provider)
    short=diagnose_private_d1_without_signals(
        d,strategy=Strategy.SHORT,as_of_utc=NOW)
    swing=diagnose_private_d1_without_signals(
        d,strategy=Strategy.SWING,as_of_utc=NOW)
    return build_private_d1_ui10_diagnostic(
        short,swing,run_id="fake-cloud-run-188",exchange="HOSE")


def scan(provider="SSI"):
    html=render_ui10_incomplete_html(build(provider))
    parser=InventoryParser()
    parser.feed(html)
    parser.close()
    return html,parser


class Ui10IncompleteHtmlTests(unittest.TestCase):
    def test_all_three_private_provider_shapes_generate_same_locked_structure(self):
        for provider in ("SSI","DNSE","VCBS"):
            with self.subTest(provider=provider):
                doc, p=scan(provider)
                self.assertTrue(doc.startswith('<!doctype html><html lang="vi">'))
                self.assertEqual(p.sections,list("ABCDEFGHI"))
                self.assertEqual(p.heading_text,GOLDEN["section_heading_order"])
                self.assertEqual(p.zone_rows,
                                 [f"B{i}" for i in range(1,9)] +
                                 [f"S{i}" for i in range(1,9)])
                self.assertEqual(p.step_rows,[str(i) for i in range(1,9)])
                self.assertEqual(p.audit_rows,[str(i) for i in range(1,9)])
                self.assertEqual(doc.count('data-zone-id="'),16)
                self.assertEqual(doc.count('data-pipeline-step="'),8)
                self.assertEqual(doc.count('data-audit-topic="'),8)
                for phrase in GOLDEN["required_negative"]:
                    self.assertIn(phrase,doc)
                for phrase in GOLDEN["forbidden_promotions"]:
                    self.assertNotIn(phrase,doc)
                self.assertIn('role="alert"',doc)
                self.assertIn('role="status"',doc)
                self.assertIn('<main aria-label="',doc)
                self.assertIn('lang="vi"',doc)
                self.assertIn('content="width=device-width,initial-scale=1"',doc)
                self.assertIn("@media(max-width:680px)",doc)
                self.assertIn(".grid{grid-template-columns:1fr}",doc)
                self.assertIn(":focus-visible",doc)
                self.assertIn("script-src &#39;none&#39;",doc)
                self.assertNotIn("<script",doc)
                self.assertNotIn("https://",doc)
                self.assertNotIn("http://",doc)
                self.assertNotIn("<form",doc)
                self.assertNotIn("<button",doc)
                self.assertNotIn("BUY NOW",doc)
                self.assertNotIn("AUTO_TRADE",doc)

    def test_locked_legend_topics_and_steps_match_frozen_golden(self):
        from swing_trading.locked_ui10_binding import (
            ZONE_LEGEND,PIPELINE_STEPS,AUDIT_TOPICS
        )
        self.assertEqual([x[1] for x in ZONE_LEGEND],GOLDEN["locked_legend"])
        self.assertEqual(list(PIPELINE_STEPS),GOLDEN["pipeline_names"])
        self.assertEqual(list(AUDIT_TOPICS),GOLDEN["audit_names"])
        doc,_=scan()
        for legend in GOLDEN["locked_legend"]:
            self.assertEqual(doc.count(legend),2)
        for step in GOLDEN["pipeline_names"]:
            self.assertIn(step,doc)
        for topic in GOLDEN["audit_names"]:
            self.assertIn(topic,doc)

    def test_determinism_across_repeated_identical_fictional_source(self):
        a,_=scan("DNSE")
        b,_=scan("DNSE")
        self.assertEqual(a,b)
        self.assertEqual(sha256(a.encode()).hexdigest(),
                         sha256(b.encode()).hexdigest())

    def test_no_source_prices_or_real_source_tokens_are_in_html(self):
        doc,_=scan("VCBS")
        for sensitive in ("50500","51000","52000","50750","native_source_data",
                          "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
                          "MST_SSI_API_SECRET","MST_DNSE_API_SECRET",
                          "FIRST_KNOWN_VERIFIED"):
            self.assertNotIn(sensitive,doc)
        self.assertIn("PRIVATE",doc.upper())
        self.assertIn("INCOMPLETE_REPORT",doc)
        self.assertIn("Chưa đo",doc)

    def test_rehashable_mutation_after_model_creation_is_revalidated(self):
        cases=(
            ("source-future",lambda d:d.update(
                publication_state="FULL_ANALYSIS")),
            ("buy",lambda d:d["strategies"]["SHORT"].update(
                decision="BUY",entry="99999",confirmed=True)),
            ("zone",lambda d:d["zone_rows"][0].update(
                status="DETECTED",confirmed=True)),
            ("audit",lambda d:d["audit_topics"][0].update(status="PASS")),
            ("steps",lambda d:d["pipeline_steps"][7].update(
                status="COMPLETE")),
            ("lost",lambda d:d["zone_rows"].pop()),
            ("section-order",lambda d:d["section_ids"].reverse()),
            ("position",lambda d:d.update(
                position_context_status="OPEN_VERIFIED")),
        )
        for name,mutation in cases:
            with self.subTest(case=name):
                valid=build()
                mutation(valid.data)
                with self.assertRaises(LockedUi10Denied):
                    render_ui10_incomplete_html(valid)

    def test_forged_new_digest_of_dangerous_model_is_still_rejected(self):
        model=build()
        bad=deepcopy(model.data)
        bad["report_published"]=True
        serialized=json.dumps(bad,sort_keys=True,separators=(",",":"),
                              ensure_ascii=False,allow_nan=False).encode()
        forgery=sha256(serialized).hexdigest()
        with self.assertRaises(LockedUi10Denied):
            render_ui10_incomplete_html(
                LockedUi10DiagnosticViewModel(bad,forgery)
            )

    def test_typed_model_and_nontrade_outside_flags_enforced(self):
        with self.assertRaises(LockedUi10Denied):
            render_ui10_incomplete_html({"publication_state":"INCOMPLETE_REPORT"})
        valid=build()
        for field in ("all_source_rules_verified","report_published",
                      "user_trade_eligible"):
            with self.subTest(field=field),self.assertRaises(
                LockedUi10Denied
            ):
                render_ui10_incomplete_html(replace(valid,**{field:True}))

    def test_no_external_asset_or_script_required_for_mobile_reading(self):
        page,parser=scan()
        attrs=[(k,a) for k,a in parser.all_attrs if k=="meta"]
        self.assertTrue(any(x.get("http-equiv")=="Content-Security-Policy"
                            for _,x in attrs))
        self.assertEqual(page.count('<section id="section-'),9)
        self.assertEqual(page.count('aria-labelledby="heading-'),9)
        self.assertEqual(page.count('scope="col"'),18)
        self.assertIn('href="#section-A"',page)
        self.assertTrue(all("aria-labelledby" in a for k,a in parser.all_attrs
                            if k=="section"))
        self.assertTrue(all("id" in a for k,a in parser.all_attrs
                            if k=="h2"))
        self.assertEqual(len([t for t in parser.tags if t=="style"]),1)


if __name__=="__main__":
    unittest.main()
