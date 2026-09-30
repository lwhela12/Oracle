#!/usr/bin/env python3
"""Delete production analytics events after the fixed 90-day retention period.

This command is intended for a scheduled one-shot job, for example::

    python scripts/maintain_analytics.py --batch-size 500 --max-rows 5000

Required environment variables:

``ORACLE_MAINTENANCE_DATABASE_URL``
    A maintenance-role PostgreSQL URL. Production requires
    ``sslmode=verify-full`` and, for a DNS hostname, a numeric ``hostaddr``.
``ORACLE_DATABASE_ENVIRONMENT`` and ``VERCEL_ENV``
    Both must be exactly ``production``. The database's protected identity
    marker must also report ``production`` before any delete is attempted.

Options are deliberately bounded. ``--batch-size`` defaults to 500 and is at
most 5,000; ``--max-rows`` defaults to 5,000 and is at most 50,000;
``--max-seconds`` defaults to 20 and is at most 60. The fixed retention period
cannot be shortened. ``--remaining-count-limit`` controls a bounded post-run
count (default 1,000, maximum 10,000); set it to 0 to skip that count.

The command prints one content-free JSON object. It never selects event payloads
or logs connection strings, credentials, role names, or driver messages.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Callable, Mapping, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg

from database import DatabaseConfigurationError, _validate_url


RETENTION_DAYS = 90
DEFAULT_BATCH_SIZE = 500
MAX_BATCH_SIZE = 5_000
DEFAULT_MAX_ROWS = 5_000
MAX_TOTAL_ROWS = 50_000
DEFAULT_MAX_SECONDS = 20.0
MAX_TOTAL_SECONDS = 60.0
DEFAULT_REMAINING_COUNT_LIMIT = 1_000
MAX_REMAINING_COUNT_LIMIT = 10_000


class MaintenanceError(RuntimeError):
    """A content-free failure code that is safe to print."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class MaintenanceOptions:
    batch_size: int = DEFAULT_BATCH_SIZE
    max_rows: int = DEFAULT_MAX_ROWS
    max_seconds: float = DEFAULT_MAX_SECONDS
    remaining_count_limit: int = DEFAULT_REMAINING_COUNT_LIMIT


@dataclass(frozen=True)
class MaintenanceConfiguration:
    database_url: str = field(repr=False)
    environment: str
    options: MaintenanceOptions


def _bounded_int(value: str, *, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"{name} must be an integer") from None
    if not minimum <= parsed <= maximum:
        raise argparse.ArgumentTypeError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return parsed


