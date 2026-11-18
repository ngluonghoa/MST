# MST §219 — GitHub OAuth app-owned Cache metadata census (manual, read-only)

## Ground truth before this PR

2026-11-18 ~12:52 ICT GitHub main \`mode=probe\`:
https://github.com/ngluonghoa/MST/actions/runs/44247189161
**SUCCESS** with \`actual_google_drive_metadata_read=true\`,
\`app_owned_cache_root_discovered=true\`,
\`google_drive_write_performed=false\`,
\`market_provider_called=false\`.
This confirms real GitHub OAuth can see the top-level app-owned root.
It does **not** verify child files, any persisted market Cache, token
permanence, provider rights, or production signal readiness.

## Minimal separate PR

This atomic implementation starts from main, not the 87-file Draft PR #23.
It intentionally does not copy the combined SSI/DNSE source/quarantine workflow
from PR #23, which has unrelated data entitlements, staging and security gates.

- \`scripts/mst_oauth_cache_census219.py\`: existing GitHub OAuth trio, exact
  five-folder identity/ownership/private-scope checks, four metadata-only child
  file inventories with bounds (max six pages of at most 100 items each),
  duplicate/file-parent/app-scope/visibility checks, fixed failure codes.
- \`tests/test_mst_oauth_cache_census219.py\`: synthetic-only malicious/invalid
  folder, file, pagination and owner-gate tests, no external calls.
- \`.github/workflows/mst-oauth-cache-census-manual.yml\`: dispatch-only,
  protected-main-only, explicitly select \`RUN_READONLY_CENSUS\`; Drive metadata
  GETs only, no timer, PR secrets, push, market APIs or Drive writers.

The JSON receipt reports counts only, no OAuth credentials, Drive identifiers,
filenames, URLs, market rows or source contents. An entirely empty four-folder
census reports \`BOOTSTRAPPED_FOLDERS_EMPTY\`; any content reports
\`PRIVATE_FILES_PRESENT_UNVERIFIED\`. Both retain
\`production_cache_ready=false\`,
\`independent_signed_highwater_attested=false\` and
\`signals_and_trading_eligible=false\`.

## Operator procedure, AFTER approved review + squash-only merge

1. Verify the PR's engineering CI passed and reconcile duplicate §216 logic
   in Draft PR #23 before any future integration. Do not force-push main.
2. Under GitHub Actions on protected \`main\`, choose workflow
   \`MST GitHub OAuth app-owned Cache census - MANUAL READ-ONLY\`.
3. Select \`confirm=RUN_READONLY_CENSUS\`; invoke once.
4. Check the workflow conclusion and the *public count-only receipt*.
   \`MST_219_GITHUB_OAUTH_CACHE_CENSUS_PASS\` is metadata scope evidence only.
   Never paste GitHub secrets or Drive private file IDs.
5. If PASS+EMPTY, next separately reviewed step is a rights-scoped immutable
   unpublished source CHUNK write and exact SHA/readback evidence using
   protected GitHub OAuth, with provider entitlement separately attested.
   If nonempty, do not assume it is valid market data: audit manifest
   identity, source rights, SHA/first-known, version and signed CAS gates.

This PR does **not** initiate market data acquisition, write a single Google
Drive Cache file, activate 1-hour schedule, merge PR #23/#26, or enable trading.
22 November 2026 is a conditional engineering RC goal only.
