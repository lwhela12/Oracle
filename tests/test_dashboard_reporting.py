import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import dashboard_reporting as reporting


REPORT_URL = (
    "postgresql://reader:do-not-log@db.example.test/oracle?"
    "sslmode=verify-full&hostaddr=203.0.113.10"
)


class DashboardReportingTests(unittest.TestCase):
    def test_fixed_windows_follow_los_angeles_calendar_across_dst(self):
        # 2026-11-01 has two 01:30 hours in Los Angeles. The seven-day window
        # still starts at local midnight six calendar dates earlier.
        now = datetime(2026, 11, 1, 9, 30, tzinfo=timezone.utc)
        today = reporting.report_window("today", now)
        seven = reporting.report_window("7d", now)
        thirty = reporting.report_window("30d", now)

        self.assertEqual(today.start.isoformat(), "2026-11-01T07:00:00+00:00")
        self.assertEqual(seven.start.isoformat(), "2026-10-26T07:00:00+00:00")
        self.assertEqual(thirty.start.isoformat(), "2026-10-03T07:00:00+00:00")
        self.assertEqual(today.end, now)
        self.assertEqual(seven.start_local_date.isoformat(), "2026-10-26")
        self.assertEqual(seven.end_local_date.isoformat(), "2026-11-01")

    def test_invalid_period_and_naive_now_are_rejected(self):
        with self.assertRaisesRegex(reporting.DashboardReportError, "invalid_period"):
            reporting.report_window("custom")
        with self.assertRaisesRegex(reporting.DashboardReportError, "invalid_now"):
            reporting.report_window("today", datetime(2026, 9, 30, 12, 0))

    def test_configuration_requires_explicit_matching_environments(self):
        valid = {
            "ORACLE_REPORT_DATABASE_URL": REPORT_URL,
            "ORACLE_DATABASE_ENVIRONMENT": "production",
            "VERCEL_ENV": "production",
        }
        configuration = reporting.load_report_configuration(valid)
        self.assertEqual(configuration.environment, "production")
        self.assertNotIn("do-not-log", repr(configuration))
        self.assertNotIn("postgresql", repr(configuration))

        cases = [
            ({}, "report_database_url_required"),
            ({**valid, "VERCEL_ENV": "preview"}, "report_environment_mismatch"),
            ({**valid, "VERCEL_ENV": "", "ORACLE_DATABASE_ENVIRONMENT": "local"},
             None),
            ({**valid, "ORACLE_DATABASE_ENVIRONMENT": "other"},
             "report_environment_mismatch"),
            ({**valid, "ORACLE_REPORT_DATABASE_URL":
              "postgresql://reader@db.example.test/oracle?sslmode=require&hostaddr=203.0.113.10"},
             "database_tls_required"),
        ]
        for values, code in cases:
            with self.subTest(code=code):
                if code is None:
                    self.assertEqual(
                        reporting.load_report_configuration(values).environment,
                        "local",
                    )
                else:
                    with self.assertRaisesRegex(reporting.DashboardReportError, code):
                        reporting.load_report_configuration(values)

    def test_unexpected_database_failures_are_sanitized(self):
        environment = {
            "ORACLE_REPORT_DATABASE_URL": REPORT_URL,
            "ORACLE_DATABASE_ENVIRONMENT": "local",
            "VERCEL_ENV": "local",
        }
        secret = "PRIVATE-DSN-CONTENT"
        with patch.dict(os.environ, environment, clear=True), patch.object(
            reporting, "_connect", side_effect=RuntimeError(secret)
        ):
            with self.assertRaises(reporting.DashboardReportError) as raised:
                reporting.build_report(
                    "today", datetime(2026, 9, 30, 20, tzinfo=timezone.utc)
                )
        self.assertEqual(str(raised.exception), "report_unavailable")
        self.assertNotIn(secret, str(raised.exception))

    def test_query_contract_filters_public_traffic_and_returns_no_ids(self):
        sql_text = "\n".join(
            value for name, value in vars(reporting).items()
            if name.endswith("_SQL") and isinstance(value, str)
        )
        self.assertIn("traffic_class = 'public'", sql_text)
        self.assertNotIn("traffic_class = %s", sql_text)
        self.assertTrue(any(
            isinstance(value, str) and "REPEATABLE READ READ ONLY" in value
            for value in reporting._build_report.__code__.co_consts
        ))
        # Returned contract field names cannot expose row-level correlation IDs.
        forbidden = {"event_id", "visitor_id", "reading_id", "attempt_id",
                     "canonical_reading_id"}
        contract_keys = {
            "schema_version", "status", "period", "timezone", "environment",
            "generated_at", "window", "coverage", "totals", "daily",
            "popularity", "latency_ms", "qrng", "tokens", "cost_estimate",
            "labels",
        }
        self.assertTrue(contract_keys.isdisjoint(forbidden))
        self.assertNotIn("provider_attempt", json.dumps(sorted(contract_keys)))


if __name__ == "__main__":
    unittest.main()
