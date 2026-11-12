# MST A02 — Original V1 old-candle correction / session-label crossover

2026-11-10. Status: synthetic original-source QA, external trust and owner NO-GO.
Exact GitHub HEAD CI initially pending.

Prior W3 multi-generation tests already demonstrate as-of restoration when older
snapshots are explicitly retained. This new boundary is distinct: the unmodified
original SyntheticIncrementalStore has a latest-only read_bars(identity) method
and accepts a caller-supplied session_id and observation window without an
independently verified session membership assertion inside FixtureBar.

Two fabricated UTC session partitions A and B are built in GitHub-hosted
ephemeral SQLite (4 + 3 M5 bars). A late historical correction to the second
A bar is applied after B begins: V1 successfully recomputes the three
affected A checkpoints to equal its cold oracle; B remains unchanged.
The revised bar carries a later first-known time, and the original ReplayClock
correctly excludes it just before that boundary, but latest-only raw read_bars
still returns the revised data; an as-of consumer must separately resolve
historical source-visible revisions. This does NOT establish that any existing
separate V1 replay adapter erroneously trades on look-ahead.

A synthetic session-B candle can also be intentionally passed under the A
CacheIdentity and a B-time window. V1 accepts it inside A and recomputes a
self-consistent checkpoint. B stays isolated under its correct key. This is
proof of caller-mislabeled input accepted without native calendar/source
membership enforcement, not proof of a live provider feed defect.

28 direct unit tests assert 21 real original-code observations, no owner
approvals, no official calendar, no source-authenticated first-known and no
real Drive cache or trading. Existing original 63 V1 and eight V2 byte-lock
must pass first. The source and protected main remain untouched, PR8 draft.
No Mac, MOCHI, local user machine, third Cloud, licensed quotes or broker.

Owner action OPEN: independent publisher-issued source/session identity,
source observation first-known and correction ledger, official VN session
calendar, source entitlement and correction retention. Only after explicit
owner approval may a separate opt-in V2 boundary reject cross-session writes
and provide authenticated as-of selection. No new V1 behavior may be silently
patched or accepted as full 1:1 parity. Formal A02 0/63, V2 0/8, A03 0/14,
G01-G08/OA01-OA06 open; production and trading NO-GO.

## Exact implementation-head CI and observed source behavior

Draft PR8 implementation HEAD `ba3d94c2d08600ab43a88ef853f986c77fb795e9`: independently verified **43/43 GitHub Actions SUCCESS**. Dedicated source-locked GitHub-hosted read-only A02 QA https://github.com/ngluonghoa/MST/actions/runs/42837052364 SUCCESS, logs show **Ran 28 tests / OK**, 21/21 original V1 SQLite source behavioral assertions PASS, original upstream/main/PR 63 inherited V1 + eight already existing opt-in V2 byte-lock SUCCESS before execution.

Actual fabricated-session counts: A initially 4 closed M5 bars; B 3. Late correction for an old A bar after B begins recomputes exactly 3 A indicator checkpoints and equals original cold recomputation, B unchanged. Raw V1 read_bars(identity) is latest-only and lacks an as_of parameter; a separate ReplayClock excludes corrected revision just before its caller-supplied first-known boundary, but the raw cache read returns that late revision. Caller-mislabeled session B candle is accepted under session A key and A becomes 5 rows with internally coherent indicator replay; proper B remains 3. This proves missing independent session-membership enforcement at the **synthetic V1 cache write boundary**, not a confirmed exchange/vendor defect or a demonstrated complete backtest leak.

Synthetic receipt SHA256 `65dddacb060dad324bdc33110f911204523c5d8db610e244fdeb65fe71a6bc01` is test consistency only, NOT a trusted provider, license, source-first-known or identity signer. Owner A02 0/63, A03 V2 0/8, A03 choices 0/14 remain open; production/trading NO-GO. Permanent Google Drive QA: https://docs.google.com/document/d/1pfYbbJ9RW8GeeNMSIy8UA-YgtNaPerwsV9L-pjJaYhE/edit .

**This QA append changes the PR HEAD; exact final report-containing HEAD GitHub CI requires separate revalidation before claiming the final 43/43 checkpoint.**
