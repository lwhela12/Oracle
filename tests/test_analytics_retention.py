import io
import json
import os
from pathlib import Path
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

from scripts import maintain_analytics as maintenance


MAINTENANCE_URL = (
    "postgresql://maintainer:do-not-log@db.example.test/oracle?"
    "sslmode=verify-full&hostaddr=203.0.113.10"
)
CUTOFF = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def production_environment(**changes):
    values = {
        "ORACLE_MAINTENANCE_DATABASE_URL": MAINTENANCE_URL,
        "ORACLE_DATABASE_ENVIRONMENT": "production",
        "VERCEL_ENV": "production",
    }
    values.update(changes)
    return values


def configuration(**option_changes):
    options = maintenance.MaintenanceOptions(
        batch_size=option_changes.get("batch_size", 2),
        max_rows=option_changes.get("max_rows", 5),
        max_seconds=option_changes.get("max_seconds", 10),
        remaining_count_limit=option_changes.get("remaining_count_limit", 3),
    )
    return maintenance.MaintenanceConfiguration(
        database_url=MAINTENANCE_URL,
        environment="production",
        options=options,
    )


class FakeCursor:
    def __init__(self, row=None, *, rowcount=-1):
        self.row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(
        self,
        *,
        delete_counts=(),
        remaining_count=0,
        marker=True,
        ssl=True,
        privileges=(True, True, False, False, False, True),
        membership=True,
    ):
        self.delete_counts = list(delete_counts)
        self.remaining_count = remaining_count
        self.marker = marker
        self.ssl = ssl
        self.privileges = privileges
        self.membership = membership
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.commits += 1

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, params))
        if "FROM pg_catalog.pg_stat_ssl" in normalized:
            return FakeCursor((
                self.ssl,
                "TLSv1.3" if self.ssl else None,
                False, False, False, False, False,
            ))
        if "has_table_privilege" in normalized:
            return FakeCursor(self.privileges)
        if "WITH RECURSIVE memberships" in normalized:
            return FakeCursor((self.membership,))
        if "analytics.environment_matches" in normalized:
            return FakeCursor((self.marker, CUTOFF, 12_345_678))
        if normalized.startswith("WITH doomed AS"):
            if not self.delete_counts:
                raise AssertionError("unexpected extra delete batch")
            return FakeCursor(rowcount=self.delete_counts.pop(0))
        if "AS bounded_old_events" in normalized:
            return FakeCursor((self.remaining_count,))
        raise AssertionError(f"unexpected query: {normalized}")


