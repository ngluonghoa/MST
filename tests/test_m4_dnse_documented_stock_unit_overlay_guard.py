"""32 fictional DNSE source-documentation overlay promotion-denial tests."""
from copy import deepcopy
import json
import unittest

from scripts.m4_dnse_documented_stock_unit_overlay_guard import (
    SCHEMA,STATUS,DOCUMENTED_URLS,DENY_RELEASE_CLAIMS,DENY_SOURCE_CLAIMS,
    DENY_WIF_CLAIMS,check_source_unit_overlay,fictional_overlay,
)

class DnseEvidenceOverlayGuardTests(unittest.TestCase):
    def new(self):
        return deepcopy(fictional_overlay())
    def bad(self,modifier,expected,exc=(ValueError,PermissionError,TypeError)):
        a=self.new()
        modifier(a)
        with self.assertRaisesRegex(exc,expected):
            check_source_unit_overlay(a)
    def test_01_fictional_no_go_status(self):
        self.assertEqual(check_source_unit_overlay(self.new())["status"],STATUS)
    def test_02_schema(self):
        self.assertEqual(check_source_unit_overlay(self.new())["schema"],SCHEMA)
    def test_03_general_stock_unit_documented(self):
        self.assertTrue(check_source_unit_overlay(self.new())["official_general_stock_unit_in_thousand_vnd_documented"])
    def test_04_general_unit_does_not_approve_ohlc(self):
        self.assertFalse(check_source_unit_overlay(self.new())["historical_ohlc_effective_unit_or_price_basis_issuer_verified"])
    def test_05_api_version_not_proven(self):
        self.assertFalse(check_source_unit_overlay(self.new())["historical_connected_mcp_effective_api_version_verified"])
    def test_06_three_aliases_quarantined(self):
        self.assertEqual(check_source_unit_overlay(self.new())["three_snapshot_manifest_unit_aliases_quarantined"],3)
    def test_07_no_alias_promotion(self):
        self.assertFalse(check_source_unit_overlay(self.new())["any_source_unit_alias_resolved_for_publishing"])
    def test_08_no_original_mutation(self):
        self.assertFalse(check_source_unit_overlay(self.new())["origin_source_docs_or_manifests_mutated"])
    def test_09_no_actual_cloud_tool_run(self):
        self.assertFalse(check_source_unit_overlay(self.new())["real_drive_or_gcp_connectors_called_by_this_script"])
    def test_10_draft_wif_does_not_enable_main_dispatch(self):
        self.assertFalse(check_source_unit_overlay(self.new())["actual_workflow_dispatch_main_ready"])
    def test_11_no_m5_issuer(self):
        self.assertFalse(check_source_unit_overlay(self.new())["dnse_native_ohlc_closed_m5_authenticated"])
    def test_12_no_license_cache_or_trading(self):
        x=check_source_unit_overlay(self.new())
        self.assertFalse(x["licensed_source_cloud_retention_or_production_cache"])
        self.assertFalse(x["trading_authorized"])
    def test_13_four_ordered_official_docs(self):
        self.assertEqual(len(DOCUMENTED_URLS),4)
    def test_14_wrong_official_url_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][0].update(url="https://example.invalid"),"FOUR_ORDERED")
    def test_15_unverified_ohlc_specific_unit_claim_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][0].update(source_specific_historical_ohlc_unit_claimed=True),"GENERAL_STOCK_UNIT")
    def test_16_wrong_documented_1000_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][0].update(unit_scale_to_VND=100),"GENERAL_STOCK_UNIT")
    def test_17_fraction_or_bool_1000_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][0].update(unit_scale_to_VND=True),"GENERAL_STOCK_UNIT")
    def test_18_ohlc_adjustment_basis_self_grant_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][1].update(declares_adjustment_basis_in_response_schema=True),"HISTORICAL_OHLC_SCHEMA")
    def test_19_ohlc_unit_field_self_grant_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][1].update(declares_specific_OHLC_price_unit_in_response_schema=True),"HISTORICAL_OHLC_SCHEMA")
    def test_20_bypass_vendor_auth_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][1].update(requires_X_API_Key_and_signature=False),"OHLC_API_VERSION")
    def test_21_fake_ws_auth_status_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][2].update(authenticated_MST_cloud_connection_proven=True),"PUBLIC_WS_DOCS")
    def test_22_fake_history_version_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][3].update(historical_MST_connected_MCP_effective_version_authenticated=True),"API_VERSION")
    def test_23_prior_native_row_count_changed_denied(self):
        self.bad(lambda x:x["real_read_only_evidence"].update(historical_D1_source_rows_preserved=179),"KNOWN_PRIVATE_D1")
    def test_24_diagnostic_becomes_auth_denied(self):
        self.bad(lambda x:x["real_read_only_evidence"].update(real_per_snapshot_source_revision_attested=True),"SOURCE_DIAGNOSTICS")
    def test_25_duplicate_symbol_denied(self):
        self.bad(lambda x:x["unresolved_metadata_conflicts"][1].update(symbol="AAA"),"THREE_DISTINCT")
    def test_26_unknown_unit_alias_denied(self):
        self.bad(lambda x:x["unresolved_metadata_conflicts"][1].update(manifest_unit_token="VND_per_share"),"UNKNOWN_DNSE_UNIT_ALIAS")
    def test_27_unit_overlay_dequarantine_denied(self):
        self.bad(lambda x:x["unresolved_metadata_conflicts"][0].update(disposition="PRODUCTION"),"SOURCE_UNIT_CONFLICT")
    def test_28_source_release_self_approval_denied(self):
        self.bad(lambda x:x["source_issuer_specific_claims"].update(connected_MCP_DNSE_history_price_unit_verified_by_provider_issuer=True),"ISSUER_CANNOT_SELF_APPROVE")
    def test_29_release_self_approval_denied(self):
        self.bad(lambda x:x["release"].update(price_scale_approved_for_MST_signals_or_cache=True),"RELEASE_CANNOT_SELF_APPROVE")
    def test_30_wif_main_workflow_not_ready_denied(self):
        self.bad(lambda x:x["wif_real_access_readiness"].update(exists_on_protected_main=True),"WIF_CANNOT_SELF_APPROVE")
    def test_31_fake_workflow_oidc_success_denied(self):
        self.bad(lambda x:x["wif_real_access_readiness"].update(real_runner_google_STS_identity_or_Drive_files_get_success=True),"WIF_CANNOT_SELF_APPROVE")
    def test_32_source_document_id_in_receipt_not_leaked(self):
        x=check_source_unit_overlay(self.new())
        s=json.dumps(x)
        self.assertNotIn("fictional_source_ID",s)
        self.assertNotIn("fictional_manifest_ID",s)
        self.assertNotIn("source_unix_time",s)
    def test_33_unknown_source_schema_denied(self):
        self.bad(lambda x:x.update(schema="production.v9"),"UNSUPPORTED_EVIDENCE_OVERLAY")
    def test_34_unsigned_new_symbol_count_denied(self):
        self.bad(lambda x:x["unresolved_metadata_conflicts"].pop(),"THREE_DNSE_UNIT_CONFLICT")
    def test_35_cloud_license_self_grant_denied(self):
        self.bad(lambda x:x["source_issuer_specific_claims"].update(vendor_cloud_storage_and_processing_rights_verified=True),"ISSUER_CANNOT_SELF_APPROVE")
    def test_36_source_provider_override_denied(self):
        self.bad(lambda x:x["unresolved_metadata_conflicts"][0].update(provider="SSI"),"SOURCE_UNIT_CONFLICT")
    def test_37_original_docs_mutation_denied(self):
        self.bad(lambda x:x["release"].update(original_source_docs_mutated=True),"RELEASE_CANNOT_SELF_APPROVE")
    def test_38_broad_scoped_drive_sharing_self_grant_denied(self):
        self.bad(lambda x:x["wif_real_access_readiness"].update(owner_private_fpt_folder_metadata_shared=True),"WIF_CANNOT_SELF_APPROVE")
    def test_39_status_cannot_become_ok_by_editing_flag(self):
        self.bad(lambda x:x.update(status="PRODUCTION"),"UNSUPPORTED_EVIDENCE_OVERLAY")
    def test_40_unsupported_document_publisher_denied(self):
        self.bad(lambda x:x["vendor_doc_evidence"][0].update(publisher="random"),"UNAUTHENTICATED_DOCUMENT")
if __name__=="__main__":
    unittest.main()
