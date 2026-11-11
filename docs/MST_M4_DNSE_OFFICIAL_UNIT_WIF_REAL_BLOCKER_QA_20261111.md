# MST M4 — DNSE official stock-price unit evidence, legacy unit-token conflicts and real WIF block

Date: 2026-11-11 Asia/Ho_Chi_Minh. Draft PR #8 additive, Cloud-only. Status **DOCUMENTARY EVIDENCE + REAL USER-CONNECTED DRIVE METADATA; NO AUTHENTICATED PRODUCTION DATA SOURCE / GOOGLE WORKLOAD IDENTITY**. Master Handoff through §121 and current Spec/Gap reviewed first.

## New independent DNSE documentation finding

Verified public official DNSE OpenAPI source:

1. **Official DNSE trading flow** https://developers.dnse.com.vn/docs/guide/intro/trading-flow/ explicitly states that for **STOCK**, API quoted market prices are measured in **thousands of VND**, multiply by 1,000 for the price value in VND when submitting an order. This is the first direct official written vendor evidence for the 1000 comparison hypothesis, not merely a cross-provider numeric coincidence.
2. **DNSE /price/ohlc history** https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/ publicly documents `1,3,5,15,30,1H,1D,1W` resolution and numeric `t,o,h,l,c,v`, signed API calls with `X-API-Key`, `X-Aux-Date`, `X-Signature` and optional `version` date header, plus `nextTime` pagination. This page does **not** explicitly state **price adjustment basis** or specific OHLC numeric currency units in its field schema. An authenticated vendor-specific contract/version is still required before treating connected ChatGPT DNSE `price_get_history` as production-qualified D1 or M5 source.
3. **DNSE WebSocket OHLC Closed** https://developers.dnse.com.vn/docs/guide/market-data/connect/ publicly documents `ohlc_closed.{resolution}.{encoding}` with start-time candle label, but no actual JWT/API account or GitHub runner session is proven for MST. A public feature is distinct from a working authenticated connector.
4. **DNSE date-based versioning** https://developers.dnse.com.vn/docs/guide/versioning/api/ explains the `version: YYYY-MM-DD` header is effective **per request**, not per API key. Existing connected ChatGPT MCP real snapshot rows do not include an independently authenticated effective endpoint version or adjustment lineage. Do not silently assume the REST docs example version matches the MCP source contract.

**New evidence level:** general STOCK API price unit `thousand VND` now has official **vendor documentation**. **Not yet evidenced:** the exact source unit and price basis of the connected MCP D1 output under a known API version, licensed cloud retention, provider first-known correction, and approved canonicalization. Thus no source unit renaming, source file rewriting, cross-provider price conversion for trading or automatic Cache.

## Existing owner-private real snapshot and metadata findings reused

MST FPT/DCM/HPG × SSI/DNSE/VCBS: 9 source-partitioned private Google Docs, 20 historical D1 rows each, 180 real rows, 2026-10-14..2026-11-10. Independently audited in last Handoff §121. Source-native SSI/VCBS OHLC agree for the sample; a *descriptive-only* ×1,000 DNSE ratio matches; three-way volume agrees. This is not a release signoff.

Source/manifest DNSE unit-label mismatch remains, UNMODIFIED in historic source:
- FPT snapshot `source_native_DNSE_units_unverified`, manifest `source_native_units_unverified`.
- DCM snapshot `source_native_scale_unverified`, manifest `native_scale_unverified`.
- HPG snapshot `source_native_scale_unverified`, manifest `native_scale_unverified`.

These are **three metadata conflicts**, NOT three numeric quote errors. Earlier `scripts/m4_private_d1_dual_schema_manifest_quarantine_lab.py` already detects and quarantines them. Never mutate original sources or old manifests to hide historical evidence.

### New owner-private evidence overlay V1

Created an additional metadata-only native Google Doc under MST `02_QA_RELEASE_EVIDENCE`:
https://docs.google.com/document/d/11fq_huON4acbUaNB5_KXY23BzMxTTMUCYPK6w-6yQvk/edit