class AnalyticsRetentionTests(unittest.TestCase):
    def test_isolated_railway_cron_build_has_minimal_runtime(self):
        root = Path(__file__).resolve().parents[1]
        railway = json.loads((root / "maintenance" / "railway.json").read_text())
        self.assertEqual(railway["build"], {
            "builder": "DOCKERFILE",
            "dockerfilePath": "maintenance/Dockerfile",
        })
        self.assertEqual(railway["deploy"], {
            "startCommand": "python scripts/maintain_analytics.py",
            "cronSchedule": "0 8 * * *",
            "restartPolicyType": "NEVER",
        })

        dockerfile = (root / "maintenance" / "Dockerfile").read_text()
        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn('"psycopg[binary]==3.3.3"', dockerfile)
        self.assertIn("USER oracle", dockerfile)
        self.assertIn("COPY --chown=oracle:oracle database.py /app/database.py", dockerfile)
        self.assertIn(
            "COPY --chown=oracle:oracle scripts/maintain_analytics.py ", dockerfile
        )
        self.assertIn("COPY --chown=oracle:oracle certs/ /app/certs/", dockerfile)
        self.assertNotIn("requirements.txt", dockerfile)
        self.assertNotIn("app.py", dockerfile)
        self.assertNotIn("google", dockerfile.lower())
        self.assertTrue((root / "certs" / "oracle-production-root.crt").is_file())

    def test_configuration_is_production_only_and_requires_verified_bounded_url(self):
        options = maintenance.MaintenanceOptions()
        cases = [
            ({}, "maintenance_database_url_required"),
            (production_environment(VERCEL_ENV="preview"),
             "production_environment_required"),
            (production_environment(ORACLE_DATABASE_ENVIRONMENT="preview"),
             "production_environment_required"),
            (production_environment(ORACLE_MAINTENANCE_DATABASE_URL=
                "postgresql://maintainer@db.example.test/oracle?sslmode=require&hostaddr=203.0.113.10"),
             "database_tls_required"),
            (production_environment(ORACLE_MAINTENANCE_DATABASE_URL=
                "postgresql://maintainer@db.example.test/oracle?sslmode=verify-full"),
             "runtime_database_address_required"),
        ]
        for environment, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(
                maintenance.MaintenanceError, code
            ):
                maintenance.load_configuration(environment, options)

    def test_configuration_repr_redacts_maintenance_url(self):
        result = maintenance.load_configuration(
            production_environment(), maintenance.MaintenanceOptions()
        )
        self.assertNotIn("do-not-log", repr(result))
        self.assertNotIn("postgresql", repr(result))

    def test_options_have_hard_upper_bounds(self):
        parsed = maintenance.parse_options([
            "--batch-size", "5000",
            "--max-rows", "50000",
            "--max-seconds", "60",
            "--remaining-count-limit", "0",
        ])
        self.assertEqual(parsed, maintenance.MaintenanceOptions(
            batch_size=5_000,
            max_rows=50_000,
            max_seconds=60,
            remaining_count_limit=0,
        ))
        for args in (["--batch-size", "5001"], ["--max-rows", "0"],
                     ["--max-seconds", "nan"],
                     ["--remaining-count-limit", "10001"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                maintenance.parse_options(args)

    def test_connection_and_statement_timeouts_are_bounded(self):
        sentinel = object()
        with patch.object(
            maintenance.psycopg, "connect", return_value=sentinel
        ) as connect:
            self.assertIs(
                maintenance._connect(configuration(max_seconds=1)), sentinel
            )
        connect.assert_called_once_with(
            MAINTENANCE_URL,
            connect_timeout=1,
            options=(
                "-c statement_timeout=250 -c lock_timeout=500 "
                "-c idle_in_transaction_session_timeout=3000"
            ),
        )

    def test_deletes_only_fixed_cutoff_and_environment_in_bounded_batches(self):
        connection = FakeConnection(delete_counts=(2, 1), remaining_count=0)
        with patch.object(maintenance, "_connect", return_value=connection):
            result = maintenance.run_maintenance(configuration())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["retention_days"], 90)
        self.assertEqual(result["cutoff_utc"], CUTOFF.isoformat())
        self.assertEqual(result["deleted_count"], 3)
        self.assertEqual(result["batches"], 2)
        self.assertEqual(result["stop_reason"], "no_rows_available")
        self.assertEqual(result["remaining_old_count"], 0)
        self.assertFalse(result["remaining_old_count_is_lower_bound"])
        self.assertEqual(result["database_size_bytes"], 12_345_678)

        preflight = next(item for item in connection.queries
                         if "SELECT analytics.environment_matches" in item[0])
        self.assertEqual(preflight[1], ("production", 90))
        deletes = [item for item in connection.queries if item[0].startswith("WITH doomed AS")]
        self.assertEqual([params for _, params in deletes], [
            ("production", CUTOFF, 2),
            ("production", CUTOFF, 2),
        ])
        for query, _ in deletes:
            self.assertIn("WHERE environment = %s AND occurred_at < %s", query)
            self.assertIn("LIMIT %s", query)
            self.assertNotIn("FOR UPDATE", query)
            self.assertNotIn("properties", query)
            self.assertNotIn("RETURNING", query)
        count_query, count_params = next(
            item for item in connection.queries if "AS bounded_old_events" in item[0]
        )
        self.assertEqual(count_params, ("production", CUTOFF, 4))
        self.assertIn("LIMIT %s", count_query)
        self.assertEqual(connection.commits, 4)

    def test_max_rows_reduces_final_batch_and_stops_exactly_at_limit(self):
        connection = FakeConnection(delete_counts=(3, 2), remaining_count=4)
        config = configuration(batch_size=3, max_rows=5, remaining_count_limit=3)
        with patch.object(maintenance, "_connect", return_value=connection):
            result = maintenance.run_maintenance(config)
        deletes = [params for query, params in connection.queries
                   if query.startswith("WITH doomed AS")]
        self.assertEqual(deletes, [
            ("production", CUTOFF, 3),
            ("production", CUTOFF, 2),
        ])
        self.assertEqual(result["deleted_count"], 5)
        self.assertEqual(result["stop_reason"], "max_rows")
        self.assertEqual(result["remaining_old_count"], 3)
        self.assertTrue(result["remaining_old_count_is_lower_bound"])

    def test_time_limit_can_stop_before_first_delete_or_optional_count(self):
        connection = FakeConnection()
        times = iter((0.0, 2.0, 2.0, 2.0))
        with patch.object(maintenance, "_connect", return_value=connection):
            result = maintenance.run_maintenance(
                configuration(max_seconds=1), clock=lambda: next(times)
            )
        self.assertEqual(result["deleted_count"], 0)
        self.assertEqual(result["batches"], 0)
        self.assertEqual(result["stop_reason"], "max_seconds")
        self.assertNotIn("remaining_old_count", result)
        self.assertFalse(any(query.startswith("WITH doomed AS")
                             for query, _ in connection.queries))

    def test_marker_tls_privilege_and_membership_fail_closed_before_delete(self):
        cases = [
            (FakeConnection(marker=False), "database_environment_marker_mismatch"),
            (FakeConnection(ssl=False), "database_tls_session_required"),
            (FakeConnection(privileges=(True, True, True, False, False, True)),
             "maintenance_privileges_invalid"),
            (FakeConnection(membership=False), "database_role_membership_invalid"),
        ]
        for connection, code in cases:
            with self.subTest(code=code), patch.object(
                maintenance, "_connect", return_value=connection
            ), self.assertRaisesRegex(maintenance.MaintenanceError, code):
                maintenance.run_maintenance(configuration())
            self.assertFalse(any(query.startswith("WITH doomed AS")
                                 for query, _ in connection.queries))

    def test_failure_output_is_single_sanitized_json_object(self):
        secret = "never-emit-this-secret"
        output = io.StringIO()
        environment = production_environment(
            ORACLE_MAINTENANCE_DATABASE_URL=(
                f"postgresql://maintainer:{secret}@db.example.test/oracle?"
                "sslmode=verify-full&hostaddr=203.0.113.10"
            )
        )
        with patch.dict(os.environ, environment, clear=True), patch.object(
            maintenance.psycopg, "connect",
            side_effect=RuntimeError(f"driver included {secret}"),
        ), redirect_stdout(output):
            exit_code = maintenance.main([])
        self.assertEqual(exit_code, 1)
        self.assertNotIn(secret, output.getvalue())
        self.assertEqual(json.loads(output.getvalue()), {
            "status": "error", "code": "analytics_maintenance_failed"
        })


if __name__ == "__main__":
    unittest.main()
