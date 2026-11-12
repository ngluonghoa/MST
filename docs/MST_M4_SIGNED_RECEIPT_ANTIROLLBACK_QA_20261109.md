# MST M4 — Signed manifest receipt and monotonic floor: proof of boundaries, not production custody

**Checkpoint:** 2026-11-09 (Asia/Ho_Chi_Minh) · **Mode:** Source-locked, test-only cloud-hosted GitHub Actions. **Policy:** DO NOT provision a production witness or change GitHub rulesets without owner approval. PR #8 remains Draft/unmerged.

## Original source lock, scoped inspection and implementation choice

- Swing Trading 1.8 source commit: `cd90c1babae8912db31490ad614fc2ad2f868042`. MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`; **all 63 inherited v1 Python modules unchanged**, original `pyproject.toml` untouched.
- Reviewed opt-in existing candidate source (NOT modified): `v2_cache_fencing_lab.py` blob `f5fdc6d3cbbd235a48887aab0053ce96455c1089`, `v2_cloud_publish_verify_lab.py` blob `33aa30fb1a1d3a9010006972deeb088f6898c636`, `v2_cloud_ref_witness_plan.py` blob `a67240de25e25f09369b45213d31ca5f01424d4e`, `v2_cache_partition_plan.py` blob `8110a9aa45f45c76f403d08a766b74a3beab8b4c`. Previous A02 findings: local-in-memory witness, optional/partition-unbound reader floor, caller metadata claims untrusted, no true distributed CAS.
- Existing `pyproject.toml` has optional `custody` dependency `cryptography>=43,<50` already installed by Foundation CI. This checkpoint does not modify dependency versions.
- New test-only `scripts/m4_signed_floor_fixture.py`: an **actual Ed25519 public-key signature verifier** over stable canonical JSON bytes (not simply checking a SHA256 field), with explicit fixture `FixtureAnchor` and `FixtureFloor`. **No private signing keys stored or produced in this script.** Keys are freshly generated in memory inside each `tests/test_m4_signed_floor_fixture.py` unittest. No tokens, privileged writer, market data, GitHub branch updates or Google Drive I/O.
- Important: `FixtureAnchor` and `FixtureFloor` are **CALLER-SUPPLIED**. Their presence and successful signature validation do not establish the signer as an authorized vendor/writer; the caller could substitute both. No opt-in V2 public ABI or original source was modified.

## Test-only signed receipt contract and controlled evidence

Signed receipt has a fixed schema and *exact* fields: `provider` (SSI/DNSE/VCBS label only), `partition_digest`, `rights_policy_digest`, `signer_id`, `key_epoch`, `generation`, `parent_receipt_digest`, `content_digest`, `source_first_known_utc`, `observed_at_utc`, `published_at_utc`, `recovery_of_receipt_digest`. Canonical JSON serialization is deterministic. The supplied `FixtureAnchor` pins provider, partition, rights-policy digest, signer ID, key epoch and Ed25519 32-byte public key. The supplied `FixtureFloor` has current generation, head receipt digest, source clock stamps and a tuple of already seen content digests.

All accepted outcomes explicitly return `FIXTURE_SIGNATURE_AND_CALLER_FLOOR_CONSISTENT_UNATTESTED`. Fields `independent_signer_custody_verified`, `authenticated_vendor_source_clock_verified`, `globally_durable_monotonic_floor_verified`, `distributed_two_writer_cas_verified`, `google_drive_byte_custody_verified`, `licensed_market_data_authorized`, `cache_write_authorized`, and `trading_authorized` are **all false**.

| 18 deterministic negative/positive cases | Observed result and boundary |
| --- | --- |
| G1→G2 chain with valid Ed25519 signatures | Locally consistent increasing generations, parent digest and signed receipt; remains UNATTESTED and non-authorizing |
| Modify signed body/content afterward | Cryptographic signature verification rejects mutation |
| Sign with a different private key while retaining pinned public key | Invalid signature rejected |
| Replace both caller-provided public key and floor, sign with another key | **Cryptographically valid but still UNATTESTED**: proof a self-selected signer key does NOT establish external authority |
| Transplant floor from different partition | Rejected by partition-bound floor identity check |
| Transplant floor from different rights-policy namespace | Rejected |
| Wrong provider, partition, policy, signer or key epoch in receipt | Rejected |
| Floor epoch differs from pinned signer key epoch | Rejected |
| Incorrect parent, jumped generation, boolean generation | Rejected |
| Re-sign old content SHA with generation/clock advanced | Rejected as replay using **caller-supplied** local seen-digest history |
| Claim recovery-of without independent owner authorization | Rejected; explicit recovery is not implemented |
| Re-sign but backdate first-known clock | Rejected by local monotonic floor |
| First-known later than observation or publication before observation | Rejected by clock-order check |
| Invalid UTC clock or extra schema field | Rejected |
| Garbage or absent signature | Rejected |
| **Two different valid signed G1 children from identical G0 floor** | **Both independently accepted as local fixtures**. This proves Ed25519 alone **does not provide distributed single-winner CAS**. Later mismatched parent rejected against a chosen local head, but each writer could choose a different local head. |
| **Reset the ephemeral floor after valid G1/G2, re-verify old G1** | **Old valid G1 accepted again**. Without independently protected durable last-accepted floor, a valid signature plus chain field DOES NOT prevent rollback. |
| Re-sign a different digest while underlying original OHLCV could still be stale | Fixture accepts structurally novel digest, but vendor truth/first-known verification flags remain FALSE. Cryptographic digest identity is not licensed source-data freshness. |

**Important policy nuance:** the fixture enforces strictly increasing first-known/observed/published clocks for each generation; this is a conservative synthetic negative guard and is **not yet an approved market-data correction policy**. Real vendor late corrections, backfills, tombstones, calendar changes and historical as-of semantics require independent provenance/retention/legal rights approval. Do not use this fixture's strict clock rule as a release strategy without signoff.

## Exact CI and GitHub cloud boundaries

Code and tests candidate HEAD `b9ab3c9513e6768d9ebc7bd621592105ad5fba8e`: [GitHub Actions Foundation #42598542614](https://github.com/ngluonghoa/MST/actions/runs/42598542614) **SUCCESS 3/3**, Python3.11 **1,675/1,675**, Python3.12 **1,675/1,675**, engineering **63/63** plus source/contract lint and wheel checks. Existing PR-only read-only remote GitHub ruleset/ref and synthetic inter-run cache workflows remained green at this code head. The technical-report-containing final HEAD requires its *own* exact-head CI check.

## Owner-controlled acceptance gates still OPEN

1. **SIGNED-G01 — External trust anchor:** owner-approved key enrollment, identity/role/rights-policy binding, key provenance and signature verification independent of candidate and writer-controlled metadata, including public-key rotation/revocation/compromise.
2. **SIGNED-G02 — Durable external monotonic floor:** last accepted per-canonical-partition+provider+policy generation, signed head, source first-known clock, publishing epoch and seen revision digests survive writer restart/new run/new account and cannot be removed, reset, shortened or transplanted by the writer.
3. **SIGNED-G03 — Real atomic winner/loser:** two independently authenticated writers race siblings of same externally protected head; exactly one authorized head transition under *server-side* CAS with definitive fail-closed loser, independent witnesses and after-crash readback. Existing same-account GitHub non-force tests do not meet it.
4. **SIGNED-G04 — Authenticated original vendor facts:** demonstrate licensed SSI/DNSE/VCBS read permissions, source revisions and first-known clocks, market-calendar/currentness, lawful Google Drive retention, historical data correction/tombstone/recovery policy and no lookahead/replay. An Ed25519 signature by a writer cannot confer vendor rights.
5. **SIGNED-G05 — Actual two-service bytes and crash proof:** fetch physical immutable Google Drive object bytes with authenticated SHA, compare protected GitHub commit/tree/ref with durable journal/floor, inject stage/promote/unknown-response faults, verify deterministic recovery without divergent heads or false success.
6. **SIGNED-G06 — Signed key/rights changes:** authorized epoch rotation and revocation must fence old writers and old policy rights globally, not just in one process. New owner-verified anchor must itself be protected by independent governance.
7. **SIGNED-G07 — Trust tier receipts:** explicitly separate `LOCAL_SIGNATURE_SHAPE_VALID`, `EXTERNAL_SIGNER_ATTESTED`, `DURABLE_HEAD_AND_CAS_PROVEN`, `LICENSED_SOURCE_ASOF_PROVEN`, and `PRODUCTION_CUSTODY_AUTHORIZED`; no implicit transition from synthetic success or hashing.
8. **SIGNED-G08 — Owner parity/release control:** maintain Swing Trading v1 63-module source lock, no change to default opt-in V2 ABI without [A03 Issue #6](https://github.com/ngluonghoa/MST/issues/6), A02 63 owner final dispositions and M3/M4/M8 signoff. Keep Draft PR #8 unmerged.

**Other blocking issues:** [#15 witness ref and policy](https://github.com/ngluonghoa/MST/issues/15), [#13 multiwriter](https://github.com/ngluonghoa/MST/issues/13), [#14 cross-service floor](https://github.com/ngluonghoa/MST/issues/14), [#10 physical M4 Cloud](https://github.com/ngluonghoa/MST/issues/10), [#11 first-known rewind](https://github.com/ngluonghoa/MST/issues/11), [#12 historical as-of](https://github.com/ngluonghoa/MST/issues/12). Proposed `WITNESS-PROV-G01..G06` still open; ruleset `MST - M4 Protected Witness (proposed)` and ref `mst/m4-witness/v1` were NOT installed/created. Production release and trading are forbidden.

**MST Cloud-only:** all new code/QA/report in the connected GitHub repository, all CI on GitHub-hosted runners and canonical docs in Google Drive. No Mac, MOCHI, external local development, proprietary vendor payloads or real production cache.
