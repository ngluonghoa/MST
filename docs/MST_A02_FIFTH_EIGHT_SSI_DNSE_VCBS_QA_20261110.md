# MST A02 — Fifth Distinct Eight Original V1 Modules: SSI / DNSE / VCBS Source Semantics and Fallback QA

**QA ID:** MST-A02-V1-FIFTH-EIGHT-SSI-DNSE-VCBS-20261110
**Date:** 2026-11-10 (Asia/Ho_Chi_Minh)
**Verdict:** **PASS** for 40 new actual-inherited-V1 runtime tests and 8 linked source-trust safety assertions; **28/28 workflows SUCCESS at the exact code/workflow HEAD**. External market-data rights, M4 G01–G08, human owner approvals, production/trading **NO-GO**.

**Review surface:** https://github.com/ngluonghoa/MST/pull/8 — Draft, unmerged, additive-only.

## 1. Original source identity and distinct coverage

Upstream source Swing Trading 1.8 commit cd90c1babae8912db31490ad614fc2ad2f868042, protected MST main 4048f91beaaa3410116d97e35896c8b688384e19, original Git tree d61bad11af6d7c21bfb922a4f80d379d4dfe3e8e. Dedicated GitHub-hosted CI rechecked REAL upstream/main/PR Git trees independently of synthetic assertions: all **63 original V1 Python modules unchanged**, all **8 pre-existing opt-in V2 sidecar source modules unchanged**. No inherited source edit or protected branch merge.

Fifth eight DISTINCT original modules not in the previous 32:
- ssi_intraday_label_diagnostics
- ssi_multivenue_review
- ssi_source_qualification
- ssi_volume_parity
- dnse_d1_reference_fallback
- vcbs_source_contract
- d1_mcp_transport_bridge
- c2_fair_source_benchmark

Five eight-module runtime tranches have now exercised limited synthetic actual-code behavior across **40/63 DISTINCT original V1 modules**, leaving **23** outside this batch-style runtime review. The earlier H3/AST 63/63 is a static API inventory, not full behavior certification. Even the 40 executed modules have NOT received human signoff and are NOT proved fully equivalent to V2.

All fixture price numbers, provider metadata, volume values, labels, clocks, Ed25519 keys where applicable, and transport responses are synthetic. Inputs come from existing unit-test fixture builders; ACTUAL inherited V1 domain functions execute, not mocks of those eight functions. There is NO real provider call, source token, physical Google Drive market cache or broker interaction.

## 2. Eight linked executable source-trust observations

1. **SSI intraday time-label geometry:** reported labels at 09:00, 09:01, 09:03 cause one apparent minute gap, yet the original diagnostics reports only conditional label geometry. It does NOT certify the missing M1 candle, that no trades occurred, first-known source provenance or official date-time semantics.
2. **SSI all three venues:** three fabricated HNX, HOSE and UPCOM SSI volume-parity samples are classified ALL_VENUES_OBSERVED_UNCERTIFIED, with three matched totals, but still only ONE provider, no provider-independent witness, trading calendar or licensed data. Duplicate identical symbol/venue/date is blocked.
3. **SSI ambiguous date contract:** a DD/MM timestamp that contradicts MM/DD provider documentation, and a 04/11 label with both date interpretations, cannot be silently converted to an approved UTC market instant. An independently verified clock-label policy remains required; the synthetic helper can model that flag, but does NOT certify vendor origin.
4. **SSI intraday vs D1 volume:** three synthetic intraday rows total 4,100 and a synthetic D1 matched-volume receipt totals 4,100; state MATCH_UNCERTIFIED, NOT full minute coverage, source entitlement or backtest qualification. Mismatch 4,101 returns BLOCKED; unknown date-layout or empty intraday is also denied.
5. **SSI→DNSE D1 fallback only:** SSI primary quote avoids DNSE fallback; when SSI unavailable, DNSE can provide reference D1 OHLCV, not native M1/M5/M15 candles, indicator eligibility, corrected corporate-action parity or trading. Unknown programming errors must not be disguised as source outages. No real network called.
6. **VCBS price and volume basis:** a synthetically parsed VCBS RAW D1 reference keeps rights_verified/indicators_allowed/actionable false; intraday price-points are NOT native minute OHLCV. Adjusted/raw price fields and total/matched volume scope cannot silently mix.
7. **Injected D1 bridge callback receipt segregation:** normal local fixture SSI response produces SSI-only receipt; explicit simulated DOWNSTREAM_UNAVAILABLE yields SSI-unavailable then DNSE-fetched receipts. Typed provider identity and two receipts are tested but remain same-process fixture callbacks, NOT authenticated MCP credentials or independent custody.
8. **Two reported sources' D1 parity is not true source verification:** fabricated SSI and VCBS same RAW matched-basis OHLC yields COMPARABLE_REPORTED and equal_sessions=1, but source_integrity_verified=false and actionable=false. If price basis is UNVERIFIED or volume scope differs, comparison blocks. `require_benchmark_source_authority` explicitly raises PermissionError.

