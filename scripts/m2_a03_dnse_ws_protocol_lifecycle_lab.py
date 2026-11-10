"""DNSE public WebSocket lifecycle negative QA; no real connection or secrets.

Implements only test-fixture control-message sequencing based on the public
client protocol. A synthetic auth_success or subscribe ACK is NOT issuer
authentication, market-data licensing, bar custody, or replay completeness.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

SCHEMA = "mst.a03.dnse-ws-client-lifecycle-documentation-synthetic.v1"
NO_GO = "DOCUMENTED_WEBSOCKET_PROTOCOL_SIMULATED_NO_LIVE_AUTHORITY"
SOURCE = "https://developers.dnse.com.vn/docs/sdk/build_websocket/"
CHANNELS = "ohlc.5.json|ohlc_closed.5.json"
MAX_AUTH_SECONDS = 30
MAX_CLOCK_SKEW_SECONDS = 300
MAX_PONG_SECONDS = 60
MAX_SESSION_SECONDS = 8 * 3600
CONTROL_KINDS = frozenset((
    "welcome", "auth", "auth_success", "subscribe", "subscribed",
    "forming_data", "closed_data", "ping", "pong", "connection_expired", "disconnect", "error",
))
CLOSE_CODES = frozenset(("1000", "1001", "1006", "1008", "1011", "1012", "1013"))
ERROR_CODES = frozenset(("AUTH_FAILED", "AUTH_TIMEOUT", "MAX_CONNECTIONS_EXCEEDED"))
INBOUND_CONTROL_ACTIONS = frozenset(("welcome", "auth_success", "subscribed",
    "unsubscribed", "ping", "pong", "connection_expired", "error"))

def classify_untrusted_inbound(payload: dict) -> str:
    """Shape only: known control action wins; other data may have action and T."""
    if type(payload) is not dict:
        raise TypeError("TYPED_INBOUND_DICT_REQUIRED")
    action = payload.get("action")
    if type(action) is str and action in INBOUND_CONTROL_ACTIONS:
        return "CONTROL_SHAPE_UNTRUSTED"
    if type(payload.get("T")) is str and payload["T"].strip():
        return "DATA_SHAPE_UNTRUSTED"
    return "UNKNOWN_SHAPE_UNTRUSTED"

def synthetic_backoff_seconds(attempt: int) -> int:
    """Public documented exponential sequence; no timers or reconnect calls."""
    if type(attempt) is not int or attempt < 0:
        raise ValueError("NONNEGATIVE_INTEGER_RETRY_INDEX_REQUIRED")
    return min(60, 2 ** min(attempt, 6))

@dataclass(frozen=True)
class ToyEvent:
    seconds: int
    kind: str
    detail: str = ""
    client_clock_seconds: int | None = None

def inspect_trace(events: tuple[ToyEvent, ...]) -> dict:
    """Strictly check imaginary client events, never initiate network I/O."""
    if type(events) is not tuple or not events:
        raise TypeError("NONEMPTY_IMMUTABLE_SYNTHETIC_TRACE_REQUIRED")
    state = "DISCONNECTED"
    observed_seconds = -1
    session_started = -1
    ping_at = None
    ping_token = None
    session_ids = set()
    auth_nonces = set()
    count = {k: 0 for k in CONTROL_KINDS}
    sessions = 0
    completed_heartbeat_roundtrips = 0
    proactive_pong_count = 0
    no_echo_pong_count = 0
    mismatched_echo_count = 0
    for e in events:
        if type(e) is not ToyEvent or type(e.seconds) is not int or e.seconds < 0:
            raise TypeError("EXACT_TYPED_MONOTONE_SYNTHETIC_EVENT_REQUIRED")
        if (type(e.kind) is not str or e.kind not in CONTROL_KINDS or
            type(e.detail) is not str):
            raise ValueError("KNOWN_CONTROL_EVENT_AND_STRING_DETAIL_REQUIRED")
        if e.seconds < observed_seconds:
            raise ValueError("LOCAL_OBSERVATION_CLOCK_REWIND")
        observed_seconds = e.seconds
        if e.kind != "auth" and e.client_clock_seconds is not None:
            raise ValueError("CLOCK_CLAIM_ONLY_ALLOWED_ON_FAKE_AUTH")
        if state != "DISCONNECTED":
            if (e.seconds - session_started > MAX_SESSION_SECONDS and
                e.kind not in ("connection_expired", "disconnect")):
                raise ValueError("EIGHT_HOUR_CONNECTION_LIMIT_NOT_RENEWAL")
            if (ping_at is not None and e.seconds - ping_at > MAX_PONG_SECONDS
                and e.kind != "disconnect"):
                raise ValueError("PONG_HEARTBEAT_DEADLINE_MISSED")
        count[e.kind] += 1
        if e.kind == "welcome":
            if state != "DISCONNECTED":
                raise ValueError("WELCOME_REQUIRES_NEW_DISCONNECTED_SESSION")
            if (not e.detail.startswith("toy-session-") or
                e.detail in session_ids):
                raise ValueError("FRESH_FAKE_WELCOME_SESSION_REQUIRED")
            session_ids.add(e.detail)
            sessions += 1
            session_started = e.seconds
            state = "WELCOMED"
        elif e.kind == "auth":
            if state != "WELCOMED":
                raise ValueError("AUTH_ONLY_AFTER_WELCOME")
            if e.seconds - session_started > MAX_AUTH_SECONDS:
                raise ValueError("AUTH_30_SECOND_DEADLINE_MISSED")
            if (type(e.client_clock_seconds) is not int or
                abs(e.seconds - e.client_clock_seconds) > MAX_CLOCK_SKEW_SECONDS):
                raise ValueError("AUTH_SYNTHETIC_CLOCK_SHAPE_OR_SKEW")
            if (not e.detail.startswith("toy-nonce-") or
                e.detail in auth_nonces):
                raise ValueError("FRESH_SYNTHETIC_NONCE_EVERY_AUTH_REQUIRED")
            auth_nonces.add(e.detail)
            state = "AUTH_SENT"
        elif e.kind == "auth_success":
            if state != "AUTH_SENT":
                raise ValueError("AUTH_SUCCESS_WITHOUT_PRIOR_FAKE_AUTH")
            if e.seconds - session_started > MAX_AUTH_SECONDS:
                raise ValueError("AUTH_SUCCESS_30_SECOND_DEADLINE_MISSED")
            state = "AUTHENTICATED_CLAIM"
        elif e.kind == "subscribe":
            if state != "AUTHENTICATED_CLAIM" or e.detail != CHANNELS:
                raise ValueError("BOTH_MST_M5_CHANNELS_AFTER_AUTH_REQUIRED")
            state = "SUBSCRIBE_SENT"
        elif e.kind == "subscribed":
            if state != "SUBSCRIBE_SENT":
                raise ValueError("SUBSCRIBED_ACK_REQUIRED_AFTER_SUBSCRIBE")
            state = "SUBSCRIBED_CLAIM"
        elif e.kind in ("forming_data", "closed_data"):
            if state != "SUBSCRIBED_CLAIM":
                raise ValueError("NO_STREAM_DATA_BEFORE_SUBSCRIPTION_ACK")
        elif e.kind == "ping":
            if state != "SUBSCRIBED_CLAIM" or ping_at is not None:
                raise ValueError("ONE_PENDING_SERVER_PING_PER_TOY_SESSION")
            if not e.detail.startswith("toy-ping-"):
                raise ValueError("FAKE_PING_TOKEN_REQUIRED")
            ping_at = e.seconds
            ping_token = e.detail
        elif e.kind == "pong":
            if state != "SUBSCRIBED_CLAIM":
                raise ValueError("PONG_ONLY_WHILE_SUBSCRIBED")
            # The official DNSE client document allows proactive PONG and
            # responses without echoed timestamps; echo only enables RTT.
            if ping_at is None:
                if e.detail:
                    raise ValueError("PROACTIVE_PONG_WITHOUT_PENDING_PING_NO_ECHO")
                proactive_pong_count += 1
            else:
                if e.seconds - ping_at > MAX_PONG_SECONDS:
                    raise ValueError("PONG_HEARTBEAT_DEADLINE_MISSED")
                if not e.detail:
                    no_echo_pong_count += 1
                elif e.detail != ping_token:
                    mismatched_echo_count += 1
                completed_heartbeat_roundtrips += 1
                ping_at = None
                ping_token = None
        elif e.kind == "connection_expired":
            if state != "SUBSCRIBED_CLAIM":
                raise ValueError("EXPIRY_ONLY_FOR_STREAMING_SESSION")
            state = "EXPIRED_CLAIM"
        elif e.kind == "error":
            if state == "DISCONNECTED" or e.detail not in ERROR_CODES:
                raise ValueError("SOURCE_DOCUMENT_ERROR_CONTROL_CODE_REQUIRED")
            state = "ERROR_CLAIM"
        elif e.kind == "disconnect":
            if state == "DISCONNECTED" or e.detail not in CLOSE_CODES:
                raise ValueError("DOCUMENTED_CLOSE_CODE_AND_ACTIVE_SESSION_REQUIRED")
            state = "DISCONNECTED"
            session_started = -1
            ping_at = None
            ping_token = None
    return {
        "schema": SCHEMA,
        "status": NO_GO,
        "public_protocol_reference": SOURCE,
        "imaginary_session_count": sessions,
        "fake_auth_attempts": count["auth"],
        "fake_subscribe_ack_count": count["subscribed"],
        "fake_closed_event_count": count["closed_data"],
        "fake_forming_event_count": count["forming_data"],
        "fake_heartbeat_roundtrips": completed_heartbeat_roundtrips,
        "fake_proactive_pongs": proactive_pong_count,
        "fake_pongs_without_echo": no_echo_pong_count,
        "fake_pong_echo_mismatches": mismatched_echo_count,
        "fake_error_controls": count["error"],
        "actual_doc_control_action_model_used": True,
        "ending_state": state,
        "synthetic_trace_only": True,
        "source_credentials_present": False,
        "real_websocket_opened": False,
        "source_issuer_authenticated": False,
        "historical_backfill_proven": False,
        "closed_delivery_completeness_proven": False,
        "real_m5_source_qualified": False,
        "google_drive_market_cache_enabled": False,
        "production_or_trading_authorized": False,
    }

def toy_trace() -> tuple[ToyEvent, ...]:
    E = ToyEvent
    return (
        E(0, "welcome", "toy-session-1"),
        E(1, "auth", "toy-nonce-1", 1),
        E(2, "auth_success"),
        E(3, "subscribe", CHANNELS),
        E(4, "subscribed"),
        E(5, "forming_data"), E(6, "closed_data"),
        E(180, "ping", "toy-ping-1"),
        E(181, "pong", "toy-ping-1"),
        E(240, "disconnect", "1008"),
        E(242, "welcome", "toy-session-2"),
        E(243, "auth", "toy-nonce-2", 243),
        E(244, "auth_success"),
        E(245, "subscribe", CHANNELS),
        E(246, "subscribed"),
        E(247, "closed_data"),
    )

def build() -> dict:
    result = inspect_trace(toy_trace())
    assert result["imaginary_session_count"] == 2
    assert result["fake_auth_attempts"] == 2
    assert result["fake_subscribe_ack_count"] == 2
    assert result["fake_closed_event_count"] == 2
    assert result["fake_heartbeat_roundtrips"] == 1
    assert result["fake_proactive_pongs"] == 0
    assert result["fake_error_controls"] == 0
    assert not result["source_issuer_authenticated"]
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    result["synthetic_receipt_sha256"] = sha256(payload.encode("ascii")).hexdigest()
    return result

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    result = build()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
