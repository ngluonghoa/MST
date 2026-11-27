"""§492 S8 causal feature distribution, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_exhaustion492 import ExhaustionFeaturePlan492
from swing_trading.causal_indicators import VolumeBasis,VolumeBasisWitness
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s8_context492 import S8ContextPlan492
from swing_trading.engine import evaluate_baseline_preview
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_b7_support_preview409 import model
from test_causal_indicators import make_bar,snap,START
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(*,close=D(20),volume=300):
    inputs=model()
    daily=tuple(snap(make_bar(7000+i,start=START+timedelta(days=i),
        close=close if i==25 else D(10),open_price=D(10),
        high=max(D(12),close) if i==25 else D(12),low=D(8),
        volume=volume if i==25 else 100)) for i in range(26))
    witnesses=tuple(VolumeBasisWitness(daily[i].selected,VolumeBasis.RAW_MATCHED_SHARES,
        "fictional-regime",str(i),daily[i].selected.verified_at_utc) for i in (15,16,17,18,19,25))
    return alter(inputs,Timeframe.D1,daily),S8ContextPlan492(
        ExhaustionFeaturePlan492(0,25,5,5,D(".9"),"fictional-volume",witnesses))


def evaluate(inputs,p,strategy=Strategy.SHORT):
    r=evaluate_baseline_preview(inputs,requests=(request("S8",p,strategy),))
    a=row(r,"S8",strategy)
    s=next(x for x in r.safe_phase_summary()["zones"] if x["zone_id"]=="S8" and x["strategy"]==strategy.value)
    return a,s


def r0(inputs,p,strategy=Strategy.SHORT):
    a,s=evaluate(inputs,p,strategy)
    return a.private_preview.assessments[0][1],s


class S8Context492Tests(unittest.TestCase):
    def test_exact_disjoint_distribution_both_strategies(self):
        for strategy in Strategy:
            inputs,p=fixture()
            g,s=r0(inputs,p,strategy)
            self.assertIs(g.state,S1State439.MATCH)
            f=g.private_features
            self.assertEqual((f.target_return,f.reference_return),(D(1),D(0)))
            self.assertEqual((f.target_range_atr,f.reference_range_atr),(D(3),D(1)))
            self.assertEqual((f.target_volume,f.reference_volume),(300,100))
            self.assertEqual(s["status"],"UNVERIFIED")

    def test_signed_return_and_zero_target_volume(self):
        inputs,p=fixture(close=D(9),volume=0)
        g,_=r0(inputs,p)
        self.assertIs(g.state,S1State439.MATCH)
        self.assertEqual(g.private_features.target_return,D("-.1"))
        self.assertEqual(g.private_features.target_volume,0)

    def test_missing_and_late_reference(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(Timeframe.D1)
        self.assertIs(r0(alter(inputs,Timeframe.D1,rows[:-1]),p)[0].state,S1State439.MISSING)
        late=snap(replace(rows[14].selected,verified_at_utc=rows[15].market_bar_key.bar_start_utc+timedelta(seconds=1)))
        self.assertIs(r0(alter(inputs,Timeframe.D1,rows[:14]+(late,)+rows[15:]),p)[0].state,S1State439.BLOCKED)

    def test_raw_witness_and_regime_required(self):
        inputs,p=fixture()
        f=p.features
        for w in (replace(f.witnesses[-1],basis=VolumeBasis.UNKNOWN),
                  replace(f.witnesses[-1],share_regime_id="other"),
                  replace(f.witnesses[-1],verified_at_utc=f.witnesses[-1].verified_at_utc+timedelta(seconds=1))):
            q=replace(p,features=replace(f,witnesses=f.witnesses[:-1]+(w,)))
            self.assertIs(r0(inputs,q)[0].state,S1State439.BLOCKED)

    def test_explicit_plan_and_bounds(self):
        inputs,p=fixture()
        for kw in (dict(return_span=4),dict(quantile=D(0)),dict(reference_count=True),dict(witnesses=())):
            _,s=evaluate(inputs,replace(p,features=replace(p.features,**kw)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction(self):
        inputs,p=fixture()
        candidate=profile((request("S8",p),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S8").private_preview.assessments[0][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in ("private_features","target_return","reference_volume","fictional-regime"):
                self.assertNotIn(key,json.dumps(s))
