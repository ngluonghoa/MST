"""§388 B6 bound D1 RF crossing, fictional data only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6RFPlan388, B6State387
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs
from test_b6_baseline_preview387 import model, config, evaluate
from test_causal_contraction_candidate386 import fixture
from test_causal_indicators import make_bar, snap


def inputs(*, price=D(113), wick=D(114), prior=D(109), late=False, missing_m15=False, far=False):
    original=model(missing=missing_m15,far=far)
    rows=list(fixture())
    start=rows[-1].market_bar_key.bar_start_utc
    # M15 approach starts the day after the final contraction bar, at +7h.
    # D1 breakout starts two or three days after that final bar.
    for i,value,high in ((26,prior,max(prior,D(110))), (27,price,wick)):
        rows.append(snap(make_bar(i,start=start+timedelta(days=i-25),
                                 open_price=value,close=value,high=high,low=min(value,D(108)))))
    m15=original.snapshots_for(Timeframe.M15)
    if late and m15:
        row=m15[-1].selected
        m15=m15[:-1]+(snap(replace(row,verified_at_utc=rows[-1].selected.bar_end_utc)),)
    frames={Timeframe.D1:tuple(rows),Timeframe.M15:m15}
    return BaselineResolvedInputs(original.instrument_id,original.exchange,original.as_of_utc,False,
                                    tuple((tf,frames.get(tf,())) for tf in BASELINE_CORE_TF))


def cfg(eps=D("0.05"), index=27):
    return replace(config(),rf=B6RFPlan388(index,eps))


class B6BoundRF388Tests(unittest.TestCase):
    def test_both_strategies_same_pivot_cross_not_a_signal(self):
        for strategy in Strategy:
            row,safe=evaluate(inputs(),strategy=strategy,cfg=cfg())
            self.assertEqual([p["ingredient_state"] for p in safe["phases"]],
                             ["NOT_REQUESTED","GEOMETRY_MATCH_ONLY","DISTANCE_ONLY","GEOMETRY_MATCH_ONLY"])
            rf=row.private_preview.assessments[-1][1]
            self.assertEqual(rf.reason,"SAME_PIVOT_D1_CROSS_ONLY_VOLUME_RISK_PENDING")
            self.assertFalse(rf.action_eligible)
            self.assertEqual(safe["status"],"UNVERIFIED")

    def test_wick_only_and_prior_already_above_are_noncross(self):
        for data in (inputs(price=D(110)),inputs(prior=D(112))):
            row,safe=evaluate(data,cfg=cfg())
            self.assertIs(row.private_preview.assessments[-1][1].state,B6State387.NONMATCH)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_late_approach_cannot_backdate_rf(self):
        row,safe=evaluate(inputs(late=True),cfg=cfg())
        self.assertEqual(safe["phases"][2]["ingredient_state"],"DISTANCE_ONLY")
        self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")
        self.assertEqual(row.private_preview.assessments[-1][1].reason,"M15_APPROACH_NOT_KNOWN_BEFORE_BREAKOUT")

    def test_missing_or_far_approach_blocks_only_rf(self):
        for data in (inputs(missing_m15=True),inputs(far=True)):
            _,safe=evaluate(data,cfg=cfg())
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"BLOCKED")

    def test_explicit_breakout_config_and_missing_rows(self):
        for bad in (cfg(index=26),cfg(eps=None),cfg(index=True)):
            _,safe=evaluate(inputs(),cfg=bad)
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))
        _,safe=evaluate(inputs(),cfg=cfg(index=28))
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")

    def test_old_plan_and_redaction(self):
        _,old=evaluate(inputs(),cfg=config())
        self.assertEqual(old["phases"][3]["ingredient_state"],"NOT_REQUESTED")
        _,new=evaluate(inputs(),cfg=cfg())
        for forbidden in (inputs().instrument_id,"113","candidate_epsilon","pivot_price","distance"):
            self.assertNotIn(forbidden,json.dumps(new))
        self.assertTrue(all(not p["phase_verified"] and not p["action_eligible"] for p in new["phases"]))
