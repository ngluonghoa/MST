"""§412 B7 causal later RF micro-high break, fictional only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7ConfirmPlan412, B7SupportState409
from swing_trading.causal_structure_geometry import TiePolicy
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import run
from test_b7_reclaim410 import data as reclaim_data, config as reclaim_config
from test_b7_choch411 import data as choch_data, config as choch_config
from test_causal_indicators import make_bar, snap


def fixture(*, choch=False, tf=Timeframe.M15, close=D("13"), late=False, missing=False, early_bad=False):
    base = (choch_data(close=D("11") if early_bad else D("13")) if choch
            else reclaim_data(close=D("6") if early_bad else D("8")))
    m15 = base.snapshots_for(Timeframe.M15)
    start = m15[-1].selected.bar_end_utc + timedelta(hours=2)
    rows = []
    for i,(hi,p) in enumerate(zip((10,12,10,11,15),(D(9),D(11),D(9),D(10),close))):
        begin = start + timedelta(hours=2*i)
        bar = make_bar(500+i,timeframe=tf,start=begin,open_price=p,close=p,high=D(hi),low=D(6))
        if tf is Timeframe.H1:
            end = begin + timedelta(hours=1)
            retrieved = end + timedelta(minutes=1)
            rev = replace(bar.observation_revision,first_known_time_utc=end,retrieved_at_utc=retrieved)
            bar = replace(bar,bar_end_utc=end,retrieved_at_utc=retrieved,
                          verified_at_utc=end+timedelta(minutes=2),observation_revision=rev)
        rows.append(snap(bar))
    if late:
        m15 = m15[:-1]+(snap(replace(m15[-1].selected,verified_at_utc=rows[3].selected.bar_end_utc)),)
    offset = len(m15) if tf is Timeframe.M15 else 0
    selected = (m15 if tf is Timeframe.M15 else ()) + tuple(rows[:-1] if missing else rows)
    inputs = replace(base,buckets=tuple((frame,selected if frame is tf else m15 if frame is Timeframe.M15 else items)
                                       for frame,items in base.buckets))
    p = choch_config() if choch else reclaim_config()
    rf = B7ConfirmPlan412(tf,offset+4,offset,offset+3,1,1,1,TiePolicy.STRICT_V1,D("0.1"))
    return inputs,replace(p,rf=rf),"B7/E_CHOCH" if choch else "B7/E_RECLAIM"


def evaluate(*, strategy=Strategy.SHORT, **kwargs):
    inputs,p,variant = fixture(**kwargs)
    return run(inputs,p,strategy=strategy,variant=variant)


class B7RF412Tests(unittest.TestCase):
    def test_both_strategies_variants_and_frames(self):
        for strategy in Strategy:
            for choch in (False,True):
                for tf in (Timeframe.M15,Timeframe.H1):
                    row,safe=evaluate(strategy=strategy,choch=choch,tf=tf)
                    route,proof=row.private_preview.assessments[-1]
                    self.assertIs(route.selected_frame,tf)
                    self.assertIs(proof.state,B7SupportState409.MATCH)
                    self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_or_equal_close_nonmatch(self):
        for close in (D("11"),D("12")):
            row,_=evaluate(close=close)
            self.assertIs(row.private_preview.assessments[-1][1].state,B7SupportState409.NONMATCH)

    def test_late_or_nonmatching_early_blocks(self):
        for kwargs in ({"late":True},{"early_bad":True}):
            _,safe=evaluate(**kwargs)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_missing_exact_frame_or_early_no_fallback(self):
        for tf in (Timeframe.M15,Timeframe.H1):
            _,safe=evaluate(tf=tf,missing=True)
            self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        inputs,p,variant=fixture()
        _,safe=run(inputs,replace(p,reclaim=None),variant=variant)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_invalid_scope_and_legacy(self):
        inputs,p,variant=fixture()
        for rf in (replace(p.rf,timeframe=Timeframe.D1),replace(p.rf,breakout_index=True),
                   replace(p.rf,candidate_epsilon=None),replace(p.rf,history_stop=p.rf.breakout_index)):
            _,safe=run(inputs,replace(p,rf=rf),variant=variant)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(inputs,replace(p,rf=None),variant=variant)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"NOT_REQUESTED")

    def test_redaction_no_trade_authority(self):
        row,safe=evaluate()
        self.assertFalse(row.private_preview.action_eligible)
        self.assertEqual(safe["status"],"UNVERIFIED")
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in (fixture()[0].instrument_id,"pivot_index","candidate_epsilon","private_atr"):
            self.assertNotIn(secret,json.dumps(safe))
