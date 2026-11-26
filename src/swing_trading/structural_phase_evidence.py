"""§207 versioned PREVIEW ONLY structure evidence → locked zone phase.

Bounded, deterministic evidence identifiers built from actual in-memory v1.2
resolved bar identities/revisions. These are UNSIGNED fingerprints and cannot
attest provider origin, licensed exchange time, calibrated thresholds, source
completeness, or an approved original B/S detector. No source prices or raw
vendor records are exported by the evidence/zone projection.

Source contract: Swing Trading 1.8 frozen 01_MASTER_SPEC §§24.4/24.5/24.10.
Only the explicit BOS / closed pivot-cross phase branches in the route table
are eligible to receive a descriptive geometry attachment. OR variants are
NEVER silently promoted. Missing, noncrossing or corrected evidence does NOT
mean the original detector is NOT_DETECTED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType

from .causal_structure_geometry import (
    GeometryState, StructureSide, TiePolicy,
    inspect_causal_pivot, inspect_closed_bos_geometry,
)
from .causal_indicators import IndicatorState, calculate_wilder_atr14
from .contracts import DecisionStatus, Strategy, ZONE_IDS
from .engine import evaluate_unimplemented_zones
from .market_data import Timeframe
from .private_multitf_readiness import BaselineResolvedInputs
from .phase_input_routing369 import route_phase_inputs
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12
from .zone_manifest_v03 import MANIFESTS, inspect_near_zone_arithmetic

SCHEMA = "mst.preview.phase_structure_evidence.v0.1"
EVENT_VERSION = "MST_PREVIEW_STRUCTURE_SHA256_V0_1"
MAX_HISTORY = 512

# Explicit, source-traceable §24.4 CLOSED structural break branches.
# §207 original 4 R_E branches are retained. §213 adds 14 R_F candidates
# where the spec actually calls for a confirmed close across a known pivot,
# support, resistance or micro-structure. A structural break alone is NEVER
# the full phase: R0/R_C context, position, volume, risk and other R_F
# ingredients are not proven here. Variant-specific OR/TP alternatives are
# deliberately not inferred or silently selected.
_ROUTES = {
    # §207 original R_E geometry paths (behavior and event ID unchanged).
    ("B1", "B1/E_BOS_UP", "R_E"): (StructureSide.HIGH, (Timeframe.M15,)),
    ("B3", "B3/E_BOS_UP", "R_E"): (StructureSide.HIGH, (Timeframe.M15,)),
    ("S4", "S4/E_BOS_DOWN", "R_E"): (
        StructureSide.LOW, (Timeframe.M15, Timeframe.H1),
    ),
    ("B8", "B8/BASE", "R_E"): (StructureSide.HIGH, (Timeframe.M15,)),
    # §213 source-locked R_F closed-break *ingredients only*, no eligibility.
    ("B1", "B1/E_BOS_UP", "R_F"): (StructureSide.HIGH, (Timeframe.D1,)),
    ("B2", "B2/BASE", "R_F"): (
        StructureSide.HIGH, (Timeframe.M15, Timeframe.H1),
    ),
    ("B4", "B4/BASE", "R_F"): (StructureSide.HIGH, (Timeframe.M15,)),
    ("B6", "B6/C_TWO_CONTRACTIONS", "R_F"): (
        StructureSide.HIGH, (Timeframe.H1, Timeframe.D1),
    ),
    ("B7", "B7/E_RECLAIM", "R_F"): (
        StructureSide.HIGH, (Timeframe.M15, Timeframe.H1),
    ),
    ("B8", "B8/BASE", "R_F"): (
        StructureSide.HIGH, (Timeframe.H1, Timeframe.D1),
    ),
    ("S1", "S1/E_CHOCH_DOWN", "R_F"): (StructureSide.LOW, (Timeframe.D1,)),
    ("S2", "S2/BASE", "R_F"): (
        StructureSide.LOW, (Timeframe.M15, Timeframe.H1),
    ),
    ("S3", "S3/F_MICRO_BREAK", "R_F"): (
        StructureSide.LOW, (Timeframe.M15, Timeframe.H1),
    ),
    ("S4", "S4/E_BOS_DOWN", "R_F"): (
        StructureSide.LOW, (Timeframe.H1, Timeframe.D1),
    ),
    ("S5", "S5/BASE", "R_F"): (StructureSide.LOW, (Timeframe.M15,)),
    ("S6", "S6/BASE", "R_F"): (
        StructureSide.LOW, (Timeframe.H1, Timeframe.D1),
    ),
    ("S7", "S7/F_MICRO_BREAK", "R_F"): (
        StructureSide.LOW, (Timeframe.H1, Timeframe.D1),
    ),
    ("S8", "S8/BASE", "R_F"): (
        StructureSide.LOW, (Timeframe.H1, Timeframe.D1),
    ),
}
ROUTES = MappingProxyType(_ROUTES)
if (len(ROUTES) != 18
        or sum(phase == "R_E" for _, _, phase in ROUTES) != 4
        or sum(phase == "R_F" for _, _, phase in ROUTES) != 14
        or any(z not in MANIFESTS or v not in MANIFESTS[z].variants
               or phase not in ("R_E", "R_F")
               or not isinstance(side, StructureSide)
               or not frames
               or any(tf not in (Timeframe.M15, Timeframe.H1, Timeframe.D1)
                      for tf in frames)
               for (z, v, phase), (side, frames) in ROUTES.items())):
    raise RuntimeError("MST_213_SOURCE_PHASE_ROUTE_DRIFT")


class PhaseEvidenceState(str, Enum):
    BLOCKED = "BLOCKED"
    NONCROSS_GEOMETRY_ONLY = "NONCROSS_GEOMETRY_ONLY"
    CROSS_GEOMETRY_UNVERIFIED = "CROSS_GEOMETRY_UNVERIFIED"


class PhaseEvidenceDenied(ValueError):
    """Fixed, non-secret errors; never imply release approval."""


def _digest(data: dict) -> str:
    try:
        wire = json.dumps(data, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError, OverflowError):
        raise PhaseEvidenceDenied("MST_207_NONCANONICAL_EVIDENCE") from None
    return sha256(wire).hexdigest()


def _bar_identity(snapshot: ResolvedBarSnapshotV12) -> dict:
    bar = snapshot.selected
    if bar is None:
        raise PhaseEvidenceDenied("MST_207_UNRESOLVED_BAR")
    key, obs, rev = bar.market_bar_key, bar.observation_key, bar.observation_revision
    return {
        "instrument_id": key.instrument_id,
        "exchange": key.exchange,
        "instrument_class": key.instrument_class.value,
        "timeframe": key.timeframe.value,
        "session_period_id": key.session_period_id,
        "bar_start_utc": key.bar_start_utc.isoformat(),
        "bar_end_utc": bar.bar_end_utc.isoformat(),
        "price_basis": key.price_basis.value,
        "calendar_version": key.calendar_version,
        "aggregation_policy_version": key.aggregation_policy_version,
        "project_id": obs.project_id,
        "provider_id": obs.provider_id,
        "origin": obs.origin.value,
        "source_stream_id": obs.source_stream_id,
        "source_revision": rev.source_revision_or_payload_digest,
        "adjustment_revision": rev.adjustment_revision,
        "ingestion_revision": rev.ingestion_revision,
        "first_known_utc": rev.first_known_time_utc.isoformat(),
        "retrieved_utc": rev.retrieved_at_utc.isoformat(),
        "verified_utc": bar.verified_at_utc.isoformat(),
        "raw_digest_sha256": bar.raw_digest_sha256,
        "normalized_digest_sha256": bar.normalized_digest_sha256,
        "source_snapshot_id": bar.provenance.source_snapshot_id,
        "source_record_id": bar.provenance.source_record_id,
        "ohlc": [str(bar.open), str(bar.high), str(bar.low), str(bar.close)],
    }


@dataclass(frozen=True)
class PhaseStructureEvidence:
    zone_id: str
    strategy: Strategy
    variant_id: str
    phase: str
    predicate_ref: str
    side: StructureSide
    timeframe: Timeframe
    as_of_utc: datetime
    state: PhaseEvidenceState
    reason: str
    pivot_preview_id: str | None = None
    bos_preview_id: str | None = None
    witness_known_at_utc: datetime | None = None
    schema: str = SCHEMA
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    source_independently_attested: bool = False
    detector_approved: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)
        route = ROUTES.get((self.zone_id, self.variant_id, self.phase))
        if (route is None or not isinstance(self.strategy, Strategy)
                or self.predicate_ref != MANIFESTS[self.zone_id].predicate_for(self.phase)
                or self.side is not route[0] or self.timeframe not in route[1]
                or not isinstance(self.state, PhaseEvidenceState)
                or not isinstance(self.reason, str) or not self.reason
                or self.schema != SCHEMA
                or self.status is not DecisionStatus.UNVERIFIED
                or self.source_independently_attested is not False
                or self.detector_approved is not False
                or self.action_eligible is not False):
            raise PhaseEvidenceDenied("MST_207_PHASE_PROMOTION_OR_SCOPE_FORBIDDEN")
        has_candidate = self.state is PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED
        if has_candidate:
            if (self.pivot_preview_id is None or self.bos_preview_id is None
                    or self.witness_known_at_utc is None):
                raise PhaseEvidenceDenied("MST_207_CROSS_MISSING_WITNESS")
            require_utc(self.witness_known_at_utc)
            if self.witness_known_at_utc > self.as_of_utc:
                raise PhaseEvidenceDenied("MST_207_FUTURE_EVIDENCE")
            for prefix, value in (("MST_PIVOT_PREVIEW_V1:", self.pivot_preview_id),
                                  ("MST_BOS_PREVIEW_V1:", self.bos_preview_id)):
                if (type(value) is not str or not value.startswith(prefix)
                        or len(value) != len(prefix) + 64
                        or any(c not in "0123456789abcdef"
                               for c in value[len(prefix):])):
                    raise PhaseEvidenceDenied("MST_207_PREVIEW_ID_INVALID")
        elif (self.pivot_preview_id is not None
              or self.bos_preview_id is not None
              or self.witness_known_at_utc is not None):
            raise PhaseEvidenceDenied("MST_207_NONCROSS_CANNOT_CLAIM_EVENT")


def inspect_phase_bos_evidence(
    *,
    zone_id: str,
    strategy: Strategy,
    variant_id: str,
    phase: str,
    pivot_history: tuple[ResolvedBarSnapshotV12, ...],
    pivot_index: int,
    left_count: int,
    right_count: int,
    previous: ResolvedBarSnapshotV12,
    breakout: ResolvedBarSnapshotV12,
    atr_d1_history: tuple[ResolvedBarSnapshotV12, ...],
    tie_policy: TiePolicy,
    candidate_epsilon: Decimal | None,
    as_of_utc: datetime,
) -> PhaseStructureEvidence:
    """Attach ONLY a descriptive event-fingerprint to a source-locked phase.

    Replay identity is stable for the same revision/time/version input.
    Corrected revisions, changed policy or changed target bar MUST yield a
    different fingerprint; downstream must handle supersession separately.
    """
    require_utc(as_of_utc)
    route = ROUTES.get((zone_id, variant_id, phase))
    if route is None or not isinstance(strategy, Strategy):
        raise PhaseEvidenceDenied("MST_207_UNSUPPORTED_ZONE_VARIANT_OR_PHASE")
    if (type(pivot_history) is not tuple or not isinstance(breakout, ResolvedBarSnapshotV12)
            or not isinstance(previous, ResolvedBarSnapshotV12)
            or type(atr_d1_history) is not tuple
            or len(pivot_history) > MAX_HISTORY
            or len(atr_d1_history) > MAX_HISTORY):
        raise PhaseEvidenceDenied("MST_207_INVALID_OR_OVERSIZED_INPUT")
    target = breakout.selected
    target_timeframe = breakout.market_bar_key.timeframe
    if target_timeframe not in route[1]:
        raise PhaseEvidenceDenied("MST_207_PHASE_TIMEFRAME_MISMATCH")
    side = route[0]
    ref = MANIFESTS[zone_id].predicate_for(phase)

    def finish(state, reason, pivot_id=None, bos_id=None, witnessed=None):
        return PhaseStructureEvidence(
            zone_id, strategy, variant_id, phase, ref, side,
            target_timeframe, as_of_utc, state, reason,
            pivot_id, bos_id, witnessed,
        )

    # A revision conflict has a grounded MarketBarKey but no selected bar.
    # This is BLOCKED, never a reason to guess a revision or report NO_SIGNAL.
    if target is None:
        return finish(PhaseEvidenceState.BLOCKED, "UNRESOLVED_TARGET_REVISION")

    geometry = inspect_closed_bos_geometry(
        pivot_history, pivot_index=pivot_index,
        left_count=left_count, right_count=right_count,
        previous=previous, breakout=breakout,
        atr_d1_history=atr_d1_history, side=side, tie_policy=tie_policy,
        candidate_epsilon=candidate_epsilon, as_of_utc=as_of_utc,
    )
    if geometry.state is GeometryState.BLOCKED:
        return finish(PhaseEvidenceState.BLOCKED, geometry.reason)
    if geometry.candidate_cross is not True:
        return finish(PhaseEvidenceState.NONCROSS_GEOMETRY_ONLY,
                      "CLOSED_CROSS_GEOMETRY_FALSE_NOT_ZONE_NOT_DETECTED")

    pivot = inspect_causal_pivot(
        pivot_history, candidate_index=pivot_index, left_count=left_count,
        right_count=right_count, side=side, tie_policy=tie_policy,
        as_of_utc=target.market_bar_key.bar_start_utc,
    )
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY or not pivot.geometric_extremum:
        raise PhaseEvidenceDenied("MST_207_PIVOT_CHANGED_BETWEEN_GATES")
    window = pivot_history[
        pivot_index-left_count:pivot_index+right_count+1
    ]
    p_sha = _digest({
        "version": EVENT_VERSION, "kind": "PIVOT_PREVIEW",
        "side": side.value, "tie_policy": tie_policy.value,
        "left_count": left_count, "right_count": right_count,
        "window": [_bar_identity(item) for item in window],
    })
    b_sha = _digest({
        "version": EVENT_VERSION, "kind": "BOS_PREVIEW",
        "rule_version": MANIFESTS[zone_id].rule_version,
        "zone": zone_id, "strategy": strategy.value,
        "variant": variant_id, "phase": phase, "predicate": ref,
        "side": side.value, "pivot_preview_sha": p_sha,
        "previous": _bar_identity(previous),
        "breakout": _bar_identity(breakout),
        "atr_history": [_bar_identity(item) for item in atr_d1_history],
        "candidate_epsilon": str(candidate_epsilon),
        "boundary": str(geometry.boundary),
    })
    return finish(
        PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED,
        "CAUSAL_BOS_GEOMETRY_ATTACHED_BUT_PHASE_SPEC_PENDING",
        "MST_PIVOT_PREVIEW_V1:" + p_sha,
        "MST_BOS_PREVIEW_V1:" + b_sha,
        geometry.witness_known_at_utc,
    )


@dataclass(frozen=True)
class UnverifiedZoneEvidenceRow:
    zone_id: str
    strategy: Strategy
    status: DecisionStatus
    phase: str | None
    preview_id: str | None
    action_eligible: bool = False

    def __post_init__(self) -> None:
        if (self.zone_id not in ZONE_IDS
                or not isinstance(self.strategy, Strategy)
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False
                or (self.preview_id is None) != (self.phase is None)):
            raise PhaseEvidenceDenied("MST_207_ZONE_OVERLAY_PROMOTION")


def project_unverified_16_zone_evidence(
    strategy: Strategy, *, as_of_utc: datetime,
    candidate: PhaseStructureEvidence | None = None,
) -> tuple[UnverifiedZoneEvidenceRow, ...]:
    """16 rows in UI-1.0 zone order, one scoped preview attachment maximum."""
    require_utc(as_of_utc)
    if not isinstance(strategy, Strategy):
        raise PhaseEvidenceDenied("MST_207_STRATEGY_INVALID")
    if candidate is not None and (
        type(candidate) is not PhaseStructureEvidence
        or candidate.strategy is not strategy
        or candidate.as_of_utc != as_of_utc
    ):
        raise PhaseEvidenceDenied("MST_207_CROSS_STRATEGY_OR_CLOCK_OVERLAY")
    decisions = evaluate_unimplemented_zones(strategy, as_of_utc)
    return tuple(
        UnverifiedZoneEvidenceRow(
            d.zone_id, strategy, DecisionStatus.UNVERIFIED,
            candidate.phase if candidate is not None
                               and candidate.zone_id == d.zone_id
                               and candidate.state is PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED
                               else None,
            candidate.bos_preview_id if candidate is not None
                                        and candidate.zone_id == d.zone_id
                                        and candidate.state is PhaseEvidenceState.CROSS_GEOMETRY_UNVERIFIED
                                        else None,
        )
        for d in decisions
    )

# §214 source §24.4 B2.RC.PULLBACK_NEAR_SUPPORT /
# S2.RC.RALLY_NEAR_RESISTANCE: actual causal support/resistance geometry,
# NOT a parameterized/approved detector or a substitute for R0/R_E/R_F.
B2S2_NEAR_SCHEMA_214 = "mst.b2s2.rc.causal_near_geometry.v0.1"
_B2S2_NEAR_VARIANTS_214 = {"B2": ("B2/BASE", StructureSide.LOW),
                             "S2": ("S2/BASE", StructureSide.HIGH)}


class NearEvidenceState214(str, Enum):
    BLOCKED = "BLOCKED"
    CAUSAL_DISTANCE_UNCALIBRATED = "CAUSAL_DISTANCE_UNCALIBRATED"


@dataclass(frozen=True)
class CausalNearEvidence214:
    zone_id: str
    strategy: Strategy
    as_of_utc: datetime
    state: NearEvidenceState214
    reason: str
    distance_atr: Decimal | None
    candidate_k_near: Decimal | None
    candidate_in_band: bool | None
    preview_id: str | None
    schema: str = B2S2_NEAR_SCHEMA_214
    phase: str = "R_C"
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    support_resistance_attested: bool = False
    price_and_atr_independently_attested: bool = False
    parameter_approved: bool = False
    phase_executable: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)
        if (self.zone_id not in _B2S2_NEAR_VARIANTS_214
                or not isinstance(self.strategy, Strategy)
                or not isinstance(self.state, NearEvidenceState214)
                or type(self.reason) is not str or not self.reason
                or self.schema != B2S2_NEAR_SCHEMA_214
                or self.phase != "R_C"
                or self.status is not DecisionStatus.UNVERIFIED
                or self.support_resistance_attested is not False
                or self.price_and_atr_independently_attested is not False
                or self.parameter_approved is not False
                or self.phase_executable is not False
                or self.action_eligible is not False):
            raise PhaseEvidenceDenied("MST_214_UNVERIFIED_NEAR_AUTHORITY_REQUIRED")
        if self.state is NearEvidenceState214.BLOCKED:
            if (self.distance_atr is not None
                    or self.candidate_k_near is not None
                    or self.candidate_in_band is not None
                    or self.preview_id is not None):
                raise PhaseEvidenceDenied("MST_214_BLOCKED_NEAR_OUTPUT_FORBIDDEN")
        elif (type(self.distance_atr) is not Decimal
              or not self.distance_atr.is_finite()
              or self.distance_atr < 0
              or (self.candidate_k_near is not None
                  and (type(self.candidate_k_near) is not Decimal
                       or not self.candidate_k_near.is_finite()
                       or self.candidate_k_near < 0))
              or (self.candidate_k_near is None
                  and self.candidate_in_band is not None)
              or (self.candidate_k_near is not None
                  and type(self.candidate_in_band) is not bool)
              or type(self.preview_id) is not str
              or not self.preview_id.startswith("MST_B2S2_RC_PREVIEW_V1:")
              or len(self.preview_id) != len("MST_B2S2_RC_PREVIEW_V1:") + 64
              or any(x not in "0123456789abcdef"
                     for x in self.preview_id.split(":")[1])):
            raise PhaseEvidenceDenied("MST_214_NEAR_GEOMETRY_INCOMPLETE")


def _near_cross_tf_scope214(bar) -> tuple:
    """Common source/basis scope, excluding legitimately distinct TF streams."""
    k, obs, rev = bar.market_bar_key, bar.observation_key, bar.observation_revision
    return (k.instrument_id, k.exchange, k.instrument_class,
            k.price_basis, k.calendar_version,
            obs.project_id, obs.provider_id, obs.origin,
            rev.adjustment_revision)


def inspect_b2s2_rc_causal_near214(
    *, zone_id: str, strategy: Strategy,
    pullback_m15: ResolvedBarSnapshotV12,
    pivot_history: tuple[ResolvedBarSnapshotV12, ...],
    candidate_index: int, left_count: int, right_count: int,
    tie_policy: TiePolicy,
    atr_d1_history: tuple[ResolvedBarSnapshotV12, ...],
    as_of_utc: datetime,
    candidate_k_near: Decimal | None = None,
) -> CausalNearEvidence214:
    """Execute R_C *distance arithmetic* from validated causal v1.2 bars.

    The pivot must be an eligible historical H1/D1 structural extreme,
    genuinely known before the M15 target START. Wilder ATR14 D1 must also
    be known before that START, with the exact same provider/basis/calendar
    and adjustment revision. No fabricated default k, trend, market regime,
    official exchange-day, position or final R_C detector can be inferred.

    candidate_k_near, when supplied, is an *unapproved what-if parameter*.
    The result is always UNVERIFIED, including when the distance is zero.
    """
    require_utc(as_of_utc)
    if (zone_id not in _B2S2_NEAR_VARIANTS_214
            or not isinstance(strategy, Strategy)):
        raise PhaseEvidenceDenied("MST_214_ZONE_OR_STRATEGY_INVALID")
    if (candidate_k_near is not None
            and (type(candidate_k_near) is not Decimal
                 or not candidate_k_near.is_finite()
                 or candidate_k_near < 0)):
        raise PhaseEvidenceDenied("MST_214_UNAPPROVED_NEAR_K_INVALID")

    def blocked(reason: str) -> CausalNearEvidence214:
        return CausalNearEvidence214(
            zone_id, strategy, as_of_utc,
            NearEvidenceState214.BLOCKED, reason, None, None, None, None,
        )

    target = pullback_m15.selected if isinstance(
        pullback_m15, ResolvedBarSnapshotV12) else None
    if (target is None or target.market_bar_key.timeframe is not Timeframe.M15
            or not pullback_m15.confirmation_prerequisites(as_of_utc)
            or target.bar_end_utc > as_of_utc):
        return blocked("M15_PULLBACK_NOT_CLOSED_AND_QUALIFIED")
    start = target.market_bar_key.bar_start_utc
    if (type(pivot_history) is not tuple or not pivot_history
            or len(pivot_history) > MAX_HISTORY
            or not isinstance(pivot_history[0], ResolvedBarSnapshotV12)
            or pivot_history[0].market_bar_key.timeframe not in (Timeframe.H1, Timeframe.D1)
            or any(not isinstance(row, ResolvedBarSnapshotV12)
                   or row.market_bar_key.timeframe != pivot_history[0].market_bar_key.timeframe
                   for row in pivot_history)):
        return blocked("PIVOT_HISTORY_NOT_H1_OR_D1")
    side = _B2S2_NEAR_VARIANTS_214[zone_id][1]
    # §206 checks all historical rows and right bars; no future pivot use.
    pivot = inspect_causal_pivot(
        pivot_history, candidate_index=candidate_index,
        left_count=left_count, right_count=right_count,
        side=side, tie_policy=tie_policy, as_of_utc=start,
    )
    if pivot.state is not GeometryState.DESCRIPTIVE_ONLY:
        return blocked("PIVOT_" + pivot.reason)
    if pivot.geometric_extremum is not True:
        return blocked("PIVOT_NOT_A_CAUSAL_STRUCTURAL_EXTREME")
    anchor = pivot_history[candidate_index].selected
    if (anchor is None or pivot.witness_known_at_utc > start
            or anchor.bar_end_utc > start
            or _near_cross_tf_scope214(anchor) != _near_cross_tf_scope214(target)):
        return blocked("PIVOT_NOT_IN_TARGET_SOURCE_SCOPE")

    if (type(atr_d1_history) is not tuple
            or not atr_d1_history or len(atr_d1_history) > MAX_HISTORY):
        return blocked("ATR_D1_HISTORY_MISSING_OR_OVERSIZED")
    atr = calculate_wilder_atr14(
        atr_d1_history, as_of_utc=as_of_utc, known_before_utc=start,
    )
    if (atr.state is not IndicatorState.COMPUTED_UNCALIBRATED
            or atr.value is None):
        return blocked("ATR14_" + atr.reason)
    d1 = atr_d1_history[0].selected
    if (d1 is None
            or _near_cross_tf_scope214(d1) != _near_cross_tf_scope214(target)):
        return blocked("ATR14_PROVIDER_BASIS_OR_ADJUSTMENT_MISMATCH")
    candidate_price = target.low if zone_id == "B2" else target.high
    # §24.5 single pivot point treated as a provisional [pivot,pivot] band.
    # Full approved price/zone band policy and k calibration are still open.
    arithmetic = inspect_near_zone_arithmetic(
        price=candidate_price, zone_lower=pivot.pivot_price,
        zone_upper=pivot.pivot_price, atr_d1=atr.value,
        candidate_k_near=candidate_k_near,
    )
    digest = _digest({
        "schema": B2S2_NEAR_SCHEMA_214, "zone": zone_id,
        "strategy": strategy.value,
        "side": side.value, "tie_policy": tie_policy.value,
        "pivot_left": left_count, "pivot_right": right_count,
        "pivot_index": candidate_index,
        "pivot_history": [_bar_identity(row) for row in pivot_history],
        "target": _bar_identity(pullback_m15),
        "atr_history": [_bar_identity(row) for row in atr_d1_history],
        "candidate_k": str(candidate_k_near),
        "normalized_distance": str(arithmetic.normalized_by_atr),
    })
    return CausalNearEvidence214(
        zone_id, strategy, as_of_utc,
        NearEvidenceState214.CAUSAL_DISTANCE_UNCALIBRATED,
        "R_C_NORMALIZED_DISTANCE_ONLY_K_AND_CONTEXT_NOT_APPROVED",
        arithmetic.normalized_by_atr, candidate_k_near,
        arithmetic.in_candidate_band,
        "MST_B2S2_RC_PREVIEW_V1:" + digest,
    )


def inspect_routed_phase_bos(
    inputs: BaselineResolvedInputs, *, zone_id: str, strategy: Strategy,
    variant_id: str, phase: str, timeframe: Timeframe,
    breakout_index: int, pivot_index: int, left_count: int, right_count: int,
    atr_start: int, atr_stop: int, tie_policy: TiePolicy,
    candidate_epsilon: Decimal | None,
):
    """Execute the existing structural ingredient on the exact input partition.

    Only index-based contiguous slices are accepted, never external candles or
    a separate decision clock. ATR slice bounds are explicit unapproved
    research configuration, not an approved history/continuity policy.
    Missing phase dependencies remain visible separately from the ingredient.
    """
    if type(inputs) is not BaselineResolvedInputs:
        raise PhaseEvidenceDenied("MST_370_REQUIRE_BASELINE_INPUTS")
    route = ROUTES.get((zone_id, variant_id, phase))
    if (route is None or type(timeframe) is not Timeframe
            or timeframe not in route[1]):
        raise PhaseEvidenceDenied("MST_370_EXPLICIT_STRUCTURAL_ROUTE")
    scope = dict(zone_id=zone_id, strategy=strategy, variant_id=variant_id, phase=phase)
    routed = route_phase_inputs(inputs, **scope)
    if timeframe in routed.choice_frames:
        routed = route_phase_inputs(inputs, selected_frame=timeframe, **scope)
    if any(type(i) is not int or i < 0 for i in (
            breakout_index, pivot_index, left_count, right_count, atr_start, atr_stop)):
        raise PhaseEvidenceDenied("MST_370_INVALID_INDEX")
    if (breakout_index < 2 or min(left_count, right_count) < 1
            or atr_start >= atr_stop or pivot_index < left_count
            or pivot_index + right_count >= breakout_index - 1):
        raise PhaseEvidenceDenied("MST_370_INVALID_SLICE_GEOMETRY")
    bars = inputs.snapshots_for(timeframe)
    atr = inputs.snapshots_for(Timeframe.D1)
    if not bars or not atr:
        evidence = PhaseStructureEvidence(
            zone_id, strategy, variant_id, phase, routed.predicate_ref,
            route[0], timeframe, inputs.as_of_utc, PhaseEvidenceState.BLOCKED,
            "MST_370_STRUCTURAL_OR_ATR_INPUT_MISSING",
        )
        return routed, evidence
    if breakout_index >= len(bars) or atr_stop > len(atr):
        raise PhaseEvidenceDenied("MST_370_INDEX_OUTSIDE_INPUT_SCOPE")
    # Keep every row in the selected prefix. An unresolved or conflicting
    # row cannot be removed or substituted by a newer/other-source row.
    evidence = inspect_phase_bos_evidence(
        **scope, pivot_history=bars[:breakout_index - 1],
        pivot_index=pivot_index, left_count=left_count, right_count=right_count,
        previous=bars[breakout_index - 1], breakout=bars[breakout_index],
        atr_d1_history=atr[atr_start:atr_stop], tie_policy=tie_policy,
        candidate_epsilon=candidate_epsilon, as_of_utc=inputs.as_of_utc,
    )
    return routed, evidence
