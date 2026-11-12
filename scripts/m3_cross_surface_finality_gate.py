"""MST M3: fail-closed cross-surface finality hints, metadata-only.

No provider calls, price data, raw quotes, credentials, persistence,
authoritative market calendar, license approval, or trading. A feed-level
'not provisional' observation cannot certify another endpoint/timeframe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import json


class Endpoint(str, Enum):
    SSI_D1 = "SSI.marketdata_list_stock_daily_data"
    SSI_INTRADAY_LATEST = "SSI.marketdata_list_intraday_stock_infor.latest"
    DNSE_D1 = "DNSE.price_get_history.DAY"
    VCBS_D1 = "VCBS.vcbs_get_history.D"
    VCBS_INTRADAY_BOARD = "VCBS.vcbs_get_intraday_history"


MARKER_ENDPOINTS = frozenset((Endpoint.VCBS_D1, Endpoint.VCBS_INTRADAY_BOARD))


@dataclass(frozen=True)
class Observation:
    """Only a date and an endpoint-specific boolean hint; NO market values."""
    endpoint: Endpoint
    day: date
    marker_present: bool = False
    marker: bool | None = None
    issuer_finality_authenticated: bool = False
    retention_authorized: bool = False

    def __post_init__(self) -> None:
        if type(self.endpoint) is not Endpoint or type(self.day) is not date:
            raise TypeError("EXACT_ENDPOINT_AND_TRADING_DAY_REQUIRED")
        if type(self.marker_present) is not bool:
            raise TypeError("EXPLICIT_MARKER_PRESENCE_REQUIRED")
        if self.endpoint not in MARKER_ENDPOINTS and self.marker_present:
            raise ValueError("ENDPOINT_DOES_NOT_SUPPLY_THIS_FINALITY_MARKER")
        if self.marker_present:
            if type(self.marker) is not bool:
                raise TypeError("PRESENT_MARKER_MUST_BE_BOOLEAN")
        elif self.marker is not None:
            raise ValueError("ABSENT_MARKER_CANNOT_HAVE_VALUE")
        if (self.issuer_finality_authenticated is not False
                or self.retention_authorized is not False):
            raise PermissionError("CALLER_CANNOT_SELF_ATTEST_SOURCE_RIGHTS_OR_FINALITY")


def classify(evidence: Observation) -> dict[str, object]:
    if type(evidence) is not Observation:
        raise TypeError("TYPED_SOURCE_EVIDENCE_REQUIRED")
    if evidence.endpoint is Endpoint.VCBS_D1 and evidence.marker_present and evidence.marker:
        state = "EXPLICIT_VCBS_D1_PROVISIONAL"
    elif evidence.endpoint is Endpoint.VCBS_INTRADAY_BOARD and evidence.marker_present:
        state = "VCBS_BOARD_OHLC_HINT_ONLY"
    elif evidence.marker_present:
        state = "NONPROVISIONAL_HINT_UNQUALIFIED"
    else:
        state = "NO_EXPLICIT_FINALITY_FIELD"
    return {
        "endpoint": evidence.endpoint.value,
        "day": evidence.day.isoformat(),
        "observed_state": state,
        "claim_scope": "D1" if evidence.endpoint in (
            Endpoint.SSI_D1, Endpoint.DNSE_D1, Endpoint.VCBS_D1
        ) else "INTRADAY_REFERENCE",
        "closed_bar_verified": False,
        "publisher_first_known_verified": False,
        "retention_authorized": False,
        "signal_eligible": False,
        "cache_publish_authorized": False,
        "production_authorized": False,
    }


def reconcile(left: Observation, right: Observation) -> dict[str, object]:
    """Compare hints without upgrading either endpoint or borrowing finality."""
    if type(left) is not Observation or type(right) is not Observation:
        raise TypeError("TWO_TYPED_SOURCE_OBSERVATIONS_REQUIRED")
    if left.day != right.day:
        raise ValueError("SAME_TRADING_DAY_REQUIRED_FOR_CROSS_SURFACE_COMPARISON")
    lhs, rhs = classify(left), classify(right)
    if left.endpoint is right.endpoint:
        raise ValueError("CROSS_SURFACE_REQUIRES_DISTINCT_ENDPOINTS")
    return {
        "day": left.day.isoformat(),
        "left": lhs["observed_state"],
        "right": rhs["observed_state"],
        "left_endpoint": left.endpoint.value,
        "right_endpoint": right.endpoint.value,
        "can_borrow_finality_between_endpoints": False,
        "source_closed_bar_verified": False,
        "source_entitlement_verified": False,
        "cache_publish_authorized": False,
        "signal_eligible": False,
        "decision": "NO_GO_CROSS_SURFACE_FINALITY_NOT_TRANSFERABLE",
    }


def example() -> dict[str, object]:
    """Invented structural metadata only; NOT a replay of vendor OHLCV."""
    d = date(2026, 11, 12)
    return reconcile(
        Observation(Endpoint.VCBS_D1, d, True, True),
        Observation(Endpoint.VCBS_INTRADAY_BOARD, d, True, False),
    )


if __name__ == "__main__":
    print(json.dumps(example(), sort_keys=True))
