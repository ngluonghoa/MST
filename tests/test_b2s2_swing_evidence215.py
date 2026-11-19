"""§215 fictional source-locked B2/S2 higher-low/lower-high R0/R_E QA."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.b2s2_swing_evidence215 import (
    B2S2PivotDenied215, B2S2PivotPair215, PivotPairState215,
    inspect_b2s2_two_pivot215,
)
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.market_data import Timeframe, PriceBasis
from swing_trading.source_quality import QualityState
from test_causal_indicators import make_bar, snap
from test_causal_structure_geometry import AS_OF, PIVOT0


def synthetic_rows(zone="B2", phase="R_E", second=None):
    frame=Timeframe.M15 if phase=="R_E" else Timeframe.D1
    lows=[6,5,3,5,6,4,6,7]
    highs=[12,14,16,14,13,15,14,12]
    if second is not None:
        if zone=="B2": lows[5]=second
        else: highs[5]=second
    rows=[]
    for i in range(8):
        start=PIVOT0+(
            timedelta(minutes=i*30) if frame is Timeframe.M15
            else timedelta(days=i))
        row=make_bar(
            i+800, timeframe=frame, start=start,
            open_price=D("10"), close=D("10"),
            high=D("12") if zone=="B2" else D(highs[i]),
            low=D(lows[i]) if zone=="B2" else D("8"),
        )
        rows.append(snap(row))
    return tuple(rows)


def inspect(zone="B2", phase="R_E", *, history=None, strategy=Strategy.SHORT,
            **changes):
    kwargs=dict(
        zone_id=zone,phase=phase,strategy=strategy,
        history=synthetic_rows(zone,phase) if history is None else history,
        first_index=2,second_index=5,left_count=1,right_count=1,
        tie_policy=TiePolicy.STRICT_V1,as_of_utc=AS_OF,
    )
    kwargs.update(changes)
    return inspect_b2s2_two_pivot215(**kwargs)


class B2S2Structure215Tests(unittest.TestCase):
    def test_source_locked_four_cases_positive_geometries_only(self):
        for zone in ("B2","S2"):
            for phase in ("R0","R_E"):
                with self.subTest(zone=zone,phase=phase):
                    r=inspect(zone,phase)
                    self.assertIs(r.state,PivotPairState215.GEOMETRY_MATCH_UNVERIFIED)
                    self.assertIs(r.status,DecisionStatus.UNVERIFIED)
                    self.assertEqual(r.zone_id,zone)
                    self.assertEqual(r.phase,phase)
                    self.assertEqual(r.timeframe, Timeframe.D1 if phase=="R0" else Timeframe.M15)
                    self.assertTrue(r.predicate_ref.startswith(zone+"."))
                    self.assertTrue(r.preview_id.startswith("MST_B2S2_PAIR215:"))
                    self.assertLess(r.first_known_at_utc,r.second_known_at_utc)
                    self.assertLessEqual(r.second_known_at_utc,AS_OF)
                    self.assertFalse(r.action_eligible)
                    self.assertFalse(r.detector_approved)
                    self.assertFalse(r.source_independently_attested)
                    self.assertFalse(r.chosen_lookback_approved)

    def test_b2_lower_low_or_s2_higher_high_is_unverified_not_detected(self):
        cases=(("B2",D("2")),("S2",D("17")))
        for zone,bad_value in cases:
            for phase in ("R0","R_E"):
                with self.subTest(zone=zone,phase=phase):
                    r=inspect(zone,phase,history=synthetic_rows(zone,phase,bad_value))
                    self.assertIs(r.state,PivotPairState215.GEOMETRY_NONMATCH_UNVERIFIED)
                    self.assertIs(r.status,DecisionStatus.UNVERIFIED)
                    self.assertFalse(r.action_eligible)

    def test_no_second_local_pivot_is_blocked_not_no_signal(self):
        for zone in ("B2","S2"):
            history=list(synthetic_rows(zone))
            target=history[5].selected
            if zone=="B2": amended=replace(target,low=D("7"))
            else: amended=replace(target,high=D("12"))
            history[5]=snap(amended)
            result=inspect(zone,history=tuple(history))
            self.assertIs(result.state,PivotPairState215.BLOCKED)
            self.assertIsNone(result.preview_id)

    def test_source_clock_and_right_bar_knowability_are_hard_gates(self):
        rows=list(synthetic_rows())
        row=rows[6].selected
        changed=snap(replace(row,quality_state=QualityState.UNVERIFIED))
        rows[6]=changed
        r=inspect(history=tuple(rows))
        self.assertIs(r.state,PivotPairState215.BLOCKED)
        self.assertIsNone(r.preview_id)
        witness=synthetic_rows()[6].selected.bar_end_utc-timedelta(seconds=1)
        past=inspect(as_of_utc=witness)
        self.assertIs(past.state,PivotPairState215.BLOCKED)

    def test_mixed_source_provider_calendar_and_adjustment_denied(self):
        rows=synthetic_rows()
        origin=rows[4].selected
        cases=(
            "provider","calendar","basis","adjustment","stream"
        )
        for which in cases:
            k=origin.market_bar_key
            o=origin.observation_key
            r=origin.observation_revision
            if which=="provider":
                o=replace(o,provider_id="OTHER")
            elif which=="stream":
                o=replace(o,source_stream_id="OTHER")
            elif which=="calendar":
                k=replace(k,calendar_version="OTHER")
                o=replace(o,market_bar_key=k)
            elif which=="basis":
                k=replace(k,price_basis=PriceBasis.ADJUSTED)
                o=replace(o,market_bar_key=k)
            else:
                r=replace(r,adjustment_revision="OTHER")
            r=replace(r,observation_key=o)
            changed=replace(origin,market_bar_key=k,
                            observation_key=o,observation_revision=r)
            with self.subTest(which=which):
                new=rows[:4]+(snap(changed),)+rows[5:]
                outcome=inspect(history=new)
                self.assertIs(outcome.state,PivotPairState215.BLOCKED)
                self.assertEqual(outcome.reason,"PIVOT_MIXED_SOURCE_OR_ADJUSTMENT")

    def test_original_venue_tf_restrictions_are_not_ignored(self):
        with self.assertRaises(B2S2PivotDenied215):
            inspect("B3")
        with self.assertRaises(B2S2PivotDenied215):
            inspect("B2","R_C")
        with self.assertRaises(B2S2PivotDenied215):
            inspect(strategy="SHORT")
        rows=list(synthetic_rows())
        origin=rows[0].selected
        k=replace(origin.market_bar_key,timeframe=Timeframe.H4)
        o=replace(origin.observation_key,market_bar_key=k)
        r=replace(origin.observation_revision,observation_key=o)
        rows[0]=snap(replace(origin,market_bar_key=k,observation_key=o,
                             observation_revision=r))
        self.assertIs(inspect(history=tuple(rows)).state,PivotPairState215.BLOCKED)

    def test_malformed_history_first_middle_or_empty_blocks_fails_closed(self):
        originals=synthetic_rows()
        for rows in (originals[:2]+(None,)+originals[3:],
                     (None,)+originals[1:],
                     ()):
            with self.subTest(rows=len(rows)):
                if not rows:
                    with self.assertRaises(B2S2PivotDenied215):
                        inspect(history=rows)
                else:
                    self.assertIs(inspect(history=rows).state,PivotPairState215.BLOCKED)

    def test_no_right_bars_overlapping_indices_and_reordered(self):
        history=synthetic_rows()
        for params in ({"second_index":7},{"second_index":3},
                       {"first_index":2,"second_index":2},
                       {"first_index":0},{"second_index":20}):
            with self.subTest(params=params):
                self.assertIs(inspect(**params).state,PivotPairState215.BLOCKED)
        shuffled=history[:1]+(history[2],history[1])+history[3:]
        self.assertIs(inspect(history=shuffled).state,PivotPairState215.BLOCKED)

    def test_boolean_indices_and_lookback_parameters_are_rejected(self):
        for params in ({"left_count":0},{"right_count":41},
                       {"first_index":True},{"second_index":False},
                       {"left_count":1.0},{"tie_policy":"STRICT_V1"}):
            with self.subTest(params=params),self.assertRaises(B2S2PivotDenied215):
                inspect(**params)
        with self.assertRaises(ValueError):
            inspect(as_of_utc=AS_OF.replace(tzinfo=None))

    def test_no_single_high_low_candidate_claims_structural_sequence(self):
        short=synthetic_rows()[:5]
        r=inspect(history=short)
        self.assertIs(r.state,PivotPairState215.BLOCKED)
        self.assertIsNone(r.first_known_at_utc)

    def test_source_revision_correction_changes_preview_id(self):
        original=inspect("S2","R_E")
        rows=list(synthetic_rows("S2","R_E"))
        row=rows[5].selected
        rev=replace(row.observation_revision,
                    source_revision_or_payload_digest="rev215-corrected")
        rows[5]=snap(replace(row,observation_revision=rev,
                             normalized_digest_sha256="b"*64))
        amended=inspect("S2","R_E",history=tuple(rows))
        self.assertIs(amended.state,PivotPairState215.GEOMETRY_MATCH_UNVERIFIED)
        self.assertNotEqual(amended.preview_id,original.preview_id)

    def test_two_strategies_isolated_and_idempotent(self):
        a=inspect(strategy=Strategy.SHORT)
        b=inspect(strategy=Strategy.SWING)
        self.assertEqual(a,inspect(strategy=Strategy.SHORT))
        self.assertNotEqual(a.preview_id,b.preview_id)
        self.assertFalse(a.action_eligible or b.action_eligible)

    def test_asof_later_cannot_relabel_same_version_as_confirmed(self):
        a=inspect()
        later=inspect(as_of_utc=AS_OF+timedelta(days=1))
        self.assertEqual(a.preview_id,later.preview_id)
        self.assertIs(later.status,DecisionStatus.UNVERIFIED)
        self.assertFalse(later.detector_approved)

    def test_signed_source_attestation_and_strategy_claim_spoofing_denied(self):
        good=inspect()
        for patch in (
            {"status":DecisionStatus.DETECTED},
            {"status":DecisionStatus.NOT_DETECTED},
            {"source_independently_attested":True},
            {"chosen_lookback_approved":True},
            {"detector_approved":True},
            {"action_eligible":True},
            {"action_eligible":1},
            {"phase":"R_F"},
            {"predicate_ref":"WRONG"},
            {"preview_id":"FAKE_APPROVED"},
            {"second_known_at_utc":AS_OF+timedelta(days=10)},
        ):
            with self.subTest(patch=patch),self.assertRaises(B2S2PivotDenied215):
                replace(good,**patch)
        blocked=inspect(second_index=1)
        with self.assertRaises(B2S2PivotDenied215):
            replace(blocked,preview_id=good.preview_id)

    def test_no_prices_positions_or_orders_published(self):
        r=inspect()
        self.assertIsInstance(r,B2S2PivotPair215)
        for forbidden in ("open","high","low","close","volume","position",
                          "quantity","order","signal_price"):
            self.assertNotIn(forbidden,r.__dict__)
        self.assertFalse(r.action_eligible)


if __name__=="__main__":
    unittest.main()