It contains a source-URL evidence register, the 3 exact unresolved source/manifest token pairs and corresponding private document IDs, observed aggregate counts, explicit vendor/API version uncertainty, release deny flags, and the verified current WIF/default-branch preflight state. The overlay was independently **read back and confirmed not shared**, with the expected single private QA folder parent. It holds **no raw licensed price bar arrays**, vendor API keys, GCP service-account key, passwords or tokens. Original private snapshot/manifest docs left unchanged. Metadata overlay is not a vendor-authorized source correction, license or approved data transformation.

## Cloud WIF readiness — independently verified real repository/Drive status

On 2026-11-11 the `.github/workflows/m4-drive-wif-metadata-only-manual.yml` file was **present in Draft PR #8** at ref `mst/m2-a03-opt-in-v2-sidecar-20261109`, but a direct GitHub fetch of that exact path at `main` returned **404 NOT FOUND**. Current protected main source SHA `4048f91beaaa3410116d97e35896c8b688384e19`. The WIF workflow intentionally supports only `workflow_dispatch` on `refs/heads/main` and demands exact immutable GitHub repository/owner ID condition. Therefore **it cannot be executed in the default-branch context as currently deployed**. Merely having it in a Draft PR or seeing successful fake unit tests does not perform an STS token exchange.

Current user-connected Google Drive metadata confirms the FPT quarantine folder has **only an owner user permission** and is `shared=false`. MST QA folder likewise remains `shared=false`. This is a sound default, but there is **NO observed exact Google service-account viewer grant** and no authenticated GitHub runner `files.get`. The available GitHub connector has **no repository variables/secrets enumeration tool**, so variables `MST_GCP_WIF_PROVIDER`, `MST_GCP_DRIVE_SA_EMAIL`, etc. are **NOT INSPECTED**, not known absent. Google project/pool/provider/SA creation, mapping, trust condition, audience, impersonation binding and user-authorized account are **NOT inspected or verified**. Do not invent them.

Existing protected default-branch manual WIF design:
- https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/.github/workflows/m4-drive-wif-metadata-only-manual.yml
- https://github.com/ngluonghoa/MST/blob/mst/m2-a03-opt-in-v2-sidecar-20261109/docs/MST_M4_WIF_IMMUTABLE_ID_TRUST_SETUP_QA_20261111.md

No merge, no service-account sharing, no GCP or GitHub variable mutation, no schedule and no production writer were performed. If moving to WIF on default branch, isolate a **small protected owner-approved code-only workflow promotion** instead of merging the entire broad unverified Draft PR. Do not promise background runner checks.

## New Cloud-only guard shipped separately on Draft PR #8

- `scripts/m4_dnse_documented_stock_unit_overlay_guard.py`: read-only and pure; verifies official documentary evidence scopes, three explicit DNSE unverified unit pairs, source-preservation flags, API version/price-adjustment/retention NO-GO and main-only manual WIF not yet deployed. The output is sanitized metadata counts and booleans; no private file IDs, quote values, API tokens, source dates or source file hashes are exported.
- `tests/test_m4_dnse_documented_stock_unit_overlay_guard.py`: 40 wholly fictional source-doc/manifest IDs + three invented symbols with strong negative attempts to self-approve unit conversion, vendor first-known, authenticated WIF, Google Drive sharing, API version or production. Running these synthetic tests is NOT real Google Drive auth.
- Existing unprivileged PR-only `.github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml`: synthetic tests and no-go report; no extra production IAM permissions.

### Open gates

DNSE exact `/price/ohlc` and connected MCP D1 issuer-account official unit and adjustment basis confirmation under effective version; vendor terms/rights for long-term Cloud storage; signed source-first-known corrections; official venue calendar; real native M5 closed source access; authenticated GitHub Actions OIDC→dedicated GCP pool/provider/SA→owner-private Drive metadata read; external protected CAS/antirollback highwater; owner approved code promotion and later production release.

This checkpoint must NOT raise production Cache or trading status, publish raw quotes to GitHub, alter original snapshot/manifest metadata, merge Draft PR, or change the locked six MST signal TFs M5/M15/M30/H1/H4/D1.
