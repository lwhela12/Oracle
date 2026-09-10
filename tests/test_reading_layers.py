"""Checks the one-call output contract without contacting a model or QRNG."""
import unittest
from unittest.mock import patch
from oracle_logic import GeminiOracle, layered_prompt

class ReadingLayersTests(unittest.TestCase):
    def test_positions_are_bound_by_index(self):
        prompt = layered_prompt('Preserve the full reading.', [{'name': 'The Hermit'}, {'name': 'The Fool'}], ['Past', 'Future'])
        self.assertIn('1: The Hermit — Past\n2: The Fool — Future', prompt)
        self.assertIn('FULL, unabridged', prompt)
        self.assertIn('copied VERBATIM', prompt)
        self.assertIn('[[SYMBOL:1:DEPTH]]', prompt)

    def test_no_symbols_for_other_traditions(self):
        prompt = layered_prompt('Interpret this hexagram.')
        self.assertIn('Symbol indices (no symbol sections when this list is empty):\n\nFinally', prompt)

    def test_test_logging_is_disabled_in_production(self):
        oracle = object.__new__(GeminiOracle)
        with patch.dict('os.environ', {'ORACLE_TEST_LLM_LOG': '1', 'VERCEL_ENV': 'production'}):
            # No chat access is attempted on a deployed runtime, even when opted in.
            self.assertIsNone(oracle._test_context(None, 'private question', 'test'))

if __name__ == '__main__':
    unittest.main()
