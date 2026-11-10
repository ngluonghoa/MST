# MST A03 — Eight Opt-in V2 Sidecars: V1 ABI/Dependency Trace and Differential QA

QA ID: MST-A03-EIGHT-V2-ABI-TRACE-20261110
Date: 2026-11-10 (Asia/Ho_Chi_Minh)
Verdict: 35/35 synthetic A03 checks PASS, 8/8 opt-in V2 static ABI/dependency paths mapped, 128/128 existing UNVERIFIED-only differential decisions confirmed, TWO deliberate V1/V2 incompatibilities retained, human A02/A03 and production/trading NO-GO.
Draft PR #8 https://github.com/ngluonghoa/MST/pull/8 — DRAFT/UNMERGED.

## 1. Original source identities and analyzed V2 modules

Original Swing Trading 1.8 upstream cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19; original source tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. GitHub-hosted CI separately fetches REAL live upstream/main/PR Git trees and enforces byte-for-byte original 63 V1 paths plus eight existing opt-in V2 sidecars unchanged, before running synthetic A03 tests.

| Unchanged existing opt-in V2 module | Scope of static V1 dependency and behavior | Current owner verdict |
|---|---|---|
| strict_contract_v2 | Original contracts/replay classes, typed opt-in clock/evidence/UNVERIFIED adapters | INTENTIONALLY NON-INTERCHANGEABLE: owner transition needed |
| v2_replay_port | Versioned causal-event and zone registry fixture consumer ports | UNVERIFIED subset checked; full ABI OPEN |
| v2_source_adapter | Fake provider identities and source probe metadata | No real vendor source or rights |
| v2_provider_readiness | Self-declared source onboarding review checklist | No independently verified entitlement |
| v2_cache_partition_plan | Synthetic Drive partition identity and refresh hints | No physical licensed cache, no source freshness |
| v2_cache_fencing_lab | In-memory manifest and fencing single fixture witness | No real two-writer server CAS or durable floor |
| v2_cloud_ref_witness_plan | Hypothetical Git-ref parent/head witness proposal | No actual production Git ref update or owner proof |
| v2_cloud_publish_verify_lab | Caller-supplied offline Git/Drive publish barrier observations | No authenticated cross-service atomic publish proof |

Exact source SHA256, public ABI syntax SHA256, direct and TRANSITIVE AST import graph of original V1 files, static dependent V2 paths, and relevant A02 owner-evidence rows are retained as 14-day machine-readable JSON and Markdown artifacts on the dedicated GitHub Actions workflow. AST IMPORTS ARE ONLY SYNTACTIC EDGES and cannot establish a complete dynamic call graph, substitutability, exhaustive ABI, transitive behavior, user rights or production safety.

## 2. Executed original V1 versus opt-in V2 behavior

Existing scripts/m2_a03_behavior_equivalence_lab.py compares untouched V1 ReplayClock, original BacktestHarness/SignalDecision and 16-zone UNVERIFIED engine with opt-in V2 StrictReplayClockV2, StrictReplayHarnessV2 and typed UNVERIFIED records. Using six fabricated causal revision events at four as-of times, 16 B/S zones, and two original strategies, 128/128 decision comparisons match only UNVERIFIED with empty evidence. Fixture event visibility and typed UNVERIFIED roundtrips match. This DOES NOT verify DETECTED/NOT_DETECTED zone behavior, buy/sell execution, indicator formulas, source provenance, full public API compatibility, trading, licence or physical Drive cache.

TWO COMPATIBILITY DIVERGENCES confirmed by actual inherited function calls:

1. Original replay.ReplayClock.as_of_utc is public and directly assignable backwards; V1 advance_to prevents rewind but a direct field assignment does not. StrictReplayClockV2 rejects backwards direct assignment with ValueError and preserves current clock. An explicit opt-in adapter, complete consumer impact audit and rollback approval are needed; do not edit inherited V1 silently.
2. Original contracts.Evidence.verified accepts truthy integer 1 under legacy dataclass semantics; StrictEvidenceV2 requires type(bool) exactly and rejects integer 1 with TypeError. No automatic truthy coercion to verified is authorized. Explicit owner-approved legacy cleansing/migration required.

The new A03 machine result explicitly labels these two differences INTENTIONAL_STRICTER_NON_INTERCHANGEABLE, rather than claiming full 1:1 ABI or functional interchangeability. It continues to label all legacy A02 owner 63/63 reviews UNSIGNED.

## 3. Additive-only Draft PR #8 artifacts

- scripts/m2_a03_eight_v2_abi_dependency_trace.py: real original AST/H3 63-row evidence crosswalk, exact eight V2 public API/static source SHA, original direct/transitive AST module import maps, actual V1/V2 strictness negative calls, existing 128-case UNVERIFIED-only differential. All owner/security/trade flags false.
- tests/test_m2_a03_eight_v2_abi_dependency_trace.py: 35 executable tests, including exact eight sidecars, 71-file graph, transitive dependency, graph-cycle/no-self reasoning, V1/V2 original contract differences, no unauthorized upgrades and deterministic safe fixture fingerprint.
- .github/workflows/m2-a03-eight-v2-abi-dependency-trace.yml: GitHub-hosted PR8-only contents:read, independent LIVE remote Git tree proof and 35 tests, JSON/Markdown artifact retained 14 days with no market-data secrets or external authorities.
- docs/MST_A03_EIGHT_V2_ABI_DEPENDENCY_TRACE_QA_20261110.md: this QA report and corresponding permanent Google Drive QA copy.

No original V1 or eight pre-existing V2 source paths modified, no user Mac/MOCHI/local or third Cloud, no live market-data vendor calls or licensed Google Drive cache, no independent signer, witness, real CAS, broker, release, production or trading action.

## 4. Verified dedicated A03 CI and fingerprints

Code/workflow HEAD: bf038b905c2aecf880db9d1f93806c576781a3c9.
Dedicated A03 https://github.com/ngluonghoa/MST/actions/runs/42790463943 — SUCCESS 35/35 tests; 128 safe synthetic decision comparisons; 2 intentional incompatible contracts; real original upstream/main/PR source lock PASS.

Original static public ABI inventory fingerprint: 20eb42b4266511ebb6578fc7bf686165eac5c291dae50a752909866d4166dfe6.
Eight V2 source ABI/AST trace fingerprint: 9024066780eb790ba5789c8d6ead0e59027717e13dcf026f52b4f5b229cbb892.
Existing 128-safe-UNVERIFIED fixture fingerprint: ed679df33ba73c8a49bac2c85d8528453815180a43cd31d4f9b516372ea78d97.

Foundation and exact final report-containing PR commit statuses must be separately verified before attributing all-workflow SUCCESS to the final commit.

## 5. Remaining owner and production blockers

A02 original V1 limited file-scope exercise 63/63; owner formal approvals 0/63. Eight existing opt-in V2 sidecars static ABI/import traced; A03 full original-to-V2 behavioral and public ABI owner approvals 0/8. Real vendor rights, official session calendar, live authenticated feed/source revisions, physical Drive cache, independently enrolled signer, monotonic witness floor, fresh revocation, server-enforced multiwriter CAS, calibrated zone detectors, complete V1/V2 ABI, production and trading all UNPROVEN. OA01–OA06, G01–G08 and M3/M4/M5/M8 remain OPEN/BLOCKED.

Next safe work is a targeted original-to-V2 consumer-driven ABI and behavioral negative-differential packet focused on original ReplayClock/Evidence and the highest-impact trading/data/cache interfaces, with independent human owner review only when appropriate. The project remains GitHub+Google Drive Cloud-only.
