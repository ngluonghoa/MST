"""§255 hosted-UI review output is entirely fictional and NEVER authorized."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest

from scripts import mst_ui10_fictional_cloud_artifact255 as m


class FictionalUi10CloudArtifact255(unittest.TestCase):
    def _create(self, root):
        folder = Path(root) / "review"
        receipt = m.build_fictional_ui_artifact(folder)
        return folder, receipt

    def test_real_html_is_produced_from_actual_merged_renderer(self):
        with TemporaryDirectory() as td:
            folder, receipt = self._create(td)
            html = (folder / m.HTML_NAME).read_text(encoding="utf-8")
            self.assertTrue(html.startswith('<!doctype html><html lang="vi">'))
            self.assertEqual(html.count('data-ui-section="'), 9)
            self.assertEqual(html.count('data-zone-id="'), 16)
            self.assertEqual(html.count('data-pipeline-step="'), 8)
            self.assertEqual(html.count('data-audit-topic="'), 8)
            for section in "ABCDEFGHI":
                self.assertIn('data-ui-section="' + section + '"', html)
            self.assertIn("INCOMPLETE_REPORT", html)
            self.assertIn("NO_TRADE", html)
            self.assertEqual(receipt["rendered_sections"], list("ABCDEFGHI"))
            self.assertEqual(receipt["zones_unverified"], 16)
            self.assertEqual(receipt["pipeline_steps"], 8)
            self.assertEqual(receipt["audit_topics"], 8)
            self.assertEqual(sha256(html.encode()).hexdigest(),
                             receipt["report_html_sha256"])

    def test_no_fake_prices_or_authentic_data_in_artifact(self):
        with TemporaryDirectory() as td:
            folder, receipt = self._create(td)
            html = (folder / m.HTML_NAME).read_text(encoding="utf-8")
            printable = (
                html + (folder / m.RECEIPT_NAME).read_text(encoding="utf-8")
                + (folder / m.READ_ME_NAME).read_text(encoding="utf-8")
            )
            for fake in m.FAKE_PRICES:
                self.assertNotIn(fake, printable)
            for forbidden in (
                "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
                "MST_SSI_API_SECRET",
                "MST_DNSE_API_SECRET",
                "api.ssi.com.vn",
                "openapi.dnse.com.vn",
                "BUY NOW",
                "AUTO_TRADE",
            ):
                self.assertNotIn(forbidden, printable)
            # The locked report may mention FULL_ANALYSIS only as a DENIAL,
            # never as a successful publication status.
            self.assertNotIn('"publication_state":"FULL_ANALYSIS"', printable)
            self.assertTrue(receipt["input_is_fictional"])
            for gate in (
                "real_provider_data_read", "cloud_secret_read",
                "cloud_vendor_api_requested", "google_drive_accessed",
                "production_cache_head_published",
                "original_16_zone_rules_verified",
                "report_step08_committed", "signals_or_trades_eligible",
            ):
                self.assertFalse(receipt[gate])

    def test_all_six_tf_displayed_but_not_certified(self):
        with TemporaryDirectory() as td:
            _, receipt = self._create(td)
            rows = receipt["required_tf_coverage"]
            self.assertEqual([x["timeframe"] for x in rows],
                             ["M5", "M15", "M30", "H1", "H4", "D1"])
            self.assertEqual([x["status"] for x in rows],
                             ["MISSING"] * 5 + ["D1_REFERENCE_ONLY"])
            self.assertEqual(receipt["source_timeframes_qualified"], 0)
            self.assertTrue(all(x["qualified"] is False for x in rows))

    def test_receipt_matches_disk_and_is_reproducible(self):
        with TemporaryDirectory() as a, TemporaryDirectory() as b:
            fa, ra = self._create(a)
            fb, rb = self._create(b)
            self.assertEqual(ra, rb)
            self.assertEqual(json.loads((fa / m.RECEIPT_NAME).read_text()), ra)
            for name in (m.HTML_NAME, m.RECEIPT_NAME, m.READ_ME_NAME):
                self.assertEqual((fa / name).read_bytes(),
                                 (fb / name).read_bytes())
            self.assertEqual({f.name for f in fa.iterdir()},
                             {m.HTML_NAME, m.RECEIPT_NAME, m.READ_ME_NAME})
            self.assertIn("FICTIONAL SAMPLE",
                          (fa / m.READ_ME_NAME).read_text())

    def test_output_not_overwritten_and_requires_path_type(self):
        with TemporaryDirectory() as td:
            folder, _ = self._create(td)
            with self.assertRaises(FileExistsError):
                m.build_fictional_ui_artifact(folder)
            with self.assertRaisesRegex(ValueError, "EXACT_PATH_REQUIRED"):
                m.build_fictional_ui_artifact(str(Path(td) / "unsafe"))

    def test_fixture_claims_no_publisher_and_is_unrelated_to_real_source(self):
        fake = m.strictly_fictional_source()
        self.assertEqual(fake["symbol"], "ZZZ")
        self.assertEqual(fake["provider"], "SSI")
        self.assertEqual(fake["source_rows_observed"], 2)
        self.assertFalse(fake["issuer_closed_bar_attested"])
        self.assertFalse(fake["signal_eligible"])
        self.assertTrue(fake["not_appowned_github_cache_publisher"])
        self.assertEqual(fake["trade_orders"], 0)
        self.assertEqual(fake["source_origin"],
                         "ChatGPT_MCP_CONNECTOR_PRIVATE_DRIVE")
        self.assertTrue(all(r["symbol"] == "ZZZ"
                            for r in fake["native_source_data"]))

    def test_cloud_review_workflow_is_main_only_zero_credentials(self):
        path = (Path(__file__).resolve().parents[1] /
                ".github/workflows/mst-ui10-fictional-review.yml")
        flow = path.read_text(encoding="utf-8")
        self.assertIn("push:", flow)
        self.assertIn("branches: [main]", flow)
        self.assertIn("permissions:\n  contents: read", flow)
        self.assertIn("persist-credentials: false", flow)
        self.assertIn("python -m scripts.mst_ui10_fictional_cloud_artifact255", flow)
        self.assertIn("actions/upload-artifact@", flow)
        self.assertIn("if-no-files-found: error", flow)
        for banned in (
            "schedule:", "pull_request_target:", "pull_request:",
            "secrets.", "vars.", "curl ", "wget ",
            "pip install", "MST_GDRIVE_OAUTH",
        ):
            self.assertNotIn(banned, flow)
        script = (Path(__file__).resolve().parents[1] /
                  "scripts/mst_ui10_fictional_cloud_artifact255.py").read_text()
        for banned in ("import requests", "import urllib", "import socket",
                       "import subprocess", "os.environ", "session.get",
                       "session.post", "auth/token", "googleapis.com"):
            self.assertNotIn(banned, script)


if __name__ == "__main__":
    unittest.main()
