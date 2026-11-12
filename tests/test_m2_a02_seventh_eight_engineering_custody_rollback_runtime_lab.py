"""A02 seventh tranche: 40 actual-original V1 engineering/custody/rollback tests.

Fixture data only. POSIX SQLite files exist only on ephemeral GH Actions
Linux; no user local computer, vendor accounts, live Drive or broker access.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sqlite3
import unittest

from scripts.m2_a02_seventh_eight_engineering_custody_rollback_runtime_lab import (
    EIGHT, SCHEMA, _FixtureReader, _secure_fixture_sqlite,
    execute_seventh_eight_runtime,
)
from swing_trading.engineering_contracts import (
    PortDescriptor, EngineeringPortRegistry, check_port,
    require_compatible_port,
)
from swing_trading.engineering_release import (
    compare_engineering_snapshots,
)
from swing_trading.fixture_scan import (
    execute_fixture_scan, FixtureResponse,
)
from swing_trading.cache_fetch_planner import (
    SourceCapability, RefreshAction,
)
from swing_trading.incremental_cache import SyntheticIncrementalStore
from swing_trading.provider_custody_host_plan import (
    HostPreflightRejected, EvidenceRole, HostControl,
    inspect_external_onboarding, require_external_trust,
)
from swing_trading.provider_review_packet import (
    PacketState, ReviewRole, require_independently_authorized_packet,
)
from swing_trading.reference_storage_preflight import (
    UnsafeReferenceStorage, inspect_reference_storage,
    require_reference_storage,
)
from swing_trading.reference_pinned_fd import pin_reference_sqlite_files
from swing_trading.vn_release_rollback import (
    RollbackLayer, preview_vn_rollback,
)
from test_engineering_release import snapshot
from test_incremental_cache import START, FIVE, bar, identity
from test_provider_custody_host_plan import (
    P, NOW, all_evidence, all_controls,
    evidence as claimed_evidence, control as claimed_control,
)
from test_provider_review_packet import packet, hold, all_marks, mark
from test_vn_release_rollback import profile, context

REQ=PortDescriptor(
    "cache.readonly_fixture","1.0.0","SYNTHETIC_TEST_ONLY",
    ("get_head","read_partition"),
)

def scan_pair():
    t=TemporaryDirectory()
    root=Path(t.name)
    s=SyntheticIncrementalStore(root/"cache.sqlite");s.initialize()
    k=identity()
    samples=tuple(bar(i) for i in range(20))
    called=[]
    def fetch(plan):
        called.append(plan.action)
        return FixtureResponse(tuple(b for b in samples
                if plan.start_utc <= b.start_utc < plan.end_utc
                and b.end_utc<=plan.end_utc),True,240)
    def scan(minute,cap=SourceCapability.WINDOWED):
        return execute_fixture_scan(
            store=s,identity=k,now_utc=START+timedelta(minutes=minute),
            session_start_utc=START,
            latest_expected_closed_start_utc=START+timedelta(minutes=(minute//5-1)*5),
            bar_duration=FIVE,capability=cap,fetch_fixture=fetch,
        )
    return t, s, called, scan


class SeventhEightRealV1SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=execute_seventh_eight_runtime()

    # 1–6 report/executed original module and authority scope
    def test_01_exact_eight_new_original_modules(self):
        self.assertEqual(len(EIGHT),8)
        self.assertEqual(len(set(EIGHT)),8)
        self.assertEqual(self.report["executed_original_modules"],list(EIGHT))

    def test_02_56_of_63_distinct_seven_remain(self):
        self.assertEqual(self.report["previous_distinct_originals"],48)
        self.assertEqual(self.report["cumulative_scoped_original_v1_modules"],56)
        self.assertEqual(self.report["originals_remaining_without_this_qa"],7)

    def test_03_no_go_receipt_and_eight_joined_checks(self):
        self.assertEqual(self.report["schema"],SCHEMA)
        self.assertIn("NO_GO",self.report["status"])
        self.assertEqual(self.report["linked_check_count"],8)
        self.assertTrue(all(self.report["linked_checks"].values()))

    def test_04_owner_a02_and_a03_absent(self):
        self.assertEqual(self.report["a02_owner_signed_module_dispositions"],0)
        self.assertFalse(self.report["a03_full_v1_v2_abi_behavior_owner_accepted"])

    def test_05_all_real_authorities_false(self):
        for k in ("actual_provider_market_quote_api_called",
                  "actual_signed_vendor_licence_verified",
                  "actual_external_custodian_authenticated",
                  "actual_provider_revocation_feed_authenticated",
                  "real_host_volume_or_drive_cache_approved",
                  "real_multiwriter_server_cas_or_monotonic_floor_verified",
                  "real_VN_exchange_settlement_verified",
                  "real_broker_order_or_rollback_executed",
                  "g01_g08_independent_prod_security_gates_closed",
                  "production_release_authorized","trading_authorized"):
            with self.subTest(field=k):
                self.assertIs(self.report[k],False)

    def test_06_receipt_is_repeatable_without_independent_witness(self):
        self.assertEqual(execute_seventh_eight_runtime(),self.report)
        self.assertEqual(self.report["synthetic_fixture_provider_fetches"],2)

    # 7–11 actual engineering contract/registration
    def test_07_semver_minor_compatible_structure_only(self):
        supplied=replace(REQ,version="1.1.0")
        result=check_port(REQ,supplied,_FixtureReader())
        self.assertTrue(result.compatible)
        self.assertTrue(result.structural_only)
        self.assertFalse(result.deploy_authorized)

    def test_08_cross_provider_scope_never_compatible(self):
        result=check_port(REQ,replace(REQ,scope="OTHER"),_FixtureReader())
        self.assertIn("SCOPE_MISMATCH_NO_IMPLICIT_PROVIDER_FALLBACK",result.reasons)
        with self.assertRaises(ValueError):
            require_compatible_port(REQ,replace(REQ,scope="OTHER"),_FixtureReader())

    def test_09_major_version_incompatible(self):
        result=check_port(REQ,replace(REQ,version="2.0.0"),_FixtureReader())
        self.assertIn("INCOMPATIBLE_CONTRACT_VERSION",result.reasons)

    def test_10_unimplemented_operation_denied(self):
        result=check_port(REQ,REQ,object())
        self.assertFalse(result.compatible)
        self.assertIn("MISSING_CALLABLE:get_head",result.reasons)

    def test_11_registry_consumer_pin_prevents_wrong_hot_swap(self):
        r=EngineeringPortRegistry();reader=_FixtureReader()
        r.add(REQ,reader)
        self.assertIs(r.bind_consumer("fixture_consumer",REQ),reader)
        with self.assertRaises(ValueError):
            r.replace(REQ,replace(REQ,version="2.0.0"),reader)
        self.assertIs(r.resolve(REQ),reader)

    # 12–15 original engineering release
    def test_12_snapshot_hash_deterministic(self):
        s=snapshot()
        self.assertEqual(s.fingerprint_sha256,snapshot().fingerprint_sha256)
        self.assertEqual(len(s.fingerprint_sha256),64)

    def test_13_new_source_contract_requires_requalification(self):
        a=snapshot();b=snapshot(module_contracts_sha256="e"*64)
        r=compare_engineering_snapshots(a,b)
        self.assertEqual(r.changed_fields,("module_contracts_sha256",))
        self.assertTrue(r.schema_or_contract_requalification_required)
        self.assertFalse(r.operational_rollback_approved)

    def test_14_document_diff_needs_sync_not_release(self):
        a=snapshot();b=snapshot(documentation_sha256="f"*64)
        r=compare_engineering_snapshots(a,b)
        self.assertTrue(r.documentation_sync_required)
        self.assertFalse(r.operational_rollback_approved)

    def test_15_snapshot_cannot_self_certify_release(self):
        s=snapshot()
        self.assertFalse(s.signed_release)
        self.assertFalse(s.independently_approved_lkg)
        self.assertFalse(s.deployment_authorized)

    # 16–20 original fixture scan
    def test_16_first_fixture_refresh_is_full_session(self):
        t,s,c,fn=scan_pair()
        try:
            r=fn(45)
            self.assertIs(r.plan.action,RefreshAction.REQUEST_FULL_SESSION)
            self.assertEqual(r.returned_rows,9)
            self.assertEqual(len(c),1)
        finally:t.cleanup()

    def test_17_five_minute_cache_hit_no_provider_callback(self):
        t,s,c,fn=scan_pair()
        try:
            fn(45);r=fn(46)
            self.assertTrue(r.cache_hit)
            self.assertEqual(r.fixture_requests,0)
            self.assertEqual(len(c),1)
        finally:t.cleanup()

    def test_18_new_closed_window_returns_two_rows(self):
        t,s,c,fn=scan_pair()
        try:
            fn(45);r=fn(50)
            self.assertEqual(r.returned_rows,2)
            self.assertIs(r.plan.action,RefreshAction.REQUEST_WINDOW)
            self.assertFalse(r.source_coverage_verified)
        finally:t.cleanup()

    def test_19_unknown_provider_capability_never_calls_callback(self):
        t,s,c,fn=scan_pair()
        try:
            r=fn(45,SourceCapability.UNKNOWN)
            self.assertIs(r.plan.action,RefreshAction.BLOCKED)
            self.assertEqual(c,[])
        finally:t.cleanup()

    def test_20_fixture_cache_hit_does_not_approve_market(self):
        t,s,c,fn=scan_pair()
        try:
            fn(45);r=fn(46)
            self.assertFalse(r.market_eligible)
            self.assertFalse(r.source_coverage_verified)
        finally:t.cleanup()

    # 21–25 original provider custody and review packet
    def test_21_all_claimed_host_controls_not_vendor_auth(self):
        r=inspect_external_onboarding(P,all_evidence(),all_controls(),checked_at_utc=NOW)
        self.assertEqual(r.missing_roles,())
        self.assertEqual(r.missing_controls,())
        self.assertFalse(r.rights_to_read_or_cache)
        self.assertFalse(r.secure_host_approved)

    def test_22_empty_onboard_has_missing_roles_and_controls(self):
        r=inspect_external_onboarding(P,(),(),checked_at_utc=NOW)
        self.assertTrue(r.missing_roles)
        self.assertTrue(r.missing_controls)

    def test_23_claimed_evidence_from_future_denied(self):
        x=replace(all_evidence()[0],recorded_at_utc=NOW+timedelta(minutes=1))
        with self.assertRaises(HostPreflightRejected):
            inspect_external_onboarding(P,(x,),(),checked_at_utc=NOW)

    def test_24_complete_review_packet_ready_only(self):
        r=packet()
        self.assertIs(r.state,PacketState.READY_FOR_EXTERNAL_REVIEW_ONLY)
        self.assertTrue(r.prepared_for_external_review)
        self.assertFalse(r.external_identity_or_signature_verified)
        with self.assertRaises(PermissionError):require_independently_authorized_packet(r)

    def test_25_revocation_hold_blocks_self_reported_packet(self):
        r=packet(holds=(hold(),))
        self.assertIs(r.state,PacketState.BLOCKED_HOLD)
        self.assertFalse(r.permission_to_read)
        self.assertFalse(r.production_authorized)

    # 26–33 actual local POSIX file & pinned FD checks on GitHub runner
    def test_26_preflight_secure_ephemeral_0700_0600_is_only_local(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private"
            db=_secure_fixture_sqlite(root)
            r=inspect_reference_storage(root,db)
            self.assertTrue(r.local_permissions_pass)
            self.assertFalse(r.host_volume_approved)
            self.assertFalse(r.provider_retention_approved)
            self.assertFalse(r.production_authorized)

    def test_27_preflight_world_readable_sqlite_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            os.chmod(db,0o644)
            r=inspect_reference_storage(root,db)
            self.assertFalse(r.local_permissions_pass)
            self.assertTrue(any("MODE_FILE:" in v for v in r.issues))
            with self.assertRaises(UnsafeReferenceStorage):
                require_reference_storage(root,db)

    def test_28_preflight_symlink_database_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            linked=root/"symlink.sqlite"
            linked.symlink_to(db)
            r=inspect_reference_storage(root,linked)
            self.assertFalse(r.local_permissions_pass)
            self.assertTrue(any("SYMLINK_FILE:" in v for v in r.issues))

    def test_29_preflight_hardlink_sqlite_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            os.link(db,root/"other.sqlite")
            r=inspect_reference_storage(root,db)
            self.assertTrue(any("HARDLINK_FILE:" in v for v in r.issues))

    def test_30_preflight_directory_outside_private_root_rejected(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            with self.assertRaises(ValueError):
                inspect_reference_storage(root,Path(td)/"other.sqlite")

    def test_31_pinned_fd_valid_header_only_not_prod_approval(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            with pin_reference_sqlite_files(root,db) as r:
                self.assertTrue(r.verify_path_names())
                self.assertTrue(r.local_permissions_pass)
                self.assertFalse(r.production_authorized)

    def test_32_pinned_fd_detects_new_sidecar(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            with pin_reference_sqlite_files(root,db) as r:
                p=Path(str(db)+"-wal");p.write_bytes(b"fixture");os.chmod(p,0o600)
                with self.assertRaises(UnsafeReferenceStorage):
                    r.verify_path_names()

    def test_33_pinned_fd_symlink_database_denied(self):
        with TemporaryDirectory() as td:
            root=Path(td)/"private";db=_secure_fixture_sqlite(root)
            path=root/"alias.sqlite";path.symlink_to(db)
            with self.assertRaises(UnsafeReferenceStorage):
                with pin_reference_sqlite_files(root,path):pass

    # 34–40 original VN rollback
    def test_34_rollback_no_lkg_cannot_activate(self):
        r=preview_vn_rollback(profile(),None,(RollbackLayer.R1_CODE,),context=context())
        self.assertIn("ROLLBACK_BLOCKED_NO_APPROVED_LKG",r.reasons)
        self.assertFalse(r.can_activate)
        self.assertFalse(r.can_place_orders)

    def test_35_parameter_rollback_invalidates_derived_cache(self):
        active=profile();prior=replace(active,parameter_sha256="e"*64)
        r=preview_vn_rollback(active,prior,(RollbackLayer.R2_RULE_PARAMS,),context=context())
        self.assertEqual(r.changed_layers,(RollbackLayer.R2_RULE_PARAMS,))
        self.assertTrue(r.invalidate_derived_cache)

    def test_36_pending_T2_is_not_current_sellable(self):
        active=profile();prior=replace(active,parameter_sha256="e"*64)
        r=preview_vn_rollback(active,prior,(RollbackLayer.R2_RULE_PARAMS,),
                              context=context(sellable=100,pending=500,requested=200))
        self.assertIn("SELL_EXCEEDS_SETTLED_SELLABLE_SHARES",r.reasons)
        self.assertFalse(r.can_place_orders)

    def test_37_bad_exchange_tick_fails_preflight(self):
        active=profile();prior=replace(active,parameter_sha256="e"*64)
        r=preview_vn_rollback(active,prior,(RollbackLayer.R2_RULE_PARAMS,),
                              context=context(price=Decimal("10050")))
        self.assertIn("INVALID_TICK_SIZE",r.reasons)

    def test_38_missing_broker_context_cannot_approve_rollback(self):
        active=profile();prior=replace(active,parameter_sha256="e"*64)
        r=preview_vn_rollback(active,prior,(RollbackLayer.R2_RULE_PARAMS,))
        self.assertIn("VN_MARKET_ACCOUNT_CONTEXT_NOT_VERIFIED",r.reasons)

    def test_39_rollback_out_of_scope_source_change_denied(self):
        active=profile();prior=replace(active,source_revision_id="REV-OLD")
        r=preview_vn_rollback(active,prior,(RollbackLayer.R1_CODE,),context=context())
        self.assertIn("OUT_OF_SCOPE_R3_SOURCE_DATA",r.reasons)
        self.assertFalse(r.can_activate)

    def test_40_full_profile_no_broker_order_even_on_complete_fake_context(self):
        active=profile();prior=replace(active,parameter_set_id="PARAM-0")
        r=preview_vn_rollback(active,prior,(RollbackLayer.R2_RULE_PARAMS,),context=context())
        self.assertFalse(r.can_activate)
        self.assertFalse(r.can_place_orders)
        self.assertIn("LKG_INDEPENDENT_APPROVAL_AND_RESTORE_PROOF_UNVERIFIED",r.reasons)


if __name__=="__main__":
    unittest.main()
