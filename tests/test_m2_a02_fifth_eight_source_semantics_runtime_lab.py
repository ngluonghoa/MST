"""Fifth batch of real, unmodified V1 source semantics + trust denial tests.

Synthetic fixtures ONLY. Test constructors are reused from existing tests,
but the eight original V1 production domain functions execute without mocking.
"""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import unittest

from scripts.m2_a02_fifth_eight_source_semantics_runtime_lab import (
    EIGHT, SCHEMA, evaluate_fifth_source_matrix,
)
from swing_trading.source_capability_evidence import ProbeEndpoint, ProbeState
from swing_trading.ssi_intraday_label_diagnostics import (
    LabelOrderEvidence, inspect_ssi_intraday_surface,
)
from swing_trading.ssi_multivenue_review import (
    MatrixState, evaluate_ssi_venue_matrix,
)
from swing_trading.ssi_source_qualification import (
    DateOrder, inspect_timestamp,
)
from swing_trading.ssi_volume_parity import (
    SsiTimestampLayout, ParityState as SsiParity,
    audit_ssi_intraday_daily_volume,
)
from swing_trading.dnse_d1_reference_fallback import (
    D1ReadState, D1Provider, D1SourceUnavailable,
)
from swing_trading.vcbs_source_contract import (
    VcbsFeed, vcbs_capability, inspect_vcbs_raw_daily_row,
)
from swing_trading.d1_mcp_transport_bridge import (
    ReceiptState,
)
from swing_trading.c2_fair_source_benchmark import (
    ComparisonAxis, ComparisonStatus, PriceBasis, VolumeBasis,
    compare_transient_d1_pair, require_benchmark_source_authority,
)
from swing_trading.incremental_cache import Provider
from swing_trading.market_data import Timeframe
from test_ssi_intraday_label_diagnostics import response, DAY as LABEL_DAY
from test_ssi_multivenue_review import full_matrix
from test_ssi_source_qualification import policy, OCT, DAY as AMBIGUOUS_DAY
from test_ssi_volume_parity import fixture as volumes, AS_OF
from test_dnse_d1_reference_fallback import (
    route as dnse_route, ssi as ssi_quote, history as dnse_history,
    request as d1_request,
)
from test_vcbs_source_contract import row as vcbs_row, STAMP
from test_d1_mcp_transport_bridge import bridge
from test_c2_fair_source_benchmark import row as fair_row


def inspect_labels(*labels, requested_day=LABEL_DAY):
    return inspect_ssi_intraday_surface(
        ProbeEndpoint.SSI_INTRADAY,response(*labels),
        symbol="SHS",requested_day=requested_day,checked_at_utc=AS_OF,
    )


class FifthOriginalSourceSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=evaluate_fifth_source_matrix()

    def test_01_eight_distinct_real_original_modules_executed(self):
        self.assertEqual(len(EIGHT),8)
        self.assertEqual(len(set(EIGHT)),8)
        self.assertEqual(self.report["executed_original_modules"],list(EIGHT))

    def test_02_prior_32_plus_eight_40_remaining_23(self):
        self.assertEqual(self.report["previous_distinct_originals"],32)
        self.assertEqual(self.report["cumulative_scoped_runtime_originals"],40)
        self.assertEqual(self.report["remaining_originals_without_tranche_style_runtime_qa"],23)

    def test_03_schema_marks_synthetic_no_go(self):
        self.assertEqual(self.report["schema"],SCHEMA)
        self.assertIn("NO_GO",self.report["status"])

    def test_04_eight_linked_safety_invariants(self):
        self.assertEqual(self.report["linked_safety_count"],8)
        self.assertTrue(all(self.report["linked_safety_checks"].values()))

    def test_05_real_provider_access_and_trading_all_false(self):
        for key in ("ssi_m1_label_gaps_are_missing_bars_proven",
                    "ssi_date_policy_certified_by_vendor",
                    "three_venues_prove_provider_independence",
                    "three_vendor_names_prove_independent_authentication",
                    "real_provider_api_or_mcp_called",
                    "full_native_m1_m5_m15_source_verified",
                    "real_vendor_data_rights_verified",
                    "source_quote_retention_approved",
                    "physical_drive_market_cache_read_write",
                    "a03_v2_full_abi_behavior_owner_approved",
                    "g01_g08_external_owner_security_gates_passed",
                    "production_release_authorized",
                    "trading_authorized"):
            with self.subTest(key=key):
                self.assertIs(self.report[key],False)

    def test_06_zero_human_owner_signatures(self):
        self.assertEqual(self.report["human_owner_a02_module_dispositions"],0)

    def test_07_ssi_label_gap_not_missing_bar(self):
        x=inspect_labels("14/10/2026 09:03:00","14/10/2026 09:01:00",
                         "14/10/2026 09:00:00")
        self.assertEqual(x.gaps_over_one_minute,1)
        self.assertEqual(x.unobserved_minutes_between_labels,1)
        self.assertFalse(x.observed_gap_is_missing_candle)

    def test_08_ssi_duplicate_second_labels_not_multiple_bar(self):
        x=inspect_labels("14/10/2026 09:00:45","14/10/2026 09:00:30",
                         "14/10/2026 09:00:30")
        self.assertEqual(x.unique_minute_labels,1)
        self.assertEqual(x.observed_rows,3)

    def test_09_ssi_lunch_gap_not_data_loss(self):
        x=inspect_labels("14/10/2026 13:01:00","14/10/2026 13:00:00",
                         "14/10/2026 11:30:00","14/10/2026 11:29:00")
        self.assertEqual(x.longest_label_gap_minutes,90)
        self.assertFalse(x.eligible_for_m1_m5_m15)

    def test_10_ssi_ambiguous_month_first_does_not_translate_utc(self):
        x=inspect_labels("05/05/2026 09:03:00",requested_day=date(2026,5,5))
        self.assertEqual(x.date_order_evidence,LabelOrderEvidence.AMBIGUOUS)
        self.assertFalse(x.timestamp_semantics_verified)

    def test_11_ssi_all_venues_sampled_not_three_independent_providers(self):
        x=evaluate_ssi_venue_matrix(full_matrix(),as_of_utc=AS_OF)
        self.assertIs(x.state,MatrixState.ALL_VENUES_OBSERVED_UNCERTIFIED)
        self.assertEqual(x.matched_count,3)
        self.assertFalse(x.provider_independent)

    def test_12_ssi_missing_one_venue_is_partial(self):
        x=evaluate_ssi_venue_matrix(full_matrix()[:2],as_of_utc=AS_OF)
        self.assertIs(x.state,MatrixState.PARTIAL_UNCERTIFIED)

    def test_13_ssi_duplicate_venue_date_sample_rejected(self):
        arr=full_matrix()
        x=evaluate_ssi_venue_matrix(arr+(arr[0],),as_of_utc=AS_OF)
        self.assertIs(x.state,MatrixState.BLOCKED)
        self.assertEqual(x.blocked_samples[0][-1],"DUPLICATE_SYMBOL_VENUE_DATE_SAMPLE")

    def test_14_ssi_three_venues_no_full_minute_certification(self):
        x=evaluate_ssi_venue_matrix(full_matrix(),as_of_utc=AS_OF)
        self.assertFalse(x.full_minutes_certified)
        self.assertFalse(x.source_entitlement_certified)

    def test_15_ssi_timestamp_date_format_conflict(self):
        x=inspect_timestamp("13/10/2026 09:00:00",OCT,policy(),intraday=True)
        self.assertEqual(x.reason_code,"DATE_ORDER_CONFLICT_OR_UNKNOWN")
        self.assertIsNone(x.interpreted_time_utc)

    def test_16_ssi_timestamp_ambiguous_mm_dd(self):
        x=inspect_timestamp("04/11/2026 09:00:00",AMBIGUOUS_DAY,
                            policy(),intraday=True)
        self.assertEqual(len(x.date_candidates),2)
        self.assertFalse(x.usable_for_market_time)

    def test_17_ssi_matching_date_without_independent_policy_still_denied(self):
        x=inspect_timestamp(
            "13/10/2026 09:00:00",OCT,
            policy(documented=DateOrder.DAY_FIRST,approved=False),
            intraday=True,
        )
        self.assertEqual(x.reason_code,"DATE_ORDER_NOT_INDEPENDENTLY_CONFIRMED")

    def test_18_ssi_date_approved_but_intraday_clock_not_approved(self):
        x=inspect_timestamp(
            "13/10/2026 09:00:00",OCT,
            policy(documented=DateOrder.DAY_FIRST,approved=True,clock=False),
            intraday=True,
        )
        self.assertEqual(x.reason_code,"INTRADAY_CLOCK_LABEL_NOT_CONFIRMED")

    def test_19_ssi_equal_intraday_daily_sum_not_minute_coverage(self):
        intraday,daily=volumes()
        x=audit_ssi_intraday_daily_volume(intraday,daily,as_of_utc=AS_OF)
        self.assertIs(x.state,SsiParity.MATCH_UNCERTIFIED)
        self.assertEqual(x.summed_intraday_matched_volume,4100)
        self.assertFalse(x.minute_coverage_certified)

    def test_20_ssi_daily_total_mismatch_is_blocked(self):
        a,b=volumes()
        x=audit_ssi_intraday_daily_volume(
            a,replace(b,total_match_volume=4101),as_of_utc=AS_OF,
        )
        self.assertIs(x.state,SsiParity.BLOCKED)

    def test_21_ssi_unrecognized_timestamp_layout_is_denied(self):
        a,b=volumes()
        x=audit_ssi_intraday_daily_volume(
            replace(a,date_layout=SsiTimestampLayout.UNKNOWN),b,
            as_of_utc=AS_OF,
        )
        self.assertIs(x.state,SsiParity.BLOCKED)

    def test_22_ssi_empty_is_not_zero_trading(self):
        a,b=volumes()
        x=audit_ssi_intraday_daily_volume(
            replace(a,rows=()),replace(b,total_match_volume=0),
            as_of_utc=AS_OF,
        )
        self.assertIs(x.state,SsiParity.BLOCKED)

    def test_23_dnse_D1_fallback_returns_reference_not_signal(self):
        x=dnse_route()
        self.assertIs(x.state,D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY)
        self.assertIs(x.source,D1Provider.DNSE)
        self.assertFalse(x.eligible_for_indicators)
        self.assertFalse(x.actionable)

    def test_24_ssi_primary_avoids_dnse_callback(self):
        called=[]
        def s(req):
            called.append("SSI")
            return ssi_quote()
        def d(req):
            called.append("DNSE")
            return dnse_history()
        x=dnse_route(s,d)
        self.assertIs(x.state,D1ReadState.PRIMARY_SSI_REFERENCE_ONLY)
        self.assertEqual(called,["SSI"])

    def test_25_dnse_never_used_for_intraday_timeframe(self):
        seen=[]
        def fn(req):
            seen.append(req)
            return None
        x=dnse_route(fn,fn,d1_request(Timeframe.M1))
        self.assertIs(x.state,D1ReadState.BLOCKED)
        self.assertEqual(seen,[])

    def test_26_dnse_source_exception_justifies_fallback_only(self):
        def unavailable(req):
            raise D1SourceUnavailable("synthetic upstream offline")
        x=dnse_route(unavailable,lambda req:dnse_history())
        self.assertIs(x.state,D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY)

    def test_27_vcbs_raw_daily_reference_cannot_be_traded(self):
        x=inspect_vcbs_raw_daily_row(vcbs_row(),symbol="SYNX",
                                     retrieved_at_utc=STAMP)
        self.assertFalse(x.rights_verified)
        self.assertFalse(x.indicators_allowed)
        self.assertFalse(x.actionable)

    def test_28_vcbs_price_series_not_minute_ohlcv(self):
        x=vcbs_capability(VcbsFeed.SESSION_PRICE_SERIES)
        self.assertFalse(x.full_minute_ohlcv)
        self.assertFalse(x.raw_ohlcv_candidate)

    def test_29_vcbs_adjusted_and_raw_fields_not_mixed(self):
        x=vcbs_row()
        x["priceBasis"]="adjusted"
        with self.assertRaises(ValueError):
            inspect_vcbs_raw_daily_row(x,symbol="SYNX",retrieved_at_utc=STAMP)

    def test_30_vcbs_volume_total_not_matched_volume(self):
        x=vcbs_row()
        x["volumeScope"]="total"
        with self.assertRaises(ValueError):
            inspect_vcbs_raw_daily_row(x,symbol="SYNX",retrieved_at_utc=STAMP)

    def test_31_d1_bridge_injected_ssi_callback_and_no_real_mcp(self):
        obj,calls=bridge()
        result=obj.run(d1_request())
        self.assertEqual([x[0] for x in calls],["SSI"])
        self.assertIs(result.audit.state,D1ReadState.PRIMARY_SSI_REFERENCE_ONLY)
        self.assertFalse(result.live_adapter_deployed)

    def test_32_d1_bridge_explicit_source_error_two_separate_receipts(self):
        err={"status":"error","data":None,
             "error":{"code":"DOWNSTREAM_UNAVAILABLE"}}
        obj,calls=bridge(ssi_response=err)
        result=obj.run(d1_request())
        self.assertEqual([x[0] for x in calls],["SSI","DNSE"])
        self.assertEqual(tuple(x.provider for x in result.receipts),
                         (D1Provider.SSI,D1Provider.DNSE))
        self.assertIs(result.receipts[0].state,ReceiptState.UNAVAILABLE)
        self.assertFalse(result.historical_backtest_qualified)

    def test_33_d1_bridge_refuses_unknown_permission_error(self):
        err={"status":"error","data":None,"error":{"code":"PERMISSION_DENIED"}}
        obj,calls=bridge(ssi_response=err)
        with self.assertRaises(Exception):
            obj.run(d1_request())
        self.assertEqual([x[0] for x in calls],["SSI"])

    def test_34_benchmark_price_pair_equal_is_caller_reported(self):
        x=compare_transient_d1_pair(
            (fair_row(),),(fair_row(Provider.VCBS),),
            axis=ComparisonAxis.PRICE,
        )
        self.assertIs(x.status,ComparisonStatus.COMPARABLE_REPORTED)
        self.assertEqual(x.equal_sessions,1)
        self.assertFalse(x.source_integrity_verified)

    def test_35_benchmark_price_basis_unknown_blocks(self):
        x=compare_transient_d1_pair(
            (fair_row(),),(fair_row(Provider.DNSE,basis=PriceBasis.UNVERIFIED),),
            axis=ComparisonAxis.PRICE,
        )
        self.assertIs(x.status,ComparisonStatus.BLOCKED_BASIS)

    def test_36_benchmark_total_vs_matched_volume_not_comparable(self):
        x=compare_transient_d1_pair(
            (fair_row(),),
            (fair_row(Provider.VCBS,vol_basis=VolumeBasis.TOTAL_WITH_DEALS),),
            axis=ComparisonAxis.VOLUME,
        )
        self.assertIs(x.status,ComparisonStatus.BLOCKED_VOLUME_SCOPE)

    def test_37_benchmark_denies_source_authority(self):
        with self.assertRaises(PermissionError):
            require_benchmark_source_authority("any synthetic verdict")

    def test_38_same_provider_not_independent_comparison(self):
        with self.assertRaises(ValueError):
            compare_transient_d1_pair(
                (fair_row(),),(fair_row(),),
                axis=ComparisonAxis.PRICE,
            )

    def test_39_report_zero_owner_signoffs_and_zero_market_rights(self):
        self.assertEqual(self.report["human_owner_a02_module_dispositions"],0)
        self.assertFalse(self.report["real_vendor_data_rights_verified"])
        self.assertFalse(self.report["trading_authorized"])

    def test_40_deterministic_aggregate_no_go_receipt(self):
        self.assertEqual(evaluate_fifth_source_matrix(),self.report)


if __name__=="__main__":
    unittest.main()
