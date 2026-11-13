# MST — MFX-style Cloud-only app-owned source ingress (stage 1, DRAFT)
Date: 2026-11-13 (Asia/Ho_Chi_Minh). Owner accepted **the MFX architectural pattern**, NOT a production/credential/repository permission bypass.

## Decision
- **MFX pattern:** GitHub Actions on Cloud connects to a separately authorized vendor market-data endpoint, then uses the same app-specific Google OAuth `drive.file` to retain sealed private source and (later) approved Cache manifests. No Mac, MOCHI, ChatGPT background process or Google Picker.
- **Already in MST main:** `scripts/mst_oauth_manual_drive_bootstrap.py` with exact app-owned root `MST_OAUTH_CACHE_V1` and private children `STAGING_ONLY`, `CHUNKS`, `MANIFESTS`, `AUDIT`; repo secrets `MST_GDRIVE_OAUTH_CLIENT_ID`, `MST_GDRIVE_OAUTH_CLIENT_SECRET`, `MST_GDRIVE_OAUTH_REFRESH_TOKEN`. **Do not create new identities or turn bootstrap gate back on.**
- **Existing real private source Docs:** the 14 v2/v3 D1 source/manifest Docs and prior §169 QA remain owner-connected Google Drive evidence, **not** automatic OAuth input. Do not copy, delete, open ACLs or alter their provenance. Google Picker is no longer on the critical path, but an approved private import can be added later if needed.
- **Provider credentials are separate from OAuth:** ChatGPT's SSI/DNSE/VCBS MCP access does not confer GitHub vendor API credentials, use rights or storage/redistribution entitlement.

## Added in existing Draft PR23
- `scripts/mst_mfx_style_appowned_pipeline.py`: exact owner/repo/main/manual workflow context, OAuth `drive.file` read-only inspection of five existing app-owned folders. Requires `shared=false`, `ownedByMe=true`, `isAppAuthorized=true` on each, correct private parent and MIME.
- Optional OFF-by-default DNSE official `GET https://openapi.dnse.com.vn/price/ohlc` D1 read, HMAC-signed using separately owner-approved market data credentials; bounded source-window, structured OHLCV, timestamp, volume/number and incomplete-page validation; no source values in public GitHub logs.
- Separate OFF-by-default `dnse-d1-quarantine-stage`: after real DNSE read, one **unpublished** raw source candidate file may be written to OAuth app-owned `CHUNKS` with name keyed to `GITHUB_RUN_ID`/attempt (not source hash/time); document stores original source-native arrays and explicit `signal_eligible=false`. Upload requires independent source/storage-rights and owner-write approvals, first-attempt-only, exact-folder census, Drive metadata/MD5/SHA256 verification, two byte-identical media readbacks, stable file version and final exact-name census. Any unknown HTTP ACK or same-run existing file fails closed; manual review is required, not an unconditional retry. **This is NOT Cache published/atomically committed.**
- `.github/workflows/mst-mfx-style-appowned-readonly.yml`: `workflow_dispatch` only, exact owner ID/repo ID/main and `contents: read` gates, no schedule/PR/push, one serialization group. It cannot be manually dispatched on default `main` while this PR remains Draft/unmerged.
- `tests/test_mst_mfx_style_appowned_pipeline.py`: invented offline inputs; failure and privacy gate tests. GitHub CI MUST PASS at the current PR head; CI does not prove real vendor credentials, real app OAuth or Drive CAS.

## Approval matrix
1. `drive-probe`: requires existing OAuth secret trio + repository Variable `MST_MFX_APP_OWNED_READONLY_ACCEPTED=true` and separately reviewed PR merge/main manual dispatch. No market API requests/Drive writes.
2. `dnse-d1-readonly`: additionally requires private `MST_DNSE_API_KEY`, `MST_DNSE_API_SECRET`, owner variables `MST_DNSE_READONLY_OWNER_ACCEPTED=true`, `MST_DNSE_SOURCE_RIGHTS_CONFIRMED=true`, bounded exact input `symbol`, `from_unix`, `to_unix`. DNSE keys MUST be market-data-only, not trading-enabled. Request is read-only; no Drive source writes.
3. `dnse-d1-quarantine-stage`: in addition requires `MST_MFX_SOURCE_QUARANTINE_WRITE_ACCEPTED=true`, `MST_DNSE_STORAGE_RIGHTS_CONFIRMED=true`, valid first `GITHUB_RUN_ATTEMPT=1`. It writes ONE untrusted source candidate to app-owned `CHUNKS`, verifies bytes. Reset write gate immediately after any separately approved test. No auto-prune, move, delete, manifest head, public artifacts, vendor data in logs or broker trades.
4. **Production Cache publisher remains NO-GO:** separate, reviewed and owner-authorized server-enforced conditional publish-head/CAS, independently anchored signed monotone highwater, crash/ACK-loss recovery, source first-known, native session finality, source retention rights and lossless multi-provider TF parity are still required. Do not treat GitHub concurrency lock/Drive filename census/sha as independent CAS.

