"""P0.8 B5 causal *geometry* only — no predicates, calibration or trade authority.

SHORT and SWING share raw arithmetic, but have independent parameter slots.
No threshold is assigned, no Boolean phase is evaluated and no backtest runs.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .b5_feature_pack import PriorPivot
from .b5_phase_contract import (
    B5Ingredient, B5PhaseReadiness, B5_VARIANTS, inspect_b5_phase_receipts,
    B5PhaseReceipt,
)
from .contracts import DecisionStatus, Strategy
from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, inspect_causal_pivot,
    inspect_closed_bos_geometry,
)
from .market_data import Timeframe
from .phase_input_routing369 import route_phase_inputs
from .private_multitf_readiness import BaselineResolvedInputs
from .structural_phase_evidence import _bar_identity, _digest
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12


class B5GeometryState(str, Enum):
    BASE_BLOCKED = "BASE_BLOCKED"
    ANCHOR_BLOCKED = "ANCHOR_BLOCKED"
    RAW_GEOMETRY_UNCALIBRATED = "RAW_GEOMETRY_UNCALIBRATED"


@dataclass(frozen=True)
class B5StrategyFormulaDraft:
    """Distinct strategy-slot registry; every unapproved threshold stays None."""
    strategy: Strategy
    rule_version: str
    rc_window_sessions: int | None = None
    rc_tolerance_atr: Decimal | None = None
    re_reclaim_buffer_atr: Decimal | None = None
    rf_support_buffer_atr: Decimal | None = None
    rf_micro_break_buffer_atr: Decimal | None = None
    rf_min_rvol: Decimal | None = None
    risk_policy_approved: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, Strategy):
            raise TypeError("Strategy must be explicit SHORT or SWING")
        expected = "B5/" + self.strategy.value + "/FORMULA_DRAFT_0_1"
        if self.rule_version != expected:
            raise ValueError("Only named uncalibrated B5 strategy drafts exist")
        for field in ("rc_window_sessions", "rc_tolerance_atr",
                      "re_reclaim_buffer_atr", "rf_support_buffer_atr",
                      "rf_micro_break_buffer_atr", "rf_min_rvol"):
            if getattr(self, field) is not None:
                raise ValueError("No approved numeric parameter is available")
        if type(self.risk_policy_approved) is not bool or self.risk_policy_approved:
            raise ValueError("B5 risk policy not approved")


def draft_for(strategy: Strategy) -> B5StrategyFormulaDraft:
    if not isinstance(strategy, Strategy):
        raise TypeError("Strategy must be explicit SHORT or SWING")
    return B5StrategyFormulaDraft(strategy, "B5/" + strategy.value + "/FORMULA_DRAFT_0_1")


@dataclass(frozen=True)
class B5RawGeometry:
    """Signed distances, not true/false phase verdicts.

    Caller-supplied ATR is merely the P0.7 receipt's proposed number, NOT
    recomputed or validated Wilder ATR14. Session counts and historical RVOL
    are purposely absent until the underlying market source is qualified.
    """
    breakout_close_above_pivot_atr: Decimal
    retest_low_minus_pivot_atr: Decimal
    retest_close_minus_pivot_atr: Decimal
    retest_recovery_from_low_atr: Decimal
    followup_support_close_minus_pivot_atr: Decimal
    followup_close_minus_micro_high_atr: Decimal
    followup_volume_observed: int
    retest_elapsed_seconds_from_breakout: Decimal
    failed_break_close_minus_pivot_atr: Decimal | None
    pivot_event_id: str
    micro_high_source_revision: str


@dataclass(frozen=True)
class B5GeometryAssessment:
    strategy: Strategy
    variant_id: str
    as_of_utc: datetime
    state: B5GeometryState
    reason: str
    formula_version: str
    geometry: B5RawGeometry | None
    detector_approved: bool = False
    actionable: bool = False

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)
        if not isinstance(self.strategy, Strategy) or self.variant_id not in B5_VARIANTS:
            raise ValueError("Explicit strategy and B5 variant required")
        if not isinstance(self.state, B5GeometryState) or not self.reason:
            raise ValueError("Typed state and reason required")
        if (self.geometry is None) == (self.state is B5GeometryState.RAW_GEOMETRY_UNCALIBRATED):
            raise ValueError("Geometry allowed only in uncalibrated state")
        if self.formula_version != draft_for(self.strategy).rule_version:
            raise ValueError("Unknown B5 formula draft version")
        if self.detector_approved or self.actionable:
            raise ValueError("No trading signal/action authority")


def _causal_anchor(
    anchor: ResolvedBarSnapshotV12 | None,
    reference: ResolvedBarSnapshotV12,
    *,
    as_of_utc: datetime,
    must_be_known_by_utc: datetime,
) -> bool:
    if not isinstance(anchor, ResolvedBarSnapshotV12) or anchor.selected is None:
        return False
    bar = anchor.selected
    ref = reference.selected
    if ref is None or not anchor.confirmation_prerequisites(as_of_utc):
        return False
    key, base = bar.market_bar_key, ref.market_bar_key
    if (key.timeframe is not Timeframe.M15
            or key.instrument_id != base.instrument_id
            or key.exchange != base.exchange
            or key.instrument_class != base.instrument_class
            or key.price_basis != base.price_basis
            or key.calendar_version != base.calendar_version):
        return False
    return (bar.bar_end_utc <= must_be_known_by_utc
            and bar.verified_at_utc is not None
            and bar.verified_at_utc <= must_be_known_by_utc
            and bar.observation_revision.first_known_time_utc <= must_be_known_by_utc)


def calculate_b5_raw_geometry(
    pivot: PriorPivot | None,
    breakout: ResolvedBarSnapshotV12 | None,
    retest: ResolvedBarSnapshotV12 | None,
    receipts: tuple[B5PhaseReceipt, ...],
    *,
    strategy: Strategy,
    variant_id: str,
    as_of_utc: datetime,
    micro_high_anchor: ResolvedBarSnapshotV12 | None,
    failed_break_anchor: ResolvedBarSnapshotV12 | None = None,
) -> B5GeometryAssessment:
    """Read validated receipt manifest and produce only descriptive Decimal math."""
    require_utc(as_of_utc)
    draft = draft_for(strategy)
    if variant_id not in B5_VARIANTS:
        raise ValueError("Explicit canonical B5 E variant required")

    def finish(state: B5GeometryState, reason: str,
               raw: B5RawGeometry | None = None) -> B5GeometryAssessment:
        return B5GeometryAssessment(strategy, variant_id, as_of_utc, state,
                                    reason, draft.rule_version, raw)

    review = inspect_b5_phase_receipts(
        pivot, breakout, retest, receipts,
        strategy=strategy, variant_id=variant_id, as_of_utc=as_of_utc,
    )
    if review.state is not B5PhaseReadiness.PRESENT_UNCALIBRATED:
        return finish(B5GeometryState.BASE_BLOCKED, "PHASE_RECEIPT_" + review.reason)
    assert pivot is not None and breakout is not None and retest is not None
    assert breakout.selected is not None and retest.selected is not None
    a, b = breakout.selected, retest.selected
    records = {r.ingredient: r for r in receipts}
    atr = records[B5Ingredient.RC_PRIOR_ATR].observed_value
    if atr is None or atr <= 0:
        return finish(B5GeometryState.BASE_BLOCKED, "ATR_RECEIPT_NOT_POSITIVE")
    support = records[B5Ingredient.RF_SUPPORT_H1_D1].bar
    follow = records[B5Ingredient.RF_MICRO_HIGH_BREAK].bar
    volume = records[B5Ingredient.RF_VOLUME].bar
    assert support is not None and follow is not None and volume is not None
    assert support.selected is not None and follow.selected is not None
    assert volume.selected is not None

    f = follow.selected
    if (not _causal_anchor(micro_high_anchor, retest, as_of_utc=as_of_utc,
                           must_be_known_by_utc=f.market_bar_key.bar_start_utc)
            or micro_high_anchor.selected.bar_end_utc < b.bar_end_utc):
        return finish(B5GeometryState.ANCHOR_BLOCKED, "NO_CAUSAL_MICRO_HIGH_ANCHOR")

    failed_value = None
    if variant_id == "B5/E_FAILED_BREAK":
        if not _causal_anchor(failed_break_anchor, retest, as_of_utc=as_of_utc,
                              must_be_known_by_utc=b.market_bar_key.bar_start_utc):
            return finish(B5GeometryState.ANCHOR_BLOCKED, "NO_PRIOR_CLOSED_FAILED_BREAK_BAR")
        assert failed_break_anchor is not None and failed_break_anchor.selected is not None
        failed = failed_break_anchor.selected
        if failed.bar_end_utc <= a.bar_end_utc or failed.close >= pivot.price:
            return finish(B5GeometryState.ANCHOR_BLOCKED, "FAILED_BREAK_BAR_NOT_BELOW_PIVOT_AFTER_BREAKOUT")
        failed_value = (failed.close - pivot.price) / atr

    gap = Decimal(str((b.bar_end_utc - a.bar_end_utc).total_seconds()))
    raw = B5RawGeometry(
        breakout_close_above_pivot_atr=(a.close - pivot.price) / atr,
        retest_low_minus_pivot_atr=(b.low - pivot.price) / atr,
        retest_close_minus_pivot_atr=(b.close - pivot.price) / atr,
        retest_recovery_from_low_atr=(b.close - b.low) / atr,
        followup_support_close_minus_pivot_atr=(support.selected.close - pivot.price) / atr,
        followup_close_minus_micro_high_atr=(f.close - micro_high_anchor.selected.high) / atr,
        followup_volume_observed=volume.selected.volume,
        retest_elapsed_seconds_from_breakout=gap,
        failed_break_close_minus_pivot_atr=failed_value,
        pivot_event_id=pivot.event_id,
        micro_high_source_revision=micro_high_anchor.selected.observation_revision.source_revision_or_payload_digest,
    )
    return finish(B5GeometryState.RAW_GEOMETRY_UNCALIBRATED,
                  "R_C_R_E_R_F_THRESHOLDS_AND_SOURCE_VALIDATION_PENDING", raw)


class B5RetestState372(str, Enum):
    BLOCKED = "BLOCKED"
    NONCROSS_GEOMETRY_ONLY = "NONCROSS_GEOMETRY_ONLY"
    RAW_RETEST_UNCALIBRATED = "RAW_RETEST_UNCALIBRATED"


@dataclass(frozen=True)
class B5RetestPlan372:
    breakout_tf: Timeframe
    breakout_index: int
    pivot_index: int
    left_count: int
    right_count: int
    atr_start: int
    atr_stop: int
    retest_index: int
    failed_break_index: int | None
    tie_policy: TiePolicy
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class B5RetestMetrics372:
    pivot_price: Decimal
    breakout_close_minus_pivot_atr: Decimal
    retest_low_minus_pivot_atr: Decimal
    retest_close_minus_pivot_atr: Decimal
    retest_recovery_from_low_atr: Decimal
    failed_break_close_minus_pivot_atr: Decimal | None
    breakout_preview_id: str
    retest_preview_id: str


@dataclass(frozen=True)
class B5BaselineRetestPreview372:
    strategy: Strategy
    variant_id: str
    as_of_utc: datetime
    routed_phases: tuple
    state: B5RetestState372
    reason: str
    metrics: B5RetestMetrics372 | None

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def rf_evaluated(self):
        return False

    @property
    def actionable(self):
        return False


def _validate_plan372(plan, variant):
    if (type(plan) is not B5RetestPlan372 or type(plan.breakout_tf) is not Timeframe
            or plan.breakout_tf not in (Timeframe.D1, Timeframe.H1)
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_372_EXPLICIT_PLAN_REQUIRED")
    integers = (plan.breakout_index, plan.pivot_index, plan.left_count,
                plan.right_count, plan.atr_start, plan.atr_stop, plan.retest_index)
    if any(type(i) is not int or i < 0 for i in integers):
        raise ValueError("MST_372_INVALID_INDEX")
    if (min(plan.left_count, plan.right_count) < 1 or plan.breakout_index < 2
            or plan.pivot_index < plan.left_count
            or plan.pivot_index + plan.right_count >= plan.breakout_index - 1
            or plan.atr_start >= plan.atr_stop):
        raise ValueError("MST_372_INVALID_SLICE")
    failed = plan.failed_break_index
    if variant == "B5/E_FAILED_BREAK":
        if type(failed) is not int or not 0 <= failed < plan.retest_index:
            raise ValueError("MST_372_FAILED_BREAK_BRANCH_INDEX_REQUIRED")
    elif failed is not None:
        raise ValueError("MST_372_RECLAIM_MUST_NOT_INFER_FAILED_BREAK")


def _known_before372(snapshot, cutoff):
    return snapshot.selected is not None and snapshot.confirmation_prerequisites(cutoff)


def _retest_order372(target, failed, breakout, witness, cutoff, pivot_price):
    if not _known_before372(target, cutoff):
        return "RETEST_NOT_CLOSED_OR_KNOWN"
    start = target.market_bar_key.bar_start_utc
    if witness > start or not _known_before372(breakout, start):
        return "BREAKOUT_NOT_VERIFIED_BEFORE_RETEST"
    if failed is not None:
        if not _known_before372(failed, start) or failed.market_bar_key.bar_start_utc < witness:
            return "FAILED_BREAK_NOT_CAUSALLY_BETWEEN_BREAKOUT_AND_RETEST"
        if failed.selected.close >= pivot_price:
            return "FAILED_BREAK_GEOMETRY_NOT_BELOW_PIVOT"
    return None


def _breakout_geometry372(rows, atr, plan, cutoff):
    history = rows[:plan.breakout_index - 1]
    prev, target = rows[plan.breakout_index - 1:plan.breakout_index + 1]
    geom = inspect_closed_bos_geometry(
        history, pivot_index=plan.pivot_index, left_count=plan.left_count,
        right_count=plan.right_count, previous=prev, breakout=target,
        atr_d1_history=atr, side=StructureSide.HIGH, tie_policy=plan.tie_policy,
        candidate_epsilon=plan.candidate_epsilon, as_of_utc=cutoff,
    )
    if geom.state is not GeometryState.DESCRIPTIVE_ONLY or not geom.candidate_cross:
        return geom, None, None
    pivot = inspect_causal_pivot(
        history, candidate_index=plan.pivot_index, left_count=plan.left_count,
        right_count=plan.right_count, side=StructureSide.HIGH,
        tie_policy=plan.tie_policy, as_of_utc=target.market_bar_key.bar_start_utc,
    )
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY or not pivot.geometric_extremum:
        raise ValueError("MST_372_PIVOT_CHANGED_BETWEEN_CHECKS")
    digest = _digest({
        "schema": "mst.b5.baseline_breakout372.v0.1",
        "pivot_index": plan.pivot_index, "left": plan.left_count, "right": plan.right_count,
        "tie": plan.tie_policy.value, "epsilon": str(plan.candidate_epsilon),
        "pivot_history": [_bar_identity(r) for r in history],
        "previous": _bar_identity(prev), "breakout": _bar_identity(target),
        "atr": [_bar_identity(r) for r in atr],
    })
    return geom, pivot.pivot_price, "MST_B5_BREAKOUT_PREVIEW372:" + digest


def inspect_b5_baseline_retest(inputs, *, strategy, variant_id, plan):
    """R0/R_C/R_E raw math from one baseline; no PriorPivot or policy claim.

    The prior pivot and breakout are re-derived from exact snapshots. A
    source-verified flag, event receipt or risk/volume policy is never minted.
    Explicit historical ATR slice/epsilon is research config, not approved
    window/threshold or proof of the latest eligible historical observation.
    R_F is deliberately not evaluated here.
    """
    if type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy:
        raise TypeError("MST_372_BASELINE_INPUT_REQUIRED")
    if variant_id not in B5_VARIANTS:
        raise ValueError("MST_372_EXPLICIT_B5_VARIANT")
    _validate_plan372(plan, variant_id)
    routes = tuple(route_phase_inputs(
        inputs, zone_id="B5", strategy=strategy, variant_id=variant_id, phase=phase,
        selected_frame=plan.breakout_tf if phase == "R0" else None,
    ) for phase in ("R0", "R_C", "R_E"))

    def finish(state, reason, metrics=None):
        return B5BaselineRetestPreview372(
            strategy, variant_id, inputs.as_of_utc, routes, state, reason, metrics)

    higher = inputs.snapshots_for(plan.breakout_tf)
    m15 = inputs.snapshots_for(Timeframe.M15)
    d1 = inputs.snapshots_for(Timeframe.D1)
    if not higher or not m15 or not d1:
        return finish(B5RetestState372.BLOCKED, "REQUIRED_GEOMETRY_INPUT_MISSING")
    if plan.breakout_index >= len(higher) or plan.retest_index >= len(m15) or plan.atr_stop > len(d1):
        raise ValueError("MST_372_INDEX_OUTSIDE_BASELINE")
    atr_rows = d1[plan.atr_start:plan.atr_stop]
    geom, pivot, preview_id = _breakout_geometry372(higher, atr_rows, plan, inputs.as_of_utc)
    if geom.state is not GeometryState.DESCRIPTIVE_ONLY:
        return finish(B5RetestState372.BLOCKED, "BREAKOUT_" + geom.reason)
    if not geom.candidate_cross:
        return finish(B5RetestState372.NONCROSS_GEOMETRY_ONLY, "NO_PRIOR_CLOSED_CROSS_GEOMETRY")
    breakout, retest = higher[plan.breakout_index], m15[plan.retest_index]
    failed = None if plan.failed_break_index is None else m15[plan.failed_break_index]
    reason = _retest_order372(retest, failed, breakout, geom.witness_known_at_utc,
                              inputs.as_of_utc, pivot)
    if reason is not None:
        return finish(B5RetestState372.BLOCKED, reason)
    atr = calculate_wilder_atr14(atr_rows, as_of_utc=inputs.as_of_utc,
                                known_before_utc=retest.market_bar_key.bar_start_utc)
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None:
        return finish(B5RetestState372.BLOCKED, "RETEST_ATR_" + atr.reason)
    a, b = breakout.selected, retest.selected
    digest = _digest({
        "schema": "mst.b5.baseline_retest372.v0.1",
        "strategy": strategy.value, "variant": variant_id, "breakout": preview_id,
        "retest": _bar_identity(retest),
        "failed": _bar_identity(failed) if failed is not None else None,
        "atr": [_bar_identity(r) for r in atr_rows],
    })
    metrics = B5RetestMetrics372(
        pivot, (a.close - pivot) / atr.value, (b.low - pivot) / atr.value,
        (b.close - pivot) / atr.value, (b.close - b.low) / atr.value,
        None if failed is None else (failed.selected.close - pivot) / atr.value,
        preview_id, "MST_B5_RETEST_PREVIEW372:" + digest,
    )
    return finish(B5RetestState372.RAW_RETEST_UNCALIBRATED,
                  "R0_RC_RE_GEOMETRY_ONLY_RF_AND_CALIBRATION_PENDING", metrics)
