# MST A02 — Seventh Distinct Eight Original V1 Engineering, Custody, POSIX Reference Storage and VN Rollback QA

QA ID: MST-A02-V1-SEVENTH-EIGHT-ENGINEERING-CUSTODY-ROLLBACK-20261110
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: 40/40 new actual-original V1 tests PASS; 8/8 linked real inherited-domain safety checks PASS; 30/30 GitHub Actions workflows SUCCESS on exact code/workflow HEAD. External vendor/account/host trust, production cache, release and trading remain NO-GO.
Draft PR: https://github.com/ngluonghoa/MST/pull/8 (Draft, unmerged).

## 1. Immutable upstream source and distinct modules

Source-of-truth Swing Trading 1.8 commit cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19; source-tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. GitHub-hosted CI separately retrieves LIVE upstream/main/PR Git tree via GitHub REST and verifies all 63 original inherited V1 Python files plus eight previously existing opt-in V2 sidecars unchanged.

Seventh executed batch, none present in previous 48 distinct original module tranches:
- engineering_contracts
- engineering_release
- fixture_scan
- provider_custody_host_plan
- provider_review_packet
- reference_storage_preflight
- reference_pinned_fd
- vn_release_rollback

Seven executed original-V1 batches now include limited meaningful synthetic fixture behavior paths for 56 DISTINCT of 63 original V1 modules, leaving 7 outside this grouped runtime review. Existing static AST/H3 63/63 inventory is separate; neither static nor scoped executed fixtures constitute full functional/ABI parity, third-party source licensing or owner approval. A02 formal owner dispositions remain 0/63.

## 2. Eight joined actual-original-code safety paths

1. **Engineering module contract:** versioned PortDescriptor structural compatibility accepts an additive minor-version same-scope implementation but rejects cross-provider scope and missing operations, including when bound to an in-process consumer. Structural match has hard-coded live_data_authorized/deploy_authorized/trading_authorized false. Original engineering module is exercised, no real adapter deployed.
2. **Release and rollback identity:** original EngineeringSnapshot canonical SHA identities and compare_engineering_snapshots detect changes to interface-lock SHA and request contract requalification. Deterministic build identity does NOT approve deployment, operational rollback, independently approved last-known-good or licensed market data.
3. **Synthetic five-minute fixture scan:** on an ephemeral GitHub runner an original SyntheticIncrementalStore executes a fabricated full session at minute 45 (9 rows), avoids redundant refresh at minute 46, performs two-row window request at minute 50, and blocks an unknown source capability without calling the fake fetcher. Two fake fetch calls, zero actual SSI/DNSE/VCBS/market data calls or market eligibility.
4. **Source signer/custodian host claims:** all six purported external reviewer roles plus nine claimed host controls supplied by one test process satisfy inventory completeness but verify no independent vendor signer origin, no fresh revocation stream, no host-volume certification, no right to read/cache, and no trading. require_external_trust raises PermissionError.
5. **Independent-review packet/hold:** three caller-reported review roles and purported full licence scope yield READY_FOR_EXTERNAL_REVIEW_ONLY, not independently authenticated vendor permission. A synthetic revocation hold changes state to BLOCKED_HOLD and cannot reinstate access. require_independently_authorized_packet raises PermissionError.
6. **POSIX storage preflight:** a newly created fixture-only SQLite file with private directory mode 0700, file mode 0600 and matching Linux UID passes original read-only path/owner checks, but host_volume_approved, provider_retention_approved and production_authorized stay false. Additional tests reject world-readable mode, symlink file, hardlink and path outside declared private root.
7. **Pinned no-follow file descriptors:** actual original pin_reference_sqlite_files opens the temporary SQLite header via Linux O_NOFOLLOW/dirfd, pins inodes and reports unchanged path; a new "-wal" sidecar appearing *after* pinning invalidates the snapshot. This is NOT a safe sqlite3.connect(path) attestation, a claim about external volume/ACL, or a physical Google Drive cache audit. All files created only on ephemeral GitHub-hosted Linux, never on user's Mac/MOCHI/local.
8. **Vietnam cash-equity release rollback:** preview_vn_rollback detects changed strategy parameters and invalidates derived cache, yet refuses to promote a caller-proposed LKG without independently approved restore. A request to sell 200 shares with only 100 settled and 500 pending T+2 is blocked; pending T+2 shares are never added to settled sellable stock. Bad tick size, missing market/account context and out-of-scope source change are separately denied in focused tests. No broker operation, short selling, release pointer move, or runtime rollback executed.

