"""Google OIDC owner authentication; no provider tokens or emails in sessions."""
import hmac
import math
import os
import re
import secrets
import time
from datetime import timedelta
from urllib.parse import urlsplit

from authlib.integrations.flask_client import OAuth
from flask import current_app, session

GOOGLE_ISSUER = "https://accounts.google.com"
SESSION_SECONDS = 3600


def configured_origin():
    value = os.environ.get("ORACLE_ADMIN_ORIGIN", "").strip()
    try:
        parts = urlsplit(value)
        valid = (parts.hostname and not parts.username and not parts.password
                 and parts.path in ("", "/") and not parts.query and not parts.fragment)
        local = (parts.scheme == "http" and parts.hostname == "127.0.0.1"
                 and os.environ.get("ORACLE_ADMIN_LOCAL_HTTP") == "1"
                 and not os.environ.get("VERCEL") and not os.environ.get("VERCEL_ENV"))
        if not valid or (parts.scheme != "https" and not local):
            return None
        # Accessing port validates malformed port values.
        _ = parts.port
        return f"{parts.scheme}://{parts.netloc}"
    except ValueError:
        return None


def subjects():
    """Read on every request so allowlist removal also revokes existing sessions."""
    values = os.environ.get("ORACLE_ADMIN_GOOGLE_SUBJECTS", "").split(",")
    return {value.strip() for value in values if re.fullmatch(r"[0-9]{1,255}", value.strip())}


def auth_ready():
    secret = os.environ.get("ORACLE_ADMIN_SESSION_SECRET", "")
    return bool(configured_origin() and len(secret) >= 32
                and secret == current_app.secret_key
                and os.environ.get("ORACLE_ADMIN_GOOGLE_CLIENT_ID")
                and os.environ.get("ORACLE_ADMIN_GOOGLE_CLIENT_SECRET")
                and current_app.extensions.get("admin_google"))


def init_auth(app):
    secret = os.environ.get("ORACLE_ADMIN_SESSION_SECRET", "")
    origin = configured_origin()
    app.config.update(
        SECRET_KEY=secret if len(secret) >= 32 else None,
        SESSION_COOKIE_NAME="oracle_admin",
        SESSION_COOKIE_PATH="/admin",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=not (origin and origin.startswith("http://127.0.0.1")),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_SECONDS),
    )
    oauth = OAuth(app)
    app.extensions["admin_google"] = oauth.register(
        name="google",
        client_id=os.environ.get("ORACLE_ADMIN_GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("ORACLE_ADMIN_GOOGLE_CLIENT_SECRET", ""),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email", "code_challenge_method": "S256", "timeout": 10},
    )


def owner_authenticated():
    if not auth_ready():
        return False
    identity = session.get("admin_identity")
    if not isinstance(identity, dict):
        return False
    try:
        now = time.time()
        issued = float(identity["issued_at"])
        expires = float(identity["expires_at"])
        return (math.isfinite(issued) and math.isfinite(expires)
                and 0 <= now - issued < SESSION_SECONDS and issued < expires and now < expires
                and expires <= issued + SESSION_SECONDS
                and identity.get("issuer") == GOOGLE_ISSUER
                and identity.get("subject") in subjects())
    except (KeyError, TypeError, ValueError):
        return False


def establish_owner(claims):
    """Only call with Authlib-verified ID-token claims, never userinfo responses."""
    now = time.time()
    try:
        expires = min(float(claims["exp"]), now + SESSION_SECONDS)
        if not math.isfinite(expires) or expires <= now:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    if claims.get("iss") != GOOGLE_ISSUER or claims.get("sub") not in subjects():
        return False
    session.clear()
    session.permanent = True
    session["admin_identity"] = {
        "issuer": GOOGLE_ISSUER, "subject": claims["sub"],
        "issued_at": now, "expires_at": expires,
    }
    session["admin_csrf"] = secrets.token_urlsafe(32)
    return True


def valid_logout_csrf(value):
    expected = session.get("admin_csrf")
    return (isinstance(value, str) and isinstance(expected, str)
            and bool(expected) and hmac.compare_digest(value, expected))
