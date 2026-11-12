"""Opt-in v2 replay consumer port, strictly ENGINEERING/SYNTHETIC only.

A v2 port must be explicitly selected; nothing here modifies or wraps
legacy v1 BacktestHarness. Versioned structural checks are NOT proof of
licensed market data, source clock custody or valid detector calibration.
"""
from dataclasses import dataclass

from .causal import CausalMarketEvent
from .contracts import DecisionStatus, Strategy, ZONE_IDS
from .engineering_contracts import PortDescriptor, require_compatible_port
from .strict_contract_v2 import StrictReplayClockV2, StrictSignalDecisionV2

V2_MARKET_PORT = PortDescriptor(
    "replay.causal_events", "2.0.0", "SYNTHETIC_TEST_ONLY",
    ("available_events",),
)
V2_RULES_PORT = PortDescriptor(
    "rules.zone_registry", "2.0.0", "SYNTHETIC_TEST_ONLY",
    ("evaluate",),
)


@dataclass(frozen=True)
class StrictReplayHarnessV2:
    """Immutable fixture wiring with mandatory, explicit v2 port descriptors."""

    clock: StrictReplayClockV2
    market_data: object
    rules: object
    market_port: PortDescriptor
    rules_port: PortDescriptor

    def __post_init__(self) -> None:
        # Enforce the contract even for direct Python construction; a caller
        # must not bypass from_contracts() by omitting versioned port metadata.
        if type(self.clock) is not StrictReplayClockV2:
            raise TypeError("Explicit StrictReplayClockV2 required")
        require_compatible_port(V2_MARKET_PORT, self.market_port, self.market_data)
        require_compatible_port(V2_RULES_PORT, self.rules_port, self.rules)

    @classmethod
    def from_contracts(
        cls, *, clock: StrictReplayClockV2, market_data: object,
        market_port: PortDescriptor, rules: object,
        rules_port: PortDescriptor,
    ) -> "StrictReplayHarnessV2":
        return cls(
            clock=clock, market_data=market_data, rules=rules,
            market_port=market_port, rules_port=rules_port,
        )

    def visible_events(self) -> tuple[CausalMarketEvent, ...]:
        """No future-known or future-event observations in synthetic replay."""
        if type(self.clock) is not StrictReplayClockV2:
            raise TypeError("Strict v2 clock required")
        observations = self.market_data.available_events(self.clock.as_of_utc)
        events = tuple(observations)
        if any(type(item) is not CausalMarketEvent for item in events):
            raise TypeError("Only typed causal fixture events accepted")
        visible = (
            event for event in events
            if self.clock.known(event.event_time_utc)
            and self.clock.known(event.first_known_time_utc)
        )
        return tuple(sorted(
            visible,
            key=lambda item: (
                item.first_known_time_utc,
                item.event_time_utc,
                item.event_id,
                item.revision_id,
            ),
        ))

    def evaluate_unverified(
        self, zone_id: str, strategy: Strategy,
    ) -> StrictSignalDecisionV2:
        """Fail closed until independent detector source qualification exists.

        A caller-supplied rule cannot claim DETECTED, NOT_DETECTED or verified
        evidence through this engineering-only v2 fixture interface.
        """
        if type(self.clock) is not StrictReplayClockV2:
            raise TypeError("Strict v2 clock required")
        if type(zone_id) is not str or zone_id not in ZONE_IDS:
            raise ValueError("Unknown zone")
        if type(strategy) is not Strategy:
            raise TypeError("Typed strategy required")
        result = self.rules.evaluate(zone_id, strategy, self.clock.as_of_utc)
        if type(result) is not StrictSignalDecisionV2:
            raise TypeError("StrictSignalDecisionV2 required from v2 rule port")
        if result.zone_id != zone_id or result.strategy is not strategy:
            raise ValueError("Rule response identity mismatch")
        if result.status is not DecisionStatus.UNVERIFIED or result.evidence:
            raise PermissionError("Engineering port cannot promote a signal")
        return result
