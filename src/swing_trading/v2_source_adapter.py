"""MST opt-in v2 source *fixture* adapter registry; no connector or network I/O.

SSI / DNSE / VCBS names and future provider identifiers are namespace labels
only. No callback, credentials, source payload, licence, OHLCV, retention,
backtest qualification, broker execution, or live provider fallback exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from .engineering_contracts import PortDescriptor, require_compatible_port
from .replay import require_utc

_PROVIDER = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_ENDPOINT = re.compile(r"^[a-z][a-z0-9_.-]{0,79}$")
_SYMBOL = re.compile(r"^[A-Z0-9-]{1,16}$")
_TIMEFRAMES = frozenset(("M5", "M15", "M30", "H1", "H4", "D1"))
_V2_CONTRACT = "source.fixture_probe"
_SCOPE = "SYNTHETIC_TEST_ONLY"
_STARTING_PROVIDERS = ("SSI", "DNSE", "VCBS")


def _provider_id(value: str) -> str:
    if type(value) is not str or not _PROVIDER.fullmatch(value):
        raise ValueError("Exact uppercase provider namespace required")
    return value


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime:
        raise TypeError("Typed UTC timestamp required")
    return require_utc(value)


def _required_v2_port(provider: str) -> PortDescriptor:
    return PortDescriptor(_V2_CONTRACT, "2.0.0", provider, ("probe",))


@dataclass(frozen=True)
class FixtureSourceIdentityV2:
    """An explicit synthetic namespace; never a provider entitlement."""

    provider_id: str
    endpoint_id: str
    version: str = "2.0.0"

    def __post_init__(self) -> None:
        _provider_id(self.provider_id)
        if type(self.endpoint_id) is not str or not _ENDPOINT.fullmatch(self.endpoint_id):
            raise ValueError("Explicit nonsecret fixture endpoint required")
        PortDescriptor(_V2_CONTRACT, self.version, self.provider_id, ("probe",))


@dataclass(frozen=True)
class FixtureProbeRequestV2:
    """Pure metadata, with no actual market observation or credential."""

    provider_id: str
    endpoint_id: str
    symbol: str
    timeframe: str
    as_of_utc: datetime

    def __post_init__(self) -> None:
        _provider_id(self.provider_id)
        if type(self.endpoint_id) is not str or not _ENDPOINT.fullmatch(self.endpoint_id):
            raise ValueError("Invalid endpoint identity")
        if type(self.symbol) is not str or not _SYMBOL.fullmatch(self.symbol):
            raise ValueError("Synthetic ticker must be normalized")
        if type(self.timeframe) is not str or self.timeframe not in _TIMEFRAMES:
            raise ValueError("Unsupported fixture timeframe")
        _utc(self.as_of_utc)


@dataclass(frozen=True)
class FixtureProbeReceiptV2:
    """Unverified audit metadata only, never a source-authority receipt."""

    provider_id: str
    endpoint_id: str
    symbol: str
    timeframe: str
    as_of_utc: datetime
    state: str = "UNVERIFIED"
    source_authorized: bool = False
    retention_authorized: bool = False
    trading_authorized: bool = False

    def __post_init__(self) -> None:
        FixtureProbeRequestV2(
            self.provider_id, self.endpoint_id, self.symbol,
            self.timeframe, self.as_of_utc,
        )
        if self.state != "UNVERIFIED":
            raise PermissionError("Fixture cannot certify live source state")
        if (self.source_authorized is not False
                or self.retention_authorized is not False
                or self.trading_authorized is not False):
            raise PermissionError("Metadata fixture cannot self-grant rights")


@dataclass(frozen=True)
class FixtureSourceAdapterV2:
    """No injected callbacks: a deterministic read-only metadata fixture."""

    identity: FixtureSourceIdentityV2

    def __post_init__(self) -> None:
        if type(self.identity) is not FixtureSourceIdentityV2:
            raise TypeError("Exact fixture identity required")

    @property
    def descriptor(self) -> PortDescriptor:
        return PortDescriptor(
            _V2_CONTRACT, self.identity.version, self.identity.provider_id,
            ("probe",),
        )

    def probe(self, request: FixtureProbeRequestV2) -> FixtureProbeReceiptV2:
        if type(request) is not FixtureProbeRequestV2:
            raise TypeError("Typed metadata request required")
        if request.provider_id != self.identity.provider_id:
            raise ValueError("PROVIDER_ISOLATION_NO_IMPLICIT_FALLBACK")
        if request.endpoint_id != self.identity.endpoint_id:
            raise ValueError("ENDPOINT_ISOLATION_NO_IMPLICIT_FALLBACK")
        return FixtureProbeReceiptV2(
            request.provider_id, request.endpoint_id, request.symbol,
            request.timeframe, request.as_of_utc,
        )


class FixtureSourceRegistryV2:
    """Cloud-independent pure-memory lab registry, not a live adapter broker.

    Register/replace/remove are explicit per provider; consumers may pin a
    minimum source contract version. Replacement validates before mutation.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, FixtureSourceAdapterV2] = {}
        self._pins: dict[str, tuple[str, PortDescriptor]] = {}

    def register(self, adapter: FixtureSourceAdapterV2) -> None:
        if type(adapter) is not FixtureSourceAdapterV2:
            raise TypeError("Explicit fixture adapter type required")
        key = adapter.identity.provider_id
        if key in self._adapters:
            raise ValueError("DUPLICATE_PROVIDER_EXPLICIT_REPLACE_REQUIRED")
        require_compatible_port(_required_v2_port(key), adapter.descriptor, adapter)
        self._adapters[key] = adapter

    def bind_consumer(
        self, consumer_id: str, provider_id: str, required: PortDescriptor,
    ) -> FixtureSourceAdapterV2:
        if type(consumer_id) is not str or not _ENDPOINT.fullmatch(consumer_id):
            raise ValueError("Explicit consumer identity required")
        if consumer_id in self._pins:
            raise ValueError("DUPLICATE_CONSUMER")
        adapter = self.resolve(provider_id, required)
        self._pins[consumer_id] = provider_id, required
        return adapter

    def resolve(
        self, provider_id: str, required: PortDescriptor,
    ) -> FixtureSourceAdapterV2:
        key = _provider_id(provider_id)
        if key not in self._adapters:
            raise KeyError("PROVIDER_NOT_REGISTERED_NO_FALLBACK")
        adapter = self._adapters[key]
        if type(required) is not PortDescriptor or required.scope != key:
            raise ValueError("REQUESTED_PROVIDER_SCOPE_MISMATCH")
        require_compatible_port(required, adapter.descriptor, adapter)
        return adapter

    def probe(
        self, request: FixtureProbeRequestV2, required: PortDescriptor,
    ) -> FixtureProbeReceiptV2:
        if type(request) is not FixtureProbeRequestV2:
            raise TypeError("Typed metadata request required")
        return self.resolve(request.provider_id, required).probe(request)

    def replace(self, provider_id: str, next_adapter: FixtureSourceAdapterV2) -> None:
        key = _provider_id(provider_id)
        if key not in self._adapters:
            raise KeyError("PROVIDER_NOT_REGISTERED_NO_FALLBACK")
        if type(next_adapter) is not FixtureSourceAdapterV2:
            raise TypeError("Exact fixture adapter required")
        if next_adapter.identity.provider_id != key:
            raise ValueError("PROVIDER_REPLACEMENT_CROSS_SCOPE_DENIED")
        prior = self._adapters[key]
        if next_adapter.identity.endpoint_id != prior.identity.endpoint_id:
            raise ValueError("ENDPOINT_CHANGE_REQUIRES_SEPARATE_MIGRATION")
        # Rollback to v2.0 is valid only if ALL pinned consumers allow it.
        # Do not mistake current v2.1 for an immutable minimum version.
        require_compatible_port(_required_v2_port(key), next_adapter.descriptor, next_adapter)
        for pinned_provider, required in self._pins.values():
            if pinned_provider == key:
                require_compatible_port(required, next_adapter.descriptor, next_adapter)
        self._adapters[key] = next_adapter

    def detach_consumer(self, consumer_id: str) -> None:
        if consumer_id not in self._pins:
            raise KeyError("UNKNOWN_CONSUMER")
        del self._pins[consumer_id]

    def remove(self, provider_id: str) -> None:
        key = _provider_id(provider_id)
        if key not in self._adapters:
            raise KeyError("PROVIDER_NOT_REGISTERED_NO_FALLBACK")
        if any(k == key for k, _ in self._pins.values()):
            raise ValueError("PROVIDER_HAS_ATTACHED_CONSUMERS")
        del self._adapters[key]

    @property
    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))


def synthetic_source_registry() -> FixtureSourceRegistryV2:
    """Explicit initial 3 namespaces; future providers require registration."""
    registry = FixtureSourceRegistryV2()
    for provider in _STARTING_PROVIDERS:
        registry.register(FixtureSourceAdapterV2(
            FixtureSourceIdentityV2(provider, f"fixture.{provider.lower()}.d1"),
        ))
    return registry
