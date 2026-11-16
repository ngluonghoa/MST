"""Fail-closed initial signal engine. All real detector formulas remain SPEC_PENDING."""
from datetime import datetime

from .contracts import SignalDecision, DecisionStatus, Strategy, ZONE_IDS
from .zone_manifest_v03 import MANIFESTS, EXECUTION_STATUS
from .replay import require_utc


def evaluate_unimplemented_zones(strategy: Strategy, as_of_utc: datetime) -> tuple[SignalDecision, ...]:
    """Never emit NOT_DETECTED or DETECTED for an unimplemented zone."""
    require_utc(as_of_utc)
    # A manifest ID is now required for every original zone, but these are
    # pre-code predicate identifiers, NOT formulas or confirmed detection.
    # Never let the presence of a manifest promote a signal.
    if tuple(MANIFESTS) != ZONE_IDS or EXECUTION_STATUS != "SPEC_PENDING_FORMULAS_AND_FIXTURES":
        raise RuntimeError("MST_SOURCE_MANIFEST_ENGINE_DRIFT")
    return tuple(
        SignalDecision(zone_id=zone, strategy=strategy, status=DecisionStatus.UNVERIFIED)
        for zone in MANIFESTS
    )
