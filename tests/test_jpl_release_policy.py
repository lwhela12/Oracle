"""Release checks for historical qualifications and pinned time-data health."""
from datetime import date
import json
import importlib.util
import os
import unittest
from unittest.mock import patch


class ReleasePolicyTests(unittest.TestCase):
    def test_expiry_and_refresh_window(self):
        from astrology.time_health import time_health
        with patch('astrology.time_health._data_version', return_value=('2027-01-23', 'test-hash', '1.55')):
            self.assertEqual(time_health(today=date(2026,10,4))['status'], 'healthy')
            self.assertEqual(time_health(today=date(2026,12,20))['status'], 'refresh_due')
            self.assertEqual(time_health(today=date(2027,1,23))['status'], 'expired')

    @unittest.skipUnless(importlib.util.find_spec('skyfield'), 'optional JPL dependencies unavailable')
    def test_historical_horoscope_keeps_safe_natal_time_qualification(self):
        from astrology.horoscopes import prepare_horoscope, horoscope_facts
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_BACKEND':'jpl'}):
            chart = prepare_horoscope({'chart_kind':'horoscope','tradition':'vedic',
                'birthday':'1850-07-15','birth':{'local_datetime':'1850-07-15T12:00'},
                'place_id':'geonames:5368361','instant_utc':'2026-10-04T12:00:00Z'})
        policy = chart['provenance']['natal_calculation']['time_policy']
        self.assertEqual(policy['input_scale'], 'historical civil UT1 approximation')
        self.assertTrue(any('Natal calculation: Before 1961' in w for w in chart['provenance']['warnings']))
        safe = json.dumps({'provenance':chart['provenance'], 'facts':horoscope_facts(chart)})
        for private in ('1850-07-15','Los Angeles','geonames:5368361','America/Los_Angeles'):
            self.assertNotIn(private, safe)

    @unittest.skipUnless(importlib.util.find_spec('skyfield'), 'optional JPL dependencies unavailable')
    def test_station_uncertainty_survives_prompt_projection(self):
        from astrology.reading import interpretation_facts
        from astrology.service import prepare_chart
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_BACKEND':'jpl'}):
            chart = prepare_chart({'chart_kind':'current','instant_utc':'2026-10-04T12:00:00Z'})
        chart['planets']['Mercury']['station_uncertain'] = True
        self.assertTrue(interpretation_facts(chart)['planets']['Mercury']['station_uncertain'])

    @unittest.skipUnless(importlib.util.find_spec('skyfield'), 'optional JPL dependencies unavailable')
    def test_health_probes_real_engine_and_expires_time_data(self):
        from app import app
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_BACKEND':'jpl','ORACLE_ASTROLOGY_ENABLED':'1'}):
            result = app.test_client().get('/astrology/health')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json['engine']['ephemeris_model'], 'JPL DE440s')
            with patch('astrology.time_health.time_health', return_value={'status':'expired'}):
                self.assertEqual(app.test_client().get('/astrology/health').status_code,503)
