"""Independent PAC/IAE post-2021 ayanamsa, not a Swiss compatibility shim.

See LAHIRI_RESEARCH.md and the official IAE 2026, printed pp. 378, 419, 442.
The source calls this 'ayanamsa'; it does not establish that every convention
marketed as 'Lahiri' is identical. Scalar Skyfield Time inputs only.
"""
import math

from skyfield.nutationlib import iau2000a_radians

CONVENTION_ID = 'iae-2021'
CONVENTION_NAME = 'Indian Astronomical Ephemeris (2021 convention)'
NUTATION_MODEL = 'IAU 2000A with IAU 2006 adjustment, IAE 2026 p. 442'
QUALIFIED_REFERENCE_YEARS = (2024, 2026, 2027)
TABLE_TOLERANCE_ARCSECONDS = 0.06
SOURCE_URLS = (
    'https://packolkata.imd.gov.in/download/IAE2024.zip',
    'https://packolkata.imd.gov.in/download/IAE2026.zip',
    'https://packolkata.imd.gov.in/download/IAE2027.zip',
)


def mean_ayanamsa(tt_jd):
    """Degrees, mean equinox of date; polynomial adopted by IAE from 2021.

    TT Julian centuries from J2000. The J2000 constant is 23 deg 51 min
    25.53 sec; every polynomial coefficient below is in arcseconds.
    Reference qualification is finite, not a global accuracy guarantee.
    """
    jd = float(tt_jd)
    if not math.isfinite(jd):
        raise ValueError('A finite scalar TT Julian date is required')
    t = (jd - 2451545.0) / 36525.0
    precession = t * (5028.796195 + t * (1.1054348 + t * (
        0.00007964 + t * (-0.00023857 - 0.0000000383 * t))))
    return (23 * 3600 + 51 * 60 + 25.53 + precession) / 3600.0


def nutation_longitude_degrees(t):
    """IAE's IAU 2006-adjusted nutation in longitude, in degrees.

    This is an orientation correction, not light time or aberration.
    Skyfield supplies the independent IAU 2000A series evaluation.
    """
    centuries = (float(t.tt) - 2451545.0) / 36525.0
    if not math.isfinite(centuries):
        raise ValueError('A finite scalar Skyfield Time is required')
    dpsi, _ = iau2000a_radians(t)
    adjustment = 1.0 + 0.4697e-6 - 2.7774e-6 * centuries
    return math.degrees(float(dpsi)) * adjustment


def true_ayanamsa(t):
    """Degrees from the true equinox: published mean ayanamsa plus nutation."""
    return mean_ayanamsa(t.tt) + nutation_longitude_degrees(t)