## Current supplier coverage
DNSE OpenAPI documentation confirms the exact D1 market data endpoint and HMAC authentication. The **DNSE connected MCP historical** product is not automatically equivalent to the official DNSE OpenAPI product; do not claim 1:1 cross-product row parity until a real API read is performed. SSI FastConnect V3 has official OHLC and authenticated SDK/REST but needs independent account/API scope and source policy. VCBS currently has connected MCP evidence; neither a GitHub-callable licensed API nor its corresponding rights have yet been proven for MST. Therefore **none** of SSI, DNSE, VCBS may be marked completed for GitHub-native ingestion yet.

## MFX parity vs MST safeguards
MFX uses the same broad GitHub -> vendor REST -> app-owned Drive -> CHUNKS/MANIFESTS pattern. MST keeps immutable-by-convention source versions separately, requires D1/M5/M15/M30/H1/H4 source semantics, source/license checks, independent CAS and rollback witness before Signal Engine consumption. The old §168 DCM 100-share provisional-to-history revision and §169 FPT September ex-right price-basis mismatch remain permanent source QA findings.

References: https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/ ; https://developers.dnse.com.vn/docs/guide/intro/authentication/ ; https://developers.ssi.com.vn/docs/tutorials/ohlc ; https://developers.google.com/workspace/drive/api/guides/manage-uploads ; https://github.com/ngluonghoa/MFX/blob/main/.github/workflows/mfx-native-htf-incremental-commit.yml

## Next milestone
After CI and separate owner deployment approval, perform a **real GitHub manual drive-probe**, observe private app-owned 5/5 folder metadata, then an owner-authorized DNSE D1 GET-only trial. Only if rights/storage/write approvals are independently granted should one quarantined source be written; then plan analogous SSI, VCBS connectors and independent authoritative Cache commit. Do not enable hourly MST automation; task ID 6af4b3f1b0408191a6265d4308a20eba stays DISABLED.


## §171 — Independently gated SSI FastConnect V3 market-data-only D1 ingress

MST Stage 1 now has **two separately credentialed Cloud source-read paths**, neither live-authorized yet. This is not a simulated second SSI source masquerading as an authenticated API read.

