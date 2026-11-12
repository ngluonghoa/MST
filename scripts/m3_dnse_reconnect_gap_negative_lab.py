"""MST M3 DNSE reconnect/closed-stream continuity NEGATIVE lab.

Offline, typed, metadata-only and deliberately SYNTHETIC. This is not a
WebSocket client, server authentication, gap recovery, data licence, trusted
first-known record, historical replay or a market cache. A connected session
and even adjacent candle-start labels cannot prove there was no missed data.
"""
from __future__ import annotations

from enum import Enum
import re

from scripts.m3_dnse_documented_closed_channel import (
    DnseChannelKind, UntrustedDnseWsMetadata, examine,
)

_SYN_SESSION = re.compile(r"^SYN-SESSION-[A-Z0-9]{1,16}$")
_SYN_NONCE = re.compile(r"^SYN-NONCE-[A-Z0-9]{1,16}$")
_SYN_TAG = re.compile(r"^SYN-DIGEST-[A-Z0-9]{1,16}$")
_RESOLUTIONS = {"5": 300, "15": 900, "30": 1800, "1H": 3600}
_MAX_SLOTS = 512


class Phase(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    NEED_WELCOME = "NEED_WELCOME"
    NEED_AUTH_ACK = "NEED_AUTH_ACK"
    NEED_SUBSCRIBED_ACK = "NEED_SUBSCRIBED_ACK"
    RECEIVE_CANDIDATES = "RECEIVE_CANDIDATES"
    QUARANTINED = "QUARANTINED"


class SyntheticDnseContinuity:
    """Bounded negative oracle; never grants actual source/Cache authority."""

    def __init__(self, *, channel: str):
        if type(channel) is not str:
            raise TypeError("EXACT_CHANNEL_STRING_REQUIRED")
        match = re.fullmatch(r"ohlc_closed\.(5|15|30|1H)\.(json|msgpack)", channel)
        if match is None:
            raise ValueError("DOCUMENTED_CLOSED_FIXED_INTRADAY_CHANNEL_ONLY")
        self.channel = channel
        self.resolution = match.group(1)
        self.interval_seconds = _RESOLUTIONS[self.resolution]
        self.phase = Phase.DISCONNECTED
        self.epoch = 0
        self._session_ids: set[str] = set()
        self._nonce_markers: set[str] = set()
        self._seen: dict[int, str] = {}
        self._last_new_start: int | None = None
        self._gap_count = 0
        self._duplicates = 0
        self._conflicts = 0
        self._out_of_order = 0
        self._clock_warnings = 0
        self._disconnections = 0
        self._epoch_gap_unknown = False

    def connect(self) -> int:
        if self.phase is not Phase.DISCONNECTED:
            raise PermissionError("DISCONNECT_REQUIRED_BEFORE_NEW_EPOCH")
        self.epoch += 1
        if self.epoch > 1:
            self._epoch_gap_unknown = True
        self.phase = Phase.NEED_WELCOME
        return self.epoch

    def welcome(self, *, epoch: int, synthetic_session_id: str) -> None:
        self._check_epoch(epoch, Phase.NEED_WELCOME)
        if (type(synthetic_session_id) is not str or
                not _SYN_SESSION.fullmatch(synthetic_session_id) or
                synthetic_session_id in self._session_ids):
            raise PermissionError("FRESH_SYNTHETIC_SESSION_ID_REQUIRED")
        self._session_ids.add(synthetic_session_id)
        self.phase = Phase.NEED_AUTH_ACK

    def auth_ack(self, *, epoch: int, synthetic_nonce_marker: str) -> None:
        self._check_epoch(epoch, Phase.NEED_AUTH_ACK)
        if (type(synthetic_nonce_marker) is not str or
                not _SYN_NONCE.fullmatch(synthetic_nonce_marker) or
                synthetic_nonce_marker in self._nonce_markers):
            raise PermissionError("FRESH_SYNTHETIC_NONCE_MARKER_REQUIRED")
        self._nonce_markers.add(synthetic_nonce_marker)
        self.phase = Phase.NEED_SUBSCRIBED_ACK

    def subscribed_ack(self, *, epoch: int, channel: str) -> None:
        self._check_epoch(epoch, Phase.NEED_SUBSCRIBED_ACK)
        if type(channel) is not str or channel != self.channel:
            raise PermissionError("EXACT_CLOSED_CHANNEL_RESUBSCRIPTION_REQUIRED")
        self.phase = Phase.RECEIVE_CANDIDATES

    def disconnect(self, *, epoch: int, close_code: int) -> None:
        if type(epoch) is not int or epoch != self.epoch or self.phase is Phase.DISCONNECTED:
            raise PermissionError("ACTIVE_EPOCH_REQUIRED_FOR_DISCONNECT")
        if type(close_code) is not int or not 1000 <= close_code <= 4999:
            raise ValueError("EXPLICIT_WEBSOCKET_CLOSE_CODE_REQUIRED")
        self._disconnections += 1
        self._epoch_gap_unknown = True
        self.phase = Phase.DISCONNECTED

    def ingest(self, *, epoch: int, message: UntrustedDnseWsMetadata,
               synthetic_digest_tag: str) -> str:
        self._check_epoch(epoch, Phase.RECEIVE_CANDIDATES)
        if type(message) is not UntrustedDnseWsMetadata:
            raise TypeError("TYPED_CLOSED_ENVELOPE_REQUIRED")
        if (message.channel != self.channel or message.kind is not DnseChannelKind.CLOSED
                or message.payload_resolution != self.resolution):
            raise PermissionError("FORMING_OR_OTHER_CHANNEL_CANNOT_ENTER_CLOSED_LEDGER")
        if type(synthetic_digest_tag) is not str or not _SYN_TAG.fullmatch(synthetic_digest_tag):
            raise ValueError("FIXTURE_ONLY_SYNTHETIC_DIGEST_TAG_REQUIRED")
        inspection = examine(message)
        if inspection["clock_order_warning"]:
            self._clock_warnings += 1
            self.phase = Phase.QUARANTINED
            return "CLIENT_CLOCK_SKEW_QUARANTINE"
        start = message.bar_time_seconds
        if start in self._seen:
            if self._seen[start] == synthetic_digest_tag:
                self._duplicates += 1
                return "IDENTICAL_DUPLICATE_UNTRUSTED"
            self._conflicts += 1
            self.phase = Phase.QUARANTINED
            return "CONFLICTING_CLOSED_SLOT_QUARANTINE"
        if self._last_new_start is not None and start < self._last_new_start:
            self._out_of_order += 1
            self.phase = Phase.QUARANTINED
            return "OUT_OF_ORDER_CLOSED_SLOT_QUARANTINE"
        if len(self._seen) >= _MAX_SLOTS:
            self.phase = Phase.QUARANTINED
            return "BOUNDED_METADATA_CAPACITY_QUARANTINE"
        if self._last_new_start is not None and (
                start - self._last_new_start > self.interval_seconds):
            # Calendar/no-trade/lunch can explain this. A candidate gap is not
            # proof that a real bar was missing, nor evidence of complete data.
            self._gap_count += 1
        self._seen[start] = synthetic_digest_tag
        self._last_new_start = start
        return "UNVERIFIED_CLOSED_CHANNEL_SLOT_ONLY"

    def authorize_replay(self) -> None:
        raise PermissionError("NO_VENDOR_SIGNED_BACKFILL_OR_SOURCE_RIGHTS_PROVEN")

    def report(self) -> dict[str, object]:
        return {
            "schema": "mst.m3.dnse.synthetic.reconnect-gap-negative.v1",
            "phase": self.phase.value,
            "synthetic_epoch": self.epoch,
            "synthetic_slots_seen": len(self._seen),
            "potential_calendar_or_delivery_gap_count": self._gap_count,
            "same_slot_duplicate_count": self._duplicates,
            "same_slot_conflict_count": self._conflicts,
            "out_of_order_count": self._out_of_order,
            "client_clock_warnings": self._clock_warnings,
            "disconnect_count": self._disconnections,
            "reconnect_delivery_history_unverified": self._epoch_gap_unknown,
            "server_gap_replay_documented": False,
            "transport_epoch_is_vendor_authenticated": False,
            "source_last_updated_is_first_known": False,
            "reconciled_with_authorized_rest_backfill": False,
            "official_calendar_or_no_trade_verified": False,
            "source_rights_and_retention_verified": False,
            "cache_publish_authorized": False,
            "signal_eligible": False,
            "production_authorized": False,
            "decision": "NO_GO_NO_TRUSTED_CONTINUITY_OR_FIRST_KNOWN",
        }

    def _check_epoch(self, epoch: int, required: Phase) -> None:
        if type(epoch) is not int or epoch != self.epoch or self.phase is not required:
            raise PermissionError("CURRENT_EPOCH_AND_EXACT_PROTOCOL_PHASE_REQUIRED")
