# MST A03 — SSI Time vs DNSE t: synthetic M5 START/END interpretation gap
QA date 2026-11-10 Asia/Ho_Chi_Minh. Draft PR8 additive-only fixture QA, not a calibrated provider decoder.

DNSE official public API: https://developers.dnse.com.vn/docs/dnse/get-ohlc-history/ exposes t as Unix timestamp seconds and resolution 5, without a clear START vs END guarantee.
SSI FastConnect docs: https://guide.ssi.com.vn/ssi-products/fastconnect-data/api-specs expose intraday Time HH:MM:SS and resollution integer, without clear START/END or entitled native M5 verification. Example Time 14:29:59 must NOT be silently rounded/assumed a M5 start.

Built a new scripts-only opt-in QA adapter that reuses original TimestampSemantic enum, the prior synthetic M5 two-interval session boundary and existing first-known revision screen, and the original native source BarProduct descriptions. Both parsed raw field *shapes* are invented: SSI local HH:MM:SS with explicit VN date, DNSE integer UNIX seconds.
At a fixed synthetic 11:30 lunch boundary, START(11:30) names a break candle and is rejected, whereas END(11:30) names the valid final [11:25,11:30) candle. At 13:00, START names first afternoon bar but END names a break bar [12:55,13:00). UNKNOWN semantic, wrong provider, wrong local date, milliseconds, bool epoch, unsupported native product and second-rounding are rejected. The historical r1/r2 revision remains known only at its fabricated first-known time.

35 new targeted unittests and 18 demonstration cases, original code byte-lock 63 V1 and 8 V2. No source of actual historical candles or SSI/DNSE credentials, no automatic production timestamp calibration, no data rights, no Google Drive cache, no orders, no GitHub main/ruleset changes. All owner approvals still zero, A02 0/63, V2 0/8, A03 choices 0/14, G01–G08/OA01–OA06 OPEN. Source issuer/calendar/auction first-known provenance and real CAS/floor remain NO-GO.

Exact final GitHub-hosted CI receipt to be appended only after observed workflow SUCCESS.