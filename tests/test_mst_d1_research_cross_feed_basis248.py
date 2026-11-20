"""§248 fictional MCP D1 cross-feed comparison, zero provider/network calls."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import unittest

from scripts.mst_d1_research_cross_feed_basis248 import (
    BasisAuditDenied, assess_three_source_d1_candidate,
)


def fixtures():
    # Fictional unit-safe prices, not a real ticker or investment advice.
    return [
        {
            "source": "SSI_MCP_COMPACT_D1",
            "symbol": "FPT",
            "session_date": "2026-11-19",
            "close": "25000",
            "volume": "1500",
            "price_unit": "VND",
            "price_basis": "raw",
            "volume_scope": "matched",
            "record_origin": "historical",
        },
        {
            "source": "DNSE_MCP_DAILY_HISTORY",
            "symbol": "FPT",
            "session_date": "2026-11-19",
            "close": 25.0,
            "volume": 1500,
            "price_unit": "THOUSAND_VND",
            "price_basis": "raw",
            "volume_scope": "matched",
            "record_origin": "historical",
        },
        {
            "source": "VCBS_MCP_HISTORY_D1",
            "symbol": "FPT",
            "session_date": "2026-11-19",
            "close": 25000,
            "volume": 1500,
            "price_unit": "VND",
            "price_basis": "raw",
            "volume_scope": "matched",
            "record_origin": "historical",
        },
    ]


def evaluate(items=None):
    return assess_three_source_d1_candidate(
        fixtures() if items is None else items
    )


class ResearchMcpCrossFeed248(unittest.TestCase):
    def test_three_sources_same_canonical_close_remain_no_trade(self):
        r = evaluate()
        self.assertEqual(r["source_count"], 3)
        self.assertTrue(r["source_units_explicitly_normalized_to_vnd"])
        self.assertTrue(r["price_basis_aligned"])
        self.assertTrue(r["matched_close_after_unit_conversion"])
        self.assertTrue(r["volume_scope_aligned"])
        self.assertTrue(r["matched_volume_only_when_scope_aligned"])
        self.assertTrue(r["all_records_claim_historical_origin"])
        self.assertIn("INDEPENDENT_SOURCE_RIGHTS_AND_FINALITY_NOT_ESTABLISHED",r["block_reasons"])
        self.assertEqual(r["status"],"OBSERVED_UNVERIFIED_NO_TRADE")
        for key in (
            "fastconnect_v3_gitHub_cloud_access_proven",
            "source_retention_rights_independently_attested",
            "source_first_known_or_venue_finality_verified",
            "corporate_action_adjustment_crosschecked",
            "safe_to_publish_cache_head","signals_or_trades_eligible",
        ):
            self.assertFalse(r[key])
        public=json.dumps(r)
        self.assertNotIn("25000",public)
        self.assertNotIn("1500",public)

    def test_dnse_thousand_vnd_requires_explicit_conversion(self):
        items=fixtures()
        items[1]["price_unit"]="VND"
        with self.assertRaisesRegex(BasisAuditDenied,"EXPLICIT_SOURCE_UNIT_REQUIRED"):
            evaluate(items)
        items=fixtures()
        items[1]["close"]=25000  # mistakenly parsed the K-VND source as VND
        with self.assertRaisesRegex(BasisAuditDenied,"VND_PRICE_INTEGRITY_DENIED"):
            evaluate(items)

    def test_same_values_on_adjusted_vs_raw_are_not_comparable(self):
        items=fixtures()
        items[0]["price_basis"]="adjusted"
        r=evaluate(items)
        self.assertFalse(r["price_basis_aligned"])
        self.assertIsNone(r["matched_close_after_unit_conversion"])
        self.assertIn("PRICE_ADJUSTMENT_BASIS_UNKNOWN_OR_MIXED",r["block_reasons"])
        self.assertFalse(r["safe_to_publish_cache_head"])

    def test_unknown_adjustment_basis_is_not_silent_match(self):
        items=fixtures()
        items[1]["price_basis"]="unknown"
        r=evaluate(items)
        self.assertFalse(r["price_basis_aligned"])
        self.assertIsNone(r["matched_close_after_unit_conversion"])

    def test_board_supplement_after_hours_does_not_become_closed_bar(self):
        items=fixtures()
        items[2]["record_origin"]="board_supplement"
        r=evaluate(items)
        self.assertFalse(r["all_records_claim_historical_origin"])
        self.assertIn("PROVISIONAL_OR_BOARD_SUPPLEMENT_OBSERVED",r["block_reasons"])
        self.assertFalse(r["source_first_known_or_venue_finality_verified"])
        self.assertFalse(r["safe_to_publish_cache_head"])

    def test_other_provisional_state_never_certifies_close(self):
        for origin in ("provisional","unknown"):
            items=fixtures()
            items[0]["record_origin"]=origin
            with self.subTest(origin=origin):
                r=evaluate(items)
            self.assertIn("PROVISIONAL_OR_BOARD_SUPPLEMENT_OBSERVED",r["block_reasons"])

    def test_volume_scope_mismatch_cannot_claim_volume_agreement(self):
        items=fixtures()
        items[0]["volume_scope"]="unknown"
        r=evaluate(items)
        self.assertFalse(r["volume_scope_aligned"])
        self.assertIsNone(r["matched_volume_only_when_scope_aligned"])
        self.assertIn("VOLUME_SCOPE_UNKNOWN_OR_MIXED",r["block_reasons"])

    def test_comparable_price_mismatch_is_observed_only(self):
        items=fixtures()
        items[2]["close"]="25050"
        r=evaluate(items)
        self.assertIs(r["matched_close_after_unit_conversion"],False)
        self.assertIn("NORMALIZED_CLOSE_DISAGREEMENT",r["block_reasons"])
        self.assertFalse(r["signals_or_trades_eligible"])

    def test_volume_mismatch_only_when_scopes_are_explicit(self):
        items=fixtures()
        items[2]["volume"]=1501
        r=evaluate(items)
        self.assertIs(r["matched_volume_only_when_scope_aligned"],False)
        self.assertIn("NORMALIZED_VOLUME_DISAGREEMENT",r["block_reasons"])

    def test_scope_and_day_mismatch_denied(self):
        for field,value in (("symbol","DCM"),
                            ("session_date","2026-11-18")):
            items=fixtures()
            items[1][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(
                BasisAuditDenied,"SCOPE_DATE_NOT_COMPARABLE"
            ):
                evaluate(items)

    def test_duplicate_or_missing_provider_denied(self):
        items=fixtures()
        items[1]["source"]="SSI_MCP_COMPACT_D1"
        items[1]["price_unit"]="VND"
        with self.assertRaisesRegex(BasisAuditDenied,"DUPLICATE_OR_MISSING_SOURCE"):
            evaluate(items)
        for bad in ([],fixtures()[:2],fixtures()+fixtures()[:1],True):
            with self.subTest(bad=type(bad).__name__), self.assertRaises(
                BasisAuditDenied
            ):
                evaluate(bad)

    def test_block_unknown_provider_and_no_fastconnect_identity_alias(self):
        for provider in ("SSI_FASTCONNECT_V3_MARKET_DATA","MCP_SSI","VCBS",
                         None,"UNKNOWN"):
            items=fixtures()
            items[0]["source"]=provider
            with self.subTest(provider=provider),self.assertRaises(
                BasisAuditDenied
            ):
                evaluate(items)

    def test_missing_extra_or_malformed_fields_denied(self):
        for edit in ("missing","extra","wrong symbol","bad date","bad basis"):
            items=fixtures()
            if edit=="missing":
                del items[0]["volume"]
            elif edit=="extra":
                items[0]["token"]="SENSITIVE"
            elif edit=="wrong symbol":
                items[0]["symbol"]="../../"
            elif edit=="bad date":
                items[0]["session_date"]="2026-02-30"
            else:
                items[0]["price_basis"]="market-close-final"
            with self.subTest(edit=edit),self.assertRaises(BasisAuditDenied):
                evaluate(items)

    def test_nan_inf_bool_negative_and_fractional_shares_denied(self):
        for field,value in (
            ("close",float("nan")),("close",float("inf")),
            ("close",-1),("close",0),("close",True),
            ("volume",-1),("volume",3.2),("volume",float("nan")),
            ("volume",True),
        ):
            items=fixtures()
            items[0][field]=value
            with self.subTest(field=field,value=str(value)),self.assertRaises(
                BasisAuditDenied
            ):
                evaluate(items)

    def test_fractional_kvnd_price_refuses_implicit_rounding(self):
        items=fixtures()
        items[1]["close"]="25.0005" # fractional VND after scaling
        with self.assertRaisesRegex(BasisAuditDenied,"VND_PRICE_INTEGRITY_DENIED"):
            evaluate(items)

    def test_prices_and_volumes_not_leaked_in_public_receipt(self):
        items=fixtures()
        items[0]["close"]="26000"
        items[1]["close"]=26.0
        items[2]["close"]=26000
        items[0]["volume"]=1700
        items[1]["volume"]=1700
        items[2]["volume"]=1700
        text=json.dumps(evaluate(items))
        self.assertNotIn("26000",text)
        self.assertNotIn("1700",text)
        self.assertNotIn("26.0",text)

    def test_pure_offline_no_io_no_publish_policy(self):
        source=(Path(__file__).resolve().parents[1] /
                "scripts/mst_d1_research_cross_feed_basis248.py").read_text()
        for forbidden in (
            "requests.", "urllib", "session.get", "session.post",
            "google.auth", "github", "token=", "os.environ",
            "print(", "sign(", "trade_order"
        ):
            # No provider or storage access in this module; status fields
            # contain a mixed-case 'gitHub', not a request to GitHub.
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
