"""M4 candidate Google Drive cache *identity/refresh planner* — no I/O.

All paths are TEST-ONLY proposals; no Google Drive files are read or written,
no licensed bars are retained, no provider head is authenticated, and no plan
grants data-source or trading rights. A source change cannot be inferred from
a local five-minute timer or a caller-supplied digest.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
import re

from .replay import require_utc
from .v2_source_adapter import FixtureSourceIdentityV2

_SYMBOL = re.compile(r"^[A-Z0-9-]{1,16}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_TIMEFRAME = frozenset(("M5", "M15", "M30", "H1", "H4", "D1"))
_VERSION = "mst.cache.partition.v2.test_only"
_CADENCE = timedelta(minutes=5)


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("Typed UTC time required")
    return require_utc(value)


@dataclass(frozen=True)
class FixturePartitionV2:
    """Explicit project/source/endpoint/instrument/timeframe/basis separation."""

    provider_id: str
    endpoint_id: str
    symbol: str
    timeframe: str
    session_date_local: date
    price_basis: str
    source_revision_namespace: str

    def __post_init__(self) -> None:
        FixtureSourceIdentityV2(self.provider_id, self.endpoint_id)
        if type(self.symbol) is not str or not _SYMBOL.fullmatch(self.symbol):
            raise ValueError("Normalized ticker required")
        if type(self.timeframe) is not str or self.timeframe not in _TIMEFRAME:
            raise ValueError("Explicit supported timeframe required")
        if type(self.session_date_local) is not date:
            raise TypeError("Session must be an explicit date, not timestamp")
        if type(self.price_basis) is not str or self.price_basis not in ("RAW", "ADJUSTED"):
            raise ValueError("RAW and ADJUSTED source basis cannot mix")
        if (type(self.source_revision_namespace) is not str
                or not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,63}", self.source_revision_namespace)):
            raise ValueError("Explicit opaque provider revision namespace required")

    @property
    def digest(self) -> str:
        payload = {
            "schema": _VERSION,
            "project": "MST",
            "provider_id": self.provider_id,
            "endpoint_id": self.endpoint_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "session_date_local": self.session_date_local.isoformat(),
            "price_basis": self.price_basis,
            "source_revision_namespace": self.source_revision_namespace,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("ascii")).hexdigest()

    @property
    def proposed_drive_key(self) -> str:
        """Plan only, NEVER an existing Drive file or permission grant."""
        return (
            f"MST_V2_TEST_ONLY/{self.provider_id}/{self.endpoint_id}/"
            f"{self.symbol}/{self.timeframe}/{self.session_date_local.isoformat()}/"
            f"{self.price_basis}/{self.digest}.manifest.json"
        )


@dataclass(frozen=True)
class FixtureHeadV2:
    """Untrusted offline metadata, NOT an authenticated market-data head."""

    partition_digest: str
    generation: int
    content_digest: str
    last_checked_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.partition_digest) is not str or not _DIGEST.fullmatch(self.partition_digest):
            raise ValueError("Partition SHA256 required")
        if type(self.content_digest) is not str or not _DIGEST.fullmatch(self.content_digest):
            raise ValueError("Content SHA256 required")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("Nonnegative generation required")
        _utc(self.last_checked_at_utc)


class CandidateRefreshHint(str, Enum):
    EMPTY_PARTITION = "EMPTY_PARTITION"
    RECENT_METADATA = "RECENT_METADATA"
    NEEDS_PROVIDER_REVALIDATION = "NEEDS_PROVIDER_REVALIDATION"


@dataclass(frozen=True)
class FixtureRefreshPlanV2:
    partition_digest: str
    hint: CandidateRefreshHint
    checked_at_utc: datetime

    @property
    def can_fetch_market_data(self) -> bool:
        return False

    @property
    def can_read_licensed_cache(self) -> bool:
        return False

    @property
    def can_write_drive(self) -> bool:
        return False

    @property
    def source_freshness_verified(self) -> bool:
        return False

    @property
    def permission_to_trade(self) -> bool:
        return False


def plan_fixture_refresh(
    partition: FixturePartitionV2,
    prior_head: FixtureHeadV2 | None,
    *,
    checked_at_utc: datetime,
) -> FixtureRefreshPlanV2:
    """Pure five-minute planning hint, no licensed data pull/cache mutation."""
    if type(partition) is not FixturePartitionV2:
        raise TypeError("FixturePartitionV2 required")
    now = _utc(checked_at_utc)
    digest = partition.digest
    if prior_head is None:
        hint = CandidateRefreshHint.EMPTY_PARTITION
    else:
        if type(prior_head) is not FixtureHeadV2:
            raise TypeError("FixtureHeadV2 or None required")
        if prior_head.partition_digest != digest:
            raise ValueError("CROSS_PARTITION_HEAD_REUSE_DENIED")
        if prior_head.last_checked_at_utc > now:
            raise ValueError("FUTURE_HEAD_CANNOT_REWIND_CLOCK")
        if now - prior_head.last_checked_at_utc < _CADENCE:
            hint = CandidateRefreshHint.RECENT_METADATA
        else:
            hint = CandidateRefreshHint.NEEDS_PROVIDER_REVALIDATION
    return FixtureRefreshPlanV2(digest, hint, now)
