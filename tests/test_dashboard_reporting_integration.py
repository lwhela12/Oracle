"""PostgreSQL aggregate-report tests; set ORACLE_TEST_ADMIN_DATABASE_URL."""

import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import quote, urlencode

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

from dashboard_reporting import build_report


ADMIN_URL = os.getenv("ORACLE_TEST_ADMIN_DATABASE_URL")
NOW = datetime(2026, 9, 30, 20, 0, tzinfo=timezone.utc)


@unittest.skipUnless(ADMIN_URL, "ORACLE_TEST_ADMIN_DATABASE_URL is not set")
class DashboardReportingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:10]
        cls.database = f"oracle_report_{suffix}"
        cls.reader = f"oracle_report_login_{suffix}"
        admin_fields = conninfo_to_dict(ADMIN_URL)
        cls.admin_url = make_conninfo(**admin_fields)
        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database))
            )
        database_fields = {**admin_fields, "dbname": cls.database}
        query = urlencode({
            key: value for key, value in database_fields.items()
            if key in {"host", "port", "sslmode"}
        })
        cls.database_url = (
            f"postgresql://{quote(database_fields['user'])}@/"
            f"{quote(cls.database)}?{query}"
        )
        with patch.dict(os.environ, {
            "ORACLE_MIGRATION_DATABASE_URL": cls.database_url,
            "ORACLE_DATABASE_ENVIRONMENT": "local",
        }, clear=False):
            command.upgrade(Config("alembic.ini"), "head")
        with psycopg.connect(cls.database_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(cls.reader))
            )
            connection.execute(
                sql.SQL("GRANT oracle_report_reader TO {}").format(
                    sql.Identifier(cls.reader)
                )
            )
        cls.reader_url = (
            f"postgresql://{quote(cls.reader)}@/{quote(cls.database)}?{query}"
        )

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    sql.Identifier(cls.database)
                )
            )
            connection.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(cls.reader))
            )

    def setUp(self):
        with psycopg.connect(self.database_url) as connection:
            connection.execute("TRUNCATE analytics.events")

    def insert_event(
        self,
        event_type,
        occurred_at,
        *,
        event_id=None,
        environment="local",
        traffic_class="public",
        visitor_id=None,
        reading_id=None,
        attempt_id=None,
        properties=None,
    ):
        identity = event_id or uuid.uuid4()
        with psycopg.connect(self.database_url) as connection:
            connection.execute("""
                INSERT INTO analytics.events (
                    event_id, schema_version, event_type, occurred_at, ingested_at,
                    environment, traffic_class, visitor_id, reading_id,
                    attempt_id, properties
                ) VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                identity, event_type, occurred_at, occurred_at + timedelta(seconds=2),
                environment, traffic_class, visitor_id, reading_id, attempt_id,
                Jsonb(properties or {}),
            ))
        return str(identity)

    def report(self, period="7d"):
        environment = {
            "ORACLE_REPORT_DATABASE_URL": self.reader_url,
            "ORACLE_DATABASE_ENVIRONMENT": "local",
            "VERCEL_ENV": "local",
        }
        with patch.dict(os.environ, environment, clear=False):
            return build_report(period, NOW)

    def test_reconciles_retries_boundaries_outcomes_and_missing_ids(self):
        visitor = uuid.uuid4()
        reading_1, attempt_1 = uuid.uuid4(), uuid.uuid4()
        start = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)
        common_start = {"mode": "tarot", "spread": "3-card", "transport": "sync"}
        self.insert_event("reading_started", start, visitor_id=visitor,
                          reading_id=reading_1, attempt_id=attempt_1,
                          properties=common_start)
        first_finish = {**common_start, "outcome": "completed", "duration_ms": 1000}
        self.insert_event("reading_finished", start + timedelta(minutes=1),
                          visitor_id=visitor, reading_id=reading_1,
                          attempt_id=attempt_1, properties=first_finish)
        # A retry/duplicate terminal record must not add another reading or attempt;
        # its later finalized mode/spread and duration are authoritative.
        latest_finish = {"mode": "runes", "spread": "norns", "transport": "stream",
                         "outcome": "completed", "duration_ms": 1100}
        self.insert_event("reading_finished", start + timedelta(minutes=2),
                          reading_id=reading_1,
                          attempt_id=attempt_1, properties=latest_finish)

        failed_reading, failed_attempt = uuid.uuid4(), uuid.uuid4()
        failed_start = NOW - timedelta(hours=2)
        self.insert_event("reading_started", failed_start,
                          reading_id=failed_reading, attempt_id=failed_attempt,
                          properties=common_start)
        self.insert_event("reading_finished", failed_start + timedelta(minutes=1),
                          reading_id=failed_reading, attempt_id=failed_attempt,
                          properties={**common_start, "outcome": "failed",
                                      "duration_ms": 60000})

        unresolved_reading, unresolved_attempt = uuid.uuid4(), uuid.uuid4()
        self.insert_event("reading_started", NOW - timedelta(minutes=20),
                          reading_id=unresolved_reading,
                          attempt_id=unresolved_attempt, properties=common_start)
        self.insert_event("reading_started", NOW - timedelta(minutes=5),
                          reading_id=uuid.uuid4(), attempt_id=uuid.uuid4(),
                          properties=common_start)
        self.insert_event("reading_finished", NOW - timedelta(minutes=30),
                          reading_id=uuid.uuid4(), attempt_id=uuid.uuid4(),
                          properties={**common_start, "outcome": "interrupted",
                                      "duration_ms": 100})

        # Reconciliation uses the latest terminal outcome for an attempt. Its
        # earlier completion still establishes a completed logical reading, but
        # it must not contribute completed-attempt latency.
        conflict_reading, conflict_attempt = uuid.uuid4(), uuid.uuid4()
        self.insert_event("reading_finished", NOW - timedelta(minutes=28),
                          reading_id=conflict_reading, attempt_id=conflict_attempt,
                          properties={**first_finish, "duration_ms": 9000})
        self.insert_event("reading_finished", NOW - timedelta(minutes=27),
                          reading_id=conflict_reading, attempt_id=conflict_attempt,
                          properties={**common_start, "outcome": "failed",
                                      "duration_ms": 10000})

        # Two anonymous completions without reading or attempt IDs remain two
        # distinct logical readings and attempts rather than one shared NULL key.
        anonymous_event_ids = []
        for offset in (40, 35):
            anonymous_event_ids.append(self.insert_event(
                "reading_finished", NOW - timedelta(minutes=offset),
                properties={"mode": "tarot", "spread": "yes-no",
                            "transport": "sync", "outcome": "completed",
                            "duration_ms": 3000},
            ))
        self.insert_event("reading_started", NOW - timedelta(hours=1),
                          properties=common_start)

        # The seven-day lower boundary is included; the exact end is excluded.
        lower = datetime(2026, 9, 24, 7, 0, tzinfo=timezone.utc)
        self.insert_event("reading_finished", lower, reading_id=uuid.uuid4(),
                          attempt_id=uuid.uuid4(),
                          properties={**first_finish, "duration_ms": 500})
        self.insert_event("reading_finished", NOW, reading_id=uuid.uuid4(),
                          attempt_id=uuid.uuid4(), properties=first_finish)

        # These rows prove both traffic-class and environment isolation.
        self.insert_event("reading_finished", NOW - timedelta(hours=1),
                          traffic_class="internal", reading_id=uuid.uuid4(),
                          attempt_id=uuid.uuid4(), properties=first_finish)
        self.insert_event("reading_finished", NOW - timedelta(hours=1),
                          environment="preview", reading_id=uuid.uuid4(),
                          attempt_id=uuid.uuid4(), properties=first_finish)

        report = self.report()
        self.assertEqual(report["totals"]["completed_readings"], 5)
        self.assertEqual(report["totals"]["linked_active_browsers"], 1)
        self.assertEqual(report["totals"]["completed_without_visitor_id"], 4)
        self.assertEqual(report["totals"]["logical_starts_eligible"], 3)
        self.assertEqual(report["totals"]["logical_starts_completed"], 1)
        self.assertEqual(report["totals"]["completion_rate_percent"], 33.33)
        self.assertEqual(report["totals"]["starts_missing_reading_id"], 1)
        self.assertEqual(report["totals"]["attempts"], {
            "total": 10, "completed": 4, "failed": 2, "interrupted": 1,
            "pending": 1, "unresolved": 2,
        })
        self.assertEqual(report["popularity"]["modes"], [
            {"mode": "tarot", "completed_readings": 4},
            {"mode": "runes", "completed_readings": 1},
        ])
        self.assertIn(
            {"mode": "runes", "spread": "norns", "completed_readings": 1},
            report["popularity"]["spreads"],
        )
        self.assertEqual(report["latency_ms"], {
            "completed_attempts": 4, "median": 2050, "p95": 3000,
        })
        self.assertEqual(len(report["daily"]), 7)
        self.assertTrue(any(day["completed_readings"] == 0 for day in report["daily"]))
        self.assertEqual(report["daily"][0]["date"], "2026-09-24")
        self.assertTrue(report["window"]["incomplete_end_day"])
        self.assertNotEqual(report["coverage"]["latest_event_at"],
                            NOW.isoformat().replace("+00:00", "Z"))

        serialized = json.dumps(report)
        for identifier in anonymous_event_ids + [str(visitor), str(reading_1),
                                                  str(attempt_1)]:
            self.assertNotIn(identifier, serialized)

    def test_qrng_tokens_coverage_and_no_data_contract(self):
        self.insert_event(
            "app_opened", NOW - timedelta(days=20), visitor_id=uuid.uuid4(),
            properties={},
        )
        self.insert_event(
            "qrng_result", NOW - timedelta(hours=1),
            properties={"source": "quantum", "reason": "none", "requested": 3,
                        "fallback_values": 0, "duration_ms": 20},
        )
        self.insert_event(
            "qrng_result", NOW - timedelta(minutes=50),
            properties={"source": "mixed", "reason": "rate_limited", "requested": 3,
                        "fallback_values": 2, "duration_ms": 50},
        )
        self.insert_event(
            "interpretation_usage", NOW - timedelta(minutes=40),
            properties={"model": "gemini-test", "input_tokens": 10,
                        "output_tokens": 5, "total_tokens": 15},
        )
        self.insert_event(
            "interpretation_usage", NOW - timedelta(minutes=30),
            properties={"model": "gemini-test"},
        )
        self.insert_event(
            "interpretation_usage", NOW - timedelta(minutes=20),
            properties={"model": "other-model", "input_tokens": 7},
        )

        report = self.report("today")
        json.dumps(report)
        self.assertEqual(report["qrng"], {
            "batches": 2, "batches_with_fallback": 1, "fallback_values": 2,
            "fallback_batch_percent": 50.0,
        })
        self.assertEqual(report["tokens"]["calls"], 3)
        self.assertEqual(report["tokens"]["calls_with_reported_tokens"], 2)
        self.assertEqual(report["tokens"]["calls_missing_reported_tokens"], 1)
        self.assertEqual(report["tokens"]["by_model"][0], {
            "model": "gemini-test", "calls": 2,
            "calls_with_reported_tokens": 1,
            "reported_counts": {"input_tokens": 1, "output_tokens": 1,
                                "thinking_tokens": 0, "cached_tokens": 0,
                                "total_tokens": 1},
            "input_tokens": 10,
            "output_tokens": 5, "thinking_tokens": None, "cached_tokens": None,
            "total_tokens": 15,
        })
        for group in report["tokens"]["by_model"]:
            for key in ("input_tokens", "output_tokens", "thinking_tokens",
                        "cached_tokens", "total_tokens"):
                self.assertTrue(group[key] is None or isinstance(group[key], int))
                self.assertIsInstance(group["reported_counts"][key], int)
        self.assertEqual(report["cost_estimate"], {
            "status": "unavailable",
            "reason": "verified_pricing_and_instrumentation_required",
        })
        self.assertEqual(report["coverage"]["earliest_retained_event_at"],
                         "2026-09-10T20:00:00Z")
        self.assertEqual(report["coverage"]["window_event_count"], 5)

        with psycopg.connect(self.database_url) as connection:
            connection.execute("TRUNCATE analytics.events")
        empty = self.report("today")
        self.assertEqual(empty["totals"]["completed_readings"], 0)
        self.assertEqual(empty["daily"], [{
            "date": "2026-09-30", "completed_readings": 0,
            "linked_active_browsers": 0,
        }])
        self.assertIsNone(empty["coverage"]["freshness_seconds"])
        self.assertIsNone(empty["qrng"]["fallback_batch_percent"])
        self.assertEqual(empty["tokens"]["by_model"], [])

    def test_reader_can_verify_marker_but_cannot_mutate_or_read_product(self):
        with psycopg.connect(self.reader_url, autocommit=True) as reader:
            self.assertEqual(
                reader.execute(
                    "SELECT analytics.environment_matches('local')"
                ).fetchone(),
                (True,),
            )
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                reader.execute("INSERT INTO analytics.events DEFAULT VALUES")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                reader.execute("SELECT * FROM product.missing_table")


if __name__ == "__main__":
    unittest.main()
