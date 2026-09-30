"""Aggregate-only reporting queries for Oracle's private owner dashboard.

The module deliberately returns no event, visitor, reading, attempt, or canonical
reading identifiers.  All identifier reconciliation and aggregation happens in
PostgreSQL inside one bounded, read-only repeatable-read transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import os
from typing import Mapping, Optional
from zoneinfo import ZoneInfo

import psycopg

from database import DatabaseConfigurationError, DatabaseSettings, _validate_url


REPORT_TIMEZONE = "America/Los_Angeles"
ATTEMPT_GRACE = timedelta(minutes=15)
_ZONE = ZoneInfo(REPORT_TIMEZONE)
_PERIOD_DAYS = {"today": 1, "7d": 7, "30d": 30}
_KNOWN_ENVIRONMENTS = {
    "local", "development", "test", "preview", "staging", "production"
}


class DashboardReportError(RuntimeError):
    """A sanitized reporting failure safe to return from an authenticated API."""

    def __init__(self, code: str = "report_unavailable") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ReportWindow:
    period: str
    start: datetime
    end: datetime
    start_local_date: date
    end_local_date: date


@dataclass(frozen=True)
class ReportConfiguration:
    database_url: str
    environment: str

    def __repr__(self) -> str:
        return (
            "ReportConfiguration(database_url='<redacted>', "
            f"environment={self.environment!r})"
        )


def report_window(period: str, now: Optional[datetime] = None) -> ReportWindow:
    """Return an inclusive-of-today local-calendar window ending at ``now``."""

    if period not in _PERIOD_DAYS:
        raise DashboardReportError("invalid_period")
    instant = now or datetime.now(timezone.utc)
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise DashboardReportError("invalid_now")
    end = instant.astimezone(timezone.utc)
    local_end = end.astimezone(_ZONE)
    start_date = local_end.date() - timedelta(days=_PERIOD_DAYS[period] - 1)
    local_start = datetime.combine(start_date, time.min, tzinfo=_ZONE)
    return ReportWindow(
        period=period,
        start=local_start.astimezone(timezone.utc),
        end=end,
        start_local_date=start_date,
        end_local_date=local_end.date(),
    )


def load_report_configuration(
    environ: Optional[Mapping[str, str]] = None,
) -> ReportConfiguration:
    """Load and validate the separately scoped aggregate-reader connection."""

    values = os.environ if environ is None else environ
    database_url = values.get("ORACLE_REPORT_DATABASE_URL")
    runtime = values.get("VERCEL_ENV") or "local"
    configured = values.get("ORACLE_DATABASE_ENVIRONMENT")
    if not database_url:
        raise DashboardReportError("report_database_url_required")
    if (
        not runtime
        or configured not in _KNOWN_ENVIRONMENTS
        or runtime != configured
    ):
        raise DashboardReportError("report_environment_mismatch")
    try:
        # Reuse the database module's serverless URL policy while keeping the
        # report credential independent from the telemetry writer credential.
        _validate_url(database_url, configured, bounded_runtime=True)
    except DatabaseConfigurationError as exc:
        raise DashboardReportError(exc.code) from None
    return ReportConfiguration(database_url=database_url, environment=configured)


_COMPLETED_CTE = """
completed_ranked AS (
    SELECT occurred_at, ingested_at, event_id, visitor_id, reading_id, properties,
           min(visitor_id::text) OVER (
               PARTITION BY CASE
                   WHEN reading_id IS NOT NULL THEN 'reading:' || reading_id::text
                   ELSE 'event:' || event_id::text
               END
           ) AS linked_visitor_id,
           row_number() OVER (
               PARTITION BY CASE
                   WHEN reading_id IS NOT NULL THEN 'reading:' || reading_id::text
                   ELSE 'event:' || event_id::text
               END
               ORDER BY occurred_at DESC, ingested_at DESC, event_id DESC
           ) AS rank
    FROM analytics.events
    WHERE environment = %s AND traffic_class = 'public'
      AND occurred_at >= %s AND occurred_at < %s
      AND event_type = 'reading_finished'
      AND properties->>'outcome' = 'completed'
),
completed AS (
    SELECT occurred_at, linked_visitor_id::uuid AS visitor_id,
           reading_id, properties
    FROM completed_ranked WHERE rank = 1
)
"""


_COVERAGE_SQL = """
SELECT
    min(occurred_at) FILTER (WHERE traffic_class = 'public') AS earliest_retained,
    max(occurred_at) FILTER (WHERE traffic_class = 'public') AS latest_event,
    max(ingested_at) FILTER (WHERE traffic_class = 'public') AS latest_ingested,
    min(occurred_at) FILTER (
        WHERE traffic_class = 'public' AND occurred_at >= %s AND occurred_at < %s
    ) AS window_first,
    max(occurred_at) FILTER (
        WHERE traffic_class = 'public' AND occurred_at >= %s AND occurred_at < %s
    ) AS window_last,
    count(*) FILTER (
        WHERE traffic_class = 'public' AND occurred_at >= %s AND occurred_at < %s
    ) AS window_event_count
