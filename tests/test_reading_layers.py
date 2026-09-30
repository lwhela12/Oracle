"""Checks the one-call output contract without contacting a model or QRNG."""
import unittest
from unittest.mock import Mock, patch
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

    def test_readings_never_reuse_chat_history_even_with_same_session_id(self):
        oracle = object.__new__(GeminiOracle)
        oracle.client = Mock()
        oracle.model_name = 'test-model'
        oracle.config = object()
        first, second, streamed = Mock(), Mock(), Mock()
        first.send_message.return_value = Mock(text='first', usage_metadata=None)
        second.send_message.return_value = Mock(text='second', usage_metadata=None)
        streamed.send_message_stream.return_value = [Mock(text='third', usage_metadata=None)]
        oracle.client.chats.create.side_effect = [first, second, streamed]
        with patch.object(oracle, '_test_context', return_value=None):
            self.assertEqual(oracle.send_chat('PRIVATE first', 'same-id'), 'first')
            self.assertEqual(oracle.send_chat('PRIVATE second', 'same-id'), 'second')
            self.assertEqual(list(oracle.stream_chat('PRIVATE third', 'same-id')), ['third'])
        self.assertEqual(oracle.client.chats.create.call_count, 3)
        first.send_message.assert_called_once_with('PRIVATE first')
        second.send_message.assert_called_once_with('PRIVATE second')
        streamed.send_message_stream.assert_called_once_with('PRIVATE third')
        self.assertFalse(hasattr(oracle, 'session_manager'))

    def test_default_session_also_creates_independent_chats(self):
        oracle = object.__new__(GeminiOracle)
        oracle.client = Mock()
        oracle.model_name, oracle.config = 'test-model', None
        oracle.get_chat()
        oracle.get_chat()
        self.assertEqual(oracle.client.chats.create.call_count, 2)
        self.assertIsNone(oracle.clear_history())

if __name__ == '__main__':
    unittest.main()
