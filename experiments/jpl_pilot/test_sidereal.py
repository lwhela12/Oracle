"""Independent published PAC/IAE reference checks; no Swiss dependency/kernel."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import unittest

from skyfield.api import load

from sidereal import mean_ayanamsa, true_ayanamsa, TABLE_TOLERANCE_ARCSECONDS


class IAESiderealChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts = load.timescale(builtin=True)
        cls.fixture = json.loads(Path(__file__).with_name('iae_fixture.json').read_text())

    def test_published_j2000_mean_reference(self):
        self.assertAlmostEqual(mean_ayanamsa(2451545.0) * 3600,
                               23 * 3600 + 51 * 60 + 25.53, places=8)

    def test_published_three_day_tables(self):
        rows = self.fixture['qualified_rows']
        self.assertEqual(len(rows), 458)
        for year in (2024, 2026, 2027):
            self.assertEqual(sum(r['source_year'] == year and r['primary_year']
                                 for r in rows), 122)
        for row in rows:
            with self.subTest(year=row['source_year'], date=row['date']):
                y, m, d = map(int, row['date'].split('-'))
                error = true_ayanamsa(self.ts.tt(y, m, d)) * 3600 - row['true_ayanamsa_arcseconds']
                self.assertLessEqual(abs(error), TABLE_TOLERANCE_ARCSECONDS)

    def test_rounded_ist_time_interpretation_does_not_change_table_agreement(self):
        # 05:29 IST means 23:59 UTC on the preceding civil date. At modern
        # leap-second offsets this is 9.184s after 0h TT, much smaller than
        # the table's 0.1 arcsecond precision; test both interpretations.
        for row in self.fixture['qualified_rows']:
            dt = datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc)
            t = self.ts.from_datetime(dt - timedelta(minutes=1))
            error = true_ayanamsa(t) * 3600 - row['true_ayanamsa_arcseconds']
            self.assertLessEqual(abs(error), TABLE_TOLERANCE_ARCSECONDS)

    def test_source_inconsistencies_remain_explicit(self):
        rows = self.fixture['excluded_diagnostics']
        self.assertEqual(len(rows), 25)
        self.assertEqual(rows[0]['date'], '2027-02-13')
        for row in rows:
            y, m, d = map(int, row['date'].split('-'))
            error = true_ayanamsa(self.ts.tt(y, m, d)) * 3600 - row['true_ayanamsa_arcseconds']
            # A diagnostic assertion, NOT a permitted production tolerance:
            # these contradict the same publication's declared formula.
            self.assertGreater(abs(error), 4.0)
            self.assertLess(abs(error), 6.0)

    def test_nonfinite_input_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                mean_ayanamsa(value)


if __name__ == '__main__':
    unittest.main()
