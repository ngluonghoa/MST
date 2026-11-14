"""Read-only HTML renderer for the approved UI-1.0 *INCOMPLETE* report.

Preserves A-I reading order, 16 B/S rows and legend, 8 pipeline steps, 8
audit topics, separate SHORT and SWING cards, position context and no-trade
conclusion. This is a static renderer, NOT a deployed site, golden screenshot,
signal certification, or permission to publish a live investment report.
No network, filesystem, JavaScript, signals, broker calls or external assets.
"""
from __future__ import annotations

from html import escape
from typing import Any

from .locked_ui10_binding import (
    LockedUi10Denied, LockedUi10DiagnosticViewModel,
    SECTION_IDS, ZONE_LEGEND, PIPELINE_STEPS, AUDIT_TOPICS,
)

_SECTION_TITLES = (
    ("A", "Dữ liệu & trạng thái xác minh"),
    ("B", "Bối cảnh thị trường"),
    ("C", "Cơ hội SHORT"),
    ("D", "Cơ hội SWING"),
    ("E", "Vùng bán & bảo vệ vị thế"),
    ("F", "Kiểm tra vùng B/S"),
    ("G", "Kiểm toán tín hiệu"),
    ("H", "Cache & lịch sử"),
    ("I", "Kết luận"),
)
if tuple(k for k, _ in _SECTION_TITLES) != SECTION_IDS:
    raise RuntimeError("MST_LOCKED_UI10_SECTION_TITLES_DRIFT")

_CSS = """
:root{color-scheme:light;--bg:#f7f8fa;--surface:#ffffff;--ink:#202b39;
 --muted:#536274;--line:#dce3eb;--warn:#815400;--warn-bg:#fff6dc;
 --buy:#17613a;--sell:#a32f2f;--info:#2c557a}
*{box-sizing:border-box}html{font-family:system-ui,-apple-system,"Segoe UI",
 Arial,sans-serif;line-height:1.5;background:var(--bg);color:var(--ink)}
body{margin:0;padding:18px}main{max-width:1120px;margin:0 auto}
h1{font-size:1.65rem;margin:.2rem 0}h2{font-size:1.15rem;margin:0 0 .8rem}
h3{font-size:1rem;margin:.7rem 0 .3rem}p{margin:.5rem 0}
.card{background:var(--surface);border:1px solid var(--line);
 border-radius:10px;padding:16px;margin:0 0 14px;min-width:0}
.diagnostic{border-left:5px solid var(--warn);background:var(--warn-bg);
 padding:12px;margin:10px 0;border-radius:5px}
.muted{color:var(--muted)}.warn{color:var(--warn);font-weight:650}
.buy{color:var(--buy)}.sell{color:var(--sell)}.tech{color:var(--info)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;
 text-align:left;font-size:.92rem}
th,td{padding:.55rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f3f6fa}caption{text-align:left;font-weight:650;margin:0 0 .35rem}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
 overflow-wrap:anywhere}
ul{padding-left:1.25rem}.note{font-size:.92rem}.skip-link{position:absolute;
 left:-10000px;top:auto}.skip-link:focus{position:static}
:focus-visible{outline:3px solid var(--info);outline-offset:3px}
@media(max-width:680px){body{padding:10px}.grid{grid-template-columns:1fr}
 .card{padding:12px}th,td{padding:.4rem;font-size:.87rem}h1{font-size:1.35rem}}
@media print{body{padding:0;background:white}.card{break-inside:avoid}}
"""


def _t(value: Any) -> str:
    """Escape every model-derived value; never interpolate raw provider HTML."""
    if not isinstance(value, str):
        raise LockedUi10Denied("MST_UI10_RENDER_NONSTRING_UNSAFE")
    return escape(value, quote=True)


def _row(*cells: str, attrs: str = "") -> str:
    # attrs and cell HTML are trusted internal constants or already escaped.
    return "<tr" + attrs + ">" + "".join(
        "<td>" + cell + "</td>" for cell in cells
    ) + "</tr>"


