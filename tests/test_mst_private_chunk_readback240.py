"""§240 offline in-memory HTTP simulation, never real Drive or market calls."""
from __future__ import annotations

from dataclasses import replace
from hashlib import md5, sha256
import json
import unittest

from scripts import mst_private_chunk_readback240 as c

PARENT = "MSTprivateCHUNKSfolder000001"
FILE = "MSTprivateCHUNKfile000001"
RUN = "44500001234"


def env(**changes):
    base = {
        **c.CONTEXT,
        "GITHUB_RUN_ID": RUN,
        "MST_PRIVATE_CHUNKS_FOLDER_ID": PARENT,
        "MST_DNSE_SOURCE_RIGHTS_CONFIRMED": "true",
        "MST_SOURCE_PROVIDER": "DNSE",
        "MST_SOURCE_SYMBOL": "FPT",
        "MST_SOURCE_TF": "D1",
    }
    base.update(changes)
    return base


def payload(*, provider="DNSE", symbol="FPT", tf="D1", **changes):
    body = {
        "schema": c.SCHEMA, "project": "MST",
        "provider": provider, "symbol": symbol,
        "native_tf": tf, "eligible_for_signals": False,
        "raw_native": {"FICTIONAL_ONLY": [1, 2, 3]},
    }
    body.update(changes)
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


class Reply:
    def __init__(self, data=None, *, status=200, media=None):
        self.status_code = status
        self._data = data
        self.content = media

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, body=None):
        self.raw = payload() if body is None else body
        self.digest = sha256(self.raw).hexdigest()
        self.name = c._candidate_name("DNSE", "FPT", "D1", RUN, self.digest)
        self.calls = []
        self.uploaded = False
        self.parent_shared = False
        self.file_shared = False
        self.incomplete = False
        self.preexisting = False
        self.postduplicate = False
        self.tamper_second = False
        self.corrupt_md5 = False
        self.change_version = False
        self.fail_upload = False
        self.media_reads = 0
        self.metadata_reads = 0

    def get(self, url, *, params, timeout, allow_redirects):
        self.calls.append(("GET", url, params))
        assert not allow_redirects
        assert timeout in (25, 35)
        if url == c.FILES and "q" in params:
            if self.incomplete:
                return Reply({"files": [], "incompleteSearch": True})
            if not self.uploaded:
                entries = [self._listed()] if self.preexisting else []
            else:
                entries = ([self._listed(), self._listed()]
                           if self.postduplicate else [self._listed()])
            return Reply({"files": entries, "incompleteSearch": False})
        if url == c.FILES + "/" + PARENT:
            return Reply({
                "id": PARENT, "name": "CHUNKS",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["MSTOAuthRoot0001"], "trashed": False,
                "shared": self.parent_shared, "ownedByMe": True,
                "isAppAuthorized": True,
            })
        if url == c.FILES + "/" + FILE:
            if params == {"alt": "media"}:
                self.media_reads += 1
                raw = (b"corrupted" if self.tamper_second
                       and self.media_reads == 2 else self.raw)
                return Reply(media=raw)
            self.metadata_reads += 1
            return Reply({
                "id": FILE, "name": self.name, "mimeType": c.MIME,
                "parents": [PARENT], "trashed": False,
                "shared": self.file_shared, "ownedByMe": True,
                "isAppAuthorized": True,
                "size": str(len(self.raw)),
                "md5Checksum": ("0"*32 if self.corrupt_md5
                                else md5(self.raw).hexdigest()),
                "version": ("2" if self.change_version
                            and self.metadata_reads >= 2 else "1"),
                "appProperties": self._props(),
            })
        raise AssertionError("Unexpected GET URL")

    def post(self, url, *, params, headers, data, timeout, allow_redirects):
        self.calls.append(("POST", url, params))
        assert url == c.UPLOAD
        assert params["uploadType"] == "multipart"
        assert timeout == 35
        assert not allow_redirects
        assert headers["Content-Type"].startswith("multipart/related; boundary=mstprivate")
        assert b"Content-Type: application/json; charset=UTF-8" in data
        assert b"Content-Type: application/json\r\n\r\n" in data
        assert self.raw in data
        assert self.digest.encode() in data
        assert self.name.encode() in data
        if self.fail_upload:
            return Reply({"error": "secret HTTP response should never be logged"}, status=403)
        self.uploaded = True
        return Reply({
            "id": FILE, "name": self.name, "mimeType": c.MIME,
            "parents": [PARENT], "trashed": False,
        }, status=200)

    def _listed(self):
        return {"id": FILE, "name": self.name,
                "mimeType": c.MIME, "parents": [PARENT], "trashed": False}

    def _props(self):
        return {
            "mst_unpublished": "true",
            "source_sha256": self.digest,
            "source_provider": "DNSE",
            "source_symbol": "FPT",
            "source_native_tf": "D1",
            "source_run_id": RUN,
            "source_rights_independently_attested": "false",
            "source_closed_bar_attested": "false",
            "source_signal_eligible": "false",
        }


