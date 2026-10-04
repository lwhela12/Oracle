from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch

from experiments.astrology import cloud


def _hosted_points(longitude: float = 10.0):
    return {
        name: {
            "pointId": name,
            "longitude": longitude,
            "speedLongitude": 1.0,
            "retrograde": False,
        }
        for name in cloud.PLANET_IDS
    }


def _hosted_chart(longitude: float = 10.0):
    return {
        "points": _hosted_points(longitude),
        "angles": {
            "ascendant": {"longitude": longitude},
            "midheaven": {"longitude": longitude},
        },
        "houses": {
            "cusps": [
                {"longitude": (longitude + index * 30.0) % 360.0}
                for index in range(12)
            ]
        },
    }


def _response(longitude: float = 10.0):
    return {"data": _hosted_chart(longitude)}


def _local_chart(longitude: float = 10.0):
    return {
        "planets": {
            name.capitalize(): {
                "longitude": longitude,
                "speed_degrees_per_day": 1.0,
                "retrograde": False,
            }
            for name in cloud.PLANET_IDS
        },
        "ascendant": {"longitude": longitude},
        "midheaven": {"longitude": longitude},
        "whole_sign_cusps": [
            {"house": index + 1, "longitude": (longitude + index * 30.0) % 360.0}
            for index in range(12)
        ],
    }


class FetchChartTests(unittest.TestCase):
    @patch("experiments.astrology.cloud.requests.post")
    def test_fixed_request_parameters_and_real_usage_headers(self, post):
        response = Mock(status_code=200)
        response.headers = {
            "X-RateLimit-Limit": "60",
            "X-Quota-Remaining": "149999",
            "Unrelated": "ignore-me",
        }
        response.json.return_value = _response()
        post.return_value = response

        result = cloud.fetch_chart(
            datetime(2026, 10, 4, 10, 30, tzinfo=timezone(timedelta(hours=-7))),
            36.1699,
            -115.1398,
            "secret-test-key",
        )

        post.assert_called_once_with(
            cloud.ENDPOINT,
            headers={
                "X-Api-Key": "secret-test-key",
                "Content-Type": "application/json",
            },
            json={
                "dateTime": "2026-10-04T17:30",
                "location": {
                    "latitude": 36.1699,
                    "longitude": -115.1398,
                    "timezone": "UTC",
                },
                "houseSystem": "whole",
                "moonCenter": "geocentric",
                "includeText": False,
                "includeReadableEntities": False,
                "points": list(cloud.PLANET_IDS),
            },
            timeout=cloud.REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        self.assertNotIn("secret-test-key", repr(result))
        self.assertEqual(
            result["usage"],
            {"X-RateLimit-Limit": "60", "X-Quota-Remaining": "149999"},
        )
        self.assertEqual(result["status"], 200)

    @patch("experiments.astrology.cloud.requests.post")
    def test_inputs_fail_before_network(self, post):
        cases = (
            (datetime(2026, 1, 1), 0, 0, "key"),
            (datetime.now(timezone.utc), 91, 0, "key"),
            (datetime.now(timezone.utc), 0, -181, "key"),
            (datetime.now(timezone.utc), 0, 0, ""),
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                cloud.fetch_chart(*args)
        post.assert_not_called()

    @patch("experiments.astrology.cloud.requests.post")
    def test_seconds_are_not_silently_discarded(self, post):
        with self.assertRaisesRegex(ValueError, "minute precision"):
            cloud.fetch_chart(datetime(2026, 10, 4, 17, 17, 36, tzinfo=timezone.utc), 0, 0, "key")
        post.assert_not_called()

    @patch("experiments.astrology.cloud.requests.post")
    def test_redacted_http_error_does_not_echo_response_or_key(self, post):
        response = Mock(status_code=401)
        response.headers = {}
        response.text = 'invalid key secret-test-key'
        post.return_value = response

        with self.assertRaises(cloud.AstroApiError) as caught:
            cloud.fetch_chart(datetime(2026, 10, 4, tzinfo=timezone.utc), 0, 0, "secret-test-key")
        message = str(caught.exception)
        self.assertEqual(message, "AstroAPI request failed with HTTP 401")
        self.assertNotIn("secret-test-key", message)
        response.json.assert_not_called()

    @patch("experiments.astrology.cloud.requests.post")
    def test_success_without_complete_valid_planets_is_rejected(self, post):
        response = Mock(status_code=200, headers={})
        response.json.return_value = {"data": {"points": {"sun": {"longitude": 10.0}}}}
        post.return_value = response

        with self.assertRaisesRegex(cloud.AstroApiError, "invalid planet data"):
            cloud.fetch_chart(datetime(2026, 10, 4, tzinfo=timezone.utc), 0, 0, "key")


class CompareChartTests(unittest.TestCase):
    def test_wraparound_uses_shortest_angular_deviation(self):
        local = _local_chart(359.995)
        hosted = {"response": _response(0.005)}

        result = cloud.compare_chart(local, hosted, tolerance_degrees=0.011)

        self.assertTrue(result["complete"])
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(
            result["deviations"]["planets"]["sun"]["deviation_degrees"], 0.01
        )

    def test_incomplete_response_cannot_false_pass(self):
        hosted = {"response": _response()}
        del hosted["response"]["data"]["angles"]["midheaven"]

        result = cloud.compare_chart(_local_chart(), hosted)

        self.assertFalse(result["complete"])
        self.assertFalse(result["within_tolerance"])
        self.assertIn("hosted.data.angles.midheaven.longitude", result["missing"])

    def test_outside_tolerance_is_complete_but_fails(self):
        result = cloud.compare_chart(_local_chart(10.0), {"response": _response(10.02)})

        self.assertTrue(result["complete"])
        self.assertFalse(result["within_tolerance"])

    def test_opposite_speed_signs_and_retrograde_flags_are_reported(self):
        local = _local_chart()
        local["planets"]["Mercury"]["speed_degrees_per_day"] = -0.00001
        local["planets"]["Mercury"]["retrograde"] = True
        hosted = {"response": _response()}
        hosted["response"]["data"]["points"]["mercury"]["speedLongitude"] = 0.00001

        result = cloud.compare_chart(local, hosted)
        mercury = result["deviations"]["planets"]["mercury"]

        self.assertTrue(result["complete"])
        self.assertFalse(result["within_tolerance"])
        self.assertEqual(mercury["local_speed_sign"], "negative")
        self.assertEqual(mercury["hosted_speed_sign"], "positive")
        self.assertFalse(mercury["speed_sign_match"])
        self.assertFalse(mercury["retrograde_match"])
        self.assertAlmostEqual(mercury["speed_deviation_degrees_per_day"], 0.00002)

    def test_missing_retrograde_data_makes_comparison_incomplete(self):
        hosted = {"response": _response()}
        del hosted["response"]["data"]["points"]["saturn"]["retrograde"]

        result = cloud.compare_chart(_local_chart(), hosted)

        self.assertFalse(result["complete"])
        self.assertFalse(result["within_tolerance"])
        self.assertIn("hosted.data.points.saturn.retrograde", result["missing"])


if __name__ == "__main__":
    unittest.main()
