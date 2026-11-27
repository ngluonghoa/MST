"""§406 exact raw matched RVOL20 for compression D1 RF."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest

from swing_trading.b6_baseline_preview387 import B6State387, B6RFVolumePlan389
from swing_trading.causal_indicators import IndicatorState, VolumeBasis, VolumeBasisWitness
from swing_trading.contracts import Strategy
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_compression_d1_rf404 import data, config, rf
from test_b6_compression_rc396 import run
from test_causal_indicators import snap


def fixture(**kwargs):
    original=data(**kwargs)
    rows=original.snapshots_for(Timeframe.D1)
    rows=rows[:-1]+(snap(replace(rows[-1].selected,volume=250)),)
    return BaselineResolvedInputs(original.instrument_id,original.exchange,original.as_of_utc,False,
        tuple((tf,rows if tf is Timeframe.D1 else bucket) for tf,bucket in original.buckets))


def volume_plan(inputs):
    rows=inputs.snapshots_for(Timeframe.D1)[1:22]
    return B6RFVolumePlan389("fictional-daily-policy",
        tuple(VolumeBasisWitness(x.selected,VolumeBasis.RAW_MATCHED_SHARES,
            "fixture-regime","fixture-rvol406-"+str(i),x.selected.verified_at_utc)
            for i,x in enumerate(rows)))


def cfg(inputs, index=21):
    p=config(index=index)
    return replace(p,rf=replace(p.rf,volume=volume_plan(inputs)))


class CompressionD1Volume406Tests(unittest.TestCase):
    def test_both_strategies_exact_target_and_prior20(self):
        inputs=fixture()
        for strategy in Strategy:
            row,safe=run(inputs,cfg(inputs),strategy=strategy)
            proof=rf(row)
            self.assertIs(proof.state,B6State387.MATCH)
            self.assertEqual(proof.volume_state,"RVOL_COMPUTED_UNCALIBRATED")
            self.assertIs(proof.rvol.state,IndicatorState.COMPUTED_UNCALIBRATED)
            self.assertEqual(proof.rvol.value,D("2.5"))
            self.assertFalse(proof.rvol.actionable)
            self.assertEqual(safe["phases"][-1]["ingredient_state"],"GEOMETRY_MATCH_ONLY")

    def test_volume_independent_of_nonmatch_or_blocked_geometry(self):
        for inputs in (fixture(price=D(110)),fixture(far=True)):
            row,_=run(inputs,cfg(inputs))
            self.assertIn(rf(row).state,(B6State387.NONMATCH,B6State387.BLOCKED))
            self.assertEqual(rf(row).rvol.value,D("2.5"))

    def test_wrong_basis_row_regime_or_late_witness(self):
        inputs=fixture()
        p=cfg(inputs)
        v=p.rf.volume
        first=v.witnesses[0]
        for bad in (replace(first,basis=VolumeBasis.ADJUSTED_SHARES),
                    replace(first,candle=v.witnesses[1].candle),
                    replace(first,share_regime_id="other"),
                    replace(first,verified_at_utc=v.witnesses[-1].verified_at_utc)):
            q=replace(p,rf=replace(p.rf,volume=replace(v,witnesses=(bad,)+v.witnesses[1:])))
            row,_=run(inputs,q)
            self.assertIs(rf(row).state,B6State387.MATCH)
            self.assertEqual(rf(row).volume_state,"RVOL_BLOCKED")
            self.assertIsNone(rf(row).rvol.value)

    def test_exact_target_missing_and_invalid_volume_plan(self):
        inputs=fixture()
        row,_=run(inputs,cfg(inputs,index=22))
        self.assertEqual(rf(row).volume_state,"EXACT_TARGET_OR_PRIOR20_MISSING")
        p=cfg(inputs)
        v=p.rf.volume
        for bad in (replace(v,witnesses=v.witnesses[:-1]),replace(v,comparison_policy_version="")):
            _,safe=run(inputs,replace(p,rf=replace(p.rf,volume=bad)))
            self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))

    def test_legacy_pending_when_not_requested(self):
        row,_=run(fixture(),config())
        self.assertEqual(rf(row).volume_state,"D1_VOLUME_SPEC_PENDING")
        self.assertIsNone(rf(row).rvol)

    def test_redacted_no_value_or_approval(self):
        inputs=fixture()
        row,safe=run(inputs,cfg(inputs))
        volume=row.private_preview.safe_rf_volume_summary()
        self.assertEqual(volume["volume_state"],"RVOL_COMPUTED_UNCALIBRATED")
        for flag in ("volume_approved","source_qualified","risk_approved","action_eligible"):
            self.assertFalse(volume[flag])
        for secret in ("2.5","fixture-rvol406","witnesses","value",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(volume))
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
