# MST Cache V2.1 — Synthetic JSON two-readback, immutability and fake CAS contract
**2026-11-11 / DRAFT only / Cloud CI only, NO real Drive writes.**

## Context and exact boundaries
MST OAuth project mst-github-actions has live GitHub Actions Drive probe PASS (run 43036386359) and manually approved app-folder bootstrap PASS (run 43037551110). The owner reports resetting repository write variable MST_OAUTH_BOOTSTRAP_ACCEPTED=false. That value cannot be independently read via the linked GitHub connector. The Drive root MST_OAUTH_CACHE_V1 was independently located in owner's My Drive and exactly four empty child folders STAGING_ONLY, CHUNKS, MANIFESTS and AUDIT were verified.

The above verified **Drive folder metadata** only. It did NOT verify market Cache JSON write/readback, highwater/CAS under actual Google Drive concurrency, independently signed revisions, existing owner-created Watchlist Sheet access, licensing for SSI/DNSE/VCBS, or any live production collector.

## This isolated Draft PR
Three additive files, no workflows or scheduling:
- scripts/mst_cache_v21_fake_two_read_contract.py
- tests/test_mst_cache_v21_fake_two_read_contract.py
- docs/MST_CACHE_V21_FAKE_TWO_READ_QA_20261111.md (this file)

The Python module is deliberately **in-memory only** and has no HTTP requests, no Google SDK, no OAuth secrets or environment accesses. It uses only Python standard-library JSON/SHA256/dataclasses.

**Permitted fixture:** strict fictional test object with exactly fixture_only=true, label starting FICTIONAL_, and bounded list of small integers. Never source/vendor OHLCV or actual stock symbols. The lab model:
1. Canonicalize strict JSON and calculate a content-addressed SHA-256 blob identifier.
2. Simulate immutable fake chunk placement (idempotent for identical bytes; reject same key with altered content).
3. Perform two independent fake reads of the chunk and verify the expected SHA-256. Reject mutation/replay between reads.
4. Simulate a generation-advancing manifest pointer with previous-manifest SHA chaining, stale pointer rejection, and an in-memory compare-and-swap revision check.
5. Recheck the fake pointer and return a sanitized receipt explicitly declaring zero Google Drive calls and writes, zero actual market data, no trusted external highwater, no demonstrated real Google CAS semantics, and NO PRODUCTION readiness.

**Important limits:** No guarantee that Google Drive files.update revision or ETag operations implement the exact CAS semantics simulated here. Even if this lab CI is green, real Drive conflict, staging/commit pointer and independent monotonic highwater testing remain required in a separately gated, authorized, isolated, owner-private synthetic-data workflow. The fake model may leave orphan content-addressed chunks after conflict, never deletes existing files, and should not be equated with a production atomic transaction.

## Acceptance evidence
44 fake-only unit cases covering no real-network boundaries, strict fictional schema, nonfinite rejection, duplicate/key collisions, two-read mutation detection, generation rollback, stale pointer, conflict, receipt fidelity, and replay. MST Foundation CI will run these on Python 3.11 and 3.12 on the isolated PR branch. CI success proves fake-only logic, not any Google Drive feature.

## Next externally approved stage — NOT implemented in this PR
Separate design-review and explicitly scoped owner approval are needed before adding a **new manual-only GitHub Actions staging workflow** with fake JSON payload writes to the existing app-owned STAGING_ONLY folder, two server readbacks, metadata/etag/revision evidence with no raw tokens or private IDs in logs, conflict/rollback cases, and a cleanup/retention strategy. Do not repurpose the current bootstrap writer for payload experiments. Keep MST_OAUTH_BOOTSTRAP_ACCEPTED false. The preexisting user-created Watchlist Sheet remains outside the app's automatic drive.file access; use Picker/explicit selection or approved app-owned migration only. Any actual source data caching requires separate licensing, official VN venue calendars/closed-bar semantics, SSI/DNSE/VCBS adapter proof, quota budget and production approval.

Protected MST main and merged PR21 remain unaffected by this Draft PR. Existing Draft PR8/17/18/19/20 remain independent.
