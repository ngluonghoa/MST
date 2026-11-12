# MST M4 — Main PR positive independent human review: OWNER PROPOSAL, NO APPLY

Date: 2026-11-10 Asia/Ho_Chi_Minh
Scope: GitHub + Google Drive only, Draft PR #8. This is not a signed owner approval, policy change or independent security root.
Main 4048f91beaaa3410116d97e35896c8b688384e19; Swing pin cd90c1babae8912db31490ad614fc2ad2f868042.

## Verified read-only GitHub configuration and limitation

Connected GitHub read for repo ruleset 26801439 "MST - Protect Main": active on default branch. Prevents deletion and non-fast-forward. Requires three existing Foundation contexts. However positive required approving reviews = 0; code owner review, stale review dismissal, last-push approval, and thread resolution are false. At the initial read, PR8 reviews collection was empty. All three recognized CODEOWNERS paths on main (root, .github and docs) returned 404 in this connected view. A separate branch protection call returned 403 to the GitHub integration. The ruleset response exposed bypass_actors=[] and current_user_can_bypass=never for the caller; this is not independent proof of all effective admin/recovery/control paths. A review event or GitHub Actions PASS cannot certify that an actual second controller exists.

## Owner-only decision candidate (none applied)

Propose a minimum of one *independent, non-author human reviewer* for main PRs, with owner discretion to require two reviews for trust root, cache rights, infrastructure and governance changes. Candidate settings require_code_owner_review=true after real CODEOWNERS + independent reviewer enrollment, dismiss_stale_reviews_on_push=true, require_last_push_approval=true, required_review_thread_resolution=true, while preserving deletion/non-fast-forward guards and all three Foundation CI contexts. Actual permitted reviewer/owner assignments, effective bypass graph, recovery/role separation and remaining shared-admin risk must be owner-reviewed privately before applying any rule. A CODEOWNERS file alone is not enforcement.

Reuse existing M4 E01, E02, E03, E06, E10, E12 and E14, decisions OA01/OA02/OA03/OA05/OA06 and security gates G01/G02/G07/G08, without creating new owner approvals. All original owner proofs are NOT_RECEIVED.

## Implementation: Draft PR #8, safe and cloud-only

Adds one public unapproved JSON candidate, one fail-closed Python preflight, 22 tests, one GitHub-hosted same-repo PR8-only workflow with read-only contents/pull-requests scopes, and this QA report. GitHub Actions audits actual rule, main, PR metadata, review collection and three CODEOWNERS paths. It does not publish reviewer identities, secrets, licenses or personal information. It checks remote original 63 V1 and 8 V2 byte lock first. Green means accurately detected NO-GO, never permission to merge.

No ruleset/permissions/main/CODEOWNERS/witness mutation, provider API, real market data or Drive cache, Mac/MOCHI/local or third Cloud. A02 owner 0/63, A03 V2 0/8, A03 owner choices 0/14; G01–G08 OA01–OA06 remain OPEN; M3/M4/M5/M8 production/trading NO-GO.

Exact report-containing HEAD CI pending verification; a code-HEAD PASS alone never certifies a later report commit.

## Exact implementation commit CI evidence — report commit needs separate verification

Draft PR8 implementation HEAD 92597dcc33977fc962ab2f4738ebd7ba602e02bd: independently checked **41/41** GitHub Actions workflow runs SUCCESS (one additional owner-governance workflow). Dedicated new read-only GitHub review audit https://github.com/ngluonghoa/MST/actions/runs/42822128609 SUCCESS, with **22/22** unit tests, original 63 V1+8 opt-in V2 source byte lock SUCCESS, GitHub actual GET-only ruleset/main/PR8/reviews and three CODEOWNERS paths SUCCESS, sanitized JSON artifact only. PR8 remains Draft/unmerged; protected main SHA 4048f91beaaa3410116d97e35896c8b688384e19 unchanged.

Owner evidence requirements E01/E02/E03/E06/E10/E12/E14 remain unreceived; no positive independent review enforcement, private signer/controller identities, effective permission independence or release authority proven. The owner candidate is not applied. Permanent Google Drive QA: https://docs.google.com/document/d/1MURIfIWRrEyF0Huj7dD9zTGOYk5wqgY5SzfgEM200II/edit .

The documentation update itself creates a new GitHub HEAD: repeat complete CI verification at the exact final report-containing commit before claiming final success.
