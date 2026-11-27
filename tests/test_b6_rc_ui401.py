"""§401 opt-in redacted B6 RC diagnostics, fictional data only."""
from dataclasses import replace
from decimal import Decimal as D
import json
import unittest
from unittest.mock import patch

from swing_trading.baseline_ui10_runtime379 import (
    build_baseline_ui10_b6_diagnostics, build_baseline_ui10_b6_rc_diagnostics,
)
from swing_trading.causal_indicators import VolumeBasis
from swing_trading.contracts import Strategy
from swing_trading.engine import BaselinePreviewRequest375, evaluate_baseline_preview
from test_b6_rc_dryup400 import compression_data, contraction_data
from test_b6_compression_rc396 import plan as atr_plan


def request(p, strategy=Strategy.SHORT, variant="B6/C_COMPRESSION"):
    return BaselinePreviewRequest375("B6",strategy,variant,p)


def run(data,p):
    return build_baseline_ui10_b6_rc_diagnostics(data,requests=(request(p),))["b6_diagnostics"][0]


class B6RcUi401Tests(unittest.TestCase):
    def test_single_engine_and_v01_contract_unchanged(self):
        data,p=compression_data()
        req=(request(p),)
        old=build_baseline_ui10_b6_diagnostics(data,requests=req)
        with patch("swing_trading.baseline_ui10_runtime379.evaluate_baseline_preview",
                   wraps=evaluate_baseline_preview) as engine:
            new=build_baseline_ui10_b6_rc_diagnostics(data,requests=req)
        engine.assert_called_once_with(data,requests=req)
        self.assertEqual(old["schema"],"mst.private.baseline_ui10_b6_diagnostics.v0.1")
        self.assertEqual(new["schema"],"mst.private.baseline_ui10_b6_diagnostics.v0.2")
        self.assertEqual(old["runtime"],new["runtime"])
        for a,b in zip(old["b6_diagnostics"],new["b6_diagnostics"]):
            self.assertEqual(a,{k:b[k] for k in a})
            self.assertNotIn("rc_method",a)

    def test_range_and_atr_independent_strategy(self):
        data,p=compression_data()
        req=(request(p),request(replace(atr_plan(),target_index=3),Strategy.SWING))
        rows=build_baseline_ui10_b6_rc_diagnostics(data,requests=req)["b6_diagnostics"]
        self.assertEqual(rows[0]["rc_method"],"RANGE_PERCENTILE")
        self.assertEqual(rows[0]["rc_dryup_state"],"CANDIDATE_MATCH_ONLY")
        self.assertEqual(rows[1]["rc_method"],"ATR_PERCENTILE")
        self.assertEqual(rows[1]["rc_geometry_state"],"MISSING_INPUT")
        self.assertEqual(rows[1]["rc_dryup_state"],"NOT_REQUESTED")

    def test_contraction_nonmatch_independent_dryup(self):
        data,p=contraction_data(nonmatch=True)
        row=build_baseline_ui10_b6_rc_diagnostics(data,requests=(
            request(p,variant="B6/C_TWO_CONTRACTIONS"),))["b6_diagnostics"][0]
        self.assertEqual(row["rc_method"],"TWO_CONTRACTIONS")
        self.assertEqual(row["rc_geometry_state"],"GEOMETRY_NONMATCH_ONLY")
        self.assertEqual(row["rc_dryup_state"],"CANDIDATE_MATCH_ONLY")

    def test_dryup_blocked_missing_nonmatch_and_not_requested(self):
        data,p=compression_data(base_volume=200)
        self.assertEqual(run(data,p)["rc_dryup_state"],"CANDIDATE_NONMATCH_ONLY")
        self.assertEqual(run(data,replace(p,dryup=None))["rc_dryup_state"],"NOT_REQUESTED")
        v=p.dryup
        bad=replace(v.witnesses[-1],basis=VolumeBasis.ADJUSTED_SHARES)
        row=run(data,replace(p,dryup=replace(v,witnesses=v.witnesses[:-1]+(bad,))))
        self.assertEqual(row["rc_dryup_state"],"BLOCKED")
        self.assertEqual(row["rc_geometry_state"],"GEOMETRY_MATCH_ONLY")
        missing=replace(v,reference_count=3,witnesses=(v.witnesses[0],)+v.witnesses)
        self.assertEqual(run(data,replace(p,dryup=missing))["rc_dryup_state"],"MISSING_INPUT")

    def test_invalid_and_unconfigured_scope(self):
        data,p=compression_data()
        req=(request(replace(p,target_index=True)),)
        rows=build_baseline_ui10_b6_rc_diagnostics(data,requests=req)["b6_diagnostics"]
        for key in ("rc_method","rc_dryup_state","rc_geometry_state"):
            self.assertEqual(rows[0][key],"CONFIG_REJECTED")
            self.assertEqual(rows[1][key],"NOT_CONFIGURED")

    def test_no_authority_or_raw_values(self):
        data,p=compression_data()
        result=build_baseline_ui10_b6_rc_diagnostics(data,requests=(request(p),))
        for row in result["b6_diagnostics"]:
            for flag in ("compression_approved","dryup_approved","volume_approved",
                         "phase_verified","action_eligible"):
                self.assertFalse(row[flag])
        self.assertEqual(result["decision"],"NO_TRADE")
        self.assertEqual(result["trade_orders"],0)
        for secret in (data.instrument_id,"mean_ratio","max_ratio","0.25","fixture-dryup","witnesses"):
            self.assertNotIn(secret,json.dumps(result))
        with self.assertRaises(TypeError):
            build_baseline_ui10_b6_rc_diagnostics(result)
