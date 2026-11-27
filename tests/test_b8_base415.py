"""§415 B8 base width and resistance candidate, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b8_base_preview415 import B8BasePlan415, B8State415
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import model
from test_causal_indicators import make_bar, snap


def fixture(tf=Timeframe.D1, *, late=False, missing=False, not_upper=False):
    inputs=model()
    start=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
    daily=list(inputs.snapshots_for(Timeframe.D1))
    if tf is Timeframe.D1:
        for i in (4,5,6,7,8):
            row=daily[i].selected
            high=D(15 if i==5 else 16 if i==8 and not_upper else 12)
            daily[i]=snap(replace(row,high=high))
        if late:
            daily[8]=snap(replace(daily[8].selected,verified_at_utc=start+timedelta(minutes=1)))
        lo,hi,pivot=4,9,1
        hourly=inputs.snapshots_for(Timeframe.H1)
    else:
        hourly=[]
        for i in range(5):
            begin=start-timedelta(hours=12-2*i)
            high=D(15 if i==1 else 16 if i==4 and not_upper else 12)
            row=make_bar(1000+i,timeframe=tf,start=begin,high=high)
            end=begin+timedelta(hours=1)
            rev=replace(row.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            row=replace(row,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=start+timedelta(minutes=1) if late and i==4
                        else end+timedelta(minutes=2),observation_revision=rev)
            hourly.append(snap(row))
        lo,hi,pivot=0,5,1
    buckets={Timeframe.D1:tuple(daily),Timeframe.H1:tuple(hourly),
             Timeframe.M15:() if missing else inputs.snapshots_for(Timeframe.M15)}
    inputs=replace(inputs,buckets=tuple((frame,buckets.get(frame,items))
                                       for frame,items in inputs.buckets))
    p=B8BasePlan415(tf,0,lo,hi,pivot,1,1,TiePolicy.STRICT_V1,0,15,D(10))
    return inputs,p


def run(inputs,p,*,strategy=Strategy.SHORT,variant="B8/BASE"):
    preview=evaluate_baseline_preview(inputs,requests=(BaselinePreviewRequest375("B8",strategy,variant,p),))
    row=next(r for r in preview.rows if r.decision.zone_id=="B8" and r.decision.strategy is strategy)
    safe=next(r for r in preview.safe_phase_summary()["zones"]
              if r["zone_id"]=="B8" and r["strategy"]==strategy.value)
    return row,safe


class B8Base415Tests(unittest.TestCase):
    def test_both_strategies_variants_and_frames(self):
        for strategy in Strategy:
            for variant in ("B8/BASE","B8/INTRADAY_RVOL_TOD_PENDING"):
                for tf in (Timeframe.D1,Timeframe.H1):
                    data,p=fixture(tf)
                    row,safe=run(data,p,strategy=strategy,variant=variant)
                    route,proof=row.private_preview.assessments[0]
                    self.assertIs(route.selected_frame,tf)
                    self.assertIs(proof.state,B8State415.MATCH)
                    self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_upper_boundary_and_width_nonmatch(self):
        for tf in (Timeframe.D1,Timeframe.H1):
            data,p=fixture(tf,not_upper=True)
            row,_=run(data,p)
            self.assertIs(row.private_preview.assessments[0][1].state,B8State415.NONMATCH)
        data,p=fixture()
        row,_=run(data,replace(p,candidate_max_width_atr=D(0)))
        self.assertIs(row.private_preview.assessments[0][1].state,B8State415.NONMATCH)

    def test_no_default_threshold(self):
        data,p=fixture()
        row,safe=run(data,replace(p,candidate_max_width_atr=None))
        self.assertIs(row.private_preview.assessments[0][1].state,B8State415.DISTANCE)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"DISTANCE_ONLY")

    def test_late_and_missing_no_fallback(self):
        for tf in (Timeframe.D1,Timeframe.H1):
            data,p=fixture(tf,late=True)
            _,safe=run(data,p)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        data,p=fixture(missing=True)
        row,_=run(data,p)
        self.assertIs(row.private_preview.assessments[0][1].state,B8State415.MISSING)

    def test_explicit_scope_invalid(self):
        data,p=fixture()
        for bad in (replace(p,timeframe=Timeframe.M15),replace(p,target_index=True),
                    replace(p,candidate_max_width_atr=D("-1")),replace(p,base_stop=p.base_start+2)):
            _,safe=run(data,bad)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_redaction_and_no_authority(self):
        data,p=fixture()
        row,safe=run(data,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_resistance","width_atr","candidate_max_width_atr",data.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
