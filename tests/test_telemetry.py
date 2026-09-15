import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from app import app
from iching import IChing
from oracle_logic import GeminiOracle
from quantum_random import SOURCE_SIZE, random_indices, random_values
from telemetry import begin, emit, flush

VISITOR = 'd454a247-0ec3-4bce-a499-d119d3367088'
READING = '61696c9e-041d-40f8-a277-28c81f80b272'


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'ORACLE_ANALYTICS_ENABLED': '1', 'POSTHOG_PROJECT_TOKEN': '', 'VERCEL_ENV': 'preview'})
        self.env.start()
        self.records = []
        self.logs = patch('telemetry.operational_log', side_effect=self.records.append)
        self.logs.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.logs.stop)
        self.client = app.test_client()
        self.body = dict(visitor_id=VISITOR, reading_id=READING, mode='tarot', spread_type='3-card', message='PRIVATE QUESTION', session_id='PRIVATE SESSION')

    def oracle(self):
        oracle = Mock()
        oracle.prepare_tarot_reading.return_value = dict(cards=['PRIVATE CARD'], positions=['Past'], spread_type='3-card', prompt='PRIVATE PROMPT')
        oracle.stream_chat.return_value = iter(['PRIVATE INTERPRETATION'])
        return oracle

    def test_stream_completion_is_one_finished_event(self):
        with patch('app.get_oracle', return_value=self.oracle()):
            result = self.client.post('/chat/stream', json=self.body)
            self.assertIn(b'event: done', result.data)
        finished = [r for r in self.records if r['event'] == 'reading_finished']
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0]['outcome'], 'completed')
        self.assertEqual(finished[0]['visitor_id'], VISITOR)
        self.assertEqual(finished[0]['reading_id'], READING)
        self.assertEqual(finished[0]['spread'], '3-card')
        self.assertNotIn('PRIVATE', json.dumps(self.records))

    def test_stream_error_and_init_error_never_count_completed(self):
        def broken(*args, **kwargs):
            yield 'partial'
            raise ValueError('PRIVATE failure')
        oracle = self.oracle()
        oracle.stream_chat.side_effect = broken
        for target in (oracle, ValueError('PRIVATE CONFIG')):
            self.records.clear()
            context = patch('app.get_oracle', side_effect=target) if isinstance(target, Exception) else patch('app.get_oracle', return_value=target)
            with context:
                result = self.client.post('/chat/stream', json=self.body)
                self.assertIn(b'event: error', result.data)
            self.assertEqual([r['outcome'] for r in self.records if r['event'] == 'reading_finished'], ['failed'])
            self.assertNotIn('PRIVATE', json.dumps(self.records))

    def test_cancelled_stream_is_interrupted(self):
        with patch('app.get_oracle', return_value=self.oracle()):
            result = self.client.post('/chat/stream', json=self.body, buffered=False)
            result.close()
        self.assertEqual([r['outcome'] for r in self.records if r['event'] == 'reading_finished'], ['interrupted'])

    def test_sync_success_and_failure(self):
        oracle = self.oracle()
        oracle.tarot_response_structured.return_value = dict(text='PRIVATE TEXT', cards=[], positions=[], spread_type='3-card')
        with patch('app.get_oracle', return_value=oracle):
            self.assertEqual(self.client.post('/chat', json=self.body).status_code, 200)
            oracle.tarot_response_structured.side_effect = ValueError('PRIVATE ERROR')
            self.assertEqual(self.client.post('/chat', json=self.body).status_code, 500)
        self.assertEqual([r['outcome'] for r in self.records if r['event'] == 'reading_finished'], ['completed', 'failed'])

    def test_opt_out_and_invalid_identifier(self):
        for headers, visitor in [({'DNT': '1'}, VISITOR), ({'Sec-GPC': '1'}, VISITOR), ({}, 'PRIVATE NAME')]:
            with patch('app.get_oracle', return_value=self.oracle()):
                self.client.post('/chat/stream', json={**self.body, 'visitor_id': visitor}, headers=headers).get_data()
            self.assertTrue(all('visitor_id' not in r for r in self.records))
            self.records.clear()
        self.client.post('/analytics/visit', json={'visitor_id': VISITOR, 'analytics_opt_out': True})
        self.assertEqual(self.records, [])

    def test_posthog_batch_contains_no_content_and_failure_is_nonfatal(self):
        with patch.dict(os.environ, {'POSTHOG_PROJECT_TOKEN': 'TEST_TOKEN'}), patch('telemetry.requests.post', side_effect=requests.Timeout) as post:
            with patch('app.get_oracle', return_value=self.oracle()):
                result = self.client.post('/chat/stream', json=self.body).get_data()
            self.assertIn(b'event: done', result)
            post.assert_called_once()
            batch = post.call_args.kwargs['json']['batch']
            self.assertEqual(len(batch), 2)
            self.assertNotIn('PRIVATE', json.dumps(batch))
            self.assertFalse(batch[0]['properties']['$process_person_profile'])
            self.assertTrue(batch[0]['properties']['$geoip_disable'])
            self.assertIn('telemetry_delivery_failed', [r['event'] for r in self.records])

    def test_qrng_reasons_and_partial_fallback(self):
        for result, reason in [(Mock(status_code=429), 'rate_limited'), (Mock(status_code=503), 'http_error'), (Mock(status_code=200, json=Mock(return_value={})), 'invalid_response')]:
            with patch('quantum_random.requests.get', return_value=result):
                self.assertEqual(len(random_values(3, 0, 1)), 3)
            self.assertEqual(self.records[-1]['reason'], reason)
            self.assertEqual(self.records[-1]['source'], 'system')
        with patch('quantum_random.requests.get', side_effect=requests.Timeout):
            random_values(1, 0, 100)
        self.assertEqual(self.records[-1]['reason'], 'timeout')
        with patch('quantum_random.requests.get', return_value=Mock(status_code=200, json=Mock(return_value={'numbers': [0, SOURCE_SIZE - 1]}))):
            random_indices([78, 77])
        self.assertEqual(self.records[-1]['source'], 'mixed')
        self.assertEqual(self.records[-1]['fallback_values'], 1)
        self.assertEqual(self.records[-1]['reason'], 'range_rejection')

    def test_iching_and_number_are_instrumented(self):
        with patch('quantum_random.requests.get', side_effect=requests.Timeout):
            self.assertEqual(len(IChing().quantum_coin_toss()), 18)
            self.assertIsInstance(object.__new__(GeminiOracle)._get_quantum_number(), int)
        self.assertEqual([r['requested'] for r in self.records], [18, 1])

    def test_visit_and_identity_disabled_by_configuration(self):
        self.client.post('/analytics/visit', json={'visitor_id': VISITOR, 'message': 'PRIVATE QUESTION'})
        self.assertEqual(self.records[0]['event'], 'app_opened')
        self.assertNotIn('PRIVATE', json.dumps(self.records))
        self.records.clear()
        with patch.dict(os.environ, {'ORACLE_ANALYTICS_ENABLED': '0'}):
            self.assertFalse(self.client.get('/analytics/config').json['enabled'])
            self.client.post('/analytics/visit', json={'visitor_id': VISITOR})
        self.assertEqual(self.records, [])

    def test_token_usage_excludes_text_and_missing_counts(self):
        oracle = object.__new__(GeminiOracle)
        oracle.model_name = 'test-model'
        oracle._log_usage(SimpleNamespace(prompt_token_count=100, candidates_token_count=200, text='PRIVATE TEXT'))
        event = self.records[-1]
        self.assertEqual(event['input_tokens'], 100)
        self.assertEqual(event['output_tokens'], 200)
        self.assertNotIn('thinking_tokens', event)
        self.assertNotIn('PRIVATE', json.dumps(event))


if __name__ == '__main__':
    unittest.main()
