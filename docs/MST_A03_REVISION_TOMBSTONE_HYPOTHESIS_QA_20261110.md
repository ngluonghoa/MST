# MST A03 — Untrusted source revision winner/tombstone hypothesis; owner NO-GO

QA ID: MST-A03-REVISION-TOMBSTONE-HYPOTHESIS-20261110
Date: 10 November 2026 (Asia/Ho_Chi_Minh)
Evidence state: PENDING new exact-HEAD GitHub Actions readback. This is a falsification/negative-case lab, NOT market-data source qualification or trading readiness.

## Source lock, scope and why this matters

- Source original: Swing Trading 1.8 commit cd90c1babae8912db31490ad614fc2ad2f868042, inherited V1 module count 63. Protected MST main commit 4048f91beaaa3410116d97e35896c8b688384e19, inherited Python tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. Eight existing opt-in V2 module files remain byte-identical.
- Draft PR #8 https://github.com/ngluonghoa/MST/pull/8 only; no merge, no protected main changes, no code modifications to inherited V1 or preexisting V2 modules.
- Previous §80 Handoff/§81 Spec: actual V1/V2 visible_events() returns a *raw list* of causally visible revisions, not a canonical revision winner or tombstone interpretation. Historical fixture with r1/r2/r3 proved only first-known filtering. Its strict source custody, revision precedence, provenance, license and authority remain unknown.
- This new packet adds a **separate Python scripts-only candidate model** for falsifying unsafe revision/tombstone assumptions, deliberately not installed as a production resolver. Even when it returns a "candidate revision", that identifier is UNVERIFIED and cannot be translated into authoritative OHLCV, "NOT_DETECTED", "DETECTED" or trading.

## 54 synthetic tests of a deterministic untrusted hypothesis

A synthetic FixturePartition keys provider, endpoint, symbol, timeframe, price basis and session. FixtureRevision includes event ID, revision ID, claimed integer sequence, explicit kind (UPSERT or TOMBSTONE), event-time, first-known UTC, claimed predecessor and payload SHA256 (only for UPSERT). These fields are *caller-supplied, not externally signed or independently authenticated*. A read-only function computes conditional fixture candidate from complete visible prefix and fails closed on ambiguity.

Actual untouched V1 BacktestHarness and existing V2 StrictReplayHarness consume the same fabricated events through the separately proposed bounded tuple fixture adapter; they agree on **raw** visibility but do not choose the winner or suppress tombstones. A dedicated hypothesis function makes only a local, unsafe-for-production candidate decision.

| As-of fixture time | Raw events visible in V1/V2 | Hypothetical untrusted candidate (NOT vendor truth) |
|---|---|---|
| T+0 | r1 UPSERT | r1, UNVERIFIED |
| T+5 | r1 UPSERT | r1, UNVERIFIED |
| T+10 | r1 UPSERT, r2 UPSERT | r2, UNVERIFIED |
| T+15 | r1 UPSERT, r2 UPSERT, r3 TOMBSTONE | NO candidate; UNVERIFIED_TOMBSTONED |
| T+20 | r1 UPSERT, r2 UPSERT, r3 TOMBSTONE | NO candidate; UNVERIFIED_TOMBSTONED |

Negative tests cover: a missing root or skipped sequence, duplicate sequence/revision ID, wrong predecessor, equal or regressed first-known knowledge, mismatched event timestamp, unknown item types, cross-provider/endpoint/event/price-basis mixing, malformed timestamps, source claim payload digest, invalid tombstone payload, self-supersession, prohibited implicit resurrection after a tombstone, and use of future-known revisions to repaint an earlier as-of view. The source first-known cutoff is a fixture input; no assertion here independently proves the timestamps are truthful.

This lab does not implement source reconciliation, tombstone authority, signed sequence provenance, canonical latest-candle selection, vendor correction APIs, corporate action handling, real data retention, distributed Google Drive CAS or recovery/rollback.

## Four NEW unsigned owner decision gates (in addition to six previous A03 choices)

| ID | Required genuine external/owner proof |
|---|---|
| A03-OWNER-SOURCE-SEQUENCE-07 | Who can attest a stable vendor revision sequence, closure, missing revisions, snapshot root and source freshness? |
| A03-OWNER-TOMBSTONE-08 | What is the provider's actual deletion/tombstone semantics, resurrection policy and retention/license scope? |
| A03-OWNER-CORRECTION-CONFLICT-09 | How are ties, duplicate revision IDs, contradictory head sequences, tombstones and cross-session corrections resolved from independently verified vendor evidence? |
| A03-OWNER-RECONCILIATION-10 | How do official VN session calendar, source revision checks, retention and rights approval affect historical as-of replay and Google Drive caches? |

All four new owner decisions UNSIGNED. Cumulative explicit A03 owner-choice review packets: 10 UNSIGNED (six prior + four new). Human source-module acceptance A02 0/63; full ABI/behavior A03 V2 signoff 0/8.

## Additive-only PR artifacts and CI requirements

- scripts/m2_a03_revision_tombstone_hypothesis_lab.py: deterministic fixture-only candidate model, raw V1/V2 visibility comparison, 54 cases, five as-of receipts, four unsigned owner records, SHA256 report.
- tests/test_m2_a03_revision_tombstone_hypothesis_lab.py: 40 unittest methods, including direct independent negative/earlier-as-of checks.
- .github/workflows/m2-a03-revision-tombstone-hypothesis.yml: GitHub-hosted PR#8 same-repository read-only CI, LIVE upstream/main/PR byte parity BEFORE tests, synthetic-only JSON artifacts retained 14 days.
- docs/MST_A03_REVISION_TOMBSTONE_HYPOTHESIS_QA_20261110.md plus native Google Drive QA mirror in MST 02_QA_RELEASE_EVIDENCE.

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-revision-tombstone-hypothesis.yml

Exact final code+QA report HEAD must have all relevant GitHub workflows (including Foundation Python3.11 and Python3.12, source/lint/wheel, independent original source tree lock) SUCCESS before a QA-green claim. Synthetic CI is not an independent attestation.

## External blockers / release policy

G01–G08, OA01–OA06 remain OPEN: independent signer/root/floor/revocation and authenticated multi-principal server CAS, SSI/DNSE/VCBS licensing/retention, genuine vendor revision ledger and legal caching rights, official session calendar, physical licensed Google Drive cache. M3/M4/M5/M8 and trading remain NO-GO; no actionable signals, broker interactions, release, PR merge, privileged GitHub settings changes, user Mac/MOCHI/local or third Cloud permitted. ONLY GitHub + Google Drive.
