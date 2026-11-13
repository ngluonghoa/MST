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


## §173 — SSI intraday request wire-format correction; bounded provider-native probes

Verified SSI's published GET `/api/v3/data/ohlc` contract requires:
- D1 `from/to`: `YYYY/MM/DD`.
- M5/M15/M30/H1 `from/to`: `YYYY/MM/DD HH:mm:ss`. The earlier adapter incorrectly sent date-only values for intraday and could have been rejected or ambiguously interpreted.
- In PR23 `scripts/mst_mfx_ssi_readonly.py`, intraday requests now explicitly use `00:00:00` on the first calendar date and `23:59:59` on the last date; D1 retains the date-only format. Source-native intraday strings `YYYY-MM-DD HH:mm:ss` and `YYYY/MM/DD HH:mm:ss` are canonicalized to the same bar key before duplicate detection. This change **does not** claim timestamp timezone, venue session, first-known or provider-native close is independently certified.

Conservative single-manual-probe request windows are now centralized in `scripts/mst_mfx_native_timeframes.py`, used by **both SSI and DNSE**:
- M5: maximum 5 calendar days; M15: 10; M30: 20; H1: 35; D1: 95.
- SSI limits use inclusive requested calendar dates (difference in dates). DNSE limits use Unix-timestamp elapsed seconds. Each read is separately limited by the existing SSI 5 pages × 100 rows or DNSE 2,048 bar-count bound, and any continuation/incomplete response is rejected. These small windows are conservative **anti-truncation probes**, NOT a general historical Cache-ingestion algorithm, completeness proof or promise that a vendor always returns a complete candle series. Longer history requires bounded partitioned backfill with overlap reconciliation, monotone source versions, source calendar and restart-safe checkpointing, separately reviewed.
- Historical REST response with `nextTime=0` proves only vendor pagination exhaustion, not that the latest returned bar is closed. DNSE's separate real-time `ohlc_closed.{resolution}.{encoding}` WebSocket channel documents events emitted upon closing a candle, distinct from the mutable `ohlc` channel; these events could inform a future first-known/closure receipt design but have NOT been connected or verified as official exchange finality. Do not set `source_closed_bar_attestation_proven=true` from REST alone.
- Earlier development intermediate GitHub CI runs failed because synthetic native M5 fixtures requested more than the new limit, and D1-only rejection was masked by time-window checks. Fixed the tests to use bounded M5 requests and made explicit D1-only/mode denial take precedence. Latest exact-head CI is the acceptance criterion, not those intermediate failed runs.
- No vendor credentials or app OAuth scopes were changed; nothing was merged to main, no private source market data was uploaded, no Cache head was published, and no scheduler or trade was enabled.

Primary contracts:
- https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc
- https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/
- https://developers.dnse.com.vn/docs/guide/market-data/connect/

**Stage 1 still NO-GO for production:** real owner-authorized cloud OAuth and marketdata-only vendor runs, usage/retention entitlement, stable all-TF backfill and source finality, VCBS independently licensed provider adapter, signed independent CAS/highwater, actual private Cache publisher and 1:1 E2E Signal Engine parity.



## §174 — SSI V3 authoritative pagination integrity and provider-secret isolation

Checked the live-published SSI FastConnect V3 **Quick Start** and **GET /api/v3/data/ohlc** response contract. Some SSI response versions include `itemsCount` (total result rows), `pageCount`, `pageNumber`, `pageIndex` and `pageSize`; these are independent guards. The old MST reader accepted a short page and concluded success without ensuring that `itemsCount` rows had been seen. That was a false-completion risk for Cache source ingress.

**Fixed in existing** `scripts/mst_mfx_ssi_readonly.py`:

