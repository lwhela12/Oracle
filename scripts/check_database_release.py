#!/usr/bin/env python3
"""Run a content-free release check against Oracle's scoped database roles.

The check deliberately leaves one ``traffic_class=test`` event in the target
database as an auditable staging fixture.  Output is a single sanitized JSON
object; connection strings, role names, and driver errors are never emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import sys
import time
from typing import Mapping
import uuid


# Make direct execution (``python scripts/check_database_release.py``) resolve
# the repository modules without requiring installation as a package.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from psycopg.conninfo import conninfo_to_dict

from analytics_store import AnalyticsStoreError, write_events
from database import DatabaseConfigurationError, _validate_url


WRITE_BUDGET_SECONDS = 0.5
_KNOWN_ENVIRONMENTS = frozenset(
    {"local", "development", "test", "preview", "staging", "production"}
)


class ReleaseCheckError(RuntimeError):
    """A content-free failure code that is safe to print."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ReleaseConfiguration:
    writer_url: str = field(repr=False)
    reader_url: str = field(repr=False)
    environment: str
    writer_remote: bool
    reader_remote: bool


def _is_remote(fields: Mapping[str, str]) -> bool:
    host = fields.get("host", "")
    if host.startswith("/"):
        return False
    address = fields.get("hostaddr") or host
    if address.lower() == "localhost":
        return False
    try:
        return not ipaddress.ip_address(address).is_loopback
    except ValueError:
        # Runtime validation requires hostaddr for a DNS hostname.  Retain this
        # conservative branch so configuration remains safe if that rule grows.
        return True


def load_configuration(environ: Mapping[str, str]) -> ReleaseConfiguration:
    writer_url = environ.get("ORACLE_DATABASE_URL")
    reader_url = environ.get("ORACLE_REPORT_DATABASE_URL")
    environment = environ.get("ORACLE_DATABASE_ENVIRONMENT")
    runtime_environment = environ.get("VERCEL_ENV")
    if not writer_url:
        raise ReleaseCheckError("writer_database_url_required")
    if not reader_url:
        raise ReleaseCheckError("report_database_url_required")
    if environment not in _KNOWN_ENVIRONMENTS or runtime_environment != environment:
        raise ReleaseCheckError("database_environment_mismatch")
    if writer_url == reader_url:
        raise ReleaseCheckError("database_roles_must_be_distinct")
    try:
        _validate_url(writer_url, environment, bounded_runtime=True)
        _validate_url(reader_url, environment, bounded_runtime=True)
        writer_fields = conninfo_to_dict(writer_url)
        reader_fields = conninfo_to_dict(reader_url)
    except DatabaseConfigurationError as exc:
        raise ReleaseCheckError(exc.code) from None
    except Exception:
        raise ReleaseCheckError("invalid_database_url") from None
    return ReleaseConfiguration(
        writer_url=writer_url,
        reader_url=reader_url,
        environment=environment,
        writer_remote=_is_remote(writer_fields),
        reader_remote=_is_remote(reader_fields),
    )


def _session_facts(connection, *, remote: bool) -> dict:
    row = connection.execute("""
        SELECT s.ssl, s.version, current_user, current_database(),
               r.rolsuper, r.rolcreaterole, r.rolcreatedb,
               r.rolreplication, r.rolbypassrls
        FROM pg_catalog.pg_stat_ssl AS s
        JOIN pg_catalog.pg_roles AS r ON r.rolname = current_user
        WHERE s.pid = pg_backend_pid()
    """).fetchone()
    if row is None:
        raise ReleaseCheckError("database_session_unverifiable")
    ssl_enabled, tls_version, role_name, database_name, *admin_flags = row
    if remote and not ssl_enabled:
        raise ReleaseCheckError("database_tls_session_required")
    if any(admin_flags):
        raise ReleaseCheckError("database_role_is_administrative")
    return {
        "ssl": bool(ssl_enabled),
        "version": tls_version if ssl_enabled else None,
        "role": role_name,
        "database": database_name,
    }


def _scoped_membership(connection, expected_role: str) -> None:
    # Check transitive membership even when INHERIT is disabled: SET ROLE can
    # otherwise expose privileges absent from the current session's checks.
    row = connection.execute("""
        WITH RECURSIVE memberships(roleid) AS (
            SELECT m.roleid FROM pg_catalog.pg_auth_members m
            JOIN pg_catalog.pg_roles r ON r.oid = m.member
            WHERE r.rolname = current_user
            UNION
            SELECT m.roleid FROM pg_catalog.pg_auth_members m
            JOIN memberships parent ON parent.roleid = m.member
        )
        SELECT count(*) = 1 AND coalesce(bool_and(r.rolname = %s), false)
        FROM memberships m JOIN pg_catalog.pg_roles r ON r.oid = m.roleid
    """, (expected_role,)).fetchone()
    if row != (True,):
        raise ReleaseCheckError("database_role_membership_invalid")


