import unittest
from scripts.usage_report import extract, summarize


def event(kind, identity, **fields):
    return dict(schema='oracle.telemetry.v1', event=kind, event_id=identity,
                timestamp='2026-09-15T06:30:00+00:00', environment='production', **fields)


class UsageReportTests(unittest.TestCase):
    def test_deduplication_daily_repeat_usage_and_preview_exclusion(self):
        events = [event('app_opened', 'visit', visitor_id='a'),
                  event('reading_started', 'start', visitor_id='a', attempt_id='a1'),
                  event('reading_finished', 'f1', visitor_id='a', reading_id='r1', outcome='completed', mode='tarot', spread='3-card'),
                  event('reading_finished', 'f2', visitor_id='a', reading_id='r2', outcome='completed', mode='runes', spread='norns'),
                  event('reading_finished', 'retry', visitor_id='a', reading_id='r2', outcome='completed', mode='runes', spread='norns'),
                  event('reading_finished', 'failed', visitor_id='b', reading_id='r3', outcome='failed'),
                  {**event('app_opened', 'preview', visitor_id='c'), 'environment': 'preview'},
                  event('qrng_result', 'q1', fallback_values=0, reason='none'),
                  event('qrng_result', 'q2', fallback_values=3, reason='rate_limited')]
        events.append(events[2])
        result = summarize(events)
        self.assertEqual(result['completed_readings'], 2)
        self.assertEqual(result['anonymous_visitors_in_export'], 2)
        self.assertEqual(result['popular_modes'], {'tarot': 1, 'runes': 1})
        self.assertEqual(result['daily'][0]['day'], '2026-09-14')
        self.assertEqual(result['daily'][0]['readers_with_2plus'], 1)
        self.assertEqual(result['qrng_fallback_percent'], 50)
        self.assertIsNone(summarize([])['qrng_fallback_percent'])

    def test_wrapped_ndjson_export(self):
        records = list(extract('{"text":"{\\"schema\\":\\"oracle.telemetry.v1\\",\\"event\\":\\"app_opened\\"}"}\ninvalid line'))
        self.assertEqual(len(records), 1)
