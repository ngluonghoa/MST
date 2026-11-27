"""§493 S8 explicit acceleration and exhaustion shapes, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s8_context492 import S8ExhaustionMode493,S8ExhaustionPlan493
from swing_trading.causal_indicators import VolumeBasis
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s8_context492 import fixture as context,evaluate
from test_causal_indicators import snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile

RANGE=S8ExhaustionMode493.RANGE_UPPER_WICK
VOLUME=S8ExhaustionMode493.VOLUME_CLIMAX


def fixture(mode=VOLUME,**kw):
    inputs,p=context(**kw)
    rows=inputs.snapshots_for(Timeframe.D1)
    if mode is RANGE:
        target=snap(replace(rows[-1].selected,high=D(30)))
        inputs=alter(inputs,Timeframe.D1,rows[:-1]+(target,))
        p=replace(p,features=replace(p.features,witnesses=p.features.witnesses[:-1]+
            (replace(p.features.witnesses[-1],candle=target.selected),)))
    b=inputs.snapshots_for(Timeframe.D1)[p.features.target_index].selected
    return inputs,S8ExhaustionPlan493(p,mode,D(".5"),D(2) if mode is RANGE else None,
        D(".4") if mode is RANGE else None,D(2) if mode is VOLUME else None,
        b.source_event_ids[0],b.observation_revision.source_revision_or_payload_digest,
        b.market_bar_key.bar_start_utc,b.verified_at_utc,
        b.market_bar_key.bar_start_utc-timedelta(days=6),b.verified_at_utc+timedelta(days=10))


def rc(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[1][1],s


class S8Exhaustion493Tests(unittest.TestCase):
    def test_both_strategies_and_explicit_shapes(self):
        for strategy in Strategy:
            for mode in (RANGE,VOLUME):
                inputs,p=fixture(mode)
                g,s=rc(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_mode,mode)
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][1]["action_eligible"])

    def test_positive_acceleration_required_and_no_fallback(self):
        for kw in (dict(close=D(10)),dict(volume=199),dict(close=D(14))):
            inputs,p=fixture(**kw)
            self.assertIs(rc(inputs,p)[0].state,S1State439.NONMATCH)
        inputs,p=fixture(RANGE)
        self.assertIs(rc(inputs,replace(p,candidate_min_upper_wick=D(".9")))[0].state,S1State439.NONMATCH)

    def test_unconfigured_threshold_and_wrong_event(self):
        inputs,p=fixture()
        for q in (replace(p,candidate_min_return=None),replace(p,candidate_min_volume_multiple=None)):
            self.assertIs(rc(inputs,q)[0].state,S1State439.DISTANCE)
        for q in (replace(p,event_id="wrong"),replace(p,revision_digest="wrong"),
                  replace(p,event_known_at_utc=p.event_known_at_utc-timedelta(seconds=1))):
            self.assertIs(rc(inputs,q)[0].state,S1State439.BLOCKED)

    def test_no_r0_bypass(self):
        inputs,p=fixture()
        f=p.context.features
        q=replace(p,context=replace(p.context,features=replace(f,witnesses=f.witnesses[:-1]+
            (replace(f.witnesses[-1],basis=VolumeBasis.UNKNOWN),))))
        self.assertIs(rc(inputs,q)[0].state,S1State439.BLOCKED)

    def test_explicit_mode_and_policy(self):
        inputs,p=fixture()
        for q in (replace(p,mode="VOLUME_CLIMAX"),replace(p,candidate_min_range_atr=D(2)),
                  replace(p,candidate_min_volume_multiple=D(1)),replace(p,policy_known_at_utc=p.bar_start_utc+timedelta(seconds=1))):
            _,s=evaluate(inputs,q)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=profile((request("S8",p),)))
            self.assertIs(row(r.private_preview,"S8").private_preview.assessments[1][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in (p.event_id,"private_event_known","private_high","private_mode"):
                self.assertNotIn(key,json.dumps(s))
        r,_=evaluate(inputs,p.context)
        self.assertEqual(len(r.private_preview.assessments),1)
