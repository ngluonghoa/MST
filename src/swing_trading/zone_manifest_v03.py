"""§205 locked Swing 1.8 §24.4 16-zone phase manifest + §24.5 NEAR arithmetic.

Source-of-truth: SOURCE_LOCKED_01_MASTER_SPEC (MST baseline 2026-11-08),
source-locked swing-trading-1-8 commit cd90c1babae8912db31490ad614fc2ad2f868042.
Do not infer detector logic/thresholds from ID tokens. The upstream spec says
all 16 zone phase predicates remain SPEC_PENDING_FORMULAS_AND_FIXTURES,
parameter family PARAM_CANDIDATE_NOT_APPROVED, and action is blocked.

Pure, offline, read-only metadata and Decimal geometry only: no API, storage,
broker, simulated trading, historical-data qualification or report publisher.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any

from .contracts import DecisionStatus, Strategy, ZONE_IDS

SPEC_REVISION = "SwingTrading18/01_MASTER_SPEC/24.4/v0.3"
NEAR_SPEC_REVISION = "SwingTrading18/01_MASTER_SPEC/24.5/NEAR/v0.3"
PHASES = ("R0", "R_C", "R_E", "R_F")
PARAM_STATUS = "PARAM_CANDIDATE_NOT_APPROVED"
EXECUTION_STATUS = "SPEC_PENDING_FORMULAS_AND_FIXTURES"
BUY_POLICY = "BUY_ACTION_REQUIRES_STRATEGY_RISK_APPROVAL"
SELL_POLICY = "SELL_ACTION_ONLY_WITH_OPEN_VERIFIED_POSITION"

# Exactly the §24.4 branch IDs and phase-predicate refs, in the locked
# original order. Semicolons in the document delimit phase-specific variants:
# they are separate explicit IDs, not implied fallback alternatives.
_ROWS = (
    ("B1", ("B1/E_RECLAIM", "B1/E_BOS_UP", "B1/F_MAJOR_REVERSAL_PENDING"),
     ("B1.R0.DECLINE_CONTEXT", "B1.RC.SUPPORT_TEST",
      "B1.RE.RECLAIM_OR_BOS_UP", "B1.RF.D1_BOS_HL_VOLUME")),
    ("B2", ("B2/BASE",),
     ("B2.R0.D1_UPTREND_SUPPORT", "B2.RC.PULLBACK_NEAR_SUPPORT",
      "B2.RE.M15_HL_RECLAIM", "B2.RF.MICRO_PIVOT_BREAK")),
    ("B3", ("B3/E_FALSE_BREAK", "B3/E_BOS_UP"),
     ("B3.R0.CAUSAL_RANGE", "B3.RC.NEAR_LOWER_BOUNDARY",
      "B3.RE.FALSE_BREAK_RECLAIM_OR_BOS", "B3.RF.H1_D1_RECLAIM")),
    ("B4", ("B4/BASE",),
     ("B4.R0.CAUSAL_BULLISH_TRANSITION", "B4.RC.FIRST_POST_EVENT_PULLBACK",
      "B4.RE.M15_HL_RECLAIM", "B4.RF.FIRST_HL_MICRO_BREAK")),
    ("B5", ("B5/E_RECLAIM", "B5/E_FAILED_BREAK"),
     ("B5.R0.PRIOR_BREAKOUT_EVENT", "B5.RC.EXACT_PIVOT_RETEST",
      "B5.RE.M15_RECLAIM_OR_FAILED_BREAK", "B5.RF.RETEST_SUPPORT_BREAK")),
    ("B6", ("B6/C_TWO_CONTRACTIONS", "B6/C_COMPRESSION"),
     ("B6.R0.UPTREND_OR_BASE", "B6.RC.TWO_CONTRACTIONS_OR_COMPRESSION",
      "B6.RE.M15_UPPER_PIVOT_APPROACH", "B6.RF.HIGHER_TF_BREAKOUT_VOLUME")),
    ("B7", ("B7/E_RECLAIM", "B7/E_CHOCH"),
     ("B7.R0.D1_DOWNTREND_CONTEXT", "B7.RC.SUPPORT_ATR_STRETCH",
      "B7.RE.M15_RECLAIM_OR_CHOCH", "B7.RF.MICRO_HIGH_BREAK_RISK")),
    ("B8", ("B8/BASE", "B8/INTRADAY_RVOL_TOD_PENDING"),
     ("B8.R0.BASE_RESISTANCE_RS", "B8.RC.NEAR_PIVOT",
      "B8.RE.M15_PIVOT_CROSS", "B8.RF.HIGHER_TF_BREAKOUT_RS_VOLUME")),
    ("S1", ("S1/E_FAILED_BREAK", "S1/E_CHOCH_DOWN", "S1/F_MAJOR_CYCLE_TOP_PENDING"),
     ("S1.R0.LONG_UPTREND_RESISTANCE", "S1.RC.DISTRIBUTION_CONTEXT",
      "S1.RE.FAILED_BREAK_OR_CHOCH_DOWN", "S1.RF.D1_BOS_DOWN_VOLUME")),
    ("S2", ("S2/BASE",),
     ("S2.R0.D1_DOWNTREND_RESISTANCE", "S2.RC.RALLY_NEAR_RESISTANCE",
      "S2.RE.M15_REJECTION_LH", "S2.RF.MICRO_LOW_BREAK")),
    ("S3", ("S3/E_MICRO_CHOCH", "S3/E_TP", "S3/F_MICRO_BREAK", "S3/F_TP"),
     ("S3.R0.D1_UPTREND_RESISTANCE_OR_TP", "S3.RC.NEAR_TARGET_EXTENSION",
      "S3.RE.MICRO_CHOCH_OR_TP", "S3.RF.MICRO_BREAK_OR_VERIFIED_TP")),
    ("S4", ("S4/E_FALSE_BREAK", "S4/E_BOS_DOWN"),
     ("S4.R0.CAUSAL_D1_RANGE", "S4.RC.UPPER_BOUNDARY_REJECTION",
      "S4.RE.FALSE_BREAK_OR_BOS_DOWN", "S4.RF.D1_H1_RANGE_REENTRY")),
    ("S5", ("S5/BASE",),
     ("S5.R0.PRIOR_BEARISH_TRANSITION", "S5.RC.FIRST_FAILED_RALLY",
      "S5.RE.M15_LH_REJECTION", "S5.RF.FIRST_LH_LOW_BREAK")),
    ("S6", ("S6/BASE",),
     ("S6.R0.PRIOR_BREAKOUT_EVENT", "S6.RC.BREAKOUT_FAILURE_WINDOW",
      "S6.RE.M15_CLOSE_BELOW_PIVOT", "S6.RF.H1_D1_PIVOT_FAILURE")),
    ("S7", ("S7/F_MICRO_BREAK", "S7/F_CONTINUATION"),
     ("S7.R0.PRIOR_BREAKDOWN_EVENT", "S7.RC.SUPPORT_RETEST_FROM_BELOW",
      "S7.RE.M15_FAILED_RECLAIM", "S7.RF.H1_D1_CONTINUATION")),
    ("S8", ("S8/BASE",),
     ("S8.R0.CAUSAL_RETURN_VOL_PERCENTILES", "S8.RC.ACCELERATION_EXHAUSTION",
      "S8.RE.M15_MICRO_REVERSAL", "S8.RF.HIGHER_TF_REVERSAL_VOLUME")),
)


class ZoneManifestDenied(ValueError):
    """Fixed failure codes, no market input, credentials or source rows."""


@dataclass(frozen=True)
class SourceLockedZoneManifest:
    zone_id: str
    rule_version: str
    variants: tuple[str, ...]
    phase_predicates: tuple[str, ...]
    strategy_action_policy: str
    evaluation_strategies: tuple[Strategy, Strategy] = (
        Strategy.SHORT, Strategy.SWING
    )
    spec_revision: str = SPEC_REVISION
    parameter_status: str = PARAM_STATUS
    predicate_executable_status: str = EXECUTION_STATUS
    eligible_for_confirmed_action: bool = False

    def __post_init__(self) -> None:
        if (self.zone_id not in ZONE_IDS
                or self.rule_version != self.zone_id + "/PRECODE_v0.3"
                or not self.variants
                or len(set(self.variants)) != len(self.variants)
                or any(not isinstance(v, str)
                       or not v.startswith(self.zone_id + "/")
                       for v in self.variants)
                or len(self.phase_predicates) != 4
                or len(set(self.phase_predicates)) != 4
                or any(not isinstance(v, str)
                       or not v.startswith(self.zone_id + ".")
                       for v in self.phase_predicates)
                or self.strategy_action_policy != (
                    BUY_POLICY if self.zone_id.startswith("B") else SELL_POLICY
                )
                or self.evaluation_strategies
                   != (Strategy.SHORT, Strategy.SWING)
                or self.spec_revision != SPEC_REVISION
                or self.parameter_status != PARAM_STATUS
                or self.predicate_executable_status != EXECUTION_STATUS
                or self.eligible_for_confirmed_action is not False):
            raise ZoneManifestDenied("MST_205_MANIFEST_NOT_SOURCE_LOCKED")

    def predicate_for(self, phase: str) -> str:
        if type(phase) is not str or phase not in PHASES:
            raise ZoneManifestDenied("MST_205_UNKNOWN_PHASE")
        return self.phase_predicates[PHASES.index(phase)]


MANIFESTS = MappingProxyType({
    z: SourceLockedZoneManifest(z, z + "/PRECODE_v0.3", v, p,
                                BUY_POLICY if z.startswith("B") else SELL_POLICY)
    for z, v, p in _ROWS
})
if tuple(MANIFESTS) != ZONE_IDS or len(MANIFESTS) != 16:
    raise RuntimeError("MST_205_MANIFEST_COVERAGE_DRIFT")


@dataclass(frozen=True)
class UnverifiedPhaseReadiness:
    zone_id: str
    strategy: Strategy
    variant_id: str
    phase: str
    predicate_ref: str
    reason: str = "SPEC_PENDING_FORMULAS_AND_FIXTURES"
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    executable: bool = False
    action_eligible: bool = False

    def __post_init__(self) -> None:
        m = MANIFESTS.get(self.zone_id)
        if (m is None or not isinstance(self.strategy, Strategy)
                or self.variant_id not in m.variants
                or self.phase not in PHASES
                or self.predicate_ref != m.predicate_for(self.phase)
                or self.reason != EXECUTION_STATUS
                or self.status is not DecisionStatus.UNVERIFIED
                or self.executable is not False
                or self.action_eligible is not False):
            raise ZoneManifestDenied("MST_205_PHASE_AUTHORITY_FORBIDDEN")


def inspect_phase(zone_id: str, *, strategy: Strategy, variant_id: str,
                  phase: str) -> UnverifiedPhaseReadiness:
    if type(zone_id) is not str or zone_id not in MANIFESTS:
        raise ZoneManifestDenied("MST_205_ZONE_INVALID")
    m = MANIFESTS[zone_id]
    if not isinstance(strategy, Strategy):
        raise ZoneManifestDenied("MST_205_STRATEGY_INVALID")
    if type(variant_id) is not str or variant_id not in m.variants:
        raise ZoneManifestDenied("MST_205_VARIANT_INVALID")
    if type(phase) is not str or phase not in PHASES:
        raise ZoneManifestDenied("MST_205_PHASE_INVALID")
    return UnverifiedPhaseReadiness(
        zone_id, strategy, variant_id, phase, m.predicate_for(phase)
    )


@dataclass(frozen=True)
class NearArithmeticPreview:
    """Normative §24.5 zone distance, never market-source qualified.

    Values are caller-supplied Decimal geometry, not trusted prices/ATR.
    k_near=None means no candidate threshold and UNKNOWN, not NOT_DETECTED.
    A candidate threshold does not authorize detection or trading.
    """
    distance: Decimal
    normalized_by_atr: Decimal
    candidate_threshold_distance: Decimal | None
    in_candidate_band: bool | None
    specification: str = NEAR_SPEC_REVISION
    source_qualified: bool = False
    parameter_calibrated: bool = False
    status: DecisionStatus = DecisionStatus.UNVERIFIED
    action_eligible: bool = False

    def __post_init__(self) -> None:
        for number in (self.distance, self.normalized_by_atr):
            if type(number) is not Decimal or not number.is_finite() or number < 0:
                raise ZoneManifestDenied("MST_205_NEAR_RESULT_INVALID")
        if (self.candidate_threshold_distance is None) != (self.in_candidate_band is None):
            raise ZoneManifestDenied("MST_205_NEAR_CANDIDATE_INCOMPLETE")
        if self.candidate_threshold_distance is not None and (
            type(self.candidate_threshold_distance) is not Decimal
            or not self.candidate_threshold_distance.is_finite()
            or self.candidate_threshold_distance < 0
        ):
            raise ZoneManifestDenied("MST_205_NEAR_RESULT_INVALID")
        if (self.specification != NEAR_SPEC_REVISION
                or self.source_qualified is not False
                or self.parameter_calibrated is not False
                or self.status is not DecisionStatus.UNVERIFIED
                or self.action_eligible is not False):
            raise ZoneManifestDenied("MST_205_NEAR_AUTHORITY_FORBIDDEN")


def inspect_near_zone_arithmetic(
    *, price: Any, zone_lower: Any, zone_upper: Any,
    atr_d1: Any, candidate_k_near: Any = None,
) -> NearArithmeticPreview:
    """Exact §24.5: distance=max(L-p,0,p-H), NEAR <= k*verified ATR.

    This function performs the *arithmetic* only. There is no source/clock,
    ATR14 warm-up, time, tick/price-basis or calibrated-k proof here.
    k=0 is a valid candidate boundary (not an approved trading threshold).
    """
    entries = (price, zone_lower, zone_upper, atr_d1)
    if (any(type(x) is not Decimal or not x.is_finite() for x in entries)
            or price < 0 or zone_lower < 0 or zone_upper < zone_lower
            or atr_d1 <= 0):
        raise ZoneManifestDenied("MST_205_NEAR_INPUT_UNVERIFIED")
    if candidate_k_near is not None and (
        type(candidate_k_near) is not Decimal
        or not candidate_k_near.is_finite()
        or candidate_k_near < 0
    ):
        raise ZoneManifestDenied("MST_205_NEAR_CANDIDATE_K_INVALID")
    distance = max(zone_lower - price, Decimal(0), price - zone_upper)
    threshold = (candidate_k_near * atr_d1
                 if candidate_k_near is not None else None)
    return NearArithmeticPreview(
        distance=distance,
        normalized_by_atr=distance / atr_d1,
        candidate_threshold_distance=threshold,
        in_candidate_band=(distance <= threshold
                           if threshold is not None else None),
    )


def source_registry_fingerprint() -> str:
    """Stable source-ID registry digest, not a proof of source approval."""
    document = {
        "spec_revision": SPEC_REVISION,
        "zones": [{
            "zone": m.zone_id, "version": m.rule_version,
            "variants": list(m.variants),
            "predicates": list(m.phase_predicates),
            "action": m.strategy_action_policy,
            "parameter": m.parameter_status, "execution": m.predicate_executable_status,
        } for m in MANIFESTS.values()],
    }
    return sha256(json.dumps(document, sort_keys=True,
                             ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
