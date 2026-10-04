"""Contract checks for saved draws, honest provenance, and inspectable output."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.astrology.run import CASES, main, prepare, render, validate_interpretation, number_evidence
from experiments.astrology.calculations import whole_sign_house


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)

    def record(self):
        with patch('quantum_random._fetch', return_value=([], {'provider': None, 'reason': 'test_offline'})):
            return prepare(CASES[0], self.instant, 'system')

    def interpretation(self):
        return {'title': 'Test', 'heart': 'Reflect.', 'themes': [
            {'title': 'A', 'text': 'Text', 'evidence': ['A','T1']},
            {'title': 'B', 'text': 'Text', 'evidence': ['R1','I']},
            {'title': 'C', 'text': 'Text', 'evidence': ['N']}],
            'tension': {'text': 'Tension', 'evidence': ['T2','R2']}, 'reflection': 'Question?'}

    def test_system_draws_are_unique_and_labelled_as_system(self):
        r = self.record()
        self.assertEqual(len({r['evidence'][f'T{i}']['name'] for i in range(1,4)}), 3)
        self.assertEqual(len({r['evidence'][f'R{i}']['name'] for i in range(1,4)}), 3)
        self.assertEqual(len(r['evidence']['I']['coin_tosses']), 6)
        self.assertTrue(0 <= r['evidence']['N']['value'] <= 100)
        self.assertEqual(len(r['draw_provenance']), 4)
        self.assertTrue(all(s['source'] == 'system' for s in r['draw_provenance']))
        self.assertEqual(r['generation']['status'], 'not_run')

    def test_missing_system_or_invented_reference_is_rejected(self):
        evidence = self.record()['evidence']
        validate_interpretation(self.interpretation(), evidence)
        bad = self.interpretation()
        bad['themes'][2]['evidence'] = ['T1']
        with self.assertRaisesRegex(ValueError, 'All five'):
            validate_interpretation(bad, evidence)
        bad['themes'][2]['evidence'] = ['A:invented']
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            validate_interpretation(bad, evidence)

    def test_render_escapes_generated_html(self):
        record = self.record()
        record['interpretation'] = self.interpretation()
        record['interpretation']['heart'] = '<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'index.html'
            render({'readings':[record]}, output)
            text = output.read_text()
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)

    def test_resume_does_not_draw_again_or_change_evidence(self):
        record = self.record()
        with tempfile.TemporaryDirectory() as folder:
            bundle_path = Path(folder) / 'bundle.json'
            bundle_path.write_text(json.dumps({'readings':[record]}))
            with patch('sys.argv', ['run', '--resume', '--output', folder]), patch('experiments.astrology.run.prepare', side_effect=AssertionError('redraw')):
                self.assertEqual(main(), 0)
            reread = json.loads(bundle_path.read_text())['readings'][0]
            self.assertEqual(record['id'], reread['id'])
            self.assertEqual(record['evidence'], reread['evidence'])
            self.assertEqual(record['draw_provenance'], reread['draw_provenance'])

    def test_near_360_does_not_jump_into_aries(self):
        self.assertEqual(whole_sign_house(359.9999999, 0), 12)

    def test_hosted_comparison_aligns_both_charts_without_changing_reading(self):
        self.instant = self.instant.replace(second=36)
        record = self.record()
        original = copy.deepcopy(record['evidence'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bundle.json'
            path.write_text(json.dumps({'readings':[record]}))
            with patch('sys.argv', ['run', '--resume', '--compare-hosted', '--output', folder]), \
                 patch.dict('os.environ', {'ASTROAPI_CLOUD_KEY':'test-only'}), \
                 patch('experiments.astrology.cloud.fetch_chart', return_value={}) as fetch, \
                 patch('experiments.astrology.cloud.compare_chart', return_value={'complete':True,'within_tolerance':True}) as compare:
                self.assertEqual(main(), 0)
            saved = json.loads(path.read_text())['readings'][0]
        expected = self.instant.replace(second=0)
        self.assertEqual(fetch.call_args.args[0], expected)
        self.assertEqual(datetime.fromisoformat(compare.call_args.args[0]['inputs']['utc']), expected)
        self.assertEqual(saved['evidence'], original)
        self.assertEqual(saved['instant_utc'], self.instant.isoformat())
        self.assertEqual(saved['hosted_comparison']['comparison_instant_utc'], expected.isoformat())

    def test_numerology_reduction_records_arithmetic_and_convention(self):
        self.assertEqual(number_evidence(99)['digit_reduction']['steps'], [99,18,9])
        self.assertEqual(number_evidence(0)['digit_reduction']['root'], 0)
        self.assertEqual(number_evidence(11)['digit_reduction']['root'], 2)


if __name__ == '__main__':
    unittest.main()
