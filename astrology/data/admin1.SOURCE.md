# GeoNames admin-1 region names

`admin1.json` is a normalized mapping of country/admin-1 codes to display names
from GeoNames [`admin1CodesASCII.txt`](https://download.geonames.org/export/dump/admin1CodesASCII.txt).
It was retrieved on 2026-10-04 and generated from the first two tab-separated
columns, sorted by code and serialized as compact UTF-8 JSON. The downloaded
source SHA-256 was
`1da92a6323a5fec3176f3f743bf4cf4040fd56a876da55e46fbca23c863aa60a`.

GeoNames states in its [data dump readme](https://download.geonames.org/export/dump/readme.txt)
that the data is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/).
The application loads this bundled file locally and does not contact GeoNames at
runtime.
