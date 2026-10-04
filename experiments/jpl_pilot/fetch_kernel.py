"""Download the pinned, unmodified NASA kernel once; runtime stays offline."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

URL = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp'
EXPECTED = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
path = Path('scratch/jpl-pilot/de440s.bsp')
path.parent.mkdir(parents=True, exist_ok=True)
if path.exists():
    if sha256(path.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('Existing kernel checksum differs; inspect it before replacement')
    print('Pinned kernel already present')
else:
    temporary = path.with_suffix('.download')
    try:
        digest=sha256()
        with urlopen(URL,timeout=60) as response, temporary.open('wb') as target:
            for chunk in iter(lambda: response.read(1024*1024),b''):
                target.write(chunk); digest.update(chunk)
        if digest.hexdigest()!=EXPECTED:
            raise ValueError('Download checksum mismatch')
        temporary.replace(path)
        print('Downloaded and verified',path)
    finally:
        temporary.unlink(missing_ok=True)
