"""Final A02 originals: 40 scoped real-source synthetic tests, NO authority.

Six inherited domain-function modules actually invoked plus __init__ import
metadata only. No full functional, live source, owner, V2 parity or trade grant.
"""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import base64
from pathlib import Path
import unittest

import swing_trading
from scripts.m2_a02_final_seven_original_v1_runtime_lab import (
    FILES, DOMAIN_MODULES, SCHEMA, MAC_KEY, build_cache_fixture,
    build_archive_fixture, _sig_args, _archive_args,
    run_final_seven_originals,
)
from swing_trading.cache_swap_preview import (
    compare_synthetic_cache_backends, FixtureCacheSwitchReview,
)
from swing_trading.reference_checkpoint_mac import (
    DetachedJournalMac, create_candidate_detached_mac,
    verify_detached_journal_mac, verify_authenticated_journal_backup,
)
from swing_trading.reference_checkpoint_signature import (
    DetachedJournalSignature, verify_detached_journal_signature,
    signature_payload,
)
from swing_trading.reference_offline_verified_archive import (
    verify_offline_signed_metadata_archive,
)
from swing_trading.reference_journal import ReferenceJournalCorrupt
from swing_trading.reference_host_dryrun import (
    StaticMcpFixture, FixtureOnlyD1HostHarness,
)
from swing_trading.dnse_d1_reference_fallback import D1Provider, D1ReadState
from swing_trading.rvol_tod_contract import (
    CumulativeVolumeDefinition, calculate_rvol_tod20,
)
from swing_trading.causal_indicators import IndicatorState, VolumeSessionClass
from swing_trading.market_data import Timeframe
from test_partition_chunk_cache import bar as cache_bar, NOW as CACHE_NOW
from test_reference_host_dryrun import fixture as host_fixture
from test_d1_mcp_transport_bridge import ssi_payload, dnse_payload
from test_dnse_d1_reference_fallback import request as d1_request, NOW as D1_NOW
from test_rvol_tod_contract import sample as rvol_sample, calculate as rvol_fixture


