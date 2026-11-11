"""40 entirely fictional dual-legacy-schema private D1 manifest quarantine tests."""
import copy
import json
import unittest

from scripts.m4_private_d1_dual_schema_manifest_quarantine_lab import (
    STATUS, SCHEMAS, MANIFESTS, PROVIDERS, KNOWN_UNVERIFIED_DNSE_TOKEN_PAIRS,
    parse_native_google_doc_text, check_snapshot, audit_private_dataset,
    synthetic_three_source_fixture, synthetic_receipt,
)


class PrivateDualSchemaD1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=synthetic_receipt()

    def fixture(self):
        return copy.deepcopy(synthetic_three_source_fixture())

    def checked(self,parts=None,manifests=None):
        a,b=self.fixture()
        return audit_private_dataset(
            a if parts is None else parts,
            b if manifests is None else manifests,
            cutoff="2025-04-28")

    def bad(self,mutator,needle,exception=(ValueError,PermissionError,TypeError)):
        a,b=self.fixture()
        mutator(a,b)
        with self.assertRaisesRegex(exception,needle):
            self.checked(a,b)

    def test_01_no_go_status(self):
        self.assertEqual(self.out["status"],STATUS)

    def test_02_exact_180_fake_rows(self):
        self.assertEqual(self.out["source_ohlcv_rows_structurally_checked"],180)

    def test_03_nine_source_partitions(self):
        self.assertEqual(self.out["source_partition_count"],9)

    def test_04_two_private_manifest_schemas(self):
        self.assertEqual(self.out["source_manifests_checked"],2)

    def test_05_three_unit_token_conflicts(self):
        self.assertEqual(self.out["source_manifest_unit_alias_conflicts"],3)

    def test_06_only_dnse_unverified_unit_conflicts(self):
        self.assertEqual({x["provider"] for x in self.out["unit_alias_conflicts"]},{"DNSE"})

    def test_07_no_implicit_denial_exception_for_expected_unverified_alias(self):
        self.assertTrue(all(x["status"]=="UNVERIFIED_UNIT_ALIAS_QUARANTINE"
                            for x in self.out["unit_alias_conflicts"]))

    def test_08_strict_no_go_production(self):
        self.assertEqual(self.out["production_admission"],
                         "DENIED_UNIT_LABEL_CONFLICT_AND_EXTERNAL_RIGHTS")

    def test_09_all_original_labels_preserved(self):
        self.assertIs(self.out["all_original_unit_labels_preserved"],True)

    def test_10_source_issuer_units_not_authenticated(self):
        self.assertIs(self.out["dnse_price_basis_and_scale_issuer_authenticated"],False)

    def test_11_no_drive_reader_in_script(self):
        self.assertIs(self.out["actual_private_docs_read_by_validator"],False)
        self.assertIs(self.out["authenticated_github_runner_drive_reader"],False)

    def test_12_no_vendor_license(self):
        self.assertIs(self.out["vendor_cloud_storage_rights_verified"],False)

    def test_13_no_trade_no_cache(self):
        self.assertIs(self.out["content_addressed_atomic_cache_or_trade_authorized"],False)

    def test_14_no_calendar_source_first_known(self):
        self.assertIs(self.out["official_holiday_halt_and_exchange_calendar_verified"],False)
        self.assertIs(self.out["source_first_known_and_corrections_attested"],False)

    def test_15_fictitious_three_symbol_daily_intersection(self):
        self.assertEqual(sorted(self.out["source_diagnostics"]),["AAA","BBB","CCC"])
        self.assertTrue(all(x["common_dates"]==20 for x in self.out["source_diagnostics"].values()))

    def test_16_fictitious_ssi_vcbs_native_price_parity(self):
        self.assertTrue(all(x["ssi_vcbs_ohlc_mismatch_days"]==0
                            for x in self.out["source_diagnostics"].values()))

    def test_17_diagnostic_1000_is_not_canonical(self):
        self.assertTrue(all(x["dnse_unapproved_1000_diagnostic_mismatch_days"]==0
                            for x in self.out["source_diagnostics"].values()))
        self.assertFalse(self.out["dnse_price_basis_and_scale_issuer_authenticated"])

    def test_18_both_snapshots_supported(self):
        self.assertEqual(set(self.out["snapshot_schema_count"]),set(SCHEMAS))

    def test_19_json_envelope_one_heading_supported(self):
        obj=parse_native_google_doc_text('MST PRIVATE PILOT - FAKE\n{"schema":"demo"}')
        self.assertEqual(obj["schema"],"demo")

    def test_20_raw_json_supported(self):
        self.assertEqual(parse_native_google_doc_text(' {"a":1}\n'),{"a":1})

    def test_21_arbitrary_prefix_disallowed(self):
        with self.assertRaisesRegex(ValueError,"ONE_MST_TITLE_LINE"):
            parse_native_google_doc_text('Not a private MST document\n{"a":1}')

    def test_22_double_heading_disallowed(self):
        with self.assertRaisesRegex(ValueError,"ONE_MST_TITLE_LINE_THEN_JSON_REQUIRED"):
            parse_native_google_doc_text('MST PILOT\nsecond header\n{"a":1}')

    def test_23_duplicate_iso_day_denied(self):
        self.bad(lambda p,m:p[("BBB","SSI")][1]["rows"].__setitem__(1,
                 copy.deepcopy(p[("BBB","SSI")][1]["rows"][0])),
                 "DUPLICATE_OR_OUT_OF_ORDER")

    def test_24_wrong_provider_scope_denied(self):
        self.bad(lambda p,m:p[("BBB","DNSE")][1].update(provider="VCBS"),
                 "BATCH_SOURCE_SCOPE")

    def test_25_wrong_pilot_source_kind_denied(self):
        self.bad(lambda p,m:p[("AAA","SSI")][1].update(snapshot_kind="PRODUCTION"),
                 "FPT_PILOT_SOURCE_SCOPE")

    def test_26_false_source_right_self_promotion_denied(self):
        self.bad(lambda p,m:p[("AAA","SSI")][1]["governance"].update(
                  production_cache_approved=True),"EXACT_NO_GO_FLAGS")

    def test_27_false_batch_source_right_denied(self):
        self.bad(lambda p,m:p[("CCC","DNSE")][1]["governance"].update(
                  independent_source_cloud_retention_license_verified=True),"EXACT_NO_GO_FLAGS")

    def test_28_unknown_extra_governance_approval_denied(self):
        self.bad(lambda p,m:p[("BBB","SSI")][1]["governance"].update(
                  hidden_release_approval=False),"EXACT_NO_GO_FLAGS")

    def test_29_unrecognized_dnse_unit_token_denied(self):
        self.bad(lambda p,m:next(x for x in m["batch"]["files"]
                  if x["symbol"]=="CCC" and x["provider"]=="DNSE").update(unit="VND"),
                 "UNRECOGNIZED_UNIT_METADATA_CONFLICT")

    def test_30_ssi_manifest_unit_conflict_denied(self):
        self.bad(lambda p,m:next(x for x in m["pilot"]["providers"]
                  if x["provider"]=="SSI").update(unit="lots"),
                 "UNRECOGNIZED_UNIT_METADATA_CONFLICT")

    def test_31_unit_in_source_snapshot_drift_denied(self):
        self.bad(lambda p,m:p[("BBB","DNSE")][1].update(price_unit="VND_per_share"),
                 "BATCH_SOURCE_NATIVE_BASIS_UNIT_DRIFT")

    def test_32_future_day_cutoff_denied(self):
        p,m=self.fixture()
        with self.assertRaisesRegex(PermissionError,"SOURCE_DAY_OPEN_OR_CUTOFF_MISMATCH"):
            audit_private_dataset(p,m,cutoff="2025-04-27")

    def test_33_wrong_pilot_last_close_denied(self):
        self.bad(lambda p,m:next(x for x in m["pilot"]["providers"]
                  if x["provider"]=="VCBS").update(last_close=123456),
                 "MANIFEST_LAST_CLOSE_TAMPER")

    def test_34_wrong_batch_last_close_denied(self):
        self.bad(lambda p,m:next(x for x in m["batch"]["files"]
                  if x["symbol"]=="CCC" and x["provider"]=="SSI").update(last_close=0),
                 "NONPOSITIVE_NONFINITE")

    def test_35_mismatched_manifest_source_file_id_denied(self):
        self.bad(lambda p,m:next(x for x in m["batch"]["files"]
                  if x["symbol"]=="BBB" and x["provider"]=="SSI").update(fileId="other"),
                 "SOURCE_DOC_ID_OR_ROW_COUNT")

    def test_36_unverified_doc_readback_self_claim_denied(self):
        self.bad(lambda p,m:next(x for x in m["pilot"]["providers"]
                  if x["provider"]=="DNSE").update(readback_verified=False),
                 "FPT_PRIVATE_READBACK")

    def test_37_invalid_ohlc_envelope_denied(self):
        self.bad(lambda p,m:p[("BBB","SSI")][1]["rows"][0].update(high="1"),
                 "SOURCE_OHLC_ENVELOPE")

    def test_38_dnse_unix_date_denied(self):
        self.bad(lambda p,m:p[("AAA","DNSE")][1]["rows"][0].update(source_unix_time=5_000_000),
                 "EXACT_DNSE_UNIX_SECONDS")

    def test_39_batch_vcbs_provisional_unknown_must_remain_unknown(self):
        self.bad(lambda p,m:p[("BBB","VCBS")][1]["rows"][0].update(provisional_source_flag=True),
                 "VCBS_BATCH_UNKNOWN_PROVISIONAL")

    def test_40_ssi_source_number_not_string_denied(self):
        self.bad(lambda p,m:p[("BBB","SSI")][1]["rows"][0].update(open=100000),
                 "SSI_NATIVE_NUMERIC_STRING_POLICY")

    def test_41_cross_source_price_mismatch_keeps_quarantine(self):
        p,m=self.fixture()
        p[("BBB","VCBS")][1]["rows"][0]["close"]+=1
        # Manifest last_close untouched because first session changes.
        report=audit_private_dataset(p,m,cutoff="2025-04-28")
        self.assertGreater(report["source_diagnostics"]["BBB"]["ssi_vcbs_ohlc_mismatch_days"],0)
        self.assertFalse(report["content_addressed_atomic_cache_or_trade_authorized"])

    def test_42_volume_mismatch_keeps_quarantine(self):
        p,m=self.fixture()
        p[("CCC","DNSE")][1]["rows"][0]["volume"]+=3
        report=audit_private_dataset(p,m,cutoff="2025-04-28")
        self.assertEqual(report["source_diagnostics"]["CCC"]["volume_mismatch_days"],1)
        self.assertFalse(report["vendor_cloud_storage_rights_verified"])

    def test_43_no_raw_quotes_emitted(self):
        self.assertNotIn("rows",self.out)
        self.assertNotIn("source_price_payload",str(self.out))
        self.assertNotIn("OHLCV_VALUES",str(self.out))

    def test_44_empty_snapshot_rows_denied(self):
        self.bad(lambda p,m:p[("AAA","SSI")][1].update(rows=[]),
                 "TWENTY_REAL_SHAPED_PILOT_ROWS_REQUIRED")

    def test_45_wrong_pilot_manifest_authority_denied(self):
        self.bad(lambda p,m:m["pilot"]["authority"].update(production_cache_approved=True),
                 "EXACT_NO_GO_FLAGS")

    def test_46_wrong_batch_manifest_authority_denied(self):
        self.bad(lambda p,m:m["batch"]["authority"].update(trading_released=True),
                 "EXACT_NO_GO_FLAGS")

    def test_47_d1_date_window_drift_denied(self):
        self.bad(lambda p,m:p[("CCC","SSI")][1].update(last_session="2025-04-25"),
                 "SOURCE_ROW_RANGE_METADATA_MISMATCH")

    def test_48_unauthorized_cross_source_partial_dates_denied(self):
        p,m=self.fixture()
        p[("BBB","SSI")][1]["rows"][5]["date"]="2025-04-09"
        # Repeats later date in the source day series and fails closed.
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_OUT_OF_ORDER"):
            audit_private_dataset(p,m,cutoff="2025-04-28")

    def test_49_no_nan_volume(self):
        self.bad(lambda p,m:p[("BBB","DNSE")][1]["rows"][1].update(volume=float("nan")),
                 "NONPOSITIVE_NONFINITE")

    def test_50_missing_vcbs_adjfactor_denied(self):
        self.bad(lambda p,m:p[("CCC","VCBS")][1]["rows"][0].pop("adjFactor"),
                 "EXPLICIT_SOURCE_NUMERIC")

if __name__=="__main__":
    unittest.main()
