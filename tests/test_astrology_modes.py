"""End-to-end Flask route contracts for transit and horoscope modes."""

from copy import deepcopy
import importlib.util
import json
import os
import unittest
import uuid
from unittest.mock import patch

from app import app


TRANSIT = {
    "chart_kind": "transit",
    "natal_request": {
        "chart_kind": "natal",
        "birth": {"local_datetime": "2000-01-01T03:17:19"},
        "place_id": "geonames:5314328",
    },
    "instant_utc": "2026-10-04T17:17:36Z",
}
HOROSCOPE = {
    "chart_kind": "horoscope",
    "birthday": "1985-07-23",
    "instant_utc": "2026-10-04T17:17:36Z",
}


def events(response):
    parsed = []
    for block in response.get_data(as_text=True).strip().split("\n\n"):
        lines = block.splitlines()
        parsed.append(
            (
                lines[0].removeprefix("event: "),
                json.loads(lines[1].removeprefix("data: ")),
            )
        )
    return parsed


class FakeOracle:
    init_count = 0
    prompts = []

    def __init__(self):
        type(self).init_count += 1

    @classmethod
    def reset(cls):
        cls.init_count = 0
        cls.prompts = []

    def stream_chat(self, prompt):
        type(self).prompts.append(prompt)
        yield "first"
        yield " second"


class ModeRouteBase(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "ORACLE_ASTROLOGY_ENABLED": "1",
                "ORACLE_ANALYTICS_ENABLED": "0",
                "GEMINI_API_KEY": "test-only-key",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = app.test_client()
        FakeOracle.reset()
        network = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Unexpected network call"),
        )
        network.start()
        self.addCleanup(network.stop)


class AstrologyModeGateTests(ModeRouteBase):
    def test_default_off_blocks_both_modes_before_calculation_or_model(self):
        with patch.dict(os.environ, {"ORACLE_ASTROLOGY_ENABLED": "0"}), patch(
            "astrology.routes._prepare"
        ) as prepare, patch("astrology.routes.GeminiOracle", FakeOracle):
            for chart_request in (TRANSIT, HOROSCOPE):
                with self.subTest(kind=chart_request["chart_kind"], endpoint="chart"):
                    response = self.client.post(
                        "/astrology/chart", json=chart_request
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.json["code"], "astrology_disabled")
                with self.subTest(kind=chart_request["chart_kind"], endpoint="stream"):
                    response = self.client.post(
                        "/astrology/read/stream",
                        json={"chart_request": chart_request},
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.json["code"], "astrology_disabled")
            prepare.assert_not_called()
            self.assertEqual(FakeOracle.init_count, 0)
            self.assertEqual(FakeOracle.prompts, [])


