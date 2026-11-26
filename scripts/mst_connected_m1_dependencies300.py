"""§300: private connected SSI M1 snapshot/window dependency audit.

Distinct from native FastConnect; no network, cache writes, first-known,
calendar, price basis, missing-minute or production qualification.
Hashes are private diagnostic evidence, not vendor signatures.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import re

from swing_trading.hose_session_geometry210 import (
    REGULAR_WINDOWS, MinuteLabelMeaning211, SsiQueryMode,
    inspect_mode_scoped_ssi_label,
)
from swing_trading.ssi_intraday_session_probe209 import (
    inspect_ssi_minute_session_reference, MinuteProbeState, MinuteProbeDenied,
)

SCHEMA = "mst.private.ssi_connected_m1_dependency.v0.1"
ENDPOINT = "SSI.marketdata_list_intraday_stock_infor"
PRODUCT = "MCP_SSI_RANGE_1D_M1_OBSERVATION"
REQUIRED = {"symbol", "trading_date", "open", "high", "low", "close", "volume"}
OPTIONAL = {"ref_price", "avg_price", "price_changed", "price"}
TFS = (("M5", 5), ("M15", 15), ("M30", 30), ("H1", 60))
LOCAL = timezone(timedelta(hours=7))


class M1DependencyDenied(ValueError):
    """Fixed error codes; no private rows in exception text."""


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _utc(value):
    if type(value) is not datetime or value.utcoffset() != timedelta(0):
        raise M1DependencyDenied("MST_300_UTC_CAPTURE_REQUIRED")
    return value.astimezone(timezone.utc)


def _scalar(value):
    if type(value) is bool or value is None:
        return True
    if type(value) is int:
        return abs(value) < 2**63
    if type(value) is str:
        return len(value) <= 64 and re.fullmatch(
            r"[+-]?[0-9]{1,25}(?:\.[0-9]{1,18})?|true|false", value
        ) is not None
    return False


def _capture(response, symbol, day, started, finished):
    started, finished = _utc(started), _utc(finished)
    if finished < started or finished.astimezone(LOCAL).date() < day:
        raise M1DependencyDenied("MST_300_CAPTURE_ORDER")
    try:
        check = inspect_ssi_minute_session_reference(
            response, symbol=symbol, trading_day=day, as_of_utc=finished,
            daily_matched_volume=None,
        )
    except (MinuteProbeDenied, ValueError, TypeError):
        raise M1DependencyDenied("MST_300_SOURCE_SHAPE") from None
    if check.state is not MinuteProbeState.OBSERVED_UNVERIFIED:
        raise M1DependencyDenied("MST_300_EMPTY_OR_UNAVAILABLE_NOT_REVISION")
    rows = response["data"]["ticks"]
    scope = {"project": "MST", "endpoint": ENDPOINT, "product": PRODUCT,
             "symbol": symbol, "range": "1d", "to_date": day.isoformat()}
    by_minute = {}
    for row in rows:
        if (not REQUIRED <= set(row) <= REQUIRED | OPTIONAL
                or any(not _scalar(v) for k, v in row.items()
                       if k not in ("symbol", "trading_date"))
                or any(type(row[k]) not in (str, int)
                       for k in ("open", "high", "low", "close", "volume"))):
            raise M1DependencyDenied("MST_300_NATIVE_FIELD_DENIED")
        try:
            clock, _ = inspect_mode_scoped_ssi_label(
                row["trading_date"], session_day=day,
                mode=SsiQueryMode.RANGE_DAY_FIRST_OBSERVED,
            )
        except ValueError:
            raise M1DependencyDenied("MST_300_LABEL_DENIED") from None
        if datetime.combine(day, clock, tzinfo=LOCAL) > finished:
            raise M1DependencyDenied("MST_300_FUTURE_LABEL")
        minute = clock.hour * 60 + clock.minute
        by_minute[minute] = (_digest({"scope": scope, "row": row}), row)
    payload = _digest({"scope": scope, "rows": rows})
    receipt = {"scope": scope, "payload_sha256": payload, "observed_rows": len(rows),
               "retrieval_started_utc": started.isoformat(),
               "retrieval_finished_utc": finished.isoformat()}
    receipt["capture_sha256"] = _digest(receipt)
    return receipt, by_minute


def _aggregate(entries):
    rows = [r for _, r in entries]
    with localcontext() as context:
        context.prec = 80
        return (Decimal(str(rows[0]["open"])),
                max(Decimal(str(r["high"])) for r in rows),
                min(Decimal(str(r["low"])) for r in rows),
                Decimal(str(rows[-1]["close"])),
                sum(int(r["volume"]) for r in rows))


def _windows(old, new, scope):
    results = []
    for meaning in MinuteLabelMeaning211:
        shift = int(meaning is MinuteLabelMeaning211.END_UNVERIFIED)
        for tf, step in TFS:
            for lo, hi, session in REGULAR_WINDOWS:
                for start in range(lo, hi-step+1, step):
                    end = start + step
                    labels = tuple(range(start+shift, end+shift))
                    # 14:45 never enters continuous session windows.
                    a = [old[m] for m in labels if m in old]
                    b = [new[m] for m in labels if m in new]
                    identity = {"scope": scope, "schema": SCHEMA, "clock": meaning.value,
                                "tf": tf, "session": session, "start": start, "end": end}
                    def dependency(source):
                        # Include missing positions; do not infer a zero-volume row.
                        return _digest({"window": identity,
                                        "inputs": [(m, source[m][0] if m in source else None)
                                                   for m in labels]})
                    prev, current = dependency(old), dependency(new)
                    complete = len(a) == len(b) == step
                    results.append({"clock": meaning.value, "tf": tf, "session": session,
                                    "start_minute": start, "end_minute": end,
                                    "old_observed": len(a), "new_observed": len(b),
                                    "old_input_sha256": prev, "new_input_sha256": current,
                                    "input_changed": prev != current,
                                    "aggregate_changed": _aggregate(a) != _aggregate(b)
                                    if complete else None,
                                    "both_full_labels": complete})
    return results


def compare_private_connected_m1(old_response, new_response, *, symbol, trading_day,
                                 old_started, old_finished, new_started, new_finished):
    """Recompute receipts from supplied observations, never trust caller hashes."""
    if type(trading_day) is not date:
        raise M1DependencyDenied("MST_300_SCOPE_DENIED")
    if _utc(new_started) < _utc(old_finished):
        raise M1DependencyDenied("MST_300_CAPTURE_OVERLAP")
    old, a = _capture(old_response, symbol, trading_day, old_started, old_finished)
    new, b = _capture(new_response, symbol, trading_day, new_started, new_finished)
    shared = a.keys() & b.keys()
    result = {"schema": SCHEMA, "old_capture": old, "new_capture": new,
              "payload_changed": old["payload_sha256"] != new["payload_sha256"],
              "changed_labels": sum(a[k][0] != b[k][0] for k in shared),
              "added_labels": len(b.keys()-a.keys()),
              "absent_labels": len(a.keys()-b.keys()),
              "windows": _windows(a, b, old["scope"]),
              "clock_selected": None, "vendor_adjustment_revision": None,
              "source_first_known_attested": False, "source_coverage_attested": False,
              "price_basis_attested": False, "source_rights_attested": False,
              "absence_is_deletion": False, "signal_eligible": False,
              "production_cache_eligible": False}
    result["comparison_sha256"] = _digest(result)
    return result
