"""PostgreSQL configuration for Oracle's server-side data stores.

This module never opens a connection at import time and never logs connection
strings.  Schema changes are performed explicitly through Alembic.
"""

from dataclasses import dataclass
import ipaddress
import math
import os
from typing import Optional

from psycopg.conninfo import conninfo_to_dict


_TLS_ENVIRONMENTS = frozenset({"production", "preview"})
_KNOWN_ENVIRONMENTS = frozenset(
    {"local", "development", "test", "preview", "staging", "production"}
)


class DatabaseConfigurationError(ValueError):
    """A safe, content-free database configuration failure."""

    def __init__(self, code: str = "database_configuration_error") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DatabaseSettings:
    database_url: str
    environment: str

    def connect_kwargs(self, timeout_seconds: float) -> dict:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise DatabaseConfigurationError("invalid_database_timeout")
        # libpq accepts whole seconds for connect_timeout.  The caller's
        # asyncio deadline is the authoritative sub-second bound.
        return {"connect_timeout": max(1, math.ceil(timeout_seconds))}

    def __repr__(self) -> str:
        return f"DatabaseSettings(database_url='<redacted>', environment={self.environment!r})"


def runtime_environment() -> str:
    value = os.getenv("VERCEL_ENV") or "local"
    if value not in _KNOWN_ENVIRONMENTS:
        raise DatabaseConfigurationError("invalid_runtime_environment")
    return value


def _validate_url(database_url: str, environment: str, *, bounded_runtime: bool) -> None:
    try:
        fields = conninfo_to_dict(database_url)
    except Exception:
        raise DatabaseConfigurationError("invalid_database_url") from None
    if not fields.get("dbname"):
        raise DatabaseConfigurationError("invalid_database_url")
    if environment in _TLS_ENVIRONMENTS and fields.get("sslmode") != "verify-full":
        raise DatabaseConfigurationError("database_tls_required")
    if bounded_runtime:
        if fields.get("service"):
            raise DatabaseConfigurationError("runtime_database_address_required")
        host = fields.get("host")
        hostaddr = fields.get("hostaddr")
        port = fields.get("port")
        if not host and not hostaddr:
            raise DatabaseConfigurationError("runtime_database_address_required")
        if (host and "," in host) or (hostaddr and "," in hostaddr):
            raise DatabaseConfigurationError("runtime_database_address_required")
        if port and (not port.isdigit() or not 1 <= int(port) <= 65535):
            raise DatabaseConfigurationError("runtime_database_address_required")
        if host and not host.startswith("/"):
            try:
                ipaddress.ip_address(host)
            except ValueError:
                if not hostaddr:
                    raise DatabaseConfigurationError("runtime_database_address_required")
        if hostaddr:
            try:
                ipaddress.ip_address(hostaddr)
            except ValueError:
                raise DatabaseConfigurationError("runtime_database_address_required") from None


def settings_from_env() -> Optional[DatabaseSettings]:
    """Return runtime settings, or ``None`` when database delivery is disabled."""

    database_url = os.getenv("ORACLE_DATABASE_URL")
    if not database_url:
        return None
    runtime = runtime_environment()
    configured = os.getenv("ORACLE_DATABASE_ENVIRONMENT")
    if configured not in _KNOWN_ENVIRONMENTS or configured != runtime:
        raise DatabaseConfigurationError("database_environment_mismatch")
    _validate_url(database_url, configured, bounded_runtime=True)
    return DatabaseSettings(database_url=database_url, environment=configured)


def migration_database_url_from_env() -> str:
    """Read and validate the separate administrative migration connection."""

    database_url = os.getenv("ORACLE_MIGRATION_DATABASE_URL")
    if not database_url:
        raise DatabaseConfigurationError("migration_database_url_required")
    runtime = runtime_environment()
    configured = os.getenv("ORACLE_DATABASE_ENVIRONMENT")
    if configured not in _KNOWN_ENVIRONMENTS or configured != runtime:
        raise DatabaseConfigurationError("database_environment_mismatch")
    _validate_url(database_url, configured, bounded_runtime=False)
    return database_url
