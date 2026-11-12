# MST A02 — Sixth Distinct Eight Original V1 Replay, Migration, Evidence and Weekly Cache Runtime QA

QA ID: MST-A02-V1-SIXTH-EIGHT-REPLAY-EVIDENCE-MIGRATION-20261110
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: PASS 40/40 new actual inherited V1 tests, PASS 16/16 linked actual V1 business safety checks, PASS 29/29 GitHub Actions workflows at exact code/workflow HEAD. OWNER/EXTERNAL AUTHORITY/PRODUCTION/TRADING: NO-GO.
Draft PR: https://github.com/ngluonghoa/MST/pull/8 — Draft, unmerged.

## 1. Source lock and genuinely distinct eight V1 originals

Source pin original Swing Trading 1.8 cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19; exact original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. A read-only GitHub Actions job independently fetches actual upstream, main and PR candidate Git trees through GitHub REST before testing, confirming all 63 source-locked original V1 Python modules and eight pre-existing V2 opt-in sidecars remain unchanged.

This sixth tranche executes ORIGINAL V1 runtime implementations of eight modules not in the five earlier batches: replay_batch, quality_audit, legacy_migration, migration_archive, durable_evidence, evidence_recovery, evidence_checkpoint, segmented_cache.

Total grouped selected original-V1 synthetic execution breadth is now 6 × 8 = 48 DISTINCT original modules out of 63; 15 originals remain outside this kind of grouped runtime evidence. Existing H3/AST 63/63 API inventory is static only. Neither the 48 scoped runtime subsets nor their other historical unit tests establish all-behavior parity, production readiness, full V1→V2 ABI, or human owner approval. Current owner module dispositions = 0/63.

## 2. Sixteen real original V1 cross-domain checks

1. Replay M15/M5 source first_known, retrieval and verification clocks must all be respected; a known revision is not thereby verified, and M5 not yet known cannot become a negative signal.
2. Exact identical source+revision retransmissions deduplicate (3 copies → 1 visible candidate, 2 repeats counted), while same revision identity with DIFFERENT OHLC/digest is SOURCE_OR_REVISION_CONFLICT and no silent latest-wins winner.
3. Late revision r2 first_known at minute 40 remains invisible in snapshots at minutes 30/39; after it becomes known, conflicting candidates remain unresolved and unactionable.
4. Immutable quality finding registry preserves OPEN/BLOCK findings. Source timestamp/manifest lacks source rights even if synthetic structural requirements are true. A self-declared waiver with a reference string is NOT independent approval and does not clear a blocked dataset.
5. A legacy "VERIFIED" label is forcibly downgraded to V1.2 QualityState.UNVERIFIED/CoverageState.UNKNOWN on migration; zero known volume remains zero, not missing, and no confirmed trading signal becomes permitted.
6. Migrating mixed closed/unknown-lifecycle legacy records with explicit raw-byte bindings yields one STAGED_UNVERIFIED and one QUARANTINED receipt; 2 exact fabricated binary raw byte payloads are stored and verified in the real original EvidenceStore SQLite transaction chain.
7. A raw-source/snapshot identity mismatch or stale expected evidence chain-tip rejects the entire attempted migration before any append; existing (count,tip) remains unchanged. No automatic reconstruction from normalized OHLC.
8. Original EvidenceCheckpoint candidate creates a copy with SHA256, chain count and tip. Parsing the checkpoint JSON in the SAME test process and verifying backup is only a SELF-HELD PIN; never an authenticated independent owner/witness.
9. Mismatching checkpoint store ID or separately supplied chain tip is rejected by actual original verifier.
10. Original restore_from_pinned uses actual evidence_recovery backup/restore of SQLite and retains both binary records, state and hash chain; refuses overwriting existing destination.
11. Original backup_verified + restore_verified also directly execute on a separate new fixture path, with a no-clobber guarantee; this is local runner filesystem only, not geographic disaster recovery or physical Google Drive.
12. One-byte modified backup copy is rejected before restoring because it disagrees with the pinned byte digest.
13. Appending a new UNAPPROVED suffix from 2 to 3 evidence items preserves previously pinned historic chain prefix; the same caller controls the pin, so neither antirollback across separate actors nor revocation freshness is established.
14. A truncated/unrelated local SQLite chain cannot satisfy the same self-held prefix checkpoint.
15. SyntheticWeeklyChunkStore produces 3 first-weekly storage objects, REUSES all three on a clean no-op, and recomputes ONLY one window after a historical revision, preserving the unchanged other two. These are UTC Monday storage buckets, not official HOSE/HNX/UPCOM sessions, nor globally certified indicators.
16. A stale expected weekly manifest head is rejected locally; require_authorized_window_cache raises PermissionError. No real Drive upload/download, external writer CAS, independent ownership or source entitlements.