- Official endpoint: \`POST https://api.ssi.com.vn/api/v3/auth/token\` with \`apiKey\`/\`apiSecret\` but **no OTP**; a Bearer market-data token stays entirely in GitHub Actions memory. Next \`GET https://api.ssi.com.vn/api/v3/data/ohlc\` sends the bounded \`symbol\`, \`from\`, \`to\`, \`timeFrame=1d\`, \`pageIndex\`, \`pageSize\` and Bearer header. No trading token, account query, purchase/sell or write API is imported.
- Implementation: \`scripts/mst_mfx_ssi_readonly.py\`, called under distinct \`ssi-d1-readonly\` option in the **same existing** \`.github/workflows/mst-mfx-style-appowned-readonly.yml\` and \`scripts/mst_mfx_style_appowned_pipeline.py\`. No new workflow, merge, production data publication or scheduled process.
- Dedicated PRIVATE GitHub Secrets: \`MST_SSI_API_KEY\`, \`MST_SSI_API_SECRET\`. Owner-accepted repo Variables: \`MST_SSI_READONLY_OWNER_ACCEPTED=true\`, \`MST_SSI_SOURCE_RIGHTS_CONFIRMED=true\`. Manual workflow additionally requires the previously approved exact-MST app-owned Drive gate and existing OAuth secret trio. In read-only SSI mode, **no DNSE secret is required**.
- Bounded manual inputs: \`symbol\` among FPT, DCM, HPG; \`from_date\`/\`to_date\` as ISO \`YYYY-MM-DD\`, with max 95-day interval; max five pages of 100 records. Reject null/empty/oversized or pagination-drifting, duplicate, wrong-symbol, outside-window or invalid-price-volume source responses. Never print raw prices, dates, token, bearer JWT, API key/secret, source rows or private Drive IDs.
- **Price basis caveat:** SSI FastConnect's official OHLC response has string price fields; the connected MCP SSI compact series uses a different product/basis and cannot be silently equated or transformed. Corporate actions such as FPT's 2026-09-21 10% bonus event remain explicit adjustment-provenance requirements before signal use.
- The official API documentation says authenticated market-data token can be obtained without OTP; it does not independently prove that an owner's future API key has the necessary market-data scope or data-retention rights. Only a live owner-provisioned GitHub Actions GET can establish that access.

Official references:
- https://developers.ssi.com.vn/docs/api-reference/auth-token
- https://developers.ssi.com.vn/docs/api-reference/data-ohlc
- https://developers.ssi.com.vn/docs/tutorials/ohlc

**NO-GO remains:** real SSI vendor entitlement/API secret, actual GitHub OAuth vendor run, source-use/storage rights, native 5m/15m/30m/H1/H4/D1 and official closed-bar semantics, independent monotonic CAS/fencing, Cache release and Signal Engine/UI. SSI D1 read-only is a Cloud ingress capability under owner gate, not a Cache producer.



## §172 — Native multi-timeframe provider contracts (read-only only)

Official provider API references independently support these **native source requests** (no invented H4 endpoint):

| MST TF | SSI GET /api/v3/data/ohlc timeFrame | DNSE GET /price/ohlc resolution | Exposure |
|---|---|---|---|
| M5 | \`5m\` | \`5\` | Manual native source read only |
| M15 | \`15m\` | \`15\` | Manual native source read only |
| M30 | \`30m\` | \`30\` | Manual native source read only |
| H1 | \`1h\` | \`1H\` | Manual native source read only |
| D1 | \`1d\` | \`1D\` | Manual native source read only |
| H4 | **NOT a native API capability** | **NOT a native API capability** | Deny as native; design separately using venue-calendar/session-verified closed H1/M30 inputs |

- Added \`scripts/mst_mfx_native_timeframes.py\` as a single provider-specific native-resolution contract and H4 denial boundary.
- Existing manual-only GitHub workflow now exposes \`native_tf\` choice and separate \`dnse-native-readonly\` / \`ssi-native-readonly\` options; **no new schedule, credentials or permissions**.
- The original \`dnse-d1-readonly\`, \`ssi-d1-readonly\` and \`dnse-d1-quarantine-stage\` modes are **explicitly D1-locked** and fail closed if the timeframe input differs. The app-owned Drive \`CHUNKS\` source quarantine path is still D1-only and unpublished.
- SSI intraday native timestamp labels must include day plus HH:MM:SS; multiple distinct bars on a single trading day are not collapsed into one D1 row. Bounded pagination, duplicate source bar keys and OHLCV constraints remain enforced.
- DNSE native observations retain Unix timestamps and explicit \`nextTime=0\` requirement: an incomplete/paginated response must fail closed rather than being treated as a completed batch.
- Source validity is **NOT venue close/finality**. None of these read-only modes independently prove native session/calendar anchoring, issuer first-known, complete historical coverage, post-close revision reconciliation, source storage entitlement, or numerical price adjustment. Output receipts set \`source_closed_bar_attestation_proven=false\`, \`H4_venue_session_aggregation_proven=false\`, \`trade_signal_eligible=false\`.
- Before adding any H4-derived Cache, define a published source-session calendar (Vietnam stock market, trading breaks/holidays), aggregation alignment, no half-built windows, live/closed-bar distinctions, multi-provider price basis and parity to Swing Trading 1.8. **Do not equate an arbitrary four-hour clock window with a verified H4 trading candle**.

Documentation confirmed:
- https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc
- https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/
- https://developers.dnse.com.vn/docs/guide/intro/authentication/

The DNSE HMAC signature signs the fixed URL PATH, not its query string (official SDK and authentication specification). The SSI Market Data token is no-OTP, but an owner-issued market-data-only credential and API license/use-rights approval remain a separate prerequisite to any actual GitHub-hosted call.

**Status:** native API TF read-only integration code and regression tests are prepared in Draft PR23. No owner-authorized real SSI or DNSE Cloud read, H4 aggregation, real Drive source upload, published Cache head, independent CAS/highwater, scheduled job or trade has been conducted.
