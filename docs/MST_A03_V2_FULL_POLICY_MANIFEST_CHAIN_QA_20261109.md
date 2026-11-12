# MST A03 — Full-policy V2 manifest lineage / first-known correction QA

**QA ID:** MST-A03-MANIFEST-FULL-POLICY-001  
**Checkpoint:** 2026-11-10 Asia/Ho_Chi_Minh (work begun 2026-11-09)  
**Outcome:** **PASS for local, synthetic four-generation content-addressed manifest consistency. NOT an independently protected or authorized Google Drive publisher/cache.**

## Purpose

MST must first retain **1:1 Swing Trading V1 behavior and source bytes**, then evaluate opt-in V2 improvements without silently changing V1. Source pin `ngluonghoa/swing-trading-1-8@cd90c1babae8912db31490ad614fc2ad2f868042`; protected MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, same Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` (216 entries, 208 blobs); 63 inherited V1 Python modules **unchanged**, 8 preexisting V2 source sidecars **unchanged**. Work in [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8), never merged or deployed.

User selected **Option A: GitHub + Google Drive only**, no other Cloud, Mac, MOCHI or local project compute. All runtime assertions execute on GitHub-hosted ephemeral Python with synthetic-only V1 SQLite and independent EMA20/Wilder ATR14 oracle. No real SSI/DNSE/VCBS, broker, Google Drive market chunk I/O, key, credential or privileged GitHub ref/ruleset change.

## A03 proposed schema (strictly laboratory-only)

Added `scripts/m2_a03_v2_full_policy_manifest_draft.py` defining `MaterializedBarRevision` and `ManifestDraft` under schema `mst.a03.v2-cache-manifest-full-policy.synthetic.v1`. It is built from the previous **read-only V1→V2 full-rights consumer contract**, not an invented licensed data source.

A single candidate manifest binds:
- Explicit `scope_binding_sha256` covering **all inherited V1 CacheIdentity policy fields**, separate candidate V2 partition digest and the legacy project/instrument mapping; immutable legacy identity SHA.
- **Eight named policy versions**: rights, source resolution, quality, adjustment revision, calendar, aggregation, indicator version and indicator parameters. Existing `FixturePartitionV2.digest` by itself **does not include** all of these and MUST NOT authorize cache reuse.
- Current materialized synthetic closed-bar list, each with bar start/end, revision label, **first-known UTC** and content SHA256. Records are strictly ordered with no duplicate starts, known-after-end, never future-known beyond the snapshot as-of; a hash matches the full revision list.
- Separate SHA256 for current revised bar materialization and for persisted EMA20/ATR14 checkpoints, the latter validated using inherited full recompute **and an independent Decimal numerical oracle**.
- Local generation, previous-manifest SHA256 (genesis has no parent) and monotonic as-of, with explicit COLD/WARM/LINEAGE_ONLY/PRICE_CORRECTION stages. A correction may only first become known **after the prior generation's as-of**; retroactive changes are denied. Unsupported historical deletions and retroactive backfills are denied, not silently treated as latest-wins.

**Important:** This local chain is self-contained and caller-derived. A malicious owner of the fixture can rewrite every hash, parent and generation. It **does not** establish independent signer root G01, external non-resettable high-water G02, true two-auth writer server CAS G03, licensed source rights G04, physical Drive/Git custody G05 or production authorization. All G01–G08 remain OPEN.

## Executed four-stage V1-derived golden fixture

Actual inherited V1 `SyntheticIncrementalStore` is used on a GitHub Actions disposable SQLite, with twenty manufactured M5 closed bars. Four successive *real local materializations* are verified as one genesis-to-head chain:

| Generation | Stage | Effect checked |
| --- | --- | --- |
| G1 | COLD | 20 manufactured bars; inherited full recompute and independent EMA/ATR reference match |
| G2 | WARM | Re-fetch unchanged bar; materialized bar and indicator digests unchanged |
| G3 | LINEAGE_ONLY | Earlier bar 8 gets revision r2 first known at minute 22; bar revision digest changes, **indicator digest unchanged** |
| G4 | PRICE_CORRECTION | Earlier bar 5 gets new synthetic close and revision r2 first known minute 23; both digests change |

Snapshot as-of times are minutes 20, 21, 22 and 23. The revised bar cannot claim it was already visible in earlier snapshots. Every generation has an explicit local parent SHA256 and consistent full-rights binding; validation requires **G1 through the latest G4**, not an isolated adjacent pair.

## Negative tests and fail-closed boundaries

Added `tests/test_m2_a03_v2_full_policy_manifest_draft.py`: **45 regression tests**, including:
- Missing genesis, skipped generation, duplicate/reordered generation, wrong parent, clock rewinds and duplicate as-of timestamps.
- Changed rights-policy binding, changed provider/partition identity, incompatible indicator-policy version, duplicate/missing/unsorted policy entries.
- Future-known revised bar, retroactive metadata correction, retroactive price correction, rewritten payload posing as the old source revision, unrecorded historical deletion, unsupported old backfill.
- Unexpected indicator changes in WARM/LINEAGE_ONLY, missing indicator invalidation after PRICE_CORRECTION, mismatched materialized bar SHA, duplicate/unsorted bar starts, invalid digest, malformed stage or inconsistent genesis.
- Reproducible local hashes and explicit `False` permission/access/provenance fields.

A first [Foundation CI run #42664972709](https://github.com/ngluonghoa/MST/actions/runs/42664972709) correctly failed two **test constructions**: test forced as-of earlier than the input's own first-known time, so the immutable manifest constructor denied future-known data **before** the intended generation-level time-order assertion. The fixtures were corrected to be individually valid, then rewired locally to isolate generation clock ordering. **No V1, existing V2 source, or manifest security guard was relaxed.**

## Hosted CI proof (pre-report code HEAD)

At PR #8 code/head `ed95b686076fd0813d81f1071c7306b1c22fb121`:
- [Full-policy manifest cloud CI #42665626455](https://github.com/ngluonghoa/MST/actions/runs/42665626455) **SUCCESS**, four-stage chain and machine-readable local negative-authority JSON. This is only a temporary GitHub Actions review artifact.
- [Foundation #42665626460](https://github.com/ngluonghoa/MST/actions/runs/42665626460) **SUCCESS 3/3**: Python 3.11 **2142/2142**, Python 3.12 **2142/2142**, engineering **63/63**, source H2/H3/lint/wheel PASS.
- Other 13 exact code-HEAD workflows successful, including upstream/main/PR V1 source tree parity and M4 no-apply blocking gates: **15/15** exact-HEAD workflow types SUCCESS.
- This technical report changes the PR HEAD; final documentation-containing SHA needs separate exact-HEAD workflow readback before claiming full checkpoint success.

New review-only files: `scripts/m2_a03_v2_full_policy_manifest_draft.py`, `tests/test_m2_a03_v2_full_policy_manifest_draft.py`, `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml`, this report. Workflows use `permissions: contents: read`, no production writes/secrets.

## Required architecture decisions before any real Google Drive publisher

1. **External trust and root separation:** G01 signer custody, G02 nonresettable floor under effective admin/root, G03 real two separately authenticated writer CAS and G06 revocation need actual independent owner evidence. A self-hashed manifest is not one.
2. **Actual data rights:** G04 provider SSI/DNSE/VCBS entitlement and first-known correction provenance; G05 physical Drive chunk bytes, immutability/recovery and independent cross-service read barrier. Cannot infer these from simulated SHA256.
3. **Full-rights V2 schema acceptance:** keep all original V1 identity and policy epochs; define versioned deletion/backfill/tombstone events with first-known and independent signed provenance before allowing them; never treat `FixturePartitionV2.digest` as the whole source identity.
4. **A02/A03 release:** owner per-module 63 original source dispositions and V2 strict ABI/behavior migration signoff remain OPEN; draft candidate has no validated production market-cache reader or trading engine.

**Verdict:** `FULL_POLICY_LOCAL_DRAFT_MANIFEST_CHAIN_PASS; SOURCE_1TO1_PRESERVED; OWNER_A02_A03_G01_G08_BLOCKED; LIVE_GDRIVE_CACHE_NOT_IMPLEMENTED`.

**Next safe step:** document the versioned tombstone/deletion/backfill contract with authenticated first-known source events and explicit fail-closed recovery semantics, still on GitHub-hosted synthetic tests and WITHOUT physical Google Drive market writes or privileged GitHub changes.