The eight cross-boundary claims are verified in a joined actual-original-code runtime matrix and additional per-module focused negative tests. All human owner, licensed market-data, physical Drive, source freshness, full native minute coverage, independent signer and trading authorization values remain FALSE.

## 3. Additive-only PR #8 artifacts

- `scripts/m2_a02_fifth_eight_source_semantics_runtime_lab.py` — executes the eight real inherited V1 modules with fabricated fixtures; emits a bounded, deterministic schema `mst.a02.fifth-eight-ssi-dnse-vcbs-source-semantics.synthetic.no-go.v1` with eight positive safety assertions.
- `tests/test_m2_a02_fifth_eight_source_semantics_runtime_lab.py` — **40 additional tests** of conditional clock labels, cross-venue evidence, timestamp policy conflicts, volume mismatches, provider fallback, VCBS price/volume basis, injected transport receipts and two-caller-source parity denial.
- `.github/workflows/m2-a02-fifth-eight-source-semantics-runtime.yml` — GitHub-hosted PR8-only contents:read, independently runs real remote original/main/PR Git source tree lock, then 40 tests and linked runtime no-go receipt; retains only nonauthenticating review JSON for 14 days. No vendor data, keys or Drive market bytes are uploaded.
- `docs/MST_A02_FIFTH_EIGHT_SSI_DNSE_VCBS_QA_20261110.md` — this QA report; copied to MST Google Drive QA.

No source `src/swing_trading` module modifications. No GitHub/Drive ACL, branch protection, ref, ruleset, signer, witness, real market cache, PR merge, release, real trade or broker actions.

## 4. Observed real GitHub-hosted CI

**Code/workflow HEAD:** 585efe4daee2fce96a96d200a6f66e510e519803.
- Fifth-eight dedicated CI: https://github.com/ngluonghoa/MST/actions/runs/42774482345 — **SUCCESS, 40/40 PASS**, eight joined actual-source safety assertions PASS, remote Swing/master/current-PR source lock PASS, no real network, production or market rights.
- Foundation: https://github.com/ngluonghoa/MST/actions/runs/42774482432 — **SUCCESS 3/3 jobs**, Python3.11 **2705/2705**, Python3.12 **2705/2705**, 63 inherited V1 source engineering boundary, H2/H3/lint/wheel PASS.
- **28/28 workflow runs SUCCESS on exact CODE/WORKFLOW HEAD.** After adding this QA Markdown file, VERIFY report-containing PR HEAD separately; do not automatically transfer CI result across commits.

## 5. Owner gates and next safe work

A02 human owner module dispositions remain **0/63**; grouped selected synthetic runtime coverage is **40 DISTINCT originals**, with 23 still outside this review. A03 full V2 ABI/behavior owner acceptance remains OPEN; two earlier confirmed legacy V1 compatibility gaps (ReplayClock public field rewind and truthy non-boolean Evidence.verified) remain unchanged pending separate approval.

OA01–OA06 owner decisions and G01–G08 genuine independent controller, provider right, immutable floor, authenticated writer/server CAS, physical Drive bytes, signer/revocation/provenance/release requirements remain OPEN; M3/M4/M5/M8 production/trading remains NO-GO. No locally signed test, caller-reported vendor name or equal volume/price totals can promote vendor account identity, official market calendar or cache/trading rights.

**Next safe A02 review:** select a sixth non-overlapping batch from the 23 remaining original modules, prioritize replay_batch, evidence_checkpoint/evidence_recovery, migration and reference-storage guardrails. Only use GitHub Actions and Google Drive Option A; never Mac/MOCHI/local or a third Cloud. Keep original Swing source 1:1.
