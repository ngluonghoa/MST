# MST — OAuth 2.0 / Google Drive drive.file Design and Synthetic Readiness
**Date:** 2026-11-11. **Status:** DESIGN ACCEPTED; **DRAFT QA ONLY**, not authenticated, deployed or production.

## User-approved choice
Use a new, MST-specific Google OAuth 2.0 client and personal Google Drive My Drive as the preferred Cloud identity route. Do **not** require Google Cloud Billing merely to build the OAuth consent/client flow. Keep M4 Google WIF metadata-only Draft PR #17 as a **dormant fallback** (NOT merge/close/delete) for future use. This change is allowed as additive, isolated draft research; protected main and all release/IAM/ACL/Secrets changes still require explicit authorization.

Source of architectural precedent: **MFX merged PR #90** and its public repository file docs/MFX_GMAIL_OAUTH_ACTIONS_SETUP.md. MFX keeps an application-created My Drive subtree via the OAuth scope https://www.googleapis.com/auth/drive.file, not a general Drive-wide scope. IMPORTANT: code merged in MFX does not itself prove unrestricted production-ready historical rights, refresh-token durability, or all-source cache/market access. No secrets or live MFX tokens are copied to MST.

## The Cloud-only high-level flow
1. MST-specific OAuth consent app in its own Google Cloud project (user selected project name mst-github-actions; actual credentials and app publication state NOT verified). Auth code and refresh token, **never** exchanged over ChatGPT or committed to GitHub.
2. GitHub Secrets **names** for a complete credential trio only:
   - MST_GDRIVE_OAUTH_CLIENT_ID
   - MST_GDRIVE_OAUTH_CLIENT_SECRET
   - MST_GDRIVE_OAUTH_REFRESH_TOKEN

   A complete trio is required, with NO silent fallback to Service Account JSON. All values remain hidden in GitHub Secrets and are NOT printed in logs. New MST values, not MFX credentials. Config values and secrets are *not* set by this draft.
3. After later owner-approved deployment only, one main-only manual bootstrap will use the user-consented app scope **drive.file** to create/check an isolated, app-created My Drive root named MST_OAUTH_CACHE_V1 with children STAGING_ONLY, CHUNKS, MANIFESTS and AUDIT. Each folder must be independently read back and exactly validated with bounded API calls and idempotent no-duplicate rules. No market data or synthetic write is permitted by the first metadata-only stage. Folder IDs from successful live creation are recorded only in designated MST variables (not code). Cache storage retention policy remains unapproved.
4. The separately existing owner-created **MST Dynamic Watchlist Google Sheet** in MST private folder is **not automatically accessible** to an app with only drive.file. Do not assume access just because the same Gmail user owns it. Before reading the Sheet from a GitHub runner, choose and verify one separately authorized path: allow user-selecting that exact file in a secure Google Picker flow using the **same OAuth app**, or create an app-owned replacement Watchlist and do a reviewed migration retaining original private controls. Never request all-Drive scope to bypass this restriction silently. The new app-owned folder alone does NOT prove existing Sheet access.
5. Any Google Sheets read also requires verified applicable Sheets API scope/capabilities, consistent revision snapshot and independent monotonic highwater; a single editable Sheet cell is NOT a trusted signer. A Drive metadata read is not Sheets values-read, and bootstrap receipt is not Cache V2.1 acceptance.
6. Existing Market Scanner manual-only Candidate Inbox, Dynamic Watchlist scheduled-only selected-symbol scope, Swing Trading 1:1 parity and the owner-private MST folder are all independent. Scanner candidates **never automatically enroll** in Watchlist. PR #8, WIF PR #17, Scanner PR #18 and Dynamic Watchlist PR #19 remain Draft/untouched by this new PR.

## OAuth publishing and security acceptance
- Google OAuth External in **Testing** typically issues refresh tokens expiring after **7 days** for nonbasic scopes. Synthetic testing may continue, but do not claim uninterrupted Cloud refresh. Select and verify publishing status, consent/verification implications, scopes and refresh rotation with the owner, and prove continuity with two independent authenticated GitHub runs before scheduling. An externally configured production status value is *not*, on its own, proof of token lifetime.
- Never collect user passwords. Store Client Secret and Refresh Token only in GitHub Actions Secrets for MST; do not use GitHub repo variables, public issues, PR comments or source code for their values.
- Prefer action SHA pinning, repo numeric IDs, main/manual-only checks, least-privilege job permissions (contents:read, no id-token since OAuth not WIF), no pull_request_target, fixed allowlisted folders, bounded retry/rate limit, zero market or order/trading calls.
- Future OAuth bootstrap WRITE to a new app-owned folder is an explicit owner-approved Cloud side effect; do not perform it based on the existence of this DRAFT. This prototype deliberately never imports Google libraries nor sends HTTP calls.

## Implemented NOW — safe contract lab only
- scripts/mst_oauth_drivefile_synthetic_contract.py: stdlib-only validation of *fictional* signed-context placeholders, complete credential **presence booleans** (never secrets), no WIF fallback, drive.file-only scope, forbidden provider/cache side effects, five app-owned fake folder records and safe aggregate readback receipt. The invented appOwned attribute is synthetic lab metadata, **NOT an actual Google Drive API response field**; future real code must use independently verifiable creation scope/identity evidence.
- tests/test_mst_oauth_drivefile_synthetic_contract.py: 54 positive/negative fictional tests including repo/ref/event/workflow guard, missing Secrets, wrong OAuth scopes, folder identity/parents/duplicates, no broad Drive or Watchlist permission, no secrets in receipt, no real Cloud/vendor code paths.
- This document. NO new GitHub Actions workflow, IAM, OAuth client, Google API authentication, GitHub Secret, private Drive folder, real data Cache, market API use, or main merge.

## Future phases, one gate at a time
1. **Owner Cloud configuration:** verify MST project and OAuth consent screen/client, explicitly confirm drive.file, OAuth publishing mode, and credentials stored directly in GitHub Secrets by owner (never shared in chat).
2. **Independent manual-only bootstrap PR** on main after code review and explicit permission, app-created root folder, exact metadata readback; no existing Watchlist Sheet access inference.
3. **Synthetic private Drive two-write/readback** with version/hash, monotonic signer and controlled quota, only after separately authorized limited synthetic Drive writes and secrets.
4. **Private Watchlist read** exact selected Sheet with explicit app access, values revision consistency and fail-closed snapshot; no scheduled market refresh.
5. **Provider license + source provenance + venue close calendars + real CAS** before permitting actual source Cache V2.1 or scheduling. No market trading module release implied.

A Google Cloud project being created, enabled API, or successful synthetic CI is not evidence of authenticated Google OAuth GitHub runner access, connected personal Drive file scope, vendor retention licensing or a deployable Cache.
