"""Local-only JPL backend contract, isolation, and API tests."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "astrology" / "jpl" / "data" / "de440s.bsp"
JPL_AVAILABLE = (
    KERNEL.is_file()
    and importlib.util.find_spec("skyfield") is not None
    and importlib.util.find_spec("jplephem") is not None
)
CURRENT = {
    "chart_kind": "current",
    "instant_utc": "2000-01-01T12:00:00Z",
    "location": {"latitude": 33.45, "longitude": -112.07},
}


@unittest.skipUnless(JPL_AVAILABLE, "optional JPL backend dependencies or kernel missing")
class JPLContractTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "ORACLE_ASTROLOGY_BACKEND": "jpl",
                "ORACLE_JPL_KERNEL_PATH": str(KERNEL),
                "ORACLE_ASTROLOGY_ENABLED": "1",
                "ORACLE_ANALYTICS_ENABLED": "0",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_chart_matches_existing_western_contract(self):
        from astrology.service import prepare_chart

        chart = prepare_chart(CURRENT)
        self.assertEqual(chart["schema_version"], 1)
        self.assertEqual(chart["chart_kind"], "current")
        self.assertEqual(chart["tradition"], "western")
        self.assertEqual(chart["zodiac"], "tropical")
        self.assertEqual(chart["inputs"]["instant"], "2000-01-01T12:00:00+00:00")
        self.assertEqual(chart["inputs"]["utc"], "2000-01-01T12:00:00Z")
        self.assertEqual(chart["engine"]["library"], "Quantum Oracle Ephemeris")
        self.assertEqual(chart["engine"]["library_version"], "1.0.0")
        self.assertEqual(chart["engine"]["engine_version"], "1.0.0")
        self.assertEqual(chart["engine"]["binding"], "jplephem")
        self.assertEqual(chart["engine"]["binding_version"], "2.24")
        self.assertEqual(chart["engine"]["ephemeris_model"], "JPL DE440s")
        self.assertEqual(
            set(chart["planets"]),
            {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"},
        )
        self.assertEqual(len(chart["whole_sign_cusps"]), 12)
        self.assertIn(chart["lunar_phase"]["label"], {
            "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
            "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
        })
        self.assertTrue(chart["major_aspects"])
        for aspect in chart["major_aspects"]:
            self.assertEqual(
                set(aspect),
                {"body_1", "body_2", "aspect", "separation", "exact_angle", "orb", "orb_limit"},
            )
        serialized = json.dumps(chart, allow_nan=False)
        self.assertNotIn(str(KERNEL), serialized)

        from astrology.reading import build_interpretation_prompt

        prompt = build_interpretation_prompt(chart, "PRIVATE-QUESTION")
        for private in ("2000-01-01", "33.45", "-112.07"):
            self.assertNotIn(private, prompt)
        self.assertIn("PRIVATE-QUESTION", prompt)

    def test_api_capabilities_and_vedic_convention_are_explicit(self):
        from app import app

        client = app.test_client()
        capabilities = client.get("/astrology/capabilities")
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json["traditions"], ["western", "vedic"])
        self.assertEqual(capabilities.json['sidereal_convention']['id'], 'iae-2021')
        self.assertEqual(
            capabilities.json["date_bounds"],
            {"min": "1850-01-01", "max": "2149-12-31"},
        )

        response = client.post(
            "/astrology/chart", json={**CURRENT, "tradition": "vedic"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['chart']['ayanamsa']['convention_id'], 'iae-2021')
        self.assertNotEqual(response.json['chart']['ayanamsa']['name'], 'Lahiri')

    def test_vedic_natal_horoscope_and_prompt_convention(self):
        from app import app
        from astrology.reading import build_interpretation_prompt
        client=app.test_client()
        birth={'local_datetime':'1985-03-28T08:38:01','timezone':'Etc/UTC'}
        natal=client.post('/astrology/chart',json={'chart_kind':'natal','tradition':'vedic',
                         'birth':birth,'location':{'latitude':35,'longitude':-110}})
        self.assertEqual(natal.status_code,200,natal.json)
        chart=natal.json['chart']
        self.assertIn('lord',chart['ascendant']['nakshatra'])
        prompt=build_interpretation_prompt(chart)
        self.assertIn('Indian Astronomical Ephemeris (2021 convention)',prompt)
        self.assertNotIn('Lahiri',prompt)
        self.assertNotIn('1985-03-28',prompt)
        horoscope=client.post('/astrology/chart',json={'chart_kind':'horoscope','tradition':'vedic',
                    'birthday':'1990-03-20','birth':{'local_datetime':'1990-03-20T15:30'},
                    'place_id':'geonames:5368361','instant_utc':'2026-10-04T12:00:00Z'})
        self.assertEqual(horoscope.status_code,200,horoscope.json)
        h=horoscope.json['chart']
        self.assertEqual(h['horoscope']['scope'],'general_moon_sign')
        self.assertNotIn('ascendant',h)
        self.assertTrue(all('moon_sign_house' in x for x in h['planets'].values()))

    def test_vedic_stream_contract_uses_independent_chart(self):
        from app import app
        class Fixture:
            def stream_chat(self,prompt):
                assert 'Indian Astronomical Ephemeris (2021 convention)' in prompt
                yield '[[HEART]] Test fixture. [[DEPTH]] Test fixture detail. [[QUOTE]] Test fixture.'
        with patch('astrology.routes.GeminiOracle',return_value=Fixture()):
            response=app.test_client().post('/astrology/read/stream',json={'chart_request':{
                'chart_kind':'natal','tradition':'vedic','birth':{'local_datetime':'1950-07-15T12:00','timezone':'Etc/UTC'},
                'location':{'latitude':35,'longitude':-110}}},buffered=True)
        text=response.get_data(as_text=True)
        self.assertIn('event: done',text)
        self.assertIn('iae-2021',text)
        self.assertNotIn('event: error',text)

    def test_advertised_western_horoscope_and_transit_modes_calculate(self):
        from app import app

        client = app.test_client()
        horoscope = client.post(
            "/astrology/chart",
            json={
                "chart_kind": "horoscope",
                "birthday": "1985-07-23",
                "instant_utc": "2026-10-04T17:17:36Z",
            },
        )
        self.assertEqual(horoscope.status_code, 200, horoscope.json)
        self.assertEqual(horoscope.json["chart"]["chart_kind"], "horoscope")
        self.assertEqual(horoscope.json["chart"]["horoscope"]["scope"], "general_sun_sign")

        transit = client.post(
            "/astrology/chart",
            json={
                "chart_kind": "transit",
                "natal_request": {
                    "chart_kind": "natal",
                    "birth": {"local_datetime": "2000-01-01T03:17:19"},
                    "place_id": "geonames:5314328",
                },
                "instant_utc": "2026-10-04T17:17:36Z",
            },
        )
        self.assertEqual(transit.status_code, 200, transit.json)
        self.assertEqual(transit.json["chart"]["chart_kind"], "transit")
        self.assertEqual(transit.json["chart"]["natal_chart"]["chart_kind"], "natal")
        self.assertTrue(transit.json["chart"]["transit_aspects"])

    def test_dependency_failure_does_not_disclose_kernel_path(self):
        from app import app

        marker = "PRIVATE-JPL-KERNEL-PATH"
        with patch.dict(os.environ, {"ORACLE_JPL_KERNEL_PATH": f"/tmp/{marker}.bsp"}):
            response = app.test_client().post("/astrology/chart", json=CURRENT)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "astrology_unavailable")
        self.assertNotIn(marker, response.get_data(as_text=True))

    def test_kernel_instance_is_shared_across_request_threads(self):
        from astrology.jpl_adapter import _pilot

        with ThreadPoolExecutor(max_workers=8) as executor:
            instances = list(executor.map(lambda _: _pilot(), range(32)))
        self.assertEqual(len({id(instance) for instance in instances}), 1)

    def test_natal_dst_resolution_remains_stdlib_only(self):
        from astrology.service import ChartInputError, prepare_chart

        request = {
            "chart_kind": "natal",
            "birth": {
                "local_datetime": "2024-11-03T01:30:00",
                "timezone": "America/New_York",
            },
            "location": {"latitude": 40.7128, "longitude": -74.006},
        }
        with self.assertRaises(ChartInputError) as raised:
            prepare_chart(request)
        self.assertEqual(raised.exception.code, "ambiguous_birth_time")
        first = prepare_chart({**request, "birth": {**request["birth"], "fold": 0}})
        second = prepare_chart({**request, "birth": {**request["birth"], "fold": 1}})
        self.assertEqual(first["inputs"]["utc"], "2024-11-03T05:30:00Z")
        self.assertEqual(second["inputs"]["utc"], "2024-11-03T06:30:00Z")

    def test_complete_api_calculation_never_imports_swiss_engine(self):
        script = """
import os, sys
os.environ.update(ORACLE_ASTROLOGY_BACKEND='jpl', ORACLE_JPL_KERNEL_PATH=r'%s', ORACLE_ASTROLOGY_ENABLED='1', ORACLE_ANALYTICS_ENABLED='0')
from app import app
response = app.test_client().post('/astrology/chart', json=%r)
assert response.status_code == 200, response.get_data(as_text=True)
assert response.json['chart']['engine']['library'] == 'Quantum Oracle Ephemeris'
assert 'astrology.engine' not in sys.modules
assert 'swisseph' not in sys.modules
response = app.test_client().post('/astrology/chart', json={**%r, 'tradition':'vedic'})
assert response.status_code == 200
assert 'astrology.engine' not in sys.modules and 'swisseph' not in sys.modules
""" % (str(KERNEL), CURRENT, CURRENT)
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
