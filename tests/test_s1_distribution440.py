"""§440 fictional causal D1 rejection with raw matched volume."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import unittest

from swing_trading.causal_indicators import VolumeBasis, VolumeBasisWitness
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.s1_distribution440 import S1DistributionPlan440
from test_s1_context439 import fixture as context,run,VARIANTS
from test_causal_indicators import make_bar,snap


def fixture(tf=Timeframe.D1,*,close=D(16),high=D(22),low=D(14),volume=250):
    inputs,p=context(tf)
    daily=inputs.snapshots_for(Timeframe.D1)
    count=20-len(daily)
    begin=daily[0].market_bar_key.bar_start_utc
    prefix=tuple(snap(make_bar(900+i,start=begin-timedelta(days=count-i)))
                 for i in range(count))
    anchor=inputs.snapshots_for(Timeframe.M15)[p.target_index].selected
    target=snap(make_bar(999,start=anchor.market_bar_key.bar_start_utc+timedelta(days=1),
                        open_price=close,close=close,high=high,low=low,volume=volume))
    rows=prefix+daily+(target,)
    inputs=replace(inputs,buckets=tuple((f,rows if f is Timeframe.D1 else s)
                                       for f,s in inputs.buckets))
    if tf is Timeframe.D1:
        p=replace(p,start=p.start+count,stop=p.stop+count)
    witnesses=tuple(VolumeBasisWitness(s.selected,VolumeBasis.RAW_MATCHED_SHARES,
                        "fixture-regime",str(i),s.selected.verified_at_utc)
                    for i,s in enumerate(rows))
    return inputs,replace(p,distribution=S1DistributionPlan440(20,"fixture-volume-v1",
                            witnesses,D("2.5"),D(".25")))


class S1Distribution440Tests(unittest.TestCase):
    def test_inclusive_both_context_frames_strategies_variants(self):
        for tf in (Timeframe.D1,Timeframe.W1):
            for strategy in Strategy:
                for variant in VARIANTS:
                    inputs,p=fixture(tf)
                    row,safe=run(inputs,p,strategy,variant)
                    g=row.private_preview.assessments[1][1]
                    self.assertEqual((g.rvol.value,g.close_location),(D("2.5"),D(".25")))
                    self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_healthy_breakout_low_volume_or_strong_close_nonmatch(self):
        for kw in ({"close":D(21)},{"volume":249},{"close":D(17)},{"high":D(19)}):
            inputs,p=fixture(**kw)
            _,safe=run(inputs,p)
            self.assertEqual(safe["phases"][1]["ingredient_state"],"GEOMETRY_NONMATCH_ONLY")

    def test_missing_or_wrong_raw_witness(self):
        inputs,p=fixture()
        plan=p.distribution
        _,safe=run(inputs,replace(p,distribution=replace(plan,target_index=19)))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"MISSING_INPUT")
        w=replace(plan.witnesses[-1],basis=VolumeBasis.UNKNOWN)
        _,safe=run(inputs,replace(p,distribution=replace(plan,witnesses=plan.witnesses[:-1]+(w,))))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")

    def test_late_witness_and_unmatched_context(self):
        inputs,p=fixture()
        plan=p.distribution
        w=replace(plan.witnesses[-1],verified_at_utc=plan.witnesses[-1].verified_at_utc+timedelta(seconds=1))
        _,safe=run(inputs,replace(p,distribution=replace(plan,witnesses=plan.witnesses[:-1]+(w,))))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")
        _,safe=run(inputs,replace(p,candidate_min_span_bars=8))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"BLOCKED")

    def test_explicit_threshold_no_defaults_and_validation(self):
        inputs,p=fixture()
        plan=p.distribution
        _,safe=run(inputs,replace(p,distribution=replace(plan,candidate_min_rvol=None)))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"DISTANCE_ONLY")
        for kw in ({"candidate_min_rvol":D(0)},{"candidate_max_close_location":D(2)},
                   {"comparison_policy":""},{"witnesses":plan.witnesses[:-1]}):
            _,safe=run(inputs,replace(p,distribution=replace(plan,**kw)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_redaction_no_authority(self):
        inputs,p=fixture()
        _,safe=run(inputs,replace(p,distribution=None))
        self.assertEqual(safe["phases"][1]["ingredient_state"],"NOT_REQUESTED")
        row,safe=run(inputs,p)
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("close_location","fixture-regime","rvol",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
