# MST §240 — Private unpublished Cloud CHUNK upload and two independent readbacks

P0-C / code-only integration stage / 2026-11-20. No live provider request or upload by this PR.

## Exact scope

Module: scripts/mst_private_chunk_readback240.py. A separately approved future manual GitHub Actions workflow would pass an authenticated OAuth drive.file session, private app-owned CHUNKS folder ID and a bounded source-envelope byte string. This PR does not wire a workflow, cron, source collector or market publisher. Offline tests use fictional data only.

Owner variables are owner declarations, not independent evidence of a vendor retention license, first-known event, source close or signed publication authority.

## Envelope and isolation

UTF-8 JSON bytes, 20-1,500,000 bytes; seven exact keys: schema=mst.cloud.unpublished_source_snapshot.v0.1, project=MST, provider=SSI|DNSE|VCBS, symbol=FPT|HPG|DCM, native_tf=M5|M15|M30|H1|D1, eligible_for_signals=false and nonempty raw_native dict/list. Duplicate JSON keys and nonfinite constants are denied. Preserve original bytes exactly; calculate raw SHA-256. No source-clock, adjustment, H4/W1 or usage-rights attestation is inferred.

Before any HTTP, guards require protected-main workflow_dispatch, exact repository/repo ID/owner ID, first run attempt, the **future** workflow ref mst-private-source-chunks-manual.yml@refs/heads/main, explicit STAGE_SOURCE_ONLY confirm, MST_PRIVATE_CHUNKS_WRITE_ACCEPTED=true, MST_SOURCE_RETENTION_RIGHTS_CONFIRMED=true, matching MST_<PROVIDER>_SOURCE_RIGHTS_CONFIRMED=true, provider/symbol/TF context, valid run ID and matching configured private folder. The future workflow does **not exist in this PR** and must be separately integrated and reviewed. Plain user-supplied environment variables are not independently signed authority.

## Protocol

1. GET CHUNKS folder metadata and confirm private, owned by OAuth user, app-authorized, unshared and untrashed.
2. Exact-name Drive files.list before upload. Fail on existing filename, truncated list, incompleteSearch, ambiguous or wrong-parent entry. Name contains provider/symbol/TF/run ID/content SHA-256.
3. One bounded Google Drive v3 uploadType=multipart using multipart/related JSON metadata/appProperties plus original bytes, explicitly UNPUBLISHED, false source closure/rights independent claims and signal_eligible=false.
4. Verify response ID and post-upload Drive metadata including owner/privacy/app authorization, size, MD5 and props. Perform **two separate server media GETs**, byte-for-byte and SHA-256 readback, with stable Drive metadata version after each.
5. Re-list exact name to detect duplicate, deletion or ambiguous result. Return internal private file ID/digest for later guarded manifest. public_receipt() contains no file IDs, content SHA, source prices or secrets and explicitly denies CAS, source rights, venue closure and promotion.

Google Drive permits duplicate filenames and does not guarantee atomic global CAS for a manifest pointer. A timeout, concurrent writer or failure may leave an orphan; never blind-retry, delete or overwrite. Two successful reads are NOT long-term immutability or source authenticity proof. Future independent signed monotonic CAS/highwater and versioned manifest custody are mandatory.

Official API references checked 2026-11-20:
- https://developers.google.com/workspace/drive/api/guides/manage-uploads
- https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create

## QA / future work

Pure fake-HTTP tests cover owner/rights denial before network, private folder requirement, ambiguous name census, upload failure, shared file, second read corruption, MD5 mismatch, version drift, malformed native JSON and receipt spoofing. They demonstrate code behavior only, not Google Drive live behavior.

Not complete: independently licensed SSI/DNSE/VCBS ingestion, hosted private CHUNKS upload, MANIFESTS, independent signed monotone highwater/CAS, historical first-known and venue close, H4/W1 aggregation, 1-hour scheduling, UI/golden/OOS and original 16 source-verified zones. All UNVERIFIED/NO_TRADE. November 22 remains a conditional engineering RC target, not production release.
