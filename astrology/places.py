"""Offline GeoNames city lookup for astrology location inputs.

The catalogue comes from the installed ``geonamescache`` package.  Loading is
lazy, process-local, and performs no network requests.  Coordinates describe a
city centre; they are not an exact birthplace.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MIN_CITY_POPULATION = 1000
MAX_RESULTS = 8
ATTRIBUTION = {'name': 'GeoNames', 'url': 'https://www.geonames.org/'}
_PLACE_ID = re.compile(r'geonames:([1-9]\d{0,11})\Z')


class PlaceLookupError(ValueError):
    """A safe, typed failure for a user-supplied place identifier."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class PlaceQueryError(ValueError):
    """A safe, typed failure for a place search query."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    characters = []
    for character in decomposed:
        if unicodedata.combining(character):
            continue
        characters.append(character if character.isalnum() else ' ')
    return ' '.join(''.join(characters).split())


@dataclass(frozen=True)
class _Catalogue:
    cities: dict
    countries: dict
    us_states: dict
    admin1_names: dict
    canonical_names: tuple


@lru_cache(maxsize=1)
def _catalogue() -> _Catalogue:
    # Import only when a place search/resolution is actually requested.  This
    # keeps the large packaged city dataset out of ordinary application startup.
    import geonamescache

    cache = geonamescache.GeonamesCache(min_city_population=MIN_CITY_POPULATION)
    cities = cache.get_cities()
    with (Path(__file__).with_name('data') / 'admin1.json').open(encoding='utf-8') as source:
        admin1_names = json.load(source)
    return _Catalogue(
        cities=cities,
        countries=cache.get_countries(),
        us_states=cache.get_us_states(),
        admin1_names=admin1_names,
        canonical_names=tuple((_normalise(city.get('name', '')), city) for city in cities.values()),
    )


def _country(catalogue: _Catalogue, city: dict) -> tuple[str, dict]:
    code = str(city.get('countrycode') or '').upper()
    data = catalogue.countries.get(code) or {}
    return str(data.get('name') or code), data


def _region(catalogue: _Catalogue, city: dict) -> str | None:
    code = str(city.get('admin1code') or '')
    country_code = str(city.get('countrycode') or '').upper()
    if country_code and code:
        official_name = catalogue.admin1_names.get(f'{country_code}.{code}')
        if official_name:
            return str(official_name)
    if country_code == 'US':
        return str((catalogue.us_states.get(code) or {}).get('name') or code) or None
    return f'Region {code}' if code else None


def _public_place(catalogue: _Catalogue, city: dict) -> dict:
    timezone = city.get('timezone')
    if not isinstance(timezone, str) or not timezone:
        raise PlaceLookupError('invalid_place_timezone', 'The selected place has no supported timezone.')
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise PlaceLookupError('invalid_place_timezone', 'The selected place has no supported timezone.') from error

    country, _ = _country(catalogue, city)
    region = _region(catalogue, city)
    name = str(city['name'])
    label_parts = [name]
    if region:
        label_parts.append(region)
    if country:
        label_parts.append(country)
    return {
        'id': f"geonames:{city['geonameid']}",
        'name': name,
        'label': ', '.join(label_parts),
        'country': country,
        'region': region,
        'latitude': float(city['latitude']),
        'longitude': float(city['longitude']),
        'timezone': timezone,
    }


def _qualifier_matches(catalogue: _Catalogue, city: dict, qualifiers: tuple[str, ...]) -> bool:
    if not qualifiers:
        return True
    country_name, country = _country(catalogue, city)
    region = _region(catalogue, city)
    values = {
        _normalise(value)
        for value in (
            country_name,
            city.get('countrycode'),
            country.get('iso3'),
            country.get('fips'),
            region,
            city.get('admin1code'),
        )
        if value
    }
    return all(any(qualifier == value or value.startswith(qualifier) for value in values)
               for qualifier in qualifiers)


def search_places(query: str, *, limit: int = MAX_RESULTS) -> list[dict]:
    """Search local city data by canonical or alternate name.

    A comma introduces state/country qualifiers, for example
    ``Sierra Vista, AZ`` or ``Paris, France``.  Results are stable: canonical
    exact matches, canonical prefixes/common alternate exact matches,
    alternate prefixes, then population and stable catalogue fields.
    """
    if not isinstance(query, str):
        raise PlaceQueryError('invalid_query', 'Place query must be text between 2 and 100 characters.')
    query = query.strip()
    if not 2 <= len(query) <= 100:
        raise PlaceQueryError('invalid_query', 'Place query must be text between 2 and 100 characters.')
    components = [component.strip() for component in query.split(',')]
    if not components[0] or any(not component for component in components[1:]):
        raise PlaceQueryError('invalid_query', 'Enter a city, optionally followed by a state or country.')
    name_query = _normalise(components[0])
    qualifiers = tuple(_normalise(component) for component in components[1:])
    if len(name_query) < 2 or any(not qualifier for qualifier in qualifiers):
        raise PlaceQueryError('invalid_query', 'Enter a city, optionally followed by a state or country.')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f'limit must be an integer from 1 through {MAX_RESULTS}')

    catalogue = _catalogue()
    raw_name_query = components[0].casefold()
    ranked = []
    for canonical, city in catalogue.canonical_names:
        if not _qualifier_matches(catalogue, city, qualifiers):
            continue
        if canonical == name_query:
            rank = 0
        elif (canonical.startswith(name_query) or
              any(isinstance(alias, str) and alias.casefold() == raw_name_query
                  for alias in city.get('alternatenames', ()))):
            rank = 1
        elif any(isinstance(alias, str) and alias.casefold().startswith(raw_name_query)
                 for alias in city.get('alternatenames', ())):
            rank = 2
        else:
            continue
        population = city.get('population')
        population = population if isinstance(population, int) else 0
        ranked.append((rank, -population, canonical, str(city.get('countrycode') or ''),
                       str(city.get('admin1code') or ''), int(city['geonameid']), city))

    results = []
    for *_, city in sorted(ranked):
        try:
            results.append(_public_place(catalogue, city))
        except PlaceLookupError:
            continue
        if len(results) == limit:
            break
    return results


def get_place(place_id: str) -> dict:
    """Resolve a GeoNames ID to server-trusted coordinates and timezone."""
    if not isinstance(place_id, str) or not (match := _PLACE_ID.fullmatch(place_id)):
        raise PlaceLookupError('invalid_place_id', 'Place id must use the geonames:<number> format.')
    catalogue = _catalogue()
    city = catalogue.cities.get(match.group(1))
    if city is None:
        raise PlaceLookupError('place_not_found', 'The selected place is not in the local city catalogue.')
    return _public_place(catalogue, city)
