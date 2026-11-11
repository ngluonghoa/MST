# MST M4 P0 — Private Three-Provider FPT/D1 Live Pilot Audit and Safe Refresh Contract

Date: 2026-11-11 Asia/Ho_Chi_Minh.
State: ONE-TIME REAL QUOTE PILOT VERIFIED IN USER PRIVATE GOOGLE DRIVE. CONTINUOUS AUTOMATIC CACHE AND PRODUCTION STILL NO-GO.

## Private pilot: real evidence, not repository contents

The user's explicit previous instruction authorized a one-time private cloud capture. ChatGPT read FPT D1 historical OHLCV from connected SSI, DNSE and VCBS MCP tools and persisted 20 historical sessions per source for 2026-10-14 through 2026-11-10, 60 rows total, as separate native Google Docs JSON snapshots under user's private MST Google Drive. These are real provider responses. GitHub repo contains **NO original licensed bars, prices, private Drive credential or vendor token**.

Private Google Drive folder:
https://drive.google.com/drive/folders/1F7mXwDXJW8KPCNSjFeKJ-2egkiobMaqz
Source docs:
SSI https://docs.google.com/document/d/1xtjwwroYLg8qU7GVAW5VZ32n1NR6u-x05d0F9Lq3xCk/edit
DNSE https://docs.google.com/document/d/1_0dIAse0YSdUKbHbV4v1p1VHjd1YsvLYUJ7RaYGLlBM/edit
VCBS https://docs.google.com/document/d/1exnZZyAGfGhsM0_0fliZpgJuGIeeus_Z5imUthQPMHw/edit
Manifest https://docs.google.com/document/d/1Ni8VN9rW0gaE9_CV8uyyaYbC4Heorsuc7gW2RQqHB3g/edit

Direct connector Google Drive readback verified 20/20 rows per source and correct private folder membership. A separately executed three-way cross-source audit joined all 20 common dates, independently checked each OHLC envelope and matched complete day-by-day native OHLC+volume. Observed mismatches: 0 for SSI vs VCBS native OHLC, 0 for SSI vs DNSE OHLC after a **diagnostic only** multiplication by 1000, 0 for raw volumes among all three, and 0 OHLC envelope failures. This is **observed 20-session pilot parity, not official provider unit proof, license approval or independently attested first-known history**. No 2026-11-11 still-open daily candle was retained.

## New code contract and intentional limitations

The additive scripts/m4_v21_private_pilot_d1_validation_lab.py implements:
- exact source-specific source-method/price basis/unit/namespace gates for SSI, DNSE and VCBS FPT/D1 one-time Google Docs pilot schema; never infer DNSE scale in stored payloads;
- per-source closed-session and date ordering, duplicate detection, complete row count, positive/finite numeric OHLC and nonnegative volume; VCBS provisional/adjustment/volume scope restrictions and DNSE Unix timestamp checked explicitly in UTC;
- private three-source manifest structural validation with verified readback flags and date completeness, no silent source substitution, issuer permission self-grant or cross-provider fallback;
- SHA256 fingerprints over the fixture payload's canonical JSON representation, **not vendor-issued signatures, external floor, immutable content-addressed Drive chunks or CAS**;
- dry-run only, idempotent closed-day incremental refresh candidate planner: same snapshot produces no append; missing old date denies; future/open bar denies; numeric value revision is tagged for issuer verification and cannot auto-publish;
- no network, GitHub source credentials, Google Drive live read/write, broker order or production cache mutation in this module.

The new tests/test_m4_v21_private_pilot_d1_validation_lab.py contains **60 focused wholly fictional cases**; .github/workflows/m2-a03-v2-manifest-full-policy-local-chain.yml runs them only in PR8 synthetic branch and emits a 14-day ephemeral fictional QA receipt. No real provider bars or private Docs content is placed in GitHub Actions artifacts. Original pinned 63 V1 plus eight previously existing V2 source modules remain unchanged.

## Platform integration gap: ChatGPT MCP is NOT a GitHub Actions auth token

Three connected ChatGPT MCP tools can read source data on the user's behalf. An independently running GitHub Actions process does NOT gain those MCP connections, permissions or refresh ability automatically. The private Google Drive Docs pilot was produced via the user-connected Drive connector, not GitHub runner service-account credentials. Actual GitHub runtime authentication, vendor endpoints, contract rights to external Cloud retention and incremental feed semantics are unverified. Do not say recurring monitoring or 5-minute refresh is active.

To genuinely automate the cache, an owner-reviewed separate Cloud identity, provider-approved transport and Google Drive publisher must demonstrate secure credentials, actual allowed account source rights and Google Drive read/write on that runner, source-specific adjustment units/calendar/first-known, idempotency/revisions, concurrency CAS/fencing, protected independent signer/high-water, revocation/retention, and explicit no silent cross-provider fallback. User's instruction to proceed eliminates unnecessary product confirmation; it does not independently authenticate a vendor's data-retention agreement.

## QA acceptance and governance

Prior exact HEAD 5dd923c7d3df14d6df86fb5c1fc840ce02588095 had 47/47 GitHub PR workflows PASS and 573 focused synthetic fixture methods. New 60 synthetic tests would yield 633 cumulative targeted, ONLY after exact report-containing HEAD and all 47 Cloud PR workflows SUCCESS. Counts are focused methods, not full repository suite.

Verify diff is only two new code/test paths, this document and existing workflow; preserve original source parity (63 V1 + eight existing V2) and pinned protected MST main at 4048f91beaaa3410116d97e35896c8b688384e19. PR #8 remains DRAFT, NOT merged.

M3 rights and service-account gating: https://github.com/ngluonghoa/MST/issues/9
M4 Drive actual distributed publisher and CAS: https://github.com/ngluonghoa/MST/issues/10

Hard NO-GO: public API access or a user-requested one-time private Google Docs pilot is not an authenticated legal vendor grant for continuous off-platform retention; no production consumer, live indicator publication, automatic schedule or trading should be enabled until the above conditions are independently evidenced.
