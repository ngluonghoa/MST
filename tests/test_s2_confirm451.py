"""§451 explicit S2 later H1/M15 causal swing-low close-cross fictional tests."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s2_context448 import S2ConfirmPlan451,S2State448
from test_s2_context448 import run
from test_s2_early450 import setup as early_setup
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap


def fixture(tf=Timeframe.M15,*,close=D(6),epsilon=D(0)):
    inputs,p=early_setup()
    existing=inputs.snapshots_for(tf)
    begin=inputs.snapshots_for(Timeframe.M15)[p.early.target_index].selected.verified_at_utc
    extra=[]
    for i,low in enumerate((9,7,9,9,6)):
        start=begin+timedelta(minutes=(20 if tf is Timeframe.M15 else 75)*(i+1))
        row=make_bar(2600+i,timeframe=tf,start=start,high=D(12),low=D(low),
                     close=close if i==4 else D(10))
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(row.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            row=replace(row,bar_end_utc=end,retrieved_at_utc=end+timedelta(minutes=1),
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(row))
    start=len(existing)
    rf=S2ConfirmPlan451(tf,start+4,start,1,1,1,TiePolicy.STRICT_V1,p.d1,0,15,epsilon)
    return alter(inputs,tf,existing+tuple(extra)),replace(p,rf=rf)


class S2Confirm451Tests(unittest.TestCase):
    def test_both_frames_both_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for strategy in Strategy:
                inputs,p=fixture(tf)
                row,safe=run(inputs,p,strategy)
                proof=row.private_preview.assessments[3][1]
                self.assertIs(proof.state,S2State448.MATCH)
                self.assertEqual(proof.private_micro_low,D(7))
                self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_strict_close_and_explicit_buffer(self):
        for close,epsilon,state in ((D(7),D(0),S2State448.NONMATCH),
                  (D(6),D(1),S2State448.NONMATCH),(D(6),None,S2State448.DISTANCE)):
            inputs,p=fixture(close=close,epsilon=epsilon)
            row,_=run(inputs,p)
            self.assertIs(row.private_preview.assessments[3][1].state,state)

    def test_missing_target_and_late_pivot_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.rf.timeframe)
        row,_=run(alter(inputs,p.rf.timeframe,rows[:-1]),p)
        self.assertIs(row.private_preview.assessments[3][1].state,S2State448.MISSING)
        late=snap(replace(rows[-3].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,p.rf.timeframe,rows[:-3]+(late,)+rows[-2:]),p)
        self.assertIs(row.private_preview.assessments[3][1].state,S2State448.BLOCKED)

    def test_new_d1_requires_current_window_and_no_critical_reclaim(self):
        inputs,p=fixture(Timeframe.H1)
        daily=inputs.snapshots_for(Timeframe.D1)
        early=inputs.snapshots_for(Timeframe.M15)[p.early.target_index].selected
        new=snap(make_bar(2700,start=early.verified_at_utc,high=D(18),close=D(17)))
        # Six-hour D1 interval is fully closed before the later H1 RF.
        # Move the H1 RF candidate series forward to make the update causal.
        hourly=inputs.snapshots_for(Timeframe.H1)
        changed=[]
        for x in hourly[p.rf.history_start:]:
            r=x.selected
            delta=timedelta(hours=8)
            key=replace(r.market_bar_key,bar_start_utc=r.market_bar_key.bar_start_utc+delta)
            obs=replace(r.observation_key,market_bar_key=key)
            rev=replace(r.observation_revision,observation_key=obs,
                first_known_time_utc=r.observation_revision.first_known_time_utc+delta,
                retrieved_at_utc=r.observation_revision.retrieved_at_utc+delta)
            changed.append(snap(replace(r,market_bar_key=key,observation_key=obs,observation_revision=rev,
                bar_end_utc=r.bar_end_utc+delta,retrieved_at_utc=r.retrieved_at_utc+delta,
                verified_at_utc=r.verified_at_utc+delta)))
        inputs=alter(alter(inputs,Timeframe.D1,daily+(new,)),Timeframe.H1,hourly[:p.rf.history_start]+tuple(changed))
        row,_=run(inputs,p)
        self.assertIs(row.private_preview.assessments[3][1].state,S2State448.BLOCKED)
        p=replace(p,rf=replace(p.rf,d1=replace(p.rf.d1,stop=16),atr_stop=16))
        row,_=run(inputs,p)
        self.assertIs(row.private_preview.assessments[3][1].state,S2State448.NONMATCH)

    def test_prior_phase_and_invalid_config(self):
        inputs,p=fixture()
        row,_=run(inputs,replace(p,early=replace(p.early,candidate_k_rejection=None)))
        self.assertIs(row.private_preview.assessments[3][1].state,S2State448.BLOCKED)
        for rf in (replace(p.rf,timeframe=Timeframe.D1),replace(p.rf,low_index=True),
                   replace(p.rf,candidate_epsilon=D(-1)),replace(p.rf,d1=replace(p.d1,stop=14))):
            _,safe=run(inputs,replace(p,rf=rf))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_determinism_and_no_action_authority(self):
        inputs,p=fixture()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        self.assertNotIn("private_micro_low",json.dumps(sa))
        old,_=run(inputs,replace(p,rf=None))
        self.assertEqual(len(old.private_preview.assessments),3)
