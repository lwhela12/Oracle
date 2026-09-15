"""Batched QRNG draws with uniform mapping and content-free source logging."""
import random
import time

import requests

from telemetry import emit

URL = 'https://qrandom.io/api/random/ints'
SOURCE_SIZE = 1 << 31


def _fetch(count, minimum, maximum):
    started = time.monotonic()
    details = {'provider': 'qrandom.io', 'requested': count, 'http_status': None}
    numbers = []
    reason = 'invalid_response'
    try:
        response = requests.get(URL, params={'n': count, 'min': minimum, 'max': maximum}, timeout=2.5)
        details['http_status'] = response.status_code
        if response.status_code == 200:
            numbers = response.json().get('numbers', [])
            if (not isinstance(numbers, list) or len(numbers) != count
                    or any(type(value) is not int or not minimum <= value <= maximum for value in numbers)):
                numbers = []
            else:
                reason = 'none'
        else:
            reason = 'rate_limited' if response.status_code == 429 else 'http_error'
    except requests.Timeout:
        reason = 'timeout'
    except requests.RequestException:
        reason = 'network_error'
    except (ValueError, TypeError, AttributeError):
        reason = 'invalid_response'
    details.update(reason=reason, duration_ms=round((time.monotonic() - started) * 1000))
    return numbers, details


def random_values(count, minimum, maximum, fallback_range=None):
    """Uniform integers in a common inclusive range, with secure fallback."""
    if count <= 0:
        return []
    numbers, details = _fetch(count, minimum, maximum)
    fallback = not numbers
    if fallback:
        rng = random.SystemRandom()
        low, high = fallback_range or (minimum, maximum)
        numbers = [rng.randint(low, high) for _ in range(count)]
    emit('qrng_result', **details, source='system' if fallback else 'quantum',
         fallback_values=count if fallback else 0)
    return numbers


def random_indices(bounds):
    """One index per bound in one request, rejecting incomplete modulo buckets.

    Rejected values use secure local randomness; no retry consumes another call.
    """
    bounds = list(bounds)
    if any(type(bound) is not int or not 1 <= bound <= SOURCE_SIZE for bound in bounds):
        raise ValueError('Bounds must be positive integers within the source range')
    if not bounds:
        return []
    numbers, details = _fetch(len(bounds), 0, SOURCE_SIZE - 1)
    rng = random.SystemRandom()
    rejected = 0
    if not numbers:
        indices = [rng.randrange(bound) for bound in bounds]
        rejected = len(bounds)
    else:
        indices = []
        for value, bound in zip(numbers, bounds):
            if value < SOURCE_SIZE - SOURCE_SIZE % bound:
                indices.append(value % bound)
            else:
                rejected += 1
                indices.append(rng.randrange(bound))
        if rejected:
            details['reason'] = 'range_rejection'
    source = 'quantum' if not rejected else 'system' if rejected == len(bounds) else 'mixed'
    emit('qrng_result', **details, source=source, fallback_values=rejected)
    return indices
