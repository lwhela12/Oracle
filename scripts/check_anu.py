#!/usr/bin/env python3
"""Make one ANU-only request; report health without exposing keys or random values.

A successful paid request costs $0.005 at the published Marketplace price.
This deliberately bypasses failover to verify the configured ANU credential.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
import requests

from quantum_random import ProviderError, _anu


def main():
    load_dotenv(ROOT / '.env', override=False)
    result = {'provider': 'anu', 'requested': 3, 'fallback_allowed': False}
    if not os.getenv('ANU_QRNG_API_KEY', '').strip():
        print(json.dumps({**result, 'ok': False, 'reason': 'missing_api_key'}))
        return 2

    started = time.monotonic()
    try:
        values = _anu(3, 2.0)
        result.update(ok=True, received=len(values), http_status=200)
    except ProviderError as error:
        result.update(ok=False, reason=error.reason, http_status=error.http_status)
    except requests.Timeout:
        result.update(ok=False, reason='timeout')
    except requests.RequestException:
        result.update(ok=False, reason='network_error')
    except (TypeError, AttributeError, KeyError):
        result.update(ok=False, reason='invalid_response')
    result['duration_ms'] = round((time.monotonic() - started) * 1000)
    print(json.dumps(result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
