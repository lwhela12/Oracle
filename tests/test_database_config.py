import os
import unittest
from unittest.mock import patch

from database import DatabaseConfigurationError, settings_from_env


class DatabaseConfigurationTests(unittest.TestCase):
    def test_missing_url_disables_database(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(settings_from_env())

    def test_environment_must_match_runtime(self):
        values = {
            "ORACLE_DATABASE_URL": "postgresql://writer@localhost/oracle",
            "ORACLE_DATABASE_ENVIRONMENT": "production",
            "VERCEL_ENV": "preview",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(DatabaseConfigurationError, "database_environment_mismatch"):
                settings_from_env()

    def test_verified_tls_is_required_for_preview_and_production(self):
        for environment in ("preview", "production"):
            values = {
                "ORACLE_DATABASE_URL": "postgresql://writer@db.example/oracle?sslmode=require",
                "ORACLE_DATABASE_ENVIRONMENT": environment,
                "VERCEL_ENV": environment,
            }
            with self.subTest(environment=environment), patch.dict(os.environ, values, clear=True):
                with self.assertRaisesRegex(DatabaseConfigurationError, "database_tls_required"):
                    settings_from_env()
                with patch.dict(os.environ, {"ORACLE_DATABASE_URL":
                        "postgresql://writer@db.example/oracle?sslmode=verify-full&hostaddr=203.0.113.10"}):
                    settings = settings_from_env()
                self.assertEqual(settings.environment, environment)
                self.assertNotIn("writer@", repr(settings))

    def test_runtime_hostname_requires_numeric_hostaddr(self):
        values = {
            "ORACLE_DATABASE_URL": "postgresql://writer@db.example/oracle",
            "ORACLE_DATABASE_ENVIRONMENT": "local",
            "VERCEL_ENV": "local",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(DatabaseConfigurationError,
                                       "runtime_database_address_required"):
                settings_from_env()

    def test_runtime_address_must_be_explicit(self):
        values = {
            "ORACLE_DATABASE_URL": "postgresql:///oracle",
            "ORACLE_DATABASE_ENVIRONMENT": "local", "VERCEL_ENV": "local",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(DatabaseConfigurationError,
                                       "runtime_database_address_required"):
                settings_from_env()


if __name__ == "__main__":
    unittest.main()
