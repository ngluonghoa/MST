# MST M2/A02 W3 — Multiwriter fencing, cross-instance rollback and source-partition custody review

**Date:** 2026-11-09 · **Scope:** GitHub-hosted ephemeral, fabricated metadata; V1 source-locked / V2 candidate observational QA only.  
**State:** Draft PR #8; **no live Drive data**, independent key/witness, distributed CAS, vendor entitlements or production authorization.

## Original provenance and scoped source inspection

- Original Swing Trading 1.8 source commit: `cd90c1babae8912db31490ad614fc2ad2f868042`. MST `main@4048f91beaaa3410116d97e35896c8b688384e19`, source-locked Git tree `d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e`. **All original 63 Python source modules unchanged**, including `pyproject.toml`; no merges.
- Candidate `src/swing_trading/v2_cache_fencing_lab.py`: Git blob `f5fdc6d3cbbd235a48887aab0053ce96455c1089`, `FixtureManifestWitnessV2.open_fence`, `submit`, `seal`, `head`. Uses Python instance dictionaries `_heads`, `_history`, `_epochs`, `_tickets` and `_sealed`. Source explicitly denies distributed CAS, durable trust/author, rights/Drive transport.
- Candidate `src/swing_trading/v2_cache_partition_plan.py`: Git blob `8110a9aa45f45c76f403d08a766b74a3beab8b4c`, typed full synthetic provider+endpoint+instrument+timeframe+basis+revision namespace identity. No verified vendor entitlement or partition owner.
- Candidate `src/swing_trading/v2_cloud_ref_witness_plan.py`: Git blob `a67240de25e25f09369b45213d31ca5f01424d4e`, Git-ref fast-forward *proposal* and caller-supplied ref readback only, no real GitHub API write.
- Candidate `src/swing_trading/v2_cloud_publish_verify_lab.py`: Git blob `33aa30fb1a1d3a9010006972deeb088f6898c636`, compares claimed Git commit, Drive object and final ref readbacks. `CONSISTENT_CLAIMS_UNATTESTED` explicitly means no independent proof.
- Reviewed existing focused tests `tests/test_m4_v2_cache_fencing_lab.py`, `tests/test_m4_v2_cloud_ref_witness_plan.py`, `tests/test_m4_v2_cloud_publish_verify_lab.py`, `tests/test_provider_head_custody.py` for existing coverage. Added new `tests/test_m2_a02_w3_multiwriter_rollback_custody.py` rather than modifying legacy sources.

## New independent negative/positive scenario matrix

| Scenario | Observation in fabricated test double | Proven boundary |
| --- | --- | --- |
| Shared verified-by-test G1, two independent witness instances, writer A vs B | Both accept conflicting G2 manifests and each retains different head from same parent | Process-local `submit` linearization **does not provide distributed CAS** even with shared ancestor |
| Witness A `seal(partition)` while witness B has its own copy of G1 | A correctly denies writes; B successfully commits G2 | Revocation lacks independent cross-account propagation/durable authority |
| Witness A holds G2; new witness instance starts with no persisted custody state | New witness accepts old G1 digest/time for same partition | In-memory epoch/head/floor **not durable** across restarts |
| One witness G1 content A, G2 content B, G3 content A with increasing clock | G3 accepted without `recovery_of_manifest_digest` | Increasing generation/time alone **cannot prove semantic source freshness**; old payload may be reintroduced without declared recovery |
| One witness partitions SSI, DNSE, VCBS | Provider partition hashes differ; seal SSI leaves DNSE/VCBS writes possible; cross-partition ticket denied | Positive namespace isolation, but provider IDs are only labels, not licenses |
| One provider, different source revision namespace | Independent heads each accepted | Versioned identity separation; no automatic continuity/rights migration across namespaces |
| Two competing self-consistent Git commit+Drive+ref readback claim sets | Both return `CONSISTENT_CLAIMS_UNATTESTED`, not permission | Separate caller-controlled observations can each look correct; **only independently authenticated remote readback and centralized append-only fence can settle a fork** |