- Enforce returned `pageSize` equals requested bounded size (100). Require at least one of `pageIndex` or `pageNumber`; if both appear, both must equal the requested one-based page. Do not treat missing or inconsistent index metadata as trusted.
- If `itemsCount` is supplied, require a positive integer no more than the 500-row single-probe cap, constant across all retrieved pages. The final unique candle count **must exactly equal** the declared count; fail closed on mid-read count mutation, missing rows, duplicate timestamp, premature zero-row continuation or count exceeding the bound.
- If a short page is returned **without** `pageCount` but the declared `itemsCount` has not been reached, continue reading instead of incorrectly concluding completeness. Stop/fail if source page structure or remaining count is not satisfied.
- If `itemsCount` is absent (the minimal API reference example omits it), the reader can still return a **read-only observation** with strict page index/page size checks. It now explicitly reports `source_items_count_verified=false` and `complete_historical_source_coverage_proven=false`. Do not promote such a result into a publisher.
- A matching count proves only that this server response was traversed consistently. It does **not** prove trading-session continuity, immutable source versions, official close, license or all historical coverage.

**Reduced GitHub credential exposure:** Existing manual workflow `.github/workflows/mst-mfx-style-appowned-readonly.yml` now injects the separate SSI market-data API key/secret into the action step **only for `ssi-*` modes**, and DNSE key/secret **only for `dnse-*` modes**. The `drive-probe` mode therefore receives neither vendor credential in its step environment. Existing OAuth `drive.file` trio remains mandatory to verify app-owned folders; no new secrets, IAM or permissions were created.

Updated existing SSI tests to model source count drift, insufficient final page, count beyond request bound, page-size drift, conflicting index aliases, short-page continuation, and lack of source-completeness proof. Historical synthetic fixtures were corrected after CI caught an invented empty continuation with no page envelope. **Only a GitHub CI success on the exact final PR head is sufficient to mark code QA PASS.**

Vendor contracts: https://developers.ssi.com.vn/en/docs/getting-started/first-api-call ; https://developers.ssi.com.vn/en/docs/api-reference/data-ohlc ; https://developers.ssi.com.vn/en/docs/api-reference/auth-token. The Quick Start and API reference illustrate differing `from/to` date spellings; the current code follows the detailed endpoint reference and awaits an actual licensed GitHub API read to prove negotiated server behavior.

**Still NO-GO:** GitHub OAuth manual real Drive read, independent SSI/DNSE vendor credentials and retention rights, source-first-known and venue closed bar, VCBS standalone API, partitioned source-versioned history/backfill, independent signed persistent CAS/highwater, protected Signal Engine parity and any schedule/trading. No ChatGPT MCP secret/permission is reused or serialized to GitHub.



## §175 — Real Google OAuth proof recovered; genuine connected-provider intraday QA (13 Nov 2026)