All eight original modules were called directly with old synthetic input constructors or fabricated ephemeral filesystem data. The actual original domain functions were not mocked. No authenticated vendor source, licensed quote history, real Drive market cache, approved root signer, independent revocation ledger, distributed CAS, or production orders.

## 3. Changes added only to Draft PR #8

- scripts/m2_a02_seventh_eight_engineering_custody_rollback_runtime_lab.py: actual original eight-module cross-boundary execution and eight linked no-authorization assertions, deterministic review-only receipt; temporary POSIX SQLite host fixture on GitHub Actions.
- tests/test_m2_a02_seventh_eight_engineering_custody_rollback_runtime_lab.py: 40 positive/negative domain cases covering port semver/scope, build SHA changes, incremental fixture scan, claimed custody and revocation, POSIX modes/symlink/hardlink/nofollow/new WAL, and VN LKG/settlement/risk.
- .github/workflows/m2-a02-seventh-eight-engineering-custody-rollback.yml: same-repository PR8 GitHub-hosted runner only, contents:read, independently validates actual remote upstream/main/PR Git source-byte tree, then runs 40 tests and joined synthetic no-go receipt, retains 14-day nonauthorizing JSON.
- docs/MST_A02_SEVENTH_EIGHT_ENGINEERING_CUSTODY_ROLLBACK_QA_20261110.md: this source-locked QA packet mirrored to MST Google Drive QA.

No original V1 or existing V2 Python source was edited. No protected main merge, GitHub branch ruleset/ref/ACL, independent signer/witness, production Drive market data, licence, broker, order or release was changed.

## 4. Exact verified GitHub Actions evidence

Code/workflow HEAD: 78b1fea9fd80990ffc9b974b2729573481a6f3a4.
Dedicated seventh eight original V1 test workflow: https://github.com/ngluonghoa/MST/actions/runs/42780651450: SUCCESS; 40/40 original domain tests, 8/8 linked review-only guards; real remote upstream/main/PR source-tree parity PASS.
Foundation: https://github.com/ngluonghoa/MST/actions/runs/42780651683: SUCCESS 3/3; Python3.11 2785/2785, Python3.12 2785/2785; engineering original source63/63, H2/H3/lint/wheel PASS.
Exact code/workflow HEAD: 30/30 GitHub Actions SUCCESS. Once this Markdown QA report is committed to the PR branch, VERIFY the new report-containing commit separately before citing all 30/30 for the final HEAD.

## 5. Safety interpretation, owner gates and next batch

A02 owner signoffs 0/63; 56 original V1 modules have *scoped* runtime fixture checks in seven batches, seven remaining. A03 complete V1→V2 behavior/ABI owner acceptance OPEN. OA01–OA06, G01–G08 actual external vendor rights, signer independence, monotonic nonresettable floor, true independent two-writer CAS, authentic revocation, Google Drive physical market cache/ACL and release authority OPEN. M3/M4/M5/M8 production and trading BLOCKED.

Remaining original V1 module names outside all seven batches: __init__, cache_swap_preview, reference_checkpoint_mac, reference_checkpoint_signature, reference_host_dryrun, reference_offline_verified_archive, rvol_tod_contract. An eighth and final seven-module review may exercise these original module paths with synthetic cases; testing __init__ only constitutes package import/API metadata behavior, NOT domain behavior. Any skipped/uncoverable path must remain explicitly recorded and not silently assigned PASS.

All project work limited to GitHub and Google Drive cloud-only, no user local/Mac/MOCHI compute, no unapproved third Cloud or live market feeds.
