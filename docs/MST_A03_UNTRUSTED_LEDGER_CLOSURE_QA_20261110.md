# MST A03 — Untrusted claimed revision-ledger closure, fake source/viewer independence, rollback falsification

QA ID: MST-A03-UNTRUSTED-LEDGER-CLOSURE-20261110
Date: 10 November 2026 (Asia/Ho_Chi_Minh)
Status: **PENDING exact-final-HEAD CI; OWNER and production NO-GO regardless of green synthetic tests**.
PR: https://github.com/ngluonghoa/MST/pull/8 (Draft only, never merge without separate owner governance).

## Baseline and gap

- Source-locked Swing Trading 1.8 upstream cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19 and original package tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e unchanged.
- 63 inherited V1 and eight already existing V2 source paths remain byte-identical; work is purely additive scripts, tests, read-only workflow and QA documents on Draft PR8.
- Earlier §81 Handoff, §82 Spec and §78 Gap: 40 tests/54 fixture scenarios showed a *hypothetical* revision winner/tombstone, not genuine source-signed completeness. No original V1/V2 code implements signed head, licensed provider revision sequence, authoritative tombstone or vendor correction history.

## This packet: 44 negative/positive source-*untrusted* cases + 44 unittest methods

scripts/m2_a03_revision_ledger_closure_lab.py creates a deterministic test-only pair of source/viewer metadata *declarations* for one partition/event/as-of. Each claim includes self-stated actor ID, custody domain, head sequence and ID, raw revision-ledger digest, as-of closure and claimed observation time. The local lab compares the TWO claims with each other and against the actual fixture rows. **It never verifies a real signature, independent principal, authenticated provider, source license, server CAS, durable high-watermark or real Google Drive cache.**

The fixture uses BAR1 revisions r1 (UPSERT), r2 (UPSERT correction), r3 (TOMBSTONE) at as-of T0, T+5, T+10, T+15, T+20. Structural observation head sequences are 1,1,2,3,3. The source/viewer strings and hashes match on the happy path, but even that result is labeled CLAIMS_STRUCTURALLY_CONSISTENT_BUT_UNTRUSTED. No source head can certify that no revision is absent merely by self-asserting closure; the latest candidate remains UNVERIFIED.

Negative controls reject mismatched source/viewer roles, equal self-declared actors/custody domains, cross-source or cross-basis claims, different event IDs, stale/as-of mismatched claimed closure and observation times, lower/higher head sequences, head ID mismatch, changed/invalid digests, future-known rows in a claimed historical snapshot, missing root/middle, duplicate revisions, bad row types, and any in-memory prior-head rollback or historical prefix rewrite.

### Two decisive counterexamples: what the lab deliberately FAILS to prove

1. **Fresh process with NO prior durable floor:** a self-declared source and viewer can agree on old r1 at T+20 after prior fixture head r3 existed. The local structural verifier returns a consistent-looking receipt because no prior independent state was retained. Thus in-memory monotonic checks do NOT protect cross-run rollback.
2. **Two colluding-looking self-claims with NO prior:** both can agree on a rehashed, tampered r1 payload while preserving a plausible r1→r2 chain. Structural digest equality does NOT prove independent custody, genuine vendor history, real source roots or market-data truth.

These counterexamples are explicitly tested and recorded with NO owner/production authority. Merely using two different string IDs, or generating SHA256, cannot close G01/G02/G03/G04/G05/G06/G07/G08.

## Four new owner decision gates — all unsigned (A03 total 14 unsigned)

| Gate | Missing evidence before any release |
|---|---|
| A03-OWNER-SOURCE-HEAD-CLOSURE-11 | Independently verifiable provider-issued closure, stable revision root, canonical snapshot scope, missing-revision completeness and official as-of semantics |
| A03-OWNER-INDEPENDENT-CUSTODY-12 | Evidence of truly independent, enrolled signer and viewer principals, controlled custody and authentication, not merely distinct declared identifiers |
| A03-OWNER-DURABLE-FLOOR-13 | Nonresettable cross-run high-watermark, rollback detection after restart/compromise and incident-recovery procedure |
| A03-OWNER-LICENSED-REPLAY-14 | Contractual SSI/DNSE/VCBS provider rights, correction/tombstone/retention policy, original vs adjusted bars, official exchange sessions and Google Drive cache permission |

Previous A03 owner decisions 01–10 remain UNSIGNED; new 11–14 UNSIGNED (14/14). A02 full module owner signoff 0/63, A03 full V2 ABI/behavior owner signoff 0/8.

## Additive-only code, cloud CI and evidence handling

- scripts/m2_a03_revision_ledger_closure_lab.py — pure fixture claims, 44 cases, 5 as-of declared-head snapshots, exact case SHA256 and two critical spoofability counterexamples.
- tests/test_m2_a03_revision_ledger_closure_lab.py — 44 unittest methods with independent replay of rollback and colluding-rehash counterexamples.
- .github/workflows/m2-a03-revision-ledger-closure.yml — GitHub-hosted Python3.12, same-repo PR8 + contents:read only, **LIVE** original upstream/main/current PR Git tree lock first, then tests; 14-day synthetic metadata-only artifact.
- docs/MST_A03_UNTRUSTED_LEDGER_CLOSURE_QA_20261110.md — this permanent QA/owner-review receipt, mirrored into native Google Drive MST 02_QA_RELEASE_EVIDENCE.

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-revision-ledger-closure.yml

No Mac/MOCHI/local processing, third Cloud, vendor live APIs, license assumption, physical licensed Google Drive market cache I/O, GitHub ruleset changes, merge, secrets, trading or broker actions.

## Unclosed gates and exact-commit evidence requirement

At creation, exact-final-HEAD green has not yet been asserted. Require the 44 tests, 44 synthetic negative cases, independent GitHub live source lock, Foundation Python3.11 and 3.12/H2/H3/lint/wheel and ALL workflows at the same current PR8 commit to complete successfully. Any updated QA Markdown commit must receive fresh exact-HEAD CI verification.

Even after green: G01–G08 and OA01–OA06 OPEN; real provider closure, source entitlement/retention, physical Drive market cache, signer/independent custody, durable floor and genuine two-principal server CAS all UNPROVEN. The original 16-zone detectors remain uncalibrated/UNVERIFIED; no full behavior parity, real backtest, production or trading approval. M3/M4/M5/M8 production and trading **NO-GO**.
