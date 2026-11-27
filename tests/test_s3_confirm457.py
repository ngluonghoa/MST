"""§457 S3 later H1/M15 micro low close-cross while D1 remains rising."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s3_context454 import S3ConfirmPlan457,S3State454
from test_s3_choch456 import fixture as early_fixture
from test_s3_context454 import run
from test_s2_rally449 import alter
from test_causal_indicators import make_bar,snap

VARIANT="S3/F_MICRO_BREAK"


def fixture(tf=Timeframe.M15,*,close=D(11),epsilon=D(0),context=Timeframe.D1):
    inputs,p=early_fixture(context)
    existing=inputs.snapshots_for(tf)
    begin=inputs.snapshots_for(Timeframe.M15)[p.choch.target_index].selected.verified_at_utc
    extra=[]
    for i,low in enumerate((13,12,13,13,11)):
        start=begin+timedelta(minutes=(20 if tf is Timeframe.M15 else 75)*(i+1))
        c=close if i==4 else D(14)
        row=make_bar(3600+i,timeframe=tf,start=start,open_price=c,high=max(D(16),c),
                     low=min(D(low),c),close=c)
        if tf is Timeframe.H1:
            end=start+timedelta(hours=1)
            rev=replace(row.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            row=replace(row,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        extra.append(snap(row))
    start=len(existing)
    rf=S3ConfirmPlan457(tf,start+4,start,1,1,1,TiePolicy.STRICT_V1,p.d1,0,15,epsilon)
    return alter(inputs,tf,existing+tuple(extra)),replace(p,rf=rf)


class S3Confirm457Tests(unittest.TestCase):
    def test_both_frames_and_strategies(self):
        for tf in (Timeframe.H1,Timeframe.M15):
            for strategy in Strategy:
                inputs,p=fixture(tf)
                row,safe=run(inputs,p,strategy,VARIANT)
                route,g=row.private_preview.assessments[3]
                self.assertIs(route.selected_frame,tf)
                self.assertEqual(row.private_preview.assessments[2][0].variant_id,"S3/E_MICRO_CHOCH")
                self.assertIs(g.state,S3State454.MATCH)
                self.assertEqual((g.private_higher_low,g.private_confirm_low),(D(8),D(12)))
                self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_close_boundary_buffer_major_loss(self):
        for close,e,state in ((D(12),D(0),S3State454.NONMATCH),(D(11),D(100),S3State454.NONMATCH),
                              (D(11),None,S3State454.DISTANCE),(D(7),D(0),S3State454.NONMATCH)):
            inputs,p=fixture(close=close,epsilon=e)
            row,_=run(inputs,p,variant=VARIANT)
            self.assertIs(row.private_preview.assessments[3][1].state,state)

    def test_missing_or_late_pivot_witness(self):
        inputs,p=fixture()
        rows=inputs.snapshots_for(p.rf.timeframe)
        row,_=run(alter(inputs,p.rf.timeframe,rows[:-1]),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[3][1].state,S3State454.MISSING)
        late=snap(replace(rows[-3].selected,verified_at_utc=rows[-2].market_bar_key.bar_start_utc+timedelta(minutes=1)))
        row,_=run(alter(inputs,p.rf.timeframe,rows[:-3]+(late,)+rows[-2:]),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[3][1].state,S3State454.BLOCKED)

    def test_intervening_m15_breakout_during_h1_confirmation(self):
        inputs,p=fixture(Timeframe.H1)
        rows=inputs.snapshots_for(Timeframe.M15)
        start=rows[-1].selected.verified_at_utc+timedelta(minutes=30)
        bad=snap(make_bar(3700,timeframe=Timeframe.M15,start=start,high=D(21),close=D(21)))
        row,_=run(alter(inputs,Timeframe.M15,rows+(bad,)),p,variant=VARIANT)
        self.assertIs(row.private_preview.assessments[3][1].state,S3State454.NONMATCH)

    def test_prior_phase_and_invalid_configuration(self):
        inputs,p=fixture()
        row,_=run(inputs,replace(p,choch=replace(p.choch,candidate_epsilon=None)),variant=VARIANT)
        self.assertIs(row.private_preview.assessments[3][1].state,S3State454.BLOCKED)
        for bad in (replace(p.rf,timeframe=Timeframe.D1),replace(p.rf,low_index=True),
                    replace(p.rf,candidate_epsilon=D(-1)),replace(p.rf,d1=replace(p.d1,stop=14))):
            _,safe=run(inputs,replace(p,rf=bad),variant=VARIANT)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,p,variant="S3/F_TP")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_legacy_and_no_authority(self):
        inputs,p=fixture(context=Timeframe.W1)
        a,sa=run(inputs,p,variant=VARIANT)
        b,sb=run(inputs,p,variant=VARIANT)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in sa["phases"]))
        for secret in ("private_confirm_low","private_micro_hl",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(sa))
        old,_=run(inputs,replace(p,rf=None),variant="S3/E_MICRO_CHOCH")
        self.assertEqual(len(old.private_preview.assessments),3)
