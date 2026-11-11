# MST — OAuth 2.0 Google Drive manual GitHub Actions proof
**2026-11-11. Draft only. Protected main unchanged. No market data or production Cache.**

## User-confirmed configuration; not independently verified
The owner reported that Google project mst-github-actions is configured with a separate MST OAuth client (scope drive.file), app published, authorization flow completed, and three GitHub repository Secrets populated: MST_GDRIVE_OAUTH_CLIENT_ID; MST_GDRIVE_OAUTH_CLIENT_SECRET; MST_GDRIVE_OAUTH_REFRESH_TOKEN. The linked GitHub tool cannot inspect secret values or prove credential validity. No secret values appear in this PR; never share them in ChatGPT, GitHub source or logs.

## Scope
This branch includes only one manual workflow, a dedicated Python Drive probe/bootstrap tool and 54 fake unit tests, plus this operator doc. MFX PR90 supplies the architecture precedent, not shared credentials. Separate MST WIF fallback PR17 remains Draft; do not merge PR8/17/18/19/20 as a shortcut. Never assume this OAuth app can open the preexisting owner-created private Watchlist Sheet simply because drive.file works.

## Two strictly separated workflow modes
- **probe** (default, no extra repository variable): approved manual workflow_dispatch on protected main only. The Python job exchanges a refresh token for a short-lived Google access token and sends a bounded Drive files.list metadata request for the app-created root named MST_OAUTH_CACHE_V1 at My Drive root; if a matching folder exists, validates files.get. No Drive writes, no content, no vendor APIs, no Cache or trading. PASS receipt: MST_OAUTH_DRIVE_FILE_READ_ONLY_PROBE_PASS. This validates one authenticated Google OAuth→Drive metadata call, not token longevity or file access beyond this scope.
- **bootstrap** (separate future owner-approved Cloud write): additionally requires exact GitHub repository variable MST_OAUTH_BOOTSTRAP_ACCEPTED=true. It creates or verifies a distinct app-created My Drive folder MST_OAUTH_CACHE_V1 and children STAGING_ONLY, CHUNKS, MANIFESTS and AUDIT, reads back metadata for each, and emits only sanitized receipt MST_OAUTH_APP_OWNED_FOLDERS_METADATA_READBACK_PASS with count 5. It does NOT write Cache market data. Set the variable back to false after a limited approved run. No automatic schedule.

## Security and failure
- Manual protected main only, GitHub immutable repository and owner IDs, exact workflow/ref, actions pinned by full SHA, no id-token, no pull_request_target, checkout credentials not persisted, Python dependencies pinned. Runtime independently checks exact GitHub environment context, mode and full OAuth trio before any Google call.
- Probe is read-only. It can list only app-scoped Drive metadata, not private user-created MST folders. A future Sheets read requires explicit app-file access and applicable Sheets API auth, plus independent trusted snapshot revision and highwater guarantees.
- OAuth external Testing-mode refresh tokens often expire after 7 days; owner reported publication but independent proof and periodic credential continuity still required.
- Safe errors omit raw tokens, file IDs and HTTP response bodies. Duplicate folder names, incomplete pagination, unexpected MIME and parent drift fail closed. A failed bootstrap may leave app-created folders; rerun checks unique names and does not delete data.
- No provider API authorization, data licensing, OHLCV, CAS, live trading or scheduled refresh is implied.

## Ordered acceptance, only with separate scoped owner approval
1. Review isolated PR code/CI and explicitly authorize protected main merge for this narrow manual-only OAuth workflow.
2. Go to GitHub Actions, select MST OAuth My Drive Folder Bootstrap - MANUAL NO MARKET DATA and mode probe on main; run manually. Verify exact PASS text, no POST, no folder creation, no prices, no secrets logged.
3. Only if separately approved, enable MST_OAUTH_BOOTSTRAP_ACCEPTED=true under GitHub Repository Variables and select mode bootstrap for exactly one manual run; expect 5 app-owned folders; immediately reset variable to false.
4. Independently verify owner Drive UI and then separately design exact authorization to preexisting Watchlist Sheet, safe synthetic Cache and vendor entitlement proof before any actual source Cache ingestion.

NO deployment, GitHub Secrets read, actual Google OAuth token exchange, real Google Drive call or user Drive modification has happened merely by creating this Draft PR.
