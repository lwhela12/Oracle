"""Tests for the reusable astrology calculation engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

try:
    from astrology.engine import (
        calculate_chart,
        calculate_sky,
        resolve_local_datetime,
    )
except ModuleNotFoundError as exc:
    if exc.name == "swisseph":
        raise unittest.SkipTest("optional swisseph binding is not installed") from exc
    raise


class GlobalSkyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instant = datetime(2026, 10, 4, 17, 17, 36, tzinfo=timezone.utc)

    def test_global_facts_equal_local_chart_facts(self) -> None:
        sky = calculate_sky(self.instant)
        chart = calculate_chart(self.instant, 36.1699, -115.1398)
        local_planets = {
            name: {
                key: value
                for key, value in planet.items()
                if key != "whole_sign_house"
            }
            for name, planet in chart["planets"].items()
        }

        self.assertEqual(sky["planets"], local_planets)
        self.assertEqual(sky["major_aspects"], chart["major_aspects"])
        self.assertEqual(sky["lunar_phase"], chart["lunar_phase"])
        self.assertEqual(sky["inputs"]["utc"], chart["inputs"]["utc"])
        self.assertEqual(sky["engine"], chart["engine"])

    def test_global_sky_omits_local_fields_and_never_calls_houses(self) -> None:
        with patch(
            "astrology.engine.swe.houses_ex",
            side_effect=AssertionError("global sky requested houses"),
        ):
            sky = calculate_sky(self.instant)

        self.assertNotIn("latitude", sky["inputs"])
        self.assertNotIn("longitude", sky["inputs"])
        self.assertNotIn("house_system", sky["provenance"])
        for field in ("location", "ascendant", "midheaven", "whole_sign_cusps"):
            self.assertNotIn(field, sky)
        self.assertTrue(
            all("whole_sign_house" not in planet for planet in sky["planets"].values())
        )
        json.dumps(sky, allow_nan=False)

    def test_j2000_historical_fixture_matches_published_solar_position(self) -> None:
        sky = calculate_sky(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))

        self.assertAlmostEqual(
            sky["planets"]["Sun"]["longitude"], 280.3747143, delta=0.02
        )
        self.assertEqual(sky["lunar_phase"]["label"], "Waning Crescent")


class EngineValidationTests(unittest.TestCase):
    def test_sky_requires_aware_representable_supported_instant(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            calculate_sky(datetime(2024, 1, 1, 12))
        with self.assertRaisesRegex(ValueError, "represented in UTC"):
            calculate_sky(datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1))))
        with self.assertRaisesRegex(ValueError, "Moshier range"):
            calculate_sky(datetime(3001, 1, 1, tzinfo=timezone.utc))

    def test_chart_rejects_boolean_and_boundary_coordinates(self) -> None:
        instant = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for latitude, longitude in (
            (True, 0.0),
            (0.0, False),
            (-90.0, 0.0),
            (90.0, 0.0),
            (0.0, -180.1),
            (0.0, 180.1),
        ):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    calculate_chart(instant, latitude, longitude)

    def test_boolean_fold_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "fold must be"):
            resolve_local_datetime(
                "2024-11-03T01:30:00", "America/Los_Angeles", fold=True
            )


class PackageImportTests(unittest.TestCase):
    def test_importing_package_does_not_load_native_binding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys, astrology; assert 'swisseph' not in sys.modules",
            ],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