These are genuine calls to inherited V1 functions with synthetic input helpers imported from existing test modules. The original domain code is not mocked or patched. SQLite and in-memory weekly fixture objects run ONLY on ephemeral GitHub-hosted runners; no user Mac/MOCHI/local computation.

## 3. Additive files in draft PR #8

- scripts/m2_a02_sixth_eight_replay_evidence_migration_runtime_lab.py: real eight-module linked execution and 16 explicit non-authority safety checks, emits a NO-GO schema with 48 distinct-module count and all release flags false.
- tests/test_m2_a02_sixth_eight_replay_evidence_migration_runtime_lab.py: 40 focused positive/negative real V1 tests: as-known replay, conflict/dedup, no backdated corrections, quality registry, migration quarantine, source binding atomicity, evidence chain validation, checkpoint wrong store/tail/one-byte corruption, prefix retention, weekly no-op/revision and stale writer.
- .github/workflows/m2-a02-sixth-eight-replay-evidence-migration-runtime.yml: GitHub-hosted PR#8 only, permissions contents:read, first actual remote upstream/main/PR Git source tree check, then 40 tests + 16 linked safety checks. Retains only nonauthenticating 14-day synthetic JSON receipts.
- docs/MST_A02_SIXTH_EIGHT_REPLAY_EVIDENCE_MIGRATION_QA_20261110.md: this report and corresponding MST Google Drive QA mirror.

No original V1 module, existing V2 sidecar, protected main, ACL/ruleset/ref, real Drive market cache, real market provider endpoint, cryptographic identity grant, broker, release or trading operation changed.

## 4. Exact GitHub CI evidence and corrected intermediate failure

Successful code/workflow HEAD: 55851ff5a7a75638a8513aeadcb98fa835b88efc.
Dedicated original eight-module CI: https://github.com/ngluonghoa/MST/actions/runs/42776704806 — SUCCESS, 40/40 tests, 16/16 linked runtime guards, real original remote source-byte lock PASS. Synthetic checkpoint 2 rows, one unapproved later suffix 3 rows; 3 weekly chunks first, 3 reused, 1 new on historical revision; ALL external authorization fields false.
Foundation CI: https://github.com/ngluonghoa/MST/actions/runs/42776705134 — SUCCESS, Python3.11 2745/2745 and Python3.12 2745/2745, engineering 63/63, H2/H3/lint/wheel PASS.
29/29 GitHub Actions workflows SUCCESS at exact code/workflow HEAD.

First intermediate workflow at an earlier SHA failed due to an invalid unused synthetic OHLC fixture alteration violating the inherited original candle OHLC invariant. That invalid line was removed ONLY in the NEW review harness. Re-run at successful HEAD passed. Source-locked original V1/V2 code was never patched. Failed intermediate runs are explicitly not claimed as green.
The report-containing later HEAD needs its own separate CI status readback before claiming 29/29 there.

## 5. Security, external ownership and release limitations

Human A02 owner dispositions: 0/63. A03 full V1→V2 ABI/behavior parity: NOT ACCEPTED. OA01–OA06 actual owner approvals and G01–G08 independent cryptographic signer, nonresettable witness floor, two real independently authenticated writers/server CAS, licensed market feed, physical Google Drive bytes/ACL, revocation and provenance: all OPEN. M3/M4/M5/M8 production/trading: BLOCKED.

The self-copied SHA256 checkpoint is NOT external custody, a self-generated fixture is NOT source-authoritative OHLCV, local SQLite integrity is NOT multi-site/independent antirollback, and local content-addressed weekly chunks are NOT real physical Google Drive cache. No actual private market-data rights or trading action was verified.

## 6. Next safe step

Proceed with meaningful original V1 executed domain fixtures over the 15 remaining originals, prioritizing engineering/retention/reference storage and recovery/rollback paths. Continue source-byte parity and explicit NO-GO, owner review outside synthetic CI. Option A remains Cloud-only GitHub + Google Drive; never Mac/MOCHI/local or third Cloud.
