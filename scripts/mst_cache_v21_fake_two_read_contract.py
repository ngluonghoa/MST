#!/usr/bin/env python3
"""MST Cache V2.1 offline TWO-read synthetic fixture contract.

No external SDK, no network, no OAuth, no Drive files, no source prices.
This is an explicitly NON-PRODUCTION in-memory model to establish QA gates.
In particular the simulated CAS is not a claim about Google Drive atomicity.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

PREFIX = "MST_FAKE_CACHE_V21"
SCHEMA = "mst-fake-cache-v2.1"
MAX_SAMPLES = 40


class SyntheticDenied(ValueError):
    """Closed validation errors with no secrets or raw payloads."""


def canonical(obj: Any) -> bytes:
    """Deterministic strict UTF-8 JSON; never allow floating non-finites."""
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SyntheticDenied("FAKE_NONCANONICAL_JSON") from None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_fake(fixture: Any) -> dict:
    """Deny anything outside a three-field, non-market fixture schema."""
    if type(fixture) is not dict or set(fixture) != {"fixture_only", "label", "samples"}:
        raise SyntheticDenied("FAKE_FIXTURE_SCHEMA_REQUIRED")
    if fixture["fixture_only"] is not True:
        raise SyntheticDenied("FAKE_FIXTURE_MUST_BE_EXPLICIT")
    label = fixture["label"]
    if type(label) is not str or not 1 <= len(label) <= 64 or not label.isascii():
        raise SyntheticDenied("FAKE_ASCII_LABEL_REQUIRED")
    if not label.startswith("FICTIONAL_") or any(
        not (c.isupper() or c.isdigit() or c == "_") for c in label
    ):
        raise SyntheticDenied("FAKE_LABEL_NAMESPACE_REQUIRED")
    samples = fixture["samples"]
    if type(samples) is not list or not 1 <= len(samples) <= MAX_SAMPLES:
        raise SyntheticDenied("FAKE_SAMPLES_BOUNDED")
    if any(type(v) is not int or not -100000 <= v <= 100000 for v in samples):
        raise SyntheticDenied("FAKE_INTEGER_SAMPLES_ONLY")
    return {"fixture_only": True, "label": label, "samples": list(samples)}


@dataclass(frozen=True)
class Pointer:
    revision: int = 0
    generation: int = 0
    manifest_sha256: str = "GENESIS"


class FakeDrive:
    """In-memory representation, NOT a Google Drive API implementation."""

    def __init__(self) -> None:
        self._chunks: dict[str, bytes] = {}
        self.pointer = Pointer()
        self.read_count = 0
        self.write_count = 0
        self.replay_mutation_after_first_read: bytes | None = None

    def put_chunk_immutable(self, key: str, payload: bytes) -> None:
        if key in self._chunks:
            if self._chunks[key] != payload:
                raise SyntheticDenied("FAKE_IMMUTABLE_KEY_COLLISION")
            return
        self._chunks[key] = payload
        self.write_count += 1

    def read_chunk(self, key: str) -> bytes:
        if key not in self._chunks:
            raise SyntheticDenied("FAKE_CHUNK_NOT_FOUND")
        self.read_count += 1
        data = self._chunks[key]
        if self.read_count == 1 and self.replay_mutation_after_first_read is not None:
            self._chunks[key] = self.replay_mutation_after_first_read
        return data

    def compare_and_swap_pointer(self, expected: Pointer, replacement: Pointer) -> None:
        if self.pointer != expected:
            raise SyntheticDenied("FAKE_POINTER_REVISION_CONFLICT")
        if replacement.revision != expected.revision + 1:
            raise SyntheticDenied("FAKE_POINTER_REVISION_NOT_INCREMENTAL")
        if replacement.generation <= expected.generation:
            raise SyntheticDenied("FAKE_GENERATION_ROLLBACK")
        self.pointer = replacement
        self.write_count += 1


def two_readback_verified(store: FakeDrive, key: str, expected_sha256: str) -> None:
    if type(expected_sha256) is not str or len(expected_sha256) != 64:
        raise SyntheticDenied("FAKE_SHA256_REQUIRED")
    first = store.read_chunk(key)
    second = store.read_chunk(key)
    if first != second or digest(first) != expected_sha256:
        raise SyntheticDenied("FAKE_TWO_READBACK_INTEGRITY_FAILURE")


def commit_fake(
    store: FakeDrive, fixture: Any, *,
    expected_pointer: Pointer,
    next_generation: int,
) -> dict[str, Any]:
    """Prepare immutable JSON, two independent reads and in-memory pointer CAS.

    A failed in-memory CAS may leave an orphan fake chunk (fail closed).
    There is no real HTTP request, and no signed independent highwater ledger.
    """
    if type(store) is not FakeDrive or type(expected_pointer) is not Pointer:
        raise SyntheticDenied("FAKE_STORE_AND_POINTER_REQUIRED")
    if type(next_generation) is not int or not 1 <= next_generation <= 1000000000:
        raise SyntheticDenied("FAKE_GENERATION_BOUNDED")
    if store.pointer != expected_pointer:
        raise SyntheticDenied("FAKE_STALE_POINTER_REJECTED")
    if next_generation <= expected_pointer.generation:
        raise SyntheticDenied("FAKE_GENERATION_ROLLBACK")
    safe = validate_fake(fixture)
    payload = canonical({"schema": SCHEMA, "data": safe})
    sha = digest(payload)
    key = PREFIX + "/CHUNKS/" + sha + ".json"
    manifest_bytes = canonical({
        "schema": SCHEMA,
        "chunk_sha256": sha,
        "generation": next_generation,
        "previous_manifest_sha256": expected_pointer.manifest_sha256,
        "previous_revision": expected_pointer.revision,
        "synthetic_only": True,
    })
    store.put_chunk_immutable(key, payload)
    two_readback_verified(store, key, sha)
    # Prevent a writer from swapping the pointer while two reads were done.
    if store.pointer != expected_pointer:
        raise SyntheticDenied("FAKE_CONCURRENT_POINTER_CHANGE")
    replacement = Pointer(
        revision=expected_pointer.revision + 1,
        generation=next_generation,
        manifest_sha256=digest(manifest_bytes),
    )
    store.compare_and_swap_pointer(expected_pointer, replacement)
    if store.pointer != replacement:
        raise SyntheticDenied("FAKE_POINTER_READBACK_FAILED")
    return {
        "status": "MST_FAKE_CACHE_V21_TWO_READ_CAS_PASS",
        "fixture_only": True,
        "chunk_digest_verified_twice": True,
        "simulated_generation": replacement.generation,
        "simulated_pointer_revision": replacement.revision,
        "simulated_immutable_chunk_count": len(store._chunks),
        "google_drive_called": False,
        "google_drive_cache_written": False,
        "market_provider_called": False,
        "real_ohlcv_present": False,
        "real_google_drive_cas_proven": False,
        "trusted_external_highwater_proven": False,
        "source_licenses_proven": False,
        "production_cache_activated": False,
    }
