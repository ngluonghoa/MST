"""M3 entitlement admission is a deny-only *offline* evidence preflight.

This test never fetches SSI, DNSE, VCBS, or other provider data and uses
invented docket IDs. A complete evidence-claim checklist is NOT authorization.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest

from swing_trading.v2_provider_readiness import (
    ClaimState, ProviderGate, ProviderReadinessV2, UnverifiedGateNoteV2,
    review_unverified_provider_docket,
)
from swing_trading.v2_source_adapter import FixtureSourceIdentityV2

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
EARLIER = NOW - timedelta(days=1)
LATER = NOW + timedelta(days=1)


def ident(provider="SSI", endpoint=None):
    return FixtureSourceIdentityV2(
        provider, endpoint or f"fixture.{provider.lower()}.d1",
    )


def note(gate, provider="SSI", state=ClaimState.UNVERIFIED, code=10000000,
         observed=EARLIER, expiry=None, endpoint=None):
    return UnverifiedGateNoteV2(
        provider, endpoint or f"fixture.{provider.lower()}.d1",
        gate, state, observed,
        None if state is ClaimState.MISSING else f"EVID-{code:08d}",
        expiry,
    )


def check(provider="SSI", notes=(), at=NOW):
    return review_unverified_provider_docket(ident(provider), notes, checked_at_utc=at)


class StrictAdmissionDenial(unittest.TestCase):
    def test_all_evidence_gates_absent_is_blocked(self):
        review = check()
        self.assertEqual(len(review.missing_gates), len(ProviderGate))
        self.assertEqual(review.gates_present, ())
        self.assertFalse(review.external_vendor_verification)
        self.assertFalse(review.live_transport_authorized)
        self.assertFalse(review.cloud_retention_authorized)
        self.assertFalse(review.backtest_authorized)
        self.assertFalse(review.trading_authorized)

    def test_even_all_ten_unverified_claims_never_grant_rights(self):
        entries = tuple(note(g, code=10000000 + i) for i, g in enumerate(ProviderGate))
        review = check(notes=entries)
        self.assertEqual(review.missing_gates, ())
        self.assertEqual(len(review.unverified_gates), len(ProviderGate))
        self.assertEqual(len(review.gates_present), len(ProviderGate))
        for key in (
            "external_vendor_verification", "live_transport_authorized",
            "cloud_retention_authorized", "backtest_authorized",
            "trading_authorized",
        ):
            with self.subTest(key=key):
                self.assertIs(getattr(review, key), False)

    def test_claim_notes_cannot_self_assert_verification(self):
        entry = note(ProviderGate.ACCOUNT_ENTITLEMENT)
        with self.assertRaises(FrozenInstanceError):
            entry.state = ClaimState.REVOKED
        self.assertFalse(hasattr(entry, "verified"))
        self.assertFalse(hasattr(entry, "access_token"))
        self.assertFalse(hasattr(entry, "raw_market_payload"))
        self.assertFalse(hasattr(entry, "agreement_body"))

    def test_untyped_claim_states_or_gates_rejected(self):
        with self.assertRaises(TypeError):
            UnverifiedGateNoteV2("SSI", "fixture.ssi.d1", "ACCOUNT_ENTITLEMENT", ClaimState.UNVERIFIED,
                                 EARLIER, "EVID-12345678")
        with self.assertRaises(TypeError):
            UnverifiedGateNoteV2("SSI", "fixture.ssi.d1", ProviderGate.ACCOUNT_ENTITLEMENT,
                                 "VERIFIED", EARLIER, "EVID-12345678")

    def test_no_arbitrary_urls_passwords_or_account_ids(self):
        for ref in (
            "https://example.org/terms", "TOKEN-abcdefgh", "EVID-short",
            "EVID-ABCDEFGH:SECRET", "EVID-abc12345", "EVID-12345678/subdir",
        ):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                replace(note(ProviderGate.ACCOUNT_ENTITLEMENT), evidence_ref=ref)

    def test_expired_or_revoked_docket_never_authorizes(self):
        revoked = note(ProviderGate.ACCOUNT_ENTITLEMENT, state=ClaimState.REVOKED)
        expiring = note(ProviderGate.CLOUD_RETENTION_RIGHTS, code=10000001,
                        expiry=EARLIER + timedelta(hours=1))
        result = check(notes=(revoked, expiring))
        self.assertIn(ProviderGate.ACCOUNT_ENTITLEMENT, result.expired_or_revoked_gates)
        self.assertIn(ProviderGate.CLOUD_RETENTION_RIGHTS, result.expired_or_revoked_gates)
        self.assertFalse(result.cloud_retention_authorized)

    def test_malformed_missing_claim_cannot_carry_artificial_rights(self):
        for ref in ("EVID-12345678", None):
            with self.subTest(ref=ref):
                if ref is None:
                    item = note(ProviderGate.ACCOUNT_ENTITLEMENT, state=ClaimState.MISSING)
                    self.assertIsNone(item.evidence_ref)
                else:
                    with self.assertRaises(ValueError):
                        UnverifiedGateNoteV2(
                            "SSI", "fixture.ssi.d1", ProviderGate.ACCOUNT_ENTITLEMENT,
                            ClaimState.MISSING, EARLIER, ref,
                        )

    def test_invalid_expiry_timeline_rejected(self):
        for end in (EARLIER, EARLIER - timedelta(seconds=1)):
            with self.subTest(end=end), self.assertRaises(ValueError):
                note(ProviderGate.ACCOUNT_ENTITLEMENT, expiry=end)

    def test_future_dated_claim_denied(self):
        entry = note(ProviderGate.ACCOUNT_ENTITLEMENT, observed=LATER)
        with self.assertRaisesRegex(ValueError, "Future-dated"):
            check(notes=(entry,))

    def test_duplicate_gate_is_refused_even_with_distinct_evidence(self):
        entries = (
            note(ProviderGate.ACCOUNT_ENTITLEMENT, code=10000001),
            note(ProviderGate.ACCOUNT_ENTITLEMENT, code=10000002),
        )
        with self.assertRaisesRegex(ValueError, "Duplicate requirement"):
            check(notes=entries)

    def test_reused_claim_reference_does_not_satisfy_two_permissions(self):
        entries = (
            note(ProviderGate.ACCOUNT_ENTITLEMENT, code=10000001),
            note(ProviderGate.READ_HISTORICAL_RIGHTS, code=10000001),
        )
        with self.assertRaisesRegex(ValueError, "Reused evidence"):
            check(notes=entries)

    def test_cross_provider_claim_cannot_be_reused(self):
        entry = note(ProviderGate.ACCOUNT_ENTITLEMENT, provider="DNSE")
        with self.assertRaisesRegex(ValueError, "CROSS_PROVIDER"):
            check("SSI", (entry,))
        self.assertEqual(check("DNSE", (entry,)).provider_id, "DNSE")

    def test_cross_endpoint_claim_cannot_be_reused(self):
        entry = note(ProviderGate.ACCOUNT_ENTITLEMENT, endpoint="fixture.ssi.intraday")
        with self.assertRaisesRegex(ValueError, "CROSS_PROVIDER_OR_ENDPOINT"):
            check("SSI", (entry,))

    def test_forged_provider_or_endpoint_identity_rejected(self):
        with self.assertRaises(ValueError):
            UnverifiedGateNoteV2("ssi", "fixture.ssi.d1", ProviderGate.ACCOUNT_ENTITLEMENT,
                                 ClaimState.UNVERIFIED, EARLIER, "EVID-12345678")
        with self.assertRaises(ValueError):
            UnverifiedGateNoteV2("SSI", "../tokens", ProviderGate.ACCOUNT_ENTITLEMENT,
                                 ClaimState.UNVERIFIED, EARLIER, "EVID-12345678")

    def test_untyped_or_unbounded_notes_rejected(self):
        for notes in ([], [note(ProviderGate.ACCOUNT_ENTITLEMENT)],
                      (object(),), "test", None):
            with self.subTest(notes=notes), self.assertRaises(TypeError):
                check(notes=notes)

    def test_timestamp_must_be_utc(self):
        naive = NOW.replace(tzinfo=None)
        nonutc = NOW.astimezone(timezone(timedelta(hours=7)))
        for bad in (naive, nonutc):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check(at=bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                note(ProviderGate.ACCOUNT_ENTITLEMENT, observed=bad)

    def test_missing_gate_does_not_erase_other_unverified_states(self):
        entries = (
            note(ProviderGate.ACCOUNT_ENTITLEMENT),
            note(ProviderGate.CLOUD_RETENTION_RIGHTS, state=ClaimState.MISSING),
        )
        result = check(notes=entries)
        self.assertIn(ProviderGate.ACCOUNT_ENTITLEMENT, result.unverified_gates)
        self.assertIn(ProviderGate.CLOUD_RETENTION_RIGHTS, result.missing_gates)
        self.assertFalse(result.live_transport_authorized)


class ReadinessReportTamperingTests(unittest.TestCase):
    def test_direct_empty_summary_cannot_claim_all_requirements_satisfied(self):
        original = check()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            replace(original, missing_gates=())

    def test_duplicate_or_contradictory_summary_gate_is_rejected(self):
        original = check()
        gate = ProviderGate.ACCOUNT_ENTITLEMENT
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            replace(original, missing_gates=(gate, gate))
        with self.assertRaisesRegex(ValueError, "contradictory"):
            replace(original, unverified_gates=(gate,))
        entry = note(gate)
        with self.assertRaisesRegex(ValueError, "contradictory"):
            replace(check(notes=(entry,)), gates_present=())

    def test_bad_summary_fields_and_scope_are_rejected(self):
        original = check()
        with self.assertRaises(TypeError):
            replace(original, missing_gates=[*original.missing_gates])
        with self.assertRaises(TypeError):
            replace(original, unverified_gates=("ACCOUNT_ENTITLEMENT",))
        with self.assertRaises(ValueError):
            replace(original, provider_id="ssi")
        with self.assertRaises(ValueError):
            replace(original, checked_at_utc=NOW.replace(tzinfo=None))

    def test_even_structurally_complete_forged_summary_grants_no_rights(self):
        all_gates = tuple(ProviderGate)
        forged = ProviderReadinessV2(
            "SSI", "fixture.ssi.d1", NOW,
            all_gates, (), all_gates, (),
        )
        self.assertEqual(forged.missing_gates, ())
        self.assertFalse(forged.external_vendor_verification)
        self.assertFalse(forged.live_transport_authorized)
        self.assertFalse(forged.cloud_retention_authorized)
        self.assertFalse(forged.backtest_authorized)
        self.assertFalse(forged.trading_authorized)


if __name__ == "__main__":
    unittest.main()
