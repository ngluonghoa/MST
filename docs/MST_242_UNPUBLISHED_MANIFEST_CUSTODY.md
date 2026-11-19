# MST §242 — private UNPUBLISHED source MANIFESTS custody

2026-11-20 ICT. This is an **isolated library + fictional offline CI**, not an enabled workflow, Cache head, scanner or broker system.

## What the module actually checks

- A trusted caller supplies a private two-read CHUNK receipt from §240, the same protected-main first-attempt owner/retention gate, **independent additional** `MST_PRIVATE_MANIFEST_WRITE_ACCEPTED=true`, and private app-owned CHUNKS/MANIFESTS folder IDs. The current §241 SSI manual workflow **does not call this library** and does not supply the manifest gate. No real MANIFESTS upload is performed by CI.
- Before writing any manifest, `scripts/mst_private_unpublished_manifest242.py` fetches Drive metadata for CHUNKS, MANIFESTS, and their common parent MST_OAUTH_CACHE_V1. It requires owned/unshared/app-authorized parents, exact private directory identities, no folder substitution.
- Independently re-reads the existing source CHUNK. Rejects mismatched SHA-256, length, exact content-addressed name, provider/symbol/timeframe/run, metadata MD5, private owner, source appProperties, or an extra same-name file. The original source envelope must pass §240 validation again, and two additional source-media reads with unchanged metadata version are required. A `PrivateUnpublishedChunk` dataclass alone is **not** integrity proof.
- Creates a deterministic bounded **private** JSON manifest containing only CHUNK identity/digest/byte count, source scope, UNPUBLISHED and all unverified flags. No raw source prices, OAuth secrets, bearer tokens or historical series are embedded. It intentionally has **no generation, CAS pointer, active highwater, production-ready close or price-basis assertions**.
- Uploads a new content-addressed MANIFESTS JSON with Google Drive v3 `multipart/related`, no overwrite. Checks private metadata, MD5, version, two independent full-media SHA-256 reads, unique exact name, and source-CHUNK postupload identity. Returns a private internal receipt; public receipt omits file IDs and digests.
- No retries, deletions, transaction rollback or promotions; any upload error may leave a private orphan. Google Drive can contain duplicate filenames, and a successful two-read candidate remains **not atomically published or protected against later mutation**.

## Real blockers, not papered over

Independent SSI/DNSE/VCBS historical retrieval/retention authorization and GitHub Actions secret provisioning were **not** inspected or confirmed in this PR. The source first-known clock, venue session-specific finality, corporate-action basis, six-native-timeframe/full W1 coverage and independent signed monotone CAS/highwater remain pending.

Without an independently authenticated private publisher that atomically enforces the signed highwater, a MANIFESTS file is only a **candidate**, never a trading Cache head. Keep 16 detector zones UNVERIFIED/NO_TRADE, no hourly scheduled market publisher, no production execution, and no claims that the 2026-11-22 conditional engineering RC implies trade readiness.

## QA

`tests/test_mst_private_unpublished_manifest242.py` uses only fake Google HTTP responses and fictional records, including negative cases for: failed owner rights, shared/redirected sibling, stale/altered CHUNK, source/version mismatch, existing/duplicated manifest, tampered second media read, bad MD5, metadata version changes, unsafe receipt reclassification and failed upload. No provider data or Drive live writes.

Previous §240 and §241 implementation remain unchanged in this atomic PR. A **separate** approved integration PR can wire this stage into a tightly gated workflow and prove actual cloud behavior only after source rights and test isolation are checked. Draft PR23 must remain unmerged.
