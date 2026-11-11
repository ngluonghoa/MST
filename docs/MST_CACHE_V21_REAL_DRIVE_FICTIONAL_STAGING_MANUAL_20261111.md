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

## 2026-11-11 hardening review before any protected-main promotion
Google Drive official v3 API references confirm POST /upload/drive/v3/files?uploadType=multipart with metadata first and media second, plus GET files/{fileId}?alt=media for raw JSON bytes; drive.file supports both operations. The v3 File resource exposes read-only shared, ownedByMe, isAppAuthorized, md5Checksum and version metadata. The create API supports ignoreDefaultVisibility=true to override domain default publication, though explicit inherited parent permissions still matter.

**New fail-closed checks in this PR:**
- Require both the root app cache folder and STAGING_ONLY folder to be private (shared=false), owned by the same Google account (ownedByMe=true), and authorized to the same OAuth app (isAppAuthorized=true) before any write. Require the same values for the created or reused fictional JSON file.
- files.create explicitly requests ignoreDefaultVisibility=true. This is not a substitute for the parent share/ownership checks; it reduces accidental domain-default publication risk.
- Each raw media response is consumed in bounded 1024-byte chunks with a strict 4096-byte ceiling during streaming; the code does not join an arbitrarily long response before rejecting it. It closes the response on every success or failure path.
- Eleven additional fake HTTP cases cover shared root/child/file, non-owned and non-app-authorized storage, default visibility override, oversized content with absent Content-Length, and read-only handling under changed sharing.

The owner-linked Drive connector independently reported shared=false for root MST_OAUTH_CACHE_V1 and child STAGING_ONLY on 2026-11-11, but the GitHub runner's own OAuth ownedByMe and isAppAuthorized response fields have not been observed live. A future real probe must pass the stricter preflight on main before a single fictional JSON write is considered. A false negative for missing metadata must fail closed, not silently bypass these checks.

Google docs:
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create

## 2026-11-12 — Drive server-version stability fence, synthetic-only QA

The Google Drive v3 File resource `version` is an output-only decimal int64 string that monotonically increases on any server-side file change, including metadata changes not otherwise visible to this test. This patch requires a present, positive, canonical decimal file version on the metadata read immediately before the two `alt=media` reads and again on the final metadata read. The values must be **equal**. A missing/malformed version or intervening revision fails closed with a constant sanitized error; IDs, versions, raw HTTP bodies and credentials are never logged.

Three additional **in-memory fake** negative tests cover: (1) file version changing between two successful identical-content media reads and final metadata, (2) absent version, and (3) malformed version. No real Drive request, market data or OAuth token is used by these tests. Existing OAuth Drive folder bootstrap, source files, and production gates are unchanged.

**Boundary:** version equality is only a single-run drift-detection check. It does **not** provide a server-enforced conditional write, atomic compare-and-swap, multiwriter transaction, immutable object lock, independent signer or trusted anti-rollback floor; a rollback or concurrent update outside the observed window may evade it. PR23 remains Draft and unmerged. The default manual probe remains read-only. The separate owner-approved gate for one fictional STAGING_ONLY JSON write remains required; no new write permission, cron or production Cache is authorized here.

Official field semantics: https://developers.google.com/workspace/drive/api/reference/rest/v3/files

## 2026-11-12 — Drive list completeness and same-name MIME collision guard

A further pre-live review of `files.list` found two independent ambiguity paths. (1) A list response may contain `incompleteSearch=true` when Drive cannot search all selected corpora; this is not evidence of file absence or uniqueness even when the `files` array is empty. (2) Filtering by expected `mimeType` inside the query hid an otherwise visible same-name file with a conflicting MIME type, allowing an unintended additional file with the same name. Per Google Drive v3 documentation, `nextPageToken` and `incompleteSearch` are distinct list-completeness signals.

The runner now requests the `incompleteSearch` field and rejects any value other than an omitted or explicit JSON false flag. It performs **name-only** lookup constrained to the exact verified folder (and `trashed=false`), then requires a single result with the exact expected MIME type, parent and name before accepting it. If two files with the name exist, a search is incomplete, or the returned file has a different MIME, the runner fails closed without invoking `files.create`. Three fake-only regression tests cover a positive incomplete-search flag, an invalid string flag, and a visible conflicting-MIME file with exactly the expected name; the last verifies the query no longer filters MIME. No real data, credentials, OAuth token or GitHub main scope changed.

This detects **visible** name conflicts only within the authorized `drive.file` scope. It cannot establish global Google Drive namespace uniqueness, transactional atomicity, strong read consistency or trust under an independently malicious Google response. A concurrent creator after the search could still race the upload; a genuine server-side CAS/independent highwater solution is separately required for market Cache V2.1. This Draft PR remains unmerged, with read-only probe default and separate scoped approval before any fictional staging upload.

Google official reference: https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list ; https://developers.google.com/workspace/drive/api/guides/search-files

## 2026-11-12 — GitHub Actions rerun fence and post-media folder context readback

GitHub documentation specifies that `GITHUB_RUN_ID` is stable across a workflow rerun and `GITHUB_RUN_ATTEMPT` increments. This prototype's filename includes **both** values. Previously, a `synthetic-write` rerun under a still-enabled repository write gate could therefore use a *different filename* and create another fictional staging file instead of verifying the first attempt. In this Draft, the Python runtime now refuses any `synthetic-write` when `GITHUB_RUN_ATTEMPT` is not **exactly `1`**, even if the write gate is still `true`; `probe` can still be rerun without writes. An interrupted first upload may leave one orphan fictional JSON and must be inspected by the owner rather than auto-repaired by GitHub rerun. Same-process re-invocation with the exact same attempt/name still verifies existing bytes (best-effort; not atomic).

