"""MST M3 public vendor-evidence intake: all live market & retention gates deny."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import unittest

from scripts.m4_v21_vendor_rights_evidence_gate_lab import (
    SCHEMA, STATUS, RESEARCH_DATE, PROVIDERS, BASE_BLOCKERS,
    PROVIDER_BLOCKERS, DocumentRole, IntendedUse, PublicDocument,
    ReviewRequest, AdmissionDecision, public_catalog, review, require_live_permission,
    build_report,
)

UTC = timezone.utc
NOW = datetime(2026,11,11,5,0,tzinfo=UTC)


class VendorPublicEvidenceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=public_catalog()
        cls.report=build_report()

    def test_01_fixed_schema(self):
        self.assertEqual(self.report["schema"],SCHEMA)

    def test_02_fixed_synthetic_no_rights_status(self):
        self.assertEqual(self.report["status"],STATUS)

    def test_03_only_three_declared_vendor_namespaces(self):
        self.assertEqual(PROVIDERS,("SSI","DNSE","VCBS"))

    def test_04_seven_public_doc_pointers_not_contracts(self):
        self.assertEqual(len(self.docs),7)
        self.assertEqual(self.report["reviewed_public_document_count"],7)

    def test_05_each_document_has_distinct_id_and_digest(self):
        self.assertEqual(len({x.doc_id for x in self.docs}),7)
        self.assertEqual(len({x.source_digest for x in self.docs}),7)

    def test_06_vendor_doc_origin_must_match_vendor_namespace(self):
        self.assertEqual({x.scope for x in self.docs},set(PROVIDERS)|{"HNX"})
        for item in self.docs:
            self.assertTrue(item.url.startswith("https://"))

    def test_07_vcbs_mcp_is_only_chat_interface_public_doc(self):
        vcbs=[d for d in self.docs if d.scope=="VCBS"]
        self.assertEqual(len(vcbs),1)
        self.assertEqual(vcbs[0].role,DocumentRole.MCP_INTERFACE)

    def test_08_hnx_notice_is_public_context_not_trading_calendar_authority(self):
        hnx=[d for d in self.docs if d.scope=="HNX"]
        self.assertEqual(len(hnx),1)
        self.assertEqual(hnx[0].role,DocumentRole.VENUE_ANNOUNCEMENT)
        self.assertFalse(hnx[0].official_full_history_authenticated)

    def test_09_ssi_terms_document_is_separate_from_capabilities(self):
        ssi=[x for x in self.docs if x.scope=="SSI"]
        self.assertEqual(len(ssi),3)
        self.assertEqual(sum(d.role is DocumentRole.PROVIDER_TERMS for d in ssi),1)

    def test_10_dnse_public_ohlc_is_not_independent_storage_license(self):
        dnse=[x for x in self.docs if x.scope=="DNSE"]
        self.assertEqual(len(dnse),2)
        self.assertTrue(all(not d.grants_cache_retention for d in dnse))

    def test_11_review_records_research_date(self):
        self.assertEqual(self.report["reviewed_on"],"2026-11-11")
        self.assertEqual(RESEARCH_DATE,date(2026,11,11))

    def test_12_fifteen_provider_use_probes_all_denied(self):
        self.assertEqual(self.report["intended_use_probes_per_provider"],5)
        self.assertEqual(self.report["total_denied_probes"],15)

    def test_13_review_each_intent_for_each_vendor(self):
        for provider in PROVIDERS:
            for intent in IntendedUse:
                dec=review(ReviewRequest(provider,intent,NOW,"FAKE001"))
                self.assertEqual(dec.status,"DENIED_UNVERIFIED_RIGHTS")
                self.assertFalse(dec.read_live_provider_allowed)
                self.assertFalse(dec.write_cloud_cache_allowed)

    def test_14_ssi_public_terms_are_explicit_blocker(self):
        d=review(ReviewRequest("SSI",IntendedUse.GOOGLE_DRIVE_RETENTION,NOW,"FAKE001"))
        self.assertIn("SSI_FASTCONNECT_TERMS_RESTRICT_PURPOSE_AND_THIRD_PARTY_DATA_SHARING",d.blockers)

    def test_15_dnse_documented_endpoint_not_a_right_to_retain(self):
        d=review(ReviewRequest("DNSE",IntendedUse.GOOGLE_DRIVE_RETENTION,NOW,"FAKE001"))
        self.assertIn(PROVIDER_BLOCKERS["DNSE"],d.blockers)

    def test_16_vcbs_chat_mcp_not_github_actions_pipeline_permission(self):
        d=review(ReviewRequest("VCBS",IntendedUse.GITHUB_ACTIONS_TRANSPORT,NOW,"FAKE001"))
        self.assertIn(PROVIDER_BLOCKERS["VCBS"],d.blockers)

    def test_17_executed_retention_contract_not_automatically_inferred(self):
        for p in PROVIDERS:
            d=review(ReviewRequest(p,IntendedUse.GOOGLE_DRIVE_RETENTION,NOW,"FAKE001"))
            self.assertIn(BASE_BLOCKERS[1],d.blockers)

    def test_18_provider_login_not_independent_issuer_custody(self):
        for p in PROVIDERS:
            d=review(ReviewRequest(p,IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"))
            self.assertIn(BASE_BLOCKERS[0],d.blockers)
            self.assertIn(BASE_BLOCKERS[4],d.blockers)

    def test_19_venue_calendar_announcement_not_full_historical_first_known(self):
        d=review(ReviewRequest("SSI",IntendedUse.HISTORICAL_BACKTEST,NOW,"FAKE001"))
        self.assertIn(BASE_BLOCKERS[3],d.blockers)

    def test_20_external_cloud_signer_and_two_writer_cas_not_proven(self):
        d=review(ReviewRequest("DNSE",IntendedUse.GOOGLE_DRIVE_RETENTION,NOW,"FAKE001"))
        self.assertIn(BASE_BLOCKERS[6],d.blockers)

    def test_21_owner_release_gate_still_open(self):
        d=review(ReviewRequest("VCBS",IntendedUse.DERIVED_INDICATORS,NOW,"FAKE001"))
        self.assertIn(BASE_BLOCKERS[7],d.blockers)

    def test_22_no_market_api_calls_during_public_reference_ci(self):
        self.assertIs(self.report["actual_vendor_market_ohlcv_requested_or_retained"],False)
        self.assertIs(self.report["public_references_fetched_in_github_ci"],False)

    def test_23_never_assume_gdrive_quote_files_created(self):
        self.assertIs(self.report["gdrive_quote_cache_read_write"],False)

    def test_24_refuse_real_backtest_trade_and_release(self):
        for p in PROVIDERS:
            d=review(ReviewRequest(p,IntendedUse.HISTORICAL_BACKTEST,NOW,"FAKE001"))
            self.assertFalse(d.run_real_backtest_allowed)
            self.assertFalse(d.use_market_data_for_trading_allowed)
        self.assertFalse(self.report["owner_approved_live_release_or_trading"])

    def test_25_invalid_provider_namespace_denied(self):
        with self.assertRaisesRegex(ValueError,"EXPLICIT_PROVIDER"):
            ReviewRequest("MOCK_OTHER",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001")

    def test_26_non_enum_intended_use_denied(self):
        with self.assertRaisesRegex(TypeError,"TYPED_INTENDED_USE"):
            ReviewRequest("SSI","GOOGLE_DRIVE_RETENTION",NOW,"FAKE001")

    def test_27_non_utc_timezone_asof_denied(self):
        with self.assertRaisesRegex(TypeError,"ZERO_OFFSET"):
            ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW.astimezone(timezone(timedelta(hours=7))),"FAKE001")

    def test_28_naive_asof_denied(self):
        with self.assertRaisesRegex(TypeError,"ZERO_OFFSET"):
            ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW.replace(tzinfo=None),"FAKE001")

    def test_29_malicious_or_malformed_symbol_denied(self):
        for symbol in ("aa","A/B","", "BTC_USD","ÁB","A"*17):
            with self.subTest(symbol=symbol),self.assertRaisesRegex(ValueError,"NORMALIZED"):
                ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,symbol)

    def test_30_caller_owner_approval_flag_cannot_self_grant(self):
        with self.assertRaisesRegex(PermissionError,"CALLER_FLAGS"):
            ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001",owner_release_approved=True)

    def test_31_caller_contract_flag_cannot_self_grant(self):
        with self.assertRaisesRegex(PermissionError,"CALLER_FLAGS"):
            ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001",contract_rights_verified=True)

    def test_32_caller_live_token_flag_cannot_self_grant(self):
        with self.assertRaisesRegex(PermissionError,"CALLER_FLAGS"):
            ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001",live_source_credential_verified=True)

    def test_33_caller_custody_flag_cannot_self_grant(self):
        with self.assertRaisesRegex(PermissionError,"CALLER_FLAGS"):
            ReviewRequest("VCBS",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001",external_custody_verified=True)

    def test_34_nonboolean_flags_denied(self):
        with self.assertRaisesRegex(TypeError,"EXPLICIT_BOOLEAN"):
            ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001",owner_release_approved=0)

    def test_35_public_doc_cannot_self_assert_rights(self):
        with self.assertRaisesRegex(PermissionError,"PUBLIC_DOC_CANNOT_SELF_GRANT"):
            replace(self.docs[0],grants_cache_retention=True)

    def test_36_public_doc_cannot_self_assert_issuer_first_known(self):
        with self.assertRaisesRegex(PermissionError,"PUBLIC_DOC_CANNOT_SELF_GRANT"):
            replace(self.docs[0],proves_first_known=True)

    def test_37_public_doc_cannot_self_assert_full_calendar_history(self):
        with self.assertRaisesRegex(PermissionError,"PUBLIC_DOC_CANNOT_SELF_GRANT"):
            replace(self.docs[-1],official_full_history_authenticated=True)

    def test_38_forged_public_doc_wrong_host_denied(self):
        with self.assertRaisesRegex(ValueError,"APPROVED_OFFICIAL_HOST"):
            replace(self.docs[0],url="https://malicious.example.com/terms")

    def test_39_non_https_public_source_denied(self):
        with self.assertRaisesRegex(ValueError,"APPROVED_OFFICIAL_HOST"):
            replace(self.docs[0],url="http://developers.ssi.com.vn/docs/getting-started/overview")

    def test_40_credentials_in_public_url_denied(self):
        with self.assertRaisesRegex(ValueError,"APPROVED_OFFICIAL_HOST"):
            replace(self.docs[0],url="https://name:secret@developers.ssi.com.vn/x")

    def test_41_unapproved_query_params_denied(self):
        with self.assertRaisesRegex(ValueError,"APPROVED_OFFICIAL_HOST"):
            replace(self.docs[0],url=self.docs[0].url+"?token=secret")

    def test_42_future_document_review_date_denied(self):
        with self.assertRaisesRegex(ValueError,"MUST_NOT_BE_FUTURE"):
            replace(self.docs[0],observed_on=date(2026,11,12))

    def test_43_venue_notice_cannot_impersonate_vendor_api(self):
        with self.assertRaisesRegex(ValueError,"HNX_NOTICE_NOT_VENDOR"):
            replace(self.docs[-1],role=DocumentRole.CAPABILITY)

    def test_44_vendor_page_cannot_become_venue_notice(self):
        with self.assertRaisesRegex(ValueError,"VENDOR_PAGE_NOT_OFFICIAL"):
            replace(self.docs[0],role=DocumentRole.VENUE_ANNOUNCEMENT)

    def test_45_vcbs_mcp_page_cannot_become_contract(self):
        with self.assertRaisesRegex(ValueError,"VCBS_MCP_PUBLIC_PAGE"):
            replace(self.docs[-2],role=DocumentRole.PROVIDER_TERMS)

    def test_46_evidence_digest_changes_on_document_version_change(self):
        doc=self.docs[0]
        self.assertNotEqual(doc.source_digest,replace(doc,synopsis=doc.synopsis+" Additional review note.").source_digest)

    def test_47_cross_vendor_public_docs_not_reused_for_other_provider(self):
        ssi=review(ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"))
        dnse=review(ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"))
        self.assertNotEqual(ssi.public_docs_digest,dnse.public_docs_digest)
        self.assertNotEqual(ssi.reviewed_public_doc_ids,dnse.reviewed_public_doc_ids)

    def test_48_missing_venue_calendar_context_denied(self):
        subset=tuple(d for d in self.docs if d.scope=="SSI")
        with self.assertRaisesRegex(ValueError,"MISSING_EXCHANGE_PUBLIC"):
            review(ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"),catalog=subset)

    def test_49_missing_provider_document_denied(self):
        subset=tuple(d for d in self.docs if d.scope=="HNX")
        with self.assertRaisesRegex(ValueError,"NO_PROVIDER_PUBLIC"):
            review(ReviewRequest("DNSE",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"),catalog=subset)

    def test_50_duplicate_doc_identifier_denied(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PUBLIC_EVIDENCE"):
            review(ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"),catalog=self.docs+(self.docs[0],))

    def test_51_fake_allow_decision_promotion_denied(self):
        d=review(ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"))
        with self.assertRaisesRegex(PermissionError,"LOCAL_PUBLIC_DOCS_CANNOT_PROMOTE"):
            replace(d,read_live_provider_allowed=True)

    def test_52_forged_approval_status_denied(self):
        d=review(ReviewRequest("VCBS",IntendedUse.GOOGLE_DRIVE_RETENTION,NOW,"FAKE001"))
        with self.assertRaisesRegex(PermissionError,"ONLY_DENY_DECISION"):
            replace(d,status="APPROVED")

    def test_53_public_doc_receipt_cannot_authorize_live_io(self):
        d=review(ReviewRequest("SSI",IntendedUse.MARKET_DATA_READ,NOW,"FAKE001"))
        with self.assertRaisesRegex(PermissionError,"NO_LIVE_IO"):
            require_live_permission(d)

    def test_54_no_grant_even_with_all_five_publicly_described_use_probes(self):
        for p in PROVIDERS:
            states=[review(ReviewRequest(p,u,NOW,"FAKE001")).status for u in IntendedUse]
            self.assertEqual(states,["DENIED_UNVERIFIED_RIGHTS"]*5)

if __name__=="__main__":
    unittest.main()
