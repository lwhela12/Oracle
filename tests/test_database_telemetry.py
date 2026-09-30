"""Request integration checks; all provider and database I/O is replaced."""
import json
import os
import unittest
import uuid
from unittest.mock import Mock, patch

from app import app
from telemetry import begin, emit, flush_database, reading_prepared

VISITOR = 'd454a247-0ec3-4bce-a499-d119d3367088'
READING = '61696c9e-041d-40f8-a277-28c81f80b272'


class DatabaseTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'VERCEL_ENV': 'preview', 'ORACLE_DATABASE_ENVIRONMENT': 'preview',
            'ORACLE_DATABASE_URL': 'configured-in-test', 'ORACLE_ANALYTICS_ENABLED': '1',
            'ORACLE_TRAFFIC_CLASS': 'test', 'POSTHOG_PROJECT_TOKEN': '',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.batches = []
        self.sink = patch('telemetry.write_database_events',
                          side_effect=lambda events, **kw: self.batches.append(events))
        self.writer = self.sink.start()
        self.addCleanup(self.sink.stop)
        self.logs = []
        self.log_patch = patch('telemetry.operational_log', side_effect=self.logs.append)
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)
        self.client = app.test_client()
        self.body = dict(message='PRIVATE question', mode='tarot', spread_type='3-card',
                         visitor_id=VISITOR, reading_id=READING, traffic_class='internal')

    def oracle(self):
        oracle = Mock()
        oracle.prepare_tarot_reading.return_value = {
            'cards': [{'name': 'PRIVATE card'}], 'positions': ['Past'],
            'spread_type': '3-card', 'prompt': 'PRIVATE prompt'}
        oracle.tarot_response_structured.return_value = {
            'text': 'PRIVATE answer', 'cards': [], 'positions': [], 'spread_type': '3-card'}
        oracle.stream_chat.return_value = iter(['PRIVATE answer'])
        return oracle

    def records(self):
        return [record for batch in self.batches for record in batch]

    def test_opt_out_operational_events_persist_without_visitor(self):
        with patch('app.get_oracle', return_value=self.oracle()):
            result = self.client.post('/chat/stream', json=self.body, headers={'DNT': '1'})
            self.assertIn(b'event: done', result.data)
        records = self.records()
        self.assertEqual([r['event'] for r in records], ['reading_started', 'reading_finished'])
        self.assertTrue(all('visitor_id' not in r for r in records))
        self.assertTrue(all(r['traffic_class'] == 'test' for r in records))
        self.assertNotIn('PRIVATE', json.dumps(records))
        self.assertEqual(records[-1]['schema'], 'oracle.telemetry.v2')
        self.assertIn('canonical_reading_id', records[-1])

    def test_disabled_sink_never_called(self):
        with patch.dict(os.environ, {'ORACLE_DATABASE_URL': ''}), patch('app.get_oracle', return_value=self.oracle()):
            result = self.client.post('/chat', json=self.body)
        self.assertEqual(result.status_code, 200)
        self.writer.assert_not_called()
        self.assertTrue(uuid.UUID(result.json['canonical_reading_id']))

    def test_failed_sink_does_not_fail_reading_or_expose_exception(self):
        self.writer.side_effect = RuntimeError('PRIVATE connection credential')
        with patch('app.get_oracle', return_value=self.oracle()):
            self.assertIn(b'event: done', self.client.post('/chat/stream', json=self.body).data)
        self.writer.assert_called_once()  # Stop spending time after the first failure.
        self.assertNotIn('PRIVATE', json.dumps(self.logs))
        self.assertEqual(len([r for r in self.logs if r['event'] == 'telemetry_delivery_failed']), 1)

    def test_inferred_start_dimensions_commit_before_provider_is_called(self):
        body = {**self.body, 'message': 'Please draw a Celtic tarot spread',
                'spread_type': 'celtic'}
        body.pop('mode')
        oracle = self.oracle()

        def provider(*args, **kwargs):
            start = self.records()[0]
            self.assertEqual(start['event'], 'reading_started')
            self.assertEqual((start['mode'], start['spread']), ('tarot', 'celtic'))
            return {'text': 'PRIVATE answer', 'cards': [], 'positions': [],
                    'spread_type': 'celtic'}

        oracle.tarot_response_structured.side_effect = provider
        with patch('app.get_oracle', return_value=oracle):
            self.assertEqual(self.client.post('/chat', json=body).status_code, 200)

    def test_error_before_inference_still_persists_start_and_finish(self):
        with patch('app.get_oracle', side_effect=ValueError('test configuration')):
            response = self.client.post('/chat', json=self.body)
        self.assertEqual(response.status_code, 500)
        records = self.records()
        self.assertEqual([record['event'] for record in records],
                         ['reading_started', 'reading_finished'])
        self.assertEqual(records[-1]['outcome'], 'failed')

    def test_after_draw_flush_and_cumulative_budget(self):
        with app.test_request_context('/chat', method='POST'):
            state = begin(self.body)
            emit('qrng_result', source='system', requested=1,
                 fallback_values=1, reason='no_provider', duration_ms=1)
            metadata = reading_prepared()
            self.assertEqual(self.records()[0]['event'], 'qrng_result')
            self.assertEqual(reading_prepared(), metadata)
            state['database_seconds'] = 0.4
            emit('reading_finished', outcome='completed', duration_ms=2)
            flush_database(state)
            self.assertAlmostEqual(self.writer.call_args.kwargs['timeout_seconds'], 0.1)
            state['database_seconds'] = 0.5
            emit('reading_finished', outcome='completed', duration_ms=2)
            before = self.writer.call_count
            flush_database(state)
            self.assertEqual(self.writer.call_count, before)
            self.assertTrue(state['database_failed'])

    def test_draw_identity_is_independent_of_analytics_and_request_correlation(self):
        with patch.dict(os.environ, {'ORACLE_ANALYTICS_ENABLED': '0'}), patch('app.get_oracle', return_value=self.oracle()):
            first = self.client.post('/chat', json=self.body).json
            second = self.client.post('/chat', json=self.body).json
        self.assertNotEqual(first['canonical_reading_id'], second['canonical_reading_id'])
        self.assertNotEqual(first['canonical_reading_id'], READING)
        self.assertIn('+00:00', first['created_at'])
        self.assertEqual(first['content_format_version'], 1)

    def test_stream_metadata_and_terminal_event_share_draw_identity(self):
        with patch('app.get_oracle', return_value=self.oracle()):
            response = self.client.post('/chat/stream', json=self.body).data.decode()
        block = response.split('\n\n')[0]
        metadata = json.loads(block.split('data: ', 1)[1])
        finished = [record for record in self.records() if record['event'] == 'reading_finished'][0]
        self.assertEqual(metadata['canonical_reading_id'], finished['canonical_reading_id'])
        self.assertEqual(finished['reading_id'], READING)
        self.assertNotEqual(finished['attempt_id'], finished['canonical_reading_id'])

    def test_actual_sync_wrapper_flushes_draw_before_model(self):
        from oracle_logic import GeminiOracle
        oracle = object.__new__(GeminiOracle)
        def prepare(*args):
            emit('qrng_result', provider='anu', source='quantum', requested=3,
                 fallback_values=0, reason='none', duration_ms=1)
            return {'cards': [], 'positions': [], 'spread_type': '3-card', 'prompt': 'PRIVATE'}
        def interpret(*args):
            self.assertIn('qrng_result', [record['event'] for record in self.records()])
            return 'PRIVATE answer'
        oracle.prepare_tarot_reading = prepare
        oracle.send_chat = interpret
        with patch('app.get_oracle', return_value=oracle):
            response = self.client.post('/chat', json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.batches), 3)

    def test_number_sync_preserves_exact_draw(self):
        oracle = Mock()
        oracle.prepare_number_reading.return_value = {'quantum_number': 42, 'prompt': 'PRIVATE prompt'}
        oracle.send_chat.return_value = 'PRIVATE answer'
        with patch('app.get_oracle', return_value=oracle):
            result = self.client.post('/chat', json={**self.body, 'mode': 'number'})
        self.assertEqual(result.json['quantum_number'], 42)
        oracle.prepare_number_reading.assert_called_once()
        self.assertTrue(uuid.UUID(result.json['canonical_reading_id']))

    def test_visit_respects_gpc_and_persists_linked_visit(self):
        self.client.post('/analytics/visit', json={'visitor_id': VISITOR}, headers={'Sec-GPC': '1'})
        self.assertEqual(self.records(), [])
        self.client.post('/analytics/visit', json={'visitor_id': VISITOR})
        self.assertEqual(self.records()[0]['event'], 'app_opened')

    def test_interrupted_stream_records_one_outcome(self):
        with patch('app.get_oracle', return_value=self.oracle()):
            response = self.client.post('/chat/stream', json=self.body, buffered=False)
            response.close()
        finishes = [r for r in self.records() if r['event'] == 'reading_finished']
        self.assertEqual([r['outcome'] for r in finishes], ['interrupted'])


if __name__ == '__main__':
    unittest.main()
