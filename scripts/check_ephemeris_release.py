"""Offline release/time-data check; emits no inputs, credentials, or file paths."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    try:
        from astrology.time_health import time_health
        from astrology.jpl_adapter import _pilot
        status = time_health()
        engine = _pilot()  # verifies pinned kernel once
        status['engine'] = engine.provenance
        if 'swisseph' in sys.modules or 'astrology.engine' in sys.modules:
            raise RuntimeError('Unexpected Swiss dependency')
        print(json.dumps(status, sort_keys=True))
        return 0 if status['status'] == 'healthy' else 1
    except Exception:
        print(json.dumps({'status': 'unavailable', 'error': 'ephemeris_release_check_failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
