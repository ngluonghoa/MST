# MST A03 — Consumer-driven V1→V2 ABI, safe opt-in migration and rollback QA

QA ID: MST-A03-CONSUMER-ABI-ROLLBACK-20261110  
Date: 2026-11-10 Asia/Ho_Chi_Minh  
Scope: GitHub+Google Drive Option A, additive Draft PR #8 only.  
Status: **QA PENDING exact-final-commit CI; owner and production NO-GO even after green synthetic tests.**

## Source and previous evidence

- Original Swing Trading 1.8 pin: cd90c1babae8912db31490ad614fc2ad2f868042.
- MST protected main pin: 4048f91beaaa3410116d97e35896c8b688384e19; original full tree: d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e.
- Earlier A02 index: 63/63 original V1 files with limited selected fixture/import evidence; **0/63** owner-approved module dispositions and **0/63** full module behavior certifications.
- Earlier A03: eight V2 sidecars AST-traced and 128/128 **UNVERIFIED**-only deterministic comparisons, **0/8** full V2 ABI/behavior owner signoffs.
- This packet uses the actual inherited and V2 code unchanged. All source checks must be independently verified by remote Git tree comparison on GitHub Actions, not inferred from local assertions.
- Latest authoritative MST canonical handoff before this packet: §77. No automatic change to any canonical source-backed contract.

## Why targeted consumer QA matters

The static import graph maps syntactic edges, not actual behavioral substitutability. This audit checks use-site migration boundaries by executing original V1 and opt-in V2 constructors, explicit contracts, wire adapters, and deterministic source/cache fixtures. It deliberately tests where a naive drop-in migration would be incorrect.

| Consumer or boundary | Executed negative/positive evidence expected | Compatibility policy |
|---|---|---|
| replay.ReplayClock → StrictReplayClockV2 | Legacy direct public as_of_utc rewind remains permitted; strict direct rewind denied; advance_to denies rewind in both; future first-known cannot appear | **Intentional BREAK**, never overwrite V1; owner decides explicit opt-in |
| contracts.Evidence → StrictEvidenceV2 | Legacy integer verified=1 accepted; V2 exact bool rejects it | **Intentional BREAK**; prohibit truthy coercion and source-claim promotion |
| SignalDecision ↔ strict V2 | Roundtrip ONLY UNVERIFIED with empty evidence; DETECTED/NOT_DETECTED and self-attested evidence cannot upgrade/downgrade | Bounded synthetic adapter, not blanket V1/V2 interchangeability |
| V1 BacktestHarness ↔ StrictReplayHarnessV2 | PortDescriptor major 1 vs 2 fails both directions; direct constructor rejects wrong clock; explicit matching fixture harness succeeds for empty safe events | Major-version adapter/consumer review required |
| untrusted JSON wire | Explicit UNVERIFIED wire only; DETECTED/NOT_DETECTED and duplicate JSON members denied | No external provider evidence authorization |
| SSI/DNSE fixture adapter | Probe receipt never grants source, retention, or trading; a requested provider scope mismatch is denied | No implied source fallback |
| cache_fetch_planner / v2_cache_partition_plan | Unknown V1 capability blocks fetch; provider identity changes partition digest; foreign head denied; V2 plan never grants physical Drive operations; cross-version plan not a compatible cache object | No automatic cache migration, real source freshness or Google Drive data writes |
| causal replay differential | Previous 128/128 UNVERIFIED decisions at four artificial timestamps remain reproducible | Not DETECTED/NOT_DETECTED parity, strategy calibration, signals or real backtests |

## Additive artifacts

- scripts/m2_a03_consumer_abi_migration_lab.py: pure Python deterministic report with **26** uniquely named guard cases, SHA-256 case fingerprint, zero owner or release permission flags.
- tests/test_m2_a03_consumer_abi_migration_lab.py: **25** unittest methods, including direct fresh negative injections beyond report readback.
- .github/workflows/m2-a03-consumer-abi-migration.yml: restricted GitHub-hosted PR8-only read-only token, Python 3.12; **first** real GitHub REST upstream/main/PR byte-source lock, **then** 25 unittest cases and 26 case report; 14-day JSON artifacts. No credentials, actual source data, local computer, Drive market-cache bytes or privileged GitHub settings.
- This Markdown review receipt records scope and denial assumptions. Green CI will not authorize an owner decision or production use.

## Independent owner review / missing proof

- **A02**: 0/63 human owner dispositions. **A03**: 0/8 full ABI and behavioral acceptance. The new packet is targeted, not exhaustive.
- Owner must choose each intentional V1/V2 strictness break, inspect actual caller signatures and dynamically loaded consumers, review non-UNVERIFIED detector behavior, document explicit adapter migration/downgrade and N/N−1 rollback tests. No silent mutation of original V1 code, no V2 auto-activation, and no auto-normalization of legacy integer "verified" proof.
- Market calendar/session policy, publisher/report behavior, live SSI/DNSE/VCBS entitlement and price-revision legal rights, source provenance, physical Google Drive cache, independent signer enrollment, nonresettable floor, authenticated two-principal CAS, revocation freshness, and valid signed release remain unproven.
- Security gates **G01–G08**, Option A owner gates **OA01–OA06**, and M3/M4/M5/M8 production/trading remain **OPEN / NO-GO**.
- GitHub + Google Drive ONLY. No Mac, MOCHI, local environment, third Cloud, new service provisioning, licensed live quote calls, broker/trading, ruleset edits, merge or production release.

## Evidence and exact-head verification

GitHub workflow: https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-consumer-abi-migration.yml  
PR #8: https://github.com/ngluonghoa/MST/pull/8

At first document creation, latest exact-head workflow evidence was pending. Subsequent **code+report HEAD 9452bdecad32e10e631d638d948d04b33bd6f32e** was independently checked live and all **35/35 GitHub Actions runs SUCCESS**, including dedicated consumer ABI/rollback [run 42796973453](https://github.com/ngluonghoa/MST/actions/runs/42796973453) (GitHub original V1/V2 source lock, 25 unittest methods, 26-case JSON packet, 14-day upload all SUCCESS), Foundation [run 42796973314](https://github.com/ngluonghoa/MST/actions/runs/42796973314) (3/3 jobs PASS; Python 3.11 + 3.12 test suites, H2/H3 source/lint/wheel) and independent original-tree [run 42796973732](https://github.com/ngluonghoa/MST/actions/runs/42796973732) SUCCESS. These results prove only the bounded synthetic compatibility packet, NOT source rights, independent custody, complete ABI parity, production or trading.

The Markdown evidence-update commit after that snapshot must also receive its own exact-HEAD CI verification before final checkpoint closure. Require independent complete exact-HEAD CI readback, foundation Python 3.11 and 3.12 counts, source tree proof, and Google Drive canonical handoff/version sync before upgrading this document's QA claim. Any failure remains a failure until corrected and rerun; no blanket release promotion.
