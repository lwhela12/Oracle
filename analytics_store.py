"""Strict, content-free PostgreSQL delivery for Oracle telemetry events."""

import asyncio
from datetime import datetime
import json
import re
from typing import Iterable, Mapping
import uuid

import psycopg
from psycopg.types.json import Jsonb

from database import DatabaseConfigurationError, settings_from_env


MAX_BATCH_SIZE = 50
_SCHEMAS = {"oracle.telemetry.v1": 1, "oracle.telemetry.v2": 2}
_COMMON_KEYS = {
    "schema", "event", "event_id", "timestamp", "environment", "traffic_class",
    "visitor_id", "reading_id", "attempt_id", "canonical_reading_id",
}
_COMMON_PROPERTIES = {"mode", "spread", "transport"}
_EVENT_PROPERTIES = {
    "app_opened": set(),
    "reading_started": set(),
    "reading_finished": {"outcome", "duration_ms"},
    "qrng_result": {
        "provider", "source", "reason", "http_status", "requested",
        "fallback_values", "duration_ms", "failovers",
    },
    "interpretation_usage": {
        "model", "input_tokens", "output_tokens", "thinking_tokens",
        "cached_tokens", "total_tokens",
    },
}
_REQUIRED_PROPERTIES = {
    "app_opened": set(),
    "reading_started": {"mode", "spread", "transport"},
    "reading_finished": {"mode", "spread", "transport", "outcome", "duration_ms"},
    "qrng_result": {"source", "reason", "requested", "fallback_values", "duration_ms"},
    "interpretation_usage": {"model"},
}
_ENUMS = {
    "mode": {"tarot", "runes", "iching", "number", "oracle", "unknown"},
    "spread": {
        "default", "3-card", "yes-no", "5-card", "celtic", "norns", "single",
        "five-cross", "thor-hammer", "nine-worlds",
    },
    "transport": {"sync", "stream"},
    "outcome": {"completed", "failed", "interrupted"},
    "source": {"quantum", "system", "mixed"},
    "reason": {
        "none", "no_provider", "budget_exhausted", "rate_limited", "http_error",
        "invalid_response", "timeout", "network_error", "range_rejection",
    },
    "provider": {"anu", "lfdr.de", "qrandom.io", "anu-legacy"},
}
_INTEGER_RANGES = {
    "duration_ms": (0, 3_600_000),
    "http_status": (100, 599),
    "requested": (0, 1024),
    "fallback_values": (0, 1024),
    "input_tokens": (0, 100_000_000),
    "output_tokens": (0, 100_000_000),
    "thinking_tokens": (0, 100_000_000),
    "cached_tokens": (0, 100_000_000),
    "total_tokens": (0, 100_000_000),
}
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_FAILOVERS = re.compile(
    r"(?:anu|lfdr\.de|qrandom\.io|anu-legacy):"
    r"(?:no_provider|budget_exhausted|rate_limited|http_error|invalid_response|timeout|network_error)"
    r"(?:,(?:anu|lfdr\.de|qrandom\.io|anu-legacy):"
    r"(?:no_provider|budget_exhausted|rate_limited|http_error|invalid_response|timeout|network_error)){0,3}\Z"
)


