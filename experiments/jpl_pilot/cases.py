"""Synthetic, reproducible comparison cases; no user birth information."""
from datetime import datetime, timedelta, timezone
import random


def cases():
    rng = random.Random(440)
    result = []
    for year in (1850, 1900, 1950, 1972, 2000, 2024, 2026, 2050, 2100, 2149):
        for month in (1, 4, 7, 10):
            dt = datetime(year, month, 15, 12, tzinfo=timezone.utc)
            result.append({'id': f'{year}-{month:02}', 'utc': dt.isoformat(),
                           'latitude': rng.uniform(-60, 60), 'longitude': rng.uniform(-180, 180)})
    for i in range(40):
        dt = datetime(1972, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=rng.randrange(55*365*86400))
        result.append({'id': f'modern-{i}', 'utc': dt.isoformat(),
                       'latitude': rng.uniform(-60, 60), 'longitude': rng.uniform(-180, 180)})
    for i, lat in enumerate((-85, -70, -66, 66, 70, 85)):
        result.append({'id': f'polar-{i}', 'utc': '2026-10-04T12:00:00+00:00', 'latitude': lat, 'longitude': 0})
    return result
