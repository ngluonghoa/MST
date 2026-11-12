"""MST M3: observe provider-reported session/ATC volume disagreements safely.

A small source-neutral reconciliation policy, NOT a quote adapter, source
publisher, official volume-basis mapping, real cache writer, or trading system.
Aggregate share counts may be compared numerically without claiming all
provider products report the same underlying market-volume scope. No real
market prices, provider credential, issuer first-known or signing operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import re


class Surface(str, Enum):
    SSI_MINUTE_SUM = "SSI.intraday.minute_volume_sum"
    DNSE_D1 = "DNSE.price_get_history.DAY"
    VCBS_D1 = "VCBS.vcbs_get_history.D"
    VCBS_BOARD = "VCBS.vcbs_get_intraday_history.board"


_ORDER = (Surface.SSI_MINUTE_SUM, Surface.DNSE_D1, Surface.VCBS_D1, Surface.VCBS_BOARD)


@dataclass(frozen=True)
class UntrustedVolumeObservation:
    source: Surface
    symbol: str
    trading_day: date
    session_volume_shares: int
    atc_volume_shares: int | None = None
    units: str = "shares"
    independent_issuer_authenticated: bool = False
    provider_volume_scope_verified: bool = False
    first_known_authenticated: bool = False
    source_retention_approved_by_vendor: bool = False

    def __post_init__(self) -> None:
        if type(self.source) is not Surface:
            raise TypeError("EXACT_PROVIDER_SURFACE_REQUIRED")
        if type(self.symbol) is not str or not re.fullmatch(r"[A-Z0-9]{1,10}", self.symbol):
            raise ValueError("CANONICAL_STOCK_SYMBOL_REQUIRED")
        if type(self.trading_day) is not date:
            raise TypeError("LOCAL_TRADING_DAY_REQUIRED")
        if self.units != "shares" or type(self.units) is not str:
            raise ValueError("EXACT_SHARE_UNIT_REQUIRED")
        if type(self.session_volume_shares) is not int or self.session_volume_shares < 0:
            raise ValueError("NONNEGATIVE_INTEGRAL_SESSION_SHARES_REQUIRED")
        if self.atc_volume_shares is not None:
            if (type(self.atc_volume_shares) is not int or
                    self.atc_volume_shares < 0 or
                    self.atc_volume_shares > self.session_volume_shares):
                raise ValueError("INTEGRAL_ATC_SUBSET_REQUIRED")
            if self.source not in (Surface.SSI_MINUTE_SUM, Surface.VCBS_BOARD):
                raise ValueError("ATC_COMPONENT_ONLY_ON_OBSERVED_INTRADAY_SURFACES")
        if (self.independent_issuer_authenticated is not False or
                self.provider_volume_scope_verified is not False or
                self.first_known_authenticated is not False or
                self.source_retention_approved_by_vendor is not False):
            raise PermissionError("CALLER_CANNOT_SELF_ATTEST_VENDOR_OR_PUBLISHER_AUTHORITY")


def reconcile_observed_volumes(*records: UntrustedVolumeObservation) -> dict[str, object]:
    """Return a deterministic numeric discrepancy report, never a source grant."""
    if not 2 <= len(records) <= 4:
        raise ValueError("TWO_TO_FOUR_DISTINCT_SOURCE_SURFACES_REQUIRED")
    if any(type(r) is not UntrustedVolumeObservation for r in records):
        raise TypeError("TYPED_UNTRUSTED_OBSERVATIONS_ONLY")
    keys = [r.source for r in records]
    if len(set(keys)) != len(records):
        raise ValueError("DUPLICATE_SOURCE_SURFACE_CANNOT_BE_DOUBLE_COUNTED")
    if len({r.symbol for r in records}) != 1 or len({r.trading_day for r in records}) != 1:
        raise ValueError("EXACT_SYMBOL_AND_TRADING_SESSION_REQUIRED")
    ordered = tuple(sorted(records, key=lambda x: _ORDER.index(x.source)))
    pairs: list[dict[str, object]] = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            diff = left.session_volume_shares - right.session_volume_shares
            atc_diff = (
                left.atc_volume_shares - right.atc_volume_shares
                if left.atc_volume_shares is not None and
                right.atc_volume_shares is not None else None
            )
            pairs.append({
                "left_source": left.source.value,
                "right_source": right.source.value,
                "left_minus_right_shares": diff,
                "exact_observed_equal": diff == 0,
                "left_minus_right_atc_shares": atc_diff,
                "session_difference_equals_atc_difference": (
                    diff == atc_diff if atc_diff is not None else None
                ),
                "auction_arithmetic_proves_cause": False,
                "identical_market_volume_scope_proven": False,
            })
    disagreements = sum(int(not p["exact_observed_equal"]) for p in pairs)
    return {
        "schema": "mst.m3.untrusted.source_volume_reconciliation.v1",
        "symbol": ordered[0].symbol,
        "trading_day": ordered[0].trading_day.isoformat(),
        "volume_by_source": [
            {"source": r.source.value, "session_shares": r.session_volume_shares,
             "atc_shares": r.atc_volume_shares}
            for r in ordered
        ],
        "pairwise_observations": pairs,
        "pairwise_disagreement_count": disagreements,
        "observed_state": (
            "OBSERVED_VOLUME_MISMATCH_QUARANTINE" if disagreements else
            "OBSERVED_EQUAL_COUNTS_UNTRUSTED"
        ),
        "provider_scope_equivalence_verified": False,
        "issuer_source_and_first_known_verified": False,
        "source_native_closed_bar_verified": False,
        "licensed_persistent_retention_verified": False,
        "complete_market_auction_proof": False,
        "cache_v2_authorized": False,
        "signal_eligible": False,
        "production_authorized": False,
    }


def compare_volume_refreshes(
    previous: tuple[UntrustedVolumeObservation, ...],
    current: tuple[UntrustedVolumeObservation, ...],
    *,
    previous_received_utc: datetime,
    current_received_utc: datetime,
) -> dict[str, object]:
    """Pure receipt/delta gate for one symbol/session, no publisher write.

    Values are *observed provider volume counts only*. Equal counts do NOT
    establish identical OHLCV, entitlement, first-known, session coverage or
    immutable provider revision. The times are local RECEIPT clocks only.
    """
    if type(previous) is not tuple or type(current) is not tuple:
        raise TypeError("IMMUTABLE_TYPED_SOURCE_RECEIPT_TUPLES_REQUIRED")
    for stamp in (previous_received_utc, current_received_utc):
        if (type(stamp) is not datetime or stamp.tzinfo is None
                or stamp.utcoffset() != timedelta(0)):
            raise ValueError("EXPLICIT_UTC_RECEIPT_CLOCK_REQUIRED")
    if current_received_utc <= previous_received_utc:
        raise ValueError("STRICTLY_MONOTONE_OBSERVATION_RECEIPTS_REQUIRED")
    earlier = reconcile_observed_volumes(*previous)
    later = reconcile_observed_volumes(*current)
    if earlier["symbol"] != later["symbol"] or earlier["trading_day"] != later["trading_day"]:
        raise ValueError("SAME_SYMBOL_SESSION_REQUERY_REQUIRED")
    before = {x.source: x for x in previous}
    after = {x.source: x for x in current}
    if before.keys() != after.keys():
        raise ValueError("EXACT_SAME_PROVIDER_SURFACES_REQUIRED_FOR_REFRESH_DIFF")
    changes = []
    for source in _ORDER:
        if source not in before:
            continue
        first, second = before[source], after[source]
        volume_delta = second.session_volume_shares - first.session_volume_shares
        atc_delta = (
            second.atc_volume_shares - first.atc_volume_shares
            if second.atc_volume_shares is not None and
            first.atc_volume_shares is not None else None
        )
        atc_changed = second.atc_volume_shares != first.atc_volume_shares
        changes.append({
            "source": source.value,
            "prior_session_volume_shares": first.session_volume_shares,
            "current_session_volume_shares": second.session_volume_shares,
            "observed_volume_delta_shares": volume_delta,
            "prior_atc_volume_shares": first.atc_volume_shares,
            "current_atc_volume_shares": second.atc_volume_shares,
            "atc_delta_shares_if_both_present": atc_delta,
            "atc_presence_or_value_changed": atc_changed,
            "source_counts_changed": volume_delta != 0 or atc_changed,
            "entire_ohlcv_history_identical_proven": False,
        })
    changed = [x["source"] for x in changes if x["source_counts_changed"]]
    prev_gap = earlier["pairwise_disagreement_count"]
    curr_gap = later["pairwise_disagreement_count"]
    return {
        "schema": "mst.m3.private-source.volume-refresh-delta-preflight.v1",
        "symbol": later["symbol"],
        "trading_day": later["trading_day"],
        "previous_local_received_utc": previous_received_utc.astimezone(timezone.utc).isoformat(),
        "current_local_received_utc": current_received_utc.astimezone(timezone.utc).isoformat(),
        "previous_disagreement_pair_count": prev_gap,
        "current_disagreement_pair_count": curr_gap,
        "observed_disagreement_persists": prev_gap > 0 and curr_gap > 0,
        "observed_disagreement_numerically_cleared": prev_gap > 0 and curr_gap == 0,
        "observed_new_disagreement": prev_gap == 0 and curr_gap > 0,
        "changed_source_surfaces": changed,
        "sources": changes,
        "incremental_candidate_action": (
            "RECORD_VOLUME_REVISION_AND_INVALIDATE_RESEARCH_DEPENDENCIES"
            if changed else "RECORD_RECHECK_RECEIPT_WITHOUT_VOLUME_REVISION"
        ),
        "source_qa_action": (
            "QUARANTINE_PROVIDER_VOLUME_CONFLICT"
            if curr_gap > 0 else "OBSERVED_NUMERIC_AGREEMENT_ONLY"
        ),
        "source_retrieval_recheck_is_native_finality": False,
        "source_clock_is_publisher_first_known": False,
        "matching_volume_proves_identical_ohlcv": False,
        "signed_issuer_revision_verified": False,
        "approved_market_cache_write": False,
        "cross_provider_master_selected": False,
        "signal_eligible": False,
        "production_authorized": False,
    }
