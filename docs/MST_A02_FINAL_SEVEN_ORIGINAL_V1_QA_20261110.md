# MST A02 — FINAL SEVEN ORIGINAL V1 FILES: CACHE PARITY, HMAC/Ed25519, OFFLINE ARCHIVE, STATIC HOST & RVOL_TOD

QA ID: MST-A02-FINAL-SEVEN-ORIGINAL-V1-SCOPED-QA-20261110
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Final conclusion: **All 63/63 inherited original V1 Python file paths have a limited scoped executed test or (for __init__.py only) import/metadata check. Exactly ZERO originals have A02 formal owner module dispositions.** Entire original V1 source is byte-for-byte preserved, but full behavioral equivalence, V2 ABI certification, independent external roots, vendor rights, real physical Drive market cache and trading remain NO-GO.

Draft PR #8: https://github.com/ngluonghoa/MST/pull/8 — DRAFT, UNMERGED. Option A Cloud-only GitHub + Google Drive; no user Mac/MOCHI/local, no third Cloud.

## 1. Source identity and precisely bounded last-seven scope

Swing Trading 1.8 upstream commit cd90c1babae8912db31490ad614fc2ad2f868042. Protected MST main 4048f91beaaa3410116d97e35896c8b688384e19. Original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. On an ephemeral GitHub Actions runner, a separate live GitHub REST remote tree lock verifies **63 inherited original V1 Python source paths and eight already-existing opt-in V2 sidecar source files still identical** against upstream/main/PR, before running the new tests.

Last seven distinct original V1 file paths:
- __init__: import/version/disclaimer **only**, no domain function and no trading behavior claim.
- cache_swap_preview: ACTUAL original synthetic cache backend substitution comparator; C3B vs C4A; nonauthorizing.
- reference_checkpoint_mac: ACTUAL original detached HMAC-SHA256 create/verify and metadata-backup verification; one locally held test key is not an independent custodian.
- reference_checkpoint_signature: ACTUAL original verifier-only detached Ed25519 check with caller-pinned test public key/fingerprint; fixture private signer is not externally approved or enrolled.
- reference_host_dryrun: ACTUAL original static SSI-first/DNSE-only-on-approved-error D1 envelope harness; no MCP provider network call.
- reference_offline_verified_archive: ACTUAL original pinned-inode SQLite metadata-only backup verifier with in-memory deserialization; no live WAL, raw SSI/DNSE quote cache or real Drive API.
- rvol_tod_contract: ACTUAL original RVOL_TOD20 candidate using target and exactly 20 distinct prior local sessions' same-slot cumulative matched volumes; not RVOL_TF20, not data source entitlement, not a signal.

The previous seven nonoverlapping batches covered 56 distinct original V1 modules with *limited* synthetic real-code cases. This last batch adds six domain modules and one metadata-only __init__ path. Therefore **63/63 ORIGINAL V1 FILE PATHS have scoped runtime/import review, with ZERO files left without this breadth-level QA**. This is NOT 63/63 full module behavioral certification, exhaustive branch coverage, independent business acceptance or V1→V2 ABI parity. A02 HUMAN OWNER DISPOSITIONS: **0/63**. A03 full V2 ABI/behavior owner acceptance OPEN.

## 2. Thirteen cross-domain safety assertions against actual inherited V1 code

1. Original package __version__ is 0.0.1; __init__ disclaimer explicitly describes engineering scaffold not a validated trading system. NO business functionality asserted for this module.
2. Original cache_swap_preview compares 20 fabricated closed bars from original SyntheticDrivePartitionIndex and SyntheticWeeklyChunkStore with pinned in-memory heads; bar/revision and full EMA/ATR semantic parity is TRUE but licensed_data_authorized, real_migration_approved and trading_authorized remain FALSE.
3. A mismatched old pinned head, attempting to compare the same backend against itself, and an intentionally revised historical candle all fail the equivalence/authorization path; changed revision returns BAR_OR_REVISION_OR_FIRST_KNOWN_MISMATCH. A result cannot be forged into real_migration_approved=True.
4. A candidate detached HMAC-SHA256 against fabricated metadata checkpoint and one 32-byte test key verifies; original verify_authenticated_journal_backup confirms one metadata chain record. This proves only shared-key possession in the same runner, not separate key custody or independent approval.
5. Wrong HMAC key or key_id is rejected. Keys are fixed synthetic test values, not real secrets, enrollments, external custody or market data licences.
6. Original verifier-only Ed25519 function validates a fixture-generated detached signature against a caller-supplied matching 32-byte public key and SHA256 fingerprint. No real vendor or independently authenticated signing root is enrolled.
7. Wrong Ed25519 public-key fingerprint and a syntactically valid but invalid 64-byte detached signature are rejected; signing date before checkpoint creation also fails closed.
8. Original reference_offline_verified_archive validates one stand-alone signed metadata-only SQLite archive from nofollow-pinned FD with identical chain tip/SHA, no table quote payload, with market_data_certified/historical_backtest_qualified/production_authorized/actionable all FALSE.
9. Mutating one archive byte (even after repinning file mode) rejects against checkpoint digest. The archive requires a stand-alone rollback-journal-mode SQLite, cannot be treated as an authenticated live SQLite/WAL view.
10. Original static SSI host D1 fixture invokes exactly one SSI reference endpoint then rejects second use; no live_mcp_deployed/data_rights_verified/production_authorized. No connected plugin or source credential.
11. Injected SSI DOWNSTREAM_UNAVAILABLE invokes the documented DNSE D1 reference endpoint as second call and remains not backtest qualified; nested credentials in static JSON are rejected; SSI permission denial does not silently authorize DNSE fallback.
12. Actual original RVOL_TOD20 with fabricated 20 distinct earlier sessions at target's same local time-slot calculates Decimal(1), used_bar_count=21 including target, COMPUTED_UNCALIBRATED and not data_certified/parameter_approved/actionable. Fixture sessions include synthetic dates and must NOT be interpreted as verified HOSE/HNX/UPCOM sessions or coverage.
13. Doubling target cumulative volume produces Decimal(2); only 19 prior sessions, mixed continuous/auction cumulative definitions, or mismatched elapsed trading minutes return BLOCKED. Missing volume cannot be interpreted as no signal or production readiness.

