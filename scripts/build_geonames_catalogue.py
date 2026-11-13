#!/usr/bin/env python3
"""Rebuild the offline place catalogue from the pinned upstream wheel.

Usage: python scripts/build_geonames_catalogue.py /path/to/geonamescache-3.0.2-py3-none-any.whl
"""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

WHEEL_SHA256 = 'b830e8942f2d58c7e68782dcf4dff2ffe8c4104a35ee881ed1ad4023cefcdba4'
DESTINATION = Path(__file__).resolve().parents[1] / 'astrology/data/geonames-cities1000.json.gz'


def main(wheel_path):
    wheel = Path(wheel_path)
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != WHEEL_SHA256:
        raise SystemExit('Unexpected wheel SHA-256; obtain the pinned 3.0.2 wheel.')
    with zipfile.ZipFile(wheel) as archive:
        data = {name: json.loads(archive.read(f'geonamescache/data/{filename}.json'))
                for name, filename in (('cities', 'cities1000'), ('countries', 'countries'),
                                       ('us_states', 'us_states'))}
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    # Empty filename and fixed timestamp eliminate local path and time variability.
    with DESTINATION.open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=9) as output:
            output.write(encoded)
    print(f'{len(data["cities"])} cities; {DESTINATION.stat().st_size} compressed bytes')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
