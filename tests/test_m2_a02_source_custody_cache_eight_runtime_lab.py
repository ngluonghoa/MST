"""A02 2nd group: actual original V1 source rights, custody and cache runtime.

All keys ephemeral, all market responses fabricated; no independent signer,
real licensed market data, Google Drive API, production access or trading.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.m2_a02_source_custody_cache_eight_runtime_lab import (
    BASE, EIGHT, SCHEMA, _custody, _event, _pin, _public,
    evaluate_source_custody_cache_matrix,
)
from scripts.m2_a02_incremental_cache_oracle_lab import bar, identity
from swing_trading.native_minute_bar_source_plan import BarProduct
from swing_trading.provider_rights_review import (
    EvidenceKind, RightsScope, UnverifiedRightsClaim,
    review_unverified_source_claims, require_authorized_source,
)
from swing_trading.source_capability_evidence import (
    ProbeEndpoint, ProbeState, summarize_source_capability,
    audit_backtest_evidence,
)
from swing_trading.provider_signed_event_chain import (
    EventKind, RightsChainState, verify_pinned_rights_event_chain,
    require_rights_chain_authorization,
)
from swing_trading.provider_head_custody import (
    CustodyRejected, audit_conditional_custody_head,
    require_authenticated_provider_rights,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore
from swing_trading.reference_journal import ReferenceJournal, ZERO
from swing_trading.reference_journal_recovery import (
    create_candidate_journal_checkpoint, verify_journal_backup_against_pinned,
    restore_journal_from_pinned,
)
from swing_trading.cache_snapshot_bundle import (
    create_fixture_snapshot, verify_fixture_snapshot, restore_fixture_snapshot,
    require_approved_cache_transport,
)
from swing_trading.partition_chunk_cache import (
    PartitionWrite, SyntheticDrivePartitionIndex,
    require_real_market_cache_transport, encode_fixture_chunk,
    decode_fixture_chunk,
)


def rights_claim(**kwargs):
    values=dict(
        product=BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
        evidence_id="EVID-2026RIGHT1",
        kind=EvidenceKind.ACCOUNT_ENTITLEMENT_CLAIM,
        recorded_at_utc=BASE-timedelta(minutes=5),
        scope_claims=tuple(RightsScope),
        contract_version_claim="SIM1",
        maximum_retention_days_claim=30,
        claimed_expiry_utc=BASE+timedelta(days=1),
    )
    values.update(kwargs)
    return UnverifiedRightsClaim(**values)


def signed_chain():
    evkey=Ed25519PrivateKey.generate()
    custkey=Ed25519PrivateKey.generate()
    event=_event(evkey,number=1,previous="0"*64,
                 kind=EventKind.GRANT_CANDIDATE)
    cust,head,floor,issued=_custody(_public(evkey),custkey,(event,))
    pin=_pin((event,),_public(evkey),issued)
    return evkey,custkey,event,cust,head,floor,pin


class SecondEightOriginalRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=evaluate_source_custody_cache_matrix()

    def test_all_eight_distinct_original_modules_exec(self):
        self.assertEqual(self.receipt["executed_count"],8)
        self.assertEqual(len(set(self.receipt["executed_original_modules"])),8)
        self.assertEqual(self.receipt["executed_original_modules"],list(EIGHT))

    def test_schema_and_no_go(self):
        self.assertEqual(self.receipt["schema"],SCHEMA)
        self.assertIn("PRODUCTION_NO_GO",self.receipt["status"])

    def test_exact_eight_business_scenarios(self):
        self.assertEqual(self.receipt["scenario_count"],8)
        self.assertEqual(len(self.receipt["scenarios"]),8)

    def test_all_eight_scenarios_pass(self):
        self.assertTrue(all(self.receipt["scenarios"].values()))

    def test_report_receipt_stable_without_exported_keys(self):
        self.assertEqual(len(self.receipt["scenario_receipt_sha256"]),64)
        self.assertNotIn("private_key",self.receipt)
        self.assertNotIn("public_key",self.receipt)

    def test_two_ephemeral_keys_dont_count_as_independent_vendor_roots(self):
        self.assertTrue(self.receipt["scenarios"]["two_ephemeral_signatures_not_independent_vendor_root"])
        self.assertFalse(self.receipt["two_independently_controlled_real_signers"])

    def test_no_production_admissions_even_with_green_crypto(self):
        for name in (
            "actual_private_source_identity_or_vendor_auth",
            "two_independently_controlled_real_signers",
            "external_monotonic_floor_proven",
            "real_provider_revocation_freshness_proven",
            "physical_google_drive_cache_read_write",
            "actual_reference_market_quotes_retained",
            "a03_full_v2_behavior_abi_parity",
            "g01_g08_independent_owner_gates_closed",
            "production_market_data_read_authorized",
            "production_market_data_write_authorized",
            "production_release_authorized", "trading_authorized",
        ):
            with self.subTest(field=name):
                self.assertFalse(self.receipt[name])

    def test_a02_owner_signoffs_still_zero(self):
        self.assertEqual(self.receipt["a02_owner_signed_modules"],0)

    def test_all_rights_claimed_never_granted(self):
        report=review_unverified_source_claims(
            BarProduct.SSI_FASTCONNECT_INTRADAY_OHLC,
            (rights_claim(),),reviewed_at_utc=BASE,
        )
        self.assertEqual(len(report.claimed_scopes_unverified),len(RightsScope))
        self.assertEqual(report.missing_scope_claims,())
        self.assertFalse(report.provider_authorization_verified)
        with self.assertRaises(PermissionError):
            require_authorized_source(report)

    def test_expired_rights_claim_not_counted(self):
        claim=rights_claim(claimed_expiry_utc=BASE-timedelta(seconds=1))
        report=review_unverified_source_claims(
            claim.product,(claim,),reviewed_at_utc=BASE,
        )
        self.assertEqual(report.claimed_scopes_unverified,())
        self.assertTrue(report.expired_claims)

    def test_cross_product_rights_cannot_be_reused(self):
        with self.assertRaises(ValueError):
            review_unverified_source_claims(
                BarProduct.DNSE_OPENAPI_OHLC,
                (rights_claim(),),reviewed_at_utc=BASE,
            )

    def test_claim_with_private_url_evidence_id_denied(self):
        with self.assertRaises(ValueError):
            rights_claim(evidence_id="https://example.test/private")

    def test_claim_with_duplicate_scope_denied(self):
        with self.assertRaises(ValueError):
            rights_claim(scope_claims=(RightsScope.READ_HISTORICAL,)*2)

    def test_ssi_one_row_does_not_enable_backtest(self):
        report=summarize_source_capability(
            ProbeEndpoint.SSI_INTRADAY,
            {"status":"ok","data":{"ticks":[{"symbol":"FPT",
                                           "trading_date":"2026-11-10"}]}},
            symbol="FPT",checked_at_utc=BASE,
        )
        self.assertEqual(report.state,ProbeState.RETURNED_ROWS)
        self.assertEqual(report.observed_rows,1)
        self.assertFalse(report.source_rights_verified)
        self.assertFalse(audit_backtest_evidence((report,)).ready_for_historical_backtest)

    def test_ssi_wrong_symbol_denied(self):
        with self.assertRaises(ValueError):
            summarize_source_capability(
                ProbeEndpoint.SSI_INTRADAY,
                {"status":"ok","data":{"ticks":[{"symbol":"WRONG",
                                               "trading_date":"2026-11-10"}]}},
                symbol="FPT",checked_at_utc=BASE,
            )

    def test_ssi_empty_count_does_not_promote_coverage(self):
        r=summarize_source_capability(
            ProbeEndpoint.SSI_INTRADAY,{"status":"ok","data":{"ticks":[]}},
            symbol="FPT",checked_at_utc=BASE,
        )
        self.assertEqual(r.state,ProbeState.RETURNED_EMPTY)
        self.assertFalse(r.continuous_m1_m5_m15_coverage_verified)

    def test_ssi_downstream_outage_is_explicit(self):
        r=summarize_source_capability(
            ProbeEndpoint.SSI_INTRADAY,
            {"status":"error","error":{"code":"DOWNSTREAM_UNAVAILABLE"}},
            symbol="FPT",checked_at_utc=BASE,
        )
        self.assertEqual(r.state,ProbeState.DOWNSTREAM_UNAVAILABLE)
        self.assertFalse(r.production_qualified)

    def test_event_signature_valid_but_vendor_auth_false(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        result=verify_pinned_rights_event_chain((ev,),pin,checked_at_utc=BASE)
        self.assertTrue(result.signature_integrity_verified)
        self.assertEqual(result.state,RightsChainState.SIGNED_CANDIDATE_UNAUTHORIZED)
        self.assertFalse(result.signer_authority_verified)

    def test_signed_chain_permission_boundary_denies(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        result=verify_pinned_rights_event_chain((ev,),pin,checked_at_utc=BASE)
        with self.assertRaises(PermissionError):
            require_rights_chain_authorization(result)

    def test_tampered_signature_scope_denied(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        tampered=replace(ev,scope_claims=(RightsScope.RETAIN_RAW_OHLCV,))
        with self.assertRaises(ValueError):
            verify_pinned_rights_event_chain((tampered,),pin,checked_at_utc=BASE)

    def test_pinned_event_tail_mismatch_denied(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        with self.assertRaises(ValueError):
            verify_pinned_rights_event_chain(
                (ev,),replace(pin,expected_tail_sha256="f"*64),
                checked_at_utc=BASE,
            )

    def test_signed_custody_head_conditional_only(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        r=audit_conditional_custody_head(
            head,cust,floor,checked_at_utc=BASE,
            event_pin=pin,events=(ev,),
        )
        self.assertTrue(r.custodian_signature_integrity)
        self.assertTrue(r.conditional_event_chain_integrity)
        self.assertFalse(r.vendor_key_origin_verified)
        self.assertFalse(r.rights_to_read_or_cache)

    def test_signed_custody_head_cannot_approve_vendor_rights(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        r=audit_conditional_custody_head(
            head,cust,floor,checked_at_utc=BASE,event_pin=pin,events=(ev,),
        )
        with self.assertRaises(PermissionError):
            require_authenticated_provider_rights(r)

    def test_custody_head_relative_floor_rejects_older_sequence(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        with self.assertRaises(CustodyRejected):
            audit_conditional_custody_head(
                head,cust,replace(floor,sequence=2),
                checked_at_utc=BASE,
            )

    def test_forged_signed_custody_head_signature_denied(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        import base64
        bad=replace(head,signature_base64=base64.b64encode(bytes(64)).decode("ascii"))
        with self.assertRaises(CustodyRejected):
            audit_conditional_custody_head(
                bad,cust,floor,checked_at_utc=BASE,
            )

    def test_custody_event_pin_must_be_paired_with_event_chain(self):
        *_,ev,cust,head,floor,pin=signed_chain()
        with self.assertRaises(CustodyRejected):
            audit_conditional_custody_head(
                head,cust,floor,checked_at_utc=BASE,
                event_pin=pin,events=None,
            )

    def test_reference_empty_journal_genesis(self):
        with TemporaryDirectory() as td:
            journal=ReferenceJournal(Path(td)/"journal.sqlite")
            journal.initialize()
            self.assertEqual(journal.verify(),(0,ZERO))

    def test_reference_journal_no_silent_reinitialization(self):
        with TemporaryDirectory() as td:
            journal=ReferenceJournal(Path(td)/"journal.sqlite")
            journal.initialize()
            with self.assertRaises(FileExistsError):
                journal.initialize()

    def test_reference_journal_backup_restores_metadata_only(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            journal=ReferenceJournal(root/"journal.sqlite")
            journal.initialize()
            cp=create_candidate_journal_checkpoint(
                journal,root/"backup.sqlite","cp-A","store-A",BASE)
            restored=restore_journal_from_pinned(
                root/"backup.sqlite",root/"restored.sqlite",
                cp,expected_store_id="store-A",
            )
            self.assertEqual(restored.verify(),(0,ZERO))
            self.assertEqual(cp.omitted_cache_rows,0)

    def test_reference_journal_wrong_store_backup_rejected(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            journal=ReferenceJournal(root/"journal.sqlite")
            journal.initialize()
            cp=create_candidate_journal_checkpoint(
                journal,root/"backup.sqlite","cp-A","store-A",BASE)
            with self.assertRaises(Exception):
                verify_journal_backup_against_pinned(
                    root/"backup.sqlite",cp,expected_store_id="other",
                )

    def test_snapshot_empty_store_genesis(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            cache=SyntheticIncrementalStore(root/"store.sqlite")
            cache.initialize()
            m=create_fixture_snapshot(
                cache,root/"snap.sqlite",root/"snap.json",
                snapshot_id="fixture1",generation=1,
                previous_manifest_sha256=None,created_at_utc=BASE,
            )
            self.assertFalse(m.live_market_data_authorized)
            self.assertFalse(m.drive_upload_performed)

    def test_snapshot_wrong_pin_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            cache=SyntheticIncrementalStore(root/"store.sqlite")
            cache.initialize()
            m=create_fixture_snapshot(
                cache,root/"snap.sqlite",root/"snap.json",
                snapshot_id="fixture1",generation=1,
                previous_manifest_sha256=None,created_at_utc=BASE,
            )
            with self.assertRaises(ValueError):
                verify_fixture_snapshot(
                    root/"snap.sqlite",(root/"snap.json").read_text(),
                    pinned_manifest_sha256="f"*64,
                )

    def test_snapshot_restore_into_new_store(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            cache=SyntheticIncrementalStore(root/"store.sqlite")
            cache.initialize()
            m=create_fixture_snapshot(
                cache,root/"snap.sqlite",root/"snap.json",
                snapshot_id="fixture1",generation=1,
                previous_manifest_sha256=None,created_at_utc=BASE,
            )
            restored=restore_fixture_snapshot(
                root/"snap.sqlite",root/"restored.sqlite",
                (root/"snap.json").read_text(),pinned_manifest_sha256=m.digest,
            )
            self.assertEqual(restored.read_bars(identity()),())

    def test_snapshot_transport_production_denied(self):
        with self.assertRaises(PermissionError):
            require_approved_cache_transport()

    def test_partition_chunk_encode_decode_real_original(self):
        key=identity()
        rows=(bar(0),)
        self.assertEqual(
            decode_fixture_chunk(encode_fixture_chunk(key,rows),
                                 expected_identity=key),rows,
        )

    def test_partition_other_provider_identity_denied(self):
        from swing_trading.incremental_cache import Provider
        key=identity()
        data=encode_fixture_chunk(key,(bar(0),))
        with self.assertRaises(ValueError):
            decode_fixture_chunk(data,expected_identity=identity(Provider.DNSE))

    def test_partition_one_manifest_then_noop(self):
        i=SyntheticDrivePartitionIndex();k=identity()
        status=i.stage_and_publish(k,(bar(0),),
                expected_head_sha256=None,created_at_utc=BASE)
        self.assertIs(status,PartitionWrite.CREATED)
        pinned=i.active_manifest_sha(k)
        self.assertEqual(i.load(k,pinned_manifest_sha256=pinned),(bar(0),))
        status=i.stage_and_publish(k,(bar(0),),
                expected_head_sha256=pinned,created_at_utc=BASE)
        self.assertIs(status,PartitionWrite.REUSED)

    def test_partition_stale_writer_denied(self):
        i=SyntheticDrivePartitionIndex();k=identity()
        i.stage_and_publish(k,(bar(0),),
                expected_head_sha256=None,created_at_utc=BASE)
        with self.assertRaises(ValueError):
            i.stage_and_publish(k,(bar(0,close=Decimal("150")),),
                expected_head_sha256=None,created_at_utc=BASE)

    def test_partition_open_bar_denied(self):
        i=SyntheticDrivePartitionIndex();k=identity()
        with self.assertRaises(ValueError):
            i.stage_and_publish(k,(replace(bar(0),closed=False),),
                expected_head_sha256=None,created_at_utc=BASE)

    def test_partition_real_market_transport_forbidden(self):
        with self.assertRaises(PermissionError):
            require_real_market_cache_transport()

    def test_source_and_cache_same_fixture_cannot_authorize_production(self):
        self.assertTrue(self.receipt["scenarios"]["self_claimed_all_rights_scopes_not_provider_license"])
        self.assertTrue(self.receipt["scenarios"]["synthetic_partition_chunk_pin_and_stale_writer"])
        self.assertFalse(self.receipt["production_market_data_read_authorized"])
        self.assertFalse(self.receipt["production_market_data_write_authorized"])

    def test_ephemeral_two_key_signature_receipt_deterministic_policy(self):
        again=evaluate_source_custody_cache_matrix()
        self.assertEqual(again["scenario_receipt_sha256"],
                         self.receipt["scenario_receipt_sha256"])


if __name__=="__main__":
    unittest.main()
