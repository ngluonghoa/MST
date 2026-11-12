"""A02 fourth 8 ORIGINAL V1 routing/session/market shape regression tests.

Domain functions are inherited Swing source, only test fixture inputs
synthetic; no provider calls, real licensed bars, local Mac/MOCHI, or trade.
"""
from dataclasses import replace
from datetime import date, timedelta
import unittest

from scripts.m2_a02_fourth_eight_routing_calendar_runtime_lab import (
    SCHEMA, EIGHT, execute_fourth_eight_runtime,
)
from swing_trading.adaptive_source_router import (
    PriceBasis, RouteMode, SourceTask, preview_adaptive_route,
)
from swing_trading.c2_source_capability_audit import (
    ConnectedEndpoint as CE, DataNeed, ProbeState, RefreshVerdict,
    advise_connected_refresh, require_authorized_c2_source,
)
from swing_trading.c2_session_probe_readiness import (
    summarize_session_probes, session_coverage,
    ByteMeasurement, SessionPhase, require_authorized_session_metrics,
)
from swing_trading.d1_atr_reconciliation import (
    SessionAuditState, audit_d1_session_inventory,
)
from swing_trading.native_minute_bar_source_plan import (
    BarProduct, SourceBarGateClosed, candidate_native_bar_sources,
    sketch_first_page_query,
)
from swing_trading.session_calendar import SessionType
from swing_trading.ssi_historical_availability import HistoricalAvailabilityState
from swing_trading.vn_2026_closure_anchors import (
    ClosureAuditState, audit_2026_notice_closure_collisions,
)
from swing_trading.incremental_cache import Provider
from swing_trading.market_data import Timeframe
from test_adaptive_source_router import NOW, candidate, probe as route_probe, select
from test_c2_source_capability_audit import (
    run as shape_run, ssi_row, ssi_d1, ssi_minute, dnse, dnse_row, vcbs_row,
)
from test_c2_session_probe_readiness import probe as session_probe
from test_d1_atr_reconciliation import AS_OF, d1, sessions
from test_native_minute_bar_source_plan import DAY as PLAN_DAY, START, END
from test_session_calendar import T as CAL_T, bar as calendar_bar, snapshot as calendar_snapshot, session
from test_ssi_historical_availability import probe as ssi_review
from test_ssi_volume_parity import fixture as ssi_receipts
from test_vn_2026_closure_anchors import inventory


