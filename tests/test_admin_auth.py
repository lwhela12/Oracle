"""Owner authorization plus real Authlib OIDC verification with synthetic JWTs."""
import os
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from flask import Flask
from joserfc import jwt
from joserfc.jwk import RSAKey

from admin_auth import GOOGLE_ISSUER
from admin_routes import init_admin

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://owner.example"
SUBJECT = "123456789012345678901"
ENV = {
    "ORACLE_ADMIN_ORIGIN": ORIGIN,
    "ORACLE_ADMIN_GOOGLE_CLIENT_ID": "synthetic-client",
    "ORACLE_ADMIN_GOOGLE_CLIENT_SECRET": "synthetic-oauth-secret",
    "ORACLE_ADMIN_SESSION_SECRET": "synthetic-session-secret-for-tests-only-123456",
    "ORACLE_ADMIN_GOOGLE_SUBJECTS": SUBJECT,
}


class AdminAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = RSAKey.generate_key(2048)
        cls.key.ensure_kid()
        cls.other_key = RSAKey.generate_key(2048)
        cls.other_key.ensure_kid()

    def setUp(self):
        self.env = patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"),
                         static_folder=str(ROOT / "static"))
        self.app.testing = True
        init_admin(self.app)
        self.client = self.app.test_client()
        self.google = self.app.extensions["admin_google"]
        self.metadata = {
            "issuer": GOOGLE_ISSUER,
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "id_token_signing_alg_values_supported": ["RS256"],
            "code_challenge_methods_supported": ["S256"],
        }
        self.patches = [
            patch.object(self.google, "load_server_metadata", return_value=self.metadata),
            patch.object(self.google, "fetch_jwk_set", return_value={"keys": [self.key.as_dict(private=False)]}),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def get(self, path, **kwargs):
        return self.client.get(path, base_url=ORIGIN, **kwargs)

    def post(self, path, **kwargs):
        return self.client.post(path, base_url=ORIGIN, **kwargs)

    def begin_login(self):
        response = self.get("/admin/auth/login?next=https://attacker.example")
        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlsplit(response.location).query)
        self.assertEqual(params["redirect_uri"], [ORIGIN + "/admin/auth/callback"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertTrue(params["code_challenge"][0])
        return params

    def finish_login(self, mutate=None, signing_key=None, callback_state=None):
        params = self.begin_login()
        now = int(time.time())
        claims = {"iss": GOOGLE_ISSUER, "sub": SUBJECT, "aud": "synthetic-client",
                  "iat": now, "exp": now + 1800, "nonce": params["nonce"][0],
                  "email": "owner@example.com", "email_verified": True}
        if mutate:
            mutate(claims)
        key = signing_key or self.key
        encoded = jwt.encode({"alg": "RS256", "kid": key.kid}, claims, key)
        fetch = Mock(return_value={"id_token": encoded, "access_token": "synthetic-token",
                                   "token_type": "Bearer"})
        with patch.object(self.google, "fetch_access_token", fetch):
            response = self.get("/admin/auth/callback", query_string={
                "state": callback_state or params["state"][0], "code": "synthetic-code"})
        return response, fetch, claims

    def test_every_admin_namespace_path_denied_without_auth(self):
        for path in ("/admin", "/admin/", "/admin/api/report", "/admin/api/unknown", "/admin/unknown"):
            with self.subTest(path=path):
                response = self.get(path, headers={"Origin": "https://attacker.example"})
                self.assertEqual(response.status_code, 401)
                self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertNotIn("Access-Control-Allow-Origin", response.headers)
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(self.client.options("/admin/api/report", base_url=ORIGIN).status_code, 401)

    def test_missing_or_insecure_configuration_is_closed(self):
        for key, value in (("ORACLE_ADMIN_SESSION_SECRET", ""),
                           ("ORACLE_ADMIN_GOOGLE_CLIENT_ID", ""),
                           ("ORACLE_ADMIN_ORIGIN", "http://owner.example")):
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                self.assertEqual(self.get("/admin").status_code, 503)
                self.assertEqual(self.get("/admin/auth/login").status_code, 503)
                self.assertEqual(self.get("/admin/api/report").status_code, 401)

    def test_host_and_forwarded_host_do_not_control_callback(self):
        self.assertEqual(self.client.get("/admin/auth/login", base_url="https://attacker.example").status_code, 400)
        response = self.get("/admin/auth/login", headers={"X-Forwarded-Host": "attacker.example"})
        self.assertIn("redirect_uri=https%3A%2F%2Fowner.example%2Fadmin%2Fauth%2Fcallback", response.location)

    def test_valid_google_login_sets_bounded_session_and_secure_cookie(self):
        response, fetch, claims = self.finish_login()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, "/admin")
        self.assertTrue(fetch.call_args.kwargs["code_verifier"])
        self.assertEqual(fetch.call_args.kwargs["redirect_uri"], ORIGIN + "/admin/auth/callback")
        cookie = response.headers["Set-Cookie"]
        for value in ("Secure", "HttpOnly", "SameSite=Lax", "Path=/admin"):
            self.assertIn(value, cookie)
        with self.client.session_transaction("/admin", base_url=ORIGIN) as sess:
            self.assertEqual(set(sess), {"_permanent", "admin_identity", "admin_csrf"})
            self.assertEqual(sess["admin_identity"]["expires_at"], claims["exp"])
            self.assertNotIn("synthetic-token", str(dict(sess)))
        self.assertEqual(self.get("/admin/api/unknown").status_code, 404)

    def test_actual_authlib_rejects_invalid_state_before_token_exchange(self):
        response, fetch, _ = self.finish_login(callback_state="forged-state")
        self.assertEqual(response.status_code, 401)
        fetch.assert_not_called()

    def test_missing_state_nonce_and_token_validation_fail_closed(self):
        variants = {
            "issuer": lambda c: c.update(iss="https://attacker.example"),
            "audience": lambda c: c.update(aud="another-client"),
            "expired": lambda c: c.update(exp=int(time.time()) - 1),
            "wrong_nonce": lambda c: c.update(nonce="wrong"),
            "missing_nonce": lambda c: c.pop("nonce"),
            "nonce_supported_false": lambda c: c.update(nonce="wrong", nonce_supported=False),
        }
        for name, mutation in variants.items():
            with self.subTest(name=name):
                response, _, _ = self.finish_login(mutation)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(self.get("/admin/api/report").status_code, 401)
        response, _, _ = self.finish_login(signing_key=self.other_key)
        self.assertEqual(response.status_code, 401)
        self.begin_login()
        self.assertEqual(self.get("/admin/auth/callback?code=synthetic-code").status_code, 401)

    def test_unauthorized_subject_never_granted_even_matching_email(self):
        response, _, _ = self.finish_login(lambda c: c.update(sub="999999"))
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"999999", response.data)
        self.assertEqual(self.get("/admin/api/report").status_code, 401)
        with patch.dict(os.environ, {"ORACLE_ADMIN_EXPECTED_EMAIL": "other@example.com"}):
            response, _, _ = self.finish_login(lambda c: c.update(sub="888888"))
        self.assertNotIn(b"888888", response.data)

    def test_allowlist_revocation_and_session_expiry_and_issuer(self):
        self.finish_login()
        with patch.dict(os.environ, {"ORACLE_ADMIN_GOOGLE_SUBJECTS": ""}):
            self.assertEqual(self.get("/admin/api/report").status_code, 401)
        for field, value in (("expires_at", time.time() - 1), ("issuer", "https://attacker.example"),
                             ("subject", "999999"), ("issued_at", time.time() + 100)):
            self.finish_login()
            with self.client.session_transaction("/admin", base_url=ORIGIN) as sess:
                sess["admin_identity"] = {**sess["admin_identity"], field: value}
            self.assertEqual(self.get("/admin/api/report").status_code, 401)

    def test_long_lived_provider_token_is_capped_to_one_hour(self):
        response, _, _ = self.finish_login(lambda c: c.update(exp=int(time.time()) + 7200))
        self.assertEqual(response.status_code, 303)
        with self.client.session_transaction("/admin", base_url=ORIGIN) as sess:
            identity = dict(sess["admin_identity"])
        self.assertEqual(identity["expires_at"] - identity["issued_at"], 3600)
        response = self.get("/admin/api/unknown")
        self.assertNotIn("Set-Cookie", response.headers)

    def test_forged_cookie_denied(self):
        self.client.set_cookie("oracle_admin", "forged.payload.signature", domain="owner.example", path="/admin")
        self.assertEqual(self.get("/admin/api/report").status_code, 401)

    def test_logout_requires_post_and_csrf(self):
        self.finish_login()
        self.assertEqual(self.get("/admin/auth/logout").status_code, 405)
        self.assertEqual(self.post("/admin/auth/logout").status_code, 403)
        self.assertEqual(self.post("/admin/auth/logout", data={"csrf_token": "wrong"}).status_code, 403)
        with self.client.session_transaction("/admin", base_url=ORIGIN) as sess:
            csrf = sess["admin_csrf"]
        self.assertEqual(self.post("/admin/auth/logout", data={"csrf_token": csrf}).status_code, 303)
        self.assertEqual(self.get("/admin/api/report").status_code, 401)

    def test_period_validation_precedes_database_and_errors_are_sanitized(self):
        self.finish_login()
        report = Mock()
        with patch.dict("sys.modules", {"dashboard_reporting": types.SimpleNamespace(build_report=report)}):
            for query in ("period=all", "period=7d&period=30d"):
                self.assertEqual(self.get("/admin/api/report?" + query).status_code, 400)
            report.assert_not_called()
            report.return_value = {"aggregate": 3}
            response = self.get("/admin/api/report?period=today")
            self.assertEqual(response.json, {"aggregate": 3})
            report.assert_called_once_with("today")
            report.side_effect = RuntimeError("postgresql://private-secret")
            response = self.get("/admin/api/report")
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b"private-secret", response.data)
            self.assertEqual(response.json["error"], "report_unavailable")

    def test_local_http_requires_explicit_loopback_and_is_disabled_on_vercel(self):
        from admin_auth import configured_origin
        with patch.dict(os.environ, {"ORACLE_ADMIN_ORIGIN": "http://127.0.0.1:5001", "ORACLE_ADMIN_LOCAL_HTTP": "1"}):
            self.assertEqual(configured_origin(), "http://127.0.0.1:5001")
            with patch.dict(os.environ, {"VERCEL_ENV": "preview"}):
                self.assertIsNone(configured_origin())
        with patch.dict(os.environ, {"ORACLE_ADMIN_ORIGIN": "http://127.0.0.1:5001"}):
            self.assertIsNone(configured_origin())
        for origin in ("https://owner.example/path", "https://user:password@owner.example", "https://owner.example?foo=x"):
            with patch.dict(os.environ, {"ORACLE_ADMIN_ORIGIN": origin}):
                self.assertIsNone(configured_origin())

    def test_actual_app_cors_preserves_reading_api_and_denies_admin(self):
        from app import app
        client = app.test_client()
        headers = {"Origin": "https://reader.example", "Access-Control-Request-Method": "POST"}
        for path in ("/chat", "/chat/stream", "/session/clear", "/init", "/analytics/visit"):
            response = client.options(path, base_url=ORIGIN, headers=headers)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "https://reader.example")
        for path in ("/admin", "/admin/api/report", "/admin/api/unknown", "/admin/assets/admin.css"):
            response = client.get(path, base_url=ORIGIN, headers=headers)
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
            self.assertIn("no-store", response.headers["Cache-Control"])
            response.close()

    def test_authlib_failure_is_not_exposed_or_logged(self):
        self.begin_login()
        with patch.object(self.google, "authorize_access_token", side_effect=RuntimeError("sensitive-provider-error")):
            response = self.get("/admin/auth/callback?state=synthetic")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(b"sensitive-provider-error", response.data)


if __name__ == "__main__":
    unittest.main()
