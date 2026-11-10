# MST Cache V2.1 — Owner-approved improvement backlog, staged P0→P1→P2

**Date:** 2026-11-11 Asia/Ho_Chi_Minh. **Approval scope:** user agreed to the eight **design/development proposals** from the MST Cache V1 vs V2 review. **NOT** an account/license approval, legacy 63-source release sign-off, V2 schema/ABI merge authorization, owner M4 G01–G08 or OA01–OA06 waiver, permission for live market storage or order/trading.

**Baseline:** Swing Trading 1.8 source commit \`cd90c1babae8912db31490ad614fc2ad2f868042\`; protected MST main \`4048f91beaaa3410116d97e35896c8b688384e19\` unchanged. Exactly seven cache+scan blob SHAs matched upstream/main/Draft PR #8 at previous checkpoint; 63 original V1 + eight preexisting opt-in V2 source modules must remain locked. Develop only via GitHub-hosted CI and Google Drive QA/docs, never Mac/MOCHI/local. Google Drive is intended future persistence but currently only contains engineering docs/evidence, not licensed market-data cache.

## Approved eight-point scope and strictly sequenced priorities

| ID | Priority | Improvement | Concrete acceptance contract | Current status |
| --- | --- | --- | --- | --- |
| V21-01 | P0 | Full-Policy Cache Identity | Full inherited V1 provider/endpoint/instrument/TF/session/raw-adjusted/corporate-action/calendar/aggregation/indicator/source rights/resolution/quality + explicit instrument mapping; bare V2 partition hash insufficient; deny revoked rights or historical-as-of wrong lineage | Existing synthetic full-policy consumer + versioned 4-gen manifest chain; owner V2 schema/ABI and external custody OPEN |
| V21-02 | P0 | Multi-Layer Smart Cache | Typed RAW→NORMALIZED→AGGREGATED→INDICATORS→ANALYSIS with separate LINEAGE/AUDIT dependencies; invalidate only affected descendants for source price revisions; metadata-only revision must preserve numeric unaffected indicator; unknown source state quarantines whole full-policy scope | This PR adds pure synthetic dependency planner and 28 negative/golden unit methods; NO Drive reads |
| V21-03 | P0 | Point-in-Time Versioned Cache | Preserve genuine issuer-first-known/revisions with as-of replay and historical corrections; no reconstructed past from latest data | Synthetic 4-gen lineage only; vendor origin, historical replay, revisions NOT PROVEN |
| V21-04 | P0 | Transactional Cloud Cache | Content-address immutable chunk + exact SHA readback + scoped manifests; independent protected witness/floor, real authenticated writer fencing, Drive/GitHub server-level race/CAS and recovery proof | Architecture and toy tests only; M4 G01–G08 OPEN |
| V21-05 | P1 | Adaptive Incremental Refresh | Use verified per-provider window/full-session capability, session finality and periodic historical correction reconcile; never invent vendor delta cursor or assume 5-minute closed bar | Legacy planner inherited; real SSI/DNSE/VCBS rights and capabilities OPEN |
| V21-06 | P1 | Content-Addressed Deduplication | Reuse identical chunk and unchanged 1→5→20→1→20 symbol/TF partitions; version only changed content and lineage | V1 chunk/weekly fixture simulations inherited; actual Drive IO OPEN |
| V21-07 | P1 | Observability / Self-Verification | Auditable cache hit/miss, bytes, revalidation, indicator recompute, denied source, corruption, orphan, recovery, rights revocation, quota and alert | Metrics/QA schema pending; no real performance SLO claim |
| V21-08 | P2 | Performance Benchmarks / Auto-Tuning | Cold vs warm, 1/5/20/100 symbols, M5/M15/M30/H1/H4/D1, corrections, multiple Cloud runs, Drive request overhead and 429/quota; optimize only from measured evidence | Benchmark acceptance plan pending; no claimed % savings |

## New V21-02 fixture-only validation

New scripts/m4_v21_layered_invalidation_lab.py plus tests/test_m4_v21_layered_invalidation_lab.py under an existing manifest-chain PR workflow. A node must carry the existing full V1 rights/policy binding SHA, **not** standalone V2 candidate partition SHA. Strict typed dependency DAG prevents cross-policy mix, missing/dependent cycles and invalid channels. An invented price/volume revision of fixture root A causes six connected descendants including its audit to be marked for recompute while three independent B nodes remain reusable. A metadata-only lineage event marks only RAW A and audit A, preserving unaffected numerical EMA/ATR-like derived nodes. An unqualified source change conservatively quarantines ALL nine nodes in the full-policy scope. This is only a bookkeeping preview, NOT real recomputation of indicator values or proof that the vendor's changed-since/clock is reliable.

All output permissions to licensed cache reads/writes, Google Drive I/O, signed publisher, independent CAS, source first-known, real-data reuse and trading remain false.

## Mandatory sequencing and release gates

1. Finish P0-01 full-policy identity and migration/ABI owner signoff; a passing toy binding is insufficient.
2. Extend P0-02 dependency DAG to source-versioned six TF and indicator/analysis structure only under approved equivalence tests; retain exact V1 mathematical outputs.
3. P0-03 independent issuer/rights proof and actual point-in-time ledger are blocked by M3 Issue #9.
4. P0-04 protected G01/G02 trust root/floor, G03 conditional publish, G04 retention and G05 independent Drive custody are blocked by M4 Issue #10, and must NOT be waived because CI is green.
5. Only after P0 conditions can P1 and P2 operational benchmarks use licensed Cloud data, with separate provider consent, production rollout and rollback owner approval.
6. Never merge Draft PR #8 or mutate protected main, local Mac, MOCHI or a real brokerage/trading endpoint under this roadmap acceptance alone.

## CI / evidence receipt

GitHub synthetic-only workflow: \`.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml\`. New targeted tests: 28 planned; actual GitHub Actions and exact final SHA require independent readback before marking PASS. Last earlier PR head \`644d10aac28136d9f98ca07e5ae5d9d2fa43fc9a\` had 47/47 prior Actions SUCCESS, not proof this new code passes.

Related: [M3 provider rights issue #9](https://github.com/ngluonghoa/MST/issues/9), [M4 cache issue #10](https://github.com/ngluonghoa/MST/issues/10), [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8).


## Implementation-HEAD QA confirmed 2026-11-11

Exact implementation commit \`dfb181c049004b7d92fae6f026b7729896c92f20\` independently checked: **47/47 GitHub Actions completed SUCCESS**. Dedicated full-policy and new V2.1 recompute workflow [#42889166667](https://github.com/ngluonghoa/MST/actions/runs/42889166667) succeeded, including all **28/28** new test methods and synthetic 6-of-9 price correction affected, 2-of-9 lineage-only affected, 9-of-9 unknown-source quarantined. Foundation [#42889166986](https://github.com/ngluonghoa/MST/actions/runs/42889166986) completed SUCCESS on Python 3.11 and Python 3.12 plus engineering contract/wheel checks. The earlier **217** focused synthetic source checks are unchanged, so the cumulative targeted source-plus-V2.1 scenario count is **245**, not a claim about every repository test. The existing 63 V1/8 V2 byte-lock workflows also passed at this implementation HEAD; no parent protected code altered.

This implementation CI demonstrates ONLY the toy DAG and full V1 binding metadata rules. It does not implement authorized live price input, full multi-timeframe physical Cache, Google Drive reads/writes, real revision ledger, multiwriter remote CAS/floor, storage rights or trading authorization. The report-containing commit that follows must be checked independently for its own exact-head full CI status.
