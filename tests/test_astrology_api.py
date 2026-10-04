"""Calculation API contracts; synthetic inputs, no model or external provider calls."""
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

from app import app


CURRENT = {'chart_kind': 'current', 'instant_utc': '2000-01-01T12:00:00Z'}
LOCATION = {'latitude': 33.45, 'longitude': -112.07}


def natal(local='2000-01-01T03:00:00', zone='America/Phoenix', **extra):
    return {'chart_kind': 'natal', 'location': LOCATION,
            'birth': {'local_datetime': local, 'timezone': zone, **extra}}


class AstrologyAPIBase(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': '1', 'ORACLE_ANALYTICS_ENABLED': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = app.test_client()
        # The chart must work without constructing a model client or making HTTP calls.
        for target in ('app.get_oracle', 'requests.sessions.Session.request'):
            guard = patch(target, side_effect=AssertionError('Unexpected model/network call'))
            guard.start()
            self.addCleanup(guard.stop)

    def post(self, payload):
        return self.client.post('/astrology/chart', json=payload)


class AstrologyAPITests(AstrologyAPIBase):
    def test_page_is_gated_independently_of_optional_dependencies(self):
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': '0'}):
            self.assertEqual(self.client.get('/astrology/').status_code, 404)
        response = self.client.get('/astrology/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/astrology/astrology.js', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_disabled_does_not_prepare_chart(self):
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': '0'}), patch('astrology.routes.prepare_chart') as prepare:
            response = self.post(CURRENT)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['code'], 'astrology_disabled')
            self.assertFalse(self.client.get('/astrology/capabilities').json['enabled'])
            prepare.assert_not_called()

    def test_chat_never_falls_back_to_numerology(self):
        for enabled, status in [('0', 404), ('1', 409)]:
            with patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': enabled}):
                for route in ('/chat', '/chat/stream'):
                    with self.subTest(enabled=enabled, route=route):
                        self.assertEqual(self.client.post(route, json={'mode': 'astrology'}).status_code, status)

    def test_invalid_requests_rejected_before_native_import(self):
        cases = [None, [], {}, {'chart_kind': 'wrong'}, {**CURRENT, 'birth': {}},
                 {**CURRENT, 'unexpected': 'PRIVATE'}, {**CURRENT, 'instant_utc': '2000-01-01T00:00:00'},
                 {**CURRENT, 'location': {'latitude': True, 'longitude': 0}},
                 {**CURRENT, 'location': {'latitude': 90, 'longitude': 0}},
                 natal(fold=False), natal(local='2000-01-01T03:00:00-07:00')]
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post('/astrology/chart', data=json.dumps(payload), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertNotIn('PRIVATE', response.get_data(as_text=True))

    def test_json_validation_and_size_limit(self):
        for raw in ('{', '{"chart_kind":"current","chart_kind":"natal"}', '{"latitude":NaN}'):
            self.assertEqual(self.client.post('/astrology/chart', data=raw, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/astrology/chart', data='{}').status_code, 415)
        self.assertEqual(self.client.post('/astrology/chart', data=' ' * 8193, content_type='application/json').status_code, 413)

    def test_unavailable_dependency_and_native_failure_are_private(self):
        for error, code in [(ImportError('PRIVATE path'), 'astrology_unavailable'),
                            (RuntimeError('PRIVATE birth detail'), 'calculation_failed')]:
            with patch('astrology.routes.prepare_chart', side_effect=error):
                response = self.post(CURRENT)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json['code'], code)
                self.assertNotIn('PRIVATE', response.get_data(as_text=True))
                self.assertEqual(response.headers['Cache-Control'], 'no-store')


@unittest.skipUnless(importlib.util.find_spec('swisseph'), 'Optional Swiss Ephemeris binding is not installed')
class AstrologyCalculationAPITests(AstrologyAPIBase):
    def test_global_chart_and_replay(self):
        with patch('telemetry.emit') as emit:
            response = self.post(CURRENT)
            emit.assert_not_called()
        self.assertEqual(response.status_code, 200, response.json)
        chart = response.json['chart']
        self.assertEqual(chart['schema_version'], 1)
        self.assertEqual(chart['location_precision'], 'global_no_location')
        for key in ('ascendant', 'midheaven', 'whole_sign_cusps'):
            self.assertNotIn(key, chart)
        self.assertNotIn('latitude', chart['inputs'])
        self.assertTrue(all('whole_sign_house' not in p for p in chart['planets'].values()))
        self.assertEqual(chart, self.post(CURRENT).json['chart'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_current_sky_captures_server_time_once(self):
        from datetime import datetime, timezone
        from astrology.service import prepare_chart
        captured = datetime(2000, 1, 1, 12, 34, 56, 123456, tzinfo=timezone.utc)
        chart = prepare_chart({'chart_kind': 'current'}, now=captured)
        self.assertEqual(chart['inputs']['utc'], '2000-01-01T12:34:56.123456Z')
        self.assertEqual(chart['input_resolution']['time_source'], 'server_clock')

    def test_local_chart_preserves_global_planets(self):
        global_chart = self.post(CURRENT).json['chart']
        response = self.post({**CURRENT, 'location': LOCATION})
        self.assertEqual(response.status_code, 200, response.json)
        chart = response.json['chart']
        self.assertEqual(len(chart['whole_sign_cusps']), 12)
        self.assertIn('ascendant', chart)
        for name, planet in global_chart['planets'].items():
            self.assertEqual(planet, {k: v for k, v in chart['planets'][name].items() if k != 'whole_sign_house'})

    def test_natal_timezone_resolution(self):
        response = self.post(natal())
        self.assertEqual(response.status_code, 200, response.json)
        chart = response.json['chart']
        self.assertEqual(chart['inputs']['utc'], '2000-01-01T10:00:00Z')
        self.assertEqual(chart['input_resolution']['utc_offset_seconds'], -7 * 3600)
        self.assertEqual(chart['input_resolution']['timezone_source'], 'caller_supplied_iana_history')

    def test_dst_and_invalid_timezone(self):
        for payload, code in [(natal(zone='Invalid/PRIVATE'), 'invalid_timezone'),
                              (natal('2024-03-10T02:30:00', 'America/New_York'), 'nonexistent_birth_time'),
                              (natal('2024-11-03T01:30:00', 'America/New_York'), 'ambiguous_birth_time')]:
            response = self.post(payload)
            self.assertEqual(response.status_code, 400, response.json)
            self.assertEqual(response.json['code'], code)
            self.assertNotIn('PRIVATE', response.get_data(as_text=True))
        first = self.post(natal('2024-11-03T01:30:00', 'America/New_York', fold=0)).json['chart']
        second = self.post(natal('2024-11-03T01:30:00', 'America/New_York', fold=1)).json['chart']
        self.assertEqual(first['inputs']['utc'], '2024-11-03T05:30:00Z')
        self.assertEqual(second['inputs']['utc'], '2024-11-03T06:30:00Z')


if __name__ == '__main__':
    unittest.main()
