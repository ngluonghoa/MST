"""M3 candidate provider admission checklist — NEVER an MCP authorization.

All evidence is opaque, unverified and metadata-only. This module does NOT
validate vendor licences, account ownership, credentials, signatures, actual
endpoints or permitted retention. A complete claim checklist is still DENIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re

from .replay import require_utc
from .v2_source_adapter import FixtureSourceIdentityV2

_DOCKET = re.compile(r"^EVID-[A-Z0-9]{8,32}$")


def _checked_utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("UTC datetime required")
    return require_utc(value)


class ProviderGate(str, Enum):
    INDEPENDENT_VENDOR_IDENTITY = "INDEPENDENT_VENDOR_IDENTITY"
    ACCOUNT_ENTITLEMENT = "ACCOUNT_ENTITLEMENT"
    ENDPOINT_AND_RATE_SCOPE = "ENDPOINT_AND_RATE_SCOPE"
    READ_HISTORICAL_RIGHTS = "READ_HISTORICAL_RIGHTS"
    CLOUD_RETENTION_RIGHTS = "CLOUD_RETENTION_RIGHTS"
    DERIVED_INDICATOR_RIGHTS = "DERIVED_INDICATOR_RIGHTS"
    RESEARCH_BACKTEST_RIGHTS = "RESEARCH_BACKTEST_RIGHTS"
    AUTHENTICATED_CLOUD_IDENTITY = "AUTHENTICATED_CLOUD_IDENTITY"
    SOURCE_TIME_REVISION_PROVENANCE = "SOURCE_TIME_REVISION_PROVENANCE"
    REVOCATION_AND_INCIDENT_ROLLBACK = "REVOCATION_AND_INCIDENT_ROLLBACK"


class ClaimState(str, Enum):
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class UnverifiedGateNoteV2:
    """Opaque docket reference, never an attached licence or secret."""

    provider_id: str
    endpoint_id: str
    gate: ProviderGate
    state: ClaimState
    observed_at_utc: datetime
    evidence_ref: str | None = None
    claimed_expires_utc: datetime | None = None

    def __post_init__(self) -> None:
        FixtureSourceIdentityV2(self.provider_id, self.endpoint_id)
        if type(self.gate) is not ProviderGate or type(self.state) is not ClaimState:
            raise TypeError("Exact gate/state enums required")
        _checked_utc(self.observed_at_utc)
        if self.state is ClaimState.MISSING:
            if self.evidence_ref is not None or self.claimed_expires_utc is not None:
                raise ValueError("Missing claim must not carry evidence")
        elif type(self.evidence_ref) is not str or not _DOCKET.fullmatch(self.evidence_ref):
            raise ValueError("Only an opaque EVID docket identifier is permitted")
        if self.claimed_expires_utc is not None:
            _checked_utc(self.claimed_expires_utc)
            if self.claimed_expires_utc <= self.observed_at_utc:
                raise ValueError("Claims with invalid expiry timeline are rejected")


@dataclass(frozen=True)
class ProviderReadinessV2:
    provider_id: str
    endpoint_id: str
    checked_at_utc: datetime
    gates_present: tuple[ProviderGate, ...]
    missing_gates: tuple[ProviderGate, ...]
    unverified_gates: tuple[ProviderGate, ...]
    expired_or_revoked_gates: tuple[ProviderGate, ...]

    def __post_init__(self) -> None:
        # A caller cannot construct a summary with all requirements omitted.
        # This remains a report of unverified CLAIMS, never vendor approval.
        FixtureSourceIdentityV2(self.provider_id, self.endpoint_id)
        _checked_utc(self.checked_at_utc)
        groups = (
            self.gates_present, self.missing_gates,
            self.unverified_gates, self.expired_or_revoked_gates,
        )
        for group in groups:
            if type(group) is not tuple or any(type(item) is not ProviderGate for item in group):
                raise TypeError("Exact immutable ProviderGate tuple required")
            if len(set(group)) != len(group):
                raise ValueError("Duplicate gate in review output")
        present, missing, unverified, revoked = map(set, groups)
        if (unverified & missing or revoked & missing or revoked & unverified
                or present - set(ProviderGate)
                or not (unverified | revoked) <= present
                or missing | unverified | revoked != set(ProviderGate)):
            raise ValueError("Incomplete or contradictory provider readiness summary")

    @property
    def external_vendor_verification(self) -> bool:
        return False

    @property
    def live_transport_authorized(self) -> bool:
        return False

    @property
    def cloud_retention_authorized(self) -> bool:
        return False

    @property
    def backtest_authorized(self) -> bool:
        return False

    @property
    def trading_authorized(self) -> bool:
        return False


def review_unverified_provider_docket(
    identity: FixtureSourceIdentityV2,
    notes: tuple[UnverifiedGateNoteV2, ...],
    *,
    checked_at_utc: datetime,
) -> ProviderReadinessV2:
    """Find missing/expired/revoked claims; NEVER approve a real provider."""
    if type(identity) is not FixtureSourceIdentityV2:
        raise TypeError("Explicit fixture provider identity required")
    if type(notes) is not tuple or any(type(n) is not UnverifiedGateNoteV2 for n in notes):
        raise TypeError("Immutable tuple of typed notes required")
    _checked_utc(checked_at_utc)
    seen = {}
    refs = set()
    for note in notes:
        if (note.provider_id != identity.provider_id
                or note.endpoint_id != identity.endpoint_id):
            raise ValueError("CROSS_PROVIDER_OR_ENDPOINT_EVIDENCE_DENIED")
        if note.gate in seen:
            raise ValueError("Duplicate requirement in docket")
        if note.observed_at_utc > checked_at_utc:
            raise ValueError("Future-dated unverified claim rejected")
        if note.evidence_ref is not None:
            if note.evidence_ref in refs:
                raise ValueError("Reused evidence docket reference")
            refs.add(note.evidence_ref)
        seen[note.gate] = note
    missing = tuple(g for g in ProviderGate
                    if g not in seen or seen[g].state is ClaimState.MISSING)
    revoked = tuple(g for g in ProviderGate
                    if g in seen and (
                        seen[g].state is ClaimState.REVOKED
                        or (seen[g].claimed_expires_utc is not None
                            and seen[g].claimed_expires_utc <= checked_at_utc)
                    ))
    unverified = tuple(g for g in ProviderGate
                       if g in seen and seen[g].state is ClaimState.UNVERIFIED
                       and g not in revoked)
    return ProviderReadinessV2(
        identity.provider_id, identity.endpoint_id, checked_at_utc,
        tuple(g for g in ProviderGate if g in seen),
        missing, unverified, revoked,
    )