FROM analytics.events
WHERE environment = %s AND occurred_at < %s
"""


_COMPLETION_TOTALS_SQL = (
    "WITH " + _COMPLETED_CTE + """
SELECT count(*) AS completed_readings,
       count(DISTINCT visitor_id) AS linked_active_browsers,
       count(*) FILTER (WHERE visitor_id IS NULL) AS completed_without_visitor_id
FROM completed
"""
)


_DAILY_SQL = (
    "WITH " + _COMPLETED_CTE + """
SELECT (occurred_at AT TIME ZONE 'America/Los_Angeles')::date AS local_day,
       count(*) AS completed_readings,
       count(DISTINCT visitor_id) AS linked_active_browsers
FROM completed
GROUP BY local_day
ORDER BY local_day
"""
)


_MODES_SQL = (
    "WITH " + _COMPLETED_CTE + """
SELECT coalesce(nullif(properties->>'mode', ''), 'unknown') AS mode,
       count(*) AS completed_readings
FROM completed
GROUP BY mode
ORDER BY completed_readings DESC, mode
"""
)


_SPREADS_SQL = (
    "WITH " + _COMPLETED_CTE + """
SELECT coalesce(nullif(properties->>'mode', ''), 'unknown') AS mode,
       coalesce(nullif(properties->>'spread', ''), 'default') AS spread,
       count(*) AS completed_readings
FROM completed
GROUP BY mode, spread
ORDER BY completed_readings DESC, mode, spread
"""
)


_LOGICAL_STARTS_SQL = """
WITH starts AS (
    SELECT reading_id, min(occurred_at) AS started_at
    FROM analytics.events
    WHERE environment = %s AND traffic_class = 'public'
      AND occurred_at >= %s AND occurred_at < %s
      AND event_type = 'reading_started' AND reading_id IS NOT NULL
    GROUP BY reading_id
), eligible AS (
    SELECT reading_id, started_at FROM starts WHERE started_at <= %s
), completed AS (
    SELECT DISTINCT e.reading_id
    FROM eligible e
    JOIN analytics.events f
      ON f.environment = %s AND f.traffic_class = 'public'
     AND f.event_type = 'reading_finished'
     AND f.reading_id = e.reading_id
     AND f.occurred_at >= e.started_at AND f.occurred_at < %s
     AND f.properties->>'outcome' = 'completed'
)
SELECT (SELECT count(*) FROM eligible) AS logical_starts_eligible,
       (SELECT count(*) FROM completed) AS logical_starts_completed,
       (SELECT count(*) FROM analytics.events
        WHERE environment = %s AND traffic_class = 'public'
          AND occurred_at >= %s AND occurred_at < %s
          AND event_type = 'reading_started' AND reading_id IS NULL
       ) AS starts_missing_reading_id
