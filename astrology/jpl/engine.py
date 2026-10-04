"""Independent, offline JPL chart engine. No Swiss Ephemeris dependency.

Original application glue and plane-intersection geometry; astronomy provided by
MIT-licensed Skyfield/jplephem and JPL DE440s. See the project source record.
This is deliberately not a complete Swiss Ephemeris implementation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from itertools import combinations
import math
from pathlib import Path

import numpy as np
from skyfield.api import load, load_file
from skyfield.framelib import ecliptic_frame, ICRS_to_J2000
from skyfield.nutationlib import mean_obliquity
from .time_scales import civil_time
from .sidereal import true_ayanamsa, nutation_longitude_degrees, CONVENTION_ID, CONVENTION_NAME

ENGINE_VERSION = '1.0.0'
KERNEL_SHA256 = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
KERNEL_URL = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp'
START = datetime(1850, 1, 1, tzinfo=timezone.utc)
STOP = datetime(2150, 1, 1, tzinfo=timezone.utc)  # exclusive, with padding for light time/differencing
SIGNS = ('Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces').split()
NAKSHATRAS = ('Ashwini|Bharani|Krittika|Rohini|Mrigashira|Ardra|Punarvasu|Pushya|Ashlesha|Magha|Purva Phalguni|Uttara Phalguni|Hasta|Chitra|Swati|Vishakha|Anuradha|Jyeshtha|Mula|Purva Ashadha|Uttara Ashadha|Shravana|Dhanishta|Shatabhisha|Purva Bhadrapada|Uttara Bhadrapada|Revati').split('|')
TARGETS = {'Sun': 10, 'Moon': 301, 'Mercury': 199, 'Venus': 299, 'Mars': 4,
           'Jupiter': 5, 'Saturn': 6, 'Uranus': 7, 'Neptune': 8, 'Pluto': 9}
# Match the product's declared aspect policy; these are choices, not ephemeris data.
ASPECTS = {'conjunction': (0, 8), 'sextile': (60, 5), 'square': (90, 7),
           'trine': (120, 7), 'opposition': (180, 8)}


def signed_difference(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def zodiac(degrees):
    degrees = float(degrees) % 360.0
    return {'longitude': degrees, 'sign': SIGNS[int(degrees // 30)],
            'degrees_in_sign': degrees % 30}


def nakshatra(degrees):
    quarter = int((degrees % 360) * 3 / 10)
    return {'name': NAKSHATRAS[quarter // 4], 'index': quarter // 4 + 1,
            'pada': quarter % 4 + 1,
            'lord': ('Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury')[(quarter//4)%9]}


def mean_node(tt_jd):
    """IERS Conventions 2010 eq 5.43; mean node in mean ecliptic/equinox of date.

    t is Julian centuries from J2000; IERS permits TT in place of TDB here.
    This is NOT an instantaneous/osculating node derived from Moon vectors.
    """
    t = (float(tt_jd) - 2451545.0) / 36525.0
    arcseconds = (-6962890.5431 * t + 7.4722 * t**2
                  + 0.007702 * t**3 - 0.00005939 * t**4)
    return (125.04455501 + arcseconds / 3600.0) % 360.0


def mean_ecliptic_rotation(t):
    epsilon = math.radians(float(mean_obliquity(t.tdb)) / 3600.0)
    c, s = math.cos(epsilon), math.sin(epsilon)
    rotation = np.array([[1, 0, 0], [0, c, s], [0, -s, c]])
    # Skyfield 1.55's mean frame uses deprecated t.P, which can replace the
    # precession_matrix method with cached data before t.M is evaluated.
    # Use the same documented precession and frame-bias matrices directly.
    return rotation @ t.precession_matrix() @ ICRS_to_J2000


def angles(t, latitude, longitude):
    """Intersect ecliptic with horizon/meridian, choosing east/upper meridian.

    Uses geodetic latitude for local zenith, apparent sidereal time, no refraction
    or polar motion. Reject near-degenerate intersections instead of inventing angles.
    """
    theta = math.radians((float(t.gast) * 15 + longitude) % 360)
    phi = math.radians(latitude)
    zenith = np.array([math.cos(phi)*math.cos(theta), math.cos(phi)*math.sin(theta), math.sin(phi)])
    east = np.array([-math.sin(theta), math.cos(theta), 0.0])
    upper_meridian = np.array([math.cos(theta), math.sin(theta), 0.0])
    eq_to_ecl = ecliptic_frame.rotation_at(t) @ t.M.T
    pole = np.array([0.0, 0.0, 1.0])

    def intersection(normal, positive_half):
        vector = np.cross(pole, eq_to_ecl @ normal)
        length = np.linalg.norm(vector)
        if length < 1e-10:
            raise ValueError('Undefined ecliptic intersection at this place/time')
        vector /= length
        direction = float(np.dot(vector, eq_to_ecl @ positive_half))
        if abs(direction) < 1e-10:
            raise ValueError('Ambiguous eastern/upper ecliptic intersection')
        if direction < 0:
            vector = -vector
        return math.degrees(math.atan2(vector[1], vector[0])) % 360

    return intersection(zenith, east), intersection(east, upper_meridian)


class QuantumOracleEphemeris:
    def __init__(self, kernel_path):
        path = Path(kernel_path)
        # Verify once at startup. Do not auto-download or silently use another kernel.
        with path.open('rb') as source:
            digest = sha256()
            for chunk in iter(lambda: source.read(1024*1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != KERNEL_SHA256:
            raise ValueError('DE440s checksum mismatch; use the pinned official kernel')
        self.kernel = load_file(str(path))
        self.ts = load.timescale(builtin=True)  # no runtime IERS/network download
        self.earth = self.kernel[399]
        self.provenance = {
            'library': 'Quantum Oracle Ephemeris', 'library_version': ENGINE_VERSION,
            'engine_version': ENGINE_VERSION, 'skyfield_version': version('skyfield'),
            'jplephem_version': version('jplephem'), 'ephemeris_model': 'JPL DE440s',
            'kernel_sha256': KERNEL_SHA256, 'kernel_source': KERNEL_URL,
            'range_utc': '[1850-01-01, 2150-01-01)',
        }
        # Independent explicit convention; PAC does not fully specify the time/frame
        # realization. Do not advertise this experimental offset as exact Lahiri.
        anchor = self.ts.tt(1956, 3, 21, 0)
        a = math.radians(23.25)
        self.sidereal_origin = mean_ecliptic_rotation(anchor).T @ np.array([math.cos(a), math.sin(a), 0.0])

    def close(self):
        self.kernel.close()

    def _positions(self, t, names):
        observer = self.earth.at(t)
        return {name: float(observer.observe(self.kernel[TARGETS[name]]).apparent()
                            .frame_latlon(ecliptic_frame)[1].degrees) for name in names}

    def _offset(self, t):
        v = ecliptic_frame.rotation_at(t) @ self.sidereal_origin
        return math.degrees(math.atan2(v[1], v[0])) % 360

    def _node_true_frame(self, t):
        a = math.radians(mean_node(t.tt))
        v = mean_ecliptic_rotation(t).T @ np.array([math.cos(a), math.sin(a), 0.0])
        v = ecliptic_frame.rotation_at(t) @ v
        return math.degrees(math.atan2(v[1], v[0])) % 360

    def chart(self, instant, latitude=None, longitude=None, *, tradition='western', speed_step_days=0.001):
        if tradition not in ('western', 'sidereal-experimental', 'vedic'):
            raise ValueError('Choose western, vedic (IAE 2021), or sidereal-experimental')
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError('An aware datetime is required')
        utc = instant.astimezone(timezone.utc)
        if not START <= utc < STOP:
            raise ValueError('Engine supports UTC dates from 1850 through 2149 only')
        if (latitude is None) != (longitude is None):
            raise ValueError('Provide both latitude and longitude, or neither')
        local = latitude is not None
        if local:
            for value in (latitude, longitude):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError('Coordinates must be finite numbers')
            if not -90 < latitude < 90 or not -180 <= longitude <= 180:
                raise ValueError('Coordinates outside geographic bounds')
        if not 0.0001 <= speed_step_days <= 0.01:
            raise ValueError('Speed step must be between 0.0001 and 0.01 days')
        t, time_policy = civil_time(self.ts, utc)
        samples = [self.ts.tt_jd(t.whole, t.tt_fraction + delta) for delta in (-speed_step_days, 0, speed_step_days)]
        sidereal = tradition != 'western'
        names = list(TARGETS)[:7] if sidereal else list(TARGETS)
        snapshots = [self._positions(sample, names) for sample in samples]
        offset_method = true_ayanamsa if tradition == 'vedic' else self._offset
        offsets = [offset_method(sample) for sample in samples] if sidereal else [0, 0, 0]
        if sidereal:
            for sample, snapshot in zip(samples, snapshots):
                snapshot['Rahu'] = ((mean_node(sample.tt) + nutation_longitude_degrees(sample)) % 360
                                    if tradition == 'vedic' else self._node_true_frame(sample))
                snapshot['Ketu'] = (snapshot['Rahu'] + 180) % 360
        planets = {}
        for name in snapshots[1]:
            longitude_now = (snapshots[1][name] - offsets[1]) % 360
            speed = signed_difference(snapshots[2][name] - offsets[2], snapshots[0][name] - offsets[0]) / (2 * speed_step_days)
            planets[name] = {**zodiac(longitude_now), 'speed_degrees_per_day': speed,
                             'retrograde': speed < 0, 'station_uncertain': abs(speed) < 1e-5}
            if name in TARGETS:
                planets[name]['jpl_target'] = TARGETS[name]
                planets[name]['target_kind'] = 'system barycenter' if 1 <= TARGETS[name] <= 9 else 'body center'
            else:
                planets[name]['coordinate_model'] = 'mean lunar node expressed in true equinox of date, then selected sidereal offset; no light-time or aberration'
                planets[name]['node_model'] = 'IERS Conventions 2010 equation 5.43; Ketu opposite Rahu'
            if sidereal:
                planets[name]['nakshatra'] = nakshatra(longitude_now)
        warnings = ['Mars through Pluto use system barycenters, not individual planet centers.',
                    'Bundled Skyfield leap seconds and Delta T; historical/future Earth rotation is uncertain.',
                    'Longitudinal speeds are central finite differences; near-station direction requires special care.']
        warnings.extend(time_policy['warnings'])
        result = {
            'engine': dict(self.provenance), 'tradition': tradition,
            'zodiac': ('sidereal' if tradition == 'vedic' else 'experimental sidereal') if sidereal else 'tropical',
            'inputs': {'utc': utc.isoformat(), 'julian_day_tt': float(t.tt), 'julian_day_ut1': float(t.ut1)},
            'planets': planets, 'major_aspects': [],
            'provenance': {'coordinate_model': 'apparent geocentric true ecliptic/equinox of date',
                           'time_model': time_policy['conversion'], 'time_policy': time_policy,
                           'speed_step_days': speed_step_days, 'warnings': warnings},
        }
        if tradition == 'vedic':
            result['ayanamsa'] = {'name': CONVENTION_NAME, 'convention_id': CONVENTION_ID,
                                 'degrees': offsets[1], 'output_frame': 'true equinox of date'}
            result['vedic_aspects'] = []
            for name in list(TARGETS)[:7]:
                allowed = {7} | {'Mars':{4,8},'Jupiter':{5,9},'Saturn':{3,10}}.get(name,set())
                for other in planets:
                    distance=(int(planets[other]['longitude']//30)-int(planets[name]['longitude']//30))%12+1
                    if name != other and distance in allowed:
                        result['vedic_aspects'].append({'body_1':name,'body_2':other,'aspect':'graha drishti','house_distance':distance})
            result['provenance']['sidereal_convention'] = CONVENTION_ID
            warnings.append('IAE 2021 ayanamsa convention; do not assume identical results to another sidereal engine or historical convention.')
        elif sidereal:
            result['ayanamsa'] = {'name': 'Experimental PAC-1956 anchor, TT / Skyfield precession', 'degrees': offsets[1],
                                 'anchor': '23.25 degrees in mean ecliptic/equinox at 1956-03-21 00:00 TT',
                                 'output_frame': 'true equinox of date'}
            warnings.append('This is not validated standard Lahiri; PAC anchor realization remains unresolved.')
            warnings.append('Kernel coverage does not establish the accuracy interval of the IERS node polynomial or experimental sidereal convention.')
        if not sidereal:
            for first, second in combinations(planets, 2):
                separation = abs(signed_difference(planets[first]['longitude'], planets[second]['longitude']))
                for name, (exact, limit) in ASPECTS.items():
                    orb = abs(separation - exact)
                    if orb <= limit:
                        result['major_aspects'].append({'body_1': first, 'body_2': second,
                            'aspect': name, 'separation': separation, 'exact_angle': exact,
                            'orb': orb, 'orb_limit': limit})
                        break
        if local:
            asc, mc = angles(t, latitude, longitude)
            asc, mc = (asc - offsets[1]) % 360, (mc - offsets[1]) % 360
            result.update(ascendant=zodiac(asc), midheaven=zodiac(mc),
                          whole_sign_cusps=[{'house': i+1, **zodiac((int(asc//30)+i)*30)} for i in range(12)])
            if sidereal:
                result['ascendant']['nakshatra'] = nakshatra(asc)
            result['inputs'].update(latitude=latitude, longitude=longitude)
            for planet in planets.values():
                planet['whole_sign_house'] = (int(planet['longitude']//30)-int(asc//30)) % 12 + 1
            if abs(latitude) >= 66:
                warnings.append('Polar-circle geometry: rising/setting conventions need separate qualification.')
        return result


# Kept for the experimental command wrappers and their frozen qualification suite.
JPLPilot = QuantumOracleEphemeris
