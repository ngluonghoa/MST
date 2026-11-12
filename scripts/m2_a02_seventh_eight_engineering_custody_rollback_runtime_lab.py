"""MST A02 7th eight distinct ORIGINAL V1 engineering/custody/rollback guards.

All domain functions execute directly from inherited Swing source. Test helpers
create only fabricated provider claims, model profiles, bytes and timestamps.
POSIX storage inspection uses an EPHEMERAL Linux GitHub Actions directory:
no Mac/MOCHI, no real Drive market cache, no real release or broker action.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from swing_trading.engineering_contracts import (
    PortDescriptor, EngineeringPortRegistry, check_port, require_compatible_port,
)
from swing_trading.engineering_release import (
    compare_engineering_snapshots,
)
from swing_trading.fixture_scan import (
    execute_fixture_scan, FixtureResponse,
)
from swing_trading.cache_fetch_planner import SourceCapability, RefreshAction
from swing_trading.incremental_cache import SyntheticIncrementalStore
from swing_trading.provider_custody_host_plan import (
    inspect_external_onboarding, require_external_trust,
)
from swing_trading.provider_review_packet import (
    PacketState, require_independently_authorized_packet,
)
from swing_trading.reference_storage_preflight import (
    inspect_reference_storage, require_reference_storage,
)
from swing_trading.reference_pinned_fd import pin_reference_sqlite_files
from swing_trading.vn_release_rollback import (
    RollbackLayer, preview_vn_rollback,
)

# Constructors of SYNTHETIC inputs only (domain functions remain ORIGINAL).
from test_engineering_release import snapshot
from test_incremental_cache import START, FIVE, bar, identity
from test_provider_custody_host_plan import P, NOW, all_evidence, all_controls
from test_provider_review_packet import packet, hold
from test_vn_release_rollback import profile, context

SCHEMA = "mst.a02.seventh-original-v1-engineering-custody-storage-rollback.synthetic.no-go.v1"
EIGHT = (
    "engineering_contracts", "engineering_release", "fixture_scan",
    "provider_custody_host_plan", "provider_review_packet",
    "reference_storage_preflight", "reference_pinned_fd",
    "vn_release_rollback",
)


def _require(value, key):
    if not value:
        raise AssertionError(key)


def _deny(action, error=PermissionError):
    try:
        action()
    except error:
        return True
    raise AssertionError("FALSE_EXTERNAL_AUTHORIZATION_NOT_DENIED")


class _FixtureReader:
    def get_head(self, identity):
        return None

    def read_partition(self, identity, pinned_digest):
        return ()


def _secure_fixture_sqlite(root):
    root.mkdir(mode=0o700)
    os.chmod(root,0o700)
    database=root/"nonproduction.sqlite"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE fixture (id INTEGER PRIMARY KEY, note TEXT)")
        conn.execute("INSERT INTO fixture(note) VALUES ('FAKE-NO-MARKET-QUOTES')")
    os.chmod(database,0o600)
    return database


def execute_seventh_eight_runtime():
    checks={}

    # Actual inherited engineering port ABI check protects provider scope
    # and pinned consumers without executing/admitting real storage.
    required=PortDescriptor(
        "cache.readonly_fixture","1.0.0","SYNTHETIC_TEST_ONLY",
        ("get_head","read_partition"),
    )
    supplied=PortDescriptor(
        "cache.readonly_fixture","1.1.0","SYNTHETIC_TEST_ONLY",
        ("get_head","read_partition"),
    )
    adapter=_FixtureReader()
    good=check_port(required,supplied,adapter)
    wrong=check_port(
        required,replace(supplied,scope="OTHER_FIXTURE"),adapter,
    )
    registry=EngineeringPortRegistry()
    registry.add(supplied,adapter)
    bound=registry.bind_consumer("fixture_consumer",required)
    _require(good.compatible and good.structural_only
             and not good.deploy_authorized and not good.live_data_authorized
             and not good.trading_authorized
             and bound is adapter
             and not wrong.compatible
             and "SCOPE_MISMATCH_NO_IMPLICIT_PROVIDER_FALLBACK" in wrong.reasons
             and _deny(lambda:require_compatible_port(
                 required,replace(supplied,scope="OTHER_FIXTURE"),adapter),
                 ValueError),
             "PORT_STRUCTURAL_MATCH_FALSE_VENDOR_AUTHORIZATION")
    checks["structural_port_version_scope_pinned_not_real_adapter_authority"]=True

    # Engineering version SHA/diff is repeatable but explicitly cannot
    # authorize deployment, rollback or licensed market data.
    current=snapshot()
    target=snapshot(module_contracts_sha256="e"*64)
    diff=compare_engineering_snapshots(current,target)
    stable=compare_engineering_snapshots(current,current)
    _require(diff.changed_fields==("module_contracts_sha256",)
             and diff.schema_or_contract_requalification_required
             and not diff.operational_rollback_approved
             and stable.exact_identity and not stable.changed_fields
             and current.fingerprint_sha256 != target.fingerprint_sha256
             and not current.trading_authorized,
             "ENGINEERING_SHA_DIFF_FALSE_RELEASE_APPROVAL")
    checks["build_SHA_manifest_change_requires_requalification_not_release"]=True

    # Actual V1 synthetic five-minute incremental scan; no connected
    # SSI/DNSE revision token or real market time sequence.
    with TemporaryDirectory(prefix="mst-a02-seven-scan-") as tmp:
        store=SyntheticIncrementalStore(Path(tmp)/"cache.sqlite")
        store.initialize()
        key=identity()
        market=tuple(bar(i) for i in range(20))
        requests=[]
        def fake_fetch(plan):
            requests.append(plan.action)
            found=tuple(x for x in market
                        if plan.start_utc <= x.start_utc < plan.end_utc
                        and x.end_utc <= plan.end_utc)
            return FixtureResponse(found, True, len(found)*120)
        def scan(minute,cap=SourceCapability.WINDOWED):
            return execute_fixture_scan(
                store=store,identity=key,
                now_utc=START+timedelta(minutes=minute),
                session_start_utc=START,
                latest_expected_closed_start_utc=START+timedelta(minutes=(minute//5-1)*5),
                bar_duration=FIVE,capability=cap,fetch_fixture=fake_fetch,
            )
        first=scan(45)
        cached=scan(46)
        second=scan(50)
        blocked=scan(55,SourceCapability.UNKNOWN)
        _require(first.plan.action is RefreshAction.REQUEST_FULL_SESSION
                 and first.returned_rows==9
                 and cached.cache_hit and cached.fixture_requests==0
                 and second.plan.action is RefreshAction.REQUEST_WINDOW
                 and second.returned_rows==2
                 and blocked.plan.action is RefreshAction.BLOCKED
                 and blocked.fixture_requests==0
                 and len(requests)==2
                 and not second.market_eligible and not second.source_coverage_verified,
                 "FIXTURE_SCAN_REFETCH_RATE_OR_UNSUPPORTED_SOURCE_CLAIM")
        checks["synthetic_first_full_then_window_noop_and_unknown_source_denial"]=True

    # Provider custody roles + controls claimed complete in ONE process
    # never prove externally authenticated signer/host/revocation.
    onboard=inspect_external_onboarding(
        P,all_evidence(),all_controls(),checked_at_utc=NOW,
    )
    missing=inspect_external_onboarding(P,(),(),checked_at_utc=NOW)
    _require(onboard.missing_roles==() and onboard.missing_controls==()
             and not onboard.vendor_key_origin_verified
             and not onboard.fresh_revocation_stream_authenticated
             and not onboard.secure_host_approved
             and not onboard.rights_to_read_or_cache
             and not onboard.trading_actionable
             and len(missing.missing_roles)>0
             and len(missing.missing_controls)>0
             and _deny(lambda:require_external_trust(onboard)),
             "SELF_CLAIMED_CUSTODY_ROLES_FALSELY_VERIFIED")
    checks["claimed_complete_custodian_roles_and_host_controls_still_NO_GO"]=True

    # Independent review packet is only a self-attested checklist; an
    # observed revocation HOLD blocks even a previously ready packet.
    ready=packet()
    held=packet(holds=(hold(),))
    _require(ready.state is PacketState.READY_FOR_EXTERNAL_REVIEW_ONLY
             and ready.prepared_for_external_review
             and not ready.external_identity_or_signature_verified
             and not ready.provider_entitlement_verified
             and not ready.permission_to_read
             and held.state is PacketState.BLOCKED_HOLD
             and not held.actionable
             and _deny(lambda:require_independently_authorized_packet(ready)),
             "PACKET_CLAIMS_FALSE_LICENSE_OR_HOLD_IGNORED")
    checks["claimed_licence_review_ready_not_authenticated_hold_is_sticky"]=True

    # Reference storage and nofollow/openat file-descriptor code are
    # exercised against ephemeral Linux temp SQLite ONLY. Approval remains
    # impossible even with exact POSIX ownership/mode/inode agreement.
    with TemporaryDirectory(prefix="mst-a02-seven-host-") as tmp:
        root=Path(tmp)/"private_fixture"
        db=_secure_fixture_sqlite(root)
        preflight=inspect_reference_storage(root,db)
        accepted=require_reference_storage(root,db)
        _require(preflight.local_permissions_pass
                 and preflight.issues==()
                 and accepted.local_permissions_pass
                 and not preflight.host_volume_approved
                 and not preflight.provider_retention_approved
                 and not preflight.production_authorized,
                 "POSIX_MODE_PASSED_AND_FALSE_PRODUCTION_ADMISSION")
        checks["read_only_reference_storage_preflight_0700_0600_not_approved"]=True
        with pin_reference_sqlite_files(root,db) as pinned:
            pinned.verify_path_names()
            _require(pinned.local_permissions_pass
                     and not pinned.production_authorized
                     and pinned.database_fd >= 0,
                     "OPENAT_NOFOLLOW_PIN_FALSE_TRADING_APPROVAL")
            # A newly created sidecar AFTER pinning is a name change that
            # must be detected within that pinned inspection context.
            sidecar=Path(str(db)+"-wal")
            sidecar.write_bytes(b"fixture-sidecar-not-real-WAL")
            os.chmod(sidecar,0o600)
            from swing_trading.reference_storage_preflight import UnsafeReferenceStorage
            _require(_deny(lambda:pinned.verify_path_names(),UnsafeReferenceStorage),
                     "NEW_SIDECAR_NAME_DID_NOT_INVALIDATE_PIN")
        checks["pinned_fd_detects_new_sidecar_name_and_denies_later_path_swap"]=True

    # VN cash-equity rollback preview must never move any pointer or trade.
    old=profile()
    target=replace(old,parameter_set_id="PARAM-0",parameter_sha256="e"*64)
    view=preview_vn_rollback(
        old,target,(RollbackLayer.R2_RULE_PARAMS,),context=context(),
    )
    over_sell=preview_vn_rollback(
        old,target,(RollbackLayer.R2_RULE_PARAMS,),
        context=context(sellable=100,pending=500,requested=200),
    )
    _require(view.changed_layers == (RollbackLayer.R2_RULE_PARAMS,)
             and view.invalidate_derived_cache
             and not view.can_activate
             and not view.can_place_orders
             and not over_sell.can_activate
             and "SELL_EXCEEDS_SETTLED_SELLABLE_SHARES" in over_sell.reasons
             and "LKG_INDEPENDENT_APPROVAL_AND_RESTORE_PROOF_UNVERIFIED"
                 in view.reasons,
             "ROLLBACK_SELL_T2_OR_NO_LKG_FALSELY_ACTIVATED")
    checks["VN_rollback_preflight_T2_pending_not_sellable_or_approved_LKG"]=True

    _require(len(checks)==8 and all(checks.values()),
             "SEVENTH_EIGHT_ORIGINAL_V1_DOMAIN_GUARDS_FAILED")
    return {
        "schema": SCHEMA,
        "status": "SEVENTH_EIGHT_REAL_ORIGINAL_V1_ENG_CUSTODY_STORAGE_ROLLBACK_QA_PASS_NO_GO",
        "executed_original_modules": list(EIGHT),
        "distinct_originals_this_tranche": 8,
        "previous_distinct_originals": 48,
        "cumulative_scoped_original_v1_modules": 56,
        "originals_remaining_without_this_qa": 7,
        "linked_checks": checks,
        "linked_check_count": len(checks),
        "synthetic_fixture_provider_fetches": len(requests),
        "actual_provider_market_quote_api_called": False,
        "actual_signed_vendor_licence_verified": False,
        "actual_external_custodian_authenticated": False,
        "actual_provider_revocation_feed_authenticated": False,
        "real_host_volume_or_drive_cache_approved": False,
        "real_multiwriter_server_cas_or_monotonic_floor_verified": False,
        "real_VN_exchange_settlement_verified": False,
        "real_broker_order_or_rollback_executed": False,
        "a02_owner_signed_module_dispositions": 0,
        "a03_full_v1_v2_abi_behavior_owner_accepted": False,
        "g01_g08_independent_prod_security_gates_closed": False,
        "production_release_authorized": False,
        "trading_authorized": False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    result=execute_seventh_eight_runtime()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="linked_checks"},sort_keys=True))


if __name__=="__main__":
    main()
