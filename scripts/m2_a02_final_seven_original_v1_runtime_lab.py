"""A02 final seventh-original-path runtime matrix, synthetic-only NO-GO.

Six original V1 domain modules: cache_swap_preview, reference_checkpoint_mac,
reference_checkpoint_signature, reference_host_dryrun,
reference_offline_verified_archive, rvol_tod_contract.
The seventh V1 Python file, __init__.py, is PACKAGE IMPORT/METADATA ONLY.
Eight previous batches? Actually first seven groups executed 56 distinct modules.
This final group completes 63/63 file-path scoped coverage, NOT 63/63 full
behavioral certification, owner acceptance, source authenticity or trading.
Synthetic private Ed25519 key and HMAC key exist ONLY within this Github runner,
and are never real independent custodian or entitlement authority.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path

import swing_trading
from swing_trading.cache_swap_preview import compare_synthetic_cache_backends
from swing_trading.partition_chunk_cache import SyntheticDrivePartitionIndex
from swing_trading.segmented_cache import SyntheticWeeklyChunkStore
from swing_trading.reference_checkpoint_mac import (
    DetachedJournalMac, create_candidate_detached_mac,
    verify_detached_journal_mac, verify_authenticated_journal_backup,
)
from swing_trading.reference_checkpoint_signature import (
    DetachedJournalSignature, verify_detached_journal_signature,
)
from swing_trading.reference_host_dryrun import (
    StaticMcpFixture, FixtureOnlyD1HostHarness,
)
from swing_trading.reference_offline_verified_archive import (
    verify_offline_signed_metadata_archive,
)
from swing_trading.reference_journal import ReferenceJournalCorrupt
from swing_trading.dnse_d1_reference_fallback import D1Provider, D1ReadState
from swing_trading.rvol_tod_contract import (
    calculate_rvol_tod20, CumulativeVolumeDefinition,
)
from swing_trading.causal_indicators import IndicatorState

# Existing fabricated input constructors only, NEVER replacements for the
# original V1 functions under evaluation. One reference fixture creates an
# ephemeral offline SQLite metadata archive and one synthetic Ed25519 signer.
from test_partition_chunk_cache import identity as cache_identity, bar as cache_bar, NOW as CACHE_NOW
from test_rvol_tod_contract import sample as rvol_sample, calculate as rvol_fixture
from test_reference_offline_verified_archive import OfflineSignedArchiveTests
from test_reference_host_dryrun import fixture as host_fixture
from test_d1_mcp_transport_bridge import ssi_payload, dnse_payload
from test_dnse_d1_reference_fallback import request as d1_request, NOW as D1_NOW

SCHEMA="mst.a02.final-seven-original-files.synthetic.no-authority.v1"
FILES=(
    "__init__", "cache_swap_preview", "reference_checkpoint_mac",
    "reference_checkpoint_signature", "reference_host_dryrun",
    "reference_offline_verified_archive", "rvol_tod_contract",
)
DOMAIN_MODULES=tuple(n for n in FILES if n!="__init__")
MAC_KEY=b"\x37"*32


def _require(predicate,reason):
    if not predicate:
        raise AssertionError(reason)


def _denied(fn, errors=(ValueError,)):
    try:
        fn()
    except errors:
        return True
    raise AssertionError("FAIL_CLOSED_BOUNDARY_ACCEPTED_BAD_INPUT")


def build_cache_fixture():
    key=cache_identity()
    candles=tuple(cache_bar(i) for i in range(20))
    a=SyntheticDrivePartitionIndex()
    b=SyntheticWeeklyChunkStore()
    a.stage_and_publish(key,candles,expected_head_sha256=None,
                        created_at_utc=CACHE_NOW)
    b.commit(key,candles,expected_head=None,observed_at_utc=CACHE_NOW)
    return key,candles,a,b


def build_archive_fixture():
    # Reuse existing synthetic fixture construction, NOT an inherited domain
    # implementation mock. Its own addCleanup is executed by caller.
    f=OfflineSignedArchiveTests(
        methodName="test_signed_metadata_archive_read_from_fd_without_live_quotes")
    f.setUp()
    return f


def _sig_args(f):
    return dict(
        public_key_raw=f.public, expected_key_id="key1",
        expected_store_id="store1",
        expected_public_key_sha256=f.fingerprint,
    )


def _archive_args(f):
    return dict(root=f.root,archive=f.archive,checkpoint=f.cp,
                signature=f.seal,**_sig_args(f))


def run_final_seven_originals():
    guards={}

    # 1. Import/API metadata only: __init__ contains NO trading logic.
    _require(swing_trading.__version__=="0.0.1"
             and "not a validated trading system" in (swing_trading.__doc__ or ""),
             "ORIGINAL_PACKAGE_METADATA_CHANGED")
    guards["original_init_module_only_import_version_and_disclaimer"]=True

    # 2. Actual cache migration preview: semantic equal bytes and EMA/ATR,
    # but no actual migrations, Google Drive reads or trusted cache custody.
    key,bars,old,new=build_cache_fixture()
    same=compare_synthetic_cache_backends(
        key,old_backend=old,candidate_backend=new,
        pinned_old_sha256=old.get_head(key),
        pinned_candidate_sha256=new.get_head(key),
    )
    _require(same.fixture_equivalent and same.old_rows==20
             and same.candidate_rows==20 and same.reasons==()
             and not same.licensed_data_authorized
             and not same.real_migration_approved
             and not same.trading_authorized,
             "CACHE_BACKEND_EQUIVALENCE_FALSE_RELEASE")
    guards["C3B_to_C4A_fixture_equal_not_market_migration"]=True

    _require(_denied(lambda:compare_synthetic_cache_backends(
                 key,old_backend=old,candidate_backend=new,
                 pinned_old_sha256="0"*64,
                 pinned_candidate_sha256=new.get_head(key)))
             and _denied(lambda:compare_synthetic_cache_backends(
                 key,old_backend=old,candidate_backend=old,
                 pinned_old_sha256=old.get_head(key),
                 pinned_candidate_sha256=old.get_head(key))),
             "STALE_OR_SAME_BACKEND_PREVIEW_ACCEPTED")
    corrected=bars[:1]+(cache_bar(1,close=Decimal("333"),revision="r2"),)+bars[2:]
    new.commit(key,corrected,expected_head=new.get_head(key),
               observed_at_utc=CACHE_NOW)
    mismatch=compare_synthetic_cache_backends(
        key,old_backend=old,candidate_backend=new,
        pinned_old_sha256=old.get_head(key),
        pinned_candidate_sha256=new.get_head(key),
    )
    _require(not mismatch.fixture_equivalent
             and "BAR_OR_REVISION_OR_FIRST_KNOWN_MISMATCH" in mismatch.reasons
             and not mismatch.real_migration_approved,
             "CHANGED_HISTORY_FALSE_CACHE_PARITY")
    guards["cache_pin_mismatch_and_changed_revision_fail_closed"]=True

    # 3-5: Synthetic metadata journal with one locally controlled signing
    # key. MAC possession != independent custodian enrollment. Signature
    # validation relies on a caller-controlled public key/fingerprint.
    f=build_archive_fixture()
    try:
        sealed_at=D1_NOW+timedelta(seconds=1)
        mac=create_candidate_detached_mac(
            f.cp,signing_key=MAC_KEY,key_id="mac-fixture",
            sealed_at_utc=sealed_at,
        )
        parsed=DetachedJournalMac.parse_json(mac.canonical_json())
        _require(parsed==mac and
                 verify_detached_journal_mac(
                     f.cp,parsed,verification_key=MAC_KEY,
                     expected_key_id="mac-fixture",expected_store_id="store1")==f.cp
                 and verify_authenticated_journal_backup(
                     f.archive,f.cp,parsed,verification_key=MAC_KEY,
                     expected_key_id="mac-fixture",expected_store_id="store1")[0]==1,
                 "DETACHED_HMAC_SEAL_VERIFICATION_FAILED")
        guards["HMAC_detached_journal_backup_one_runner_key_only"]=True
        _require(_denied(
                  lambda:verify_detached_journal_mac(
                      f.cp,parsed,verification_key=b"X"*32,
                      expected_key_id="mac-fixture",expected_store_id="store1"),
                  (ReferenceJournalCorrupt,))
                 and _denied(
                     lambda:verify_detached_journal_mac(
                         f.cp,parsed,verification_key=MAC_KEY,
                         expected_key_id="forged-id",expected_store_id="store1"),
                     (ReferenceJournalCorrupt,)),
                 "HMAC_WRONG_SHARED_KEY_OR_ID_ACCEPTED")
        guards["HMAC_wrong_key_and_key_id_denied"]=True

        signature=DetachedJournalSignature.parse_json(f.seal.canonical_json())
        _require(signature==f.seal
                 and verify_detached_journal_signature(
                     f.cp,signature,**_sig_args(f))==f.cp,
                 "DETACHED_ED25519_PINNED_SIGNATURE_INVALID")
        guards["Ed25519_detached_checkpoint_verifies_caller_pinned_key_only"]=True
        _require(
            _denied(
                lambda:verify_detached_journal_signature(
                    f.cp,signature,
                    **{**_sig_args(f),
                       "expected_public_key_sha256":"0"*64}),
                (ReferenceJournalCorrupt,))
            and _denied(
                lambda:verify_detached_journal_signature(
                    f.cp,replace(signature,signature_base64=
                                 base64.b64encode(b"\x00"*64).decode("ascii")),
                    **_sig_args(f)),
                (ReferenceJournalCorrupt,)),
            "ED25519_INVALID_FINGERPRINT_OR_SIGNATURE_ACCEPTED")
        guards["Ed25519_wrong_fingerprint_or_signature_denied"]=True

        archive=verify_offline_signed_metadata_archive(**_archive_args(f))
        _require(archive.journal_records==1
                 and archive.chain_tip_sha256==f.cp.chain_tip_sha256
                 and archive.archive_sha256==f.cp.backup_sha256
                 and archive.signed_manifest_checked and archive.metadata_only
                 and not archive.production_authorized
                 and not archive.market_data_certified
                 and not archive.historical_backtest_qualified
                 and not archive.actionable,
                 "OFFLINE_SIGNED_ARCHIVE_FALSE_MARKET_RIGHTS")
        guards["fd_pinned_SQLite_metadata_archive_one_row_not_price_cache"]=True

        corrupted=f.root/"changed-bytes.sqlite"
        raw=f.archive.read_bytes()
        corrupted.write_bytes(raw[:32]+bytes([raw[32]^1])+raw[33:])
        corrupted.chmod(0o600)
        _require(_denied(
            lambda:verify_offline_signed_metadata_archive(
                **{**_archive_args(f),"archive":corrupted}),
            (ReferenceJournalCorrupt,)),
            "MODIFIED_OFFLINE_SQLITE_BACKUP_ACCEPTED")
        guards["offline_archive_mutated_bytes_digest_denied"]=True
    finally:
        f.doCleanups()

    # 6. Offline static D1 envelope host NEVER reaches network/MCP plugin.
    ssi=host_fixture(D1Provider.SSI,ssi_payload())
    dnse=host_fixture(D1Provider.DNSE,dnse_payload())
    host=FixtureOnlyD1HostHarness(
        ssi=ssi,dnse=dnse,
        clock_utc=D1_NOW-timedelta(minutes=1))
    r=host.run_once(d1_request())
    _require(
        r.endpoint_order==("SSI.marketdata_list_daily_stock_infor",)
        and r.run.audit.state is D1ReadState.PRIMARY_SSI_REFERENCE_ONLY
        and r.fixture_only and not r.live_mcp_deployed
        and not r.data_rights_verified and not r.production_authorized
        and not r.actionable
        and _denied(lambda:host.run_once(d1_request()),(PermissionError,)),
        "OFFLINE_D1_FIXTURE_ACCIDENTAL_CONNECTED_MCP")
    guards["host_SSI_only_fixture_one_shot_no_network_or_authority"]=True

    ssi_error=host_fixture(D1Provider.SSI,{
        "status":"error","error":"DOWNSTREAM_UNAVAILABLE"})
    fallback=FixtureOnlyD1HostHarness(
        ssi=ssi_error,dnse=dnse,
        clock_utc=D1_NOW-timedelta(minutes=1)).run_once(d1_request())
    _require(
        fallback.endpoint_order==(
            "SSI.marketdata_list_daily_stock_infor","DNSE.price_get_history")
        and fallback.run.audit.state is D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY
        and not fallback.run.historical_backtest_qualified
        and _denied(lambda:host_fixture(
            D1Provider.SSI,{"status":"ok","token":"DO_NOT_USE"})),
        "STATIC_D1_FALLBACK_OR_CREDENTIAL_BOUNDARY_FAILED")
    guards["host_allowlisted_DNSE_fallback_and_credential_redaction"]=True

    # 7. Original RVOL_TOD20 uses SAME LOCAL SLOT 20 distinct PRIOR
    # fabricated sessions (not 20 prior bars), with calendar NOT attested.
    target,prior=rvol_sample()
    result=calculate_rvol_tod20(target,prior,as_of_utc=
                                 __import__("test_rvol_tod_contract").AS_OF)
    _require(result.state is IndicatorState.COMPUTED_UNCALIBRATED
             and result.value==Decimal("1")
             and result.used_bar_count==21
             and not result.actionable and not result.data_certified
             and not result.parameter_approved,
             "RVOL_TOD20_NOT_EXACT_SAME_LOCAL_SLOT_OR_FALSE_TRADING")
    guards["RVOL_TOD20_20_prior_same_slot_synthetic_only"]=True
    double=replace(target,cumulative_matched_volume=2000)
    twice=rvol_fixture(target=double,prior=prior)
    missing=rvol_fixture(target=target,prior=prior[:-1])
    different=rvol_fixture(
        target=target,
        prior=(replace(prior[0],volume_definition=
                       CumulativeVolumeDefinition.MATCHED_INCLUDING_AUCTIONS),
               )+prior[1:])
    _require(twice.value==Decimal("2")
             and missing.state is IndicatorState.BLOCKED
             and different.state is IndicatorState.BLOCKED,
             "RVOL_TOD20_BAD_DENOMINATOR_OR_INCOMPATIBLE_VOLUME_POLICY")
    guards["RVOL_TOD20_missing_prior_or_auction_basis_blocks"]=True

    _require(len(guards)==14 and all(guards.values()),
             "FINAL_SEVEN_REAL_V1_PATHS_SYNTHETIC_SAFETY_GUARDS_FAILED")
    return {
        "schema":SCHEMA,
        "status":"FINAL_SEVEN_ORIGINAL_V1_PATHS_SCOPED_EXECUTION_PASS_OWNER_PRODUCTION_NO_GO",
        "original_upstream_sha":"cd90c1babae8912db31490ad614fc2ad2f868042",
        "protected_main_sha":"4048f91beaaa3410116d97e35896c8b688384e19",
        "executed_original_v1_file_paths":list(FILES),
        "domain_function_modules_executed":list(DOMAIN_MODULES),
        "package_init_coverage":"IMPORT_VERSION_AND_METADATA_ONLY",
        "prior_distinct_scoped_v1":56,
        "new_distinct_scoped_v1_files":7,
        "cumulative_scoped_original_v1_files":63,
        "remaining_original_v1_files_without_scoped_test":0,
        "full_behavioral_module_acceptances":0,
        "human_a02_owner_dispositions":0,
        "a03_full_v1_v2_abi_owner_accepted":False,
        "linked_invariants":guards,
        "linked_invariant_count":len(guards),
        "trusted_out_of_band_public_key_verified":False,
        "independent_HMAC_custodian_verified":False,
        "ed25519_independent_external_signer_enrolled":False,
        "actual_external_monotonic_floor_proven":False,
        "real_vendor_data_rights_verified":False,
        "real_mcp_provider_network_called":False,
        "real_google_drive_market_cache_accessed":False,
        "real_multiwriter_server_cas_verified":False,
        "vn_exchange_calendar_or_trading_authority_verified":False,
        "production_release_authorized":False,
        "trading_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    r=run_final_seven_originals()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",
                            encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="linked_invariants"},
                     sort_keys=True))


if __name__=="__main__":
    main()
