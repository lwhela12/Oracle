"""Offline operational status of the pinned Earth-rotation data."""
from datetime import date, datetime, timezone
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files


@lru_cache(maxsize=1)
def _data_version():
    from skyfield.api import load
    timescale = load.timescale(builtin=True)
    last = timescale.tt_jd(float(timescale.delta_t_table[0][-1])).tt_strftime('%Y-%m-%d')
    digest = sha256(files('skyfield.data').joinpath('iers.npz').read_bytes()).hexdigest()
    return last, digest, version('skyfield')


def time_health(*, today=None, refresh_within_days=45):
    """No downloads; predictions are distinguished from a data expiry guarantee."""
    today = today or datetime.now(timezone.utc).date()
    last, digest, skyfield_version = _data_version()
    remaining = (date.fromisoformat(last) - today).days
    status = 'expired' if remaining <= 0 else 'refresh_due' if remaining <= refresh_within_days else 'healthy'
    return {'status': status, 'skyfield_version': skyfield_version,
            'earth_rotation_table_last_date': last,
            'days_remaining': remaining, 'refresh_within_days': refresh_within_days,
            'time_data_sha256': digest,
            'note': 'The table includes predictions. Future Earth rotation and leap seconds are uncertain.'}
