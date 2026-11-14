"""UI-1.0 LOCKED diagnostic ReportViewModel (NO renderer, NO trading).

The fixed A-I section order, B1..B8/S1..S8 legend, 8 stages and 8
per-signal audit topics are copied from approved 02_REPORT_UI_v1.0,
sections 3, 4, 5, 7 and 9.2. This is only a typed binding/negative gate for
an incomplete source and a SPEC_PENDING engine: it cannot publish a FULL
ANALYSIS or confirm a buy/sell/position, nor does it render a UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

from .contracts import DecisionStatus, Strategy, ZONE_IDS
from .private_cache_source_bridge import PrivateD1Diagnostic
from .replay import require_utc

UI_VERSION="UI-1.0"
SCHEMA="mst.ui10.private_d1_diagnostic_viewmodel.v0.1"
SECTION_IDS=tuple("ABCDEFGHI")
ZONE_LEGEND=(
    ("B1","Đáy lớn sau xu hướng giảm kéo dài"),
    ("B2","Đáy nhịp điều chỉnh trong xu hướng tăng"),
    ("B3","Đáy vùng tích lũy đi ngang"),
    ("B4","Đáy cao đầu tiên sau đảo chiều tăng"),
    ("B5","Retest sau Breakout"),
    ("B6","Vùng nén giá trong xu hướng tăng"),
    ("B7","Đáy hồi kỹ thuật trong xu hướng giảm"),
    ("B8","Momentum Breakout, phá nền giá/kháng cự mạnh"),
    ("S1","Đỉnh lớn sau xu hướng tăng kéo dài"),
    ("S2","Đỉnh nhịp hồi trong xu hướng giảm"),
    ("S3","Đỉnh nhịp tăng trong xu hướng tăng"),
    ("S4","Đỉnh vùng đi ngang hoặc phân phối"),
    ("S5","Đỉnh thấp đầu tiên sau đảo chiều giảm"),
    ("S6","Bull Trap, Breakout thất bại"),
    ("S7","Retest sau Breakdown"),
    ("S8","Blow-off Top, đỉnh tăng nóng/hưng phấn cực độ"),
)
PIPELINE_STEPS=(
    "DATA MANAGER", "DATA VALIDATOR", "ANALYSIS ENGINE",
    "EXIT PROTECTION", "ZONE DETECTION", "SIGNAL ENGINE",
    "AUDIT & DECISION", "REPORT & HISTORY",
)
AUDIT_TOPICS=(
    "Data Quality", "Multi-Timeframe", "Market & RS",
    "Setup / Zone Evidence", "Trigger / Candle Close",
    "Volume / Momentum / Volatility", "Risk & Executability",
    "Reproducibility / Evidence",
)
_RUN_ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
_EXCHANGE=re.compile(r"(HOSE|HNX|UPCOM)\Z")
_EXPECTED_ZONE=tuple(z[0] for z in ZONE_LEGEND)
if _EXPECTED_ZONE != ZONE_IDS:
    raise RuntimeError("MST_LOCKED_UI10_ZONE_ORDER_NOT_SOURCE_ALIGNED")


class LockedUi10Denied(ValueError):
    """Error messages must never include source prices or private document IDs."""


@dataclass(frozen=True)
class LockedUi10DiagnosticViewModel:
    """Immutable JSON-serializable *read-only diagnostic* viewmodel."""
    data: dict[str,Any]
    reference_sha256: str
    all_source_rules_verified: bool=False
    report_published: bool=False
    user_trade_eligible: bool=False

    def __post_init__(self) -> None:
        if (not isinstance(self.data,dict)
                or self.data.get("schema") != SCHEMA
                or self.data.get("ui_version") != UI_VERSION
                or self.data.get("publication_state") != "INCOMPLETE_REPORT"
                or self.data.get("action_eligible") is not False):
            raise LockedUi10Denied("MST_LOCKED_UI10_VIEWMODEL_AUTHORITY_INVALID")
        try:
            canonical=json.dumps(self.data,sort_keys=True,
                                 separators=(",",":"),ensure_ascii=False,
                                 allow_nan=False).encode("utf-8")
        except (ValueError,TypeError):
            raise LockedUi10Denied("MST_LOCKED_UI10_VIEWMODEL_JSON_INVALID") from None
        if sha256(canonical).hexdigest()!=self.reference_sha256:
            raise LockedUi10Denied("MST_LOCKED_UI10_VIEWMODEL_DIGEST_DRIFT")


def _require_diag(d: Any, strategy: Strategy, *, as_of: datetime,
                  digest: str, symbol: str, provider: str) -> None:
    if type(d) is not PrivateD1Diagnostic or d.strategy is not strategy:
        raise LockedUi10Denied("MST_LOCKED_UI10_BOTH_STRATEGIES_REQUIRED")
    if (d.as_of_utc != as_of or d.source.raw_source_sha256!=digest
            or d.source.symbol!=symbol or d.source.provider!=provider
            or d.source.eligible_for_signals is not False
            or d.source.eligible_for_backtest is not False
            or d.source.venue_close_attested is not False
            or d.source.issuer_first_known_attested is not False
            or d.source.source_is_appowned_publisher is not False
            or d.eligible_for_signals is not False
            or d.trading_or_broker_calls != 0):
        raise LockedUi10Denied("MST_LOCKED_UI10_CROSS_SOURCE_OR_AUTHORITY_DRIFT")
    decisions=d.decisions
    if (type(decisions) is not tuple or len(decisions)!=16
            or tuple(x.zone_id for x in decisions)!=ZONE_IDS
            or any(x.strategy is not strategy
                   or x.status is not DecisionStatus.UNVERIFIED
                   or x.evidence for x in decisions)):
        raise LockedUi10Denied("MST_LOCKED_UI10_16_ZONE_COVERAGE_NOT_UNVERIFIED")


def _run_id(s: Any) -> str:
    if type(s) is not str or not _RUN_ID.fullmatch(s):
        raise LockedUi10Denied("MST_LOCKED_UI10_RUN_ID_INVALID")
    return s


def build_private_d1_ui10_diagnostic(
    short: PrivateD1Diagnostic,
    swing: PrivateD1Diagnostic,
    *,
    run_id: str,
    exchange: str,
) -> LockedUi10DiagnosticViewModel:
    """Bind two fail-closed original-engine views into the LOCKED A-I skeleton.

    This is *not* a renderer or FULL_ANALYSIS and does not access the network.
    No source revisions/rows/price points/holdings leak into this diagnostic.
    """
    _run_id(run_id)
    if type(exchange) is not str or not _EXCHANGE.fullmatch(exchange):
        raise LockedUi10Denied("MST_LOCKED_UI10_EXCHANGE_UNATTESTED")
    if type(short) is not PrivateD1Diagnostic:
        raise LockedUi10Denied("MST_LOCKED_UI10_SHORT_DIAGNOSTIC_REQUIRED")
    require_utc(short.as_of_utc)
    source=short.source
    if (source.source_rows_observed < 1
            or not source.raw_source_sha256
            or source.source_snapshot_day > short.as_of_utc.date()):
        raise LockedUi10Denied("MST_LOCKED_UI10_SOURCE_NOT_CAUSALLY_AVAILABLE")
    for d,strategy in ((short,Strategy.SHORT),(swing,Strategy.SWING)):
        _require_diag(d,strategy,as_of=short.as_of_utc,
                      digest=source.raw_source_sha256,
                      symbol=source.symbol,provider=source.provider)
        if (d.source.source_snapshot_day != source.source_snapshot_day
                or d.source.source_rows_observed != source.source_rows_observed):
            raise LockedUi10Denied("MST_LOCKED_UI10_SOURCE_REVISION_DRIFT")

    zone_rows=[
        {
            "zone_id":zone,"locked_legend":label,
            "status":"UNVERIFIED","source_quality":"UNVERIFIED",
            "reason":"SOURCE_UNPUBLISHED_AND_DETECTOR_SPEC_PENDING",
            "confirmed":False,"eligible_for_signal":False,
            "timeframe_verified":False,"evidence":[],
        }
        for zone,label in ZONE_LEGEND
    ]
    steps=[
        {
            "step_id":i,"step_name":name,
            "status":"BLOCKED" if i in (1,2) else "NOT_STARTED",
            "method":None,"completed_at_utc":None,
            "evidence":[],
            "reason":("PRIVATE_REFERENCE_NOT_VERIFIED_APP_OWNED_SOURCE"
                      if i in (1,2) else
                      "UPSTREAM_SOURCE_ORIGINAL_ENGINE_NOT_VERIFIED"),
        }
        for i,name in enumerate(PIPELINE_STEPS,1)
    ]
    audit=[
        {"audit_id":i,"topic":name,"status":"WARN",
         "reason":"MANDATORY_DATA_OR_SIGNAL_EVIDENCE_UNVERIFIED",
         "last_checked_utc":short.as_of_utc.isoformat(),
         "hard_fail":True,"evidence":[]}
        for i,name in enumerate(AUDIT_TOPICS,1)
    ]
    branch={
        "state":"BLOCKED","primary_zone":None,"secondary_zones":[],
        "trigger":None,"score":None,"early":False,"confirmed":False,
        "watch_zone":None,"entry":None,"max_entry":None,
        "stop_loss":None,"take_profit_1":None,"take_profit_2":None,
        "risk_reward":None,"decision":"NO_TRADE",
        "reason":"SOURCE_AND_SIGNAL_NOT_VERIFIED",
    }
    # The nine SECTION IDs are a binding contract, not a new layout.
    view={
        "schema":SCHEMA,"ui_version":UI_VERSION,
        "ui_design_locked":True,"run_id":run_id,
        "symbol":source.symbol,"exchange":exchange,
        "as_of_utc":short.as_of_utc.isoformat(),
        "source_provider":source.provider,
        "source_capture_day":source.source_snapshot_day.isoformat(),
        "source_native_tf":"D1",
        "source_rows_observed":source.source_rows_observed,
        "source_raw_sha256":source.raw_source_sha256,
        "source_origin":"PRIVATE_CONNECTED_MCP_REFERENCE_ONLY",
        "issuer_close_attested":False,
        "issuer_first_known_attested":False,
        "data_quality":"UNVERIFIED",
        "pipeline_verified_count":0,"zone_evaluated_count":16,
        "zone_verified_count":0,
        "audit_verified_count":0,
        "pipeline_steps":steps,
        "zone_rows":zone_rows,
        "audit_topics":audit,
        "strategies":{
            "SHORT":dict(branch),
            "SWING":dict(branch),
        },
        "position_context_status":"NOT_PROVIDED",
        "position_context_wording":"Không có vị thế được cung cấp",
        "step04_result":None,
        "sell_state":"WATCH_BLOCKED_POSITION_UNVERIFIED",
        "exit_protection_result":None,
        "cache_metrics_measured":False,
        "cache_hit_rate":None,
        "publication_state":"INCOMPLETE_REPORT",
        "step08_atomic_commit_verified":False,
        "report_published":False,
        "action_eligible":False,
        "reasons":[
            "REAL_PRIVATE_MCP_SOURCE_NOT_PRODUCTION_PUBLISHER",
            "OFFICIAL_VENUE_CLOSE_FIRST_KNOWN_UNATTESTED",
            "ORIGINAL_16_DETECTOR_RULES_SPEC_PENDING",
            "STEP08_COMMIT_AND_UI_RENDERER_NOT_IMPLEMENTED",
        ],
        "section_ids":list(SECTION_IDS),
        "sections":{
            "A":{"status":"SOURCE_UNVERIFIED","report_gate":"BLOCKED"},
            "B":{"status":"MARKET_CONTEXT_NOT_VERIFIED"},
            "C":{"strategy":"SHORT","status":"BLOCKED"},
            "D":{"strategy":"SWING","status":"BLOCKED"},
            "E":{"status":"NO_POSITION_DATA_PROVIDED"},
            "F":{"status":"16_UNVERIFIED","zone_count":16,
                 "pipeline_steps_present":8},
            "G":{"status":"AUDIT_UNVERIFIED","topic_count":8},
            "H":{"status":"CACHE_PRIVATE_DIAGNOSTIC_ONLY",
                 "no_measured_hit_rate":True},
            "I":{"status":"INCOMPLETE_REPORT","decision":"NO_TRADE"},
        },
        "rendered_ui":False,
        "new_ui_design_approved":False,
        "trading_or_broker_calls":0,
    }
    raw=json.dumps(view,sort_keys=True,separators=(",",":"),
                   ensure_ascii=False,allow_nan=False).encode("utf-8")
    return LockedUi10DiagnosticViewModel(view,sha256(raw).hexdigest())