def attempt(sess=None, owner=None, raw=None):
    instance = FakeSession() if sess is None else sess
    result = c.upload_private_unpublished_chunk(
        instance, env() if owner is None else owner,
        PARENT, instance.raw if raw is None else raw,
    )
    return result, instance


class ChunkReadback240Tests(unittest.TestCase):
    def test_good_two_readback_receipt_stays_unpublished_and_private(self):
        result, s = attempt()
        self.assertEqual(s.media_reads, 2)
        self.assertEqual(s.metadata_reads, 3)
        self.assertEqual(result.bytes_verified, len(payload()))
        self.assertEqual(result.sha256, sha256(payload()).hexdigest())
        self.assertEqual(result.file_id, FILE)
        self.assertEqual(result.distinct_readbacks_verified, 2)
        pub = result.public_receipt()
        self.assertIs(pub["market_cache_promoted"], False)
        self.assertIs(pub["source_rights_independently_attested"], False)
        self.assertIs(pub["independent_signed_monotone_cas_verified"], False)
        self.assertIs(pub["signals_or_trade_eligible"], False)
        for term in (FILE, PARENT, result.sha256, "FICTIONAL_ONLY"):
            self.assertNotIn(term, json.dumps(pub))
        self.assertEqual(
            [x[0] for x in s.calls],
            ["GET", "GET", "POST", "GET", "GET", "GET",
             "GET", "GET", "GET"],
        )

    def test_no_private_rights_context_no_network(self):
        for key, value in (
            ("GITHUB_REPOSITORY", "bad/MST"),
            ("GITHUB_REPOSITORY_ID", "0"),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_WORKFLOW_REF", "other"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("MST_CHUNK_STAGE_CONFIRM", "NO"),
            ("MST_PRIVATE_CHUNKS_WRITE_ACCEPTED", "false"),
            ("MST_SOURCE_RETENTION_RIGHTS_CONFIRMED", "false"),
            ("MST_DNSE_SOURCE_RIGHTS_CONFIRMED", "false"),
            ("MST_SOURCE_TF", "H4"),
            ("MST_SOURCE_PROVIDER", "SSI"),
            ("MST_SOURCE_SYMBOL", "HPG"),
            ("MST_PRIVATE_CHUNKS_FOLDER_ID", "wrongParent0001"),
            ("GITHUB_RUN_ID", "x"),
        ):
            with self.subTest(key=key):
                session = FakeSession()
                with self.assertRaises(c.ChunkDenied):
                    attempt(session, env(**{key: value}))
                self.assertEqual(session.calls, [])

    def test_no_root_or_shared_folder_permission(self):
        for is_shared in (True,):
            s = FakeSession()
            s.parent_shared = is_shared
            with self.assertRaisesRegex(c.ChunkDenied, "PRIVATE_CHUNKS_SCOPE"):
                attempt(s)
            self.assertFalse(s.uploaded)

    def test_deny_duplicate_pre_upload_and_post_upload(self):
        s = FakeSession()
        s.preexisting = True
        with self.assertRaisesRegex(c.ChunkDenied, "EXISTING_CHUNK_NAME"):
            attempt(s)
        self.assertFalse(s.uploaded)
        s = FakeSession()
        s.postduplicate = True
        with self.assertRaisesRegex(c.ChunkDenied, "CHUNK_CENSUS_AMBIGUOUS"):
            attempt(s)
        self.assertTrue(s.uploaded)

    def test_never_infer_absence_from_incomplete_search(self):
        s = FakeSession()
        s.incomplete = True
        with self.assertRaisesRegex(c.ChunkDenied, "CENSUS_AMBIGUOUS"):
            attempt(s)
        self.assertFalse(s.uploaded)

    def test_reject_second_media_corruption(self):
        s = FakeSession()
        s.tamper_second = True
        with self.assertRaisesRegex(c.ChunkDenied, "MEDIA_READBACK_MISMATCH"):
            attempt(s)
        self.assertEqual(s.media_reads, 2)
        self.assertTrue(s.uploaded)

    def test_reject_version_change_after_first_read(self):
        s = FakeSession()
        s.change_version = True
        with self.assertRaisesRegex(c.ChunkDenied, "VERSION_DRIFT"):
            attempt(s)
        self.assertTrue(s.uploaded)

    def test_reject_wrong_google_md5_even_with_correct_sha(self):
        s = FakeSession()
        s.corrupt_md5 = True
        with self.assertRaisesRegex(c.ChunkDenied, "METADATA_NOT_PRIVATE"):
            attempt(s)

    def test_reject_shared_chunk(self):
        s = FakeSession()
        s.file_shared = True
        with self.assertRaisesRegex(c.ChunkDenied, "METADATA_NOT_PRIVATE"):
            attempt(s)

    def test_http_non200_does_not_leak_source_server_response(self):
        s = FakeSession()
        s.fail_upload = True
        with self.assertRaisesRegex(c.ChunkDenied, "^MST_240_DRIVE_HTTP_DENIED$"):
            attempt(s)
        self.assertFalse(s.uploaded)

    def test_unexpected_transport_exception_static(self):
        class Broken:
            def get(self, *args, **kwargs):
                raise RuntimeError("LEAKED_REAL_SECRET_STRING")
        with self.assertRaisesRegex(c.ChunkDenied, "^MST_240_DRIVE_GET_FAILED$"):
            c.upload_private_unpublished_chunk(Broken(), env(), PARENT, payload())

    def test_noncanonical_or_ambiguous_source_json_rejected(self):
        cases = (
            b"not json at all",
            b"\xff" * 20,
            b'{"schema":"a","schema":"b","project":"MST"}',
            b'{"value":NaN,"schema":"bad"}',
            payload(eligible_for_signals=True),
            payload(schema="unknown"),
            payload(raw_native={}),
            payload(raw_native=[]),
            payload(provider="UNKNOWN"),
            payload(tf="H4"),
            payload(raw_native="secret"),
            payload(extra_key="bad"),
        )
        for raw in cases:
            with self.subTest(raw=raw[:25]):
                s = FakeSession()
                with self.assertRaises(c.ChunkDenied):
                    attempt(s, raw=raw)
                self.assertFalse(s.calls)

    def test_raw_sha_content_address_changes_with_revision(self):
        first = payload()
        revised = payload(raw_native={"FICTIONAL_ONLY": [1, 2, 4]})
        self.assertNotEqual(sha256(first).hexdigest(), sha256(revised).hexdigest())
        a = c._candidate_name("DNSE", "FPT", "D1", RUN, sha256(first).hexdigest())
        b = c._candidate_name("DNSE", "FPT", "D1", RUN, sha256(revised).hexdigest())
        self.assertNotEqual(a, b)

    def test_public_receipt_cannot_relabel_as_market_cache(self):
        result, _ = attempt()
        for key in (
            "source_rights_independently_attested",
            "venue_closed_bar_attested",
            "signed_cas_verified",
            "published_to_market_cache",
            "signals_or_trade_eligible",
        ):
            with self.subTest(key=key), self.assertRaises(c.ChunkDenied):
                replace(result, **{key: True})

    def test_no_runtime_io_before_explicit_guard(self):
        for raw in (b"", "not bytes", b"{" * (c.MAX_BYTES+1)):
            s = FakeSession()
            with self.subTest(type=type(raw).__name__), self.assertRaises(c.ChunkDenied):
                attempt(s, raw=raw)
            self.assertFalse(s.calls)

    def test_probe_not_a_publisher_or_independent_cas(self):
        import inspect
        s = inspect.getsource(c)
        self.assertNotIn("files.update", s)
        self.assertNotIn("delete(", s)
        self.assertNotIn("time.sleep", s)
        self.assertNotIn("print(", s)
        self.assertNotIn("MST_LIVE_TRADE", s)


if __name__ == "__main__":
    unittest.main()
