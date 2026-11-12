# MST M4 — PR review freshness and account deduplication: negative audit, NOT reviewer authority

Date: 2026-11-10 (Asia/Ho_Chi_Minh)
QA: MST-M4-PR8-REVIEW-FRESHNESS-NEGATIVE-20261110
Status: Draft PR8 read-only implementation; exact HEAD CI pending.

## Why this matters
Existing owner proposal reads that GitHub ruleset requires 0 positive approvals, and counts PR8 reviews. A raw count alone cannot show whether a review targets the actual head, is a dismissed/stale approval, comes from the same account as the author, represents multiple accounts, or even originates from a Bot. GitHub's real merge decision also depends on ruleset policy, reviewer permissions, code ownership, most recent reviewable push, merge-base/diff freshness, and owner-controlled authority; a read-only REST fixture cannot independently certify those.

## New read-only scanner and 33 synthetic tests
scripts/m4_pr_review_freshness_audit.py fetches live PR8 metadata twice around a paginated GET-only review scan, refusing head/base/draft changes. Evaluates review states and latest submitted event per numeric GitHub account ID, excludes author and Bot accounts, requires current-head SHA, refuses duplicate review IDs and unknown states, treats unsubmitted/pending/malformed data as zero credits and fails on unexhausted pagination. Sanitized JSON emits only totals and strict NO-GO flags; no actor IDs, emails, logins, review messages, secrets or raw reviewer objects. Conservative COMMENTED-after-APPROVED classification may undercount GitHub's actual count; this is an audit signal, NOT an implementation of GitHub's review approval algorithm.

Tests target same account repeated approvals, a second numeric user ID not proving separate human/controller, bot, author, stale SHA, new CHANGES_REQUESTED/DISMISSED, pending, invalid date, missing IDs, moved head, base drift, duplicate events, partial pagination, and denial of all merge/market/trading flags. Existing owner-policy 22 tests remain, plus 33 new tests in the same GitHub-hosted PR8-only read-only workflow. Original 63 V1 and 8 opt-in V2 locked source bytes checked first.

## Actual status and durable external requirements
At last observed live read, Draft PR #8 had zero review events and main ruleset 26801439 required zero positive PR reviews, with code owner review, stale approval dismissal and last push approval disabled. This new tool does not change settings or enroll an independent human. It can count technical distinct GitHub account IDs but **cannot prove genuinely independent controllers or reviewers with write/code-owner permission**, and must not treat a second account as independent approval. PR review data alone cannot establish last pusher identity, GitHub's diff merge-base review state or independent authorization.

Current owner gates A03 0/14, A02 0/63, V2 0/8; E01/E02/E03/E06/E10/E12/E14 still NOT_RECEIVED and G01–G08/OA01–OA06 OPEN. Main and Swing source unchanged; PR8 remains Draft/unmerged. No Mac/MOCHI/local/third Cloud, signer secrets, provider rights, real Drive market cache, privileged GitHub mutations, merge or production trading.

### Owner-only next action, not performed
Authorized independent GitHub reviewer enrollment, private effective permission/bypass readback, positive approval count and stale/last-push protection ruleset decisions, then controlled approval process. No reviewer identity or private evidence in this public artifact. Documentation/CI reference must be updated after exact final report HEAD is checked.

## Implementation code-HEAD GitHub CI actual evidence (later report HEAD must be checked)

At Draft PR #8 code HEAD b345ea2264070a88754bfdd62e2867c1a359e2ae, independently verified **41/41 GitHub Actions SUCCESS**.
Existing GitHub-hosted M4 review governance workflow
https://github.com/ngluonghoa/MST/actions/runs/42825461076
returned SUCCESS for all steps, with GitHub job log explicitly reporting
"Ran 22 tests" / OK (old policy) and "Ran 33 tests" / OK (new review
freshness/dedup), live remote 63 inherited V1 and 8 V2 source byte lock,
live GET-only main ruleset/PR/reviews/CODEOWNERS and sanitized fresh PR8
review scan. PR8 live scan recorded review_events_seen=0 and
PR_REVIEW_ACCOUNT_EVENTS_SCANNED_INDEPENDENT_AUTHORITY_NOT_PROVEN_NO_GO.
No reviewer ID, login, review text or secrets copied to public artifact.

This is a NEGATIVE observation at one token/time snapshot and public fixture
proof, NOT official GitHub review merge eligibility, independently authenticated
owner custody or protected external supplier origin. GitHub merge rules must
be approved and applied by owner separately; source, vendor licenses and
trading remain NO-GO. The appended report creates a new PR HEAD; revalidate
all 41 workflows at that exact report-containing HEAD before final claim.
Permanent Drive QA: https://docs.google.com/document/d/1iVpD157dM8favh_As6P_QaeZ-uAkOKnCUqk5OLgcYaE/edit .
