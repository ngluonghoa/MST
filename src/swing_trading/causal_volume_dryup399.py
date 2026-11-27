"""§399 D1 mean-volume dry-up candidate on exact disjoint windows."""
from dataclasses import dataclass
from decimal import Decimal

from .causal_indicators import (
    VolumeBasisWitness, VolumeComparisonBar, VolumeSessionClass,
    _raw_volume_witness_ok, _validate_ordered_bars,
)
from .market_data import Timeframe
from .replay import require_utc


@dataclass(frozen=True)
class DryUpPlan399:
    reference_count: int
    base_count: int
    max_ratio: Decimal
    comparison_policy_version: str
    witnesses: tuple[VolumeBasisWitness, ...]


@dataclass(frozen=True)
class DryUpCandidate399:
    reason: str
    mean_ratio: Decimal | None = None
    at_or_below: bool | None = None

    def safe_summary(self):
        return {"schema": "mst.private.d1_dryup_candidate.v0.1",
                "reason": self.reason, "at_or_below": self.at_or_below,
                "volume_approved": False, "source_qualified": False,
                "parameter_approved": False, "action_eligible": False}


def _check_counts399(plan):
    if type(plan) is not DryUpPlan399:
        raise ValueError("MST_399_EXPLICIT_DRYUP_PLAN")
    if any(type(n) is not int or n < 2 for n in (plan.reference_count, plan.base_count)):
        raise ValueError("MST_399_EXPLICIT_WINDOW_COUNTS")
    if plan.reference_count + plan.base_count > 512:
        raise ValueError("MST_399_BOUNDED_WINDOW")


def _check_plan399(plan):
    _check_counts399(plan)
    q = plan.max_ratio
    if type(q) is not Decimal or not q.is_finite() or not 0 <= q <= 1:
        raise ValueError("MST_399_EXPLICIT_MAX_RATIO")
    if type(plan.comparison_policy_version) is not str or not plan.comparison_policy_version.strip():
        raise ValueError("MST_399_EXPLICIT_COMPARISON_POLICY")
    if (type(plan.witnesses) is not tuple
            or len(plan.witnesses) != plan.reference_count + plan.base_count
            or any(type(w) is not VolumeBasisWitness for w in plan.witnesses)):
        raise ValueError("MST_399_EXACT_WITNESSES")


def _witnesses399(history, plan, reference_cutoff, as_of):
    for i, (row, witness) in enumerate(zip(history, plan.witnesses)):
        tagged = VolumeComparisonBar(row, VolumeSessionClass.DAILY, plan.comparison_policy_version)
        cutoff = reference_cutoff if i < plan.reference_count else as_of
        if not _raw_volume_witness_ok(tagged, witness, cutoff):
            return "RAW_MATCHED_WITNESS_UNVERIFIED"
    if any(w.share_regime_id != plan.witnesses[0].share_regime_id for w in plan.witnesses):
        return "SHARE_REGIME_CHANGED"
    return ""


def inspect_d1_volume_dryup(history, *, plan, as_of_utc):
    """Exact preceding reference + base; reference frozen before base start.

    Mean(base raw matched shares)/mean(reference raw matched shares), inclusive
    <= explicit candidate threshold. No missing-session or source attestation,
    no causal reconstruction of revisions before each individual base candle.
    """
    require_utc(as_of_utc)
    _check_plan399(plan)
    n = plan.reference_count
    if type(history) is not tuple or len(history) != n + plan.base_count:
        return DryUpCandidate399("EXACT_REFERENCE_BASE_HISTORY_REQUIRED")
    rows, reason = _validate_ordered_bars(history, as_of_utc, as_of_utc, Timeframe.D1)
    if rows is None:
        return DryUpCandidate399("INPUT_" + reason)
    cutoff = rows[n].market_bar_key.bar_start_utc
    reference, reason = _validate_ordered_bars(history[:n], as_of_utc, cutoff, Timeframe.D1)
    if reference is None:
        return DryUpCandidate399("REFERENCE_" + reason)
    reason = _witnesses399(history, plan, cutoff, as_of_utc)
    if reason:
        return DryUpCandidate399(reason)
    total = sum(r.volume for r in reference)
    if total <= 0:
        return DryUpCandidate399("ZERO_REFERENCE_VOLUME")
    ratio = Decimal(sum(r.volume for r in rows[n:])) * n / (Decimal(total) * plan.base_count)
    return DryUpCandidate399("MEAN_RAW_MATCHED_VOLUME_RATIO_ONLY", ratio, ratio <= plan.max_ratio)


def inspect_bound_d1_volume_dryup(rows, *, base_stop, plan, as_of_utc,
                                  expected_base_start=None):
    """Bind to the exact exclusive base endpoint and optional full base span."""
    _check_plan399(plan)
    if type(base_stop) is not int or base_stop < 1:
        raise ValueError("MST_400_EXPLICIT_BASE_STOP")
    base_start = base_stop - plan.base_count
    if expected_base_start is not None and base_start != expected_base_start:
        raise ValueError("MST_400_EXACT_CONTRACTION_BASE_REQUIRED")
    start = base_start - plan.reference_count
    if start < 0 or base_stop > len(rows):
        return DryUpCandidate399("EXACT_REFERENCE_BASE_HISTORY_REQUIRED")
    return inspect_d1_volume_dryup(rows[start:base_stop], plan=plan, as_of_utc=as_of_utc)
