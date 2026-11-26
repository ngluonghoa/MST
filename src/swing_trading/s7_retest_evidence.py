"""§264 S7 R0/R_C geometry, not a detector. Frozen spec §§16.7,24.4/5.
Reuse causal LOW pivot/BOS and prior ATR; no inferred expiry, thresholds,
calendar, source entitlement, trade or approved S7 phase.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy, inspect_causal_pivot,
    inspect_closed_bos_geometry, _eligible, _cross_tf_identity, _source_identity,
)
from .contracts import DecisionStatus, Strategy
from .market_data import Timeframe
from .private_multitf_readiness import BaselineResolvedInputs
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12
from .structural_phase_evidence import (
    _bar_identity, _digest, PhaseEvidenceState, inspect_phase_bos_evidence,
)



def _consistent_chain_observations(*groups):
    """Reject contradictory snapshots of one exact MarketBarKey across phases.

    This is an in-memory consistency gate, not a provider revision policy.
    Identical repeated observations are allowed across distinct dependencies;
    an unresolved input or a different selected payload for the same key
    cannot be silently spliced into a single diagnostic chain.
    """
    seen = {}
    for group in groups:
        if type(group) is not tuple:
            return False
        for snap in group:
            if not isinstance(snap, ResolvedBarSnapshotV12):
                return False
            if snap.selected is None:
                return False
            key = snap.market_bar_key
            if key in seen and seen[key] != snap.selected:
                return False
            seen[key] = snap.selected
    return True


@dataclass(frozen=True)
class S7RetestEvidence:
    strategy: Strategy
    as_of_utc: datetime
    reason: str
    origin_preview_id: str | None = None
    retest_preview_id: str | None = None
    close_distance_atr: Decimal | None = None
    range_distance_atr: Decimal | None = None
    close_above_pivot: bool | None = None
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    action_eligible: bool = False
    parameter_approved: bool = False
    detector_approved: bool = False

    def __post_init__(self):
        require_utc(self.as_of_utc)
        if (not isinstance(self.strategy, Strategy) or not self.reason
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False
                or self.parameter_approved is not False
                or self.detector_approved is not False):
            raise ValueError("S7_PREVIEW_AUTHORITY_FORBIDDEN")
        fields = (self.origin_preview_id, self.retest_preview_id,
                  self.close_distance_atr, self.range_distance_atr,
                  self.close_above_pivot)
        if any(x is not None for x in fields):
            if (any(x is None for x in fields)
                    or self.reason != "EXACT_PIVOT_GEOMETRY_UNCALIBRATED"
                    or type(self.close_above_pivot) is not bool
                    or any(type(x) is not Decimal or not x.is_finite() or x < 0
                           for x in fields[2:4])
                    or any(type(x) is not str or len(x) != 64
                           or any(c not in "0123456789abcdef" for c in x)
                           for x in fields[:2])):
                raise ValueError("S7_PREVIEW_SHAPE_INVALID")
        elif self.reason == "EXACT_PIVOT_GEOMETRY_UNCALIBRATED":
            raise ValueError("S7_PREVIEW_MISSING_GEOMETRY")


def inspect_s7_retest_evidence(
    pivot_history, *, pivot_index, left_count, right_count, tie_policy,
    previous, breakdown, prior_retest, retest, atr_d1_history,
    retest_atr_d1_history, candidate_epsilon, strategy, as_of_utc,
):
    """One original support break, then one later M15 observation from below.
    No declaration that the supplied prior bars are exchange-adjacent;
    no window policy or approved NEAR predicate. All outputs UNVERIFIED.
    """
    require_utc(as_of_utc)

    def blocked(reason):
        return S7RetestEvidence(strategy, as_of_utc, reason)

    a = _eligible(breakdown, cutoff=as_of_utc)
    b = _eligible(retest, cutoff=as_of_utc)
    if a is None or b is None:
        return blocked("SOURCE_OR_ASOF_UNVERIFIED")
    ka, kb = a.market_bar_key, b.market_bar_key
    if ka.timeframe not in (Timeframe.D1, Timeframe.H1) or kb.timeframe is not Timeframe.M15:
        return blocked("S7_REQUIRES_D1_H1_ORIGIN_AND_M15_REFERENCE")
    if _cross_tf_identity(a) != _cross_tf_identity(b):
        return blocked("MIXED_SOURCE_OR_BASIS")
    cutoff = kb.bar_start_utc
    prior = _eligible(prior_retest, cutoff=cutoff)
    if (prior is None or prior.market_bar_key.timeframe is not Timeframe.M15
            or _source_identity(prior) != _source_identity(b)
            or prior.bar_end_utc > cutoff or prior.market_bar_key == kb
            or _eligible(breakdown, cutoff=prior.market_bar_key.bar_start_utc) is None):
        return blocked("RETEST_SEQUENCE_OR_PRIOR_NOT_KNOWN")
    bos = inspect_closed_bos_geometry(
        pivot_history, pivot_index=pivot_index, left_count=left_count,
        right_count=right_count, previous=previous, breakout=breakdown,
        atr_d1_history=atr_d1_history, side=StructureSide.LOW,
        tie_policy=tie_policy, candidate_epsilon=candidate_epsilon,
        as_of_utc=prior.market_bar_key.bar_start_utc,
    )
    if bos.state is not GeometryState.DESCRIPTIVE_ONLY or bos.candidate_cross is not True:
        return blocked("NO_CAUSAL_LOW_PIVOT_CROSS")
    pivot = inspect_causal_pivot(
        pivot_history, candidate_index=pivot_index, left_count=left_count,
        right_count=right_count, side=StructureSide.LOW, tie_policy=tie_policy,
        as_of_utc=ka.bar_start_utc,
    )
    if pivot.pivot_price is None or prior.close >= pivot.pivot_price:
        return blocked("NO_APPROACH_FROM_BELOW")
    atr = calculate_wilder_atr14(
        retest_atr_d1_history, as_of_utc=as_of_utc, known_before_utc=cutoff,
    )
    if atr.state is not IndicatorState.COMPUTED_UNCALIBRATED or atr.value is None or atr.value <= 0:
        return blocked("RETEST_ATR_UNAVAILABLE")
    if _cross_tf_identity(retest_atr_d1_history[0].selected) != _cross_tf_identity(b):
        return blocked("RETEST_ATR_SOURCE_MISMATCH")
    if not _consistent_chain_observations(
        pivot_history, (previous, breakdown, prior_retest, retest),
        atr_d1_history, retest_atr_d1_history,
    ):
        return blocked("S7_CHAIN_REVISION_CONFLICT")
    price = pivot.pivot_price
    origin = _digest({"version": "S7_ORIGIN_PREVIEW_264", "pivot_history":
                      [_bar_identity(x) for x in pivot_history],
                      "index": pivot_index, "left": left_count, "right": right_count,
                      "tie": tie_policy.value, "epsilon": str(candidate_epsilon),
                      "previous": _bar_identity(previous),
                      "breakdown": _bar_identity(breakdown),
                      "atr": [_bar_identity(x) for x in atr_d1_history]})
    evidence = _digest({"version": "S7_RETEST_PREVIEW_264", "origin": origin,
                        "prior": _bar_identity(prior_retest),
                        "retest": _bar_identity(retest),
                        "atr": [_bar_identity(x) for x in retest_atr_d1_history]})
    return S7RetestEvidence(
        strategy, as_of_utc, "EXACT_PIVOT_GEOMETRY_UNCALIBRATED",
        origin, evidence, abs(b.close-price)/atr.value,
        max(b.low-price, Decimal(0), price-b.high)/atr.value, b.close > price,
    )


class S7EarlyMode(str, Enum):
    """Explicit research shapes, NOT new canonical strategy variants."""
    TOUCH_CLOSE_BELOW = "TOUCH_CLOSE_BELOW"
    LATER_CLOSE_BELOW = "LATER_CLOSE_BELOW"


@dataclass(frozen=True)
class S7EarlyEvidence:
    strategy: Strategy
    as_of_utc: datetime
    mode: S7EarlyMode
    reason: str
    origin_preview_id: str | None = None
    retest_preview_id: str | None = None
    early_preview_id: str | None = None
    shape_observed: bool | None = None
    witness_known_at_utc: datetime | None = None
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    action_eligible: bool = False
    detector_approved: bool = False
    source_independently_attested: bool = False

    def __post_init__(self):
        require_utc(self.as_of_utc)
        if (not isinstance(self.strategy, Strategy)
                or not isinstance(self.mode, S7EarlyMode)
                or type(self.reason) is not str or not self.reason
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False
                or self.detector_approved is not False
                or self.source_independently_attested is not False):
            raise ValueError("S7_EARLY_AUTHORITY_FORBIDDEN")
        ids = (self.origin_preview_id, self.retest_preview_id, self.early_preview_id)
        fields = (*ids, self.shape_observed, self.witness_known_at_utc)
        if self.reason == "M15_SHAPE_ONLY_UNCALIBRATED":
            if (any(type(x) is not str or len(x) != 64
                    or any(c not in "0123456789abcdef" for c in x) for x in ids)
                    or type(self.shape_observed) is not bool):
                raise ValueError("S7_EARLY_SHAPE_INVALID")
            require_utc(self.witness_known_at_utc)
            if self.witness_known_at_utc > self.as_of_utc:
                raise ValueError("S7_EARLY_FUTURE_WITNESS")
        elif any(x is not None for x in fields):
            raise ValueError("S7_EARLY_BLOCKED_HAS_OUTPUT")


def inspect_s7_early_evidence(
    *, mode: S7EarlyMode, followup=None, **base_inputs,
) -> S7EarlyEvidence:
    """Source-locked §24.4 R_E M15 ingredient, without an approved predicate.

    Recompute R0/R_C from the exact inputs; never accept caller-supplied
    evidence IDs. TOUCH_CLOSE_BELOW: high reaches pivot, close strictly
    below. LATER_CLOSE_BELOW: retest close strictly above pivot, then a
    distinct closed M15 bar below. The latter retest must be known by the
    followup start. Equality is not a cross. No implicit mode fallback,
    no inferred exchange adjacency, expiry, wick ordering, NEAR threshold,
    LH, invalidation, source rights, or full S7 phase. False geometry is
    not NOT_DETECTED. No action or provider qualification.
    """
    if not isinstance(mode, S7EarlyMode):
        raise ValueError("S7_EARLY_EXPLICIT_MODE_REQUIRED")
    as_of = base_inputs["as_of_utc"]
    strategy = base_inputs["strategy"]
    require_utc(as_of)

    def blocked(reason):
        return S7EarlyEvidence(strategy, as_of, mode, reason)

    if mode is S7EarlyMode.TOUCH_CLOSE_BELOW and followup is not None:
        return blocked("UNEXPECTED_FOLLOWUP")
    if mode is S7EarlyMode.LATER_CLOSE_BELOW and followup is None:
        return blocked("MISSING_FOLLOWUP")
    base = inspect_s7_retest_evidence(**base_inputs)
    if base.origin_preview_id is None or base.retest_preview_id is None:
        return blocked("BASE_" + base.reason)
    retest = base_inputs["retest"]
    b = retest.selected
    # The same LOW pivot was already recomputed and validated by the base
    # function. Reuse that exact input bar, not a supplied price or ID.
    pivot = base_inputs["pivot_history"][base_inputs["pivot_index"]].selected.low
    if mode is S7EarlyMode.TOUCH_CLOSE_BELOW:
        shape = b.high >= pivot and b.close < pivot
        witness = b
        followup_identity = None
    else:
        c = _eligible(followup, cutoff=as_of)
        if (c is None or c.market_bar_key.timeframe is not Timeframe.M15
                or _source_identity(c) != _source_identity(b)
                or c.market_bar_key == b.market_bar_key
                or b.bar_end_utc > c.market_bar_key.bar_start_utc
                or _eligible(retest, cutoff=c.market_bar_key.bar_start_utc) is None):
            return blocked("FOLLOWUP_SOURCE_OR_CLOCK_MISMATCH")
        shape = b.close > pivot and c.close < pivot
        witness = c
        followup_identity = _bar_identity(followup)
    digest = _digest({
        "version": "S7_EARLY_PREVIEW_266", "mode": mode.value,
        "origin": base.origin_preview_id, "retest": base.retest_preview_id,
        "followup": followup_identity,
    })
    known = max(witness.bar_end_utc, witness.verified_at_utc,
                witness.observation_revision.first_known_time_utc)
    return S7EarlyEvidence(
        strategy, as_of, mode, "M15_SHAPE_ONLY_UNCALIBRATED",
        base.origin_preview_id, base.retest_preview_id, digest, shape, known,
    )


@dataclass(frozen=True)
class S7ConfirmationEvidence:
    strategy: Strategy
    as_of_utc: datetime
    reason: str
    origin_preview_id: str | None = None
    retest_preview_id: str | None = None
    early_preview_id: str | None = None
    micro_bos_preview_id: str | None = None
    confirmation_preview_id: str | None = None
    witness_known_at_utc: datetime | None = None
    variant_id: str = "S7/F_MICRO_BREAK"
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    action_eligible: bool = False
    detector_approved: bool = False
    parameter_approved: bool = False
    source_independently_attested: bool = False

    def __post_init__(self):
        require_utc(self.as_of_utc)
        if (not isinstance(self.strategy, Strategy)
                or type(self.reason) is not str or not self.reason
                or self.variant_id != "S7/F_MICRO_BREAK"
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False
                or self.detector_approved is not False
                or self.parameter_approved is not False
                or self.source_independently_attested is not False):
            raise ValueError("S7_RF_AUTHORITY_FORBIDDEN")
        ids = (self.origin_preview_id, self.retest_preview_id,
               self.early_preview_id, self.confirmation_preview_id)
        fields = (*ids, self.micro_bos_preview_id, self.witness_known_at_utc)
        if self.reason == "RF_CHAIN_GEOMETRY_UNCALIBRATED":
            if any(type(x) is not str or len(x) != 64
                   or any(c not in "0123456789abcdef" for c in x) for x in ids):
                raise ValueError("S7_RF_INVALID_CHAIN_ID")
            prefix = "MST_BOS_PREVIEW_V1:"
            micro = self.micro_bos_preview_id
            if (type(micro) is not str or not micro.startswith(prefix)
                    or len(micro) != len(prefix)+64
                    or any(c not in "0123456789abcdef" for c in micro[len(prefix):])):
                raise ValueError("S7_RF_INVALID_MICRO_BOS_ID")
            require_utc(self.witness_known_at_utc)
            if self.witness_known_at_utc > self.as_of_utc:
                raise ValueError("S7_RF_FUTURE_WITNESS")
        elif any(x is not None for x in fields):
            raise ValueError("S7_RF_BLOCKED_HAS_OUTPUT")


def inspect_s7_confirmation_evidence(
    *, variant_id, mode, followup=None, confirmation, micro_history,
    micro_index, micro_left, micro_right, micro_previous, micro_atr_history,
    micro_tie_policy, micro_epsilon, **base_inputs,
) -> S7ConfirmationEvidence:
    """Bind only the existing S7/F_MICRO_BREAK descriptive branch.

    Recompute R_E before target START. Require closed H1/D1 below original
    support and a distinct subsequent same-TF causal LOW crossing. The
    candidate micro pivot starts after the early witness (conservative
    research subset, not an approved definition of a retest swing).
    No continuity, expiry, volume, risk, holding or alternative F_CONTINUATION
    certification; no caller-supplied IDs or inferred strategy approval.
    """
    if variant_id != "S7/F_MICRO_BREAK":
        raise ValueError("S7_RF_EXPLICIT_MICRO_BREAK_ONLY")
    as_of = base_inputs["as_of_utc"]
    strategy = base_inputs["strategy"]
    require_utc(as_of)

    def blocked(reason):
        return S7ConfirmationEvidence(strategy, as_of, reason)

    target = _eligible(confirmation, cutoff=as_of)
    if target is None or target.market_bar_key.timeframe not in (Timeframe.H1, Timeframe.D1):
        return blocked("RF_TARGET_NOT_CLOSED_H1_D1")
    cutoff = target.market_bar_key.bar_start_utc
    early_inputs = dict(base_inputs, as_of_utc=cutoff)
    early = inspect_s7_early_evidence(mode=mode, followup=followup, **early_inputs)
    if early.shape_observed is not True or early.witness_known_at_utc is None:
        return blocked("RF_EARLY_SHAPE_NOT_CAUSALLY_PRESENT")
    retest = base_inputs["retest"].selected
    if _cross_tf_identity(target) != _cross_tf_identity(retest):
        return blocked("RF_TARGET_SOURCE_MISMATCH")
    old_support = base_inputs["pivot_history"][base_inputs["pivot_index"]].selected.low
    if target.close >= old_support:
        return blocked("RF_CLOSE_NOT_BELOW_ORIGINAL_SUPPORT")
    if (type(micro_history) is not tuple or len(micro_history) > 512
            or type(micro_index) is not int or not 0 <= micro_index < len(micro_history)):
        return blocked("RF_MICRO_HISTORY_INVALID")
    rows = tuple(_eligible(item, cutoff=cutoff) for item in micro_history)
    if (any(row is None or row.market_bar_key.timeframe is not target.market_bar_key.timeframe
            or _source_identity(row) != _source_identity(target) for row in rows)
            or rows[micro_index].market_bar_key.bar_start_utc < early.witness_known_at_utc):
        return blocked("RF_MICRO_PIVOT_SOURCE_OR_SEQUENCE_MISMATCH")
    phase = inspect_phase_bos_evidence(
        zone_id="S7", strategy=strategy, variant_id=variant_id, phase="R_F",
        pivot_history=micro_history, pivot_index=micro_index,
        left_count=micro_left, right_count=micro_right,
        previous=micro_previous, breakout=confirmation,
        atr_d1_history=micro_atr_history, tie_policy=micro_tie_policy,
        candidate_epsilon=micro_epsilon, as_of_utc=as_of,
    )
    if phase.state is not PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED:
        return blocked("RF_MICRO_CROSS_NOT_PRESENT")
    early_bars = (followup,) if followup is not None else ()
    if not _consistent_chain_observations(
        base_inputs["pivot_history"], base_inputs["atr_d1_history"],
        base_inputs["retest_atr_d1_history"],
        (base_inputs["previous"], base_inputs["breakdown"],
         base_inputs["prior_retest"], base_inputs["retest"]),
        early_bars, micro_history, (micro_previous, confirmation), micro_atr_history,
    ):
        return blocked("S7_CHAIN_REVISION_CONFLICT")
    digest = _digest({
        "version": "S7_RF_CHAIN_PREVIEW_267", "variant": variant_id,
        "origin": early.origin_preview_id, "retest": early.retest_preview_id,
        "early": early.early_preview_id, "micro_bos": phase.bos_preview_id,
        "target": _bar_identity(confirmation),
    })
    return S7ConfirmationEvidence(
        strategy, as_of, "RF_CHAIN_GEOMETRY_UNCALIBRATED",
        early.origin_preview_id, early.retest_preview_id, early.early_preview_id,
        phase.bos_preview_id, digest, phase.witness_known_at_utc,
    )


@dataclass(frozen=True)
class S7OriginPlan374:
    timeframe: Timeframe
    history_start: int
    breakdown_index: int
    pivot_index: int
    left_count: int
    right_count: int
    atr_start: int
    atr_stop: int
    retest_atr_start: int
    retest_atr_stop: int
    retest_index: int
    mode: S7EarlyMode
    followup_index: int | None
    tie_policy: TiePolicy
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class S7MicroPlan374:
    timeframe: Timeframe
    history_start: int
    confirmation_index: int
    pivot_index: int
    left_count: int
    right_count: int
    atr_start: int
    atr_stop: int
    tie_policy: TiePolicy
    candidate_epsilon: Decimal | None


@dataclass(frozen=True)
class S7BaselinePreview374:
    strategy: Strategy
    variant_id: str
    as_of_utc: datetime
    routed_phases: tuple
    retest: S7RetestEvidence | None
    early: S7EarlyEvidence | None
    confirmation: S7ConfirmationEvidence | None
    reason: str

    @property
    def status(self):
        return DecisionStatus.UNVERIFIED

    @property
    def action_eligible(self):
        return False


def _slice374(rows, start, stop):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop:
        raise ValueError("MST_374_INVALID_SLICE")
    if rows and stop > len(rows):
        raise ValueError("MST_374_SLICE_OUTSIDE_SCOPE")
    return rows[start:stop]


def _index374(rows, index):
    if type(index) is not int or index < 0:
        raise ValueError("MST_374_INVALID_INDEX")
    if rows and index >= len(rows):
        raise ValueError("MST_374_INDEX_OUTSIDE_SCOPE")
    return rows[index] if rows else None


def _validate_break374(plan, target_index):
    if (type(plan.timeframe) is not Timeframe
            or plan.timeframe not in (Timeframe.D1, Timeframe.H1)
            or type(plan.tie_policy) is not TiePolicy):
        raise ValueError("MST_374_EXPLICIT_BREAK_FRAME_OR_TIE")
    nums = (target_index, plan.history_start, plan.pivot_index,
            plan.left_count, plan.right_count)
    if any(type(n) is not int or n < 0 for n in nums):
        raise ValueError("MST_374_INVALID_BREAK_INDEX")
    if (min(plan.left_count, plan.right_count) < 1
            or plan.pivot_index < plan.left_count
            or plan.history_start + plan.pivot_index + plan.right_count >= target_index - 1):
        raise ValueError("MST_374_INVALID_BREAK_WINDOW")


def _origin374(inputs, plan, strategy):
    _validate_break374(plan, plan.breakdown_index)
    if type(plan.retest_index) is not int or plan.retest_index < 1:
        raise ValueError("MST_374_RETEST_REQUIRES_PRIOR")
    if type(plan.mode) is not S7EarlyMode:
        raise ValueError("MST_374_EXPLICIT_EARLY_MODE")
    if plan.mode is S7EarlyMode.LATER_CLOSE_BELOW:
        if type(plan.followup_index) is not int or plan.followup_index != plan.retest_index + 1:
            raise ValueError("MST_374_EXPLICIT_NEXT_OBSERVED_FOLLOWUP")
    elif plan.followup_index is not None:
        raise ValueError("MST_374_TOUCH_HAS_NO_FOLLOWUP")
    higher = inputs.snapshots_for(plan.timeframe)
    m15 = inputs.snapshots_for(Timeframe.M15)
    d1 = inputs.snapshots_for(Timeframe.D1)
    history = _slice374(higher, plan.history_start, plan.breakdown_index - 1)
    atr = _slice374(d1, plan.atr_start, plan.atr_stop)
    retest_atr = _slice374(d1, plan.retest_atr_start, plan.retest_atr_stop)
    breakdown = _index374(higher, plan.breakdown_index)
    prior = _index374(m15, plan.retest_index - 1)
    retest = _index374(m15, plan.retest_index)
    followup = None if plan.followup_index is None else _index374(m15, plan.followup_index)
    if not history or not atr or not retest_atr or prior is None or retest is None:
        return None, followup
    return dict(pivot_history=history, pivot_index=plan.pivot_index,
                left_count=plan.left_count, right_count=plan.right_count,
                tie_policy=plan.tie_policy, previous=higher[plan.breakdown_index - 1],
                breakdown=breakdown, prior_retest=prior, retest=retest,
                atr_d1_history=atr, retest_atr_d1_history=retest_atr,
                candidate_epsilon=plan.candidate_epsilon, strategy=strategy,
                as_of_utc=inputs.as_of_utc), followup


def _micro374(inputs, plan):
    _validate_break374(plan, plan.confirmation_index)
    rows = inputs.snapshots_for(plan.timeframe)
    history = _slice374(rows, plan.history_start, plan.confirmation_index - 1)
    atr = _slice374(inputs.snapshots_for(Timeframe.D1), plan.atr_start, plan.atr_stop)
    target = _index374(rows, plan.confirmation_index)
    if not history or not atr or target is None:
        return None
    return dict(confirmation=target, micro_history=history,
                micro_index=plan.pivot_index, micro_left=plan.left_count,
                micro_right=plan.right_count, micro_previous=rows[plan.confirmation_index - 1],
                micro_atr_history=atr, micro_tie_policy=plan.tie_policy,
                micro_epsilon=plan.candidate_epsilon)


def inspect_s7_baseline_preview(inputs, *, strategy, variant_id, origin_plan, micro_plan=None):
    """Recompute one exact S7 chain from bound rows; continuation stays pending.

    Plan indices address contiguous observed slices, not attested exchange
    adjacency. Explicit continuation has no approved predicate; never substitute
    the micro-break result or invent a continuation threshold.
    """
    if (type(inputs) is not BaselineResolvedInputs or type(strategy) is not Strategy
            or type(origin_plan) is not S7OriginPlan374
            or variant_id not in ("S7/F_MICRO_BREAK", "S7/F_CONTINUATION")):
        raise ValueError("MST_374_EXPLICIT_S7_PLAN_REQUIRED")
    if variant_id == "S7/F_MICRO_BREAK":
        if type(micro_plan) is not S7MicroPlan374:
            raise ValueError("MST_374_EXPLICIT_MICRO_PLAN_REQUIRED")
    elif micro_plan is not None:
        raise ValueError("MST_374_CONTINUATION_NOT_MICRO_FALLBACK")
    base, followup = _origin374(inputs, origin_plan, strategy)
    micro = _micro374(inputs, micro_plan) if micro_plan is not None else None
    routes = tuple(route_phase_inputs(
        inputs, zone_id="S7", strategy=strategy, variant_id=variant_id, phase=phase,
        selected_frame=(origin_plan.timeframe if phase == "R0" else
                        micro_plan.timeframe if phase == "R_F" and micro_plan is not None else None),
    ) for phase in ("R0", "R_C", "R_E", "R_F"))

    def finish(reason, retest=None, early=None, confirmation=None):
        return S7BaselinePreview374(strategy, variant_id, inputs.as_of_utc,
                                    routes, retest, early, confirmation, reason)

    if base is None:
        return finish("ORIGIN_OR_RETEST_INPUT_MISSING")
    retest = inspect_s7_retest_evidence(**base)
    early = inspect_s7_early_evidence(mode=origin_plan.mode, followup=followup, **base)
    if variant_id == "S7/F_CONTINUATION":
        return finish("CONTINUATION_PREDICATE_SPEC_PENDING", retest, early)
    if micro is None:
        return finish("MICRO_INPUT_MISSING", retest, early)
    confirmation = inspect_s7_confirmation_evidence(
        variant_id=variant_id, mode=origin_plan.mode, followup=followup, **micro, **base)
    return finish(confirmation.reason, retest, early, confirmation)
