import asyncio
import os
import socket
import time
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from analytics_store import AnalyticsStoreError, validate_event, write_events
from database import DatabaseSettings


def valid_event(**changes):
    event = {
        "schema": "oracle.telemetry.v1",
        "event": "reading_finished",
        "event_id": str(uuid.uuid4()),
        "timestamp": "2026-09-29T12:00:00+00:00",
        "environment": "local",
        "traffic_class": "test",
        "reading_id": str(uuid.uuid4()),
        "attempt_id": str(uuid.uuid4()),
        "mode": "tarot",
        "spread": "3-card",
        "transport": "sync",
        "outcome": "completed",
        "duration_ms": 120,
    }
    event.update(changes)
    return event


class AnalyticsStoreTests(unittest.TestCase):
    def test_v1_and_v2_identifier_rules(self):
        canonical = str(uuid.uuid4())
        with self.assertRaisesRegex(AnalyticsStoreError, "invalid_event"):
            validate_event(valid_event(canonical_reading_id=canonical))
        row = validate_event(valid_event(
            schema="oracle.telemetry.v2", canonical_reading_id=canonical
        ))
        self.assertEqual(str(row[9]), canonical)

    def test_content_unknown_keys_and_bad_typed_values_are_rejected(self):
        invalid = [
            {"question": "private"},
            {"prompt": "private"},
            {"interpretation": "private"},
            {"journal_text": "private"},
            {"cards": ["The Hermit"]},
            {"runes": ["Fehu"]},
            {"hexagram": 1},
            {"quantum_number": 42},
            {"response": "private"},
            {"duration_ms": True},
            {"model": "bad model with spaces", "event": "interpretation_usage",
             "mode": "tarot", "spread": "3-card", "transport": "sync"},
            {"event_id": "not-a-uuid"},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaisesRegex(
                AnalyticsStoreError, "invalid_event"
            ):
                validate_event(valid_event(**change))

    def test_missing_database_url_is_a_sanitized_configuration_failure(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AnalyticsStoreError, "configuration_error"):
                write_events([valid_event()], timeout_seconds=0.1)

    def test_runtime_hostname_fails_before_dns_resolution(self):
        values = {
            "ORACLE_DATABASE_URL": "postgresql://writer@unresolved.invalid/oracle",
            "ORACLE_DATABASE_ENVIRONMENT": "local", "VERCEL_ENV": "local",
        }
        with patch.dict(os.environ, values, clear=True), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("resolver must not run")
        ) as resolver:
            started = time.monotonic()
            with self.assertRaisesRegex(AnalyticsStoreError, "configuration_error"):
                write_events([valid_event()], timeout_seconds=0.02)
        self.assertLess(time.monotonic() - started, 0.15)
        resolver.assert_not_called()

    def test_total_timeout_cancels_async_write(self):
        class Transaction:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class StalledConnection:
            def __init__(self):
                self.closed = False
                self.cancelled_after_close = False

            def transaction(self):
                return Transaction()

            async def execute(self, *args):
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    self.cancelled_after_close = self.closed
                    if not self.closed:  # Model psycopg's slow cancel path.
                        await asyncio.sleep(0.25)
                    raise

            async def close(self):
                self.closed = True

        connection = StalledConnection()

        settings = DatabaseSettings("postgresql://writer@localhost/oracle", "local")
        started = time.monotonic()
        with patch("analytics_store.settings_from_env", return_value=settings), patch(
            "analytics_store.psycopg.AsyncConnection.connect",
            new=AsyncMock(return_value=connection),
        ):
            with self.assertRaisesRegex(AnalyticsStoreError, "timeout"):
                write_events([valid_event()], timeout_seconds=0.05)
        self.assertLess(time.monotonic() - started, 0.15)
        self.assertTrue(connection.closed)
        self.assertTrue(connection.cancelled_after_close)


if __name__ == "__main__":
    unittest.main()