def _writer_security(connection) -> None:
    row = connection.execute("""
        SELECT
            has_table_privilege(current_user, 'analytics.events', 'INSERT'),
            has_table_privilege(current_user, 'analytics.events', 'SELECT'),
            has_table_privilege(current_user, 'analytics.events', 'UPDATE'),
            has_table_privilege(current_user, 'analytics.events', 'DELETE'),
            has_schema_privilege(current_user, 'product', 'USAGE')
    """).fetchone()
    if row != (True, False, False, False, False):
        raise ReleaseCheckError("writer_privileges_invalid")
    _scoped_membership(connection, "oracle_telemetry_writer")


def _reader_security(connection) -> None:
    row = connection.execute("""
        SELECT
            has_table_privilege(current_user, 'analytics.events', 'SELECT'),
            has_table_privilege(current_user, 'analytics.events', 'INSERT'),
            has_table_privilege(current_user, 'analytics.events', 'UPDATE'),
            has_table_privilege(current_user, 'analytics.events', 'DELETE'),
            has_schema_privilege(current_user, 'product', 'USAGE')
    """).fetchone()
    if row != (True, False, False, False, False):
        raise ReleaseCheckError("reader_privileges_invalid")
    _scoped_membership(connection, "oracle_report_reader")


def _fixture(environment: str) -> dict:
    return {
        "schema": "oracle.telemetry.v1",
        "event": "reading_finished",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "traffic_class": "test",
        "reading_id": str(uuid.uuid4()),
        "attempt_id": str(uuid.uuid4()),
        "mode": "tarot",
        "spread": "3-card",
        "transport": "sync",
        "outcome": "completed",
        "duration_ms": 0,
    }


def _connect(database_url: str):
    """Open a bounded utility session without rewriting the runtime DSN."""

    return psycopg.connect(
        database_url,
        connect_timeout=5,
        options="-c statement_timeout=5000 -c lock_timeout=1000",
    )


def run_check() -> dict:
    started = time.monotonic()
    configuration = load_configuration(os.environ)
    event = _fixture(configuration.environment)

    phase_started = time.monotonic()
    with _connect(configuration.writer_url) as writer:
        writer_facts = _session_facts(writer, remote=configuration.writer_remote)
        _writer_security(writer)
    writer_security_ms = round((time.monotonic() - phase_started) * 1000, 2)

    phase_started = time.monotonic()
    with _connect(configuration.reader_url) as reader:
        reader_facts = _session_facts(reader, remote=configuration.reader_remote)
        _reader_security(reader)
    reader_security_ms = round((time.monotonic() - phase_started) * 1000, 2)

    if writer_facts["role"] == reader_facts["role"]:
        raise ReleaseCheckError("database_roles_must_be_distinct")
    if writer_facts["database"] != reader_facts["database"]:
        raise ReleaseCheckError("database_target_mismatch")

    phase_started = time.monotonic()
    first_insert = write_events([event], timeout_seconds=WRITE_BUDGET_SECONDS)
    second_insert = write_events([event], timeout_seconds=WRITE_BUDGET_SECONDS)
    write_ms = round((time.monotonic() - phase_started) * 1000, 2)
    if (first_insert, second_insert) != (1, 0):
        raise ReleaseCheckError("event_deduplication_failed")

    phase_started = time.monotonic()
    with _connect(configuration.reader_url) as reader:
        row = reader.execute("""
            SELECT event_id::text, reading_id::text, attempt_id::text,
                   environment, traffic_class
            FROM analytics.events
            WHERE event_id = %s AND reading_id = %s AND attempt_id = %s
        """, (event["event_id"], event["reading_id"], event["attempt_id"])).fetchone()
    read_ms = round((time.monotonic() - phase_started) * 1000, 2)
    expected = (
        event["event_id"], event["reading_id"], event["attempt_id"],
        configuration.environment, "test",
    )
    if row != expected:
        raise ReleaseCheckError("fixture_readback_failed")

    return {
        "status": "ok",
        "environment": configuration.environment,
        "fixture": {
            "event_id": event["event_id"],
            "reading_id": event["reading_id"],
            "attempt_id": event["attempt_id"],
            "traffic_class": "test",
            "retained": True,
        },
        "deduplication": {"first_inserted": 1, "second_inserted": 0},
        "tls": {
            "writer": {"enabled": writer_facts["ssl"], "version": writer_facts["version"]},
            "reader": {"enabled": reader_facts["ssl"], "version": reader_facts["version"]},
        },
        "timing_ms": {
            "write_budget": round(WRITE_BUDGET_SECONDS * 1000),
            "writer_security": writer_security_ms,
            "reader_security": reader_security_ms,
            "write_and_dedup": write_ms,
            "fixture_readback": read_ms,
            "elapsed": round((time.monotonic() - started) * 1000, 2),
        },
    }


def main() -> int:
    try:
        result = run_check()
    except ReleaseCheckError as exc:
        result = {"status": "error", "code": exc.code}
        exit_code = 1
    except AnalyticsStoreError as exc:
        result = {"status": "error", "code": f"event_write_{exc.code}"}
        exit_code = 1
    except (psycopg.Error, TimeoutError):
        result = {"status": "error", "code": "database_check_failed"}
        exit_code = 1
    except Exception:
        result = {"status": "error", "code": "release_check_failed"}
        exit_code = 1
    else:
        exit_code = 0
    print(json.dumps(result, separators=(",", ":"), sort_keys=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