"""


_ATTEMPTS_SQL = """
WITH relevant AS (
    SELECT event_id, attempt_id, event_type, occurred_at, ingested_at,
           properties->>'outcome' AS outcome,
           CASE WHEN attempt_id IS NOT NULL THEN 'attempt:' || attempt_id::text
                ELSE 'event:' || event_id::text END AS attempt_key
    FROM analytics.events
    WHERE environment = %s AND traffic_class = 'public'
      AND occurred_at >= %s AND occurred_at < %s
      AND event_type IN ('reading_started', 'reading_finished')
), attempts AS (
    SELECT attempt_key,
           bool_or(event_type = 'reading_started') AS has_start,
           max(occurred_at) FILTER (WHERE event_type = 'reading_started') AS started_at
    FROM relevant GROUP BY attempt_key
), terminal_ranked AS (
    SELECT attempt_key, outcome,
           row_number() OVER (
               PARTITION BY attempt_key
               ORDER BY occurred_at DESC, ingested_at DESC, event_id DESC
           ) AS rank
    FROM relevant WHERE event_type = 'reading_finished'
), reconciled AS (
    SELECT a.attempt_key,
           CASE
               WHEN t.outcome IN ('completed', 'failed', 'interrupted') THEN t.outcome
               WHEN a.has_start AND a.started_at > %s THEN 'pending'
               ELSE 'unresolved'
           END AS outcome
    FROM attempts a LEFT JOIN terminal_ranked t
      ON t.attempt_key = a.attempt_key AND t.rank = 1
)
SELECT count(*) AS total,
       count(*) FILTER (WHERE outcome = 'completed') AS completed,
       count(*) FILTER (WHERE outcome = 'failed') AS failed,
       count(*) FILTER (WHERE outcome = 'interrupted') AS interrupted,
       count(*) FILTER (WHERE outcome = 'pending') AS pending,
       count(*) FILTER (WHERE outcome = 'unresolved') AS unresolved
FROM reconciled
"""


_LATENCY_SQL = """
WITH ranked AS (
    SELECT properties, row_number() OVER (
        PARTITION BY CASE WHEN attempt_id IS NOT NULL
                          THEN 'attempt:' || attempt_id::text
                          ELSE 'event:' || event_id::text END
        ORDER BY occurred_at DESC, ingested_at DESC, event_id DESC
    ) AS rank
    FROM analytics.events
    WHERE environment = %s AND traffic_class = 'public'
      AND occurred_at >= %s AND occurred_at < %s
      AND event_type = 'reading_finished'
), durations AS (
    SELECT (properties->>'duration_ms')::numeric AS duration_ms
    FROM ranked
    WHERE rank = 1 AND properties->>'outcome' = 'completed'
      AND properties ? 'duration_ms'
)
SELECT count(*) AS completed_attempts,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS median,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95
FROM durations
"""


_QRNG_SQL = """
SELECT count(*) AS batches,
       count(*) FILTER (WHERE (properties->>'fallback_values')::integer > 0)
           AS batches_with_fallback,
       coalesce(sum((properties->>'fallback_values')::integer), 0) AS fallback_values
FROM analytics.events
WHERE environment = %s AND traffic_class = 'public'
  AND occurred_at >= %s AND occurred_at < %s
  AND event_type = 'qrng_result'
"""


_TOKENS_SQL = """
SELECT coalesce(nullif(properties->>'model', ''), 'unknown') AS model,
       count(*) AS calls,
       count(*) FILTER (WHERE properties ?| ARRAY[
           'input_tokens', 'output_tokens', 'thinking_tokens',
           'cached_tokens', 'total_tokens'
       ]) AS calls_with_reported_tokens,
       count(*) FILTER (WHERE properties ? 'input_tokens') AS input_count,
       count(*) FILTER (WHERE properties ? 'output_tokens') AS output_count,
       count(*) FILTER (WHERE properties ? 'thinking_tokens') AS thinking_count,
       count(*) FILTER (WHERE properties ? 'cached_tokens') AS cached_count,
       count(*) FILTER (WHERE properties ? 'total_tokens') AS total_count,
       sum((properties->>'input_tokens')::bigint) AS input_tokens,
       sum((properties->>'output_tokens')::bigint) AS output_tokens,
       sum((properties->>'thinking_tokens')::bigint) AS thinking_tokens,
       sum((properties->>'cached_tokens')::bigint) AS cached_tokens,
       sum((properties->>'total_tokens')::bigint) AS total_tokens
