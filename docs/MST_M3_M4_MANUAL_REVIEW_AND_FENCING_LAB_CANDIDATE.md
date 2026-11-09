# MST M3/M4 — Deny-only readiness review + witness/fencing lab (NOT production)

**Status:** CANDIDATE ENGINEERING CONTRACT / SYNTHETIC CI VALIDATED / OWNER ACCEPTANCE OPEN / NO LIVE PROVIDER / NO GOOGLE DRIVE CACHE WRITE.  
**GitHub:** [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8). The original `main` remains source-locked to `4048f91beaaa3410116d97e35896c8b688384e19` with tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`.

## 1. M3 manual source review — reject fabricated readiness summaries

The initial `v2_provider_readiness.ProviderReadinessV2` had deny-by-default authority properties, but callers could construct the report dataclass directly with contradictory or incomplete `gates_present`, `missing_gates`, `unverified_gates` and `expired_or_revoked_gates` tuples, without passing through the review function. Even though its five authorization properties remained always `False`, a downstream display or human reviewer might have mistaken the malformed status list for a complete evaluation.

**Candidate fix** adds `ProviderReadinessV2.__post_init__` to check provider and endpoint identity, explicit UTC time, exact immutable `ProviderGate` tuples, no duplicates, disjoint MISSING/UNVERIFIED/REVOKED dispositions, completeness of all ten known gates, and agreement of observed gates with the listed dispositions. Four new negative/golden tests cover direct construction with missing/duplicate/contradictory/untyped data, malformed provider/time, and a forged structurally complete all-UNVERIFIED summary. Such a summary **still grants no rights**, because all five authorization properties remain false.

**Risk status:** The inherited H3 heuristic still marks this module **IMPROVE / HIGH_BRANCH_SCORE** (rough max branch 21). A threshold flag is a manual-review prompt, not proof that the code is defective. The correctness gap above was independently inspected and closed *on Draft PR #8 only*; broader production source entitlement and review governance remain unimplemented. Do not mark all M3 or A02 signoffs completed.

## 2. M4 in-memory witness lab: scope and explicit limits

`v2_cache_fencing_lab.py` models a single-object append-only manifest history on synthetic cache partition keys from `v2_cache_partition_plan.py`. It contains NO Google Drive client, external compare-and-swap primitive, Cloud storage, durable database, token, source request, signing/enrollment, provider credentials or data rights.

- `FixtureManifestV2` records exact partition SHA, content SHA **claimed by caller**, positive generation, previous manifest SHA, writer ID, fence epoch and UTC timestamp. Its own SHA256 is over canonical metadata in a unique `mst.cache.manifest.v2.lab_only` domain. **A SHA is not a publisher signature** and cannot validate licensed data by itself.
- `FixtureManifestWitnessV2.open_fence()` hands out successive per-partition epochs in **one process**. The in-memory value is neither an independently authenticated writer identity nor an external durable lease; an equivalent forged ticket is possible.
- `submit(partition, ticket, manifest, expected_head_digest=...)` checks active epoch, exact writer, partition, expected current head (local optimistic CAS), parent SHA, generation increment of exactly one and non-rewinding declared UTC. On all rejects, the old local head remains. These invariants model *future* distributed-fencing acceptance tests, not a Drive write authorization.
- `seal()` blocks future local fence issuance and head promotion but **does not erase** Google Drive data, revoke a real vendor key, or prove deletion.
- Recovery (a previous content digest selected from the same partition's accepted local history) must be expressed as a NEW generation referencing the current head and the chosen historical digest. Do not reset generation or overwrite prior manifests in place.
- **Decisive negative test:** two independent witness objects can each accept conflicting genesis heads for the SAME partition. Therefore this lab explicitly **FAILS** the production distributed-CAS requirement, even though per-witness operations pass local tests. Cross-account/out-of-band writers, signer spoofing, crash durability, missing leases, simultaneous Google Drive updates and remote last-writer-wins remain unresolved.
- Auth flags `cloud_cas_proven`, `independently_authenticated_witness`, `drive_write_authorized`, and manifest `live_data_authorized`, `drive_write_authorized`, `trading_authorized` are always false.

## 3. Test and parity evidence

`tests/test_m4_v2_cache_fencing_lab.py` adds **25** synthetic tests: digest determinism, generation/parent constraints, manifest immutability, type/UTC checks, stale expected heads, duplicate/replayed manifest, writer-epoch supersession, wrong provider/ticker/timeframe/price-basis, time rewind, revocation, ordered recovery, rejected foreign/unknown recovery, and independent-witness split-brain.

`tests/test_m3_v2_provider_readiness.py` adds **4** additional summary-construction tests. Together with the 1,454 previously verified tests, current source/test total is **1,483** per Python 3.11 and 3.12.

The 63 inherited source Python files are pinned byte-for-byte with SHA1 Git blob identifiers in `tests/test_m2_a03_legacy_blob_parity.py`, as is original `pyproject.toml`. The candidate branch adds exactly six separate opt-in v2 modules; `main` keeps its original 63. H3 current branch has **69** modules, with new witness `v2_cache_fencing_lab` provisional IMPROVE due score 23 (not an independently proven defect).

**Verified at source/test HEAD before this documentation-only commit:** [PR GitHub Actions #42557233379](https://github.com/ngluonghoa/MST/actions/runs/42557233379) and [push #42557228144](https://github.com/ngluonghoa/MST/actions/runs/42557228144), three required jobs PASS, Python 3.11 and 3.12 each 1,483 tests OK, 63 engineering checks OK, H2/H3 exact generated matrix and lint/wheel build/install PASS. After this Markdown change, revalidate all 3 required CI checks on the new exact PR HEAD before claiming it accepted.

## 4. M4 deployment prerequisites — still NOT DONE

The next operational implementation cannot simply call `Google_Drive.update_file` from several writers and treat the result as globally atomic. A supported external Cloud serialization / compare-and-swap protocol must be selected, authorization-controlled and tested for crash/out-of-band/forked writers; a single GitHub Actions concurrency group is not sufficient against outside writers. Producer must check actual vendor permits Cloud retention and derived processing (M3), independently verify provider source provenance/candle revisions, acquire a separately authenticated writer fence, persist immutable chunks, verify their canonical SHA/source rights, conditionally publish manifest with monotonic witness, and prove rollback/expiry/revocation. Otherwise **BLOCK all physical Cache persistence**.

No source/rights approval, CI green state or signed-v1-domain result in this lab permits execution, market-data ingestion, Cloud cache writes, release, or broker orders. The legacy Swing Trading domains, source files, package 0.0.1 and identifiers must remain pinned.

**Tracking:** [M3 rights Issue #9](https://github.com/ngluonghoa/MST/issues/9); [M4 Drive Cache Issue #10](https://github.com/ngluonghoa/MST/issues/10); [M2/A03 Issue #6](https://github.com/ngluonghoa/MST/issues/6); [A02 63-module audit Issue #4](https://github.com/ngluonghoa/MST/issues/4). All operational/owner-gated issues stay OPEN.