def _table(headings: tuple[str, ...], rows: list[str], *,
           caption: str) -> str:
    return (
        '<div class="table-wrap"><table><caption>' + caption + '</caption>'
        + '<thead><tr>' + "".join('<th scope="col">' + _t(x) + "</th>"
                                  for x in headings)
        + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _strategy(label: str, branch: dict) -> str:
    if (branch.get("state") != "BLOCKED"
            or branch.get("decision") != "NO_TRADE"
            or branch.get("confirmed") is not False
            or any(branch.get(k) is not None for k in (
                "primary_zone","entry","stop_loss",
                "take_profit_1","take_profit_2","risk_reward"))):
        raise LockedUi10Denied("MST_UI10_RENDER_FALSE_STRATEGY")
    lines=[
        ("Trạng thái", "BLOCKED · Chưa đủ bằng chứng"),
        ("Vùng chính/phụ", "Chưa xác định"),
        ("Watch Zone", "Chưa xác định"),
        ("Entry / Max Entry", "Chưa xác định"),
        ("Trigger / mức xác nhận", "Chưa xác định · UNVERIFIED"),
        ("Điểm chất lượng", "Chưa xác định, không phải xác suất thắng"),
        ("SL / TP1 / TP2 / R:R", "Chưa xác định"),
        ("Quyết định", "NO_TRADE"),
    ]
    return ('<div class="card" aria-label="' + _t(label) + '">'
            '<h3>' + _t(label) + "</h3>"
            + _table(("Trường","Kết quả"),
                     [_row(_t(a),_t(b)) for a,b in lines],
                     caption="Đánh giá hiện tại")
            + "</div>")


def _section(section: str, inner: str) -> str:
    title=dict(_SECTION_TITLES)[section]
    return ('<section id="section-' + section + '" data-ui-section="' + section
            + '" class="card" aria-labelledby="heading-' + section + '">'
            '<h2 id="heading-' + section + '">' + section + " · "
            + _t(title) + "</h2>" + inner + "</section>")


def render_ui10_incomplete_html(model: LockedUi10DiagnosticViewModel) -> str:
    """Return a stand-alone, CSP-locked, accessible static diagnostic HTML.

    Revalidate at the exact rendering boundary. The dataclass is frozen but
    its underlying dict is not, so mutation after construction must fail.
    The revalidated source snapshot alone never constitutes a verified signal.
    """
    if type(model) is not LockedUi10DiagnosticViewModel:
        raise LockedUi10Denied("MST_UI10_RENDER_TYPED_INPUT_REQUIRED")
    if (model.all_source_rules_verified is not False
            or model.report_published is not False
            or model.user_trade_eligible is not False):
        raise LockedUi10Denied("MST_UI10_RENDER_MODEL_AUTHORITY_FORBIDDEN")
    # Repeat full nested gate + hash after any caller might have mutated data.
    LockedUi10DiagnosticViewModel(model.data,model.reference_sha256)
    d=model.data
    if (d.get("ui_version")!="UI-1.0"
            or d.get("source_native_tf")!="D1"
            or d.get("source_provider") not in ("SSI","DNSE","VCBS")
            or d.get("position_context_wording")!="Không có vị thế được cung cấp"
            or d.get("sell_state")!="WATCH_BLOCKED_POSITION_UNVERIFIED"):
        raise LockedUi10Denied("MST_UI10_RENDER_SOURCE_OR_POSITION_DRIFT")
    symbol,venue,asof,provider,run=(
        _t(d["symbol"]),_t(d["exchange"]),_t(d["as_of_utc"]),
        _t(d["source_provider"]),_t(d["run_id"])
    )
    # The source hash is diagnostic metadata, never actual first-known proof.
    source_hash=_t(d["source_raw_sha256"])
    stamp=_t(d["source_capture_day"])
    sections={}
    sections["A"]=(
        "<h1>" + symbol + " / " + venue + " · INCOMPLETE_REPORT</h1>"
        '<p class="muted">UI-1.0 · ' + asof + " · " + provider
        + ' · D1 (tham khảo riêng tư)</p>'
        '<div class="diagnostic" role="alert"><strong>CHƯA ĐỦ DỮ LIỆU XÁC MINH'
        '</strong><p>Pipeline 0/8 VERIFIED · B 0/8, S 0/8 VERIFIED. '
        '16 vùng đã được liệt kê nhưng đều UNVERIFIED. '
        'Không có điểm mua/bán được phép sử dụng.</p></div>'
        '<p class="note">Nguồn: ' + provider
        + " · ngày ghi nhận " + stamp
        + " · SHA256 nguồn (kiểm tra nội bộ): <code>" + source_hash[:12]
        + '…</code></p><p class="muted">Run ID: <code>' + run + "</code></p>"
    )
    sections["B"]=(
        '<p class="warn">Chưa xác minh VN-Index, ngành, xu hướng W1/D1/H1'
        ', nguồn M15/M5, thanh khoản và corporate actions.</p>'
        '<p>Không gán trạng thái xu hướng hoặc phiên đóng khi chưa có '
        'chứng cứ từ nguồn được cấp quyền.</p>'
    )
    sections["C"]=_strategy("SHORT · 3–10 phiên",d["strategies"]["SHORT"])
    sections["D"]=_strategy("SWING · 10–60 phiên",d["strategies"]["SWING"])
    sections["E"]=(
        '<p class="warn">Không có vị thế được cung cấp</p>'
        '<p>SELL WATCH / Exit Protection: UNVERIFIED. Không suy ra '
        'đang nắm giữ hoặc đã xác minh không có cổ phiếu. '
        'Không phát lệnh bán hay tính số lượng/SL thực thi.</p>'
    )
    zones=d["zone_rows"]
    matrix=[]
    for entry in zones:
        z=_t(entry["zone_id"])
        matrix.append(_row(
            '<strong class="' + ("buy" if z.startswith("B") else "sell")
            + '">' + z + "</strong>",
            _t(entry["locked_legend"]),_t(entry["status"]),
            _t(entry["reason"]),
            attrs=' data-zone-id="' + z + '"',
        ))
    matrix_html=_table(
        ("Vùng","Tên vùng đã chốt","Trạng thái","Lý do"),
        matrix,caption="Ma trận 16 vùng B/S · 16/16 đã liệt kê, 0/16 VERIFIED",
    )
    legend=_table(
        ("Mã","Chú giải đã chốt"),
        [_row(_t(z),_t(name)) for z,name in ZONE_LEGEND],
        caption="Chú giải vùng B1–B8 và S1–S8",
    )
    step_rows=[]
    for step in d["pipeline_steps"]:
        i=step["step_id"]
        step_rows.append(_row(
            _t(f"{i:02d}"),_t(step["step_name"]),_t(step["status"]),
            _t(step["reason"]),
            attrs=' data-pipeline-step="' + str(i) + '"',
        ))
    steps_html=_table(
        ("Bước","Tên bước","Trạng thái","Bằng chứng/Chặn"),
        step_rows,caption="Checklist xác minh thực thi 8 bước · 0/8 COMPLETE",
    )
    sections["F"]=(
        matrix_html + legend + steps_html
        + '<p class="note muted">UNVERIFIED không tương đương NOT_DETECTED, '
        'NO SIGNAL hoặc kết quả phân tích đã hoàn tất.</p>'
    )
    audit_rows=[]
    for topic in d["audit_topics"]:
        i=topic["audit_id"]
        audit_rows.append(_row(
            _t(f"{i:02d}"),_t(topic["topic"]),_t(topic["status"]),
            _t(topic["reason"]),
            attrs=' data-audit-topic="' + str(i) + '"',
        ))
    sections["G"]=_table(
        ("Mục","Nội dung","Trạng thái","Lý do"),
        audit_rows,caption="8 mục kiểm toán · 0/8 PASS",
    )
    sections["H"]=(
        '<p>Cache nghiên cứu riêng tư, chưa phải Cache phát hành bằng '
        'atomic signed CAS.</p>'
        '<p>Hit rate: <strong>Chưa đo</strong>. Delta / lần chạy trước, '
        'invalidations, publisher highwater: Chưa xác minh.</p>'
        '<p class="muted">Không suy ra Cache hit, freshness hoặc '
        'first-known từ SHA256 nguồn.</p>'
    )
    sections["I"]=(
        '<div class="diagnostic" role="status">'
        '<strong>INCOMPLETE_REPORT · NO_TRADE</strong>'
        '<p>SHORT: BLOCKED · SWING: BLOCKED · SELL: UNVERIFIED.</p>'
        '<p>Thiếu xác nhận nguồn/phiên đóng, công thức 16 detector gốc, '
        'kiểm toán phát hành và Step08 atomic commit. '
        'Không tạo entry, SL, TP hay khuyến nghị giao dịch.</p></div>'
        '<p class="muted">Không phải FULL_ANALYSIS, không phải báo cáo LIVE '
        'đã xuất bản. Dữ liệu này chỉ phục vụ QA Cloud.</p>'
    )
    body="".join(_section(k,sections[k]) for k in SECTION_IDS)
    return (
        '<!doctype html><html lang="vi"><head>'
        '<meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; '
        'img-src &#39;none&#39;; script-src &#39;none&#39;; '
        'connect-src &#39;none&#39;; form-action &#39;none&#39;">'
        '<title>MST · INCOMPLETE_REPORT · UI-1.0</title>'
        '<style>' + _CSS + '</style></head><body>'
        '<a class="skip-link" href="#section-A">Bỏ qua đến nội dung chính</a>'
        '<main aria-label="MST UI-1.0 báo cáo chẩn đoán chưa hoàn tất">'
        + body + '</main></body></html>'
    )
