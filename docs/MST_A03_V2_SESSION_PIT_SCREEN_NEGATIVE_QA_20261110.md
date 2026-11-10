# MST A03 — Test-only V2 session-membership + retained-history PIT screen (NO APPLY)

QA ID: MST-A03-V2-SESSION-PIT-UNTRUSTED-COMPOSITION-20261110
Date: 2026-11-10 Asia/Ho_Chi_Minh
Status: 34 synthetic unittest and 16 original/V2 integration assertions, exact GitHub CI pending.

## Precise scope and relevance
This is the next checkpoint after §91/§92 original V1 late-first-known and wrong-session cache boundary. It is NOT another copy of A03 revision supersession or of A02 five-generation as-of archive: it composes the existing original V1 SyntheticIncrementalStore, existing A03 V1→V2 FixtureV2ConsumerScope, existing V2 FixturePartitionV2 and A03 typed FixtureRevision/resolve_untrusted_fixture, using a completely **new, opt-in QA-only screening layer under scripts/** (not a ninth V2 src module). The new layer adds the missing *single-bar session membership and payload-binding decision* before an as-of candidate can be selected in a strictly untrusted fixture.

It constructs a self-reported exact M5 session grid, retains r1 and late-known r2 payloads under explicit session A identity, verifies SHA256/first-known/revision/datetime linkage and a contiguous ordered supersession chain, and selects r1 just before r2 publication, r2 precisely at r2 publication. A late correction of session A after the nominal session end is allowed because the original event-time membership remains A. It refuses future-known bars, mismatched provider/endpoint/price-basis/session-date, invalid calendars, missing historical root, stale or ambiguous sequence and self-reported calendar authority.

Actual original source integration counterexample: original V1 cache can receive a next-day B candle under A key when caller passes a wide scope; existing read-only V2 consumer can structurally preview that contaminated current state because its partition+checkpoint checks alone do NOT prove bar-to-calendar session membership. Existing V2 preview correctly refuses old historical as-of before the materialized cursor. New separate QA-only screen independently rejects the deliberately crossed B candle according to its explicit caller-supplied A-session grid.

## No external root or real source admission
The grid, retained r1/r2 version list, source first-known clocks and opaque digests are ALL fabricated; they can be self-selected and backfilled by a caller. An untrusted code-level pass **does not establish** licensed SSI/DNSE/VCBS issuer, correction-history closure, official Vietnamese market session boundaries, actual independent signer/custody, true CAS/floor, immutable physical Google Drive cache or a permitted market signal. Candidate output is explicitly UNVERIFIED, never trading. Original 63 V1 and eight existing opt-in V2 source files remain unchanged and byte-locked; the new screen lives only in scripts/tests and only runs on GitHub Actions. No Mac, MOCHI, local developer computer, other cloud, GitHub ACL/ruleset/ref updates or merge.

## Owner decision remains OPEN
A02 owner 0/63, A03 V2 0/8, A03 owner choices 0/14; G01–G08 and OA01–OA06 OPEN. Before a real opt-in V2 consumer can enforce session + PIT, owner must approve an independent official session/calendar source with verifiable provider record membership, source-first-known and correction closure/retention, licensed Drive storage policy, V1 vs V2 behavior change and deterministic after-correction replay. No trading or production until all gates close.

## QA status
Pending GitHub-hosted exact implementation and final report HEAD checks. When it runs green it proves ONLY the stated synthetic negative interface characterization, not an owner signoff or production-ready feature.
