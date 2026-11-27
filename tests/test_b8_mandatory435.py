"""§435 cumulative mandatory candidate gate, fictional only."""
from dataclasses import replace
import json
import unittest

from swing_trading.b8_base_preview415 import B8State415
from swing_trading.b8_mandatory435 import apply_phase435
from test_b8_dual_basis434 import model
from test_b8_base415 import run
from test_b8_r0_band433 import bind as r0_band
from test_b8_band426 import bind as rf_band
from test_b8_execution430 import full
from test_b8_rf_threshold431 import threshold
from test_b8_rf_volume419 import fixture as volume_fixture


class B8Mandatory435Tests(unittest.TestCase):
    def test_legacy_and_strict_missing_rf(self):
        inputs,p=model()
        p=rf_band(inputs,r0_band(inputs,p))
        row,safe=run(inputs,p)
        self.assertIsNone(row.private_preview.assessments[0][1].candidate_evidence_complete)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"GEOMETRY_MATCH_ONLY")
        row,safe=run(inputs,replace(p,strict_candidate_evidence=True))
        self.assertTrue(row.private_preview.assessments[0][1].candidate_evidence_complete)
        self.assertEqual(safe["phases"][3]["ingredient_state"],"MISSING_INPUT")
        self.assertIn("RF_RVOL",row.private_preview.assessments[-1][1].mandatory_gaps)

    def test_r0_requires_explicit_band_and_rs(self):
        inputs,p=model()
        row,safe=run(inputs,replace(p,strict_candidate_evidence=True))
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")
        self.assertIn("R0_RAW_BAND",row.private_preview.assessments[0][1].mandatory_gaps)
        p=replace(r0_band(inputs,p),rs=None,rs_stock=None,strict_candidate_evidence=True)
        row,safe=run(inputs,p)
        self.assertIn("R0_RS",row.private_preview.assessments[0][1].mandatory_gaps)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"MISSING_INPUT")

    def test_uncalibrated_rs_not_promoted(self):
        inputs,p=model()
        p=replace(r0_band(inputs,p),rs=replace(p.rs,candidate_min_slope=None),
                  strict_candidate_evidence=True)
        _,safe=run(inputs,p)
        self.assertEqual(safe["phases"][0]["ingredient_state"],"DISTANCE_ONLY")

    def test_selected_tod_variant_requires_threshold_evidence(self):
        inputs,p=model()
        p=replace(r0_band(inputs,p),strict_candidate_evidence=True)
        row,safe=run(inputs,p,variant="B8/INTRADAY_RVOL_TOD_PENDING")
        self.assertEqual(safe["phases"][2]["ingredient_state"],"MISSING_INPUT")
        self.assertIn("RE_TOD",row.private_preview.assessments[2][1].mandatory_gaps)

    def test_unit_gate_complete_and_missing_budget(self):
        # Deliberately isolated gate unit test with synthetic ingredient objects.
        # Not a claim that these separate source windows form an integrated fixture.
        inputs,p=full()
        row,_=run(inputs,p)
        g=row.private_preview.assessments[-1][1]
        rs_inputs,rs_p=model()
        rs_row,_=run(rs_inputs,rs_p)
        vol_inputs,vol_p=volume_fixture()
        from decimal import Decimal
        vol_row,_=run(vol_inputs,threshold(vol_p,Decimal(1)))
        g=replace(g,rs=rs_row.private_preview.assessments[-1][1].rs,
                  rvol=vol_row.private_preview.assessments[-1][1].rvol,
                  rvol_candidate_match=True)
        p=replace(p,strict_candidate_evidence=True)
        result=apply_phase435(p,"R_F",g,"B8/BASE",states=B8State415)
        self.assertTrue(result.candidate_evidence_complete)
        result=apply_phase435(p,"R_F",replace(g,portfolio=None),"B8/BASE",states=B8State415)
        self.assertIs(result.state,B8State415.MISSING)
        self.assertFalse(result.candidate_evidence_complete)

    def test_invalid_flag_and_redaction(self):
        inputs,p=model()
        _,safe=run(inputs,replace(p,strict_candidate_evidence=1))
        self.assertTrue(all(x["ingredient_state"]=="CONFIG_REJECTED" for x in safe["phases"]))
        row,safe=run(inputs,replace(r0_band(inputs,p),strict_candidate_evidence=True))
        self.assertFalse(row.private_preview.action_eligible)
        self.assertTrue(all(not x["phase_verified"] and not x["action_eligible"] for x in safe["phases"]))
        for secret in ("mandatory_gaps","candidate_evidence_complete",inputs.instrument_id):
            self.assertNotIn(secret,json.dumps(safe))