After two bounded, independent media-content GETs and the final matching metadata-version readback, the writer now re-reads the *full* root-to-stage folder chain and requires the same STAGING_ONLY ID, parent relationship, `shared=false`, `ownedByMe=true`, `isAppAuthorized=true`, exact names/MIME and untrashed state before emitting a success receipt. If the folder was reparented, shared, replaced or access was revoked after the preflight, it **fails closed**. This is an additional postcondition, not a server-enforced permission lock: a prior shared interval, a race outside the two checks or a file left behind after an error cannot be undone by these checks.

Seven entirely synthetic new negative/positive tests exercise write rerun denial, read-only probe rerun, late root privacy drift, late stage privacy drift, app authorization revocation, reparenting and a successful five-list metadata verification sequence. No real OAuth token, Google Drive file, provider data, new workflow privilege or secret is used by CI. Owner approvals are still distinct: review+approve PR23 merge, then default **probe** on protected main, then a separate one-file synthetic-write approval and immediate variable reset.

**Important residual single-use gap:** two distinct GitHub `workflow_dispatch` runs receive different run IDs, so if the owner leaves `MST_CACHE_V21_STAGING_WRITE_ACCEPTED=true`, separate original attempts can each create one file. This limited guard blocks *reruns*, not multiple distinct dispatches or globally coordinated concurrent writers. No claim of exactly-once, Drive CAS, signed highwater or production-safe Cache is made.

References: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts ; https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs

## 2026-11-12 — Final same-name identity and uniqueness revalidation

A pre-upload `files.list` name check cannot prove the same name still identifies one and only one original file by the end of a two-read proof. Another authorized actor could create a duplicate, rename/reparent the original, change its MIME, or replace it with a same-name different-ID object after the initial search. The existing two `alt=media` reads and matching `files.get` metadata/version readback validate **the original ID's** bytes but could still emit a PASS while the latest folder name lookup had become ambiguous.

PR23 now performs a **final independent exact-name and parent-scoped** `files.list` after verifying the root-to-STAGING_ONLY private folder chain. The final result must be complete, unique, have the same expected JSON MIME/parent/name/untrashed status, and identify **the exact same original Google Drive file ID**. Zero results, duplicates, newly wrong MIME/parent or a swapped ID fail closed with sanitized constant errors; no automatic rename, deletion, recovery, overwrite or new cloud authorization is performed. Five additional pure in-memory regressions cover all five negative cases. The existing successful fake-HTTP case now confirms six total list calls (folder preflight two, file preflight one, folder postcondition two, exact-name postcondition one).

**Limits:** This is a second observational uniqueness check within the app's `drive.file` visible scope. It does not make Google Drive names globally unique or enforce a transactional lock. A rename/create/move immediately after the final read may still occur, multiple distinct dispatches can still create separate named fixtures, and Google Drive atomic CAS/signed anti-rollback highwater remain unproven. No production rights, provider ingestion, Watchlist integration or real Drive files are involved until the distinct owner approvals.

## 2026-11-12 — Whole-staging-folder census: block sequential fresh-dispatch duplicates

GitHub Actions rerun blocking (`GITHUB_RUN_ATTEMPT == 1`) does **not** stop two separately dispatched first attempts while the owner repository variable `MST_CACHE_V21_STAGING_WRITE_ACCEPTED=true` remains enabled. Previously, each run checked only for its own generated filename, so a second run with a new `GITHUB_RUN_ID` could see “not found” and create another fictional JSON. No global live write or incident is claimed; this is a scenario derived from the code's name-filtered behavior.

The isolated Draft writer now uses an **entire-folder census** for the exact app-owned, private STAGING_ONLY folder before it considers a fictional JSON upload, instead of filtering to the current run's name. The only accepted results are: (a) **zero visible untrashed objects**, permitting at most one owner-authorized fictional upload, or (b) **one visible matching JSON with the exact same current run/attempt name**, which must still pass full metadata, SHA256/MD5, server-version and two content-read checks. Any previous distinct run's JSON, unrelated file, two objects, incomplete search or pagination fails closed; no overwrite, delete, automatic cleanup or attempt to migrate existing files. The final post-read revalidation repeats the full-folder census, so a late unrelated object also prevents a success receipt.

Five additional **fake-only** regression tests cover a prior distinct dispatch, unrelated non-JSON staging file, correct same-run file plus a second object, late unrelated object and assertions that both staging queries omit name/MIME filters. Existing same-name idempotent in-process retry tests remain. The focused staging test set grows from 73 to **78**. All external HTTP is faked in CI and no OAuth secrets or real Google Drive write is used.

This is a **best-effort sequential single-visible-artifact guard**, not true exactly-once authorization. It cannot see objects outside the OAuth `drive.file` access boundary, cannot stop two independent concurrent writers that both observe an empty folder before either creates, cannot prevent visibility mutations immediately after the final read, and does not provide server-enforced CAS, immutable audit or independent anti-rollback signing. GitHub Actions concurrency serializes this *one workflow* within a repository but not every possible writer or another process. The owner must still approve main merge separately, execute default metadata-only `probe`, separately authorize **one** harmless JSON creation, and promptly reset the write variable to false. In the event of an ambiguous upload, inspect the staging folder manually rather than blindly retrying or deleting artifacts. Production Cache and provider data remain NO-GO.
