#!/usr/bin/env python3
"""MST staging-only fictional JSON proof. MANUAL / DRAFT / no market data.

Read-only probe is the default. The real single-file Google Drive upload is
possible only after a separate exact owner repository-variable acceptance.
This DOES NOT implement Google Drive transactions, CAS or market Cache.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping

from scripts.mst_oauth_manual_drive_bootstrap import (
    OAuthSecrets, _new_authorized_session,
)

DRIVE = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
ROOT = "MST_OAUTH_CACHE_V1"
CHILD = "STAGING_ONLY"
FOLDER_MIME = "application/vnd.google-apps.folder"
OWNER_REPO = "ngluonghoa/MST"
EXPECTED_WORKFLOW_REF = (
    "ngluonghoa/MST/.github/workflows/"
    "mst-cache-v21-staging-fictional-manual.yml@refs/heads/main"
)
SECRETS = (
    "MST_GDRIVE_OAUTH_CLIENT_ID",
    "MST_GDRIVE_OAUTH_CLIENT_SECRET",
    "MST_GDRIVE_OAUTH_REFRESH_TOKEN",
)
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{8,160}\Z")
BOUNDARY = "MST_FAKE_V21_BOUNDARY_STATIC_DATA_ONLY"
READ_LIMIT = 4096


class StagingDenied(ValueError):
    """Errors must not include raw Google responses, private IDs or tokens."""


def guard(env: Mapping[str, str]) -> tuple[str, OAuthSecrets, str]:
    if not isinstance(env, Mapping):
        raise StagingDenied("MST_STAGING_MANUAL_CONTEXT_REQUIRED")
    expected = {
        "GITHUB_REPOSITORY": OWNER_REPO,
        "GITHUB_REPOSITORY_ID": "1450356304",
        "GITHUB_REPOSITORY_OWNER_ID": "353049266",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": EXPECTED_WORKFLOW_REF,
    }
    if any(env.get(key) != value for key, value in expected.items()):
        raise StagingDenied("MST_STAGING_MANUAL_MAIN_EXACT_REPO_GATE_REQUIRED")
    mode = env.get("MST_STAGING_MODE", "probe")
    if mode not in ("probe", "synthetic-write"):
        raise StagingDenied("MST_STAGING_INVALID_MODE")
    # Owner-confirmed prior folder bootstrap variable must NOT be re-enabled.
    if env.get("MST_OAUTH_BOOTSTRAP_ACCEPTED", "") == "true":
        raise StagingDenied("MST_STAGING_BOOTSTRAP_WRITER_MUST_REMAIN_DISABLED")
    if mode == "synthetic-write" and env.get("MST_CACHE_V21_STAGING_WRITE_ACCEPTED") != "true":
        raise StagingDenied("MST_STAGING_SEPARATE_OWNER_WRITE_GATE_REQUIRED")
    if any(not isinstance(env.get(k), str) or not env[k].strip() for k in SECRETS):
        raise StagingDenied("MST_STAGING_COMPLETE_PRIVATE_OAUTH_TRIO_REQUIRED")
    if env.get("MST_GDRIVE_SERVICE_ACCOUNT_JSON"):
        raise StagingDenied("MST_STAGING_WIF_FALLBACK_FORBIDDEN")
    run_id, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"[1-9][0-9]{5,19}", run_id) or not re.fullmatch(r"[1-9][0-9]{0,5}", attempt):
        raise StagingDenied("MST_STAGING_VALID_GITHUB_RUN_IDENTIFIERS_REQUIRED")
    name = f"MST_FAKE_V21_RUN_{run_id}_{attempt}.json"
    return mode, OAuthSecrets(*(env[k] for k in SECRETS)), name


def validate_id(value: Any) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise StagingDenied("MST_STAGING_INVALID_DRIVE_ID")
    return value


def json_response(response: Any, success=(200,)) -> dict:
    try:
        if response.status_code not in success:
            raise StagingDenied("MST_STAGING_GOOGLE_REQUEST_REJECTED")
        payload = response.json()
        if type(payload) is not dict:
            raise StagingDenied("MST_STAGING_GOOGLE_JSON_OBJECT_REQUIRED")
        return payload
    except StagingDenied:
        raise
    except Exception:
        raise StagingDenied("MST_STAGING_GOOGLE_RESPONSE_FAILURE") from None


def google_get_json(session: Any, url: str, params: dict) -> dict:
    try:
        return json_response(session.get(url, params=params, timeout=30))
    except StagingDenied:
        raise
    except Exception:
        raise StagingDenied("MST_STAGING_GOOGLE_GET_FAILURE") from None


def find_one(session: Any, name: str, parent: str | None, mime: str) -> dict | None:
    if name not in (ROOT, CHILD) and not re.fullmatch(r"MST_FAKE_V21_RUN_[1-9][0-9]{5,19}_[1-9][0-9]{0,5}\.json", name):
        raise StagingDenied("MST_STAGING_FIXED_NAME_ONLY")
    parent_part = "'root'" if parent is None else "'" + validate_id(parent) + "'"
    result = google_get_json(session, DRIVE, {
        "q": f"{parent_part} in parents and name = '{name}' and mimeType = '{mime}' and trashed = false",
        "pageSize": 100,
        "fields": "nextPageToken,files(id,name,mimeType,parents,trashed,appProperties)",
    })
    files = result.get("files")
    if type(files) is not list or len(files) > 1 or result.get("nextPageToken"):
        raise StagingDenied("MST_STAGING_AMBIGUOUS_DRIVE_LIST")
    if not files:
        return None
    f = files[0]
    if type(f) is not dict:
        raise StagingDenied("MST_STAGING_INVALID_LISTED_FILE")
    validate_id(f.get("id"))
    if f.get("name") != name or f.get("mimeType") != mime or f.get("trashed") is not False:
        raise StagingDenied("MST_STAGING_LIST_METADATA_DRIFT")
    if parent is not None and f.get("parents") != [parent]:
        raise StagingDenied("MST_STAGING_WRONG_PARENT")
    return f


def get_metadata(session: Any, file_id: str) -> dict:
    return google_get_json(session, DRIVE + "/" + validate_id(file_id), {
        "fields": "id,name,mimeType,parents,trashed,size,md5Checksum,appProperties,version",
    })


def exact_staging(session: Any) -> str:
    root = find_one(session, ROOT, None, FOLDER_MIME)
    if root is None:
        raise StagingDenied("MST_STAGING_EXISTING_APP_ROOT_REQUIRED")
    root_id = root["id"]
    root_detail = get_metadata(session, root_id)
    if (root_detail.get("id") != root_id or root_detail.get("name") != ROOT
            or root_detail.get("mimeType") != FOLDER_MIME
            or root_detail.get("trashed") is not False
            or type(root_detail.get("parents")) is not list
            or len(root_detail["parents"]) != 1):
        raise StagingDenied("MST_STAGING_ROOT_READBACK_DRIFT")
    stage = find_one(session, CHILD, root_id, FOLDER_MIME)
    if stage is None:
        raise StagingDenied("MST_STAGING_EXISTING_CHILD_REQUIRED")
    stage_id = stage["id"]
    stage_detail = get_metadata(session, stage_id)
    if (stage_detail.get("id") != stage_id or stage_detail.get("name") != CHILD
            or stage_detail.get("mimeType") != FOLDER_MIME
            or stage_detail.get("parents") != [root_id]
            or stage_detail.get("trashed") is not False):
        raise StagingDenied("MST_STAGING_CHILD_READBACK_DRIFT")
    return stage_id


def fixed_fixture(name: str) -> bytes:
    if not re.fullmatch(r"MST_FAKE_V21_RUN_[1-9][0-9]{5,19}_[1-9][0-9]{0,5}\.json", name):
        raise StagingDenied("MST_STAGING_INVALID_FICTIONAL_NAME")
    payload = {
        "schema": "mst-staging-fictional-v2.1",
        "fixture_only": True,
        "fictional_integer_samples": [-2, 0, 3],
        "label": "FICTIONAL_INTEGRITY_PROBE",
        "run_file": name,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if not data or len(data) > 1024:
        raise StagingDenied("MST_STAGING_FICTIONAL_BYTES_NOT_BOUNDED")
    return data


def make_multipart(meta: dict, content: bytes) -> bytes:
    """RFC2387 multipart/related for Drive v3 files.create uploadType=multipart."""
    if len(content) > 1024 or b"\r" in content or b"\n" in content or BOUNDARY.encode() in content:
        raise StagingDenied("MST_STAGING_INVALID_MEDIA_BYTES")
    headers = (b"--" + BOUNDARY.encode() +
               b"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n")
    med = (b"\r\n--" + BOUNDARY.encode() +
           b"\r\nContent-Type: application/json\r\n\r\n")
    end = b"\r\n--" + BOUNDARY.encode() + b"--\r\n"
    return headers + json.dumps(meta, sort_keys=True, separators=(",", ":")).encode() + med + content + end


def upload_one(session: Any, stage_id: str, name: str, content: bytes, sha: str) -> str:
    metadata = {
        "name": name,
        "mimeType": "application/json",
        "parents": [validate_id(stage_id)],
        "appProperties": {"mst_fixture_only": "true", "sha256": sha, "schema": "fictional-v21"},
    }
    body = make_multipart(metadata, content)
    try:
        response = session.post(UPLOAD, params={
            "uploadType": "multipart",
            "fields": "id,name,mimeType,parents,trashed,size,md5Checksum,appProperties,version",
        }, headers={"Content-Type": f"multipart/related; boundary={BOUNDARY}"},
            data=body, timeout=30)
        obj = json_response(response, success=(200, 201))
    except StagingDenied:
        raise
    except Exception:
        raise StagingDenied("MST_STAGING_UPLOAD_FAILED_CLOSED") from None
    file_id = validate_id(obj.get("id"))
    verify_metadata(session, file_id, stage_id, name, content, sha)
    return file_id


def verify_metadata(session: Any, file_id: str, stage_id: str, name: str,
                    content: bytes, sha: str) -> None:
    m = get_metadata(session, file_id)
    expected_properties = {"mst_fixture_only": "true", "sha256": sha,
                           "schema": "fictional-v21"}
    if (m.get("id") != file_id or m.get("name") != name
            or m.get("mimeType") != "application/json"
            or m.get("parents") != [stage_id]
            or m.get("trashed") is not False
            or m.get("appProperties") != expected_properties
            or str(m.get("size")) != str(len(content))
            or m.get("md5Checksum") != hashlib.md5(content).hexdigest()):
        raise StagingDenied("MST_STAGING_FILE_METADATA_INTEGRITY_DRIFT")


def two_real_media_reads(session: Any, file_id: str, expected: bytes) -> None:
    url = DRIVE + "/" + validate_id(file_id)
    wanted = hashlib.sha256(expected).digest()
    for _ in range(2):
        try:
            response = session.get(url, params={"alt": "media"}, timeout=30, stream=True)
            try:
                if response.status_code != 200:
                    raise StagingDenied("MST_STAGING_MEDIA_REQUEST_REJECTED")
                if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > READ_LIMIT:
                    raise StagingDenied("MST_STAGING_MEDIA_OVERSIZE")
                content = b"".join(response.iter_content(chunk_size=READ_LIMIT+1))
                if len(content) > READ_LIMIT:
                    raise StagingDenied("MST_STAGING_MEDIA_OVERSIZE")
            finally:
                response.close()
        except StagingDenied:
            raise
        except Exception:
            raise StagingDenied("MST_STAGING_MEDIA_READ_FAILED_CLOSED") from None
        if hashlib.sha256(content).digest() != wanted or content != expected:
            raise StagingDenied("MST_STAGING_TWO_READ_CONTENT_MISMATCH")


def run(session: Any, name: str, mode: str) -> dict:
    stage_id = exact_staging(session)
    if mode == "probe":
        return {
            "status": "MST_STAGING_EXISTING_FOLDER_READ_ONLY_PASS",
            "real_google_drive_metadata_read": True,
            "real_google_drive_file_written": False,
            "synthetic_only": True,
            "market_source_called": False,
            "production_cache_activated": False,
        }
    if mode != "synthetic-write":
        raise StagingDenied("MST_STAGING_INVALID_MODE")
    content = fixed_fixture(name)
    sha = hashlib.sha256(content).hexdigest()
    existing = find_one(session, name, stage_id, "application/json")
    if existing is None:
        file_id = upload_one(session, stage_id, name, content, sha)
    else:
        file_id = existing["id"]
        verify_metadata(session, file_id, stage_id, name, content, sha)
    two_real_media_reads(session, file_id, content)
    verify_metadata(session, file_id, stage_id, name, content, sha)
    return {
        "status": "MST_STAGING_FICTIONAL_JSON_UPLOAD_TWO_REAL_READS_PASS",
        "synthetic_only": True,
        "real_google_drive_file_written_or_preexisting_verified": True,
        "two_distinct_server_media_reads_verified": True,
        "sha256_integrity_verified": True,
        "google_drive_atomic_cas_proven": False,
        "independent_highwater_proven": False,
        "user_created_watchlist_access_proven": False,
        "market_source_called": False,
        "real_ohlcv_downloaded": False,
        "market_cache_written": False,
        "production_cache_activated": False,
    }


def main() -> None:
    mode, secrets, name = guard(os.environ)
    session = _new_authorized_session(secrets)
    print(json.dumps(run(session, name, mode), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except StagingDenied as exc:
        raise SystemExit(str(exc)) from None
