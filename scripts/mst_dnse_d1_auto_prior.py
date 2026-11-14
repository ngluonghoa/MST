"""Bounded, fail-closed discovery of a previous app-owned DNSE D1 source.

Only discovers a candidate ID. Existing source reader MUST independently
verify full source bytes, owner/private parent, checksums, and session overlap.
No publisher, market-data calls, or trading.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

MAX_CENSUS_PAGES = 8
PAGE_SIZE = 100
D1_NAME = re.compile(
    r"MST_UNPUBLISHED_DNSE_(?:D1|NATIVE_D1)_([1-9][0-9]{5,19})_1\.json\Z"
)
OTHER_NATIVE_NAME = re.compile(
    r"MST_UNPUBLISHED_DNSE_NATIVE_(?:M5|M15|M30|H1)_[1-9][0-9]{5,19}_1\.json\Z"
)


def discover_previous_dnse_d1(
    session: Any, env: Mapping[str, str], parent_id: str,
) -> str | None:
    """Unique predecessor by preceding GitHub run ID, never filename guess.

    A missing labeled D1 predecessor returns None only after complete bounded
    census. Unlabeled legacy D1 data fail closed and need explicit migration.
    """
    from scripts import mst_mfx_style_appowned_pipeline as cloud

    mode, _ = cloud.guard(env)
    if (mode not in (cloud.MODE_STAGE, cloud.MODE_STAGE_NATIVE)
            or env.get("MST_SOURCE_TF", "D1") != "D1"
            or env.get("MST_DNSE_PREVIOUS_SOURCE_FILE_ID") != "auto"):
        raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_STAGE_ONLY")
    if type(parent_id) is not str or not cloud.DRIVE_ID_RE.fullmatch(parent_id):
        raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_PARENT_INVALID")
    current_id = env.get("GITHUB_RUN_ID", "")
    if type(current_id) is not str or not re.fullmatch(r"[1-9][0-9]{5,19}", current_id):
        raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_RUN_ID_INVALID")
    symbol = env["MST_DNSE_SYMBOL"]

    ids: set[str] = set()
    names: set[str] = set()
    matching: list[tuple[int, str]] = []
    token = None
    complete = False
    used_tokens: set[str] = set()
    for _ in range(MAX_CENSUS_PAGES):
        params: dict[str, Any] = {
            "q": ("'" + parent_id + "' in parents and "
                  "name contains 'MST_UNPUBLISHED_DNSE_' and trashed = false"),
            "fields": "nextPageToken,files(id,name,mimeType,parents,trashed,appProperties)",
            "pageSize": PAGE_SIZE,
        }
        if token is not None:
            params["pageToken"] = token
        try:
            response = session.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params, timeout=25, allow_redirects=False,
            )
            if response.status_code != 200:
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_HTTP_DENIED")
            data = response.json()
        except cloud.CloudGateDenied:
            raise
        except Exception:
            raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_REQUEST_FAILED") from None
        if type(data) is not dict or type(data.get("files")) is not list:
            raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_SHAPE_INVALID")
        entries = data["files"]
        if len(entries) > PAGE_SIZE:
            raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_PAGE_OVERSIZED")
        for record in entries:
            if type(record) is not dict:
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_RECORD_INVALID")
            file_id, name = record.get("id"), record.get("name")
            if (type(file_id) is not str or not cloud.DRIVE_ID_RE.fullmatch(file_id)
                    or type(name) is not str or not name.startswith("MST_UNPUBLISHED_DNSE_")
                    or record.get("mimeType") != "application/json"
                    or record.get("parents") != [parent_id]
                    or record.get("trashed") is not False):
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_SCOPE_DRIFT")
            if file_id in ids or name in names:
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_DUPLICATE_CENSUS")
            ids.add(file_id)
            names.add(name)
            match = D1_NAME.fullmatch(name)
            if match is None:
                if not OTHER_NATIVE_NAME.fullmatch(name):
                    raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_UNKNOWN_SOURCE_FILENAME")
                continue
            props = record.get("appProperties")
            if (type(props) is not dict
                    or props.get("mst_unpublished") != "true"
                    or props.get("source_symbol") not in ("FPT", "DCM", "HPG")
                    or props.get("source_native_tf") != "D1"
                    or props.get("source_run_id") != match.group(1)
                    or type(props.get("source_sha256")) is not str
                    or not re.fullmatch(r"[0-9a-f]{64}", props["source_sha256"])):
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_LEGACY_OR_UNLABELED_SOURCE")
            if props["source_symbol"] != symbol:
                continue
            run_id = int(match.group(1))
            if run_id >= int(current_id):
                raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_FUTURE_OR_SELF_SOURCE")
            matching.append((run_id, file_id))
        new_token = data.get("nextPageToken")
        if new_token is None or new_token == "":
            complete = True
            break
        if (type(new_token) is not str or len(new_token) > 512
                or new_token in used_tokens):
            raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_BAD_CENSUS_TOKEN")
        used_tokens.add(new_token)
        token = new_token
    if not complete:
        raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_CENSUS_INCOMPLETE")
    if not matching:
        return None
    matching.sort(key=lambda item: item[0], reverse=True)
    if len(matching) > 1 and matching[0][0] == matching[1][0]:
        raise cloud.CloudGateDenied("MST_MFX_AUTO_D1_AMBIGUOUS_PREDECESSOR")
    return matching[0][1]
