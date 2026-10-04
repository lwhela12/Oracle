"""Focused tests for the isolated astrology calculation experiment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import unittest

from experiments.astrology.calculations import (
    calculate_chart,
    calculate_major_aspects,
    resolve_local_datetime,
    whole_sign_cusps,
    whole_sign_house,
)


class ChartCalculationTests(unittest.TestCase):
    def test_timezone_equivalent_instants_produce_the_same_sky(self) -> None:
        utc = datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc)
        eastern = datetime(
            2024, 6, 1, 8, 30, tzinfo=timezone(timedelta(hours=-4))
        )
        first = calculate_chart(utc, 36.1699, -115.1398)
        second = calculate_chart(eastern, 36.1699, -115.1398)

        self.assertEqual(first["inputs"]["utc"], second["inputs"]["utc"])
        self.assertEqual(first["planets"], second["planets"])
        self.assertEqual(first["ascendant"], second["ascendant"])

    def test_planet_positions_are_global_while_angles_are_local(self) -> None:
        instant = datetime(2025, 1, 15, 18, 0, tzinfo=timezone.utc)
        las_vegas = calculate_chart(instant, 36.1699, -115.1398)
        london = calculate_chart(instant, 51.5074, -0.1278)

        for name in las_vegas["planets"]:
            self.assertEqual(
                las_vegas["planets"][name]["longitude"],
                london["planets"][name]["longitude"],
            )
            self.assertEqual(
                las_vegas["planets"][name]["speed_degrees_per_day"],
                london["planets"][name]["speed_degrees_per_day"],
            )
        self.assertNotEqual(
            las_vegas["ascendant"]["longitude"], london["ascendant"]["longitude"]
        )
        self.assertNotEqual(
            las_vegas["midheaven"]["longitude"], london["midheaven"]["longitude"]
        )

    def test_j2000_sun_matches_usno_published_approximation(self) -> None:
        # USNO's published J2000 formula gives 280.3747 degrees at D=0 and is
        # stated accurate to about 1 arcminute within two centuries of 2000:
        # https://aa.usno.navy.mil/faq/sun_approx
        chart = calculate_chart(
            datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc), 0.0, 0.0
        )
        self.assertAlmostEqual(
            chart["planets"]["Sun"]["longitude"], 280.3747143, delta=0.02
        )
        self.assertEqual(chart["lunar_phase"]["label"], "Waning Crescent")
        self.assertGreaterEqual(chart["lunar_phase"]["angle"], 292.5)
        self.assertLess(chart["lunar_phase"]["angle"], 337.5)

    def test_retrograde_flag_is_derived_from_longitudinal_speed(self) -> None:
        chart = calculate_chart(
            datetime(2024, 4, 15, 12, 0, tzinfo=timezone.utc), 36.1699, -115.1398
        )
        mercury = chart["planets"]["Mercury"]
        self.assertLess(mercury["speed_degrees_per_day"], 0.0)
        self.assertTrue(mercury["retrograde"])
        for planet in chart["planets"].values():
            self.assertEqual(
                planet["retrograde"], planet["speed_degrees_per_day"] < 0.0
            )

    def test_chart_is_json_safe_and_reports_requested_engine(self) -> None:
        chart = calculate_chart(
            datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc), 36.1699, -115.1398
        )
        json.dumps(chart, allow_nan=False)
        self.assertIn("Moshier", chart["engine"]["ephemeris_model"])
        self.assertEqual(chart["provenance"]["warnings"], [])
        self.assertEqual(len(chart["whole_sign_cusps"]), 12)
        self.assertEqual(
            set(chart["planets"]),
            {
                "Sun",
                "Moon",
                "Mercury",
                "Venus",
                "Mars",
                "Jupiter",
                "Saturn",
                "Uranus",
                "Neptune",
                "Pluto",
            },
        )

    def test_naive_time_and_bad_coordinates_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            calculate_chart(datetime(2024, 1, 1, 12, 0), 0.0, 0.0)
        for latitude, longitude in (
            (math.nan, 0.0), (0.0, math.inf), (90.0, 0.0), (0.0, 180.1)
        ):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    calculate_chart(
                        datetime(2024, 1, 1, tzinfo=timezone.utc),
                        latitude,
                        longitude,
                    )


class ConventionTests(unittest.TestCase):
    def test_aspects_use_shortest_wraparound_separation(self) -> None:
        aspects = calculate_major_aspects({"A": 359.0, "B": 1.0, "C": 179.0})
        indexed = {(item["body_1"], item["body_2"]): item for item in aspects}
        self.assertEqual(indexed[("A", "B")]["aspect"], "conjunction")
        self.assertAlmostEqual(indexed[("A", "B")]["separation"], 2.0)
        self.assertAlmostEqual(indexed[("A", "B")]["orb"], 2.0)
        self.assertEqual(indexed[("A", "C")]["aspect"], "opposition")
        self.assertAlmostEqual(indexed[("A", "C")]["separation"], 180.0)

    def test_whole_sign_cusps_and_house_assignment_wrap(self) -> None:
        self.assertEqual(
            whole_sign_cusps(359.9),
            [
                330.0,
                0.0,
                30.0,
                60.0,
                90.0,
                120.0,
                150.0,
                180.0,
                210.0,
                240.0,
                270.0,
                300.0,
            ],
        )
        self.assertEqual(whole_sign_house(359.0, 359.9), 1)
        self.assertEqual(whole_sign_house(0.0, 359.9), 2)
        self.assertEqual(whole_sign_house(329.999, 359.9), 12)


class LocalTimeResolutionTests(unittest.TestCase):
    def test_nonexistent_dst_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonexistent local time"):
            resolve_local_datetime("2024-03-10T02:30:00", "America/Los_Angeles")

    def test_ambiguous_dst_time_requires_fold(self) -> None:
        with self.assertRaisesRegex(ValueError, "ambiguous local time"):
            resolve_local_datetime("2024-11-03T01:30:00", "America/Los_Angeles")
        first = resolve_local_datetime(
            "2024-11-03T01:30:00", "America/Los_Angeles", fold=0
        )
        second = resolve_local_datetime(
            "2024-11-03T01:30:00", "America/Los_Angeles", fold=1
        )
        self.assertEqual(
            second.astimezone(timezone.utc) - first.astimezone(timezone.utc),
            timedelta(hours=1),
        )

    def test_unambiguous_local_time_resolves_normally(self) -> None:
        local = resolve_local_datetime(
            "2024-07-01T09:15:00", "America/Los_Angeles"
        )
        self.assertEqual(
            local.astimezone(timezone.utc),
            datetime(2024, 7, 1, 16, 15, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
