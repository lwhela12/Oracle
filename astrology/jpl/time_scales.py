"""Explicit civil-time policy, independent of Swiss Ephemeris.

1961–1971 coefficients are factual data from USNO's tai-utc.dat. No ERFA/SOFA
or Swiss implementation is copied. See TIME_POLICY.md for the limits of the
pre-1961 approximation and of predictions beyond bundled Earth-rotation data.
"""
from datetime import datetime, timezone

# Effective date, TAI minus UTC seconds, reference MJD, drift seconds/day.
# https://maia.usno.navy.mil/ser7/tai-utc.dat (checked October 4, 2026)
DRIFT_UTC = (
    ((1961, 1, 1), 1.4228180, 37300, .001296),
    ((1961, 8, 1), 1.3728180, 37300, .001296),
    ((1962, 1, 1), 1.8458580, 37665, .0011232),
    ((1963, 11, 1), 1.9458580, 37665, .0011232),
    ((1964, 1, 1), 3.2401300, 38761, .001296),
    ((1964, 4, 1), 3.3401300, 38761, .001296),
    ((1964, 9, 1), 3.4401300, 38761, .001296),
    ((1965, 1, 1), 3.5401300, 38761, .001296),
    ((1965, 3, 1), 3.6401300, 38761, .001296),
    ((1965, 7, 1), 3.7401300, 38761, .001296),
    ((1965, 9, 1), 3.8401300, 38761, .001296),
    ((1966, 1, 1), 4.3131700, 39126, .002592),
    ((1968, 2, 1), 4.2131700, 39126, .002592),
)
UTC = timezone.utc


def civil_time(ts, instant):
    """Return Skyfield Time and a serializable explanation of its time policy."""
    instant = instant.astimezone(UTC)
    second = instant.second + instant.microsecond / 1e6
    fields = (instant.year, instant.month, instant.day, instant.hour, instant.minute, second)
    if instant.year < 1961:
        t = ts.ut1(*fields)
        policy = {'input_scale': 'historical civil UT1 approximation',
                  'conversion': 'Timezone-normalized historical clock treated as UT1; TT from Skyfield Delta T reconstruction',
                  'warnings': ['Before 1961, civil time is approximated as UT1; recorded clocks, local time history and Delta T limit accuracy.']}
    elif instant.year < 1972:
        effective, base, reference, rate = next(row for row in reversed(DRIFT_UTC)
                                               if tuple(fields[:3]) >= row[0])
        # Standard datetime ordinal: Gregorian 0001-01-01 midnight is JD 1721425.5.
        midnight_jd = instant.toordinal() + 1721424.5
        fraction = (instant.hour * 3600 + instant.minute * 60 + second) / 86400
        mjd = midnight_jd - 2400000.5 + fraction
        offset = base + (mjd - reference) * rate
        t = ts.tai_jd(midnight_jd, fraction + offset / 86400)
        policy = {'input_scale': 'UTC with historical frequency drift',
                  'conversion': 'USNO TAI-UTC piecewise drift, TT=TAI+32.184 seconds; UT1 from Skyfield Delta T',
                  'tai_minus_utc_seconds': offset, 'usno_segment_start': '%04d-%02d-%02d' % effective,
                  'warnings': []}
    else:
        t = ts.from_datetime(instant)
        policy = {'input_scale': 'UTC', 'conversion': 'Skyfield pinned leap-second table; TT and reconstructed/predicted UT1', 'warnings': []}
    last_tt = float(ts.delta_t_table[0][-1])
    policy['earth_rotation_table_last_tt_jd'] = last_tt
    policy['earth_rotation_table_last_date'] = ts.tt_jd(last_tt).tt_strftime('%Y-%m-%d')
    policy['earth_rotation_extrapolated'] = float(t.tt) > last_tt
    if policy['earth_rotation_extrapolated']:
        policy['warnings'].append('Beyond the bundled Earth-rotation table: UT1 is extrapolated and future leap seconds are unknown; angles are predictions.')
    return t, policy