@unittest.skipUnless(
    importlib.util.find_spec("swisseph")
    and importlib.util.find_spec("geonamescache"),
    "Optional astrology calculation dependencies are not installed",
)
class AstrologyModeRouteTests(ModeRouteBase):
    def test_actual_chart_post_replays_both_modes_without_model_calls(self):
        with patch("astrology.routes.GeminiOracle", FakeOracle):
            for chart_request in (TRANSIT, HOROSCOPE):
                with self.subTest(kind=chart_request["chart_kind"]):
                    first = self.client.post(
                        "/astrology/chart", json=deepcopy(chart_request)
                    )
                    second = self.client.post(
                        "/astrology/chart", json=deepcopy(chart_request)
                    )
                    self.assertEqual(first.status_code, 200, first.json)
                    self.assertEqual(second.status_code, 200, second.json)
                    self.assertEqual(first.json["type"], "astrology")
                    self.assertEqual(
                        first.json["chart_kind"], chart_request["chart_kind"]
                    )
                    self.assertEqual(first.json["chart"], second.json["chart"])
                    self.assertNotEqual(first.json["chart_id"], second.json["chart_id"])
                    uuid.UUID(first.json["chart_id"])
                    uuid.UUID(second.json["chart_id"])
                    self.assertEqual(first.headers["Cache-Control"], "no-store")
        self.assertEqual(FakeOracle.init_count, 0)
        self.assertEqual(FakeOracle.prompts, [])

    def test_invalid_mode_inputs_are_http_errors_before_model(self):
        transit_placements = deepcopy(TRANSIT)
        transit_placements["natal_request"]["planets"] = {
            "Sun": {"longitude": 0}
        }
        invalid_timezone = {
            "chart_kind": "transit",
            "natal_request": {
                "chart_kind": "natal",
                "birth": {
                    "local_datetime": "2000-01-01T03:17:19",
                    "timezone": "Invalid/PRIVATE",
                },
                "location": {"latitude": 33.45, "longitude": -112.07},
            },
            "instant_utc": "2026-10-04T17:17:36Z",
        }
        invalid = (
            (transit_placements, "invalid_request"),
            (invalid_timezone, "invalid_timezone"),
            (
                {
                    "chart_kind": "horoscope",
                    "birthday": "1985-02-30",
                    "instant_utc": "2026-10-04T17:17:36Z",
                },
                "invalid_birthday",
            ),
            (
                {
                    **HOROSCOPE,
                    "birth_time": "PRIVATE-TIME",
                },
                "invalid_request",
            ),
        )
        with patch("astrology.routes.GeminiOracle", FakeOracle):
            for chart_request, code in invalid:
                with self.subTest(kind=chart_request["chart_kind"], code=code):
                    response = self.client.post(
                        "/astrology/read/stream",
                        json={"chart_request": chart_request},
                    )
                    self.assertEqual(response.status_code, 400, response.json)
                    self.assertEqual(response.json["code"], code)
                    self.assertNotIn("PRIVATE", response.get_data(as_text=True))
        self.assertEqual(FakeOracle.init_count, 0)
        self.assertEqual(FakeOracle.prompts, [])

    def test_streams_metadata_then_tokens_once_and_prompts_are_private(self):
        for chart_request in (TRANSIT, HOROSCOPE):
            with self.subTest(kind=chart_request["chart_kind"]), patch(
                "astrology.routes.GeminiOracle", FakeOracle
            ):
                FakeOracle.reset()
                response = self.client.post(
                    "/astrology/read/stream",
                    json={
                        "chart_request": deepcopy(chart_request),
                        "question": "What should I notice?",
                    },
                )
                stream = events(response)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "text/event-stream")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.headers["X-Accel-Buffering"], "no")
                self.assertEqual(
                    [event for event, _ in stream],
                    ["metadata", "token", "token", "done"],
                )
                metadata = stream[0][1]
                self.assertEqual(metadata["type"], "astrology")
                self.assertEqual(
                    metadata["chart_kind"], chart_request["chart_kind"]
                )
                self.assertEqual(
                    metadata["chart"]["chart_kind"], chart_request["chart_kind"]
                )
                self.assertEqual(stream[1][1]["token"], "first")
                self.assertEqual(stream[2][1]["token"], " second")
                self.assertEqual(stream[3][1], {"done": True})
                self.assertEqual(FakeOracle.init_count, 1)
                self.assertEqual(len(FakeOracle.prompts), 1)

                prompt = FakeOracle.prompts[0]
                self.assertIn('"question":"What should I notice?"', prompt)
                self.assertIn("[[HEART]]", prompt)
                self.assertIn("[[DEPTH]]", prompt)
                self.assertIn("[[QUOTE]]", prompt)

                if chart_request["chart_kind"] == "transit":
                    natal = metadata["chart"]["natal_chart"]
                    forbidden = (
                        chart_request["natal_request"]["birth"]["local_datetime"],
                        "2000-01-01",
                        "03:17:19",
                        natal["place"]["id"],
                        natal["place"]["name"],
                        natal["place"]["region"],
                        natal["place"]["timezone"],
                        str(natal["inputs"]["latitude"]),
                        str(natal["inputs"]["longitude"]),
                    )
                    self.assertIn('"transit_body"', prompt)
                    self.assertIn('"natal_planets"', prompt)
                else:
                    forbidden = (chart_request["birthday"],)
                    self.assertIn('"scope":"general_sun_sign"', prompt)
                    self.assertIn('"sun_sign":"Leo"', prompt)

                for private in forbidden:
                    self.assertNotIn(private, prompt)


if __name__ == "__main__":
    unittest.main()
