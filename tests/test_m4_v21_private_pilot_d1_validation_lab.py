"""MST M4: purely fictional private FPT D1 cache contract and refresh QA."""
from copy import deepcopy
from datetime import timedelta,datetime,timezone
from decimal import Decimal
import unittest

from scripts.m4_v21_private_pilot_d1_validation_lab import (
 SCHEMA, MANIFEST_SCHEMA, STATUS, PROVIDERS, DENIED_FLAGS, SOURCE_META,
 validate_snapshot, verify_manifest, plan_closed_day_refresh, fabricated_fixture,
 run_lab, _fingerprint,
)


class PrivatePilotD1ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m,cls.snap=fabricated_fixture()
        cls.out=run_lab()

    def _snap(self,p):
        return deepcopy(self.snap[p])

    def _manifest(self):
        return deepcopy(self.m)

    def _check(self,p,s=None,cutoff="2026-11-03"):
        return validate_snapshot(s if s is not None else self._snap(p),
                                 expected_provider=p,historical_cutoff=cutoff)

    def test_01_report_is_fixture_only(self):
        self.assertTrue(self.out["source_records_are_completely_fabricated"])

    def test_02_real_market_data_not_embedded_in_github(self):
        self.assertIs(self.out["original_real_mcp_market_data_in_github_artifacts"],False)

    def test_03_exact_three_separated_source_namespaces(self):
        self.assertEqual(PROVIDERS,("SSI","DNSE","VCBS"))
        self.assertEqual(len(set(self.snap)),3)

    def test_04_four_no_go_flags_are_false(self):
        for k in ("github_actions_account_authentication_performed",
                  "real_drive_docs_read_write_performed_in_ci",
                  "automatic_live_provider_ingestion_active"):
            self.assertIs(self.out[k],False)
        self.assertIs(self.out["all_production_gates_no_go"],True)

    def test_05_source_native_scale_not_auto_converted(self):
        self.assertEqual(self.snap["DNSE"]["rows"][-1]["close"],0.102)
        self.assertEqual(self.snap["SSI"]["rows"][-1]["close"],"102")

    def test_06_each_fixture_snapshot_parses(self):
        for p in PROVIDERS:
            with self.subTest(provider=p):
                self.assertEqual(self._check(p)["row_count"],2)

    def test_07_provider_namespaces_not_shared(self):
        self.assertEqual(len({self._check(p)["namespace"] for p in PROVIDERS}),3)

    def test_08_all_source_dates_complete_in_fixture(self):
        out=verify_manifest(self.m,self.snap,historical_cutoff="2026-11-03")
        self.assertEqual(out["cross_source_diagnostic"]["equal_dates_count"],2)

    def test_09_numeric_consistency_is_only_diagnostic(self):
        x=verify_manifest(self.m,self.snap,historical_cutoff="2026-11-03")["cross_source_diagnostic"]
        self.assertTrue(x["ssi_vcbs_native_ohlcv_equal"])
        self.assertTrue(x["dnse_factor_1000_observed_but_not_approved"])
        self.assertFalse(x["dnse_unit_and_price_basis_authenticated"])

    def test_10_no_independent_license_or_auto_refresh(self):
        x=verify_manifest(self.m,self.snap,historical_cutoff="2026-11-03")
        self.assertFalse(x["cross_source_diagnostic"]["independent_license_or_github_cloud_auth_verified"])
        self.assertFalse(x["cross_source_diagnostic"]["automatic_refresh_or_production_cache"])

    def test_11_fingerprint_changes_with_source_price(self):
        x=self._snap("SSI")
        a=self._check("SSI",x)["rows_fingerprint_sha256"]
        x["rows"][1]["close"]="101"
        self.assertNotEqual(self._check("SSI",x)["rows_fingerprint_sha256"],a)

    def test_12_future_session_is_denied(self):
        with self.assertRaisesRegex(PermissionError,"OPEN_OR_FUTURE_SESSION"):
            self._check("SSI",cutoff="2026-11-02")

    def test_13_snapshot_query_cannot_be_today_as_final_close(self):
        s=self._snap("SSI")
        s["scope"]["max_closed_session_date"]="2026-11-05"
        with self.assertRaisesRegex(PermissionError,"FUTURE_OPEN_OR_UNQUALIFIED"):
            self._check("SSI",s,cutoff="2026-11-05")

    def test_14_snapshot_earlier_cutoff_than_required_denied(self):
        s=self._snap("SSI")
        s["scope"]["max_closed_session_date"]="2026-11-02"
        with self.assertRaisesRegex(PermissionError,"FUTURE_OPEN_OR_UNQUALIFIED"):
            self._check("SSI",s)

    def test_15_cannot_use_missing_governance_dict(self):
        s=self._snap("VCBS");s.pop("governance")
        with self.assertRaisesRegex(PermissionError,"CANNOT_CLAIM_REAL_DATA_RIGHTS"):
            self._check("VCBS",s)

    def test_16_cannot_self_promote_production(self):
        s=self._snap("VCBS");s["governance"]["production_cache_approved"]=True
        with self.assertRaisesRegex(PermissionError,"CANNOT_CLAIM_REAL_DATA_RIGHTS"):
            self._check("VCBS",s)

    def test_17_cannot_self_promote_issuer_signed(self):
        s=self._snap("SSI");s["governance"]["issuer_signed_first_known"]=True
        with self.assertRaisesRegex(PermissionError,"CANNOT_CLAIM_REAL_DATA_RIGHTS"):
            self._check("SSI",s)

    def test_18_nonboolean_grant_denied(self):
        s=self._snap("DNSE");s["governance"]["production_cache_approved"]=0
        with self.assertRaisesRegex(PermissionError,"CANNOT_CLAIM_REAL_DATA_RIGHTS"):
            self._check("DNSE",s)

    def test_19_no_disguised_other_project(self):
        s=self._snap("SSI");s["scope"]["project"]="SWING"
        with self.assertRaisesRegex(PermissionError,"UNAPPROVED_PILOT"):
            self._check("SSI",s)

    def test_20_no_other_symbol_in_fpt_scope(self):
        s=self._snap("SSI");s["scope"]["symbol"]="HPG"
        with self.assertRaisesRegex(PermissionError,"UNAPPROVED_PILOT"):
            self._check("SSI",s)

    def test_21_no_infer_m5_from_daily(self):
        s=self._snap("VCBS");s["scope"]["timeframe"]="M5"
        with self.assertRaisesRegex(PermissionError,"UNAPPROVED_PILOT"):
            self._check("VCBS",s)

    def test_22_cross_provider_snapshot_denied(self):
        with self.assertRaisesRegex(PermissionError,"CROSS_PROVIDER"):
            self._check("SSI",self._snap("DNSE"))

    def test_23_basis_or_unit_guess_denied(self):
        s=self._snap("DNSE");s["scope"]["unit"]="VND_per_share"
        with self.assertRaisesRegex(PermissionError,"SOURCE_PRICE_BASIS_OR_UNIT"):
            self._check("DNSE",s)

    def test_24_non_chapgpt_source_method_denied(self):
        s=self._snap("SSI");s["scope"]["source_method"]="GitHub Actions service account authenticated"
        with self.assertRaisesRegex(PermissionError,"UNAPPROVED_PILOT"):
            self._check("SSI",s)

    def test_25_unknown_snapshot_schema_denied(self):
        s=self._snap("VCBS");s["schema"]="UNKNOWN"
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_PRIVATE"):
            self._check("VCBS",s)

    def test_26_unknown_snapshot_kind_denied(self):
        s=self._snap("VCBS");s["snapshot_kind"]="PRODUCTION"
        with self.assertRaisesRegex(PermissionError,"UNAPPROVED_SNAPSHOT_KIND"):
            self._check("VCBS",s)

    def test_27_duplicate_source_date_denied(self):
        s=self._snap("SSI");s["rows"][1]["date"]=s["rows"][0]["date"]
        with self.assertRaisesRegex(ValueError,"DUPLICATED_SOURCE_SESSION"):
            self._check("SSI",s)

    def test_28_out_of_order_dates_denied(self):
        s=self._snap("SSI");s["rows"].reverse()
        with self.assertRaisesRegex(ValueError,"STRICTLY_ASCENDING"):
            self._check("SSI",s)

    def test_29_ohlc_envelope_denied(self):
        s=self._snap("VCBS");s["rows"][0]["low"]=999
        with self.assertRaisesRegex(ValueError,"SOURCE_OHLC_PRICE_ENVELOPE_INVALID"):
            self._check("VCBS",s)

    def test_30_zero_close_denied(self):
        s=self._snap("SSI");s["rows"][0]["close"]="0"
        with self.assertRaisesRegex(ValueError,"NEGATIVE_ZERO_OR_NONFINITE"):
            self._check("SSI",s)

    def test_31_negative_volume_denied(self):
        s=self._snap("SSI");s["rows"][0]["volume"]="-1"
        with self.assertRaisesRegex(ValueError,"NEGATIVE_ZERO_OR_NONFINITE"):
            self._check("SSI",s)

    def test_32_nan_denied(self):
        s=self._snap("SSI");s["rows"][0]["high"]="NaN"
        with self.assertRaisesRegex(ValueError,"NEGATIVE_ZERO_OR_NONFINITE"):
            self._check("SSI",s)

    def test_33_infinite_denied(self):
        s=self._snap("DNSE");s["rows"][0]["close"]=float("inf")
        with self.assertRaisesRegex(ValueError,"NEGATIVE_ZERO_OR_NONFINITE"):
            self._check("DNSE",s)

    def test_34_row_count_mismatch_denied(self):
        s=self._snap("SSI");s["row_count"]=3
        with self.assertRaisesRegex(ValueError,"SOURCE_ROW_COUNT_REQUIRED"):
            self._check("SSI",s)

    def test_35_ssi_native_strings_required(self):
        s=self._snap("SSI");s["rows"][0]["open"]=100
        with self.assertRaisesRegex(TypeError,"SSI_NATIVE_NUMERIC_STRING"):
            self._check("SSI",s)

    def test_36_dnse_timestamp_utc_date_required(self):
        s=self._snap("DNSE");s["rows"][0]["source_unix_time"]+=86400
        with self.assertRaisesRegex(PermissionError,"DNSE_SOURCE_UNIX_DATE_MISMATCH"):
            self._check("DNSE",s)

    def test_37_dnse_timestamp_absent_denied(self):
        s=self._snap("DNSE");s["rows"][0].pop("source_unix_time")
        with self.assertRaisesRegex(TypeError,"DNSE_SOURCE_UNIX_TIMESTAMP"):
            self._check("DNSE",s)

    def test_38_vcbs_provisional_bar_denied(self):
        s=self._snap("VCBS");s["rows"][1]["provisional"]=True
        with self.assertRaisesRegex(PermissionError,"VCBS_PROVISIONAL"):
            self._check("VCBS",s)

    def test_39_vcbs_raw_close_missing_denied(self):
        s=self._snap("VCBS");s["rows"][0].pop("raw_close")
        with self.assertRaisesRegex(TypeError,"SOURCE_PRICE_OR_VOLUME"):
            self._check("VCBS",s)

    def test_40_vcbs_wrong_volume_scope_denied(self):
        s=self._snap("VCBS");s["rows"][0]["volumeScope"]="all_mixed"
        with self.assertRaisesRegex(PermissionError,"VCBS_PROVISIONAL"):
            self._check("VCBS",s)

    def test_41_no_cross_source_manifest_member(self):
        m=self._manifest();m["providers"].pop()
        with self.assertRaisesRegex(ValueError,"EXACT_THREE_SOURCE"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_42_no_duplicated_manifest_provider(self):
        m=self._manifest();m["providers"][2]["provider"]="SSI"
        with self.assertRaisesRegex(ValueError,"EXACT_THREE_SOURCE"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_43_private_manifest_readback_required(self):
        m=self._manifest();m["providers"][1]["readback_verified"]=False
        with self.assertRaisesRegex(PermissionError,"PRIVATE_READBACK"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_44_public_manifest_denied(self):
        m=self._manifest();m["providers"][0]["private"]=False
        with self.assertRaisesRegex(PermissionError,"PRIVATE_READBACK"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_45_tampered_manifest_source_count_denied(self):
        m=self._manifest();m["providers"][0]["rows"]=22
        with self.assertRaisesRegex(ValueError,"MANIFEST_SOURCE_ROWS"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_46_tampered_manifest_last_close_denied(self):
        m=self._manifest();m["providers"][2]["last_close"]=5000
        with self.assertRaisesRegex(ValueError,"MANIFEST_SOURCE_ROWS"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_47_fake_manifest_prod_promotion_denied(self):
        m=self._manifest();m["authority"]["production_cache_approved"]=True
        with self.assertRaisesRegex(PermissionError,"MANIFEST_AUTHORITY"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_48_three_source_session_mismatch_denied(self):
        s=deepcopy(self.snap)
        s["DNSE"]["rows"][0]["date"]="2026-11-01"
        s["DNSE"]["rows"][0]["source_unix_time"]-=86400
        with self.assertRaisesRegex(PermissionError,"CROSS_PROVIDER_DATE_PARITY"):
            verify_manifest(self.m,s,historical_cutoff="2026-11-03")

    def test_49_global_manifest_total_count_denied(self):
        m=self._manifest();m["total_rows"]=7
        with self.assertRaisesRegex(ValueError,"MANIFEST_GLOBAL_DATE"):
            verify_manifest(m,self.snap,historical_cutoff="2026-11-03")

    def test_50_identical_snapshot_refresh_has_no_recompute(self):
        p=plan_closed_day_refresh(self.snap["SSI"],self.snap["SSI"],
                                  provider="SSI",historical_cutoff="2026-11-03")
        self.assertEqual(p["unchanged_numeric_sessions"],2)
        self.assertEqual(p["proposed_new_closed_sessions"],[])
        self.assertEqual(p["observed_value_revision_dates_require_issuer_verification"],[])

    def test_51_same_source_value_revision_is_not_auto_approved(self):
        next_=self._snap("SSI");next_["rows"][1]["close"]="100"
        r=plan_closed_day_refresh(self.snap["SSI"],next_,
                                  provider="SSI",historical_cutoff="2026-11-03")
        self.assertEqual(r["observed_value_revision_dates_require_issuer_verification"],["2026-11-03"])
        self.assertFalse(r["drive_write_or_manifest_promotion_authorized"])

    def test_52_missing_old_cached_session_is_denied(self):
        next_=self._snap("SSI");next_["rows"].pop(0);next_["row_count"]=1
        with self.assertRaisesRegex(PermissionError,"SOURCE_LOST_PREVIOUSLY_CACHED"):
            plan_closed_day_refresh(self.snap["SSI"],next_,
                                   provider="SSI",historical_cutoff="2026-11-03")

    def test_53_extra_source_session_after_cutoff_denied(self):
        next_=self._snap("SSI")
        n=deepcopy(next_["rows"][1]);n["date"]="2026-11-04"
        next_["rows"].append(n);next_["row_count"]=3
        with self.assertRaisesRegex(PermissionError,"OPEN_OR_FUTURE_SESSION"):
            plan_closed_day_refresh(self.snap["SSI"],next_,
                                   provider="SSI",historical_cutoff="2026-11-03")

    def test_54_no_merge_of_provider_denied(self):
        with self.assertRaisesRegex(PermissionError,"CROSS_PROVIDER"):
            plan_closed_day_refresh(self.snap["SSI"],self.snap["DNSE"],
                                   provider="SSI",historical_cutoff="2026-11-03")

    def test_55_manifest_schema_lock(self):
        self.assertEqual(self.m["schema"],MANIFEST_SCHEMA)
        self.assertEqual(self.snap["SSI"]["schema"],SCHEMA)

    def test_56_json_hash_stable_for_key_reorder(self):
        self.assertEqual(_fingerprint({"a":1,"b":2}),_fingerprint({"b":2,"a":1}))

    def test_57_manifest_source_scope_and_no_go(self):
        r=verify_manifest(self.m,self.snap,historical_cutoff="2026-11-03")
        self.assertEqual(r["total_verified_rows"],6)
        self.assertTrue(r["production_and_trading_no_go"])

    def test_58_missing_source_does_not_silently_fallback(self):
        other=deepcopy(self.snap);other.pop("DNSE")
        with self.assertRaisesRegex(PermissionError,"ALL_THREE_PROVIDER"):
            verify_manifest(self.m,other,historical_cutoff="2026-11-03")

    def test_59_null_volume_allowed_as_zero_only_if_explicit_zero(self):
        s=self._snap("SSI");s["rows"][0]["volume"]="0"
        self.assertEqual(self._check("SSI",s)["row_count"],2)
        s["rows"][0]["volume"]=None
        with self.assertRaises(TypeError):
            self._check("SSI",s)

    def test_60_non_iso_session_date_denied(self):
        s=self._snap("SSI");s["rows"][0]["date"]="02/11/2026"
        with self.assertRaisesRegex(ValueError,"YYYY_MM_DD"):
            self._check("SSI",s)


if __name__=="__main__":
    unittest.main()
