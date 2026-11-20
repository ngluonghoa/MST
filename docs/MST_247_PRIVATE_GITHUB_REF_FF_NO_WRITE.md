# MST §247 — owner-private GitHub ref fast-forward candidate, NO WRITE

2026-11-20 ICT. Isolated original source-locked §199 module from broad Draft PR23; now depends on protected-main §246 signed CAS intent. **No private repository or GitHub API write is executed by this change.**

## Purpose

`scripts/mst_github_highwater_ref_proposal.py` validates caller-supplied **candidate** snapshots only, not independently authenticated GitHub responses:

1. Signed Ed25519 conditional-write intent must already pass §246 exact anchor/digest re-read, with all no-trade/no-publish authority flags still false.
2. Proposed ref must be `refs/heads/highwater/<SERIES_ID>` in a separate repo declared `visibility=private` (public `ngluonghoa/MST` forbidden). The exact observed old 40-hex SHA must match the caller's expected old SHA.
3. Proposed commit must be a nonzero, different Git SHA with **exactly one parent** equal to the old head. Merge commits, unrelated ancestry and trying to use the old SHA as the new commit fail.
4. A deterministic fingerprint binds repository/ref, expected parent, candidate commit/tree SHA, signed intent, series ID, generations/tips/revisions and `force=false`, `remote_write_executed=false`, `atomic_cas_independently_proven=false`, `cache_published=false`, `signals_eligible=false`.
5. A pre-submit ref reread rejects a moved/changed remote head or tampered proposal SHA. It does **not** call PATCH Git ref.

The internal candidate includes private ref SHAs and the signed intent fingerprint; **never print it or persist it in public CI logs**. Unit tests use fictional repo identifiers and invented hex hashes only.

## Why this is still not safe to publish

A supplied `private` flag is not a verified GitHub repo visibility guarantee. A nonforced fast-forward commit is an ancestry constraint, **not a globally immutable and independently signed CAS highwater**, and a privileged owner could still rewrite a branch or change rulesets. A stale backend could show identical old head to two writers; only an authorized remote operation followed by independent signed verification and durable external monotone witness closes that race.

The §244 GET-only private GitHub probe is available for later owner-controlled Cloud audit, but no owner-private repository authorization, effective ruleset/bypass review, independent public key/tip, signer lifecycle or trusted write principal is currently established in this branch. Do not create a public highwater repo or disclose owner credentials to public MST.

No SSI/DNSE rights to retain real market data, no source-finality/first-known, no production MANIFESTS/publisher, no 16 source-verified B/S zones, no OOS/UI golden. All remain UNVERIFIED/NO_TRADE. 2026-11-22 is conditional engineering RC only.
