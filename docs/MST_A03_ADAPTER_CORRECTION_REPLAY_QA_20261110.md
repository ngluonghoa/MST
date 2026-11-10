# MST A03 — Explicit adapter review candidates and causal correction/as-of replay QA

QA ID: MST-A03-ADAPTER-CORRECTION-REPLAY-20261110
Date: 10 November 2026 (Asia/Ho_Chi_Minh)
Status: **PENDING exact-HEAD hosted CI. No owner or production approval.**
GitHub: https://github.com/ngluonghoa/MST/pull/8 (Draft PR #8).

## Original source and guardrail

The source lock is Swing Trading 1.8 upstream commit cd90c1babae8912db31490ad614fc2ad2f868042. MST protected main remains 4048f91beaaa3410116d97e35896c8b688384e19; original package Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. Exactly 63 V1 inherited and eight pre-existing opt-in V2 Python source paths MUST remain byte-for-byte untouched. All new engineering is additive to the unmerged PR branch.

Previous A03 evidence confirmed four V1/V2 compatibility observations: direct legacy clock rewind vs strict clock; legacy truthy-integer Evidence.verified vs exact bool; one-pass BacktestHarness generator exhaustion vs V2 materialization; V1 subclass acceptance vs V2 exact event-type rejection. Earlier 128 synthetic decisions verified only UNVERIFIED with empty evidence; no trading signals.

## Six unsigned owner choices

| Review ID | Proposed approach (NOT approved) | Alternative / unresolved risk |
|---|---|---|
| A03-OWNER-ITERATOR-01 | Explicit, bounded snapshot-to-tuple fixture adapter at selected consumer port | Reject generators instead; alters V1 visibility, requires max-size policy |
| A03-OWNER-SUBCLASS-02 | Explicit exact-base-event policy for strict V2, deny subclass before both consumers | Separate versioned subclass conversion with source/payload semantics and human approval; no silent type stripping |
| A03-OWNER-REVISIONS-03 | Preserve immutable raw revision events and first-known timestamps for historical as-of replay | Authenticated provider supersession/tombstone/correction policy NOT implemented |
| A03-OWNER-ROLLBACK-04 | Fresh historical as-of replay without repainting earlier snapshots | Actual signed N/N-1 release rollback, durable anti-rollback not implemented |
| A03-OWNER-CLOCK-05 | Retain original legacy clock direct-field semantics pending opt-in | Strict V2 monotonic-clock transition can break old callers |
| A03-OWNER-EVIDENCE-06 | Deny migration of truthy nonboolean evidence to verified V2 | Requires independently verified source/typed evidence and approval |

All six are review proposals, not permission to deploy source adapters. Owner approvals A02=0/63, A03=0/8. All six choices UNSIGNED.

## Actual executed-code fixture scope

New scripts/m2_a03_adapter_revision_replay_lab.py defines **38 synthetic checks** on real untouched V1 BacktestHarness/CausalMarketEvent and strict V2 consumers. Test adapter candidates are contained ONLY in scripts/, not application src/swing_trading. tests/test_m2_a03_adapter_revision_replay_lab.py adds **36 independent unittest methods**. A dedicated read-only GitHub Actions workflow first verifies original source bytes against live upstream/main/PR Git objects and then runs tests, producing 14-day JSON metadata only.

- Raw one-pass generator divergence remains observable. Only an explicitly chosen bounded tuple fixture bridge changes V1 observed visibility to tuple behavior; rejects unbounded data and unsupported types, preserves source event payload/object, and grants no vendor rights.
- Subclass behavior remains observable. Strict candidate port rejects subclasses before either consumer; no automatic normalization, promotion or coercion.
- Four synthetic as-of times at 0/+5/+10/+15 minutes include three revisions of the SAME BAR-1 event: [r1], [r1], [r1,r2], [r1,r2,r3]. Late revisions are not visible at earlier knowledge times. Historical T0 replay remains [r1] even after r3 exists in the fixture dataset.
- **CRITICAL:** V1 and V2 visible_events() produce raw revisions, NOT an authenticated winner or canonical latest revision. A collection containing r1+r2+r3 is NOT source-certified supersession; tombstones, official calendar, conflicts and correction resolution stay OPEN.
- All 16 B/S zones under both SHORT/SWING strategies stay UNVERIFIED; no actionable output.

## Additive artifacts

- scripts/m2_a03_adapter_revision_replay_lab.py: proposed fixture-only bounded adapter and exact event guard, four as-of traces, six unsigned owner decision rows, deterministic SHA256 report.
- tests/test_m2_a03_adapter_revision_replay_lab.py: 36 unittest methods with injected negative cases.
- .github/workflows/m2-a03-adapter-correction-replay.yml: GitHub-hosted same-repo PR #8, read-only source lock + tests, 14-day nonauthorizing artifacts.
- docs/MST_A03_ADAPTER_CORRECTION_REPLAY_QA_20261110.md: this report; permanent Google Drive mirror.

Workflow: https://github.com/ngluonghoa/MST/actions/workflows/m2-a03-adapter-correction-replay.yml

## Exact-head verification / hard blocks

Do not claim green until actual report-containing SHA has independent LIVE GitHub tree source lock, 36 tests, Foundation Python3.11 and 3.12, engineering source/lint/wheel, and all workflows at exact commit verified. Green synthetic QA is not full ABI parity nor independently authenticated source truth.

External G01–G08 and OA01–OA06 remain OPEN; SSI/DNSE/VCBS rights, actual source corrections, official exchange calendar, physical licensed Google Drive market cache, independent signing root/revocation/floor and two-writer server CAS UNPROVEN. Protected main unchanged, PR#8 remains DRAFT/UNMERGED. **M3/M4/M5/M8 production and trading NO-GO.** GitHub + Google Drive only, no Mac/MOCHI/local/third Cloud.
