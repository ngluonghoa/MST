# MST Cache V2.1 — Live Google Drive fictional STAGING_ONLY JSON proof
**2026-11-11. DRAFT / approval-required / never scheduled / no market data.**

## Existing accepted state
- Authenticated GitHub Actions → Google Drive files.list metadata proved in run 43036386359.
- Isolated root folder MST_OAUTH_CACHE_V1 and four children created or verified via GitHub owner-triggered run 43037551110; independent owner Drive connector readback verified root + STAGING_ONLY, CHUNKS, MANIFESTS, AUDIT.
- Owner confirmed repository variable MST_OAUTH_BOOTSTRAP_ACCEPTED set to false (cannot independently read variable value through GitHub connector).
- PR22 https://github.com/ngluonghoa/MST/pull/22 covers *offline* fake JSON SHA-256/two-read/in-memory-CAS contract and does not implement Google Drive CAS.

## Separate live-API workflow proposed in this Draft PR
Files: one isolated Python script, a strictly manual GitHub workflow, fake HTTP tests and this document; no modifications to inherited market source code, OAuth Secrets or production Cache.

Workflow name: MST Cache V2.1 Fictional JSON Staging - MANUAL ONLY.
- Trigger: workflow_dispatch **only**, exact main ref + repository/owner numeric identity, no schedule, no PR events, no Github token write permissions, checkout never persists GitHub credentials.
- Default mode: **probe**, authenticates with three MST-specific GitHub OAuth Secrets, lists/reads metadata for existing app-owned MST_OAUTH_CACHE_V1/STAGING_ONLY folders, does **zero writes**. Requires exact parent/name/MIME checks.
- Explicit mode: **synthetic-write**. In addition to the same safety guards, the repository variable MST_CACHE_V21_STAGING_WRITE_ACCEPTED must be **exactly true**. Prior MST_OAUTH_BOOTSTRAP_ACCEPTED must NOT equal true. This is a NEW independent write gate, and MUST NOT be set without explicit owner permission.
- On synthetic-write: one uniquely named application-created JSON file under existing STAGING_ONLY named MST_FAKE_V21_RUN_<GitHub run ID>_<attempt>.json. The hard-coded data are entirely fictional: fixture_only true, label FICTIONAL_INTEGRITY_PROBE, samples [-2,0,3]; no stock symbols, prices or provider identifiers. No existing file overwrites, updates, deletes, public sharing or cloud product additions.
- Uses the documented Drive v3 POST /upload/drive/v3/files?uploadType=multipart for a single new file, with parents constrained to the verified app-owned STAGING_ONLY ID and explicit appProperties fixture marker + SHA256. GET metadata checks id/name/parent/MIME/size/MD5/appProperties. Two distinct GET files/{id}?alt=media calls independently validate exact SHA256 and byte equality. Re-GET metadata after both reads.
- An exact same-run retry checks for one previously-created file and verifies its metadata and two content reads rather than creating a duplicate. Ambiguous list or pagination, missing app root or stage, invalid parent, inconsistent content or non-200 Drive response: fail closed. User-facing GitHub log receipt contains **no file IDs**, credential values, Drive response bodies, uploaded bytes, raw HTTP errors, personal market data or Google tokens.
- The receipt status MST_STAGING_FICTIONAL_JSON_UPLOAD_TWO_REAL_READS_PASS proves only a **single limited app-owned fictional JSON upload** and two content readbacks during that one run. It explicitly leaves CAS, highwater, Watchlist, market Cache, OHLCV, source licensing and production as false/unproven.
- Failed write might leave an orphan **fictional JSON file** in STAGING_ONLY; do not auto-delete or widen Drive authorization. A single small retained staging test artifact is acceptable only if separately authorized by the owner.

## Safe acceptance order
1. Review exactly four new files, fake-only CI, and keep PR DRAFT. No main merge or live workflow execution merely from design approval.
2. After specific owner approval for main promotion, merge only this focused PR and run the workflow on main with mode **probe** first. Confirm MST_STAGING_EXISTING_FOLDER_READ_ONLY_PASS and no Drive writes.
3. Only after a SECOND specific permission to create one harmless 200-byte-class JSON file in STAGING_ONLY, set GitHub Repository Variable MST_CACHE_V21_STAGING_WRITE_ACCEPTED=true, select mode synthetic-write exactly once, and read sanitized PASS receipt + independent Drive content verification if needed. Set this variable back to false immediately.
4. Never reset MST_OAUTH_BOOTSTRAP_ACCEPTED to true as a shortcut; it must remain false.
5. Keep real provider ingestion, production Cache V2.1, schedules, Google Sheets Watchlist integration and trusted CAS/highwater as independent NO-GO gates.

## Technical limitations explicitly not solved
Drive v3 native file metadata version is not by itself a proven atomic compare-and-swap transaction or rollback-resistant trusted generation ledger. The workflow does not attempt to simulate or claim transactional commit; it does not populate CHUNKS/MANIFESTS/AUDIT or move any committed pointers. Parallel writers or Drive conflict tests and recovery must be separately built and approved. SHA256 and Google md5Checksum provide content-integrity evidence only, not authorization or antirollback signatures. A one-off successful Refresh Token exchange does not prove future credentials remain valid. Scope remains only OAuth drive.file for app-created files; existing private owner-created Watchlist Google Sheet remains outside automatic access.

Google official API references:
- https://developers.google.com/workspace/drive/api/guides/manage-uploads
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get