**Corrected historical gate finding.** Read the actual GitHub-hosted manual bootstrap logs on protected `main`:
- [GitHub Actions 43036386359](https://github.com/ngluonghoa/MST/actions/runs/43036386359) completed with `MST_OAUTH_DRIVE_FILE_READ_ONLY_PROBE_PASS` and `actual_google_drive_metadata_read=true`. This proves a **real GitHub-origin OAuth Drive read on 11 Nov 2026**, not a simulated CI test.
- [GitHub Actions 43037551110](https://github.com/ngluonghoa/MST/actions/runs/43037551110) completed with `MST_OAUTH_APP_OWNED_FOLDERS_METADATA_READBACK_PASS`, `app_owned_folder_count=5`. Existing approved OAuth `drive.file` bootstrap created/read back app-owned root and four children. No market Cache data was written by those runs.
- Prior wording implying **GitHub OAuth had never been verified** was too broad. The still-open gate is **the new PR23 workflow's independent owner-reviewed manual execution** and its **direct market-provider API entitlements**, plus secure source storage/write authority. The earlier runs do **not** prove long-term OAuth refresh continuity, licensed vendor access, independent source-first-known, source retention rights or an actual Cache publisher.

**Real connected-provider market source observations, separately kept PRIVATE** (not GitHub-app-owned and not raw content in GitHub):
- 13 Nov intraday: source-native SSI intraday ticks and VCBS minute-last-price series captured for FPT/DCM/HPG. Six canonical private source snapshots hold **1,291 entries** (SSI 643 ticks; VCBS 648 minute-price points). One extra earlier HPG capture was byte-for-byte equivalent in native ticks, explicitly excluded and marked as an ignored redundant audit capture, not double counted.
- Only **643 minute clock labels** occur in both provider reports. Of these, **621 displayed last prices agreed** and **22 differed** (FPT 17, DCM 3, HPG 2). Different publisher sampling, event-time convention and source scopes mean equal minute labels do **not** independently prove identical exchange events.
- VCBS DCM native minute series contains two repeated labels with identical prices. **Retain original rows**; future normalization must set a deterministic duplicate policy and fail on divergent same-key values.
- SSI tick `volume` is NOT proven to be comparable with VCBS cumulative session `totalVolume`. VCBS minute-last-price series does NOT provide per-minute OHLCV and cannot be silently promoted into native M5/M15/M30/H1 bars. SSI latest vs range MCP timestamp date formats also differ; parse only with an explicit validated source format.
- At the observed time of capture, **SSI/VCBS/DNSE daily series still ended 12 Nov**. New 13 Nov intraday evidence must remain separate and **PROVISIONAL / not D1-final**, even where a displayed `ohlc_provisional` flag has become false. No issuer-signed closed-bar evidence was gathered.

Private staging and QA receipt references are stored in the owner's Google Drive Handoff §175, **not public GitHub**. The registered 6-snapshot manifest + QA were fully read back and access checked `shared=false`. Connected Google Drive verified that MST app-owned `CHUNKS` and `MANIFESTS` remain EMPTY (0/0). No OAuth app-owned input, cache publication, GitHub vendor credentials, scheduler, trading, IAM change or production merge occurred.

**Priority refined:** Treat Drive OAuth as historically *proven for bootstrap*, not a never-tested unknown. P0 owner actions should now focus on approved GitHub PR23 deployment/manual mode, licensed standalone SSI/DNSE market-data-only keys and retention rights, real source GET, post-session revision/finality and independent signed CAS/highwater. Do NOT transfer private MCP tokens or source Docs to public GitHub or equate connected ChatGPT vendor MCP credentials with GitHub vendor credentials.


## §176 — Source metadata integrity and exact native-timeframe telemetry guard (13 Nov 2026; Draft)
- Corrected the existing SSI FastConnect V3 read-only pagination acceptance gap: optional source `itemsCount` and `pageCount` must have stable presence across pages. A source field disappearing or appearing mid-read, or explicitly null, now fails closed with fixed error codes; total-absent responses remain low-authority observations that cannot qualify Cache/source completeness.
- Corrected DNSE OpenAPI native-timeframe count reporting: `observed_native_rows` is valid for all supported native TFs; legacy `observed_native_d1_rows` exists **only** for D1. M5/M15/M30/H1 must never be reported as daily coverage; H4 remains unsupported and rejected. This is a metadata classification guard, not a source closed-bar or trading authorization.
- Recorded public DNSE wire documentation discrepancy: endpoint parameter table names a required `X-Aux-Date` header, whereas official FAQ and authentication examples describe signed `Date`. Keep current FAQ-aligned signed Date unchanged pending independent vendor-authenticated Cloud read; do not guess at extra credentials or a signature change. Sources: https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/ ; https://developers.dnse.com.vn/docs/guide/intro/authentication/ ; https://developers.dnse.com.vn/docs/guide/faq/ .
- Change confined to the existing Draft PR23 scripts/tests/runbook, no new workflow, IAM, OAuth, secrets, Drive write, publisher, schedule, main merge, Signal Engine or trading. Run hosted CI at exact new head; it proves code/fixture consistency only, not real vendor data ingestion.


## §177 — DNSE owner-gated native multi-TF quarantine staging (13 Nov 2026; Draft only)
- Extended existing PR23 MFX-style cloud pipeline with a distinct manual-only `dnse-native-quarantine-stage` mode for source-native DNSE M5/M15/M30/H1/D1. This does **not** alter the `dnse-d1-quarantine-stage` mode, existing OAuth scope, run identity, source API host/signature, or Drive folder naming. H4 remains a hard error (not native).
- The existing workflow exposes an explicit new selection with TF. Still main-only workflow_dispatch, repo/owner identity and explicit approval, never scheduled or PR-triggered. Every native capture separately requires licensed market-data and retention/storage rights, a dedicated DNSE key/secret, stage-write owner acceptance, a first-attempt GitHub run and a TF-bounded request window.
- Each bounded attempt stores one **UNPUBLISHED** private candidate only when independently permitted: `MST_UNPUBLISHED_DNSE_NATIVE_<TF>_<RUN_ID>_1.json`. The old D1-only namespace `MST_UNPUBLISHED_DNSE_D1_<RUN_ID>_1.json` is unchanged. Raw provider-native arrays are retained in the app-owned private CHUNKS folder with source resolution/TF and receive time; all issue-first-known, venue-final-close, independent publisher-CAS and signals flags remain **false**.
- Same duplicate/ACK-unknown fail-closed path: pre-existing attempt blocks upload, private ownership and size/hash metadata checked, media read back twice with exact bytes and version, post-write exact-name census. Google Drive same-name listing is **not atomic CAS**; candidates remain unusable as authoritative Cache head.
- New targeted synthetic regression QA: all five TF mode paths and correct native filenames/resolutions, duplicated run refusal, storage-rights/owner gate denial, H4 and excessive M5 window refusal, rerun/wrong branch refusal, tamper/out-of-bounds denial. No real licensed API/Drive production write in CI; needs exact-commit hosted CI PASS.
- Draft-only, no merge, no secrets/IAM changes, no new scheduler, no publisher, no trades. Next real blocker remains owner-reviewed direct vendor Cloud entitlement and source/finality evidence.


## §178 — DNSE direct-helper rights boundary and strict wire resource guards (13 Nov 2026; Draft only)
- Closed a previously uncovered entrypoint: `_fetch_dnse_once` and its `read_dnse_once` wrapper now **enforce the same exact main-only/manual GitHub identity and provider market-data entitlement gate** as the top-level runner before any HTTP call. This protects against accidental direct imports calling DNSE outside licensed workflow context. No new OAuth/Secrets/Variables or changes to existing CI triggers.
- Enforced canonical **ASCII Unix-seconds** request boundaries (1–12 digits, positive, no leading zeros, not milliseconds, within Python-supported year-9999 limit) in both workflow input guard and request builder. Non-ASCII numeral strings, giant/millisecond epochs, wrong native types, unprintable/header-injection date values and oversized windows now fail with fixed non-sensitive codes rather than risk unbounded integer conversion or malformed provider requests.
- Preserved the official DNSE OHLCV type contract: source volume must be a nonnegative signed int64; large Python integer prices that overflow a float conversion are safely rejected instead of raising uncontrolled `OverflowError`. Strict `0 < HTTP response bytes <= 1,500,000` and HTTP exactly 200; known 302, 429, empty and malformed response bodies fail closed. Nonzero vendor `nextTime` remains **incomplete** and cannot be accepted, silently truncated or uploaded: paging/coverage requires a separate reviewed collector and licensed source proof.
- New synthetic transport-level tests exercise the **actual source helper**, including no HTTP when owner/source/branch/mode invalid, a valid native M5 fake GET with strictly aggregate receipt, ms/Unicode/overlong epochs, signed-request injection, unauthorized status/oversized response, unfinished vendor pagination and int overflow/int64 bounds. No live vendor call, Drive data write or Signal Engine promotion has been executed.
- Existing native M5/M15/M30/H1/D1 quarantine staging remains owner-gated and UNPUBLISHED only, H4 remains unproven, standalone VCBS API and immutable signed CAS/first-known remain OPEN. Cloud-only PR23 Draft and protected main governance unchanged. Only the exact new-head hosted Foundation CI PASS can mark these code changes QA-complete.

- **CI fixture correction at §178:** Initial hosted run 43431000228 correctly failed one case on both Python versions: the test used literal escaped backslash-r/backslash-n text instead of real CRLF, exposing fixture ambiguity rather than a live vendor issue. Added strict header literal-backslash rejection plus a separate actual-CRLF test (both must fail closed). Do not promote the original failing run as evidence; only subsequent exact-commit CI SUCCESS counts.
