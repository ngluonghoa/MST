"""MST Cloud market-data timeframe contract; no H4 native provider claim.

SSI FastConnect V3 public OHLC and DNSE OpenAPI both document
5m/15m/30m/1h/1d, not a native H4 endpoint. H4 is NOT requested, forged or
silently resampled without venue session boundaries and closed-bar proof.
"""
from __future__ import annotations

from typing import Final

SOURCE_NATIVE_TFS: Final = {
    "M5": ("5m", "5", 300),
    "M15": ("15m", "15", 900),
    "M30": ("30m", "30", 1800),
    "H1": ("1h", "1H", 3600),
    "D1": ("1d", "1D", 86400),
}
UNSUPPORTED_NATIVE_TFS: Final = ("H4",)
SOURCE_CLOCK_TZ = "Asia/Ho_Chi_Minh"


class NativeTfDenied(ValueError):
    pass


def provider_resolution(provider: str, timeframe: str) -> str:
    if timeframe in UNSUPPORTED_NATIVE_TFS:
        raise NativeTfDenied("MST_NATIVE_H4_NOT_AVAILABLE_ON_PROVIDER")
    if timeframe not in SOURCE_NATIVE_TFS:
        raise NativeTfDenied("MST_UNKNOWN_OR_UNSUPPORTED_NATIVE_TF")
    if provider not in ("SSI", "DNSE"):
        raise NativeTfDenied("MST_UNVERIFIED_PROVIDER_NATIVE_TF")
    return SOURCE_NATIVE_TFS[timeframe][0 if provider == "SSI" else 1]


def source_tf_metadata(provider: str, timeframe: str) -> dict[str, object]:
    resolution = provider_resolution(provider, timeframe)
    return {
        "source_native_tf": timeframe,
        "provider_resolution": resolution,
        "provider_native_bar_interval_seconds": SOURCE_NATIVE_TFS[timeframe][2],
        "H4_venue_session_aggregation_proven": False,
        "source_closed_bar_attestation_proven": False,
        "provider_marketdata_rights_verified": False,
        "trade_signal_eligible": False,
    }
