"""Private aggregate dashboard routes, with a default-deny namespace guard."""
import hmac
import os
import secrets
import time

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, send_from_directory, session
from admin_auth import (GOOGLE_ISSUER, auth_ready, configured_origin, establish_owner,
                        init_auth, owner_authenticated, valid_logout_csrf)

admin = Blueprint("admin", __name__, url_prefix="/admin")
PUBLIC_PATHS = {"/admin/auth/login", "/admin/auth/callback",
                "/admin/assets/admin.css", "/admin/assets/admin.js"}


def login_page(message=None, status=401, verified_subject=None):
    return render_template("admin_login.html", configured=auth_ready(), message=message,
                           verified_subject=verified_subject), status


def init_admin(app):
    init_auth(app)
    app.register_blueprint(admin)

    @app.before_request
    def guard_admin_namespace():
        if request.path != "/admin" and not request.path.startswith("/admin/"):
            return None
        origin = configured_origin()
        if origin and request.host_url.rstrip("/") != origin:
            return jsonify(error="invalid_admin_origin"), 400
        if request.path in PUBLIC_PATHS:
            return None
        if not owner_authenticated():
            if request.path.startswith("/admin/api/"):
                return jsonify(error="authentication_required"), 401
            return login_page(status=401 if auth_ready() else 503)
        return None

    @app.after_request
    def admin_response_headers(response):
        if request.path == "/admin" or request.path.startswith("/admin/"):
            response.headers["Cache-Control"] = "no-store, private, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            )
            for name in list(response.headers.keys()):
                if name.lower().startswith("access-control-"):
                    del response.headers[name]
        return response


@admin.get("")
@admin.get("/")
def overview():
    return render_template("admin.html", csrf_token=session["admin_csrf"])


@admin.get("/assets/<filename>")
def assets(filename):
    if filename not in ("admin.css", "admin.js"):
        abort(404)
    return send_from_directory(current_app.static_folder, filename)


@admin.get("/auth/login")
def login():
    if not auth_ready():
        return login_page("Owner sign-in has not been configured yet.", 503)
    session.clear()
    nonce = secrets.token_urlsafe(32)
    session["admin_login_nonce"] = nonce
    session["admin_login_started"] = time.time()
    try:
        return current_app.extensions["admin_google"].authorize_redirect(
            configured_origin() + "/admin/auth/callback", nonce=nonce,
            prompt="select_account", max_age=0,
        )
    except Exception:
        session.clear()
        return login_page("Google sign-in is temporarily unavailable. Please try again.", 503)


@admin.get("/auth/callback")
def callback():
    if not auth_ready():
        return login_page("Owner sign-in has not been configured yet.", 503)
    try:
        nonce = session.get("admin_login_nonce")
        started = session.get("admin_login_started", 0)
        if not nonce or not 0 <= time.time() - started < 600:
            raise ValueError("invalid_login")
        # Authlib consumes state, binds the authorization code to PKCE and verifies
        # signature, issuer, audience, expiration, and nonce using Google discovery.
        token = current_app.extensions["admin_google"].authorize_access_token(leeway=0)
        claims = token.get("userinfo")
        if (not claims or claims.get("iss") != GOOGLE_ISSUER
                or not isinstance(claims.get("nonce"), str)
                or not hmac.compare_digest(claims["nonce"], nonce)
                or not isinstance(claims.get("sub"), str)):
            raise ValueError("invalid_identity")
        session.clear()
        if establish_owner(claims):
            return redirect("/admin", code=303)
        # Enrollment never grants access. Only this browser sees its own verified
        # immutable subject; identities and provider errors are never logged.
        return login_page("This Google account does not have owner access.", 403,
                          verified_subject=(claims["sub"] if (
                              not os.environ.get("ORACLE_ADMIN_EXPECTED_EMAIL")
                              or (claims.get("email_verified") is True and
                                  claims.get("email", "").lower() == os.environ["ORACLE_ADMIN_EXPECTED_EMAIL"].lower())
                          ) else None))
    except Exception:
        session.clear()
        return login_page("Sign-in could not be verified. Please start again.", 401)


@admin.post("/auth/logout")
def logout():
    if not valid_logout_csrf(request.form.get("csrf_token")):
        return jsonify(error="invalid_csrf"), 403
    session.clear()
    return redirect("/admin", code=303)


@admin.get("/api/report")
def report():
    period = request.args.get("period", "7d")
    if period not in ("today", "7d", "30d") or len(request.args.getlist("period")) > 1:
        return jsonify(error="invalid_period"), 400
    try:
        from dashboard_reporting import build_report
        return jsonify(build_report(period))
    except Exception:
        # Never return database messages or present an outage as zero usage.
        return jsonify(error="report_unavailable",
                       message="Reporting is temporarily unavailable. Please try again."), 503
