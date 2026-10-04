from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import unittest
from skyfield.api import load
from time_scales import civil_time, DRIFT_UTC
from engine import JPLPilot, signed_difference

UTC=timezone.utc


class TimePolicyChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.ts=load.timescale(builtin=True)

    def test_usno_published_offsets(self):
        # Independently evaluated USNO table values, including nonzero drift.
        fixtures=[((1961,1,1),1.422818),((1961,1,2),1.424114),
                  ((1962,1,1),1.845858),((1964,1,1),2.765794),
                  ((1966,1,1),4.313170),((1968,2,1),6.185682)]
        for date,expected in fixtures:
            dt=datetime(*date,tzinfo=UTC)
            t,policy=civil_time(self.ts,dt)
            self.assertAlmostEqual(policy['tai_minus_utc_seconds'],expected,places=8)
            nominal=dt.toordinal()+1721424.5
            seconds=(t.whole-nominal)*86400+t.tt_fraction*86400
            self.assertAlmostEqual(seconds,expected+32.184,places=7)

    def test_drift_segment_transitions(self):
        for effective,*_ in DRIFT_UTC[1:]:
            boundary=datetime(*effective,tzinfo=UTC)
            _,before=civil_time(self.ts,boundary-timedelta(microseconds=1))
            _,after=civil_time(self.ts,boundary)
            self.assertNotEqual(before['usno_segment_start'],after['usno_segment_start'])

    def test_pre1961_explicit_ut1_policy(self):
        dt=datetime(1900,1,1,12,tzinfo=UTC)
        t,policy=civil_time(self.ts,dt)
        self.assertAlmostEqual(t.ut1,2415021.0,places=8)
        self.assertIn('UT1 approximation',policy['input_scale'])
        self.assertTrue(policy['warnings'])

    def test_modern_leap_second_and_1972_transition(self):
        t,policy=civil_time(self.ts,datetime(1972,1,1,tzinfo=UTC))
        seconds=(t.whole-2441317.5)*86400+t.tt_fraction*86400
        self.assertAlmostEqual(seconds,42.184,places=7)
        before,_=civil_time(self.ts,datetime(2016,12,31,23,59,59,tzinfo=UTC))
        after,_=civil_time(self.ts,datetime(2017,1,1,tzinfo=UTC))
        self.assertAlmostEqual(((after.whole-before.whole)+(after.tt_fraction-before.tt_fraction))*86400,2,places=7)

    def test_future_rotation_is_explicitly_extrapolated(self):
        _,policy=civil_time(self.ts,datetime(2140,1,1,tzinfo=UTC))
        self.assertTrue(policy['earth_rotation_extrapolated'])
        self.assertTrue(any('future leap seconds' in x for x in policy['warnings']))

    def test_historical_horizons(self):
        file=Path(__file__).with_name('historical_fixture.json')
        self.assertTrue(file.exists(),'Generate the reference fixture first')
        engine=JPLPilot('scratch/jpl-pilot/de440s.bsp')
        try:
            for row in json.loads(file.read_text())['rows']:
                dt=datetime.fromisoformat(row['utc'])
                actual=engine.chart(dt)['planets'][row['body']]['longitude']
                # Different historical Delta T models and frame/ephemeris versions;
                # 3 arcseconds is a regression guard, not an accuracy guarantee.
                self.assertLess(abs(signed_difference(actual,row['longitude']))*3600,3,(row['body'],row['utc']))
        finally: engine.close()


if __name__=='__main__': unittest.main()
