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
    "forming_data", "closed_data", "ping", "pong", "expired", "disconnect",
))
CLOSE_CODES = frozenset(("1000", "1001", "1006", "1008", "1011", "1012", "1013"))

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
                e.kind not in ("expired", "disconnect")):
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
            if (state != "SUBSCRIBED_CLAIM" or ping_at is None or
                e.detail != ping_token):
                raise ValueError("PONG_MUST_ECHO_PENDING_FAKE_PING")
            if e.seconds - ping_at > MAX_PONG_SECONDS:
                raise ValueError("PONG_HEARTBEAT_DEADLINE_MISSED")
            ping_at = None
            ping_token = None
        elif e.kind == "expired":
            if state != "SUBSCRIBED_CLAIM":
                raise ValueError("EXPIRY_ONLY_FOR_STREAMING_SESSION")
            state = "EXPIRED_CLAIM"
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
        "fake_heartbeat_roundtrips": count["pong"],
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