def _bounded_seconds(value: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("max-seconds must be a number") from None
    if not math.isfinite(parsed) or not 1.0 <= parsed <= MAX_TOTAL_SECONDS:
        raise argparse.ArgumentTypeError(
            f"max-seconds must be between 1 and {int(MAX_TOTAL_SECONDS)}"
        )
    return parsed


def parse_options(argv: Sequence[str] | None = None) -> MaintenanceOptions:
    parser = argparse.ArgumentParser(
        description="Run bounded 90-day production analytics retention."
    )
    parser.add_argument(
        "--batch-size",
        default=DEFAULT_BATCH_SIZE,
        type=lambda value: _bounded_int(
            value, name="batch-size", minimum=1, maximum=MAX_BATCH_SIZE
        ),
    )
    parser.add_argument(
        "--max-rows",
        default=DEFAULT_MAX_ROWS,
        type=lambda value: _bounded_int(
            value, name="max-rows", minimum=1, maximum=MAX_TOTAL_ROWS
        ),
    )
    parser.add_argument(
        "--max-seconds",
        default=DEFAULT_MAX_SECONDS,
        type=_bounded_seconds,
    )
    parser.add_argument(
        "--remaining-count-limit",
        default=DEFAULT_REMAINING_COUNT_LIMIT,
        type=lambda value: _bounded_int(
            value,
            name="remaining-count-limit",
            minimum=0,
            maximum=MAX_REMAINING_COUNT_LIMIT,
        ),
    )
    args = parser.parse_args(argv)
    return MaintenanceOptions(
        batch_size=args.batch_size,
        max_rows=args.max_rows,
        max_seconds=args.max_seconds,
        remaining_count_limit=args.remaining_count_limit,
    )


def load_configuration(
    environ: Mapping[str, str], options: MaintenanceOptions
) -> MaintenanceConfiguration:
    database_url = environ.get("ORACLE_MAINTENANCE_DATABASE_URL")
    if not database_url:
        raise MaintenanceError("maintenance_database_url_required")
    configured = environ.get("ORACLE_DATABASE_ENVIRONMENT")
    runtime = environ.get("VERCEL_ENV")
    if configured != "production" or runtime != "production":
        raise MaintenanceError("production_environment_required")
    try:
        # Requiring an explicit numeric hostaddr keeps DNS resolution outside
        # the scheduled run and therefore inside the total-time design.
        _validate_url(database_url, "production", bounded_runtime=True)
    except DatabaseConfigurationError as exc:
        raise MaintenanceError(exc.code) from None
    return MaintenanceConfiguration(
        database_url=database_url,
        environment="production",
        options=options,
    )


def _session_security(connection) -> str | None:
    row = connection.execute("""
        SELECT s.ssl, s.version,
               r.rolsuper, r.rolcreaterole, r.rolcreatedb,
               r.rolreplication, r.rolbypassrls
        FROM pg_catalog.pg_stat_ssl AS s
        JOIN pg_catalog.pg_roles AS r ON r.rolname = current_user
        WHERE s.pid = pg_backend_pid()
    """).fetchone()
    if row is None:
        raise MaintenanceError("database_session_unverifiable")
    ssl_enabled, tls_version, *admin_flags = row
    if not ssl_enabled:
        raise MaintenanceError("database_tls_session_required")
    if any(admin_flags):
        raise MaintenanceError("database_role_is_administrative")

    privileges = connection.execute("""
        SELECT
            has_table_privilege(current_user, 'analytics.events', 'SELECT'),
            has_table_privilege(current_user, 'analytics.events', 'DELETE'),
            has_table_privilege(current_user, 'analytics.events', 'INSERT'),
            has_table_privilege(current_user, 'analytics.events', 'UPDATE'),
            has_schema_privilege(current_user, 'product', 'USAGE'),
            has_function_privilege(
                current_user, 'analytics.environment_matches(text)', 'EXECUTE'
            )
    """).fetchone()
    if privileges != (True, True, False, False, False, True):
        raise MaintenanceError("maintenance_privileges_invalid")

    membership = connection.execute("""
        WITH RECURSIVE memberships(roleid) AS (
            SELECT m.roleid FROM pg_catalog.pg_auth_members m
            JOIN pg_catalog.pg_roles r ON r.oid = m.member
            WHERE r.rolname = current_user
            UNION
            SELECT m.roleid FROM pg_catalog.pg_auth_members m
            JOIN memberships parent ON parent.roleid = m.member
        )
        SELECT count(*) = 1 AND coalesce(
            bool_and(r.rolname = 'oracle_maintenance'), false
        )
        FROM memberships m
        JOIN pg_catalog.pg_roles r ON r.oid = m.roleid
    """).fetchone()
    if membership != (True,):
        raise MaintenanceError("database_role_membership_invalid")
    return tls_version


def _preflight(connection, environment: str) -> tuple[datetime, int, str | None]:
    tls_version = _session_security(connection)
    row = connection.execute("""
        SELECT analytics.environment_matches(%s),
               clock_timestamp() - make_interval(days => %s),
               pg_database_size(current_database())
    """, (environment, RETENTION_DAYS)).fetchone()
    if row is None or row[0] is not True:
        raise MaintenanceError("database_environment_marker_mismatch")
    cutoff, database_size = row[1], row[2]
    if not isinstance(cutoff, datetime) or cutoff.tzinfo is None:
        raise MaintenanceError("database_clock_unverifiable")
    if not isinstance(database_size, int) or database_size < 0:
        raise MaintenanceError("database_size_unverifiable")
    return cutoff, database_size, tls_version


def _connect(configuration: MaintenanceConfiguration):
    total_ms = int(configuration.options.max_seconds * 1_000)
    statement_timeout_ms = max(100, min(2_000, total_ms // 4))
    connect_timeout = max(1, min(5, math.ceil(configuration.options.max_seconds)))
    return psycopg.connect(
        configuration.database_url,
        connect_timeout=connect_timeout,
        options=(
            f"-c statement_timeout={statement_timeout_ms} "
            "-c lock_timeout=500 -c idle_in_transaction_session_timeout=3000"
        ),
    )


def _delete_batch(connection, *, environment: str, cutoff: datetime, limit: int) -> int:
    cursor = connection.execute("""
        WITH doomed AS (
            SELECT ctid
            FROM analytics.events
            WHERE environment = %s AND occurred_at < %s
            ORDER BY occurred_at, event_id
            LIMIT %s
        )
        DELETE FROM analytics.events AS events
        USING doomed
        WHERE events.ctid = doomed.ctid
    """, (environment, cutoff, limit))
    if cursor.rowcount < 0 or cursor.rowcount > limit:
        raise MaintenanceError("delete_count_invalid")
    return cursor.rowcount


def _bounded_remaining_count(
    connection, *, environment: str, cutoff: datetime, limit: int
) -> tuple[int, bool]:
    row = connection.execute("""
        SELECT count(*)
        FROM (
            SELECT 1
            FROM analytics.events
            WHERE environment = %s AND occurred_at < %s
            LIMIT %s
        ) AS bounded_old_events
    """, (environment, cutoff, limit + 1)).fetchone()
    if row is None or not isinstance(row[0], int) or row[0] < 0:
        raise MaintenanceError("remaining_count_invalid")
    return min(row[0], limit), row[0] > limit


def run_maintenance(
    configuration: MaintenanceConfiguration,
    *,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    started = clock()
    deadline = started + configuration.options.max_seconds
    deleted = 0
    batches = 0
    stop_reason = "max_seconds"
    remaining_count: int | None = None
    remaining_is_lower_bound: bool | None = None

    with _connect(configuration) as connection:
        cutoff, database_size, tls_version = _preflight(
            connection, configuration.environment
        )
        connection.commit()

        while clock() < deadline and deleted < configuration.options.max_rows:
            batch_limit = min(
                configuration.options.batch_size,
                configuration.options.max_rows - deleted,
            )
            batch_deleted = _delete_batch(
                connection,
                environment=configuration.environment,
                cutoff=cutoff,
                limit=batch_limit,
            )
            connection.commit()
            deleted += batch_deleted
            batches += 1
            if deleted >= configuration.options.max_rows:
                stop_reason = "max_rows"
                break
            if batch_deleted < batch_limit:
                stop_reason = "no_rows_available"
                break

        if (
            configuration.options.remaining_count_limit > 0
            and clock() < deadline
        ):
            remaining_count, remaining_is_lower_bound = _bounded_remaining_count(
                connection,
                environment=configuration.environment,
                cutoff=cutoff,
                limit=configuration.options.remaining_count_limit,
            )
            connection.commit()

    result = {
        "status": "ok",
        "environment": configuration.environment,
        "retention_days": RETENTION_DAYS,
        "cutoff_utc": cutoff.isoformat(),
        "deleted_count": deleted,
        "batches": batches,
        "stop_reason": stop_reason,
        "database_size_bytes": database_size,
        "tls": {"enabled": True, "version": tls_version},
        "limits": {
            "batch_size": configuration.options.batch_size,
            "max_rows": configuration.options.max_rows,
            "max_seconds": configuration.options.max_seconds,
            "remaining_count_limit": configuration.options.remaining_count_limit,
        },
        "elapsed_ms": round((clock() - started) * 1_000, 2),
    }
    if remaining_count is not None:
        result["remaining_old_count"] = remaining_count
        result["remaining_old_count_is_lower_bound"] = remaining_is_lower_bound
    return result


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = parse_options(argv)
        configuration = load_configuration(os.environ, options)
        result = run_maintenance(configuration)
    except MaintenanceError as exc:
        result = {"status": "error", "code": exc.code}
        exit_code = 1
    except (psycopg.Error, TimeoutError):
        result = {"status": "error", "code": "database_maintenance_failed"}
        exit_code = 1
    except Exception:
        result = {"status": "error", "code": "analytics_maintenance_failed"}
        exit_code = 1
    else:
        exit_code = 0
    print(json.dumps(result, separators=(",", ":"), sort_keys=True), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
