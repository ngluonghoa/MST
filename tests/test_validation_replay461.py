"""§461 chronological causal validation replays the same candidate engine."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
import unittest

from swing_trading.market_data import Timeframe
from swing_trading.unified_mode459 import EngineMode, evaluate_candidate
from swing_trading.validation_replay461 import ValidationPlan461, replay_candidate_validation
from test_shared_feature460 import profile
from test_causal_indicators import make_bar
from test_causal_trend_candidate382 import fixture
from test_engine_d1_context383 import plan as trend


def schedule(cutoffs, candidate=None):
    start = cutoffs[0] - timedelta(days=2)
    return ValidationPlan461(candidate or profile(None), start, start, 3600, cutoffs)


def run(plan, rows, keys=None):
    k = rows[0].market_bar_key
    return replay_candidate_validation(plan, instrument_id=k.instrument_id,
        exchange=k.exchange, m5_armed=False, market_bar_keys=keys if keys is not None else
        tuple(dict.fromkeys(r.market_bar_key for r in rows)), source_rows=rows)


class ValidationReplay461Tests(unittest.TestCase):
    def test_same_candidate_and_feature_recomputed_at_cutoff(self):
        rows = tuple(s.selected for s in fixture())
        cutoffs = (rows[-2].verified_at_utc, rows[-1].verified_at_utc)
        p = schedule(cutoffs, profile(trend()))
        result = run(p, rows)
        for frame in result.private_frames:
            self.assertIs(frame.private_evaluation.private_profile, p.profile)
            self.assertEqual(frame.private_evaluation.private_preview,
                evaluate_candidate(frame.private_inputs, mode=EngineMode.RESEARCH,
                                   profile=p.profile).private_preview)
        self.assertEqual(len(result.private_frames[0].private_inputs.snapshots_for(Timeframe.D1)), len(rows)-1)
        self.assertEqual(result.private_frames[-1].private_evaluation.safe_summary()
                         ["shared_d1_context"]["relation"], "ALIGNED_GEOMETRY_ONLY")

    def test_future_revision_not_selected_and_later_conflict_retained(self):
        row = make_bar(0)
        later = make_bar(0, known=row.verified_at_utc+timedelta(hours=1), close=Decimal("11"))
        r = run(schedule((row.verified_at_utc, later.verified_at_utc)), (row, later))
        a,b = (f.private_inputs.snapshots_for(Timeframe.D1)[0] for f in r.private_frames)
        self.assertEqual(a.selected, row)
        self.assertIsNone(b.selected)
        self.assertEqual(b.reason, "SOURCE_OR_REVISION_CONFLICT")

    def test_known_but_not_verified_fails_closed_no_fallback(self):
        row = make_bar(0)
        r = run(schedule((row.observation_revision.first_known_time_utc, row.verified_at_utc)), (row,))
        self.assertEqual(r.private_frames[0].reason, "INPUT_DENIED_UNVERIFIED")
        self.assertIsNone(r.private_frames[0].private_evaluation)
        self.assertIsNotNone(r.private_frames[1].private_evaluation)

    def test_future_bar_excluded_missing_revision_remains_missing(self):
        row, future = make_bar(0), make_bar(2)
        cutoff = row.market_bar_key.bar_start_utc
        r = run(schedule((cutoff, row.verified_at_utc)), (row, future))
        first = r.private_frames[0].private_inputs.snapshots_for(Timeframe.D1)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].reason, "NO_VISIBLE_REVISION")
        self.assertIsNone(first[0].selected)

    def test_freeze_embargo_strict_order_and_inventory(self):
        row = make_bar(0)
        c = row.verified_at_utc
        p = schedule((c,))
        for changes in (dict(scoring_cutoffs_utc=(c,c)), dict(frozen_at_utc=c),
                        dict(embargo_seconds=31622400), dict(embargo_seconds=True)):
            with self.assertRaises(ValueError):
                replace(p, **changes)
        for keys in ((row.market_bar_key,row.market_bar_key), ()):
            with self.assertRaises(ValueError):
                run(p, (row,), keys)

    def test_safe_summary_no_qualification_or_profile_market_identity(self):
        row = make_bar(0)
        p = schedule((row.verified_at_utc,))
        summary = run(p, (row,)).safe_summary()
        self.assertEqual(summary["candidate_evaluations"], 1)
        self.assertEqual(summary["decision"], "NO_TRADE")
        for flag in ("freeze_independently_attested","oos_qualified","validation_qualified",
                     "source_released","production_qualified","publication_allowed"):
            self.assertIs(summary[flag], False)
        for value in (row.market_bar_key.instrument_id, p.profile.configuration_sha256,
                      p.profile.code_git_sha, "private_frames"):
            self.assertNotIn(value, json.dumps(summary))
