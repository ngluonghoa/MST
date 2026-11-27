"""§448 S2 D1 bearish context + H1 LH fictional candidates."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375,evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.s2_context448 import S2ContextPlan448,S2Window448
from test_b7_support_preview409 import model
from test_causal_indicators import make_bar,snap


def fixture(*,rising=False,h1_rising=False,anchor_close=D(10)):
    inputs=model()
    anchor=inputs.snapshots_for(Timeframe.M15)[0].selected
    anchor=snap(replace(anchor,open=anchor_close,high=max(anchor_close,anchor.high),
                        low=min(anchor_close,anchor.low),close=anchor_close))
    start=anchor.market_bar_key.bar_start_utc
    daily=[]
    hourly=[]
    for i in range(9):
        h=D(20 if i==1 else (22 if rising else 16) if i==5 else 12)
        l=D(8 if i==3 else 6 if i==7 else 9)
        row=make_bar(2000+i,start=start-timedelta(days=10-i),high=h,low=l)
        daily.append(snap(row))
    for i in range(7):
        h=D(16 if i==1 else (18 if h1_rising else 14) if i==5 else 12)
        begin=start-timedelta(hours=16-2*i)
        end=begin+timedelta(hours=1)
        row=make_bar(2100+i,timeframe=Timeframe.H1,start=begin,high=h,low=D(9))
        rev=replace(row.observation_revision,first_known_time_utc=end,retrieved_at_utc=end+timedelta(minutes=1))
        row=replace(row,bar_end_utc=end,retrieved_at_utc=end+timedelta(minutes=1),
                    verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        hourly.append(snap(row))
    data={Timeframe.D1:tuple(daily),Timeframe.H1:tuple(hourly),Timeframe.M15:(anchor,)}
    inputs=replace(inputs,buckets=tuple((f,data.get(f,rows)) for f,rows in inputs.buckets))
    d=S2Window448(0,9,(1,5),(3,7),1,1,TiePolicy.STRICT_V1)
    h=S2Window448(0,7,(1,5),None,1,1,TiePolicy.STRICT_V1)
    return inputs,S2ContextPlan448(0,d,h)


def run(inputs,p,strategy=Strategy.SHORT):
    result=evaluate_baseline_preview(inputs,requests=(BaselinePreviewRequest375("S2",strategy,"S2/BASE",p),))
    row=next(r for r in result.rows if r.decision.zone_id=="S2" and r.decision.strategy is strategy)
    safe=next(r for r in result.safe_phase_summary()["zones"] if r["zone_id"]=="S2" and r["strategy"]==strategy.value)
    return row,safe


class S2Context448Tests(unittest.TestCase):
    def test_both_strategies_full_context(self):
        for strategy in Strategy:
            inputs,p=fixture()
            row,safe=run(inputs,p,strategy)
            g=row.private_preview.assessments[0][1]
            self.assertEqual((g.private_d1_lh,g.private_d1_ll,g.private_resistance),(D(16),D(6),D(14)))
            self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_rising_or_critical_lh_reclaim_nonmatch(self):
        for kw in ({"rising":True},{"h1_rising":True},{"anchor_close":D(16)}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_h1_no_d1_fallback(self):
        inputs,p=fixture()
        for tf in (Timeframe.D1,Timeframe.H1,Timeframe.M15):
            altered=replace(inputs,buckets=tuple((f,() if f is tf else rows) for f,rows in inputs.buckets))
            _,safe=run(altered,p)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")

    def test_late_right_and_stale_supplied_window(self):
        inputs,p=fixture()
        for tf,plan in ((Timeframe.D1,p.d1),(Timeframe.H1,p.h1)):
            rows=inputs.snapshots_for(tf)
            cutoff=inputs.snapshots_for(Timeframe.M15)[0].market_bar_key.bar_start_utc
            late=snap(replace(rows[-1].selected,verified_at_utc=cutoff+timedelta(minutes=1)))
            altered=replace(inputs,buckets=tuple((f,rows[:-1]+(late,) if f is tf else s) for f,s in inputs.buckets))
            _,safe=run(altered,p)
            self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,h1=replace(p.h1,stop=6)))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"BLOCKED")

    def test_invalid_plan_fail_closed(self):
        inputs,p=fixture()
        for changed in (replace(p,anchor_index=True),replace(p,d1=replace(p.d1,low_indices=None)),
                        replace(p,h1=replace(p.h1,low_indices=(1,5))),
                        replace(p,d1=replace(p.d1,high_indices=(True,5)))):
            _,safe=run(inputs,changed)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_no_authority_and_redaction(self):
        inputs,p=fixture()
        a,sa=run(inputs,p)
        b,sb=run(inputs,p)
        self.assertEqual(a.private_preview,b.private_preview)
        self.assertEqual(sa,sb)
        self.assertFalse(a.private_preview.action_eligible)
        self.assertEqual(sa["status"],"UNVERIFIED")
        for key in ("private_d1_lh","private_d1_ll","private_resistance",inputs.instrument_id):
            self.assertNotIn(key,json.dumps(sa))
