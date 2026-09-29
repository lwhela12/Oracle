"""Draw integrity and request budgets, with no live QRNG or LLM calls."""
import itertools
import os
import unittest
from collections import Counter
from unittest.mock import Mock, patch

import requests

import quantum_random
from quantum_random import SOURCE_SIZE, random_indices, random_values
from runes import RuneCast
from tarot import TarotDeck


def response(numbers):
    return Mock(status_code=200, json=Mock(return_value={'numbers': numbers}))


class QuantumDrawTests(unittest.TestCase):
    # Mapping tests pin one provider so each draw is exactly one mocked request.
    def setUp(self):
        quantum_random._cooldown_until.clear()
        env = patch.dict(os.environ, {'QRNG_PROVIDERS': 'qrandom'})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(quantum_random._cooldown_until.clear)

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
                self.assertEqual(get.call_args.kwargs['timeout'], 1.5)

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


class Reply:
    def __init__(self, status=200, body=None, error=None):
        self.status_code, self.body, self.error = status, body, error

    def json(self):
        if self.error:
            raise self.error
        return self.body


class ProviderFailoverTests(unittest.TestCase):
    def setUp(self):
        quantum_random._cooldown_until.clear()
        self.addCleanup(quantum_random._cooldown_until.clear)
        env = patch.dict(os.environ, {'QRNG_PROVIDERS': 'lfdr,qrandom,anu_legacy'})
        env.start()
        self.addCleanup(env.stop)
        self.events = []
        emit = patch('quantum_random.emit', side_effect=lambda event, **f: self.events.append(f))
        emit.start()
        self.addCleanup(emit.stop)

    def route(self, replies):
        def get(url, **kwargs):
            for host, reply in replies.items():
                if host in url:
                    if isinstance(reply, Exception):
                        raise reply
                    return reply
            raise AssertionError(url)
        return patch('quantum_random.requests.get', side_effect=get)

    def test_lfdr_hex_maps_to_31_bit_values(self):
        with self.route({'lfdr.de': Reply(body={'qrn': 'ffffffff00000001', 'length': 8})}) as get:
            self.assertEqual(quantum_random._fetch(2)[0], [SOURCE_SIZE - 1, 0])
        self.assertEqual(get.call_args.kwargs['params'], {'length': 8, 'format': 'HEX'})

    def test_fails_over_in_order_and_logs_the_serving_provider(self):
        with self.route({'lfdr.de': Reply(503), 'qrandom.io': requests.Timeout(),
                         'anu.edu.au': Reply(body={'success': True, 'data': ['00000002', '00000004']})}) as get:
            self.assertEqual(random_indices([10, 10]), [1, 2])
            self.assertEqual(get.call_args.kwargs['params'], {'length': 2, 'type': 'hex16', 'size': 4})
        event = self.events[-1]
        self.assertEqual((event['provider'], event['source'], event['reason']), ('anu-legacy', 'quantum', 'none'))
        self.assertEqual(event['failovers'], 'lfdr.de:http_error,qrandom.io:timeout')

    def test_failed_provider_cools_down_on_this_instance(self):
        ok = Reply(body={'numbers': [5]})
        with self.route({'lfdr.de': Reply(503), 'qrandom.io': ok}) as get:
            random_indices([10])
            random_indices([10])
        hosts = [call.args[0] for call in get.call_args_list]
        self.assertEqual(sum('lfdr.de' in h for h in hosts), 1)
        self.assertEqual(sum('qrandom.io' in h for h in hosts), 2)

    def test_everything_down_uses_system_randomness_and_says_so(self):
        with self.route({'lfdr.de': Reply(500), 'qrandom.io': Reply(429),
                         'anu.edu.au': Reply(body={'success': False})}):
            self.assertEqual(len(random_indices([78, 77, 76])), 3)
            # All providers cooling down: they are still retried rather than skipped.
            random_indices([2])
        self.assertEqual(self.events[0]['source'], 'system')
        self.assertEqual(self.events[0]['failovers'], 'lfdr.de:http_error,qrandom.io:rate_limited,anu-legacy:invalid_response')
        self.assertEqual(self.events[1]['source'], 'system')

    def test_malformed_payloads_are_rejected(self):
        for body in ({'qrn': 'zz' * 8}, {'qrn': 'ab'}, {'qrn': None}, [], None):
            with self.subTest(body=body), self.route({'lfdr.de': Reply(body=body), 'qrandom.io': Reply(503), 'anu.edu.au': Reply(503)}):
                quantum_random._cooldown_until.clear()
                self.assertEqual(quantum_random._fetch(2)[0], [])
        with self.route({'lfdr.de': Reply(error=ValueError('bad json')), 'qrandom.io': Reply(503), 'anu.edu.au': Reply(503)}):
            quantum_random._cooldown_until.clear()
            self.assertEqual(quantum_random._fetch(1)[1]['failovers'].split(',')[0], 'lfdr.de:invalid_response')

    def test_paid_anu_is_first_only_when_keyed(self):
        with patch.dict(os.environ, {'QRNG_PROVIDERS': 'anu,lfdr'}):
            os.environ.pop('ANU_QRNG_API_KEY', None)
            self.assertEqual(quantum_random._order(), ['lfdr'])
            with patch.dict(os.environ, {'ANU_QRNG_API_KEY': 'k'}), self.route({'quantumnumbers': Reply(body={'success': True, 'data': ['00000006']})}) as get:
                self.assertEqual(quantum_random._fetch(1)[0], [3])
                self.assertEqual(get.call_args.kwargs['headers'], {'x-api-key': 'k'})
                self.assertEqual(get.call_args.kwargs['params'], {'length': 1, 'type': 'hex16', 'size': 2})

    def test_paid_anu_block_width_matches_live_api(self):
        # The paid service returns four hex digits per size unit, observed live.
        # The old size=4 request returned 16 digits, which our 32-bit parser rejected.
        def paid_reply(url, **kwargs):
            width = 4 * kwargs['params']['size']
            return Reply(body={'success': True, 'type': 'hex16', 'length': '1',
                               'data': ['00000006'.zfill(width)]})
        with patch.dict(os.environ, {'ANU_QRNG_API_KEY': 'k'}), \
                patch('quantum_random.requests.get', side_effect=paid_reply) as get:
            self.assertEqual(quantum_random._anu(1, 2.0), [3])
            get.assert_called_once()

    def test_time_budget_caps_total_wait(self):
        now = [0.0]
        def slow(url, **kwargs):
            now[0] += 3.0 if 'lfdr.de' in url else 0.9
            raise requests.Timeout()
        with patch('quantum_random.time.monotonic', side_effect=lambda: now[0]), \
                patch('quantum_random.requests.get', side_effect=slow) as get:
            numbers, details = quantum_random._fetch(1)
        self.assertEqual(numbers, [])
        self.assertEqual(details['reason'], 'budget_exhausted')
        self.assertEqual([c.kwargs['timeout'] for c in get.call_args_list], [2.0, 1.0])

    def test_random_values_keeps_its_range_on_fallback(self):
        with self.route({'lfdr.de': Reply(503), 'qrandom.io': Reply(503), 'anu.edu.au': Reply(503)}):
            values = random_values(500, 0, 100)
        self.assertTrue(all(0 <= v <= 100 for v in values))
        with self.route({'lfdr.de': Reply(body={'qrn': '00000000' + '000000ca'})}):
            self.assertEqual(random_values(2, 0, 100), [0, 0x65 % 101])


if __name__ == '__main__':
    unittest.main()