These are real calls to six inherited original production-domain functions plus a package import check, using existing test fixture constructors for synthetic inputs. No original inherited domain implementation was modified/mocked. Ed25519 signing helper originates only from an existing synthetic *test* fixture; the original signature module remains verifier-only. A successful in-run key check is not independent trusted ownership or nonresettable monotonic floor.

## 3. Additive-only code and hosted workflow

- scripts/m2_a02_final_seven_original_v1_runtime_lab.py — final 7 original file path matrix, 13 linked invariants, exact 63 scoped count, owner/production/trading flags hard FALSE, all fabricated metadata.
- tests/test_m2_a02_final_seven_original_v1_runtime_lab.py — **40 focused direct-source unittest cases** including positive/negative cache pinned head/revision, HMAC bad key, Ed25519 bad fingerprint/signature, offline archive byte mutation/sidecar presence, static provider host session/forbidden credential, exact same-local-slot 20-prior RVOL_TOD and missing denominator safety.
- .github/workflows/m2-a02-final-seven-original-v1-runtime.yml — same-repo Draft PR8 only, GitHub-hosted Python3.12 with optional [custody] verification crypto; permissions contents:read. Runs real remote upstream/main/PR Git tree equality before 40 actual V1 tests and 13 cross-boundary receipt asserts; uploads 14-day synthetic nonauthoritative no-go metadata only.
- docs/MST_A02_FINAL_SEVEN_ORIGINAL_V1_QA_20261110.md — this QA report, mirrored to MST Google Drive QA folder.

There was one intermediate CI failure in a *new test receipt-key spelling*: the test expected previous_distinct_scoped_v1 but the generated schema correctly emits prior_distinct_scoped_v1. The test-only field read was corrected; original V1/V2 source and receipt schema unchanged. Reran 40 tests and all foundation checks, success. Do not attribute intermediate failed SHA as green.

## 4. Exact GitHub Actions verification

Code/workflow HEAD: f5630e7b95e21d15b07a2402ad4c519fb053af56.
Dedicated final seven CI https://github.com/ngluonghoa/MST/actions/runs/42783412595: **SUCCESS 40/40 tests**, 13 linked safety invariants PASS, actual remote Swing upstream/MST main/PR source-tree byte lock PASS; exact 63 scoped paths, 0 fully certified/owner signed.
Foundation https://github.com/ngluonghoa/MST/actions/runs/42783412343: **SUCCESS 3/3 jobs**, Python3.11 **2825/2825**, Python3.12 **2825/2825**, original-source engineering 63/63 and H2/H3/lint/wheel PASS.
**31/31 GitHub Actions workflows SUCCESS on exact code/workflow HEAD.** After committing this Markdown QA, independently verify 31/31 on the report-containing HEAD before stating green on that final commit.

## 5. Governance gate and exact next phase

A02 **scoped original-file breadth review 63/63 complete**, not owner closure. **Owner A02 formal module dispositions: 0/63**. A03 full V2 ABI and behavior 1:1 owner acceptance OPEN. G01–G08 independent real provider signer, external monotonic floor, two authenticated writers/server-side CAS, legal market-source licences, physical Google Drive cache and ACL, revocation freshness, independent provenance and release proof OPEN. OA01–OA06 owner security choices unresolved. Production, live signal generation, trading/broker/M3/M4/M5/M8 release ALL BLOCKED.

Next work should NOT keep mechanically counting V1 modules. Instead create a **formal per-module A02 disposition / evidence sufficiency matrix** separating each of the 63 original V1 paths: static AST API signatures, scoped synthetic executed cases, still-unverified real provider behavior, owner dispositions, and A03 behavioral+ABI parity traceability, with explicit G01–G08 dependencies and required original→V2 ABI boundary test packets. No owner waiver, trusted root, real physical Drive market cache, production trading or protected main merge is authorized by these green CI receipts.