These cases are distinct from previous tests proving one-instance stale fence rejection. The existing local test's two-witness divergent genesis is extended to *shared G1 then competing G2*, which is the relevant lost-serializability scenario.

## Suggested M4 owner acceptance gates — OPEN, NOT IMPLEMENTED

1. **W3-MULTI-G01 shared linearization**: exactly one external active writer transition per canonical partition; enforce durable compare-and-swap against an independently protected last-accepted head, not two process-local clocks; prove simultaneous fork losers are rejected, including two runner accounts and reused credentials.
2. **W3-MULTI-G02 persistent monotonic floor**: trusted partition generation+head/clock state, publisher epoch and key identity survive GitHub Action runner shutdown/restart and account replacement; authenticate writer and protect rollback floor against caller-provided downgrade.
3. **W3-MULTI-G03 durable entitlement/revocation**: authenticated data-provider scope/retention and per-partition writer rights; revoke one writer/provider across all live instances and new instances; block and quarantine stale events and previously uploaded objects per retention terms.
4. **W3-MULTI-G04 content/source-clock freshness**: require authenticated source first-known/source observation plus accepted prior content and revision lineage; old content reintroduction only through explicitly reviewed recovery flow with `recovery_of` and independent authority, distinguish legitimate vendor revisions and deletions.
5. **W3-MULTI-G05 real two-service read barrier**: validate protected Git commit parent/ref/tree + immutable Drive object payload SHA and authorized retention, and read back both services after promotion, fail closed on publication races/unknown responses, replay/conflicting signer.
6. **W3-MULTI-G06 provider and policy independence**: prove SSI/DNSE/VCBS and each endpoint, ticker, timeframe, basis, correction namespace, calendar and rights policy are independently fenced with no cross-source claims or stale revocation.
7. **W3-MULTI-G07 fail-closed product receipt**: do not silently upgrade `CONSISTENT_CLAIMS_UNATTESTED` to an authorized cache, backtest, cloud writer or trading signal; expose signed durable evidence, not just a local `success` count.

## CI evidence and governance

Added **7** source-locked synthetic tests on [Draft PR #8](https://github.com/ngluonghoa/MST/pull/8). Exact code HEAD `b44f0d8a9f0037f2d9f42b12d0789a1e61739ffb` passed [GitHub Actions #42580003475](https://github.com/ngluonghoa/MST/actions/runs/42580003475) **SUCCESS 3/3**: Python 3.11 **1,579/1,579**, Python 3.12 **1,579/1,579**, engineering **63/63**, H2/H3/lint/wheel. The report-containing HEAD `5238d410d8f99f6807bf85c8371b75aad60c76d5` also passed [GitHub Actions #42580254428](https://github.com/ngluonghoa/MST/actions/runs/42580254428) **SUCCESS 3/3**: Python 3.11/3.12 **1,579 each**, engineering **63/63**. Tracking [Issue #13](https://github.com/ngluonghoa/MST/issues/13) adds distinct owner acceptance gates beyond general M4 Issue #10. Reverify this evidence-only follow-up HEAD in Actions before canonical Drive checkpoint.

**Known blockers:** A02 63 owner-reviewed module dispositions OPEN; A03 opt-in V2 ABI/release approval OPEN; M3 independent verified SSI/DNSE/VCBS entitlement + authenticated source clock + permitted Drive retention UNVERIFIED; M4 real Google Drive cache objects/private signer/independent protected monotonic floor/multi-account CAS/fencing/rollback and crash recovery NOT IMPLEMENTED; production trades and live deployment NOT AUTHORIZED. No Mac/MOCHI/local. Changes only to candidate PR test/report files. This is not an exploit demonstration against GitHub or Google Drive and must not be described as one.
