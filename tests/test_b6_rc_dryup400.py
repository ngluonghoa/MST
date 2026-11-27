"""§400 B6 independent volume dry-up on exact bound base."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness
from swing_trading.causal_volume_dryup399 import DryUpPlan399
from swing_trading.b6_baseline_preview387 import B6State387
from swing_trading.contracts import Strategy
from test_b6_baseline_preview387 import config, evaluate, model
from test_b6_compression_rc396 import model as comp_model, run as comp_run
from test_b6_range_choice398 import plan as range_plan
from test_causal_contraction_candidate386 import fixture
from test_causal_range_percentile397 import fixture as range_fixture
from test_causal_indicators import make_bar, snap


def witnesses(rows,n,m,threshold=D("0.5")):
    return DryUpPlan399(n,m,threshold,"fixture-policy",
        tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
            "fixture-regime","fixture-dryup-"+str(i),s.selected.verified_at_utc)
            for i,s in enumerate(rows)))


def contraction_data(*, nonmatch=False, base_volume=50):
    base=fixture(((120,90),(128,96),(112,84))) if nonmatch else fixture()
    base=tuple(snap(replace(s.selected,volume=base_volume)) for s in base)
    first=base[0].market_bar_key.bar_start_utc
    prefix=tuple(snap(make_bar(200+i,start=first-timedelta(days=3-i),volume=200)) for i in range(3))
    rows=prefix+base
    c=replace(config(),d1_start=3,d1_stop=29,atr_start=3,atr_stop=18,
              dryup=witnesses(rows,3,26))
    return model(history=rows),c


def compression_data(width=D(2),base_volume=50):
    rows=tuple(snap(replace(s.selected,volume=200 if i<2 else base_volume))
               for i,s in enumerate(range_fixture(width)))
    c=replace(range_plan(),dryup=witnesses(rows,2,2))
    return comp_model(rows),c


def rc(row):
    return next(e for r,e in row.private_preview.assessments if r.phase=="R_C")


class B6DryUp400Tests(unittest.TestCase):
    def test_exact_full_contraction_base_both_strategies(self):
        data,p=contraction_data()
        for strategy in Strategy:
            row,safe=evaluate(data,cfg=p,strategy=strategy)
            self.assertIs(rc(row).state,B6State387.MATCH)
            self.assertEqual(rc(row).dryup.mean_ratio,D("0.25"))
            self.assertTrue(rc(row).dryup.at_or_below)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_compression_exact_target_both_strategies(self):
        data,p=compression_data()
        for strategy in Strategy:
            row,safe=comp_run(data,p,strategy=strategy)
            self.assertIs(rc(row).state,B6State387.MATCH)
            self.assertEqual(rc(row).dryup.mean_ratio,D("0.25"))
            self.assertEqual(safe["phases"][2]["ingredient_state"],"NOT_REQUESTED")
            self.assertEqual(safe["phases"][3]["ingredient_state"],"NOT_REQUESTED")

    def test_geometry_and_volume_independent(self):
        data,p=contraction_data(nonmatch=True)
        row,_=evaluate(data,cfg=p)
        self.assertIs(rc(row).state,B6State387.NONMATCH)
        self.assertTrue(rc(row).dryup.at_or_below)
        data,p=compression_data(base_volume=200)
        row,_=comp_run(data,p)
        self.assertIs(rc(row).state,B6State387.MATCH)
        self.assertFalse(rc(row).dryup.at_or_below)

    def test_wrong_exact_witness_and_missing_prefix(self):
        data,p=compression_data()
        v=p.dryup
        bad=replace(v.witnesses[-1],basis=VolumeBasis.ADJUSTED_SHARES)
        row,_=comp_run(data,replace(p,dryup=replace(v,witnesses=v.witnesses[:-1]+(bad,))))
        self.assertIs(rc(row).state,B6State387.MATCH)
        self.assertIsNone(rc(row).dryup.mean_ratio)
        row,_=comp_run(data,replace(p,dryup=replace(v,reference_count=3,
                         witnesses=(v.witnesses[0],)+v.witnesses)))
        self.assertEqual(rc(row).dryup.reason,"EXACT_REFERENCE_BASE_HISTORY_REQUIRED")

    def test_exact_base_span_and_invalid_plan(self):
        data,p=contraction_data()
        bad=replace(p.dryup,base_count=25,witnesses=p.dryup.witnesses[:-1])
        _,safe=evaluate(data,cfg=replace(p,dryup=bad))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        data,p=compression_data()
        _,safe=comp_run(data,replace(p,dryup=replace(p.dryup,max_ratio=D("NaN"))))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_no_plan_unchanged_and_redaction(self):
        row,_=evaluate()
        self.assertIsNone(rc(row).dryup)
        data,p=compression_data()
        row,safe=comp_run(data,p)
        self.assertFalse(rc(row).dryup.safe_summary()["volume_approved"])
        self.assertFalse(row.private_preview.action_eligible)
        for secret in ("mean_ratio","max_ratio","fixture-dryup","0.25","dryup"):
            self.assertNotIn(secret,json.dumps(safe))
