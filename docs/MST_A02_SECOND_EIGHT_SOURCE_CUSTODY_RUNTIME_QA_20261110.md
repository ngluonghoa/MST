# MST A02 — Second Eight Inherited V1 Runtime Modules: Source Rights, Signed Custody, Journal and Cache

QA ID: MST-A02-V1-SOURCE-CUSTODY-CACHE-8-EXECUTED-001
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: PASS 42/42 new executed-original-V1 tests and 25/25 code-HEAD workflows. Actual provider/root/Drive production authority NO-GO.
PR: https://github.com/ngluonghoa/MST/pull/8 (Draft/unmerged).

## 1. Eight different original modules executed

The preceding A02 tranche exercised eight inherited V1 market/engine/replay/cache modules. This separate tranche runs eight OTHER original V1 modules: provider_rights_review, source_capability_evidence, provider_signed_event_chain, provider_head_custody, reference_journal, reference_journal_recovery, cache_snapshot_bundle, partition_chunk_cache.

Together the two tranches executed scoped runtime scenarios on 16/63 distinct original V1 modules. This is not 16 owner signoffs, complete module behavior coverage, or V1/V2 ABI parity. Another 47 original modules still lack this cross-module executed QA. Existing H3/AST inventory covers static API across all 63 only.

Source pin upstream Swing Trading 1.8 cd90c1babae8912db31490ad614fc2ad2f868042 and protected MST main 4048f91beaaa3410116d97e35896c8b688384e19 share original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e (216 entries, 208 blobs, 63 original V1 Python modules). Exactly eight earlier opt-in V2 source modules unchanged. GitHub Actions separately invokes real GitHub upstream/main/PR source-byte parity.

## 2. Eight linked actual-runtime safety scenarios

1. Eight self-declared source scope claims: review_unverified_source_claims sees all eight RightsScope values but does not independently verify licence. require_authorized_source always raises PermissionError. The set of missing claim types can be empty while legal rights and account binding are still UNKNOWN.
2. One synthetic SSI intraday row: summarize_source_capability only classifies metadata count and endpoint. No real M1/M5/M15 coverage, first-known truth, price adjustment, data retention or backtest entitlement is inferred.
3. Two distinct EPHEMERAL Ed25519 signing keys created within ONE GitHub Actions runner: original SignedRightsEvent/ClaimedExternalLedgerPin and SignedCustodyHead/ClaimedMonotonicFloor verify conditional crypto and linked event tail. Keys have one effective synthetic controller; valid signature is NOT SSI/DNSE authorization, independent custodian enrollment or nonresettable remote floor. Both explicit permission boundaries deny.
4. Signed provider revocation event linked to grant: RightsChainState SIGNED_HOLD_UNAUTHORIZED, no automatic regrant even when chain signature is valid.
5. Stale signed old head vs stronger self-supplied sequence floor: original custody audit rejects local relative rollback, which does NOT prove an independently stored cross-run monotonic floor.
6. Fresh empty ReferenceJournal + metadata-only JournalCheckpoint backup and restore into new SQLite file: genesis chain (0, ZERO) unchanged; no licensed quote cache, private rights custody or externally trusted pin.
7. WAL-aware empty synthetic SQLite snapshot create/verify/restore; source/cache original APIs run, but no real Drive upload, no signed external floor and require_approved_cache_transport raises PermissionError.
8. SyntheticDrivePartitionIndex one-partition in-memory content-addressed chunk, first publish, pinned load, repeated clean REUSED, stale expected head rejected; strictly not remote server CAS or actual physical Google Drive cache. require_real_market_cache_transport denies.

No raw market vendor API, accounts, licensed data or broker used. Ed25519 fixture keys were generated during a hosted run and never persisted in Git, Docs or upload artifacts.

## 3. Additive files and test boundaries

- scripts/m2_a02_source_custody_cache_eight_runtime_lab.py: executes real eight original module APIs and 8 linked source/custody/cache scenarios with a deterministic NO-GO-only aggregate receipt.
- tests/test_m2_a02_source_custody_cache_eight_runtime_lab.py: 42 tests for self-claimed/expired/private URL rights metadata, bad SSI shapes, crypto/signed-chain corruption, mismatched head/tail, revocation, counterfeit permission attempt, metadata journal backup, snapshot wrong pin, partition identity/open-bar/stale-head and no-production flags.
- .github/workflows/m2-a02-source-custody-cache-eight-runtime.yml: GitHub-hosted PR8 only, permissions contents:read; existing custody dependency, actual upstream/main/PR Git tree REST source lock, 42 tests, 8-scenario matrix, 14-day review-only artifact, no real Google Drive API access.
- docs/MST_A02_SECOND_EIGHT_SOURCE_CUSTODY_RUNTIME_QA_20261110.md: this QA report, to be mirrored into MST Google Drive QA.

Original src/swing_trading files and V2 sidecars were NOT changed. No GitHub ACL, refs, rulesets, owner credentials, signer/key enrollment, market cache writes, releases, PR merge, trading.

## 4. Exact code/workflow GitHub Actions evidence

Code/workflow HEAD a749f73c826ce5e513f674a0fdf93adf73ef7523.
Dedicated new runtime https://github.com/ngluonghoa/MST/actions/runs/42765872969: SUCCESS 42/42, 8/8 linked actual-original V1 scenarios, remote source-tree 1:1 PASS, status EIGHT_SOURCE_CUSTODY_CACHE_REAL_V1_RUNTIME_GUARDS_PASS_PRODUCTION_NO_GO.
Foundation https://github.com/ngluonghoa/MST/actions/runs/42765872676: SUCCESS 3/3 jobs, Python3.11 2585/2585, Python3.12 2585/2585, original engineering source-boundary63/63, H2/H3/lint/wheel.
All 25/25 GitHub Actions SUCCESS on the exact CODE HEAD. Report-containing future HEAD requires its OWN final commit readback.
Deterministic no-authority receipt SHA256 ed3bcb8fb7bed0a696c9fed9824bc16eb5ed90bf0a128c43eea499fe0d4c89d1 is reproducibility only, never a source signature.

## 5. Owner gates and future safe work

H3 static API reviewed 63/63; two executed eight-module A02 tranches now cover 16 distinct V1 modules with limited meaningful synthetic cases, 47 remain for such expanded executed coverage. Formal owner module decisions 0/63; A03 V2 ABI/full behavior acceptance OPEN including known permissive V1 ReplayClock direct field rewind and Evidence.verified non-boolean truthy field. G01 independent root/signer, G02 externally nonresettable floor, G03 real independent writers server CAS, G04 licensed market rights, G05 physical Drive bytes and ACL, G06 revocation, G07 provenance, G08 release all OPEN. OA01–OA06 and M3/M4/M5/M8 production and trading remain BLOCKED.

Next safe A02 scope: expand real V1 synthetic domain-function cases to remaining 47 original modules in selected review batches. Human owner must individually disposition all 63 later; never promote CI green or self-attested signing into market rights, permission to publish/trade, or protected branch changes.

Project Option A GitHub+Google Drive ONLY, no Mac/MOCHI/local/third Cloud, vendor quotes, real Drive market cache, private owner material, production/trading or main merge.