class FinalSevenOriginalV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=run_final_seven_originals()

    def _archive(self):
        f=build_archive_fixture()
        self.addCleanup(f.doCleanups)
        return f

    def _mac(self,f):
        return create_candidate_detached_mac(
            f.cp,signing_key=MAC_KEY,key_id="mac-fixture",
            sealed_at_utc=D1_NOW+timedelta(seconds=1),
        )

    def _host(self,ssi=None,dnse=None):
        return FixtureOnlyD1HostHarness(
            ssi=ssi or host_fixture(D1Provider.SSI,ssi_payload()),
            dnse=dnse or host_fixture(D1Provider.DNSE,dnse_payload()),
            clock_utc=D1_NOW-timedelta(minutes=1),
        )

    # 1–5 packet scope; __init__ never claimed domain behavior
    def test_01_seven_remaining_original_paths_exactly(self):
        self.assertEqual(len(FILES),7)
        self.assertEqual(len(set(FILES)),7)
        self.assertEqual(self.receipt["executed_original_v1_file_paths"],list(FILES))

    def test_02_six_actual_domain_modules_plus_init_metadata(self):
        self.assertEqual(len(DOMAIN_MODULES),6)
        self.assertEqual(self.receipt["package_init_coverage"],
                         "IMPORT_VERSION_AND_METADATA_ONLY")
        self.assertEqual(swing_trading.__version__,"0.0.1")
        self.assertIn("not a validated trading system",swing_trading.__doc__)

    def test_03_56_plus_seven_is_63_scoped_only(self):
        self.assertEqual(self.receipt["previous_distinct_scoped_v1"],56)
        self.assertEqual(self.receipt["cumulative_scoped_original_v1_files"],63)
        self.assertEqual(self.receipt["remaining_original_v1_files_without_scoped_test"],0)
        self.assertEqual(self.receipt["full_behavioral_module_acceptances"],0)

    def test_04_thirteen_joined_checks_actual_original_functions(self):
        self.assertEqual(self.receipt["schema"],SCHEMA)
        self.assertEqual(self.receipt["linked_invariant_count"],13)
        self.assertTrue(all(self.receipt["linked_invariants"].values()))
        self.assertIn("NO_GO",self.receipt["status"])

    def test_05_owner_prod_trading_all_no_go(self):
        self.assertEqual(self.receipt["human_a02_owner_dispositions"],0)
        for k in ("a03_full_v1_v2_abi_owner_accepted",
                  "trusted_out_of_band_public_key_verified",
                  "independent_HMAC_custodian_verified",
                  "ed25519_independent_external_signer_enrolled",
                  "actual_external_monotonic_floor_proven",
                  "real_vendor_data_rights_verified",
                  "real_mcp_provider_network_called",
                  "real_google_drive_market_cache_accessed",
                  "real_multiwriter_server_cas_verified",
                  "vn_exchange_calendar_or_trading_authority_verified",
                  "production_release_authorized","trading_authorized"):
            with self.subTest(k=k): self.assertFalse(self.receipt[k])

    # 6–11 actual original cache backend comparison
    def test_06_equal_c3b_and_c4a_fixture_histories_only(self):
        k,b,a,c=build_cache_fixture()
        r=compare_synthetic_cache_backends(
            k,old_backend=a,candidate_backend=c,
            pinned_old_sha256=a.get_head(k),pinned_candidate_sha256=c.get_head(k))
        self.assertTrue(r.fixture_equivalent)
        self.assertEqual((r.old_rows,r.candidate_rows),(20,20))
        self.assertFalse(r.real_migration_approved)
        self.assertFalse(r.trading_authorized)

    def test_07_mismatching_pinned_old_head_denied(self):
        k,b,a,c=build_cache_fixture()
        with self.assertRaises(ValueError):
            compare_synthetic_cache_backends(
                k,old_backend=a,candidate_backend=c,
                pinned_old_sha256="0"*64,pinned_candidate_sha256=c.get_head(k))

    def test_08_mismatching_pinned_candidate_head_denied(self):
        k,b,a,c=build_cache_fixture()
        with self.assertRaises(ValueError):
            compare_synthetic_cache_backends(
                k,old_backend=a,candidate_backend=c,
                pinned_old_sha256=a.get_head(k),pinned_candidate_sha256="0"*64)

    def test_09_same_backend_cannot_be_called_replacement(self):
        k,b,a,c=build_cache_fixture()
        with self.assertRaises(ValueError):
            compare_synthetic_cache_backends(
                k,old_backend=a,candidate_backend=a,
                pinned_old_sha256=a.get_head(k),pinned_candidate_sha256=a.get_head(k))

    def test_10_mutated_historic_revision_not_equivalent(self):
        k,b,a,c=build_cache_fixture()
        changed=b[:1]+(cache_bar(1,close=Decimal("333"),revision="r2"),)+b[2:]
        c.commit(k,changed,expected_head=c.get_head(k),observed_at_utc=CACHE_NOW)
        r=compare_synthetic_cache_backends(
            k,old_backend=a,candidate_backend=c,
            pinned_old_sha256=a.get_head(k),pinned_candidate_sha256=c.get_head(k))
        self.assertFalse(r.fixture_equivalent)
        self.assertIn("BAR_OR_REVISION_OR_FIRST_KNOWN_MISMATCH",r.reasons)

    def test_11_cache_comparison_authority_flag_cannot_flip(self):
        k,b,a,c=build_cache_fixture()
        r=compare_synthetic_cache_backends(
            k,old_backend=a,candidate_backend=c,
            pinned_old_sha256=a.get_head(k),pinned_candidate_sha256=c.get_head(k))
        with self.assertRaises(PermissionError):
            replace(r,real_migration_approved=True)

    # 12–17 actual original detached HMAC, one locally controlled test key
    def test_12_MAC_valid_selfheld_fixture_key_only(self):
        f=self._archive();mac=self._mac(f)
        self.assertEqual(verify_detached_journal_mac(
            f.cp,mac,verification_key=MAC_KEY,expected_key_id="mac-fixture",
            expected_store_id="store1"),f.cp)

    def test_13_MAC_canonical_roundtrip(self):
        f=self._archive();mac=self._mac(f)
        self.assertEqual(DetachedJournalMac.parse_json(mac.canonical_json()),mac)

    def test_14_MAC_wrong_key_denied(self):
        f=self._archive();mac=self._mac(f)
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_detached_journal_mac(f.cp,mac,verification_key=b"x"*32,
                                        expected_key_id="mac-fixture",
                                        expected_store_id="store1")

    def test_15_MAC_wrong_store_binding_denied(self):
        f=self._archive();mac=self._mac(f)
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_detached_journal_mac(f.cp,mac,verification_key=MAC_KEY,
                                        expected_key_id="mac-fixture",
                                        expected_store_id="other-store")

    def test_16_MAC_short_or_nonbytes_key_denied(self):
        f=self._archive()
        with self.assertRaises(ValueError):
            create_candidate_detached_mac(
                f.cp,signing_key=b"short",key_id="mac-fixture",
                sealed_at_utc=D1_NOW+timedelta(seconds=1))

    def test_17_MAC_backup_verified_not_custodian_verified(self):
        f=self._archive();mac=self._mac(f)
        r=verify_authenticated_journal_backup(
            f.archive,f.cp,mac,verification_key=MAC_KEY,
            expected_key_id="mac-fixture",expected_store_id="store1")
        self.assertEqual(r[0],1)
        self.assertFalse(self.receipt["independent_HMAC_custodian_verified"])

    # 18–22 actual original signed Ed25519 checkpoint verifier
    def test_18_signature_canonical_roundtrip(self):
        f=self._archive()
        self.assertEqual(DetachedJournalSignature.parse_json(
            f.seal.canonical_json()),f.seal)

    def test_19_signature_valid_against_caller_supplied_fingerprint(self):
        f=self._archive()
        self.assertEqual(verify_detached_journal_signature(
            f.cp,f.seal,**_sig_args(f)),f.cp)

    def test_20_signature_invalid_public_fingerprint_rejected(self):
        f=self._archive()
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_detached_journal_signature(
                f.cp,f.seal,**{**_sig_args(f),"expected_public_key_sha256":"0"*64})

    def test_21_signature_validly_formatted_but_wrong_bytes_rejected(self):
        f=self._archive()
        forged=replace(f.seal,signature_base64=base64.b64encode(b"\x00"*64).decode("ascii"))
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_detached_journal_signature(f.cp,forged,**_sig_args(f))

    def test_22_signing_payload_requires_checkpoint_not_future_injection(self):
        f=self._archive()
        with self.assertRaises(ValueError):
            signature_payload(f.cp,key_id="key1",
                              signed_at_utc=f.cp.created_at_utc-timedelta(seconds=1))

    # 23–27 original offline verified metadata-only signed archive
    def test_23_pinned_offline_archive_metadata_only(self):
        f=self._archive();r=verify_offline_signed_metadata_archive(**_archive_args(f))
        self.assertEqual(r.journal_records,1)
        self.assertTrue(r.metadata_only)
        self.assertTrue(r.signed_manifest_checked)
        self.assertFalse(r.market_data_certified)

    def test_24_archive_sha_and_tip_equal_pinned_checkpoint(self):
        f=self._archive();r=verify_offline_signed_metadata_archive(**_archive_args(f))
        self.assertEqual(r.chain_tip_sha256,f.cp.chain_tip_sha256)
        self.assertEqual(r.archive_sha256,f.cp.backup_sha256)

    def test_25_offline_archive_modified_bytes_denied(self):
        f=self._archive();raw=f.archive.read_bytes()
        path=f.root/"tampered.sqlite"
        path.write_bytes(raw[:32]+bytes([raw[32]^1])+raw[33:]);path.chmod(0o600)
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_offline_signed_metadata_archive(**{**_archive_args(f),"archive":path})

    def test_26_offline_archive_sidecar_present_denied(self):
        f=self._archive()
        sidecar=Path(str(f.archive)+"-wal");sidecar.write_bytes(b"fixture")
        sidecar.chmod(0o600)
        with self.assertRaises(Exception):
            verify_offline_signed_metadata_archive(**_archive_args(f))

    def test_27_offline_archive_forged_archive_key_pin_denied(self):
        f=self._archive()
        with self.assertRaises(ReferenceJournalCorrupt):
            verify_offline_signed_metadata_archive(
                **{**_archive_args(f),"expected_public_key_sha256":"0"*64})

    # 28–33 actual original offline MCP host envelope
    def test_28_host_SSI_reference_only_one_shot(self):
        h=self._host();r=h.run_once(d1_request())
        self.assertEqual(r.endpoint_order,("SSI.marketdata_list_daily_stock_infor",))
        self.assertIs(r.run.audit.state,D1ReadState.PRIMARY_SSI_REFERENCE_ONLY)
        self.assertFalse(r.live_mcp_deployed)
        self.assertFalse(r.production_authorized)

    def test_29_host_denies_reused_one_shot_session(self):
        h=self._host();h.run_once(d1_request())
        with self.assertRaises(PermissionError):h.run_once(d1_request())

    def test_30_host_DNSE_fallback_only_after_approved_source_error(self):
        err=host_fixture(D1Provider.SSI,{"status":"error","error":"DOWNSTREAM_UNAVAILABLE"})
        h=self._host(ssi=err);r=h.run_once(d1_request())
        self.assertEqual(r.endpoint_order,(
            "SSI.marketdata_list_daily_stock_infor","DNSE.price_get_history"))
        self.assertIs(r.run.audit.state,D1ReadState.FALLBACK_DNSE_REFERENCE_ONLY)
        self.assertFalse(r.run.historical_backtest_qualified)

    def test_31_host_unapproved_error_no_DNSE_fallback(self):
        err=host_fixture(D1Provider.SSI,{"status":"error","error":"PERMISSION_DENIED"})
        with self.assertRaises(ValueError):
            self._host(ssi=err).run_once(d1_request())

    def test_32_host_rejects_nested_credential_in_fixture(self):
        with self.assertRaises(ValueError):
            host_fixture(D1Provider.SSI,{"data":{"token":"forbidden"}})

    def test_33_host_no_native_M1_substitution(self):
        h=self._host();r=h.run_once(d1_request(Timeframe.M1))
        self.assertEqual(r.endpoint_order,())
        self.assertFalse(r.actionable)

    # 34–40 actual original RVOL_TOD20 same LOCAL slot contract
    def test_34_RVOL_TOD_20_prior_unique_sessions_is_one(self):
        r=rvol_fixture()
        self.assertIs(r.state,IndicatorState.COMPUTED_UNCALIBRATED)
        self.assertEqual(r.value,Decimal("1"))
        self.assertEqual(r.used_bar_count,21)
        self.assertFalse(r.actionable)

    def test_35_RVOL_TOD_two_times_target_cumulative_is_two(self):
        t,p=rvol_sample()
        self.assertEqual(rvol_fixture(
            target=replace(t,cumulative_matched_volume=2000),prior=p).value,
            Decimal("2"))

    def test_36_RVOL_TOD_only_19_prior_sessions_blocked(self):
        t,p=rvol_sample()
        self.assertIs(rvol_fixture(target=t,prior=p[:-1]).state,IndicatorState.BLOCKED)

    def test_37_RVOL_TOD_incompatible_auction_volume_definition_blocked(self):
        t,p=rvol_sample()
        pr=(replace(p[0],volume_definition=
                    CumulativeVolumeDefinition.MATCHED_INCLUDING_AUCTIONS),)+p[1:]
        self.assertIs(rvol_fixture(target=t,prior=pr).state,IndicatorState.BLOCKED)

    def test_38_RVOL_TOD_mismatching_elapsed_trading_minutes_blocked(self):
        t,p=rvol_sample()
        pr=(replace(p[0],elapsed_trading_minutes=31),)+p[1:]
        self.assertIs(rvol_fixture(target=t,prior=pr).state,IndicatorState.BLOCKED)

    def test_39_RVOL_TOD_duplicate_prior_local_session_denied(self):
        t,p=rvol_sample()
        pr=(p[0],)+p[:-1]
        self.assertIs(rvol_fixture(target=t,prior=pr).state,IndicatorState.BLOCKED)

    def test_40_final_receipt_repeatable_full_owner_no_go(self):
        self.assertEqual(run_final_seven_originals(),self.receipt)
        self.assertEqual(self.receipt["human_a02_owner_dispositions"],0)
        self.assertFalse(self.receipt["trading_authorized"])


if __name__=="__main__":
    unittest.main()