FROM analytics.events
WHERE environment = %s AND traffic_class = 'public'
  AND occurred_at >= %s AND occurred_at < %s
  AND event_type = 'interpretation_usage'
GROUP BY model
ORDER BY calls DESC, model
"""


def _connect(configuration: ReportConfiguration):
    settings = DatabaseSettings(
        database_url=configuration.database_url,
        environment=configuration.environment,
    )
    return psycopg.connect(
        configuration.database_url,
        **settings.connect_kwargs(3),
        options=(
            "-c statement_timeout=5000 -c lock_timeout=500 "
            "-c idle_in_transaction_session_timeout=10000 "
            "-c transaction_timeout=10000"
        ),
    )


def _rows(connection, query: str, parameters: tuple) -> list[tuple]:
    return connection.execute(query, parameters).fetchall()


def _one(connection, query: str, parameters: tuple) -> tuple:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise DashboardReportError("report_query_failed")
    return row


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _number(value):
    if value is None:
        return None
    result = float(value)
    return int(result) if result.is_integer() else round(result, 2)


def _integer(value):
    return None if value is None else int(value)


def _percentage(numerator: int, denominator: int):
    if not denominator:
        return None
    return round(100 * numerator / denominator, 2)


def _build_report(
    connection, configuration: ReportConfiguration, window: ReportWindow
) -> dict:
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    marker = _one(
        connection,
        "SELECT analytics.environment_matches(%s)",
        (configuration.environment,),
    )
    if marker != (True,):
        raise DashboardReportError("report_environment_mismatch")

    common = (configuration.environment, window.start, window.end)
    coverage = _one(
        connection,
        _COVERAGE_SQL,
        (
            window.start,
            window.end,
            window.start,
            window.end,
            window.start,
            window.end,
            configuration.environment,
            window.end,
        ),
    )
    completed = _one(connection, _COMPLETION_TOTALS_SQL, common)
    logical = _one(
        connection,
        _LOGICAL_STARTS_SQL,
        (
            configuration.environment,
            window.start,
            window.end,
            window.end - ATTEMPT_GRACE,
            configuration.environment,
            window.end,
            configuration.environment,
            window.start,
            window.end,
        ),
    )
    attempts = _one(
        connection,
        _ATTEMPTS_SQL,
        common + (window.end - ATTEMPT_GRACE,),
    )
    latency = _one(connection, _LATENCY_SQL, common)
    qrng = _one(connection, _QRNG_SQL, common)
    token_rows = _rows(connection, _TOKENS_SQL, common)

    daily_by_date = {
        row[0]: {
            "date": row[0].isoformat(),
            "completed_readings": row[1],
            "linked_active_browsers": row[2],
        }
        for row in _rows(connection, _DAILY_SQL, common)
    }
    daily = []
    current = window.start_local_date
    while current <= window.end_local_date:
        daily.append(
            daily_by_date.get(
                current,
                {
                    "date": current.isoformat(),
                    "completed_readings": 0,
                    "linked_active_browsers": 0,
                },
            )
        )
        current += timedelta(days=1)

    modes = [
        {"mode": row[0], "completed_readings": row[1]}
        for row in _rows(connection, _MODES_SQL, common)
    ]
    spreads = [
        {"mode": row[0], "spread": row[1], "completed_readings": row[2]}
        for row in _rows(connection, _SPREADS_SQL, common)
    ]
    token_groups = [
        {
            "model": row[0],
            "calls": row[1],
            "calls_with_reported_tokens": row[2],
            "reported_counts": {
                "input_tokens": row[3],
                "output_tokens": row[4],
                "thinking_tokens": row[5],
                "cached_tokens": row[6],
                "total_tokens": row[7],
            },
            "input_tokens": _integer(row[8]),
            "output_tokens": _integer(row[9]),
            "thinking_tokens": _integer(row[10]),
            "cached_tokens": _integer(row[11]),
            "total_tokens": _integer(row[12]),
        }
        for row in token_rows
    ]
    token_calls = sum(row["calls"] for row in token_groups)
    token_reported = sum(row["calls_with_reported_tokens"] for row in token_groups)

    latest_event = coverage[1]
    freshness = None
    if latest_event is not None:
        freshness = max(0, int((window.end - latest_event).total_seconds()))

    return {
        "schema_version": 1,
        "status": "ok",
        "period": window.period,
        "timezone": REPORT_TIMEZONE,
        "environment": configuration.environment,
        "generated_at": _iso(window.end),
        "window": {
            "start": _iso(window.start),
            "end": _iso(window.end),
            "start_local_date": window.start_local_date.isoformat(),
            "end_local_date": window.end_local_date.isoformat(),
            "includes_today": True,
            "incomplete_end_day": True,
        },
        "coverage": {
            "earliest_retained_event_at": _iso(coverage[0]),
            "latest_event_at": _iso(latest_event),
            "latest_ingested_at": _iso(coverage[2]),
            "window_first_event_at": _iso(coverage[3]),
            "window_last_event_at": _iso(coverage[4]),
            "freshness_seconds": freshness,
            "window_event_count": coverage[5],
        },
        "totals": {
            "completed_readings": completed[0],
            "linked_active_browsers": completed[1],
            "completed_without_visitor_id": completed[2],
            "logical_starts_eligible": logical[0],
            "logical_starts_completed": logical[1],
            "completion_rate_percent": _percentage(logical[1], logical[0]),
            "starts_missing_reading_id": logical[2],
            "attempts": {
                "total": attempts[0],
                "completed": attempts[1],
                "failed": attempts[2],
                "interrupted": attempts[3],
                "pending": attempts[4],
                "unresolved": attempts[5],
            },
        },
        "daily": daily,
        "popularity": {"modes": modes, "spreads": spreads},
        "latency_ms": {
            "completed_attempts": latency[0],
            "median": _number(latency[1]),
            "p95": _number(latency[2]),
        },
        "qrng": {
            "batches": qrng[0],
            "batches_with_fallback": qrng[1],
            "fallback_values": qrng[2],
            "fallback_batch_percent": _percentage(qrng[1], qrng[0]),
        },
        "tokens": {
            "calls": token_calls,
            "calls_with_reported_tokens": token_reported,
            "calls_missing_reported_tokens": token_calls - token_reported,
            "by_model": token_groups,
        },
        "cost_estimate": {
            "status": "unavailable",
            "reason": "verified_pricing_and_instrumentation_required",
        },
        "labels": {
            "linked_active_browsers": "Anonymous browser IDs, not people",
            "completion": (
                "Server completed generation; it does not prove display or reading"
            ),
            "window": "Includes today; the current day is incomplete",
        },
    }


def build_report(period: str, now: Optional[datetime] = None) -> dict:
    """Build a compact aggregate report for one fixed dashboard period."""

    window = report_window(period, now)
    try:
        configuration = load_report_configuration()
        with _connect(configuration) as connection:
            with connection.transaction():
                return _build_report(connection, configuration, window)
    except DashboardReportError:
        raise
    except (DatabaseConfigurationError, psycopg.Error, TimeoutError):
        raise DashboardReportError("report_unavailable") from None
    except Exception:
        # Never surface a DSN, query, driver diagnostic, or stored value.
        raise DashboardReportError("report_unavailable") from None
