"""§204 Cloud-only SIX timeframe Cache→Signal readiness, unpublished only.

This is a bounded consistency/coverage view over CALLER-supplied immutable
CanonicalCandle candidates, not actual licensed SSI/DNSE/VCBS ingestion or
a backtest/qualified 16-zone strategy. H4 is DERIVED-ONLY after separately
reviewed venue-session/calendar closure and will NEVER be inferred as
a native SSI/DNSE feed. All market qualification and Signal/UI/trade gates
stay false even if every synthetic CanonicalCandle passes local checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

from .market_data import CanonicalCandle, PriceBasis, Timeframe
from .replay import require_utc

TF_ORDER = (Timeframe.M5, Timeframe.M15, Timeframe.M30,
            Timeframe.H1, Timeframe.H4, Timeframe.D1)
TF_NAMES = tuple(x.value for x in TF_ORDER)
ID = re.compile(r"[A-Za-z0-9:_./-]{3,120}\Z")
EXCHANGE = re.compile(r"(HOSE|HNX|UPCOM)\Z")
MAX_BARS_PER_TF = 512


class PrivateMultiTfDenied(ValueError):
    """Fixed errors, never return source prices/secret/row identity."""


@dataclass(frozen=True)
class PrivateMultiTfReadiness:
    summary: dict[str, Any]
    reference_sha256: str
    qualified_for_signals: bool = False
    qualified_for_backtest: bool = False
    eligible_for_trades: bool = False

    def __post_init__(self) -> None:
        if (type(self.summary) is not dict
                or self.summary.get("schema") != "mst.private.six_tf_readiness.v0.1"
                or self.summary.get("pipeline_state") != "UNVERIFIED"
                or self.summary.get("source_released") is not False
                or self.summary.get("signal_engine_parity_verified") is not False
                or self.summary.get("ui_step08_approved") is not False
                or self.summary.get("trades_eligible") is not False
                or self.qualified_for_signals is not False
                or self.qualified_for_backtest is not False
                or self.eligible_for_trades is not False):
            raise PrivateMultiTfDenied("MST_SIX_TF_RELEASE_CLAIM_FORBIDDEN")
        rows = self.summary.get("timeframes")
        if (type(rows) is not list or len(rows) != 6
                or [r.get("timeframe") for r in rows if type(r) is dict]
                   != list(TF_NAMES)
                or any(type(r) is not dict
                       or r.get("verified_for_signals") is not False
                       or r.get("source_finality_attested") is not False
                       or r.get("price_basis_officially_attested") is not False
                       or r.get("status") not in (
                           "MISSING", "CANDIDATE_ONLY_UNVERIFIED")
                       or type(r.get("observed_candles")) is not int
                       or not 0 <= r["observed_candles"] <= MAX_BARS_PER_TF
                       for r in rows)):
            raise PrivateMultiTfDenied("MST_SIX_TF_STRUCTURE_INVALID")
        if (self.summary.get("h4_native_provider_supported") is not False
                or self.summary.get("w1_context_verified") is not False
                or self.summary.get("highwater_independent_cas_verified") is not False
                or self.summary.get("venue_calendar_verified") is not False):
            raise PrivateMultiTfDenied("MST_SIX_TF_FABRICATED_H4_OR_W1")
        try:
            raw = json.dumps(
                self.summary, sort_keys=True, separators=(",", ":"),
                allow_nan=False, ensure_ascii=True,
            ).encode()
        except (ValueError, TypeError, OverflowError):
            raise PrivateMultiTfDenied("MST_SIX_TF_SUMMARY_JSON_INVALID") from None
        if sha256(raw).hexdigest() != self.reference_sha256:
            raise PrivateMultiTfDenied("MST_SIX_TF_SUMMARY_DIGEST_CHANGED")


def inspect_six_tf_candidate_coverage(
    candles_by_tf: Any, *, instrument_id: str, exchange: str,
    as_of_utc: datetime,
) -> PrivateMultiTfReadiness:
    """Inspect a homogeneous source partition and 6 explicit TF buckets.

    Even VERIFIED+CLOSED synthetic CanonicalCandle inputs only prove
    *necessary local checks*, not venue/provider attestation or eligibility.
    Missing TF is not "NO SIGNAL", nor may source corrections be erased.
    """
    require_utc(as_of_utc)
    if (type(instrument_id) is not str
            or ID.fullmatch(instrument_id) is None
            or type(exchange) is not str
            or EXCHANGE.fullmatch(exchange) is None
            or type(candles_by_tf) is not dict
            or set(candles_by_tf) != set(TF_ORDER)):
        raise PrivateMultiTfDenied("MST_SIX_TF_INPUT_SCOPE_INVALID")
    rows = []
    provider_seen: str | None = None
    basis_seen: PriceBasis | None = None
    for timeframe in TF_ORDER:
        candles = candles_by_tf[timeframe]
        if (type(candles) not in (list, tuple)
                or len(candles) > MAX_BARS_PER_TF):
            raise PrivateMultiTfDenied("MST_SIX_TF_COUNT_OR_TYPE_INVALID")
        previous = None
        local_provider: str | None = None
        local_basis: PriceBasis | None = None
        necessary = 0
        for candle in candles:
            if type(candle) is not CanonicalCandle:
                raise PrivateMultiTfDenied("MST_SIX_TF_NON_CANONICAL_CANDLE")
            key = candle.market_bar_key
            if (key.timeframe is not timeframe
                    or key.instrument_id != instrument_id
                    or key.exchange != exchange
                    or key.instrument_class.value != "STOCK"
                    or candle.revision.first_known_time_utc > as_of_utc
                    or candle.revision.retrieved_at_utc > as_of_utc
                    or candle.bar_end_utc > as_of_utc
                    or key.bar_start_utc > as_of_utc):
                raise PrivateMultiTfDenied("MST_SIX_TF_LOOKAHEAD_OR_IDENTITY")
            if previous is not None and key.bar_start_utc <= previous:
                raise PrivateMultiTfDenied("MST_SIX_TF_DUPLICATE_OR_REORDERED")
            previous = key.bar_start_utc
            p = candle.observation_key.provider_id
            basis = key.price_basis
            if (type(p) is not str or not p
                    or local_provider is not None and p != local_provider
                    or local_basis is not None and basis is not local_basis
                    or provider_seen is not None and provider_seen != p
                    or basis_seen is not None and basis is not basis_seen):
                raise PrivateMultiTfDenied("MST_SIX_TF_MIXED_PROVIDER_OR_BASIS")
            provider_seen = local_provider = p
            basis_seen = local_basis = basis
            necessary += int(candle.eligible_for_confirmed_signals(as_of_utc))
        rows.append({
            "timeframe": timeframe.value,
            "observed_candles": len(candles),
            "local_necessary_checks_count": necessary,
            "status": ("CANDIDATE_ONLY_UNVERIFIED" if candles else "MISSING"),
            "source_finality_attested": False,
            "price_basis_officially_attested": False,
            "verified_for_signals": False,
            "derived_h4_venue_policy_proven": False if timeframe is Timeframe.H4 else None,
        })
    report = {
        "schema": "mst.private.six_tf_readiness.v0.1",
        "instrument_id": instrument_id, "exchange": exchange,
        "source_provider": provider_seen,
        "as_of_utc": as_of_utc.isoformat(),
        "timeframes": rows,
        "required_timeframes": list(TF_NAMES),
        "candidate_timeframes_present": sum(
            row["observed_candles"] > 0 for row in rows
        ),
        "h4_native_provider_supported": False,
        "w1_context_verified": False,
        "venue_calendar_verified": False,
        "source_released": False,
        "highwater_independent_cas_verified": False,
        "signal_engine_parity_verified": False,
        "ui_step08_approved": False,
        "pipeline_state": "UNVERIFIED",
        "trades_eligible": False,
    }
    wire = json.dumps(report, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()
    return PrivateMultiTfReadiness(report, sha256(wire).hexdigest())
