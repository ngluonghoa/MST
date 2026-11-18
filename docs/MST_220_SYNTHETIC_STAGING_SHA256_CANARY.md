# MST §220 — Synthetic-only private Google Drive STAGING_ONLY canary

Date: 2026-11-18. Depends on §219 four-folder read-only census.

## Why / evidence boundary

The protected-main manual OAuth \`probe\` already **passed**:
https://github.com/ngluonghoa/MST/actions/runs/44247189161
This proves the GitHub OAuth principal can list the app-owned root,
not that a private Drive **file upload → GET media → SHA-256 readback**
works. The §219 PR #27 provides a separate GET-only four-folder census;
this §220 proposal is deliberately a **stacked, atomic PR based on #27**.

## Behavior

- Run only after separate owner review, CI PASS, sequential squash-only
  promotion of #27 then #220 to protected \`main\`.
- Workflow is \`MST OAuth synthetic STAGING_ONLY SHA256 canary - MANUAL PRIVATE WRITE\`.
- Manual \`confirm=WRITE_SYNTHETIC_STAGING_ONLY\`, main branch, original
  protected owner/repo IDs, workflow identity, **first run attempt only**.
- Uses existing \`MST_GDRIVE_OAUTH_CLIENT_ID\`,
  \`MST_GDRIVE_OAUTH_CLIENT_SECRET\`,
  \`MST_GDRIVE_OAUTH_REFRESH_TOKEN\` with the existing \`drive.file\` scope.
  No new credential, broad Drive access, service-account fallback, or consent.
- Calls §219 census first. Refuses write if app-owned root/child scope,
  private ownership, ACL, pagination or file identity is not trustworthy.
- Checks deterministic name is absent. Writes **one** JSON file with a
  fictional sentinel and no price, key, Watchlist row, OHLCV or account data,
  into OAuth-owned \`STAGING_ONLY\` only. No overwrite or automatic deletion.
  A unique first-attempt GitHub run ID avoids colliding with earlier canaries.
- Verifies post-upload Google Drive file ID, exact parent, MIME,
  app authorization, private ownership, byte length and SHA-256 of a
  fresh \`alt=media\` readback. Confirms post-write name lookup identifies
  exactly one file. Public GitHub logs contain only bytes+SHA receipt;
  never file/folder IDs, tokens, URLs, raw provider payloads or exception
  descriptions. A failed receipt may leave a quarantined synthetic file:
  do not blindly rerun the same run.
- No provider API request, retention-license assumption, publishing of
  \`CHUNKS\`/\`MANIFESTS\`, CAS/highwater, or signal/trade promotion.
- This is a narrow **Drive I/O proof**, NOT production Cache certification.

## Operator sequence

1. Owner reviews #27, checks its Foundation CI, then explicitly
   **squash-merges #27** using the repository's protected-main process.
2. Re-run/inspect §219 manual read-only four-folder census from main with
   \`confirm=RUN_READONLY_CENSUS\`. A PASS proves private folder scope
   and counts, not actual market data.
3. Update the stacked #220 PR base to main if needed, review its new files,
   check CI, then owner-approved squash-only merge.
4. In GitHub Actions choose the §220 manual synthetic canary workflow,
   branch \`main\`, \`confirm=WRITE_SYNTHETIC_STAGING_ONLY\`, run once.
5. Inspect for \`MST_220_SYNTHETIC_STAGING_WRITE_SHA256_READBACK_PASS\`,
   \`synthetic_only=true\`, \`market_cache_promoted=false\`,
   \`signals_and_trading_eligible=false\`. An empty or malformed proof is
   a blocker; do not promote signals or enable the hourly schedule.
6. Then separately implement and verify immutable licensed real-source
   CHUNKS, authoritative closed candles/first-known/rights, manifest
   readback, independent signed monotonic CAS, six TF+W1, sixteen original
   B/S detector parity, Stage08 UI A–I and release risk gates.

## Status as authored

PR #27: isolated 4-file GET-only census, CI PASS, owner review pending.
PR #220: synthetic canary source/test/workflow/docs under review,
no live Drive upload has happened merely by proposing these files.
The user-approved target **22 Nov 2026** remains conditional engineering
RC with NO_TRADE / UNVERIFIED until independent evidence is accepted.
