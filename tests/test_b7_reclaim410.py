"""§410 closed M15 same-support reclaim; fictional data only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b7_support_preview409 import B7ReclaimPlan410, B7SupportState409
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from test_b7_support_preview409 import model, plan, run
from test_causal_indicators import make_bar, snap


def data(*, prior=D("6"), close=D("8"), late=False, missing=False, wick=False):
    base = model()
    old = base.snapshots_for(Timeframe.M15)[0].selected
    start = old.market_bar_key.bar_start_utc
    nxt = make_bar(101, timeframe=Timeframe.M15, start=start+timedelta(minutes=30),
                   open_price=D("7"), close=close, low=D("5"), high=D("12"))
    old = replace(old, open=D("7"), close=prior, low=min(prior,D("6")))
    if late:
        old = replace(old, verified_at_utc=nxt.bar_end_utc)
    rows = (snap(old),) if missing else (snap(old),snap(nxt))
    return replace(base,buckets=tuple((tf,rows if tf is Timeframe.M15 else items)
                                      for tf,items in base.buckets))


def config(epsilon=D("0.1")):
    return replace(plan(), reclaim=B7ReclaimPlan410(epsilon))


class B7Reclaim410Tests(unittest.TestCase):
    def test_same_support_both_strategies(self):
        for strategy in Strategy:
            row,safe=run(data(),config(),strategy=strategy)
            self.assertIs(row.private_preview.assessments[1][1].state,B7SupportState409.MATCH)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"DISTANCE_ONLY")
            self.assertEqual(safe["phases"][2]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_wick_equal_and_already_above_nonmatch(self):
        for inputs in (data(close=D("6")),data(close=D("7")),data(prior=D("8"))):
            row,_=run(inputs,config())
            self.assertIs(row.private_preview.assessments[1][1].state,B7SupportState409.NONMATCH)

    def test_explicit_buffer(self):
        row,_=run(data(),config(D("1")))
        self.assertIs(row.private_preview.assessments[1][1].state,B7SupportState409.NONMATCH)

    def test_missing_pair_late_prior_and_invalid_support(self):
        for inputs,p,state in ((data(missing=True),config(),"MISSING_INPUT"),
            (data(late=True),config(),"BLOCKED"),
            (data(),replace(config(),candidate_index=4),"BLOCKED")):
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][2]["ingredient_state"],state)

    def test_no_choch_fallback_and_bad_epsilon(self):
        for p in (config(None),config(D("-1")),config(D("NaN"))):
            _,safe=run(data(),p)
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        _,safe=run(data(),config(),variant="B7/E_CHOCH")
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_redaction_and_no_authority(self):
        _,safe=run(data(),plan())
        self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(data(),config())
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("private_support","private_atr","candidate_epsilon",data().instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
