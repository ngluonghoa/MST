# MST A03 — Self-anchored proof contract: independently anchored authority remains absent

QA ID: MST-A03-SELF-ANCHOR-FALSIFICATION-20261110
Status: DRAFT PR8, exact-final-HEAD CI PENDING. This is *a negative-falsification experiment*, not a fix for independent trust, source licensing or owner approval.
Source: Swing cd90c1babae8912db31490ad614fc2ad2f868042; MST protected main 4048f91beaaa3410116d97e35896c8b688384e19; inherited 63 V1 + eight opt-in V2 unchanged.

## Findings / limitation after previous semantic text lock
The new reviewed semantic SHA256 and Python REVIEWED_* constants are public code and public fixtures stored in the **same mutable Draft PR**. They detect one-sided accidental changes; they cannot prevent a single controller from modifying the checklist AND its reviewed Python constant and then recomputing a perfectly well-formed SHA256. The standalone local verifier accepts that new pair. In this situation, a green GitHub Actions run is not independent acceptance of the revised semantics. GitHub source code provenance or public Drive summaries under one account do not create an independently controlled trust root.

## Three executable explicit counterexamples, no real trust material
- Co-edit owner-source enrollment criterion and reviewer literal; original validator rejects, altered validator accepts, SHA changes.
- Reassign source correction incompleteness to durable-floor gate while co-editing its risk-to-gate verifier fixture; original validator rejects, altered accepts.
- Relabel existing M4 E11 proof kind and corresponding reviewer constant; original validator rejects, altered accepts.

For all three: 16 targeted unittest methods assert unilateral rejection and jointly modified acceptance, the original coarse gate/case index remains the same, the semantic hash changes but is only locally recalculated, and **every real authority/production/trading status remains false**. Synthetic mutable Python patch fixtures do not edit any real market data or actual owner approvals.

## Actual read-only GitHub control observation (connector scope, not external root proof)
Read-only GitHub API observed repo ruleset ID 26801439 named MST - Protect Main, active; deletion and non-fast-forward restricted, three required status checks, and pull_request required_approving_review_count=0, require_code_owner_review=false, dismiss_stale_reviews_on_push=false. PR8 reviews collection returned [] at observation time. No CODEOWNERS at root or .github path tested. Branch-protection endpoint returned 403 for the current integration, so a full independently authenticated effective permission/bypass inventory is **not** established. The ruleset result also exposes a bypass actor field, but its returned scope is not proof of complete effective root/custody separation, nor proof the policy cannot later be modified by admins.

Risk: if an actor controls PR fixture and verifier changes, current automated tests alone do not impose a required independent human approval. This observation does **not** grant permission to change GitHub branch rules, policies, identities or merge PR. It confirms why existing M4 E01/E02/E03/E10/E12/E14 and A03 INDEPENDENT-CUSTODY-12 remain OPEN.

## Owner-facing next decisions (separate authorization required)
- Owner to decide a truly independently controlled review/approval and effective admin/bypass/custody model within Option A GitHub+Drive; don't substitute a CODEOWNERS file alone for effective enforcement.
- An authorized controller to propose the main ruleset requiring positive independent reviews, code-owner review where appropriate, stale-review dismissal and branch policy protections. These are proposals only, not applied.
- Independently scoped reviewers to verify effective permission/role, provenance and signer-root rights privately; keep real principal identities and keys out of public Git and PR logs.
- Provider licensing, official revisions, revocations, genuine cross-run floor, real server CAS and Drive physical licensed market-data cache must be independently qualified before any production gate.

No main/ruleset/ref/ACL changes; no Mac/MOCHI/local/third Cloud; no real vendor API/cache, broker or trading. A02 owner 0/63, A03 full V2 0/8, A03 owner choices 0/14, G01–G08/OA01–OA06 remain OPEN; PR8 stays DRAFT/UNMERGED and all production/trading NO-GO.
