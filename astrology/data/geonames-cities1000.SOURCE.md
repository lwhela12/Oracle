# Offline GeoNames city catalogue

`geonames-cities1000.json.gz` contains the complete `cities1000.json`,
`countries.json`, and `us_states.json` datasets from the PyPI
[GeoNamesCache 3.0.2 wheel](https://pypi.org/project/geonamescache/3.0.2/),
serialized together as compact UTF-8 JSON and gzip-compressed. All source
records and fields, including alternate names and order, are retained. The
wheel SHA-256 is
`b830e8942f2d58c7e68782dcf4dff2ffe8c4104a35ee881ed1ad4023cefcdba4`.
The generated artifact SHA-256 is
`66dd00e2783fe4ff8ee1186aa61a22ef2edc3b25a5f25a129ba2d0e09c007e1e`.

GeoNamesCache is MIT licensed; its copyright and license are reproduced in
`geonamescache.LICENSE`. The underlying geographical data is from
[GeoNames](https://www.geonames.org/), whose data is available under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
Region display names have separate provenance in `admin1.SOURCE.md`.

To rebuild, download the pinned wheel, then run:

```sh
python -m pip download --no-deps geonamescache==3.0.2 -d /tmp/geonames-wheel
python scripts/build_geonames_catalogue.py /tmp/geonames-wheel/geonamescache-3.0.2-py3-none-any.whl
```

The generator verifies the upstream wheel hash and uses a fixed gzip timestamp.
No network access or package installation is needed at application runtime.
