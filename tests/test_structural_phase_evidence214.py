"""§214 B2/S2 causal R_C fixture QA; never source-authoritative/tradable."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from swing_trading.contracts import DecisionStatus, Strategy
from swing_trading.causal_structure_geometry import StructureSide, TiePolicy
from swing_trading.market_data import PriceBasis, Timeframe
from swing_trading.source_quality import QualityState
from swing_trading.structural_phase_evidence import (
    CausalNearEvidence214, NearEvidenceState214, PhaseEvidenceDenied,
    inspect_b2s2_rc_causal_near214,
)
from test_causal_indicators import make_bar, snap
from test_causal_structure_geometry import AS_OF, PIVOT0, atr_d1
from test_structural_phase_evidence213 import bars_for


def make_target(zone, *, low=None, high=None):
    lo,hi=(D("3.5"),D("12")) if zone=="B2" else (D("8"),D("16.5"))
    return snap(make_bar(
        409,timeframe=Timeframe.M15,start=PIVOT0+timedelta(days=6),
        open_price=D("10"),close=D("10"),
        low=lo if low is None else low,
        high=hi if high is None else high,
    ))


def near(zone="B2", *, tf=Timeframe.H1, k=None, strategy=Strategy.SHORT,
         target=None, history=None, atr=None, **changes):
    side=StructureSide.LOW if zone=="B2" else StructureSide.HIGH
    args=dict(
        zone_id=zone,strategy=strategy,
        pullback_m15=make_target(zone) if target is None else target,
        pivot_history=bars_for(side,tf)[:4] if history is None else history,
        candidate_index=2,left_count=1,right_count=1,
        tie_policy=TiePolicy.STRICT_V1,
        atr_d1_history=atr_d1() if atr is None else atr,
        as_of_utc=AS_OF,candidate_k_near=k,
    )
    args.update(changes)
    return inspect_b2s2_rc_causal_near214(**args)


class B2S2CausalNear214Tests(unittest.TestCase):
    def test_mirror_h1_and_d1_near_distance_both_unverified(self):
        for zone in ("B2","S2"):
            for tf in (Timeframe.H1,Timeframe.D1):
                with self.subTest(zone=zone,tf=tf):
                    r=near(zone,tf=tf)
                    self.assertIs(r.state,NearEvidenceState214.CAUSAL_DISTANCE_UNCALIBRATED)
                    self.assertEqual(r.distance_atr,D("0.125"))
                    self.assertIs(r.status,DecisionStatus.UNVERIFIED)
                    self.assertIsNone(r.candidate_in_band)
                    self.assertFalse(r.action_eligible)

    def test_explicit_k_is_unapproved_whatif_not_live_near_signal(self):
        for zone in ("B2","S2"):
            inside=near(zone,k=D("0.2"))
            outside=near(zone,k=D("0.1"))
            self.assertTrue(inside.candidate_in_band)
            self.assertFalse(outside.candidate_in_band)
            self.assertEqual(inside.distance_atr,outside.distance_atr)
            self.assertNotEqual(inside.preview_id,outside.preview_id)
            self.assertFalse(inside.parameter_approved)
            self.assertFalse(outside.phase_executable)

    def test_zero_distance_never_implies_approved_phase(self):
        for zone,change in (("B2",{"low":D("3")}),
                            ("S2",{"high":D("16")})):
            result=near(zone,target=make_target(zone,**change))
            self.assertEqual(result.distance_atr,D("0"))
            self.assertIsNone(result.candidate_k_near)
            self.assertFalse(result.action_eligible)

    def test_candidate_outside_buffer_is_not_verified_not_detected(self):
        for zone,change in (("B2",{"low":D("1")}),
                            ("S2",{"high":D("20")})):
            r=near(zone,target=make_target(zone,**change),k=D("0.1"))
            self.assertFalse(r.candidate_in_band)
            self.assertIs(r.status,DecisionStatus.UNVERIFIED)

    def test_unqualified_target_or_future_asof_blocks(self):
        source=make_target("B2").selected
        bad=snap(replace(source,quality_state=QualityState.UNVERIFIED))
        self.assertIs(near(target=bad).state,NearEvidenceState214.BLOCKED)
        asof=source.bar_end_utc-timedelta(seconds=1)
        self.assertIs(near(as_of_utc=asof).state,NearEvidenceState214.BLOCKED)

    def test_wrong_pivot_frame_or_missing_history_blocks(self):
        for tf in (Timeframe.H4,Timeframe.M15):
            r=near(tf=tf)
            self.assertIs(r.state,NearEvidenceState214.BLOCKED)
        r=near(history=())
        self.assertIs(r.state,NearEvidenceState214.BLOCKED)

    def test_no_witness_after_target_start_or_unqualified_right_bar(self):
        items=bars_for(StructureSide.LOW,Timeframe.H1)[:4]
        bad=snap(replace(items[3].selected,quality_state=QualityState.UNVERIFIED))
        r=near(history=items[:3]+(bad,))
        self.assertIs(r.state,NearEvidenceState214.BLOCKED)
        self.assertIsNone(r.preview_id)

    def test_d1_atr_missing_14_bars_or_future_blocks(self):
        for history in ((),atr_d1()[:14]):
            r=near(atr=history)
            self.assertIs(r.state,NearEvidenceState214.BLOCKED)
        r=near(as_of_utc=PIVOT0-timedelta(days=1))
        self.assertIs(r.state,NearEvidenceState214.BLOCKED)

    def test_mixed_price_basis_source_or_calendar_is_rejected(self):
        base=make_target("B2").selected
        for change in ("basis","provider","calendar"):
            if change=="provider":
                key=base.market_bar_key
                obs=replace(base.observation_key,provider_id="OTHER")
            else:
                key=replace(
                    base.market_bar_key,
                    **({"price_basis":PriceBasis.ADJUSTED}
                       if change=="basis" else {"calendar_version":"OTHER"})
                )
                obs=replace(base.observation_key,market_bar_key=key)
            row=replace(
                base,market_bar_key=key,observation_key=obs,
                observation_revision=replace(base.observation_revision,observation_key=obs),
            )
            with self.subTest(change=change):
                r=near(target=snap(row))
                self.assertIs(r.state,NearEvidenceState214.BLOCKED)
                self.assertIn("SOURCE_SCOPE",r.reason)

    def test_atr_history_revision_alters_replay_id(self):
        first=near()
        history=list(atr_d1())
        row=history[1].selected
        changed=replace(row,observation_revision=replace(
            row.observation_revision,source_revision_or_payload_digest="rev-214"),
            raw_digest_sha256="d"*64)
        history[1]=snap(changed)
        second=near(atr=tuple(history))
        self.assertEqual(first.distance_atr,second.distance_atr)
        self.assertNotEqual(first.preview_id,second.preview_id)

    def test_short_swing_identity_distinct_and_replay_deterministic(self):
        a=near(strategy=Strategy.SHORT)
        b=near(strategy=Strategy.SWING)
        self.assertEqual(a,near(strategy=Strategy.SHORT))
        self.assertEqual(a.distance_atr,b.distance_atr)
        self.assertNotEqual(a.preview_id,b.preview_id)

    def test_no_implicit_bad_threshold_zone_or_strategy(self):
        for bad in (True,0.25,"0.25",D("-1"),D("NaN")):
            with self.subTest(k=bad),self.assertRaises(PhaseEvidenceDenied):
                near(k=bad)
        with self.assertRaises(PhaseEvidenceDenied):
            near(zone="S5")
        with self.assertRaises(PhaseEvidenceDenied):
            near(strategy="SHORT")

    def test_untrusted_index_and_malformed_clock_fail_closed(self):
        with self.assertRaises(ValueError):
            near(candidate_index=True)
        self.assertIs(near(candidate_index=50).state,NearEvidenceState214.BLOCKED)
        with self.assertRaises(ValueError):
            near(as_of_utc=AS_OF.replace(tzinfo=None))

    def test_cannot_forge_market_attestation_or_trading_with_replace(self):
        result=near(k=D("0.2"))
        for patch in (
            {"status":DecisionStatus.DETECTED},
            {"status":DecisionStatus.NOT_DETECTED},
            {"support_resistance_attested":True},
            {"price_and_atr_independently_attested":True},
            {"parameter_approved":True},
            {"phase_executable":True},
            {"action_eligible":True},
            {"phase":"R_F"},
            {"candidate_in_band":None},
            {"preview_id":"FORGED"},
        ):
            with self.subTest(patch=patch),self.assertRaises(PhaseEvidenceDenied):
                replace(result,**patch)
        blocked=near(tf=Timeframe.H4)
        with self.assertRaises(PhaseEvidenceDenied):
            replace(blocked,distance_atr=D("0"))

    def test_no_trade_or_vendor_prices_in_preview_contract(self):
        result=near()
        self.assertIsInstance(result,CausalNearEvidence214)
        self.assertNotIn("open",result.__dict__)
        self.assertNotIn("close",result.__dict__)
        self.assertNotIn("volume",result.__dict__)
        self.assertNotIn("order",result.__dict__)
        self.assertFalse(result.action_eligible)


if __name__=="__main__":
    unittest.main()
