"""§241 fictional SSI->Drive manual staging integration, offline only."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from scripts.mst_ssi_retrieval_provenance import make_provenance
import json
from unittest import TestCase
from unittest.mock import patch

from scripts import mst_ssi_cloud_private_chunk241 as m
from scripts.mst_private_chunk_readback240 import PrivateUnpublishedChunk


ROOT = "MSTAppOwnedOAuthRoot00001"
CHUNKS = "MSTAppOwnedChunks00001"


def owner_env(**update):
    env = {
        **m.CHUNK_CONTEXT, "GITHUB_RUN_ID": "44600012345",
        "MST_SSI_READONLY_OWNER_ACCEPTED": "true",
        "MST_SSI_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_SOURCE_PROVIDER": "SSI",
        "MST_SSI_SYMBOL": "FPT",
        "MST_SOURCE_SYMBOL": "FPT",
        "MST_SOURCE_TF": "D1",
        "MST_SSI_FROM_DATE": "2026-11-17",
        "MST_SSI_TO_DATE": "2026-11-18",
        "MST_SSI_API_KEY": "fakekey",
        "MST_SSI_API_SECRET": "fake-secret-only",
        "MST_GDRIVE_OAUTH_CLIENT_ID": "fake-client-id",
        "MST_GDRIVE_OAUTH_CLIENT_SECRET": "fake-oauth-secret",
        "MST_GDRIVE_OAUTH_REFRESH_TOKEN": "fake-refresh",
        "MST_OAUTH_BOOTSTRAP_ACCEPTED": "false",
    }
    env.update(update)
    return env


def rows():
    return [{
        "symbol": "FPT", "tradingDate": "2026-11-17",
        "open": 52, "high": 54, "low": 51, "close": 53, "volume": 400,
    }]


def report():
    return {
        "provider": "SSI_FASTCONNECT_V3_MARKET_DATA",
        "private_retrieval_provenance": make_provenance(
            datetime(2026, 11, 19, 1, tzinfo=timezone.utc),
            datetime(2026, 11, 19, 1, 1, tzinfo=timezone.utc),
            symbol="FPT", tf="D1", first=date(2026, 11, 17),
            last=date(2026, 11, 18), rows=rows()),
        "source_native_tf": "D1",
        "native_source_rows_observed": 1,
        "source_ohlcv_invariants_verified": True,
        "private_data_stored_to_drive": False,
        "signal_eligible": False,
        "trading_or_broker_calls": 0,
    }


class Response:
    status_code = 200
    def __init__(self, body):
        self.body = body
    def json(self):
        return self.body


class FakeDiscovery:
    def __init__(self):
        self.calls = []
        self.root_shared = False
        self.child_shared = False
        self.ambiguous = False
        self.truncated = False
        self.child_wrong_parent = False
        self.unowned = False

    def get(self, url, *, params, timeout, allow_redirects):
        self.calls.append((url, params))
        assert url == m.DRIVE
        assert timeout == 25 and allow_redirects is False
        query = params["q"]
        is_root = "'root' in parents" in query
        name = "MST_OAUTH_CACHE_V1" if is_root else "CHUNKS"
        ident = ROOT if is_root else CHUNKS
        own_parent = "MyDriveRootID00001" if is_root else ROOT
        if not is_root and self.child_wrong_parent:
            own_parent = "UnrelatedRootID00001"
        item = {
            "id": ident, "name": name,
            "mimeType": m.FOLDER_MIME,
            "parents": [own_parent],
            "trashed": False,
            "shared": (self.root_shared if is_root else self.child_shared),
            "ownedByMe": not self.unowned,
            "isAppAuthorized": True,
        }
        return Response({
            "files": ([item, item] if self.ambiguous else [item]),
            "incompleteSearch": self.truncated,
            "nextPageToken": None,
        })


def saved_candidate(raw):
    return PrivateUnpublishedChunk(
        file_id="MSTPrivateFile00000001",
        sha256="a"*64,
        provider="SSI", symbol="FPT", native_tf="D1",
        bytes_verified=len(raw),
    )


class SsiManualSourceCloud241(TestCase):
    def test_end_to_end_wiring_uses_private_source_only_and_redacts_receipt(self):
        cloud, source = FakeDiscovery(), object()
        staged = []
        def record(session, forwarded, folder, payload):
            self.assertIs(session, cloud)
            self.assertEqual(folder, CHUNKS)
            self.assertEqual(forwarded["MST_PRIVATE_CHUNKS_FOLDER_ID"], CHUNKS)
            raw = json.loads(payload)
            self.assertEqual(raw["schema"], m.SCHEMA)
            self.assertEqual(raw["raw_native"], rows())
            self.assertIs(raw["eligible_for_signals"], False)
            self.assertEqual(set(raw), {
                "schema", "project", "provider", "symbol", "native_tf",
                "raw_native", "eligible_for_signals", "retrieval_provenance",
            })
            staged.append(payload)
            return saved_candidate(payload)

        with patch.object(m, "_fetch_ssi_native_once") as f, patch.object(
            m, "upload_private_unpublished_chunk", side_effect=record
        ) as w:
            f.return_value = (report(), rows())
            receipt = m.run_private_ssi_stage(source, cloud, owner_env())
        self.assertEqual(len(cloud.calls), 2)
        self.assertEqual(len(staged), 1)
        f.assert_called_once()
        self.assertIs(f.call_args.args[0], source)
        self.assertEqual(
            f.call_args.args[1]["MST_MFX_SOURCE_MODE"],
            "ssi-native-quarantine-stage",
        )
        w.assert_called_once()
        self.assertEqual(receipt["source_observed_rows"], 1)
        self.assertFalse(receipt["source_timestamp_semantics_attested"])
        self.assertFalse(receipt["vendor_corporate_action_basis_attested"])
        self.assertFalse(receipt["market_cache_promoted"])
        self.assertFalse(receipt["signals_or_trade_eligible"])
        for secret in ("fake-oauth-secret", "fake-secret-only", CHUNKS, ROOT,
                       "MSTPrivateFile00000001", '"open"'):
            self.assertNotIn(secret, json.dumps(receipt))

    def test_owner_rights_and_main_only_guards_block_before_network(self):
        for name, value in (
            ("GITHUB_REF", "refs/heads/not-main"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_REPOSITORY_ID", "0"),
            ("GITHUB_WORKFLOW_REF", "wrong-workflow"),
            ("MST_CHUNK_STAGE_CONFIRM", "NO"),
            ("MST_PRIVATE_CHUNKS_WRITE_ACCEPTED", "false"),
            ("MST_SOURCE_RETENTION_RIGHTS_CONFIRMED", "false"),
            ("MST_SSI_READONLY_OWNER_ACCEPTED", "false"),
            ("MST_SSI_SOURCE_RIGHTS_CONFIRMED", "false"),
            ("MST_SOURCE_PROVIDER", "DNSE"),
            ("MST_SOURCE_TF", "H4"),
            ("MST_SSI_SYMBOL", "VCB"),
            ("MST_SOURCE_SYMBOL", "HPG"),
            ("MST_OAUTH_BOOTSTRAP_ACCEPTED", "true"),
            ("MST_GDRIVE_OAUTH_REFRESH_TOKEN", ""),
            ("MST_SSI_TO_DATE", "not-a-date"),
            ("GITHUB_RUN_ID", "bad"),
        ):
            cloud = FakeDiscovery()
            with self.subTest(name=name), patch.object(
                m, "_fetch_ssi_native_once"
            ) as get_ohlc, patch.object(
                m, "upload_private_unpublished_chunk"
            ) as put, self.assertRaises((m.SsiStageDenied,)):
                m.run_private_ssi_stage(object(), cloud, owner_env(**{name: value}))
            self.assertEqual(cloud.calls, [])
            get_ohlc.assert_not_called()
            put.assert_not_called()

    def test_fake_private_folder_preflight_is_ownership_and_parent_scoped(self):
        for field in ("root_shared", "child_shared", "ambiguous",
                      "truncated", "child_wrong_parent", "unowned"):
            cloud = FakeDiscovery()
            setattr(cloud, field, True)
            with self.subTest(field=field), patch.object(
                m, "_fetch_ssi_native_once"
            ) as fetch, self.assertRaises(m.SsiStageDenied):
                m.run_private_ssi_stage(object(), cloud, owner_env())
            fetch.assert_not_called()

    def test_source_capture_count_and_false_authority_gate(self):
        wrong_reports = [
            {**report(), "provider": "SSI_BROKER_ORDERS"},
            {**report(), "source_native_tf": "H1"},
            {**report(), "native_source_rows_observed": 2},
            {**report(), "native_source_rows_observed": True},
            {**report(), "signal_eligible": True},
            {**report(), "trading_or_broker_calls": 1},
            {**report(), "private_data_stored_to_drive": True},
            {**report(), "source_ohlcv_invariants_verified": False},
        ]
        for bad in wrong_reports:
            with self.subTest(bad=bad), self.assertRaises(m.SsiStageDenied):
                m.source_envelope(bad, rows(), owner_env())
        self.assertRaises(m.SsiStageDenied, m.source_envelope,
                          report(), [], owner_env())
        self.assertRaises(m.SsiStageDenied, m.source_envelope,
                          report(), [{**rows()[0], "token":"oops"}], owner_env())

    def test_nonfinite_native_price_serialization_fails_closed(self):
        changed = deepcopy(rows())
        changed[0]["close"] = float("nan")
        with self.assertRaisesRegex(m.SsiStageDenied, "SOURCE_JSON_OR_TRANSPORT"):
            m.source_envelope(report(), changed, owner_env())

    def test_fail_unknown_provider_request_without_leak(self):
        cloud = FakeDiscovery()
        with patch.object(m, "_fetch_ssi_native_once") as fetch:
            fetch.side_effect = RuntimeError("PRIVATE_SSI_AUTH_TOKEN")
            with self.assertRaisesRegex(m.SsiStageDenied, "^MST_SSI_CLOUD_STAGE_UNEXPECTED_FAILURE$"):
                m.run_private_ssi_stage(object(), cloud, owner_env())

    def test_source_provider_scope_only_ssi(self):
        for provider in ("DNSE", "VCBS", "OTHER"):
            e = owner_env(MST_SOURCE_PROVIDER=provider)
            with self.subTest(provider=provider), self.assertRaises(m.SsiStageDenied):
                m.require_manual_source_stage(e)


if __name__ == "__main__":
    import unittest
    unittest.main()