class FourthEightRoutingCalendarV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = execute_fourth_eight_runtime()

    def test_01_eight_distinct_inherited_source_modules(self):
        self.assertEqual(len(EIGHT),8)
        self.assertEqual(len(set(EIGHT)),8)
        self.assertEqual(self.report["executed_original_modules"],list(EIGHT))

    def test_02_cumulative_32_originals_and_31_remaining(self):
        self.assertEqual(self.report["prior_tranches_distinct_modules"],24)
        self.assertEqual(self.report["cumulative_distinct_original_v1_module_count"],32)
        self.assertEqual(self.report["remaining_original_v1_without_tranche_runtime_qa"],31)

    def test_03_metadata_review_no_trade_status(self):
        self.assertEqual(self.report["schema"], SCHEMA)
        self.assertIn("PRODUCTION_NO_GO",self.report["status"])

    def test_04_all_linked_original_runtime_safety_assertions(self):
        self.assertEqual(len(self.report["linked_checks"]),9)
        self.assertTrue(all(self.report["linked_checks"].values()))

    def test_05_source_rights_and_market_calendar_remain_unverified(self):
        for field in ("source_license_verified",
                      "official_full_exchange_calendar_verified",
                      "real_provider_source_credential_bound",
                      "real_minute_history_coverage_verified",
                      "actual_provider_network_call_made",
                      "actual_drive_market_cache_read_write"):
            with self.subTest(field=field):
                self.assertFalse(self.report[field])

    def test_06_zero_owner_and_production(self):
        self.assertEqual(self.report["a02_owner_signed_modules"],0)
        for field in ("a03_v2_full_abi_approved","g01_g08_actual_security_gates_closed",
                      "production_release_authorized","trading_authorized"):
            self.assertFalse(self.report[field])

    def test_07_D1_route_DNSE_reference_not_authoritative(self):
        out=select(candidate(Provider.SSI),candidate(Provider.DNSE))
        self.assertIs(out.selected,Provider.DNSE)
        self.assertFalse(out.source_authority_verified)
        self.assertFalse(out.trading_actionable)

    def test_08_M1_route_requires_SSI_not_vcbs_price_ticks(self):
        out=select(candidate(Provider.DNSE,SourceTask.M1_OHLCV),
                   candidate(Provider.VCBS,SourceTask.M1_OHLCV),
                   task=SourceTask.M1_OHLCV)
        self.assertIs(out.mode,RouteMode.BLOCKED)

    def test_09_M1_ssi_route_never_proves_native_closed_bar(self):
        out=select(candidate(Provider.SSI,SourceTask.M1_OHLCV),
                   task=SourceTask.M1_OHLCV)
        self.assertIs(out.selected,Provider.SSI)
        self.assertFalse(out.indicator_eligible)

    def test_10_quality_gate_before_speed(self):
        bad=candidate(Provider.DNSE,complete=False)
        fast=tuple(route_probe(Provider.DNSE,ms=1) for _ in range(6))
        out=select(bad,candidate(Provider.SSI),probes=fast)
        self.assertNotEqual(out.selected,Provider.DNSE)
        self.assertFalse(out.trading_actionable)

    def test_11_adjusted_cannot_silently_satisfy_raw(self):
        r=select(candidate(Provider.DNSE,price_basis=PriceBasis.ADJUSTED))
        self.assertIs(r.mode,RouteMode.BLOCKED)

    def test_12_ssi_valid_shape_not_source_rights(self):
        r=shape_run(CE.SSI_D1_DETAILED,ssi_d1(ssi_row()))
        self.assertIs(r.state,ProbeState.SHAPE_RETURNED)
        self.assertFalse(r.source_rights_verified)
        with self.assertRaises(PermissionError): require_authorized_c2_source(r)

    def test_13_ssi_missing_candle_field_schema_rejected(self):
        row=ssi_row()
        row.pop("low")
        r=shape_run(CE.SSI_D1_DETAILED,ssi_d1(row))
        self.assertIs(r.state,ProbeState.SCHEMA_REJECTED)

    def test_14_dnse_d1_shape_positive_metadata_only(self):
        r=shape_run(CE.DNSE_D1_HISTORY,dnse(dnse_row()))
        self.assertIs(r.state,ProbeState.SHAPE_RETURNED)
        self.assertFalse(r.live_trading_enabled)

    def test_15_vcbs_raw_shape_positive_not_price_adjustment_proof(self):
        r=shape_run(CE.VCBS_D1_WINDOW,[vcbs_row()])
        self.assertIs(r.state,ProbeState.SHAPE_RETURNED)
        self.assertFalse(r.price_adjustment_parity_verified)

    def test_16_ssi_empty_intraday_not_successful_M1_history(self):
        r=shape_run(CE.SSI_INTRADAY_SESSION,ssi_minute())
        self.assertIs(r.state,ProbeState.EMPTY_UNVERIFIED)
        self.assertFalse(r.indicator_eligible)

    def test_17_refresh_whole_session_not_five_minute_delta(self):
        r=advise_connected_refresh(CE.SSI_INTRADAY_SESSION,DataNeed.MINUTE_OHLCV)
        self.assertIs(r.verdict,RefreshVerdict.REFETCH_WHOLE_SESSION)
        self.assertFalse(r.supports_delta_from_last_change)

    def test_18_claimed_changed_since_cursor_blocked(self):
        r=advise_connected_refresh(CE.SSI_INTRADAY_SESSION,
                                   DataNeed.MINUTE_OHLCV,changed_since_required=True)
        self.assertIs(r.verdict,RefreshVerdict.BLOCKED)

    def test_19_five_synthetic_probe_latency_observations_not_SLA(self):
        s=tuple(session_probe(client_monotonic_elapsed_ns=n*1_000_000)
                for n in (50,100,120,300,900))
        out=summarize_session_probes(s)[0]
        self.assertEqual((out.median_elapsed_ms,out.p95_elapsed_ms),(120,900))
        self.assertFalse(out.provider_sla_verified)

    def test_20_four_samples_no_descriptive_percentiles(self):
        out=summarize_session_probes(tuple(session_probe() for _ in range(4)))[0]
        self.assertIsNone(out.p95_elapsed_ms)

    def test_21_json_serialized_bytes_not_measured_network_wire(self):
        x=summarize_session_probes(tuple(session_probe(
            estimated_serialized_json_bytes=1000) for _ in range(5)))[0]
        self.assertEqual(x.measured_network_wire_samples,0)
        self.assertIsNone(x.median_network_wire_bytes)

    def test_22_single_weekday_missing_auction_and_multiple_sessions(self):
        c=session_coverage((session_probe(),))[0]
        self.assertIn("MULTIPLE_WEEKDAY_SESSIONS_MISSING",c.missing_review_gates)
        self.assertIn("AUCTION_PHASE_MISSING",c.missing_review_gates)
        self.assertFalse(c.authorized_for_router)

    def test_23_session_probe_metrics_never_grant_access(self):
        with self.assertRaises(PermissionError):
            require_authorized_session_metrics()

    def test_24_D1_exact_self_supplied_inventory_only_uncertified(self):
        rows=d1(20)
        r=audit_d1_session_inventory(rows,sessions(rows),as_of_utc=AS_OF)
        self.assertIs(r.state,SessionAuditState.MATCH_UNCERTIFIED)
        self.assertFalse(r.calendar_certified)

    def test_25_D1_missing_one_expected_closed_session_blocks(self):
        rows=d1(20)
        r=audit_d1_session_inventory(rows[:-1],sessions(rows),as_of_utc=AS_OF)
        self.assertIs(r.state,SessionAuditState.BLOCKED)
        self.assertTrue(r.missing_session_ids)

    def test_26_D1_future_calendar_inventory_blocks(self):
        rows=d1(20)
        inv=replace(sessions(rows),first_known_time_utc=AS_OF+timedelta(minutes=1))
        r=audit_d1_session_inventory(rows,inv,as_of_utc=AS_OF)
        self.assertIs(r.state,SessionAuditState.BLOCKED)

    def test_27_catalog_all_minute_sources_not_executable(self):
        x=candidate_native_bar_sources(Timeframe.M5)
        self.assertEqual(len(x),4)
        self.assertTrue(all(not a.executable and not a.actionable for a in x))

    def test_28_connected_SSI_tick_action_not_native_M5(self):
        with self.assertRaises(SourceBarGateClosed):
            sketch_first_page_query(BarProduct.SSI_CONNECTED_INTRADAY_TICKS,
                                    Timeframe.M5,symbol="FPT",session_day=PLAN_DAY)

    def test_29_SSI_fastconnect_M15_integer_not_documented(self):
        with self.assertRaises(SourceBarGateClosed):
            sketch_first_page_query(BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
                                    Timeframe.M15,symbol="FPT",session_day=PLAN_DAY)

    def test_30_DNSE_native_M5_sketch_requires_explicit_UTC(self):
        p=sketch_first_page_query(BarProduct.DNSE_OPENAPI_OHLC,
                                  Timeframe.M5,symbol="FPT",session_day=PLAN_DAY,
                                  start_utc=START,end_utc=END)
        self.assertFalse(p.connected)
        self.assertFalse(p.ready_to_send)
        self.assertFalse(p.retention_approved)

    def test_31_calendar_positive_fabricated_continuous_slot(self):
        r=calendar_snapshot().resolve_intraday(
            calendar_bar(),CAL_T+timedelta(minutes=15))
        self.assertIsNotNone(r)
        self.assertIs(r.session_type,SessionType.CONTINUOUS)

    def test_32_calendar_unverified_and_auction_denied(self):
        self.assertIsNone(calendar_snapshot(verified=False).resolve_intraday(
            calendar_bar(),CAL_T+timedelta(minutes=15)))
        a=calendar_snapshot((session("ATC",kind=SessionType.AUCTION),))
        self.assertIsNone(a.resolve_intraday(calendar_bar(sid="ATC"),
                                             CAL_T+timedelta(minutes=15)))

    def test_33_calendar_lunch_gap_cannot_span_closed_M15(self):
        self.assertIsNone(calendar_snapshot().resolve_intraday(
            calendar_bar(CAL_T+timedelta(minutes=45)),
            CAL_T+timedelta(hours=2,minutes=15)))

    def test_34_ssi_nonempty_volume_parity_still_uncertified(self):
        r=ssi_review()
        self.assertIs(r.state,HistoricalAvailabilityState.NONEMPTY_MATCHED_UNCERTIFIED)
        self.assertFalse(r.source_entitlement_certified)

    def test_35_ssi_intraday_empty_d1_positive_is_data_gap_not_no_trades(self):
        i,d=ssi_receipts()
        r=ssi_review(intraday=replace(i,rows=()))
        self.assertIs(r.state,HistoricalAvailabilityState.INTRADAY_EMPTY_DAILY_TRADES_UNCERTIFIED)
        self.assertFalse(r.complete_m1_history_certified)

    def test_36_ssi_both_empty_and_daily_zero_not_full_market_closed(self):
        i,d=ssi_receipts()
        r=ssi_review(intraday=replace(i,rows=()),
                     daily=replace(d,total_match_volume=0))
        self.assertIs(r.state,HistoricalAvailabilityState.BLOCKED)

    def test_37_exchange_notice_2026_jan2_both_HOSE_HNX_block(self):
        inv=inventory(date(2026,1,2))
        for exch in ("HOSE","HNX"):
            with self.subTest(exchange=exch):
                r=audit_2026_notice_closure_collisions(inv,exchange=exch)
                self.assertIs(r.state,ClosureAuditState.BLOCKED)

    def test_38_nonlisted_date_still_full_calendar_uncertified(self):
        r=audit_2026_notice_closure_collisions(
            inventory(date(2026,1,5)),exchange="HOSE")
        self.assertIs(r.state,ClosureAuditState.NO_KNOWN_COLLISION_UNCERTIFIED)
        self.assertFalse(r.full_calendar_certified)

    def test_39_untrusted_fixture_source_does_not_gain_root(self):
        self.assertFalse(self.report["real_provider_source_credential_bound"])
        self.assertFalse(self.report["official_full_exchange_calendar_verified"])
        self.assertFalse(self.report["g01_g08_actual_security_gates_closed"])

    def test_40_repeat_eight_original_runtime_receipt_is_deterministic(self):
        self.assertEqual(execute_fourth_eight_runtime(),self.report)


if __name__=="__main__":
    unittest.main()
