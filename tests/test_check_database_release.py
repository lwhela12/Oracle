import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import check_database_release as release_check


WRITER_URL = "postgresql://writer:writer-secret@127.0.0.1/oracle"
READER_URL = "postgresql://reader:reader-secret@127.0.0.1/oracle"


def configuration(**changes):
    values = {
        "ORACLE_DATABASE_URL": WRITER_URL,
        "ORACLE_REPORT_DATABASE_URL": READER_URL,
        "ORACLE_DATABASE_ENVIRONMENT": "local",
        "VERCEL_ENV": "local",
    }
    values.update(changes)
    return values


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, role, event=None, *, writer_privileges=None,
                 reader_privileges=None, ssl=True, membership_valid=True):
        self.role = role
        self.event = event
        self.writer_privileges = writer_privileges or (True, False, False, False, False)
        self.reader_privileges = reader_privileges or (True, False, False, False, False)
        self.ssl = ssl
        self.membership_valid = membership_valid
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, params))
        if "FROM pg_catalog.pg_stat_ssl" in normalized:
            return FakeCursor((self.ssl, "TLSv1.3" if self.ssl else None,
                               self.role, "oracle", False, False, False, False, False))
        if "WITH RECURSIVE memberships" in normalized:
            return FakeCursor((self.membership_valid,))
        if "has_table_privilege" in normalized:
            return FakeCursor(self.writer_privileges if self.role == "writer"
                              else self.reader_privileges)
        if "FROM analytics.events" in normalized:
            return FakeCursor((
                self.event["event_id"], self.event["reading_id"],
                self.event["attempt_id"], self.event["environment"], "test",
            ))
        raise AssertionError(f"unexpected query: {normalized}")


class DatabaseReleaseCheckTests(unittest.TestCase):
    def test_configuration_requires_distinct_urls_and_matching_environments(self):
        with self.assertRaisesRegex(release_check.ReleaseCheckError,
                                    "report_database_url_required"):
            release_check.load_configuration(configuration(ORACLE_REPORT_DATABASE_URL=""))
        with self.assertRaisesRegex(release_check.ReleaseCheckError,
                                    "database_environment_mismatch"):
            release_check.load_configuration(configuration(VERCEL_ENV="production"))
        with self.assertRaisesRegex(release_check.ReleaseCheckError,
                                    "database_roles_must_be_distinct"):
            release_check.load_configuration(
                configuration(ORACLE_REPORT_DATABASE_URL=WRITER_URL)
            )

    def test_configuration_repr_redacts_both_urls(self):
        result = release_check.load_configuration(configuration())
        self.assertNotIn("writer-secret", repr(result))
        self.assertNotIn("reader-secret", repr(result))
        self.assertNotIn("postgresql", repr(result))

    def test_success_checks_scoped_roles_dedup_and_only_reads_own_fixture(self):
        connections = []
        written = []

        def connect(url, **kwargs):
            self.assertEqual(kwargs, {
                "connect_timeout": 5,
                "options": "-c statement_timeout=5000 -c lock_timeout=1000",
            })
            role = "writer" if url == WRITER_URL else "reader"
            connection = FakeConnection(role, written[0] if written else None)
            connections.append(connection)
            return connection

        def write_events(records, *, timeout_seconds):
            self.assertEqual(timeout_seconds, 0.5)
            written[:] = records
            return 1 if write_events.calls == 0 else 0

        write_events.calls = 0

        def counted_write(records, *, timeout_seconds):
            result = write_events(records, timeout_seconds=timeout_seconds)
            write_events.calls += 1
            return result

        with patch.dict(os.environ, configuration(), clear=True), patch.object(
            release_check.psycopg, "connect", side_effect=connect
        ), patch.object(release_check, "write_events", side_effect=counted_write):
            result = release_check.run_check()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["deduplication"], {"first_inserted": 1, "second_inserted": 0})
        self.assertEqual(result["fixture"]["traffic_class"], "test")
        self.assertTrue(result["fixture"]["retained"])
        self.assertEqual(result["timing_ms"]["write_budget"], 500)
        read_query, params = connections[-1].queries[-1]
        self.assertIn("WHERE event_id = %s AND reading_id = %s AND attempt_id = %s", read_query)
        self.assertEqual(params, (
            result["fixture"]["event_id"], result["fixture"]["reading_id"],
            result["fixture"]["attempt_id"],
        ))
        self.assertNotIn("count(*)", read_query.lower())

    def test_remote_connection_must_report_tls(self):
        remote = configuration(
            ORACLE_DATABASE_ENVIRONMENT="preview",
            VERCEL_ENV="preview",
            ORACLE_DATABASE_URL=(
                "postgresql://writer@db.example/oracle?"
                "sslmode=verify-full&hostaddr=203.0.113.10"
            ),
            ORACLE_REPORT_DATABASE_URL=(
                "postgresql://reader@db.example/oracle?"
                "sslmode=verify-full&hostaddr=203.0.113.10"
            ),
        )
        with patch.dict(os.environ, remote, clear=True), patch.object(
            release_check.psycopg, "connect", return_value=FakeConnection("writer", ssl=False)
        ), self.assertRaisesRegex(release_check.ReleaseCheckError,
                                  "database_tls_session_required"):
            release_check.run_check()

    def test_failure_output_is_single_sanitized_json_object(self):
        secret = "do-not-print-this-password"
        output = io.StringIO()
        values = configuration(
            ORACLE_DATABASE_URL=f"postgresql://writer:{secret}@127.0.0.1/oracle"
        )
        with patch.dict(os.environ, values, clear=True), patch.object(
            release_check.psycopg, "connect",
            side_effect=RuntimeError(f"driver exposed {secret}"),
        ), redirect_stdout(output):
            exit_code = release_check.main()
        self.assertEqual(exit_code, 1)
        self.assertNotIn(secret, output.getvalue())
        self.assertEqual(json.loads(output.getvalue()),
                         {"status": "error", "code": "release_check_failed"})

    def test_privilege_drift_fails_before_any_event_write(self):
        writer = FakeConnection(
            "writer", writer_privileges=(True, True, False, False)
        )
        with patch.dict(os.environ, configuration(), clear=True), patch.object(
            release_check.psycopg, "connect", return_value=writer
        ), patch.object(release_check, "write_events") as write, self.assertRaisesRegex(
            release_check.ReleaseCheckError, "writer_privileges_invalid"
        ):
            release_check.run_check()
        write.assert_not_called()

    def test_unexpected_membership_or_product_access_rejected_before_write(self):
        for writer, code in [
            (FakeConnection("writer", membership_valid=False),
             "database_role_membership_invalid"),
            (FakeConnection("writer", writer_privileges=(True, False, False, False, True)),
             "writer_privileges_invalid"),
        ]:
            with self.subTest(code=code), patch.dict(os.environ, configuration(), clear=True), patch.object(
                release_check.psycopg, "connect", return_value=writer
            ), patch.object(release_check, "write_events") as write, self.assertRaisesRegex(
                release_check.ReleaseCheckError, code
            ):
                release_check.run_check()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
