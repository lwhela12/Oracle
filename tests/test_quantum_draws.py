"""Draw integrity and request budgets, with no live QRNG or LLM calls."""
import itertools
import unittest
from collections import Counter
from unittest.mock import Mock, patch

import requests

from quantum_random import SOURCE_SIZE, random_indices
from runes import RuneCast
from tarot import TarotDeck


def response(numbers):
    return Mock(status_code=200, json=Mock(return_value={'numbers': numbers}))


class QuantumDrawTests(unittest.TestCase):
    def test_tarot_spread_budgets_and_no_duplicates(self):
        for count in (1, 3, 5, 10, 78):
            with self.subTest(count=count), patch('quantum_random.requests.get', return_value=response([0] * count)) as get:
                deck = TarotDeck()
                drawn = deck.reading(count)
                self.assertEqual(len(set(drawn)), count)
                self.assertEqual(len(deck.cards), 78 - count)
                self.assertTrue(set(drawn).isdisjoint(deck.cards))
                get.assert_called_once()
                self.assertEqual(get.call_args.kwargs['params'], {'n': count, 'min': 0, 'max': SOURCE_SIZE - 1})
                self.assertEqual(get.call_args.kwargs['timeout'], 2.5)

    def test_tarot_resets_and_can_select_last_remaining_card(self):
        deck = TarotDeck()
        original = deck.cards.copy()
        with patch('quantum_random.requests.get', return_value=response([77, 76, 75])):
            self.assertEqual(deck.reading(3), original[-1:-4:-1])
            self.assertEqual(deck.reading(3), original[-1:-4:-1])

    def test_full_shuffle_preserves_deck(self):
        deck = TarotDeck()
        original = deck.cards.copy()
        with patch('quantum_random.requests.get', return_value=response(list(range(77, -1, -1)))):
            deck.quantum_shuffle()
        self.assertEqual(deck.cards, original[::-1])

    def test_uniform_mapping_for_small_source_including_rejections(self):
        # Eight equally likely source values; six fit evenly into three buckets.
        # The remaining two must use an independent uniform fallback.
        outcomes = Counter()
        for value, fallback in itertools.product(range(8), range(3)):
            with patch('quantum_random.SOURCE_SIZE', 8), patch('quantum_random.requests.get', return_value=response([value])), patch('quantum_random.random.SystemRandom') as rng:
                rng.return_value.randrange.return_value = fallback
                outcomes[random_indices([3])[0]] += 1
                self.assertEqual(rng.return_value.randrange.call_count, int(value >= 6))
        self.assertEqual(outcomes, {0: 8, 1: 8, 2: 8})

    def test_each_ordered_three_card_draw_has_one_index_sequence(self):
        outcomes = set()
        for indices in itertools.product(range(4), range(3), range(2)):
            deck = TarotDeck()
            def reset():
                deck.cards = list('ABCD')
            with patch.object(deck, 'reset_deck', side_effect=reset), patch('quantum_random.requests.get', return_value=response(list(indices))):
                outcomes.add(tuple(deck.reading(3)))
        self.assertEqual(outcomes, set(itertools.permutations('ABCD', 3)))

    def test_bad_responses_use_secure_fallback(self):
        bad = [Mock(status_code=429), response([]), response([0]),
               response([0, True]), response([0, -1]), response([0, SOURCE_SIZE]),
               response([0, 1.5]), response('bad'),
               Mock(status_code=200, json=Mock(return_value=None)),
               Mock(status_code=200, json=Mock(side_effect=ValueError('bad JSON')))]
        for result in bad:
            with self.subTest(result=result), patch('quantum_random.requests.get', return_value=result), patch('quantum_random.random.SystemRandom') as rng:
                rng.return_value.randrange.side_effect = [2, 1]
                self.assertEqual(random_indices([3, 2]), [2, 1])
                self.assertEqual([call.args[0] for call in rng.return_value.randrange.call_args_list], [3, 2])

    def test_timeout_still_returns_complete_unique_draws(self):
        with patch('quantum_random.requests.get', side_effect=requests.Timeout):
            self.assertEqual(len(set(TarotDeck().reading(10))), 10)
            self.assertEqual(len({r['key'] for r in RuneCast().quantum_draw_with_reversals(24)}), 24)

    def test_rune_reversal_rules_and_budget(self):
        runes = RuneCast()
        # Select each candidate in order; request reversed for all of them.
        with patch('quantum_random.requests.get', return_value=response([0] * 24 + [1] * 24)) as get:
            drawn = runes.quantum_draw_with_reversals(24)
            self.assertEqual(get.call_args.kwargs['params']['n'], 48)
        self.assertEqual(len({r['key'] for r in drawn}), 24)
        self.assertNotIn('wyrd', [r['key'] for r in drawn])
        for rune in drawn:
            self.assertEqual(rune['is_reversed'], rune['reversible'])
            self.assertEqual(rune['active_meaning'], rune['merkstave'] if rune['reversible'] else rune['meaning'])
        with patch('quantum_random.requests.get', return_value=response([0] * 6)) as get:
            self.assertEqual(len(runes.quantum_draw_with_reversals()), 3)
            self.assertEqual(get.call_args.kwargs['params']['n'], 6)

    def test_rune_no_reversals_and_optional_blank(self):
        runes = RuneCast()
        with patch('quantum_random.requests.get', return_value=response([24, 0, 0])) as get:
            drawn = runes.quantum_draw_with_reversals(3, allow_reversals=False, include_wyrd=True)
            self.assertEqual(get.call_args.kwargs['params']['n'], 3)
        self.assertEqual(drawn[0]['key'], 'wyrd')
        self.assertTrue(all(not r['is_reversed'] for r in drawn))
        self.assertEqual(len({r['key'] for r in drawn}), 3)

    def test_empty_draws_skip_provider(self):
        with patch('quantum_random.requests.get') as get:
            self.assertEqual(TarotDeck().reading(0), [])
            self.assertEqual(RuneCast().quantum_draw_with_reversals(0), [])
            get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
