"""SSI retrieval custody metadata; never vendor first-known or adjustment proof."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

SSI_PROVENANCE_SCHEMA = "mst.cloud.unpublished_source_snapshot.v0.2"
PROVENANCE_FIELDS = {
    "retrieval_started_utc", "retrieval_finished_utc", "requested_from_date",
    "requested_to_date", "requested_symbol", "requested_native_tf",
    "native_rows_sha256", "source_first_known_clock_attested",
    "vendor_adjustment_revision",
}


class RetrievalDenied(ValueError):
    """Fixed code only."""


def native_rows_digest(rows: Any) -> str:
    try:
        raw = json.dumps(rows, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise RetrievalDenied("MST_SSI_RETRIEVAL_JSON_DENIED") from None


def utc_label(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _utc(value: Any) -> datetime:
    if type(value) is not str or len(value) != 32:
        raise RetrievalDenied("MST_SSI_RETRIEVAL_CLOCK_DENIED")
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo != timezone.utc or utc_label(dt) != value:
            raise ValueError
        return dt
    except (ValueError, OverflowError):
        raise RetrievalDenied("MST_SSI_RETRIEVAL_CLOCK_DENIED") from None


def make_provenance(start: datetime, end: datetime, *, symbol: str,
                    tf: str, first: date, last: date, rows: Any) -> dict:
    p = {
        "retrieval_started_utc": utc_label(start),
        "retrieval_finished_utc": utc_label(end),
        "requested_from_date": first.isoformat(),
        "requested_to_date": last.isoformat(),
        "requested_symbol": symbol,
        "requested_native_tf": tf,
        "native_rows_sha256": native_rows_digest(rows),
        "source_first_known_clock_attested": False,
        "vendor_adjustment_revision": None,
    }
    validate_provenance(p, rows, {
        "MST_SSI_FROM_DATE": first.isoformat(),
        "MST_SSI_TO_DATE": last.isoformat(),
        "MST_SOURCE_SYMBOL": symbol, "MST_SOURCE_TF": tf,
    })
    return p


def validate_provenance(p: Any, rows: Any, env: Mapping[str, str]) -> None:
    if (type(p) is not dict or set(p) != PROVENANCE_FIELDS
            or p["source_first_known_clock_attested"] is not False
            or p["vendor_adjustment_revision"] is not None):
        raise RetrievalDenied("MST_SSI_RETRIEVAL_AUTHORITY_DENIED")
    if _utc(p["retrieval_finished_utc"]) < _utc(p["retrieval_started_utc"]):
        raise RetrievalDenied("MST_SSI_RETRIEVAL_CLOCK_DENIED")
    for key, env_key in (
        ("requested_from_date", "MST_SSI_FROM_DATE"),
        ("requested_to_date", "MST_SSI_TO_DATE"),
        ("requested_symbol", "MST_SOURCE_SYMBOL"),
        ("requested_native_tf", "MST_SOURCE_TF"),
    ):
        if type(p[key]) is not str or p[key] != env.get(env_key):
            raise RetrievalDenied("MST_SSI_RETRIEVAL_SCOPE_DENIED")
    try:
        first = date.fromisoformat(p["requested_from_date"])
        last = date.fromisoformat(p["requested_to_date"])
        if first.isoformat() != p["requested_from_date"] or last.isoformat() != p["requested_to_date"] or first > last:
            raise ValueError
    except ValueError:
        raise RetrievalDenied("MST_SSI_RETRIEVAL_SCOPE_DENIED") from None
    if type(rows) is not list or not rows or p["native_rows_sha256"] != native_rows_digest(rows):
        raise RetrievalDenied("MST_SSI_RETRIEVAL_DIGEST_DENIED")
