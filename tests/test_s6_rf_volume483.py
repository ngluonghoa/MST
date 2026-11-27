"""§483 synthetic same-frame raw RF volume and fail-closed scope tests."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis,VolumeBasisWitness,VolumeSessionClass
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_context_preview439 import S1State439
from swing_trading.s6_rf_volume483 import S6VolumePlan483,S6RFVolumePlan483
from swing_trading.unified_mode459 import EngineMode,evaluate_candidate
from test_s6_confirm482 import fixture as confirm_fixture
from test_s6_breakout479 import evaluate
from test_causal_indicators import make_bar,snap
from test_s2_rally449 import alter
from test_baseline_engine375 import request,row
from test_unified_mode459 import profile


def fixture(tf=Timeframe.H1,*,volume=250,threshold=D("2.5"),prefix=True):
    inputs,g=confirm_fixture(tf)
    rows=inputs.snapshots_for(tf)
    if tf is Timeframe.H1 and prefix:
        first=rows[0].selected.market_bar_key.bar_start_utc
        older=tuple(snap(make_bar(7000+i,timeframe=tf,start=first-timedelta(hours=2*(20-i))))
                    for i in range(20))
        e=g.early
        f=e.failure
        b=f.breakout
        b=replace(b,history_start=b.history_start+20,target_index=b.target_index+20)
        f=replace(f,breakout=b,failure_index=f.failure_index+20)
        g=replace(g,early=replace(e,failure=f),history_start=g.history_start+20,target_index=g.target_index+20)
        rows=older+rows
    i=g.target_index
    rows=rows[:i]+(snap(replace(rows[i].selected,volume=volume)),)+rows[i+1:]
    session=VolumeSessionClass.DAILY if tf is Timeframe.D1 else VolumeSessionClass.CONTINUOUS
    window=rows[max(0,i-20):i+1]
    w=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,"fixture-s6-regime",
                               "fixture-s6-witness-"+str(j),s.selected.verified_at_utc)
            for j,s in enumerate(window))
    if len(w)<21:
        w=(w[0],)*(21-len(w))+w
    return alter(inputs,tf,rows),S6VolumePlan483(g,S6RFVolumePlan483("fixture-s6-policy",(session,)*21,w,threshold))


def rf(inputs,p,strategy=Strategy.SHORT):
    r,s=evaluate(inputs,p,strategy)
    return r.private_preview.assessments[-1][1],s


class S6Volume483Tests(unittest.TestCase):
    def test_both_frames_strategies_and_exact_boundary(self):
        for tf in (Timeframe.H1,Timeframe.D1):
            for strategy in Strategy:
                inputs,p=fixture(tf)
                g,s=rf(inputs,p,strategy)
                self.assertIs(g.state,S1State439.MATCH)
                self.assertEqual(g.private_rvol.value,D("2.5"))
                self.assertFalse(g.private_rvol.actionable)
                self.assertEqual(s["status"],"UNVERIFIED")
                self.assertFalse(s["phases"][3]["action_eligible"])

    def test_low_volume_and_no_default(self):
        for kwargs,state in ((dict(volume=249),S1State439.NONMATCH),(dict(threshold=None),S1State439.DISTANCE)):
            inputs,p=fixture(**kwargs)
            self.assertIs(rf(inputs,p)[0].state,state)

    def test_missing_exact_prior_window(self):
        inputs,p=fixture(prefix=False)
        self.assertIs(rf(inputs,p)[0].state,S1State439.MISSING)

    def test_wrong_basis_scope_late_and_class(self):
        inputs,p=fixture()
        v=p.volume
        w=v.witnesses[-1]
        for bad in (replace(w,basis=VolumeBasis.UNKNOWN),
                    replace(w,candle=v.witnesses[0].candle),
                    replace(w,verified_at_utc=w.verified_at_utc+timedelta(seconds=1))):
            q=replace(p,volume=replace(v,witnesses=v.witnesses[:-1]+(bad,)))
            self.assertIs(rf(inputs,q)[0].state,S1State439.BLOCKED)
        for classes in ((VolumeSessionClass.DAILY,)*21,v.session_classes[:-1]+(VolumeSessionClass.CLOSING_AUCTION,)):
            self.assertIs(rf(inputs,replace(p,volume=replace(v,session_classes=classes)))[0].state,S1State439.BLOCKED)

    def test_no_geometry_bypass_or_bad_plan(self):
        inputs,p=fixture()
        g=replace(p.geometry,candidate_epsilon=D(10))
        self.assertIs(rf(inputs,replace(p,geometry=g))[0].state,S1State439.NONMATCH)
        for v in (replace(p.volume,candidate_min_rvol=D(0)),replace(p.volume,witnesses=p.volume.witnesses[:-1]),
                  replace(p.volume,comparison_policy_version="")):
            _,s=evaluate(inputs,replace(p,volume=v))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in s["phases"]))

    def test_shared_modes_redaction_and_legacy(self):
        inputs,p=fixture()
        candidate=profile((request("S6",p,variant="S6/BASE"),))
        for mode in (EngineMode.RESEARCH,EngineMode.VALIDATION):
            r=evaluate_candidate(inputs,mode=mode,profile=candidate)
            self.assertIs(row(r.private_preview,"S6").private_preview.assessments[-1][1].state,S1State439.MATCH)
            s=r.safe_summary()
            self.assertFalse(s["publication_allowed"])
            for key in ("private_rvol","fixture-s6-regime","fixture-s6-witness","fixture-s6-policy"):
                self.assertNotIn(key,json.dumps(s))
        g,s=rf(inputs,p.geometry)
        self.assertIs(g.state,S1State439.MATCH)
        self.assertFalse(hasattr(g,"private_rvol"))
