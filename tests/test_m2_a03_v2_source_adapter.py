"""M2/A03 isolated v2 provider fixture contracts and source-scope QA.

Entirely synthetic metadata. No actual market data, MCP connection, vendor
credentials, cache persistence, source entitlement, live broker, or network.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from swing_trading.engineering_contracts import PortDescriptor
from swing_trading.v2_source_adapter import (
    FixtureProbeReceiptV2, FixtureProbeRequestV2,
    FixtureSourceAdapterV2, FixtureSourceIdentityV2,
    FixtureSourceRegistryV2, synthetic_source_registry,
)

T0 = datetime(2026, 11, 9, tzinfo=timezone.utc)
PROVIDERS = ("SSI", "DNSE", "VCBS")


def identity(provider="SSI", version="2.0.0", endpoint=None):
    return FixtureSourceIdentityV2(
        provider, endpoint or f"fixture.{provider.lower()}.d1", version,
    )


def adapter(provider="SSI", version="2.0.0", endpoint=None):
    return FixtureSourceAdapterV2(identity(provider, version, endpoint))


def request(provider="SSI", endpoint=None, symbol="FAKE001", timeframe="D1"):
    return FixtureProbeRequestV2(
        provider, endpoint or f"fixture.{provider.lower()}.d1",
        symbol, timeframe, T0,
    )


def descriptor(provider="SSI", version="2.0.0", operations=("probe",)):
    return PortDescriptor("source.fixture_probe", version, provider, operations)


class IdentityAndRightsTests(unittest.TestCase):
    def test_three_explicit_legacy_provider_names_are_independent(self):
        registry = synthetic_source_registry()
        self.assertEqual(registry.providers, tuple(sorted(PROVIDERS)))
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                a = registry.resolve(provider, descriptor(provider))
                self.assertEqual(a.identity.provider_id, provider)
                self.assertEqual(a.descriptor.scope, provider)
                self.assertEqual(a.identity.endpoint_id, f"fixture.{provider.lower()}.d1")

    def test_all_receipts_are_unverified_and_have_no_authority(self):
        registry = synthetic_source_registry()
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                receipt = registry.probe(request(provider), descriptor(provider))
                self.assertEqual(receipt.provider_id, provider)
                self.assertEqual(receipt.endpoint_id, f"fixture.{provider.lower()}.d1")
                self.assertEqual(receipt.symbol, "FAKE001")
                self.assertEqual(receipt.state, "UNVERIFIED")
                self.assertIs(receipt.source_authorized, False)
                self.assertIs(receipt.retention_authorized, False)
                self.assertIs(receipt.trading_authorized, False)
                self.assertFalse(hasattr(receipt, "ohlcv"))
                self.assertFalse(hasattr(receipt, "raw_payload"))
                self.assertFalse(hasattr(receipt, "access_token"))

    def test_receipt_cannot_self_grant_authority_or_source_state(self):
        r = adapter().probe(request())
        for name in ("source_authorized", "retention_authorized", "trading_authorized"):
            with self.subTest(flag=name), self.assertRaises(PermissionError):
                replace(r, **{name: True})
            with self.subTest(flag=name + " type"), self.assertRaises(PermissionError):
                replace(r, **{name: 1})
        with self.assertRaises(PermissionError):
            replace(r, state="VERIFIED")
        with self.assertRaises(PermissionError):
            replace(r, state="DETECTED")
        with self.assertRaises(PermissionError):
            replace(r, state="AVAILABLE")

    def test_frozen_fixture_receipt_and_identity(self):
        r = adapter().probe(request())
        with self.assertRaises(FrozenInstanceError):
            r.provider_id = "DNSE"
        with self.assertRaises(FrozenInstanceError):
            identity().provider_id = "VCBS"

    def test_provider_id_exact_case_and_shape(self):
        for bad in ("ssi", "DnsE", "S", "", "SSI/VCBS", "SSI;DNSE", 1, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                FixtureSourceIdentityV2(bad, "fixture.bad.d1")

    def test_endpoint_is_an_explicit_nonsecret_fixture(self):
        for bad in ("", "https://provider.example/path", "../token", "SSI.ACCESS", None, 5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                FixtureSourceIdentityV2("SSI", bad)

    def test_metadata_request_validates_ticker_and_timeframe(self):
        for bad in ("fake001", "../secret", "FAKE/001", "", None, 99):
            with self.subTest(symbol=bad), self.assertRaises(ValueError):
                FixtureProbeRequestV2("SSI", "fixture.ssi.d1", bad, "D1", T0)
        for bad in ("M1", "W1", "random", "", None, 100):
            with self.subTest(timeframe=bad), self.assertRaises(ValueError):
                FixtureProbeRequestV2("SSI", "fixture.ssi.d1", "FAKE001", bad, T0)

    def test_naive_and_offset_time_denied(self):
        for bad in (
            T0.replace(tzinfo=None),
            T0.astimezone(timezone(timedelta(hours=7))),
            "2026-11-09T00:00:00Z",
        ):
            with self.subTest(timestamp=bad), self.assertRaises((TypeError, ValueError)):
                FixtureProbeRequestV2("SSI", "fixture.ssi.d1", "FAKE001", "D1", bad)

    def test_non_v2_major_cannot_register(self):
        reg = FixtureSourceRegistryV2()
        for version in ("1.9.9", "3.0.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                reg.register(adapter(version=version))
        self.assertEqual(reg.providers, ())

    def test_invalid_port_version_cannot_claim_equivalence(self):
        for bad in ("2.0", "2.0.0-dev", "02.0.0"):
            with self.subTest(version=bad), self.assertRaises(ValueError):
                identity(version=bad)


class SourceIsolationTests(unittest.TestCase):
    def test_wrong_provider_never_implicitly_falls_back(self):
        registry = synthetic_source_registry()
        with self.assertRaises(ValueError):
            registry.probe(request("DNSE"), descriptor("SSI"))
        with self.assertRaises(KeyError):
            registry.probe(request("FOURTH"), descriptor("FOURTH"))
        self.assertEqual(registry.providers, tuple(sorted(PROVIDERS)))

    def test_wrong_provider_cannot_call_other_adapter(self):
        a = adapter("SSI")
        with self.assertRaisesRegex(ValueError, "PROVIDER_ISOLATION"):
            a.probe(request("DNSE"))
        self.assertEqual(a.identity.provider_id, "SSI")

    def test_wrong_endpoint_cannot_be_silently_relabelled(self):
        a = adapter("SSI")
        with self.assertRaisesRegex(ValueError, "ENDPOINT_ISOLATION"):
            a.probe(request("SSI", endpoint="fixture.dnse.d1"))
        with self.assertRaisesRegex(ValueError, "ENDPOINT_ISOLATION"):
            a.probe(request("SSI", endpoint="fixture.ssi.intraday"))

    def test_wrong_contract_or_operation_is_rejected(self):
        reg = synthetic_source_registry()
        for desc in (
            PortDescriptor("different.source", "2.0.0", "SSI", ("probe",)),
            descriptor("SSI", operations=("query",)),
        ):
            with self.subTest(desc=desc), self.assertRaises(ValueError):
                reg.probe(request(), desc)

    def test_missing_scope_and_wrong_major_cannot_downgrade(self):
        reg = synthetic_source_registry()
        for d in (descriptor("VCBS"), descriptor("SSI", "1.0.0"),
                  descriptor("SSI", "3.0.0")):
            with self.subTest(d=d), self.assertRaises(ValueError):
                reg.resolve("SSI", d)

    def test_same_symbol_never_merges_receipt_namespaces(self):
        reg = synthetic_source_registry()
        receipts = [reg.probe(request(p), descriptor(p)) for p in PROVIDERS]
        self.assertEqual({r.symbol for r in receipts}, {"FAKE001"})
        self.assertEqual({r.provider_id for r in receipts}, set(PROVIDERS))
        self.assertEqual(len(set(receipts)), 3)

    def test_provider_future_n_is_opt_in_and_isolated(self):
        reg = synthetic_source_registry()
        with self.assertRaises(KeyError):
            reg.resolve("FOURTH", descriptor("FOURTH"))
        reg.register(adapter("FOURTH"))
        self.assertEqual(reg.providers, ("DNSE", "FOURTH", "SSI", "VCBS"))
        r = reg.probe(request("FOURTH"), descriptor("FOURTH"))
        self.assertEqual((r.provider_id, r.state), ("FOURTH", "UNVERIFIED"))
        with self.assertRaises(ValueError):
            reg.probe(request("FOURTH"), descriptor("VCBS"))

    def test_direct_untyped_probe_request_denied(self):
        with self.assertRaises(TypeError):
            adapter().probe({
                "provider_id": "SSI", "endpoint_id": "fixture.ssi.d1",
            })
        with self.assertRaises(TypeError):
            synthetic_source_registry().probe(request(), "SSI")


class RegistrySwapAndRollbackTests(unittest.TestCase):
    def test_duplicate_registration_requires_explicit_replace(self):
        reg = synthetic_source_registry()
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PROVIDER"):
            reg.register(adapter("SSI"))
        self.assertEqual(reg.providers, tuple(sorted(PROVIDERS)))

    def test_replacement_with_higher_minor_preserves_other_providers(self):
        reg = synthetic_source_registry()
        old_ssi = reg.resolve("SSI", descriptor("SSI"))
        old_dnse = reg.resolve("DNSE", descriptor("DNSE"))
        next_ssi = adapter("SSI", "2.1.0")
        reg.replace("SSI", next_ssi)
        self.assertIs(reg.resolve("SSI", descriptor("SSI")), next_ssi)
        self.assertIs(reg.resolve("DNSE", descriptor("DNSE")), old_dnse)
        self.assertNotEqual(old_ssi.identity.version, next_ssi.identity.version)

    def test_rollback_to_v2_baseline_allowed_without_newer_consumer(self):
        reg = synthetic_source_registry()
        old = reg.resolve("SSI", descriptor("SSI"))
        reg.bind_consumer("mst.demo", "SSI", descriptor("SSI"))
        reg.replace("SSI", adapter("SSI", "2.1.0"))
        reg.replace("SSI", old)
        self.assertIs(reg.resolve("SSI", descriptor("SSI")), old)

    def test_newer_pinned_consumer_prevents_rollback(self):
        reg = synthetic_source_registry()
        reg.replace("SSI", adapter("SSI", "2.1.0"))
        upgraded = descriptor("SSI", "2.1.0")
        reg.bind_consumer("mst.newclient", "SSI", upgraded)
        with self.assertRaisesRegex(ValueError, "INCOMPATIBLE_CONTRACT_VERSION"):
            reg.replace("SSI", adapter("SSI", "2.0.0"))
        self.assertEqual(reg.resolve("SSI", upgraded).identity.version, "2.1.0")

    def test_failed_wrong_provider_replace_is_atomic(self):
        reg = synthetic_source_registry()
        old = reg.resolve("SSI", descriptor("SSI"))
        for candidate in (
            adapter("DNSE"),
            adapter("SSI", endpoint="fixture.ssi.alternate"),
            adapter("SSI", "3.0.0"),
        ):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                reg.replace("SSI", candidate)
            self.assertIs(reg.resolve("SSI", descriptor("SSI")), old)

    def test_pinned_consumer_blocks_removal_and_detach_allows(self):
        reg = synthetic_source_registry()
        reg.bind_consumer("mst.preview", "SSI", descriptor("SSI"))
        with self.assertRaisesRegex(ValueError, "PROVIDER_HAS_ATTACHED_CONSUMERS"):
            reg.remove("SSI")
        reg.detach_consumer("mst.preview")
        reg.remove("SSI")
        self.assertEqual(reg.providers, ("DNSE", "VCBS"))

    def test_unknown_provider_and_consumer_must_fail(self):
        reg = synthetic_source_registry()
        with self.assertRaises(KeyError):
            reg.remove("FOURTH")
        with self.assertRaises(KeyError):
            reg.detach_consumer("mst.unknown")
        with self.assertRaises(KeyError):
            reg.replace("FOURTH", adapter("FOURTH"))

    def test_bad_consumer_id_and_duplicate_pin_fail(self):
        reg = synthetic_source_registry()
        with self.assertRaises(ValueError):
            reg.bind_consumer("Upper Name", "SSI", descriptor("SSI"))
        reg.bind_consumer("mst.preview", "SSI", descriptor("SSI"))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CONSUMER"):
            reg.bind_consumer("mst.preview", "DNSE", descriptor("DNSE"))

    def test_provider_removal_never_removes_other_provider(self):
        reg = synthetic_source_registry()
        reg.remove("SSI")
        self.assertEqual(reg.providers, ("DNSE", "VCBS"))
        self.assertEqual(
            reg.probe(request("VCBS"), descriptor("VCBS")).provider_id,
            "VCBS",
        )


if __name__ == "__main__":
    unittest.main()
