"""§233 synthetic-only main/manual SSI cloud receipt tests, no network."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import mst_ssi_native_cloud_readonly233 as m


def env(**changes):
    x = {
        "GITHUB_REPOSITORY": "ngluonghoa/MST",
        "GITHUB_REPOSITORY_ID": "1450356304",
        "GITHUB_REPOSITORY_OWNER_ID": "353049266",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": m.WORKFLOW_REF,
        "GITHUB_RUN_ATTEMPT": "1",
        "MST_SSI_PROBE_CONFIRM": "READ_SSI_ONLY",
        "MST_MFX_SOURCE_MODE": "ssi-native-readonly",
        "MST_SOURCE_TF": "D1",
        "MST_SSI_READONLY_OWNER_ACCEPTED": "true",
        "MST_SSI_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_SSI_API_KEY": "FAKE_SSI_API_KEY_NOT_VALID",
        "MST_SSI_API_SECRET": "FAKE_SSI_API_SECRET_NOT_VALID",
        "MST_SSI_SYMBOL": "AAA",
        "MST_SSI_FROM_DATE": "2026-11-10",
        "MST_SSI_TO_DATE": "2026-11-12",
    }
    x.update(changes)
    return x


def safe_report(tf="D1", rows=3, pages=1):
    from scripts.mst_mfx_native_timeframes import provider_resolution
    return {
        "provider": "SSI_FASTCONNECT_V3_MARKET_DATA",
        "source_native_tf": tf,
        "provider_resolution": provider_resolution("SSI", tf),
        "native_source_rows_observed": rows,
        "source_pages_verified": pages,
        "source_ohlcv_invariants_verified": True,
        "private_data_stored_to_drive": False,
        "signal_eligible": False,
        "trade_signal_eligible": False,
        "trading_or_broker_calls": 0,
        "source_closed_bar_attestation_proven": False,
        "provider_marketdata_rights_verified": False,
    }


class SsiCloudReadOnly233Tests(unittest.TestCase):
    def test_main_manual_gate_without_network(self):
        m.require_manual_owner_readonly(env())

    def test_deny_fork_pr_schedule_other_branch_or_workflow(self):
        for change in (
            {"GITHUB_REPOSITORY": "someone/MST"},
            {"GITHUB_REPOSITORY_ID": "123"},
            {"GITHUB_REPOSITORY_OWNER_ID": "123"},
            {"GITHUB_REF": "refs/heads/feature"},
            {"GITHUB_EVENT_NAME": "pull_request"},
            {"GITHUB_EVENT_NAME": "schedule"},
            {"GITHUB_WORKFLOW_REF": "fake"},
            {"GITHUB_RUN_ATTEMPT": "2"},
            {"MST_SSI_PROBE_CONFIRM": "NO"},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(
                m.SsiCloudProbeDenied, "OWNER_GATE_REQUIRED"
            ):
                m.require_manual_owner_readonly(env(**change))

    def test_no_trade_mode_or_unapproved_source_rights(self):
        for change in (
            {"MST_MFX_SOURCE_MODE": "ssi-native-quarantine-stage"},
            {"MST_MFX_SOURCE_MODE": "dnse-native-readonly"},
            {"MST_SSI_SOURCE_RIGHTS_CONFIRMED": "false"},
            {"MST_SSI_READONLY_OWNER_ACCEPTED": "false"},
            {"MST_SSI_API_KEY": ""},
            {"MST_SSI_API_SECRET": ""},
            {"MST_SSI_TO_DATE": "2026-01-01"},
            {"MST_SOURCE_TF": "H4"},
        ):
            with self.subTest(change=change), self.assertRaises(
                m.SsiCloudProbeDenied
            ):
                m.require_manual_owner_readonly(env(**change))

    def test_only_bounded_safe_receipt_is_exposed(self):
        source = safe_report()
        source.update(
            {"accessToken": "FAKE_BEARER_NOT_REAL",
             "price_rows": [{"close": 999999}],
             "privateFileId": "FAKE_PRIVATE_ID"},
        )
        with patch.object(m, "read_ssi_native_once", return_value=source) as mock:
            receipt = m.run_probe(object(), env())
        mock.assert_called_once()
        self.assertEqual(receipt["status"],
                         "MST_233_SSI_CLOUD_NATIVE_READONLY_PROBE_PASS")
        self.assertEqual(receipt["source_rows_observed"], 3)
        self.assertFalse(receipt["data_written_to_drive"])
        self.assertFalse(receipt["signals_and_trading_eligible"])
        self.assertNotIn("FAKE_BEARER_NOT_REAL", str(receipt))
        self.assertNotIn("999999", str(receipt))
        self.assertNotIn("FAKE_PRIVATE_ID", str(receipt))

    def test_same_safe_receipt_for_each_supported_tf(self):
        for tf in ("M5", "M15", "M30", "H1", "D1"):
            with self.subTest(tf=tf), patch.object(
                m, "read_ssi_native_once", return_value=safe_report(tf)
            ):
                receipt = m.run_probe(object(), env(MST_SOURCE_TF=tf))
                self.assertEqual(receipt["timeframe"], tf)
                self.assertFalse(receipt["closed_candle_first_known_attested"])
                self.assertFalse(receipt["source_rights_independently_attested"])

    def test_invalid_rows_or_pages_never_produce_pass_receipt(self):
        for report in (
            safe_report(rows=0), safe_report(rows=True),
            safe_report(rows=10000), safe_report(pages=0),
            safe_report(pages=True), safe_report(pages=10),
        ):
            with self.subTest(report=report), self.assertRaisesRegex(
                m.SsiCloudProbeDenied, "INVALID_READONLY_SOURCE_REPORT"
            ):
                m._bounded_receipt(report, env())

    def test_false_data_rights_or_trade_claims_block_report(self):
        for key, bad in (
            ("source_ohlcv_invariants_verified", False),
            ("private_data_stored_to_drive", True),
            ("signal_eligible", True),
            ("trade_signal_eligible", True),
            ("trading_or_broker_calls", 1),
            ("source_closed_bar_attestation_proven", True),
            ("provider_marketdata_rights_verified", True),
            ("provider", "SSI_TRADING_API"),
            ("provider_resolution", "fake"),
        ):
            report = safe_report()
            report[key] = bad
            with self.subTest(key=key), self.assertRaisesRegex(
                m.SsiCloudProbeDenied, "INVALID_READONLY_SOURCE_REPORT"
            ):
                m._bounded_receipt(report, env())

    def test_provider_safe_failure_redacts_untrusted_exception(self):
        from scripts.mst_mfx_ssi_readonly import SsiSourceDenied
        with patch.object(
            m, "read_ssi_native_once",
            side_effect=SsiSourceDenied("FAKE_TOKEN_SHOULD_NOT_PRINT"),
        ):
            with self.assertRaises(m.SsiCloudProbeDenied) as ctx:
                m.run_probe(object(), env())
        self.assertNotIn("FAKE_TOKEN_SHOULD_NOT_PRINT", str(ctx.exception))

    def test_uncategorized_provider_exception_is_fixed_code(self):
        with patch.object(
            m, "read_ssi_native_once", side_effect=RuntimeError("FAKE_SECRET")
        ):
            with self.assertRaisesRegex(
                m.SsiCloudProbeDenied, "SSI_TRANSPORT_FAILED_CLOSED"
            ) as ctx:
                m.run_probe(object(), env())
        self.assertNotIn("FAKE_SECRET", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
