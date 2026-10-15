"""Sanctum prototype routes; QRNG is mocked, so no model or network calls."""
import os
import unittest
from unittest.mock import patch

from app import SANCTUM_TRADITIONS, app


class SanctumTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'ORACLE_ANALYTICS_ENABLED': '0'})
        env.start()
        self.addCleanup(env.stop)
        self.client = app.test_client()
        guard = patch('app.get_oracle', side_effect=AssertionError('Unexpected model call'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_page_is_served_uncached(self):
        response = self.client.get('/sanctum/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/static/sanctum/sanctum.js', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        response.close()

    def test_choose_maps_every_draw_to_a_tradition_the_reading_flow_accepts(self):
        for index, expected in enumerate(SANCTUM_TRADITIONS):
            with self.subTest(index=index), patch('app.random_values', return_value=[index]) as draw:
                response = self.client.post('/sanctum/choose')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), {'tradition': expected})
                draw.assert_called_once_with(1, 0, len(SANCTUM_TRADITIONS) - 1)
        self.assertEqual(set(SANCTUM_TRADITIONS), {'tarot', 'runes', 'iching', 'number'})

    def test_choose_rejects_get(self):
        self.assertEqual(self.client.get('/sanctum/choose').status_code, 405)


if __name__ == '__main__':
    unittest.main()
