"""§327 private connected M1 same-slot cumulative prefix diagnostics.

Neither calendar/clock nor historical first-known or source rights are
established here. This does not calculate RVOL, authorize a cache or construct
qualified TODCumulativeObservation instances.
"""
from datetime import date
from scripts.mst_connected_m1_dependencies300 import (
    _capture, _digest, M1DependencyDenied,
)
from swing_trading.hose_session_geometry210 import (
    REGULAR_WINDOWS, MinuteLabelMeaning211,
)

SCHEMA = "mst.private.ssi_rvol_tod20_prefix_coverage.v0.1"
TFS = (("M1", 1), ("M5", 5), ("M15", 15))
CAPTURE_FIELDS = {"day", "response", "started", "finished"}


def inspect_private_tod20_prefix_coverage(*, symbol, target_day,
                                          prior_days, captures):
    """Use exactly the explicitly supplied 20 prior dates plus target.

    Dates are caller-observed D1 anchors, NOT an approved market calendar.
    Every capture is recomputed, never replaced with another date or revision.
    Full continuous prefix includes previous session segment(s); lunch and
    auction labels are excluded. Both label hypotheses remain unselected.
    """
    if (type(target_day) is not date or type(prior_days) is not tuple
            or len(prior_days) != 20
            or any(type(d) is not date for d in prior_days)
            or any(a >= b for a, b in zip(prior_days, prior_days[1:]))
            or prior_days[-1] >= target_day
            or type(captures) is not tuple or len(captures) != 21):
        raise M1DependencyDenied("MST_327_EXACT_PRIOR_SCOPE_REQUIRED")
    dates = (*prior_days, target_day)
    receipts = []
    observed = []
    for day, capture in zip(dates, captures):
        if (type(capture) is not dict or set(capture) != CAPTURE_FIELDS
                or type(capture["day"]) is not date or capture["day"] != day):
            raise M1DependencyDenied("MST_327_CAPTURE_SCOPE_MISMATCH")
        receipt, rows = _capture(capture["response"], symbol, day,
                                 capture["started"], capture["finished"])
        receipts.append(receipt)
        observed.append(set(rows))
    groups = []
    for meaning in MinuteLabelMeaning211:
        shift = int(meaning is MinuteLabelMeaning211.END_UNVERIFIED)
        for tf, step in TFS:
            slots = []
            previous_segments = ()
            for lo, hi, session in REGULAR_WINDOWS:
                for start in range(lo, hi-step+1, step):
                    end = start + step
                    labels = set(range(start+shift, end+shift))
                    prefix = set(previous_segments) | set(range(lo+shift, end+shift))
                    prior_local = sum(labels <= p for p in observed[:-1])
                    prior_prefix = sum(prefix <= p for p in observed[:-1])
                    target_local = labels <= observed[-1]
                    target_prefix = prefix <= observed[-1]
                    slots.append({
                        "session": session, "start_minute": start,
                        "end_minute": end, "expected_prefix_labels": len(prefix),
                        "prior_local_full_count": prior_local,
                        "prior_prefix_full_count": prior_prefix,
                        "target_local_full": target_local,
                        "target_prefix_full": target_prefix,
                        "local_21_observations": prior_local == 20 and target_local,
                        "prefix_21_observations": prior_prefix == 20 and target_prefix,
                    })
                previous_segments += tuple(range(lo+shift, hi+shift))
            groups.append({
                "clock": meaning.value, "tf": tf,
                "slots": slots, "slot_count": len(slots),
                "local_21_count": sum(s["local_21_observations"] for s in slots),
                "prefix_21_count": sum(s["prefix_21_observations"] for s in slots),
            })
    result = {
        "schema": SCHEMA, "symbol": symbol,
        "target_day": target_day.isoformat(),
        "prior_observed_days": [d.isoformat() for d in prior_days],
        "captures": receipts, "groups": groups,
        "clock_selected": None, "calendar_attested": False,
        "source_coverage_attested": False, "source_rights_attested": False,
        "source_first_known_attested": False, "price_basis_attested": False,
        "volume_definition_attested": False, "missing_is_zero": False,
        "rvol_calculation_authorized": False, "production_cache_eligible": False,
        "signal_eligible": False,
    }
    result["coverage_sha256"] = _digest(result)
    return result
