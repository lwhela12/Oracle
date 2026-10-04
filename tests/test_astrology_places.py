"""Offline place-search and trusted chart-location contracts."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

from flask import Flask

from astrology.place_routes import blueprint as places_blueprint
from astrology.places import (
    PlaceLookupError,
    PlaceQueryError,
    _Catalogue,
    _normalise,
    get_place,
    search_places,
)
from astrology.service import ChartInputError, prepare_chart


def _city(gid, name, latitude, longitude, country, population, timezone_name,
          region='', alternates=()):
    return {
        'geonameid': gid,
        'name': name,
        'latitude': latitude,
        'longitude': longitude,
        'countrycode': country,
        'population': population,
        'timezone': timezone_name,
        'admin1code': region,
        'alternatenames': list(alternates),
    }


def _synthetic_catalogue():
    cities = {
        '1': _city(1, 'Springfield', 39.8, -89.6, 'US', 100000, 'America/Chicago', 'IL'),
        '2': _city(2, 'Springfield', 44.0, -123.0, 'US', 60000, 'America/Los_Angeles', 'OR'),
        '3': _city(3, 'München', 48.14, 11.58, 'DE', 1500000, 'Europe/Berlin', '02', ('Munich',)),
        '4': _city(4, 'Munichville', 1.0, 2.0, 'US', 1000, 'America/New_York', 'NY'),
        '5': _city(5, 'Paris', 48.86, 2.35, 'FR', 2100000, 'Europe/Paris', '11'),
        '6': _city(6, 'Toronto', 43.70, -79.42, 'CA', 2800000, 'America/Toronto', '08'),
    }
    return _Catalogue(
        cities=cities,
        countries={
            'US': {'name': 'United States', 'iso3': 'USA', 'fips': 'US'},
            'DE': {'name': 'Germany', 'iso3': 'DEU', 'fips': 'GM'},
            'FR': {'name': 'France', 'iso3': 'FRA', 'fips': 'FR'},
            'CA': {'name': 'Canada', 'iso3': 'CAN', 'fips': 'CA'},
        },
        us_states={
            'IL': {'name': 'Illinois'}, 'OR': {'name': 'Oregon'}, 'NY': {'name': 'New York'},
        },
        admin1_names={'DE.02': 'Bavaria', 'FR.11': 'Île-de-France', 'CA.08': 'Ontario'},
        canonical_names=tuple((_normalise(city['name']), city) for city in cities.values()),
    )


class PlaceSearchTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = _synthetic_catalogue()
        self.catalogue_patch = patch('astrology.places._catalogue', return_value=self.catalogue)
        self.catalogue_patch.start()
        self.addCleanup(self.catalogue_patch.stop)

    def test_exact_prefix_population_and_qualifier_ordering(self):
        matches = search_places('Springfield')
        self.assertEqual([place['id'] for place in matches], ['geonames:1', 'geonames:2'])
        self.assertEqual(search_places('Springfield, Oregon')[0]['id'], 'geonames:2')
        self.assertEqual(search_places('Springfield, USA')[0]['region'], 'Illinois')

    def test_diacritics_and_common_alternate_names(self):
        for query in ('München, DE', 'Munchen, Germany', 'Munich, DE'):
            with self.subTest(query=query):
                self.assertEqual(search_places(query)[0]['id'], 'geonames:3')

    def test_global_region_names_and_qualifiers(self):
        paris = search_places('Paris, Ile-de-France')[0]
        self.assertEqual(paris['label'], 'Paris, Île-de-France, France')
        self.assertEqual(paris['region'], 'Île-de-France')
        toronto = search_places('Toronto, Ontario, Canada')[0]
        self.assertEqual(toronto['label'], 'Toronto, Ontario, Canada')
        self.assertEqual(toronto['region'], 'Ontario')

    def test_result_schema_limit_and_lookup(self):
        place = get_place('geonames:1')
        self.assertEqual(set(place), {
            'id', 'name', 'label', 'country', 'region', 'latitude', 'longitude', 'timezone',
        })
        self.assertEqual(place['label'], 'Springfield, Illinois, United States')
        self.assertLessEqual(len(search_places('Sp')), 8)

    def test_invalid_queries_and_ids_are_typed_and_do_not_echo_input(self):
        for query in (None, '', 'x', 'x' * 101, ', US', 'Paris,'):
            with self.subTest(query=query), self.assertRaises(PlaceQueryError):
                search_places(query)
        for place_id, code in ((None, 'invalid_place_id'), ('PRIVATE', 'invalid_place_id'),
                               ('geonames:999', 'place_not_found')):
            with self.subTest(place_id=place_id), self.assertRaises(PlaceLookupError) as raised:
                get_place(place_id)
            self.assertEqual(raised.exception.code, code)
            self.assertNotIn('PRIVATE', str(raised.exception))


class PlaceRouteTests(unittest.TestCase):
    def setUp(self):
        application = Flask(__name__)
        application.register_blueprint(places_blueprint)
        self.client = application.test_client()
        self.env = patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_post_only_success_is_no_store_and_attributed(self):
        match = {'id': 'geonames:1', 'name': 'Test'}
        with patch('astrology.place_routes.search_places', return_value=[match]) as search:
            response = self.client.post('/astrology/places', json={'query': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['places'], [match])
        self.assertEqual(response.json['attribution']['name'], 'GeoNames')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        search.assert_called_once_with('Test')
        self.assertEqual(self.client.get('/astrology/places?query=PRIVATE').status_code, 405)

    def test_disabled_does_not_search(self):
        with patch.dict(os.environ, {'ORACLE_ASTROLOGY_ENABLED': '0'}), \
             patch('astrology.place_routes.search_places') as search:
            response = self.client.post('/astrology/places', json={'query': 'Test'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json['code'], 'astrology_disabled')
        search.assert_not_called()

    def test_request_validation_and_private_failures(self):
        cases = [
            ({}, 400), ({'query': 'Test', 'extra': 'PRIVATE'}, 400),
            ({'query': 4}, 400), ({'query': 'x'}, 400),
        ]
        for payload, status in cases:
            with self.subTest(payload=payload):
                response = self.client.post('/astrology/places', json=payload)
                self.assertEqual(response.status_code, status)
                self.assertNotIn('PRIVATE', response.get_data(as_text=True))
        for raw in ('{', '{"query":"a","query":"b"}'):
            self.assertEqual(self.client.post('/astrology/places', data=raw,
                                              content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/astrology/places', data='{}').status_code, 415)
        self.assertEqual(self.client.post('/astrology/places', data=' ' * 1025,
                                          content_type='application/json').status_code, 413)

    def test_catalogue_failure_is_safe(self):
        with patch('astrology.place_routes.search_places', side_effect=ImportError('PRIVATE path')):
            response = self.client.post('/astrology/places', json={'query': 'Test'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json['code'], 'astrology_unavailable')
        self.assertNotIn('PRIVATE', response.get_data(as_text=True))


PLACE = {
    'id': 'geonames:5128581',
    'name': 'New York City',
    'label': 'New York City, New York, United States',
    'country': 'United States',
    'region': 'New York',
    'latitude': 40.71427,
    'longitude': -74.00597,
    'timezone': 'America/New_York',
}


class PlaceServiceValidationTests(unittest.TestCase):
    def test_place_conflicts_and_unknown_id_are_typed(self):
        cases = [
            ({'chart_kind': 'natal', 'place_id': PLACE['id'], 'location': {'latitude': 0, 'longitude': 0},
              'birth': {'local_datetime': '2000-01-01T00:00'}}, 'conflicting_location'),
            ({'chart_kind': 'natal', 'place_id': PLACE['id'],
              'birth': {'local_datetime': '2000-01-01T00:00', 'timezone': 'America/New_York'}},
             'conflicting_timezone'),
            ({'chart_kind': 'current', 'place_id': 'PRIVATE'}, 'invalid_place_id'),
        ]
        for payload, code in cases:
            with self.subTest(code=code), self.assertRaises(ChartInputError) as raised:
                prepare_chart(payload)
            self.assertEqual(raised.exception.code, code)
        with patch('astrology.places.get_place',
                   side_effect=PlaceLookupError('place_not_found', 'Place was not found.')):
            with self.assertRaises(ChartInputError) as raised:
                prepare_chart({'chart_kind': 'current', 'place_id': 'geonames:999'})
        self.assertEqual(raised.exception.code, 'place_not_found')


@unittest.skipUnless(importlib.util.find_spec('swisseph'), 'Optional Swiss Ephemeris binding is not installed')
class PlaceServiceCalculationTests(unittest.TestCase):
    def test_natal_place_uses_historical_timezone_without_mutating_input(self):
        payload = {'chart_kind': 'natal', 'place_id': PLACE['id'],
                   'birth': {'local_datetime': '2024-11-03T01:30:00', 'fold': 1}}
        original = deepcopy(payload)
        with patch('astrology.places.get_place', return_value=deepcopy(PLACE)):
            chart = prepare_chart(payload)
        self.assertEqual(payload, original)
        self.assertEqual(chart['inputs']['utc'], '2024-11-03T06:30:00Z')
        self.assertEqual(chart['location_precision'], 'city_center')
        self.assertEqual(chart['place'], PLACE)
        self.assertEqual(chart['input_resolution']['location_source'], 'geonames')
        self.assertEqual(chart['input_resolution']['timezone_source'], 'geonames_iana_history')
        self.assertEqual(chart['input_resolution']['local_datetime'], '2024-11-03T01:30:00')
        self.assertEqual(chart['input_resolution']['fold'], 1)

    def test_new_york_dst_gap_and_current_local_time(self):
        with patch('astrology.places.get_place', return_value=deepcopy(PLACE)):
            with self.assertRaises(ChartInputError) as raised:
                prepare_chart({'chart_kind': 'natal', 'place_id': PLACE['id'],
                               'birth': {'local_datetime': '2024-03-10T02:30:00'}})
            chart = prepare_chart({'chart_kind': 'current', 'place_id': PLACE['id'],
                                   'instant_utc': '2024-07-01T12:00:00Z'})
        self.assertEqual(raised.exception.code, 'nonexistent_birth_time')
        self.assertEqual(chart['input_resolution']['local_datetime'], '2024-07-01T08:00:00-04:00')
        self.assertIn('ascendant', chart)


@unittest.skipUnless(importlib.util.find_spec('geonamescache'), 'Optional GeoNames catalogue is not installed')
class RealGeoNamesTests(unittest.TestCase):
    def test_sierra_vista_and_diacritics_from_packaged_catalogue(self):
        # Remove the synthetic cache only if another test/process populated it.
        from astrology import places
        places._catalogue.cache_clear()
        sierra_vista = search_places('Sierra Vista, AZ')[0]
        self.assertEqual(sierra_vista['id'], 'geonames:5314328')
        self.assertEqual(sierra_vista['timezone'], 'America/Phoenix')
        self.assertEqual(sierra_vista['region'], 'Arizona')
        sao_paulo = search_places('Sao Paulo, Brazil')[0]
        self.assertEqual(sao_paulo['name'], 'São Paulo')
        self.assertEqual(search_places('Paris, Ile-de-France')[0]['region'], 'Île-de-France')
        self.assertEqual(search_places('Toronto, Ontario, Canada')[0]['region'], 'Ontario')
        self.assertEqual(get_place(sierra_vista['id']), sierra_vista)


if __name__ == '__main__':
    unittest.main()
