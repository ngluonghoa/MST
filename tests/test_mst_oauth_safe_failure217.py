"""§217 isolated fictional OAuth failure classification; never print secrets."""
import unittest

from scripts import mst_oauth_manual_drive_bootstrap as m
from test_mst_oauth_manual_drive_bootstrap import FakeResponse


RefreshError = type("RefreshError", (Exception,), {"__module__": "google.auth.exceptions"})
TransportError = type("TransportError", (Exception,), {"__module__": "google.auth.exceptions"})
ConnectTimeout = type("ConnectTimeout", (Exception,), {"__module__": "requests.exceptions"})


class RaisingSession:
    def __init__(self, error):
        self.error = error
    def get(self, url, *, params, timeout):
        raise self.error
    def post(self, url, *, params, json, timeout):
        raise self.error


class StatusSession:
    def __init__(self, status):
        self.status = status
    def get(self, url, *, params, timeout):
        return FakeResponse({"sensitive": "SECRET"}, status=self.status)


def request(session, method="GET"):
    return m._get_response(session, method, m.DRIVE_FILES, params={})


class OAuthSafeFailure217Tests(unittest.TestCase):
    def test_strict_allowlisted_invalid_grant_never_leaks_payload_or_token(self):
        e = RefreshError("SECRET_TOKEN_DO_NOT_PRINT",
                         {"error": "invalid_grant",
                          "error_description": "SECRET_USER_DO_NOT_PRINT",
                          "refresh_token": "SECRET_REFRESH"})
        classification = m.classify_safe_oauth_failure217(e)
        self.assertEqual(classification, "MST_217_OAUTH_INVALID_GRANT_REAUTHORIZE_REQUIRED")
        self.assertNotIn("SECRET_", classification)
        with self.assertRaisesRegex(m.BootstrapDenied, "MST_217_OAUTH_INVALID_GRANT") as c:
            request(RaisingSession(e))
        self.assertNotIn("SECRET_", str(c.exception))

    def test_invalid_client_and_unauthorized_client_distinct(self):
        for error, expected in (
            ("invalid_client", "MST_217_OAUTH_INVALID_CLIENT_CONFIGURATION"),
            ("unauthorized_client", "MST_217_OAUTH_UNAUTHORIZED_CLIENT"),
        ):
            with self.subTest(error=error):
                e=RefreshError("SECRET",{"error":error,"client_secret":"NEVER_PRINT"})
                self.assertEqual(m.classify_safe_oauth_failure217(e), expected)

    def test_unknown_refresh_error_is_redacted_and_fails_closed(self):
        e=RefreshError("SECRET_REFRESH_TEXT",{"error":"example_new_code",
                                              "access_token":"SECRET_TOKEN"})
        with self.assertRaisesRegex(m.BootstrapDenied,
                                    "MST_217_OAUTH_REFRESH_REJECTED_UNCLASSIFIED") as c:
            request(RaisingSession(e))
        self.assertNotIn("SECRET",str(c.exception))

    def test_missing_structured_refresh_error_never_sniffs_message(self):
        e=RefreshError("invalid_grant SECRET_REVOKED")
        self.assertEqual(m.classify_safe_oauth_failure217(e),
                         "MST_217_OAUTH_REFRESH_REJECTED_UNCLASSIFIED")
        e=RefreshError("invalid_grant", {"error": 123, "secret": "LEAK"})
        self.assertEqual(m.classify_safe_oauth_failure217(e),
                         "MST_217_OAUTH_REFRESH_REJECTED_UNCLASSIFIED")

    def test_transport_and_network_errors_static_only(self):
        for error, expected in (
            (TransportError("SECRET_PROXY"),"MST_217_OAUTH_TRANSPORT_ERROR"),
            (ConnectTimeout("SECRET_URL"),"MST_217_OAUTH_NETWORK_OR_TLS_ERROR"),
        ):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(m.classify_safe_oauth_failure217(error),expected)
                with self.assertRaisesRegex(m.BootstrapDenied,expected) as c:
                    request(RaisingSession(error))
                self.assertNotIn("SECRET",str(c.exception))

    def test_unrecognized_exception_still_generic_not_revealed(self):
        with self.assertRaisesRegex(m.BootstrapDenied,
                                    "MST_OAUTH_DRIVE_REQUEST_FAILED_CLOSED") as c:
            request(RaisingSession(RuntimeError("SECRET_USER_PRIVATE")))
        self.assertNotIn("SECRET",str(c.exception))

    def test_http_errors_static_status_never_body_or_url(self):
        for status, code in (
            (401,"MST_217_DRIVE_HTTP_401_UNAUTHORIZED"),
            (403,"MST_217_DRIVE_HTTP_403_FORBIDDEN"),
            (429,"MST_217_DRIVE_HTTP_429_RATE_LIMITED"),
            (408,"MST_217_DRIVE_HTTP_TRANSIENT_FAILURE"),
            (500,"MST_217_DRIVE_HTTP_TRANSIENT_FAILURE"),
            (503,"MST_217_DRIVE_HTTP_TRANSIENT_FAILURE"),
            (404,"MST_OAUTH_DRIVE_REQUEST_REJECTED"),
        ):
            with self.subTest(status=status):
                with self.assertRaisesRegex(m.BootstrapDenied,code) as c:
                    request(StatusSession(status))
                self.assertNotIn("SECRET",str(c.exception))

    def test_post_does_not_retry_or_echo_refresh_token(self):
        e=RefreshError("SECRET",{"error":"invalid_grant","token":"SECRET"})
        class OnceSession(RaisingSession):
            calls=0
            def post(self,url,*,params,json,timeout):
                self.calls+=1
                return super().post(url,params=params,json=json,timeout=timeout)
        s=OnceSession(e)
        with self.assertRaises(m.BootstrapDenied):
            request(s, method="POST")
        self.assertEqual(s.calls,1)

    def test_no_oauth_proof_claims_in_failure_code(self):
        for error in (
            RefreshError("SECRET",{"error":"invalid_grant"}),
            RefreshError("SECRET",{"error":"invalid_client"}),
            TransportError("SECRET"),
            ConnectTimeout("SECRET"),
        ):
            result=m.classify_safe_oauth_failure217(error)
            self.assertTrue(result.startswith("MST_217_"))
            self.assertNotIn("PASS",result)
            self.assertNotIn("VERIFIED",result)
            self.assertNotIn("CERTIFIED",result)

    def test_other_module_spoof_of_exception_name_not_classified(self):
        Fake = type("RefreshError", (Exception,), {"__module__": "other_module"})
        self.assertEqual(m.classify_safe_oauth_failure217(Fake("invalid_grant")),
                         "MST_OAUTH_DRIVE_REQUEST_FAILED_CLOSED")


if __name__=="__main__":
    unittest.main()
