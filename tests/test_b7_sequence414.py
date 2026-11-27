"""§414 supplied D1 intermediate-window sequence, fictional."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7TrendWindow413
from swing_trading.market_data import Timeframe
from swing_trading.contracts import Strategy
from test_b7_trend413 import setup
from test_b7_support_preview409 import run
from test_causal_indicators import make_bar, snap


def fixture(*,choch=False,tf=Timeframe.M15,late=False,tail=False):
    inputs,p,variant=setup(choch=choch,tf=tf)
    daily=list(inputs.snapshots_for(Timeframe.D1))
    rc=inputs.snapshots_for(Timeframe.M15)[p.target_index].market_bar_key.bar_start_utc
    for i in range(3+int(tail)):
        price=D(8)-D(i)/5
        row=make_bar(700+i,start=rc+timedelta(days=i),open_price=price,
                     high=price+1,low=price-1,close=price)
        if late and i==0:
            row=replace(row,verified_at_utc=rc+timedelta(days=2,hours=7))
        daily.append(snap(row))
    rf=list(inputs.snapshots_for(tf))
    for i in range(p.rf.history_start,len(rf)):
        old=rf[i].selected
        begin=old.market_bar_key.bar_start_utc+timedelta(days=4)
        bar=make_bar(800+i,timeframe=tf,start=begin,open_price=old.open,
                     high=old.high,low=old.low,close=old.close)
        if tf is Timeframe.H1:
            end=begin+timedelta(hours=1)
            rev=replace(bar.observation_revision,first_known_time_utc=end,
                        retrieved_at_utc=end+timedelta(minutes=1))
            bar=replace(bar,bar_end_utc=end,retrieved_at_utc=rev.retrieved_at_utc,
                        verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rf[i]=snap(bar)
    inputs=replace(inputs,buckets=tuple((frame,tuple(daily) if frame is Timeframe.D1
                    else tuple(rf) if frame is tf else items) for frame,items in inputs.buckets))
    def w(i):
        return B7TrendWindow413(i,60+i,(10-i,30-i),(20-i,40-i))
    return inputs,replace(p,trend=replace(p.trend,rf=w(3),intermediate=(w(1),w(2)))),variant


def evaluate(*,strategy=Strategy.SHORT,**kwargs):
    inputs,p,variant=fixture(**kwargs)
    return run(inputs,p,variant=variant,strategy=strategy)


class B7Sequence414Tests(unittest.TestCase):
    def test_complete_explicit_sequence(self):
        for strategy in Strategy:
            for choch in (True,False):
                for tf in (Timeframe.M15,Timeframe.H1):
                    row,safe=evaluate(strategy=strategy,choch=choch,tf=tf)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
                    self.assertEqual(row.private_preview.assessments[-1][1].reason,"SUPPLIED_D1_WINDOW_SEQUENCE_ONLY")

    def test_middle_nonmatch_cannot_be_hidden_by_endpoints(self):
        inputs,p,variant=fixture()
        w=replace(p.trend.intermediate[0],high_indices=(10,29))
        trend=replace(p.trend,intermediate=(w,p.trend.intermediate[1]))
        _,safe=run(inputs,replace(p,trend=trend),variant=variant)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_and_skipped_tail_block(self):
        for kwargs in ({"late":True},{"tail":True}):
            _,safe=evaluate(**kwargs)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_exact_intermediate_sequence_no_silent_omission(self):
        inputs,p,variant=fixture()
        for middle in ((),p.trend.intermediate[1:],p.trend.intermediate[::-1],list(p.trend.intermediate)):
            _,safe=run(inputs,replace(p,trend=replace(p.trend,intermediate=middle)),variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_zero_new_daily_and_legacy_endpoint_only(self):
        inputs,p,variant=setup()
        row,safe=run(inputs,replace(p,trend=replace(p.trend,intermediate=())),variant=variant)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(row.private_preview.assessments[-1][1].reason,"SUPPLIED_D1_WINDOW_SEQUENCE_ONLY")
        row,_=run(inputs,p,variant=variant)
        self.assertEqual(row.private_preview.assessments[-1][1].reason,"D1_PAIRED_FALLING_GEOMETRY_ONLY")

    def test_redaction_and_no_authority(self):
        row,safe=evaluate()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("intermediate","high_indices","SUPPLIED_D1_WINDOW_SEQUENCE_ONLY",fixture()[0].instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
