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
from .contracts import DecisionStatus, Strategy, ZONE_IDS
from .engine import evaluate_unimplemented_zones
from .market_data import Timeframe
from .replay import require_utc
from .source_quality import ResolvedBarSnapshotV12
from .zone_manifest_v03 import MANIFESTS

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
