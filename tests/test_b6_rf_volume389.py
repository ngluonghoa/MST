"""§389 B6 RF volume raw witnesses bound to exact D1 target and prior 20."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6RFVolumePlan389, B6State387
from swing_trading.causal_indicators import IndicatorState, VolumeBasis, VolumeBasisWitness
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_baseline_preview387 import evaluate
from test_b6_bound_rf388 import inputs, cfg
from test_causal_indicators import snap


def volume_model(**kwargs):
    data=inputs(**kwargs)
    rows=data.snapshots_for(Timeframe.D1)
    last=snap(replace(rows[-1].selected,volume=250))
    return BaselineResolvedInputs(data.instrument_id,data.exchange,data.as_of_utc,False,
        tuple((tf,rows[:-1]+(last,) if tf is Timeframe.D1 else bucket)
              for tf,bucket in data.buckets))


def witnesses(data):
    rows=data.snapshots_for(Timeframe.D1)[7:28]
    return B6RFVolumePlan389("fictional-daily-compare",
        tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
              "fixture-regime","fixture-raw-volume-"+str(i),s.selected.verified_at_utc)
              for i,s in enumerate(rows)))


def run(data, plan=None, *, strategy=Strategy.SHORT, index=27):
    c=cfg(index=index)
    return evaluate(data,strategy=strategy,cfg=replace(c,rf=replace(c.rf,volume=plan)))


class B6RFVolume389Tests(unittest.TestCase):
    def test_exact_raw_witnesses_both_strategies_and_cross(self):
        data=volume_model()
        for strategy in Strategy:
            row,safe=run(data,witnesses(data),strategy=strategy)
            rf=row.private_preview.assessments[-1][1]
            self.assertIs(rf.state,B6State387.MATCH)
            self.assertEqual(rf.volume_state,"RVOL_COMPUTED_UNCALIBRATED")
            self.assertEqual(rf.rvol.value,D("2.5"))
            self.assertFalse(rf.rvol.data_certified)
            self.assertFalse(rf.rvol.actionable)
            self.assertEqual(safe["status"],"UNVERIFIED")

    def test_missing_witness_not_implicit_price_volume_pass(self):
        row,safe=run(volume_model())
        rf=row.private_preview.assessments[-1][1]
        self.assertIs(rf.state,B6State387.MATCH)
        self.assertEqual(rf.volume_state,"RAW_MATCHED_WITNESS_MISSING")
        self.assertIsNone(rf.rvol)
        self.assertFalse(row.private_preview.safe_rf_volume_summary()["volume_approved"])

    def test_wrong_row_adjusted_basis_and_regime_change_block(self):
        data=volume_model()
        plan=witnesses(data)
        last=plan.witnesses[-1]
        for altered in (replace(last,basis=VolumeBasis.ADJUSTED_SHARES),
                        replace(last,candle=plan.witnesses[-2].candle),
                        replace(last,share_regime_id="other-regime")):
            row,_=run(data,replace(plan,witnesses=plan.witnesses[:-1]+(altered,)))
            rf=row.private_preview.assessments[-1][1]
            self.assertIs(rf.state,B6State387.MATCH)
            self.assertEqual(rf.volume_state,"RVOL_BLOCKED")
            self.assertIs(rf.rvol.state,IndicatorState.BLOCKED)
            self.assertIsNone(rf.rvol.value)

    def test_volume_separate_from_wick_only_and_late_approach(self):
        for data in (volume_model(price=D(110)),volume_model(late=True)):
            row,_=run(data,witnesses(data))
            rf=row.private_preview.assessments[-1][1]
            self.assertIn(rf.state,(B6State387.NONMATCH,B6State387.BLOCKED))
            self.assertEqual(rf.volume_state,"RVOL_COMPUTED_UNCALIBRATED")
            self.assertFalse(rf.action_eligible)

    def test_missing_exact_target_and_bad_plan(self):
        data=volume_model()
        plan=witnesses(data)
        row,_=run(data,plan,index=28)
        rf=row.private_preview.assessments[-1][1]
        self.assertEqual(rf.volume_state,"EXACT_TARGET_OR_PRIOR20_MISSING")
        for bad in (replace(plan,witnesses=plan.witnesses[:-1]),
                    replace(plan,comparison_policy_version="")):
            _,safe=run(data,bad)
            self.assertTrue(all(p["ingredient_state"]=="CONFIG_REJECTED" for p in safe["phases"]))

    def test_redacted_summary_no_value_or_identity(self):
        data=volume_model()
        row,_=run(data,witnesses(data))
        safe=row.private_preview.safe_rf_volume_summary()
        self.assertEqual(safe["volume_state"],"RVOL_COMPUTED_UNCALIBRATED")
        for flag in ("volume_approved","source_qualified","risk_approved","action_eligible"):
            self.assertFalse(safe[flag])
        for forbidden in (data.instrument_id,"2.5","fictional","fixture-raw","witnesses","value"):
            self.assertNotIn(forbidden,json.dumps(safe))
