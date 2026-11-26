"""§391 same-input B6 diagnostic sidecar, fictional fixtures only."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from swing_trading.baseline_ui10_runtime379 import (
    build_baseline_ui10_runtime, build_baseline_ui10_b6_diagnostics,
)
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from swing_trading.market_data import Timeframe
from swing_trading.private_multitf_readiness import BaselineResolvedInputs
from test_b6_prior_trend390 import data as trend_data, plan as trend_plan
from test_b6_rf_volume389 import volume_model, witnesses
from test_b6_bound_rf388 import cfg


def request(strategy, plan):
    return BaselinePreviewRequest375("B6",strategy,"B6/C_TWO_CONTRACTIONS",plan)


def combined():
    base=volume_model()
    prefix=trend_data().snapshots_for(Timeframe.D1)[:60]
    inputs=BaselineResolvedInputs(base.instrument_id,base.exchange,base.as_of_utc,False,
        tuple((tf,prefix+rows if tf is Timeframe.D1 else rows) for tf,rows in base.buckets))
    plan=replace(trend_plan(),rf=replace(cfg().rf,breakout_index=87,volume=witnesses(base)))
    return inputs,plan


class B6Ui391Tests(unittest.TestCase):
    def test_single_execution_and_unchanged_runtime(self):
        inputs,plan=combined()
        requests=(request(Strategy.SHORT,plan),)
        expected=build_baseline_ui10_runtime(inputs,requests=requests)
        with patch("swing_trading.baseline_ui10_runtime379.evaluate_baseline_preview",
                   wraps=evaluate_baseline_preview) as engine:
            result=build_baseline_ui10_b6_diagnostics(inputs,requests=requests)
        engine.assert_called_once_with(inputs,requests=requests)
        self.assertEqual(result["runtime"],expected)
        self.assertEqual(result["schema"],"mst.private.baseline_ui10_b6_diagnostics.v0.1")

    def test_r0_and_rf_volume_both_strategies_independent(self):
        inputs,plan=combined()
        other=replace(plan,r0=None,rf=replace(plan.rf,volume=None))
        result=build_baseline_ui10_b6_diagnostics(inputs,
            requests=(request(Strategy.SWING,other),request(Strategy.SHORT,plan)))
        rows={r["strategy"]:r for r in result["b6_diagnostics"]}
        self.assertEqual(tuple(rows),tuple(s.value for s in Strategy))
        self.assertEqual(rows["SHORT"]["r0_context_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(rows["SHORT"]["rf_geometry_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(rows["SHORT"]["rf_volume_state"],"RVOL_COMPUTED_UNCALIBRATED")
        self.assertEqual(rows["SWING"]["r0_context_state"],"NOT_REQUESTED")
        self.assertEqual(rows["SWING"]["rf_volume_state"],"RAW_MATCHED_WITNESS_MISSING")

    def test_volume_blocked_separate_from_geometry(self):
        inputs,plan=combined()
        vol=plan.rf.volume
        bad=replace(vol,witnesses=vol.witnesses[:-1]+(vol.witnesses[-2],))
        req=request(Strategy.SHORT,replace(plan,rf=replace(plan.rf,volume=bad)))
        row=build_baseline_ui10_b6_diagnostics(inputs,requests=(req,))["b6_diagnostics"][0]
        self.assertEqual(row["rf_geometry_state"],"GEOMETRY_MATCH_ONLY")
        self.assertEqual(row["rf_volume_state"],"RVOL_BLOCKED")

    def test_missing_and_rejected_scopes_not_reused(self):
        inputs,plan=combined()
        bad=request(Strategy.SHORT,replace(plan,target_index=True))
        result=build_baseline_ui10_b6_diagnostics(inputs,requests=(bad,))
        rows={r["strategy"]:r for r in result["b6_diagnostics"]}
        self.assertEqual(rows["SHORT"]["r0_context_state"],"CONFIG_REJECTED")
        self.assertEqual(rows["SHORT"]["rf_volume_state"],"CONFIG_REJECTED")
        self.assertEqual(rows["SWING"]["rf_volume_state"],"NOT_CONFIGURED")
        self.assertEqual(rows["SWING"]["r0_context_state"],"NOT_CONFIGURED")

    def test_no_authority_redaction_and_fresh_projection(self):
        inputs,plan=combined()
        req=(request(Strategy.SHORT,plan),)
        result=build_baseline_ui10_b6_diagnostics(inputs,requests=req)
        for r in result["b6_diagnostics"]:
            for flag in ("trend_approved","volume_approved","risk_approved","phase_verified","action_eligible"):
                self.assertFalse(r[flag])
        for flag in ("source_released","report_published","step08_committed","action_eligible"):
            self.assertFalse(result[flag])
        self.assertEqual(result["decision"],"NO_TRADE")
        self.assertEqual(result["trade_orders"],0)
        for secret in (inputs.instrument_id,"2.5","candidate_epsilon","fixture-raw","pivot_price","witnesses"):
            self.assertNotIn(secret,json.dumps(result))
        result["b6_diagnostics"][0]["rf_volume_state"]="fabricated"
        self.assertEqual(build_baseline_ui10_b6_diagnostics(inputs,requests=req)["b6_diagnostics"][0]["rf_volume_state"],
                         "RVOL_COMPUTED_UNCALIBRATED")

    def test_detached_runtime_not_accepted(self):
        inputs,plan=combined()
        with self.assertRaises(TypeError):
            build_baseline_ui10_b6_diagnostics(build_baseline_ui10_runtime(inputs))
        with self.assertRaises(TypeError):
            build_baseline_ui10_b6_diagnostics(inputs,phase_summary={})
