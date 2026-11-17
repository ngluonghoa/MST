# MST §217 — GitHub OAuth → Google Drive read-only regression and recovery

Observed: 2026-11-18 00:35 ICT (2026-11-17 17:35 UTC).
Status: P0-C BLOCKED; no Cloud Cache production readiness.
Host evidence: https://github.com/ngluonghoa/MST/actions/runs/43036386359 attempt 2 on protected main SHA e4b162c57f10a47de62809188389bdc35d1261f5.
Safety: This reran the original mode=probe, which reads Drive metadata only. No bootstrap, Drive writes, stock-source calls, cron, orders or main mutation.

## Observed outcome, not a guessed root cause

On 2026-11-11, original run 43036386359 mode=probe succeeded but app_owned_cache_root_discovered=false. Later 43037503159 and 43037551110 mode=bootstrap each succeeded: five app-owned folder metadata readbacks, drive_cache_data_written=false.

Rerunning the original probe job on 2026-11-18 ICT (attempt 2) passed the GitHub secret-presence check and executed mode=probe, but exited with MST_OAUTH_DRIVE_REQUEST_FAILED_CLOSED. The old main source maps unexpected AuthorizedSession.get or JSON exceptions to this generic code. Therefore it does NOT prove invalid_grant, token revocation, malformed OAuth client, TLS/network failure, or a Drive ACL issue. The actual reason remains UNKNOWN.

Separately connected ChatGPT Google Drive sees MST_OAUTH_CACHE_V1 with four child folders AUDIT / MANIFESTS / CHUNKS / STAGING_ONLY, all with zero visible files at audit time. The GitHub OAuth principal and this Drive connector may have distinct scopes and visibility. Zero visible files here does NOT prove GitHub OAuth sees an empty folder. No GitHub execution was found for the separately drafted mst-mfx-style-appowned-readonly.yml source workflow, which is not on protected main.

## Change prepared only in Draft PR #23

The existing scripts/mst_oauth_manual_drive_bootstrap.py now returns fixed diagnostic codes:
- Structured Google-auth RefreshError invalid_grant => MST_217_OAUTH_INVALID_GRANT_REAUTHORIZE_REQUIRED.
- Structured invalid_client => MST_217_OAUTH_INVALID_CLIENT_CONFIGURATION.
- Structured unauthorized_client => MST_217_OAUTH_UNAUTHORIZED_CLIENT.
- Other or malformed RefreshError => MST_217_OAUTH_REFRESH_REJECTED_UNCLASSIFIED.
- Google-auth TransportError => MST_217_OAUTH_TRANSPORT_ERROR.
- Bounded requests/urllib3 network and TLS errors => MST_217_OAUTH_NETWORK_OR_TLS_ERROR.
- Google Drive HTTP 401, 403, 429, 408 or common 5xx => fixed HTTP-only code.
- Unknown exceptions => old generic fail-closed code.

Only allowlisted structured error types/codes are inspected. No provider body, exception message, traceback, URL, refresh token, client secret or OAuth error_description is printed. No retry, side effect, extra OAuth scopes, market source ingest, ACL changes or trade promotion. Ten new fictional synthetic tests validate redaction, invalid/malformed and unhashable error objects, HTTP and transport branches. This improved classifier is NOT on main until an explicitly reviewed and approved controlled squash-only merge.

## Operator recovery checklist

1. The old main workflow is GitHub Actions / MST OAuth My Drive Folder Bootstrap - MANUAL NO MARKET DATA, input mode=probe. This has already been rerun and failed. Do not repeatedly rerun without a changed condition. Bootstrap mode is NOT needed; it may create folders.
2. Check Google Cloud project mst-github-actions, Google Auth Platform / Audience and Clients: confirm the actual publishing status, the OAuth client used to mint the token and Drive scope https://www.googleapis.com/auth/drive.file. Do not put OAuth identifiers or secrets in issues, pull requests, chat, Drive QA or logs.
3. If invalid_grant becomes independently confirmed, validate refresh token expiration/revocation and client mismatch. Official Google OAuth guidance: https://developers.google.com/identity/protocols/oauth2 . An External/Testing project may issue a seven-day refresh token for non-identity scopes. Earlier MST documents said the app was Published: do NOT assert it switched back to Testing without observing that change.
4. If renewal is required, authorize the same OAuth client with the existing drive.file scope through approved Google Cloud/OAuth Playground flow. Update only repository GitHub Actions secret MST_GDRIVE_OAUTH_REFRESH_TOKEN (or appropriate matching client credentials when proven wrong) through GitHub Settings, never paste values in ChatGPT. Re-run main workflow in probe mode and confirm a NEW successful host log.
5. Once the current GitHub OAuth connection passes, a separately reviewed, owner-controlled promotion of the draft source-readonly workflow is required before the §216 four-child metadata census can execute from main. Do NOT bypass main/owner gates with secrets in pull_request or branch-push CI.
6. Even a successful census and nonempty CHUNKS/MANIFESTS do not prove source licensing, authoritative candle closure, first-known, independent signed monotonic CAS, durable immutable chunk/manifest readback, full 16 zone parity, approved UI-1.0 or actual trade eligibility.

Release target 2026-11-22 is CONDITIONAL engineering RC. P0-C remains NO-GO until separately attested real cloud-side evidence exists. Preserve PR23 Draft and protected main without automatic merges or trading.
