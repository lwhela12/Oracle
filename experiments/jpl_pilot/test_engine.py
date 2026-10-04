"""Offline pilot qualification, including external numerical references."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from skyfield.framelib import ecliptic_frame
from engine import JPLPilot, angles, mean_node, signed_difference, mean_ecliptic_rotation

UTC = timezone.utc


class PilotChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = JPLPilot('scratch/jpl-pilot/de440s.bsp')

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_no_swiss_dependency_installed(self):
        self.assertIsNone(importlib.util.find_spec('swisseph'), 'Run this suite in the isolated JPL environment')

    def test_startup_and_reading_without_network(self):
        with patch('socket.socket', side_effect=AssertionError('Runtime network access attempted')):
            isolated=JPLPilot('scratch/jpl-pilot/de440s.bsp')
            try:
                self.assertEqual(len(isolated.chart(datetime(2026,1,1,tzinfo=UTC))['planets']),10)
            finally:
                isolated.close()

    def test_external_horizons_longitudes(self):
        fixture = json.loads(Path(__file__).with_name('horizons_fixture.json').read_text())
        self.assertEqual(len(fixture['rows']), 30)
        for row in fixture['rows']:
            with self.subTest(body=row['body'], time=row['utc_horizons']):
                dt = datetime.strptime(row['utc_horizons'], '%Y-%b-%d %H:%M:%S.%f').replace(tzinfo=UTC)
                actual = self.engine.chart(dt)['planets'][row['body']]['longitude']
                self.assertLess(abs(signed_difference(actual,row['longitude']))*3600, 1.0)

    def test_horizon_and_upper_meridian_geometry(self):
        for year in (1900,2000,2026):
            t = self.engine.ts.utc(year,3,20)
            for lat in (-85,-45,0,45,85):
                for lon in (-179,0,179):
                    asc,mc = angles(t,lat,lon)
                    transform = t.M @ ecliptic_frame.rotation_at(t).T
                    def equatorial(deg):
                        rad=math.radians(deg)
                        v=transform @ np.array([math.cos(rad),math.sin(rad),0.0])
                        return math.atan2(v[1],v[0]), math.asin(v[2])
                    ra,dec=equatorial(asc)
                    theta=math.radians(t.gast*15+lon)
                    phi=math.radians(lat)
                    h=theta-ra
                    altitude_sine=math.sin(phi)*math.sin(dec)+math.cos(phi)*math.cos(dec)*math.cos(h)
                    self.assertAlmostEqual(altitude_sine,0,places=10)
                    self.assertGreater(-math.cos(dec)*math.sin(h),0)  # east half
                    ra,dec=equatorial(mc)
                    self.assertAlmostEqual(math.cos(theta-ra),1,places=10)

    def test_known_mean_node_polynomial_values(self):
        for centuries,expected in [(-1,259.1828904373915),(0,125.04455501),(1,350.9103707718359)]:
            self.assertAlmostEqual(mean_node(2451545+36525*centuries),expected,places=9)

    def test_mean_and_true_frame_order_is_safe(self):
        t=self.engine.ts.tt(1956,3,21)
        mean=mean_ecliptic_rotation(t)
        true=ecliptic_frame.rotation_at(t)
        self.assertTrue(np.isfinite(true).all())
        np.testing.assert_allclose(mean @ mean.T,np.eye(3),atol=1e-12)

    def test_vedic_is_explicitly_experimental(self):
        dt=datetime(2026,3,22,tzinfo=UTC)
        with self.assertRaises(ValueError): self.engine.chart(dt,tradition='lahiri')
        chart=self.engine.chart(dt,tradition='sidereal-experimental')
        self.assertIn('Experimental',chart['ayanamsa']['name'])
        self.assertEqual(len(chart['planets']),9)
        self.assertAlmostEqual(abs(signed_difference(chart['planets']['Rahu']['longitude'],chart['planets']['Ketu']['longitude'])),180)
        self.assertIn('mean lunar node',chart['planets']['Rahu']['coordinate_model'])
        official=self.engine.chart(dt,35,-110,tradition='vedic')
        self.assertEqual(official['ayanamsa']['convention_id'],'iae-2021')
        self.assertIn('lord',official['ascendant']['nakshatra'])
        self.assertTrue(official['vedic_aspects'])

    def test_input_validation_and_range(self):
        dt=datetime(2000,1,1,tzinfo=UTC)
        for instant in (datetime(2000,1,1), datetime(1849,12,31,tzinfo=UTC), datetime(2150,1,1,tzinfo=UTC)):
            with self.assertRaises(ValueError): self.engine.chart(instant)
        for lat,lon in [(0,None),(90,0),(float('nan'),0),(0,181),(True,0)]:
            with self.assertRaises(ValueError): self.engine.chart(dt,lat,lon)
        for instant in (datetime(1850,1,1,tzinfo=UTC), datetime(2149,12,31,23,59,59,tzinfo=UTC)):
            self.assertEqual(len(self.engine.chart(instant)['planets']),10)

    def test_checksum_rejects_wrong_kernel(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'not the pinned ephemeris'); f.flush()
            with self.assertRaisesRegex(ValueError,'checksum'): JPLPilot(f.name)

    def test_no_local_fields_for_global_sky(self):
        chart=self.engine.chart(datetime(2000,1,1,tzinfo=UTC))
        self.assertNotIn('ascendant',chart)
        self.assertNotIn('whole_sign_cusps',chart)
        self.assertTrue(all('whole_sign_house' not in x for x in chart['planets'].values()))

    def test_sign_boundary_and_longitude_wrap(self):
        start=datetime(2024,3,19,tzinfo=UTC); end=datetime(2024,3,21,tzinfo=UTC)
        # Find this engine's vernal-equinox crossing, then exercise both sides.
        for _ in range(24):
            mid=start+(end-start)/2
            if self.engine.chart(mid)['planets']['Sun']['longitude']>180: start=mid
            else: end=mid
        before=self.engine.chart(start-timedelta(minutes=1))['planets']['Sun']
        after=self.engine.chart(end+timedelta(minutes=1))['planets']['Sun']
        self.assertEqual(before['sign'],'Pisces'); self.assertEqual(after['sign'],'Aries')
        self.assertGreater(before['speed_degrees_per_day'],0)
        self.assertLess(abs(after['speed_degrees_per_day']-before['speed_degrees_per_day']),1e-4)

    def test_mercury_station_and_step_stability(self):
        start=datetime(2024,4,1,tzinfo=UTC); end=datetime(2024,4,3,tzinfo=UTC)
        for _ in range(24):
            mid=start+(end-start)/2
            if self.engine.chart(mid)['planets']['Mercury']['speed_degrees_per_day']>0: start=mid
            else: end=mid
        before=self.engine.chart(start-timedelta(minutes=10))['planets']['Mercury']
        after=self.engine.chart(end+timedelta(minutes=10))['planets']['Mercury']
        self.assertFalse(before['retrograde']); self.assertTrue(after['retrograde'])
        station=self.engine.chart(end)['planets']['Mercury']
        self.assertTrue(station['station_uncertain'])
        speeds=[self.engine.chart(end,speed_step_days=h)['planets']['Mercury']['speed_degrees_per_day'] for h in (0.0001,0.001,0.01)]
        self.assertLess(max(speeds)-min(speeds),1e-5)

    def test_repeatability_across_threads(self):
        times=[datetime(2026,1,1,tzinfo=UTC)+timedelta(days=i*13) for i in range(12)]
        def calculate(dt): return self.engine.chart(dt,35,-110)
        expected=list(map(calculate,times))
        with ThreadPoolExecutor(max_workers=4) as pool:
            actual=list(pool.map(calculate,times))
        self.assertEqual(actual,expected)


if __name__=='__main__': unittest.main()
