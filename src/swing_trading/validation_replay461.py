"""§461 bounded chronological replay of one pinned candidate, not OOS approval."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .market_data import MarketBarKey, Timeframe
from .private_multitf_readiness import BASELINE_CORE_TF, BaselineResolvedInputs, PrivateMultiTfDenied
from .replay import require_utc
from .replay_batch import replay_frame
from .source_quality import CanonicalCandleV12
from .unified_mode459 import CandidateProfile459, EngineMode, ModeEvaluation459, evaluate_candidate


@dataclass(frozen=True)
class ValidationPlan461:
    profile: CandidateProfile459
    research_end_utc: datetime
    frozen_at_utc: datetime
    embargo_seconds: int
    scoring_cutoffs_utc: tuple[datetime, ...]

    def __post_init__(self):
        if type(self.profile) is not CandidateProfile459:
            raise ValueError("MST_461_EXPLICIT_PROFILE")
        if type(self.scoring_cutoffs_utc) is not tuple or not 1 <= len(self.scoring_cutoffs_utc) <= 32:
            raise ValueError("MST_461_BOUNDED_CUTOFFS")
        times = (self.research_end_utc, self.frozen_at_utc) + self.scoring_cutoffs_utc
        for value in times:
            if type(value) is not datetime:
                raise ValueError("MST_461_EXACT_UTC_TIMES")
            require_utc(value)
        if self.frozen_at_utc < self.research_end_utc:
            raise ValueError("MST_461_FREEZE_BEFORE_RESEARCH_END")
        if type(self.embargo_seconds) is not int or not 0 <= self.embargo_seconds <= 31622400:
            raise ValueError("MST_461_EXPLICIT_EMBARGO")
        embargo_end = self.research_end_utc + timedelta(seconds=self.embargo_seconds)
        if any(t <= self.frozen_at_utc or t < embargo_end for t in self.scoring_cutoffs_utc):
            raise ValueError("MST_461_SCORING_BEFORE_FREEZE_OR_EMBARGO")
        if any(a >= b for a, b in zip(self.scoring_cutoffs_utc, self.scoring_cutoffs_utc[1:])):
            raise ValueError("MST_461_STRICT_CHRONOLOGY")


@dataclass(frozen=True)
class ValidationFrame461:
    cutoff_utc: datetime
    reason: str
    private_inputs: BaselineResolvedInputs | None
    private_evaluation: ModeEvaluation459 | None


@dataclass(frozen=True)
class ValidationSequence461:
    private_plan: ValidationPlan461
    private_frames: tuple[ValidationFrame461, ...]

    def safe_summary(self):
        return {
            "schema": "mst.private.candidate_validation_sequence.v1",
            "frames": len(self.private_frames),
            "candidate_evaluations": sum(f.private_evaluation is not None for f in self.private_frames),
            "blocked_frames": sum(f.private_evaluation is None for f in self.private_frames),
            "mode": "VALIDATION", "chronology_checked": True,
            "freeze_independently_attested": False, "calendar_inventory_attested": False,
            "source_released": False, "holdout_frozen": False,
            "oos_qualified": False, "validation_qualified": False,
            "production_qualified": False, "publication_allowed": False,
            "decision": "NO_TRADE", "trade_orders": 0,
        }


def _group_rows461(keys, rows):
    if type(rows) is not tuple or len(rows) > 12288:
        raise ValueError("MST_461_BOUNDED_SOURCE_ROWS")
    grouped = {k: [] for k in keys}
    for row in rows:
        if type(row) is not CanonicalCandleV12 or row.market_bar_key not in grouped:
            raise ValueError("MST_461_EXACT_SOURCE_INVENTORY")
        grouped[row.market_bar_key].append(row)
    return {k: tuple(v) for k, v in grouped.items()}


def _key_inventory461(keys, *, instrument_id, exchange, frames):
    if type(keys) is not tuple or len(keys) > 3072:
        raise ValueError("MST_461_BOUNDED_KEY_INVENTORY")
    by_tf = {tf: [] for tf in frames}
    for key in keys:
        if type(key) is not MarketBarKey or key.timeframe not in by_tf:
            raise ValueError("MST_461_EXACT_KEY_TIMEFRAME")
        if key.instrument_id != instrument_id or key.exchange != exchange:
            raise ValueError("MST_461_EXACT_INSTRUMENT_SCOPE")
        by_tf[key.timeframe].append(key)
    if len(set(keys)) != len(keys) or any(len(v) > 512 for v in by_tf.values()):
        raise ValueError("MST_461_DUPLICATE_OR_OVERSIZE_INVENTORY")
    return {tf: tuple(sorted(v, key=lambda k: k.bar_start_utc)) for tf, v in by_tf.items()}


def _resolved_bucket461(keys, grouped, cutoff):
    # Keys are caller-supplied inventory, not an independently known calendar.
    # Never expose a future bar start to the candidate; preserve visible conflicts.
    return tuple(replay_frame((key,), grouped[key], cutoff).bars[0].resolution
                 for key in keys if key.bar_start_utc <= cutoff)


def _frame461(plan, cutoff, *, scope, inventory, grouped):
    buckets = tuple((tf, _resolved_bucket461(keys, grouped, cutoff))
                    for tf, keys in inventory.items())
    try:
        inputs = BaselineResolvedInputs(as_of_utc=cutoff, buckets=buckets, **scope)
    except PrivateMultiTfDenied:
        # In particular, a first-known row whose retrieval/verification is in
        # the future is not converted to a selected historical bar or fallback.
        return ValidationFrame461(cutoff, "INPUT_DENIED_UNVERIFIED", None, None)
    evaluation = evaluate_candidate(inputs, mode=EngineMode.VALIDATION, profile=plan.profile)
    return ValidationFrame461(cutoff, "CANDIDATE_ONLY_UNVERIFIED", inputs, evaluation)


def replay_candidate_validation(plan, *, instrument_id, exchange, m5_armed,
                                market_bar_keys, source_rows):
    """Re-resolve the same raw revisions per cutoff, then call the shared engine.

    Caller-supplied freeze, inventory and clocks are not external attestations.
    No label-return calculation, holdout certification, tuning or publication.
    """
    if type(plan) is not ValidationPlan461 or type(m5_armed) is not bool:
        raise ValueError("MST_461_EXACT_PLAN_SCOPE")
    frames = BASELINE_CORE_TF + ((Timeframe.M5,) if m5_armed else ())
    scope = dict(instrument_id=instrument_id, exchange=exchange, m5_armed=m5_armed)
    BaselineResolvedInputs(as_of_utc=plan.frozen_at_utc,
                           buckets=tuple((tf, ()) for tf in frames), **scope)
    inventory = _key_inventory461(market_bar_keys, instrument_id=instrument_id,
                                 exchange=exchange, frames=frames)
    grouped = _group_rows461(market_bar_keys, source_rows)
    results = tuple(_frame461(plan, cutoff, scope=scope, inventory=inventory, grouped=grouped)
                    for cutoff in plan.scoring_cutoffs_utc)
    return ValidationSequence461(plan, results)
