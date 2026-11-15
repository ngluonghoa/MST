"""Strict in-process source observation -> private staging binding.

A binding is formed in a GitHub workflow immediately after the existing
licensed vendor GET. Its hash identifies the *validated native payload*,
request window, provider, symbol, TF and run attempt. It is NOT a vendor
signature, original HTTP byte digest, venue-close attestation, license, CAS
or signal approval. The binding is private metadata, never stdout.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import re
from typing import Any, Mapping

from scripts.mst_native_source_fingerprint import native_canonical_sha256

SCHEMA = "mst.cloud.private_inprocess_source_binding.v0.1"
PROVIDERS = {
    "DNSE": {
        "mode": ("dnse-d1-quarantine-stage", "dnse-native-quarantine-stage"),
        "source": "DNSE_OFFICIAL_OPENAPI",
        "endpoint": "https://openapi.dnse.com.vn/price/ohlc",
        "symbol_key": "MST_DNSE_SYMBOL",
    },
    "SSI": {
        "mode": ("ssi-native-quarantine-stage",),
        "source": "SSI_FASTCONNECT_V3_MARKET_DATA",
        "endpoint": "https://api.ssi.com.vn/api/v3/data/ohlc",
        "symbol_key": "MST_SSI_SYMBOL",
    },
}
EXPECTED_KEYS = frozenset((
    "schema", "repository", "github_run_id", "github_run_attempt",
    "source", "source_endpoint", "symbol", "native_tf",
    "requested_window", "native_canonical_sha256", "row_count",
    "scope", "issuer_attested", "cache_publisher_authorized",
))


class SourceBindingDenied(ValueError):
    """Never include credentials, vendor responses or source prices."""


def _window(provider: str, env: Mapping[str, str]) -> dict[str, Any]:
    try:
        if provider == "DNSE":
            a = env["MST_DNSE_FROM_UNIX"]
            b = env["MST_DNSE_TO_UNIX"]
            if (type(a) is not str or type(b) is not str
                    or re.fullmatch(r"[1-9][0-9]{8,12}", a) is None
                    or re.fullmatch(r"[1-9][0-9]{8,12}", b) is None
                    or int(a) >= int(b)):
                raise ValueError("invalid unix window")
            return {"from_unix": int(a), "to_unix": int(b)}
        a, b = env["MST_SSI_FROM_DATE"], env["MST_SSI_TO_DATE"]
        if (type(a) is not str or type(b) is not str
                or re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", a) is None
                or re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", b) is None
                or date.fromisoformat(a) > date.fromisoformat(b)):
            raise ValueError("invalid date window")
        return {"from_date": a, "to_date": b}
    except (KeyError, ValueError, TypeError):
        raise SourceBindingDenied("MST_SOURCE_BINDING_WINDOW_INVALID") from None


def _native(provider: str, env: Mapping[str, str], raw: Any
            ) -> tuple[Any, int]:
    try:
        if provider == "DNSE":
            from scripts.mst_mfx_style_appowned_pipeline import validate_dnse_native
            window = _window(provider, env)
            summary = validate_dnse_native(
                raw, window["from_unix"], window["to_unix"],
                timeframe=env["MST_SOURCE_TF"],
            )
            return raw, summary["observed_native_rows"]
        from scripts.mst_ssi_native_stage import _normal_rows
        window = _window(provider, env)
        rows = _normal_rows(
            raw, symbol=env["MST_SSI_SYMBOL"], tf=env["MST_SOURCE_TF"],
            first=date.fromisoformat(window["from_date"]),
            last=date.fromisoformat(window["to_date"]),
        )
        return [rows[k] for k in sorted(rows)], len(rows)
    except SourceBindingDenied:
        raise
    except Exception:
        raise SourceBindingDenied("MST_SOURCE_BINDING_NATIVE_INVALID") from None


def make_source_binding(provider: str, env: Mapping[str, str],
                        native: Any) -> dict[str, Any]:
    """Bind source observation to source request/run, without any secret."""
    if provider not in PROVIDERS:
        raise SourceBindingDenied("MST_SOURCE_BINDING_PROVIDER_UNSUPPORTED")
    p = PROVIDERS[provider]
    tf, symbol = env.get("MST_SOURCE_TF", "D1"), env.get(p["symbol_key"])
    run = env.get("GITHUB_RUN_ID")
    if (env.get("GITHUB_REPOSITORY") != "ngluonghoa/MST"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("MST_MFX_SOURCE_MODE") not in p["mode"]
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or type(run) is not str
            or re.fullmatch(r"[1-9][0-9]{5,19}", run) is None
            or type(symbol) is not str
            or re.fullmatch(r"[A-Z]{3}", symbol) is None
            or tf not in ("D1", "M5", "M15", "M30", "H1")):
        raise SourceBindingDenied("MST_SOURCE_BINDING_RUN_OR_IDENTITY_INVALID")
    canonical, count = _native(provider, env, native)
    try:
        digest = native_canonical_sha256(provider, symbol, tf, canonical)
    except Exception:
        raise SourceBindingDenied("MST_SOURCE_BINDING_DIGEST_INVALID") from None
    return {
        "schema": SCHEMA,
        "repository": "ngluonghoa/MST",
        "github_run_id": run,
        "github_run_attempt": "1",
        "source": p["source"],
        "source_endpoint": p["endpoint"],
        "symbol": symbol,
        "native_tf": tf,
        "requested_window": _window(provider, env),
        "native_canonical_sha256": digest,
        "row_count": count,
        "scope": "IN_PROCESS_REQUEST_TO_PRIVATE_STAGE_UNATTESTED",
        "issuer_attested": False,
        "cache_publisher_authorized": False,
    }


def binding_sha256(binding: Any) -> str:
    if type(binding) is not dict or set(binding) != EXPECTED_KEYS:
        raise SourceBindingDenied("MST_SOURCE_BINDING_FIELD_SET_INVALID")
    try:
        payload = json.dumps(
            binding,sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode("utf-8")
        if len(payload) > 4096:
            raise ValueError("oversized binding")
        return hashlib.sha256(payload).hexdigest()
    except (TypeError, ValueError, OverflowError):
        raise SourceBindingDenied("MST_SOURCE_BINDING_JSON_INVALID") from None


def verify_source_binding(provider: str, env: Mapping[str, str],
                          native: Any, binding: Any) -> str:
    """Reject wrong/stale provider, request window, row body or run before POST."""
    expected = make_source_binding(provider, env, native)
    if type(binding) is not dict or binding != expected:
        raise SourceBindingDenied("MST_SOURCE_BINDING_INPROCESS_MISMATCH")
    return binding_sha256(binding)


def verify_archived_source_binding(archive: Mapping[str, Any],
                                   props: Mapping[str, Any]) -> bool:
    """Verify optional new-format binding after private Drive media readback.

    Older candidates have neither field and remain UNPUBLISHED. A partial,
    mismatched, forged-claims or invalid new-format receipt fails closed.
    """
    receipt = archive.get("source_ingress_binding")
    meta_sha = props.get("source_ingress_binding_sha256")
    if receipt is None and meta_sha is None:
        return False
    if (type(receipt) is not dict or set(receipt) != EXPECTED_KEYS
            or type(meta_sha) is not str
            or re.fullmatch(r"[0-9a-f]{64}", meta_sha) is None):
        raise SourceBindingDenied("MST_SOURCE_BINDING_ARCHIVE_FIELDS_INVALID")
    provider = next((k for k, v in PROVIDERS.items()
                     if v["source"] == archive.get("source")), None)
    if provider is None:
        raise SourceBindingDenied("MST_SOURCE_BINDING_ARCHIVE_PROVIDER_INVALID")
    window = ({"from_unix": archive.get("from_unix"),
               "to_unix": archive.get("to_unix")} if provider == "DNSE" else
              {"from_date": archive.get("from_date"),
               "to_date": archive.get("to_date")})
    expected = {
        "schema": SCHEMA,
        "repository": "ngluonghoa/MST",
        "github_run_id": props.get("source_run_id"),
        "github_run_attempt": "1",
        "source": PROVIDERS[provider]["source"],
        "source_endpoint": PROVIDERS[provider]["endpoint"],
        "symbol": archive.get("symbol"),
        "native_tf": archive.get("source_native_tf"),
        "requested_window": window,
        "native_canonical_sha256": archive.get("native_canonical_sha256"),
        "row_count": (len(archive.get("raw_native", {}).get("t", []))
                      if provider == "DNSE" else len(archive.get("raw_native", []))),
        "scope": "IN_PROCESS_REQUEST_TO_PRIVATE_STAGE_UNATTESTED",
        "issuer_attested": False,
        "cache_publisher_authorized": False,
    }
    if receipt != expected or meta_sha != binding_sha256(receipt):
        raise SourceBindingDenied("MST_SOURCE_BINDING_ARCHIVE_MISMATCH")
    return True