class AnalyticsStoreError(RuntimeError):
    """A sanitized failure safe for operational logs."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _uuid(value, *, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value) > 36:
        raise AnalyticsStoreError("invalid_event")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise AnalyticsStoreError("invalid_event") from None
    if str(parsed) != value.lower():
        raise AnalyticsStoreError("invalid_event")
    return parsed


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise AnalyticsStoreError("invalid_event")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AnalyticsStoreError("invalid_event") from None
    if parsed.tzinfo is None or not 2020 <= parsed.year < 2100:
        raise AnalyticsStoreError("invalid_event")
    return parsed


def _validate_property(key, value):
    if key in _ENUMS:
        if type(value) is not str or value not in _ENUMS[key]:
            raise AnalyticsStoreError("invalid_event")
    elif key in _INTEGER_RANGES:
        low, high = _INTEGER_RANGES[key]
        if type(value) is not int or not low <= value <= high:
            raise AnalyticsStoreError("invalid_event")
    elif key == "model":
        if type(value) is not str or not _MODEL.fullmatch(value):
            raise AnalyticsStoreError("invalid_event")
    elif key == "failovers":
        if type(value) is not str or not _FAILOVERS.fullmatch(value):
            raise AnalyticsStoreError("invalid_event")
    else:  # This is unreachable when the property maps above remain exhaustive.
        raise AnalyticsStoreError("invalid_event")


def validate_event(record: Mapping) -> tuple:
    if not isinstance(record, Mapping):
        raise AnalyticsStoreError("invalid_event")
    schema_version = _SCHEMAS.get(record.get("schema"))
    event_type = record.get("event")
    if schema_version is None or event_type not in _EVENT_PROPERTIES:
        raise AnalyticsStoreError("invalid_event")
    allowed_properties = _COMMON_PROPERTIES | _EVENT_PROPERTIES[event_type]
    allowed_keys = _COMMON_KEYS | allowed_properties
    if set(record) - allowed_keys:
        raise AnalyticsStoreError("invalid_event")
    required = {"schema", "event", "event_id", "timestamp", "environment", "traffic_class"}
    if not required <= set(record) or not _REQUIRED_PROPERTIES[event_type] <= set(record):
        raise AnalyticsStoreError("invalid_event")
    environment = record["environment"]
    if environment not in {"local", "development", "test", "preview", "staging", "production"}:
        raise AnalyticsStoreError("invalid_event")
    traffic_class = record["traffic_class"]
    if traffic_class not in {"public", "internal", "test"}:
        raise AnalyticsStoreError("invalid_event")
    canonical = _uuid(record.get("canonical_reading_id"))
    if schema_version == 1 and canonical is not None:
        raise AnalyticsStoreError("invalid_event")
    properties = {}
    for key in allowed_properties:
        if key in record:
            _validate_property(key, record[key])
            properties[key] = record[key]
    if len(json.dumps(properties, separators=(",", ":"), sort_keys=True).encode()) > 4096:
        raise AnalyticsStoreError("invalid_event")
    return (
        _uuid(record["event_id"], required=True), schema_version, event_type,
        _timestamp(record["timestamp"]), environment, traffic_class,
        _uuid(record.get("visitor_id")), _uuid(record.get("reading_id")),
        _uuid(record.get("attempt_id")), canonical, Jsonb(properties),
    )


_INSERT = """
INSERT INTO analytics.events (
    event_id, schema_version, event_type, occurred_at, environment, traffic_class,
    visitor_id, reading_id, attempt_id, canonical_reading_id, properties
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT DO NOTHING
"""


async def _connect_before(database_url: str, timeout_seconds: float):
    task = asyncio.create_task(psycopg.AsyncConnection.connect(
        database_url, connect_timeout=max(1, int(timeout_seconds + 0.999))
    ))
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout_seconds)
        if not done:
            task.cancel()
            result = (await asyncio.gather(task, return_exceptions=True))[0]
            if not isinstance(result, BaseException):
                await result.close()
            raise asyncio.TimeoutError
        return task.result()
    except BaseException:
        if not task.done():
            task.cancel()
            result = (await asyncio.gather(task, return_exceptions=True))[0]
            if not isinstance(result, BaseException):
                await result.close()
        raise


async def _transaction(connection, rows: list, timeout_seconds: float) -> int:
    async with connection.transaction():
        milliseconds = max(1, int(timeout_seconds * 1000))
        await connection.execute("SELECT set_config('statement_timeout', %s, true)",
                                 (f"{milliseconds}ms",))
        await connection.execute("SELECT set_config('lock_timeout', %s, true)",
                                 (f"{milliseconds}ms",))
        marker = await connection.execute(
            "SELECT analytics.environment_matches(%s)", (rows[0][4],)
        )
        if not (await marker.fetchone())[0]:
            raise AnalyticsStoreError("configuration_error")
        cursor = connection.cursor()
        await cursor.executemany(_INSERT, rows)
        return max(0, cursor.rowcount)


async def _write(database_url: str, rows: list, timeout_seconds: float) -> int:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    connection = await _connect_before(database_url, timeout_seconds)
    task = None
    try:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError
        task = asyncio.create_task(_transaction(connection, rows, remaining))
        done, _ = await asyncio.wait({task}, timeout=remaining)
        if done:
            return task.result()

        # Psycopg's AsyncConnection.wait() catches task cancellation and can
        # spend five seconds cancelling before waiting on the original query
        # again.  Finish the socket first.  Once the pgconn is closed, psycopg
        # skips that cancellation path and the operation cannot outlive this
        # request's wall-clock budget.
        await connection.close()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise asyncio.TimeoutError
    finally:
        if task is not None and not task.done():
            await connection.close()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await connection.close()


def write_events(records: Iterable[Mapping], *, timeout_seconds: float) -> int:
    """Validate and insert one batch within a single cumulative wall-clock bound."""

    if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 5:
        raise AnalyticsStoreError("configuration_error")
    try:
        records = list(records)
    except Exception:
        raise AnalyticsStoreError("invalid_event") from None
    if not records:
        return 0
    if len(records) > MAX_BATCH_SIZE:
        raise AnalyticsStoreError("invalid_event")
    rows = [validate_event(record) for record in records]
    try:
        settings = settings_from_env()
    except DatabaseConfigurationError:
        raise AnalyticsStoreError("configuration_error") from None
    if settings is None:
        raise AnalyticsStoreError("configuration_error")
    if any(row[4] != settings.environment for row in rows):
        raise AnalyticsStoreError("invalid_event")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # A synchronous request boundary cannot safely nest an event loop.  Do
        # not create a thread whose work could outlive the caller's deadline.
        raise AnalyticsStoreError("configuration_error")
    try:
        return asyncio.run(_write(settings.database_url, rows, timeout_seconds))
    except (asyncio.TimeoutError, TimeoutError):
        raise AnalyticsStoreError("timeout") from None
    except AnalyticsStoreError:
        raise
    except Exception:
        raise AnalyticsStoreError("database_error") from None
