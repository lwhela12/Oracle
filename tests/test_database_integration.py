"""PostgreSQL integration checks; set ORACLE_TEST_ADMIN_DATABASE_URL to enable."""

import os
import json
import time
import unittest
import uuid
from urllib.parse import quote, urlencode
from unittest.mock import patch

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from analytics_store import AnalyticsStoreError, write_events
from app import app
from telemetry import emit


ADMIN_URL = os.getenv("ORACLE_TEST_ADMIN_DATABASE_URL")


@unittest.skipUnless(ADMIN_URL, "ORACLE_TEST_ADMIN_DATABASE_URL is not set")
class PostgreSQLFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:10]
        cls.database = f"oracle_foundation_{suffix}"
        cls.writer = f"oracle_writer_{suffix}"
        cls.reader = f"oracle_reader_{suffix}"
        admin_fields = conninfo_to_dict(ADMIN_URL)
        cls.admin_url = make_conninfo(**admin_fields)
        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.database)))
        database_fields = {**admin_fields, "dbname": cls.database}
        query = urlencode({key: value for key, value in database_fields.items()
                           if key in {"host", "port", "sslmode"}})
        cls.database_url = (
            f"postgresql://{quote(database_fields['user'])}@/{quote(cls.database)}?{query}"
        )
        migration_env = {
            "ORACLE_MIGRATION_DATABASE_URL": cls.database_url,
            "ORACLE_DATABASE_ENVIRONMENT": "local",
        }
        with patch.dict(os.environ, migration_env, clear=False):
            command.upgrade(Config("alembic.ini"), "head")
            command.upgrade(Config("alembic.ini"), "head")
        with psycopg.connect(cls.database_url, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(cls.writer)))
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(cls.reader)))
            connection.execute(sql.SQL("GRANT oracle_telemetry_writer TO {}").format(sql.Identifier(cls.writer)))
            connection.execute(sql.SQL("GRANT oracle_report_reader TO {}").format(sql.Identifier(cls.reader)))
        cls.writer_url = f"postgresql://{quote(cls.writer)}@/{quote(cls.database)}?{query}"
        cls.reader_url = f"postgresql://{quote(cls.reader)}@/{quote(cls.database)}?{query}"

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(cls.admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(cls.database)))
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(cls.writer)))
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(cls.reader)))

    def event(self, **changes):
        record = {
            "schema": "oracle.telemetry.v2",
            "event": "reading_finished",
            "event_id": str(uuid.uuid4()),
            "timestamp": "2026-09-29T12:00:00+00:00",
            "environment": "local",
            "traffic_class": "test",
            "reading_id": str(uuid.uuid4()),
            "attempt_id": str(uuid.uuid4()),
            "canonical_reading_id": str(uuid.uuid4()),
            "mode": "tarot", "spread": "3-card", "transport": "sync",
            "outcome": "completed", "duration_ms": 10,
        }
        record.update(changes)
        return record

    def runtime_env(self, url=None):
        return patch.dict(os.environ, {
            "ORACLE_DATABASE_URL": url or self.writer_url,
            "ORACLE_DATABASE_ENVIRONMENT": "local",
            "VERCEL_ENV": "local",
        }, clear=False)

    def test_migration_idempotent_event_insert_and_database_constraints(self):
        event = self.event()
        with self.runtime_env():
            self.assertEqual(write_events([event], timeout_seconds=0.5), 1)
            self.assertEqual(write_events([event], timeout_seconds=0.5), 0)
        with psycopg.connect(self.database_url) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM analytics.events").fetchone()[0], 1)
            with self.assertRaises(psycopg.errors.CheckViolation):
                connection.execute("""
                    INSERT INTO analytics.events
                    (event_id, schema_version, event_type, occurred_at, environment, traffic_class, properties)
                    VALUES (%s, 1, 'app_opened', now(), 'local', 'test', %s::jsonb)
                """, (str(uuid.uuid4()), '{"question":"private"}'))

    def test_runtime_roles_are_scoped(self):
        with psycopg.connect(self.writer_url, autocommit=True) as writer:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                writer.execute("SELECT * FROM analytics.events")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                writer.execute("UPDATE analytics.events SET traffic_class = 'public'")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                writer.execute("DELETE FROM analytics.events")
        with psycopg.connect(self.reader_url, autocommit=True) as reader:
            reader.execute("SELECT count(*) FROM analytics.events").fetchone()
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                reader.execute("SELECT * FROM product.missing_table")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                reader.execute("INSERT INTO analytics.events DEFAULT VALUES")

    def test_database_identity_marker_blocks_wrong_database(self):
        with psycopg.connect(self.database_url) as connection:
            connection.execute("UPDATE analytics.database_identity SET environment = 'preview'")
            connection.commit()
        try:
            with self.runtime_env(), self.assertRaisesRegex(AnalyticsStoreError, "configuration_error"):
                write_events([self.event()], timeout_seconds=0.5)
        finally:
            with psycopg.connect(self.database_url) as connection:
                connection.execute("UPDATE analytics.database_identity SET environment = 'local'")
                connection.commit()

    def test_real_flask_request_persists_content_free_event_contract(self):
        class OracleStub:
            def prepare_tarot_reading(self, *args, **kwargs):
                emit("qrng_result", provider="anu", source="quantum", reason="none",
                     requested=3, fallback_values=0, duration_ms=1)
                return {"cards": [], "positions": [], "spread_type": "3-card",
                        "prompt": "PRIVATE prompt"}

            def stream_chat(self, *args, **kwargs):
                emit("interpretation_usage", model="test-model", input_tokens=10,
                     output_tokens=4, total_tokens=14)
                yield "PRIVATE answer"

        reading_id = str(uuid.uuid4())
        environment = {
            "ORACLE_DATABASE_URL": self.writer_url,
            "ORACLE_DATABASE_ENVIRONMENT": "local", "VERCEL_ENV": "local",
            "ORACLE_TRAFFIC_CLASS": "test", "ORACLE_ANALYTICS_ENABLED": "1",
            "POSTHOG_PROJECT_TOKEN": "",
        }
        body = {"message": "PRIVATE question", "mode": "tarot",
                "spread_type": "3-card", "reading_id": reading_id,
                "visitor_id": str(uuid.uuid4())}
        with patch.dict(os.environ, environment, clear=False), patch(
            "app.get_oracle", return_value=OracleStub()
        ):
            response = app.test_client().post(
                "/chat/stream", json=body, headers={"DNT": "1"}
            )
            payload = response.data.decode()
        metadata = json.loads(payload.split("\n\n", 1)[0].split("data: ", 1)[1])
        canonical = uuid.UUID(metadata["canonical_reading_id"])
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute("""
                SELECT event_type, visitor_id, canonical_reading_id, properties::text
                FROM analytics.events WHERE reading_id = %s ORDER BY ingested_at
            """, (reading_id,)).fetchall()
        self.assertEqual([row[0] for row in rows], [
            "reading_started", "qrng_result", "interpretation_usage", "reading_finished"
        ])
        self.assertTrue(all(row[1] is None for row in rows))
        self.assertEqual(rows[-1][2], canonical)
        self.assertNotIn("PRIVATE", json.dumps(rows, default=str))

    def test_real_driver_write_obeys_lock_timeout(self):
        blocker = psycopg.connect(self.database_url)
        blocker.execute("LOCK TABLE analytics.events IN ACCESS EXCLUSIVE MODE")
        started = time.monotonic()
        try:
            with self.runtime_env(), self.assertRaisesRegex(AnalyticsStoreError, "timeout|database_error"):
                write_events([self.event()], timeout_seconds=0.1)
            self.assertLess(time.monotonic() - started, 0.75)
        finally:
            blocker.rollback()
            blocker.close()


if __name__ == "__main__":
    unittest.main()
