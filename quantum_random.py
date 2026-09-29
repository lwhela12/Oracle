"""Batched QRNG draws with provider failover, uniform mapping and content-free logging.

Every draw asks one quantum provider for 31-bit integers. Providers are tried in
order (QRNG_PROVIDERS) within a shared time budget; a provider that just failed on
this warm instance is skipped for a short cooldown so a dead source costs latency
once, not on every reading. Only if every provider fails does the draw use secure
system randomness, and telemetry records exactly which source served it.
"""
import os
import random
import re
import time

import requests

from telemetry import emit

SOURCE_SIZE = 1 << 31
MAX_BATCH = 1024          # Smallest provider batch limit (ANU); readings need <= 48.
TOTAL_BUDGET = 4.0        # Seconds across all providers before falling back.
COOLDOWN = 60.0           # Seconds to skip a provider after it fails on this instance.
DEFAULT_ORDER = 'anu,lfdr,qrandom,anu_legacy'
HEX8 = re.compile(r'[0-9a-fA-F]{8}')

_cooldown_until = {}


class ProviderError(Exception):
    def __init__(self, reason, http_status=None):
        super().__init__(reason)
        self.reason = reason
        self.http_status = http_status


def _json(response):
    if response.status_code != 200:
        raise ProviderError('rate_limited' if response.status_code == 429 else 'http_error',
                            response.status_code)
    try:
        return response.json()
    except ValueError as err:
        raise ProviderError('invalid_response', 200) from err


def _hex_words(words, count):
    """Eight hex digits (32 bits) per value; drop one bit for a uniform 31-bit integer."""
    if not isinstance(words, list) or len(words) != count or not all(isinstance(w, str) and HEX8.fullmatch(w) for w in words):
        raise ProviderError('invalid_response', 200)
    return [int(word, 16) >> 1 for word in words]


def _lfdr(count, timeout):
    # OTH Regensburg Laboratory for Digitalisation, ID Quantique QRNG PCIe hardware.
    data = _json(requests.get('https://lfdr.de/qrng_api/qrng',
                              params={'length': 4 * count, 'format': 'HEX'}, timeout=timeout))
    qrn = data.get('qrn') if isinstance(data, dict) else None
    if not isinstance(qrn, str) or len(qrn) != 8 * count:
        raise ProviderError('invalid_response', 200)
    return _hex_words([qrn[i:i + 8] for i in range(0, len(qrn), 8)], count)


def _qrandom(count, timeout):
    data = _json(requests.get('https://qrandom.io/api/random/ints',
                              params={'n': count, 'min': 0, 'max': SOURCE_SIZE - 1}, timeout=timeout))
    numbers = data.get('numbers') if isinstance(data, dict) else None
    if (not isinstance(numbers, list) or len(numbers) != count
            or any(type(value) is not int or not 0 <= value < SOURCE_SIZE for value in numbers)):
        raise ProviderError('invalid_response', 200)
    return numbers


def _anu_words(url, count, timeout, headers=None, size=4):
    data = _json(requests.get(url, params={'length': count, 'type': 'hex16', 'size': size},
                              headers=headers, timeout=timeout))
    if not isinstance(data, dict) or data.get('success') is not True:
        raise ProviderError('invalid_response', 200)
    return _hex_words(data.get('data'), count)


def _anu(count, timeout):
    # Paid ANU Quantum Numbers API (AWS-hosted); only used when a key is configured.
    # Paid hex16 size counts 16-bit words; legacy size counts bytes.
    # Two paid words and four legacy bytes both produce eight hex digits.
    return _anu_words('https://api.quantumnumbers.anu.edu.au', count, timeout,
                      headers={'x-api-key': os.environ['ANU_QRNG_API_KEY']}, size=2)


def _anu_legacy(count, timeout):
    # Free legacy ANU endpoint; rate-limited, so it is a last resort.
    return _anu_words('https://qrng.anu.edu.au/API/jsonI.php', count, timeout)


PROVIDERS = {
    'anu': ('anu', _anu, 2.0),
    'lfdr': ('lfdr.de', _lfdr, 2.0),
    'qrandom': ('qrandom.io', _qrandom, 1.5),
    'anu_legacy': ('anu-legacy', _anu_legacy, 2.0),
}


def _order():
    names = [n.strip() for n in os.getenv('QRNG_PROVIDERS', DEFAULT_ORDER).split(',')]
    names = [n for n in names if n in PROVIDERS and (n != 'anu' or os.getenv('ANU_QRNG_API_KEY'))]
    now = time.monotonic()
    ready = [n for n in names if _cooldown_until.get(n, 0) <= now]
    # If every source is cooling down, still try them rather than skip quantum entirely.
    return ready or names


def _fetch(count):
    """Return (31-bit integers or [], telemetry details) from the first working provider."""
    started = time.monotonic()
    details = {'provider': None, 'requested': count, 'http_status': None, 'reason': 'no_provider'}
    failovers = []
    numbers = []
    for name in _order():
        label, fetch, timeout = PROVIDERS[name]
        remaining = TOTAL_BUDGET - (time.monotonic() - started)
        if remaining <= 0.2:
            details['reason'] = 'budget_exhausted'
            break
        try:
            numbers = fetch(count, min(timeout, remaining))
            _cooldown_until.pop(name, None)
            details.update(provider=label, http_status=200, reason='none')
            break
        except ProviderError as err:
            reason, status = err.reason, err.http_status
        except requests.Timeout:
            reason, status = 'timeout', None
        except requests.RequestException:
            reason, status = 'network_error', None
        except (TypeError, AttributeError, KeyError):
            reason, status = 'invalid_response', None
        _cooldown_until[name] = time.monotonic() + COOLDOWN
        failovers.append(f'{label}:{reason}')
        details.update(provider=label, http_status=status, reason=reason)
    if failovers:
        details['failovers'] = ','.join(failovers)
    details['duration_ms'] = round((time.monotonic() - started) * 1000)
    return numbers, details


def random_indices(bounds):
    """One index per bound in one request, rejecting incomplete modulo buckets.

    Rejected values use secure local randomness; no retry consumes another call.
    """
    bounds = list(bounds)
    if any(type(bound) is not int or not 1 <= bound <= SOURCE_SIZE for bound in bounds):
        raise ValueError('Bounds must be positive integers within the source range')
    if not bounds:
        return []
    if len(bounds) > MAX_BATCH:
        raise ValueError(f'At most {MAX_BATCH} values per draw')
    numbers, details = _fetch(len(bounds))
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


def random_values(count, minimum, maximum):
    """Uniform integers in an inclusive range; the range never changes on fallback."""
    if count <= 0:
        return []
    if type(minimum) is not int or type(maximum) is not int or maximum < minimum:
        raise ValueError('Invalid range')
    return [minimum + index for index in random_indices([maximum - minimum + 1] * count)]
