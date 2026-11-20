"""MST §248: nontrading cross-feed D1 SOURCE-BASIS/FRESHNESS audit.

This is NOT a data adapter or market Cache publisher. Inputs must come from
separately observed SSI MCP / DNSE MCP / VCBS MCP research surfaces, NOT the
GitHub Actions SSI FastConnect V3 ingress. Three providers returning identical
numbers does not certify licensed storage, first-known, raw/adjusted basis,
volume scopes, or closed venue candles.

No transport, storage, broker, signer, CAS, or policy flags are set by this
module. Never print untrusted raw input or actual price/volume values.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

RECORD_FIELDS = frozenset((
    "source", "symbol", "session_date", "close", "volume",
    "price_unit", "price_basis", "volume_scope", "record_origin",
))
SOURCE_UNITS = {
    "SSI_MCP_COMPACT_D1": "VND",
    "DNSE_MCP_DAILY_HISTORY": "THOUSAND_VND",
    "VCBS_MCP_HISTORY_D1": "VND",
}
PRICE_BASIS = frozenset(("raw", "adjusted", "unknown"))
VOLUME_SCOPES = frozenset(("matched", "all_trades", "unknown"))
RECORD_ORIGINS = frozenset((
    "historical", "board_supplement", "provisional", "unknown",
))
MAX_CLOSE_VND = Decimal("10000000")
MAX_VOLUME = 1_000_000_000_000


class BasisAuditDenied(ValueError):
    """Stable errors only. Never include provider rows, prices, or tokens."""


def _decimal(value: Any, field: str) -> Decimal:
    if type(value) not in (int, float, str):
        raise BasisAuditDenied("MST_248_"+field+"_TYPE_DENIED")
    if type(value) is str and (not value or len(value) > 25 or value.strip() != value):
        raise BasisAuditDenied("MST_248_"+field+"_TEXT_DENIED")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, OverflowError):
        raise BasisAuditDenied("MST_248_"+field+"_INVALID") from None
    if not number.is_finite():
        raise BasisAuditDenied("MST_248_"+field+"_NONFINITE_DENIED")
    return number


def _row(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != RECORD_FIELDS:
        raise BasisAuditDenied("MST_248_RECORD_FIELD_SET_DENIED")
    provider = value.get("source")
    if type(provider) is not str or provider not in SOURCE_UNITS:
        raise BasisAuditDenied("MST_248_SOURCE_NOT_MCP_D1")
    if (type(value.get("symbol")) is not str
        or value["symbol"] not in ("FPT", "DCM", "HPG")):
        raise BasisAuditDenied("MST_248_PILOT_SYMBOL_DENIED")
    raw_date = value.get("session_date")
    if (type(raw_date) is not str or len(raw_date) != 10):
        raise BasisAuditDenied("MST_248_SESSION_DATE_DENIED")
    try:
        day = date.fromisoformat(raw_date)
    except ValueError:
        raise BasisAuditDenied("MST_248_SESSION_DATE_DENIED") from None
    if day.isoformat() != raw_date:
        raise BasisAuditDenied("MST_248_SESSION_DATE_DENIED")
    if (type(value.get("price_unit")) is not str
        or value["price_unit"] != SOURCE_UNITS[provider]):
        raise BasisAuditDenied("MST_248_EXPLICIT_SOURCE_UNIT_REQUIRED")
    if (type(value.get("price_basis")) is not str
        or value["price_basis"] not in PRICE_BASIS):
        raise BasisAuditDenied("MST_248_PRICE_BASIS_DENIED")
    if (type(value.get("volume_scope")) is not str
        or value["volume_scope"] not in VOLUME_SCOPES):
        raise BasisAuditDenied("MST_248_VOLUME_SCOPE_DENIED")
    if (type(value.get("record_origin")) is not str
        or value["record_origin"] not in RECORD_ORIGINS):
        raise BasisAuditDenied("MST_248_RECORD_ORIGIN_DENIED")
    close = _decimal(value["close"], "CLOSE")
    scale = Decimal(1000) if provider == "DNSE_MCP_DAILY_HISTORY" else Decimal(1)
    close_vnd = close * scale
    # Never silently round a price, upcast to a float or treat 45 as 45 VND.
    if (not 0 < close_vnd <= MAX_CLOSE_VND
        or close_vnd != close_vnd.to_integral_value()):
        raise BasisAuditDenied("MST_248_VND_PRICE_INTEGRITY_DENIED")
    volume = _decimal(value["volume"], "VOLUME")
    if (not 0 <= volume <= MAX_VOLUME
        or volume != volume.to_integral_value()):
        raise BasisAuditDenied("MST_248_SHARES_INTEGRITY_DENIED")
    return {
        "source": provider,
        "symbol": value["symbol"],
        "session_date": raw_date,
        "close_vnd": int(close_vnd),
        "volume_shares": int(volume),
        "price_basis": value["price_basis"],
        "volume_scope": value["volume_scope"],
        "record_origin": value["record_origin"],
    }


def assess_three_source_d1_candidate(records: Any) -> dict[str, Any]:
    """Only observational diagnostic; never a trusted source acceptance.

    Even when all three figures match and all say 'historical', the caller
    cannot make this produce trade-ready or closed-bar/rights attestations.
    """
    if type(records) is not list or len(records) != len(SOURCE_UNITS):
        raise BasisAuditDenied("MST_248_THREE_INDEPENDENT_SOURCES_REQUIRED")
    observations = [_row(record) for record in records]
    by_source = {r["source"]: r for r in observations}
    if set(by_source) != set(SOURCE_UNITS):
        raise BasisAuditDenied("MST_248_DUPLICATE_OR_MISSING_SOURCE")
    symbols = {r["symbol"] for r in observations}
    dates = {r["session_date"] for r in observations}
    if len(symbols) != 1 or len(dates) != 1:
        raise BasisAuditDenied("MST_248_SCOPE_DATE_NOT_COMPARABLE")
    basis_set = {r["price_basis"] for r in observations}
    scope_set = {r["volume_scope"] for r in observations}
    basis_aligned = len(basis_set) == 1 and "unknown" not in basis_set
    volume_aligned = len(scope_set) == 1 and "unknown" not in scope_set
    source_origin_historical = all(
        r["record_origin"] == "historical" for r in observations
    )
    reasons = []
    if not basis_aligned:
        reasons.append("PRICE_ADJUSTMENT_BASIS_UNKNOWN_OR_MIXED")
    if not volume_aligned:
        reasons.append("VOLUME_SCOPE_UNKNOWN_OR_MIXED")
    if not source_origin_historical:
        reasons.append("PROVISIONAL_OR_BOARD_SUPPLEMENT_OBSERVED")
    close_match = (
        len({r["close_vnd"] for r in observations}) == 1
        if basis_aligned else None
    )
    volume_match = (
        len({r["volume_shares"] for r in observations}) == 1
        if volume_aligned else None
    )
    if close_match is False:
        reasons.append("NORMALIZED_CLOSE_DISAGREEMENT")
    if volume_match is False:
        reasons.append("NORMALIZED_VOLUME_DISAGREEMENT")
    if not reasons:
        reasons.append("INDEPENDENT_SOURCE_RIGHTS_AND_FINALITY_NOT_ESTABLISHED")
    # This diagnostic is intentionally observational. A price match and
    # 'historical' label from data providers cannot grant release authority.
    return {
        "schema": "mst.cloud.research_three_feed_d1_basis_audit.v0.1",
        "status": "OBSERVED_UNVERIFIED_NO_TRADE",
        "symbol": observations[0]["symbol"],
        "session_date": observations[0]["session_date"],
        "source_count": len(observations),
        "source_units_explicitly_normalized_to_vnd": True,
        "price_basis_aligned": basis_aligned,
        "matched_close_after_unit_conversion": close_match,
        "volume_scope_aligned": volume_aligned,
        "matched_volume_only_when_scope_aligned": volume_match,
        "all_records_claim_historical_origin": source_origin_historical,
        "block_reasons": reasons,
        "fastconnect_v3_gitHub_cloud_access_proven": False,
        "source_retention_rights_independently_attested": False,
        "source_first_known_or_venue_finality_verified": False,
        "corporate_action_adjustment_crosschecked": False,
        "safe_to_publish_cache_head": False,
        "signals_or_trades_eligible": False,
    }
