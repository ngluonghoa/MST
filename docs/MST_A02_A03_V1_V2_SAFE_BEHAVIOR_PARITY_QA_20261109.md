# MST A02/A03 — V1 ↔ opt-in V2 safe behavior differential, Cloud-only QA

**QA ID:** MST-A02-A03-BEHAVIOR-DIFF-001  
**Date:** 2026-11-09 (Asia/Ho_Chi_Minh)  
**Verdict:** **PASS for the explicit synthetic / UNVERIFIED causal-event and decision subset. Full 1:1 behavior and ABI acceptance NOT complete.**  
**Scope:** GitHub + Google Drive only. Runs entirely on GitHub-hosted CI without third-party Cloud compute, Mac, MOCHI or local project runtime.

## 1. Source and contract boundaries

- Original Swing Trading 1.8 pinned commit: `cd90c1babae8912db31490ad614fc2ad2f868042`; protected MST `main@4048f91beaaa3410116d97e35896c8b688384e19` holds the exact original Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e` (216 tree entries, 208 blobs). The **63 inherited Python modules remain unchanged**, as independently verified by the real remote [full-tree audit](https://github.com/ngluonghoa/MST/actions/runs/42632181256). 8 known additive opt-in V2 modules stay separate; this change writes only scripts/tests/workflow/QA files.
- A02 per-module *manual* 63 disposition (#4) remains OPEN. Actual V2 ABI and owner contract acceptance (#6) remains OPEN. Static byte-preservation is stronger evidence than file-count checks but does not certify runtime behavior.
- Four confirmed V1 permissive runtime contracts (issue #6): direct `ReplayClock.as_of_utc` assignment can rewind, untyped strategy/status values in `SignalDecision`, and untyped `Evidence.verified` are accepted by legacy code. V2 `StrictReplayClockV2`, `StrictSignalDecisionV2` and `StrictEvidenceV2` intentionally fail closed on these. They **are not drop-in ABI replacements**; direct V1 construction and V1 `1.x` descriptors remain valid, V2 opt-in `2.x` descriptors are separate.

## 2. Executed side-by-side behavior, not just AST/introspection

New `scripts/m2_a03_behavior_equivalence_lab.py` instantiates the **real inherited**:
- `ReplayClock` and `BacktestHarness.from_contracts` using actual `PortDescriptor(..., "1.0.0", "SYNTHETIC_TEST_ONLY")`.
- `evaluate_unimplemented_zones`, all 16 original `B1..B8` and `S1..S8`, both `Strategy.SHORT` and `Strategy.SWING`, returning `SignalDecision(..., UNVERIFIED)`.
- `CausalMarketEvent` with event timestamps and distinct `first_known_time_utc` and revisions.

Against actual additive V2:
- `StrictReplayClockV2`, `StrictReplayHarnessV2.from_contracts` with exact `V2_MARKET_PORT` and `V2_RULES_PORT` at `2.0.0`.
- `StrictSignalDecisionV2` safe UNVERIFIED fixture output, explicit `legacy_to_v2_unverified`, `v2_to_legacy_unverified`, `encode_unverified_v2_json` and `decode_untrusted_v2_json` typed roundtrip.
- No real provider, source callback, market API, actual cache, broker or network code is used by the fixture. GitHub Actions supplies the hosted Python runtime and checks the report.

Deterministic as-of snapshots `2026-11-09T00:00Z`, `00:05Z`, `00:10Z`, `00:15Z`. Six synthetic event revisions, deliberately returned out of input order, exercise late knowledge, later revisions, future events and late corrections. Both V1/V2 exposed **exactly the same sorted (event_id,revision_id) sequence** at each snapshot: visible counts **1 → 2 → 4 → 6**. A revision marked first-known later is not visible at earlier timestamps.

For every snapshot and each strategy, all **16 original zone slots** are evaluated using the legacy engine and the V2 opt-in unverified port. Every comparison requires matching identity, strategy, status, *empty evidence*, explicit migration/rollback adapters, and deterministic V2 safe wire roundtrip. The total is **4 × 2 × 16 = 128 decision comparisons**. Every decision must remain `UNVERIFIED`. The 128-trace/6-revision **synthetic fingerprint** is `ed679df33ba73c8a49bac2c85d8528453815180a43cd31d4f9b516372ea78d97`; this is a reproducibility digest, **not** independent signer or source proof.

## 3. New tests and guarded regressions

New `tests/test_m2_a03_behavior_equivalence_lab.py`: **23 new tests** on top of the existing suite, including:
- 16-zone order, two unchanged strategy enums, 128 paired decisions, 4 snapshots, six revisions, 1/2/4/6 causal visibility counts, known-time sort order and repeatable trace digest.
- Legacy class/constructor ABI unchanged; explicit V1/V2 `1.0.0` vs `2.0.0` descriptor isolation; V1 permissive type/rewind known gaps are **not silently patched**; strict V2 guards remain in place.
- Negative fixtures: a V2 rule falsely returns `DETECTED` with synthetic evidence, returns a V1 decision, changes zone identity or strategy, or uses a different known event set. These are denied instead of silently counted as V1/V2 parity.
- Untrusted/extra future source events remain outside the as-of window; untyped causal events are rejected.
- Explicit wire input cannot promote `DETECTED`/`NOT_DETECTED` from untrusted JSON.

A new read-only `.github/workflows/m2-a03-v1-v2-behavior-differential.yml` runs on same-repo **Draft PR #8** with `permissions: contents: read`, installs the pinned package, executes actual V1/V2 Python fixtures, then writes one 14-day Actions artifact. A workflow PASS is **not** an owner signature or production admission.

## 4. Exact hosted evidence (pre-report code HEAD)

**Code/workflow HEAD:** `6f378506099f18902e43ddda546801af717d6706`.

- [Dedicated A02/A03 behavior differential #42633944710](https://github.com/ngluonghoa/MST/actions/runs/42633944710) **SUCCESS**. Output: `V1_V2_SAFE_UNVERIFIED_FIXTURE_SUBSET_MATCHES`; four snapshot counts 1/2/4/6; `decision_comparisons=128`; `causal_event_revisions=6`; all market/data/authorization flags false. Temporary review-only [artifact 13682043082](https://github.com/ngluonghoa/MST/actions/runs/42633944710/artifacts/13682043082), 14-day retention.
- [Foundation CI #42633944333](https://github.com/ngluonghoa/MST/actions/runs/42633944333) **SUCCESS 3/3**: Python 3.11 **2008/2008**, Python 3.12 **2008/2008**, engineering **63/63**, source-boundary H2/H3, lint, wheel PASS.
- [Remote 1:1 source-tree check #42633944313](https://github.com/ngluonghoa/MST/actions/runs/42633944313) **SUCCESS** on the same code HEAD; other read-only and synthetic M4 workflows also green. **11/11 workflows SUCCESS** on this code HEAD.
- This QA Markdown change creates a **new PR HEAD**, so exact final HEAD workflows must be rechecked before declaring the documentation-containing checkpoint green.

## 5. Precisely what is NOT accepted

The old `engine.evaluate_unimplemented_zones` is **explicitly an unimplemented-zone placeholder**: it cannot truthfully generate DETECTED or NOT_DETECTED. This suite **does not** exercise actual B/S detector formulas, entry/exit signals, prices, finance decisions, real OHLCV, SSI/DNSE/VCBS licenses, H4/D1 source availability, trading calendar, source corrections in a provider, persistence or multiwriter Google Drive caching. Although 128 comparisons pass, **full end-to-end Swing Trading parity has not been certified**.

The V1 permissive vs V2 strict runtime semantics and major-version descriptor incompatibility remain **intentional opt-in differences**. Treating V2 as a drop-in replacement without ABI review is prohibited. No legacy V1 byte or method was modified to make these tests pass. In particular, a caller-provided `StrictEvidenceV2(verified=True)` is not an independently authenticated source attestation; untrusted wire decoding still cannot promote a classified decision.

Owner decisions still required: [#4 A02 63 module reviews](https://github.com/ngluonghoa/MST/issues/4), [#6 A03 V2 ABI/semantics](https://github.com/ngluonghoa/MST/issues/6), [#9 M3 legal licensed data](https://github.com/ngluonghoa/MST/issues/9), [#10 M4 physical Drive bytes](https://github.com/ngluonghoa/MST/issues/10), and [#16 G01..G08 independent custody](https://github.com/ngluonghoa/MST/issues/16). Protected witness/ref, signer keys, remote rollback floor, two independent writers and owner production release remain UNVERIFIED. GitHub+Drive Option A persists with no extra cloud, Mac, MOCHI, local, main policy changes or PR merge.

**Next safe work:** expand the A02/A03 golden behavioral fixture coverage to the most consequential genuine legacy modules (e.g. `market_data`, `causal`, cache policies, VN T+2 backtest) one interface at a time with explicit owner review and source-derived expected outputs, then prepare V2 ABI compatibility decision; do **not** label generic UNVERIFIED placeholders as completed trading signals.
