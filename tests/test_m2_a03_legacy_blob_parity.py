"""M2/A03 Git-blob byte-for-byte lock for every one of 63 legacy modules.

Pins were taken from the *immutable pinned main* at
4048f91beaaa3410116d97e35896c8b688384e19 and source tree
d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e.
This never clones, changes, or authorizes the original Swing Trading source.
"""
from hashlib import sha1
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "swing_trading"
V1_BLOB_SHA = {
    "__init__.py": "55a8ce1d21acc78edc57a41368ca4fe749e1e2c1",
    "adaptive_source_router.py": "42c0de05393c5a88c1af3ae726c8ad26723d3693",
    "b5_calibration_draft.py": "7df642aa41527b825ca0b866b99601f1964ebf16",
    "b5_feature_pack.py": "d7cbfd59376ee785f89606d3959f63602c8f60c9",
    "b5_formula_geometry.py": "216cdde40c79136ae73017c157778550c920f3e1",
    "b5_phase_contract.py": "0772f5f1c3751c0c02899a5a90c6e99391a650f5",
    "b5_temporal_split_audit.py": "a187b6cb70d1fa9a440ee4b5d07c7135b5431346",
    "backtest.py": "d4251209f4aa41565beaed1be9a4bde4ef9a610d",
    "c2_fair_source_benchmark.py": "24c2ae84dedb8d8365b82ce96eda23ce6eb7e878",
    "c2_session_probe_readiness.py": "d8b77c63c488fe394ed95ee0128356828b9f1e48",
    "c2_source_capability_audit.py": "09798cc21673290d5084c617e2fd76809179dc9d",
    "cache_fetch_planner.py": "ce7b239ee750162f84f5680c9ad9b87ff9ad6767",
    "cache_snapshot_bundle.py": "f4802272197dae16ccd96b88b7728a0df88cfad5",
    "cache_swap_preview.py": "5570fbf068376b6f25c5647860f3661bb73b315a",
    "causal_indicators.py": "6dce942bcf4bdcd512659a962ffaf571c69db967",
    "causal.py": "10899bb28bd1db98d8ed75ed42691ae13228f456",
    "contracts.py": "4cec604057ab9909a5af3971f3693ae9563e9d3f",
    "d1_atr_reconciliation.py": "5f7792a7f2900ee691f15d2a5cb8bc11d8db3acd",
    "d1_mcp_transport_bridge.py": "53e321c1baff805703244b703b392a2e7ff665b9",
    "dnse_d1_reference_fallback.py": "7712b112b386ac62f1ea4162c15436ae8686b4a4",
    "durable_evidence.py": "cead16f5ebecbee68eb0870dbdd0dcc1859165ab",
    "engine.py": "24fd35c68860a1bdabd10b14f21cf8f925178ef4",
    "engineering_contracts.py": "67d3edbb254606eea9bbbcbade1bd2ed1881adde",
    "engineering_release.py": "9e6941a48db35703c4edb33bce9359d555220022",
    "evidence_checkpoint.py": "71e5245800505817db592019c85f3d0b5b64bc27",
    "evidence_recovery.py": "54c54f7052b7f2cadaef459d2a9dd1f656335460",
    "fixture_scan.py": "af66306a8e901ec5489c5a65fc097b23de2b61af",
    "incremental_cache.py": "db06f6f0d63523d80ef3826c0f49a24c02d60be8",
    "legacy_migration.py": "8a5304e04fd3d8397d31c3f5b2207e0e64caef4a",
    "market_data.py": "4640b6aae7bcb7593436a964464dfc5d959a0c2a",
    "migration_archive.py": "a1a94e98cf817f825e91d0a1507f1a733ca1556d",
    "native_minute_bar_source_plan.py": "2893986a85e03d4b0ec44b957dbeb80f421c2362",
    "partition_chunk_cache.py": "30f4dd112a42c91905bf9abe95114dc7c58f70d9",
    "provider_custody_host_plan.py": "f692facd4e32304d33bbc6c1be33eb70101838f4",
    "provider_head_custody.py": "d937ea91bb70e811c038fef3fb4d48f2a3f2d662",
    "provider_review_packet.py": "7d9f2d01bcedfed6e70c78117e566785afe995a1",
    "provider_rights_review.py": "b653d8331caf34efa849bfeea7707be5234f4a19",
    "provider_signed_event_chain.py": "06abe9f357d6ad14c29a63c25aa4ae89e6e18c6c",
    "quality_audit.py": "17338936a008615c9403f0897b3c495660415df0",
    "reference_checkpoint_mac.py": "7d3356e608c0bbc2f389d19d814f1be1de287e4d",
    "reference_checkpoint_signature.py": "f322fd6c5031b8b67a368f03f9e3d46e5caea090",
    "reference_host_dryrun.py": "41c9049113360a19cdca93d7219b1c5cc9aced07",
    "reference_journal_recovery.py": "116dc20c040ef54d162582dcb2385e71fb46970e",
    "reference_journal.py": "213b243f7420be423ad180cd25ea9c25f66f1751",
    "reference_offline_verified_archive.py": "79d3ee9abad502cdbac10a3f1507abe4db43d58d",
    "reference_pinned_fd.py": "deb5c1ca6ce4bae083a948935ba843ff5819533e",
    "reference_storage_preflight.py": "5a50bccf93e764090a321d32c943b2d6430cbcf1",
    "replay_batch.py": "950e9672035a553d78af948186f5999fd086e777",
    "replay.py": "38c2b0a6c0cdf531e5b3ade6d68950d1cbeed97a",
    "rvol_tod_contract.py": "e9c28d56e98e25f69391fcb6c796981664870424",
    "segmented_cache.py": "b2f55a6fc3061114df5b46ea6b53439378aeba0f",
    "session_calendar.py": "e39b2dd58251f04200176c39504f2e63b158c383",
    "source_capability_evidence.py": "1c35247d56784e0aa95577fef3f7c1ca05a26431",
    "source_quality.py": "92fcb45745303fab4d1a39edd3af6ad85517a7ff",
    "ssi_historical_availability.py": "2f02dda4e21524c3b4d1a2d671b7c174e87ebdc2",
    "ssi_intraday_label_diagnostics.py": "2c7190a9c8eea66986b9f290ed21d4e35a15641b",
    "ssi_multivenue_review.py": "1e16fe9459de0c2e681b8417436691e14f9b20e3",
    "ssi_source_qualification.py": "f9d321d7cae7a0d19cafe8af3ac143aba1b70c60",
    "ssi_volume_parity.py": "428b4bf69dc088ef38f73d83c344889d69eb05a3",
    "vcbs_source_contract.py": "96d438bdb3829dd906fd78445745f9911f557776",
    "vn_2026_closure_anchors.py": "49c1fac5e693c8d733a769fa1c4f4652e6bf4492",
    "vn_backtest_execution_fixture.py": "3aafbf5575426748ae017d716d009b1f960116d7",
    "vn_release_rollback.py": "7836bb7513e51b14a551543ca8a9f61cb4b55ba5",
}
ALLOWED_NEW_OPT_IN_MODULES = frozenset(("strict_contract_v2.py", "v2_replay_port.py", "v2_source_adapter.py", "v2_provider_readiness.py", "v2_cache_partition_plan.py", "v2_cache_fencing_lab.py", "v2_cloud_ref_witness_plan.py"))


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + bytes((0,))
    return sha1(header + data).hexdigest()


class LegacySourceExactParityTests(unittest.TestCase):
    def test_every_original_v1_module_has_exact_pinned_git_blob(self):
        self.assertEqual(len(V1_BLOB_SHA), 63)
        for name, expected_sha in V1_BLOB_SHA.items():
            with self.subTest(module=name):
                path = SOURCE / name
                self.assertTrue(path.is_file())
                self.assertEqual(git_blob_sha(path.read_bytes()), expected_sha)

    def test_only_two_explicit_v2_modules_added_to_original_package(self):
        names = {path.name for path in SOURCE.glob("*.py")}
        self.assertEqual(
            names, set(V1_BLOB_SHA) | ALLOWED_NEW_OPT_IN_MODULES
        )
        self.assertEqual(len(names), 70)

    def test_original_package_metadata_remains_pinned(self):
        self.assertEqual(
            git_blob_sha((ROOT / "pyproject.toml").read_bytes()),
            "1cf5392d0d57089f011e0c68854bb2d060fcfe65"
        )


if __name__ == "__main__":
    unittest.main()
