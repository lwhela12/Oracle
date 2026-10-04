# Source and licensing record

This directory is an isolated feasibility pilot, not a fork of Swiss Ephemeris.
No Swiss Ephemeris implementation was copied, translated, vendored, or imported
by `engine.py`, `run.py`, or its tests. The existing Oracle engine is called only
by the separate `export_baseline.py` comparison harness, in a different virtualenv.
Do not bundle that harness as part of a standalone engine distribution.

## Original implementation and scope

Our original code implements chart assembly, plane-intersection angle geometry,
explicit product conventions, validation, and source provenance. It does not
numerically integrate Solar System orbits: JPL has already performed that work.
Skyfield and jplephem evaluate the kernel and perform astronomical corrections.
The public source of a mathematical formula is identified below; no Swiss source
is used to implement it. Compatibility measurements do not tune constants to
match the old engine.

The new original code has no public license grant at this stage. The owner can
choose a license for original contributions before distribution. This does not
relicense JPL data or third-party packages. Nothing here changes the license of
the existing Oracle app. A dependency/distribution review remains necessary
before making a legal compliance claim or shipping a standalone package.

## Dependencies and data

| Component | Installed version | License / conditions |
| --- | --- | --- |
| Skyfield | 1.55 | MIT; preserve license/copyright notice when distributed |
| jplephem | 2.24 | MIT; preserve notice |
| NumPy | 2.0.2 | BSD family; wheel also carries notices for bundled components |
| sgp4 | 2.25 | MIT; installed by Skyfield, not used for planets |
| certifi | 2026.7.22 | MPL-2.0 certificate data package; retain its terms |
| DE440s | pinned SHA-256 below | JPL/NAIF kernel use/redistribution rules |

Versions and license metadata were inspected in `scratch/jpl-venv` on October 4,
2026. This table is not a substitute for preserving each distribution's actual
license files. MIT/BSD dependencies do not require this original application
code to become AGPL. Do not claim ownership of the dependency code or kernel.

- [Skyfield license](https://github.com/skyfielders/python-skyfield/blob/master/LICENSE).
- [jplephem](https://pypi.org/project/jplephem/) (installed distribution metadata: MIT).
- [NumPy license](https://numpy.org/doc/stable/license.html).
- [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html): commercial use is allowed;
  kernels may be downloaded/used and redistributed unmodified under the stated
  rules. Modified kernels have additional attribution/metadata requirements.
  This pilot uses an unmodified official kernel and makes no NASA endorsement claim.

DE440s URL:
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp

SHA-256:
`c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2`

The hash pins the file downloaded over official HTTPS in this pilot; it is not
claimed to be a separately authenticated JPL-published checksum. Keep the 32 MB
file under ignored `scratch/`; never fetch it automatically on a reading request.
The file spans 1849-12-25 to 2150-01-21; accepted pilot dates are 1850 through
2149 to leave padding for finite differences and light time.

## Astronomical conventions

- [Skyfield positions](https://rhodesmill.org/skyfield/positions.html) and
  [reference frames](https://rhodesmill.org/skyfield/api-framelib.html): observe
  each target from Earth's center, apply apparent corrections, then transform
  into the true ecliptic/equinox of date. No topocentric parallax or refraction.
- [Kernel targets and coverage](https://rhodesmill.org/skyfield/planets.html):
  Mars through Pluto are system barycenters in this kernel. They must not be
  described as exact physical planet centers. Supplementary satellite kernels
  would be needed for center-specific equivalence.
- [Time](https://rhodesmill.org/skyfield/time.html): Skyfield's bundled leap-second
  and Delta T data, explicitly offline, plus the [USNO historical drift table](https://maia.usno.navy.mil/ser7/tai-utc.dat)
  for 1961–1971. Earlier civil labels use an explicit UT1 approximation. See
  [TIME_POLICY.md](TIME_POLICY.md); future UT1 and leap seconds remain uncertain.
- Ascendant/MC: independently constructed plane intersections. Rotate geodetic
  zenith/east vectors from true equatorial to ecliptic axes, intersect horizon
  and meridian planes with the ecliptic, choose eastern/upper intersections.
  Apparent sidereal time supplies local rotation. No copied house routine.
  Whole Sign cusps start at the ascending sign's zero longitude.
- Speeds: central finite differences of apparent longitude, using two-part TT
  Julian dates and a default 0.001-day half-step. Near-zero speed is flagged.
- Aspects: the existing product's chosen 0/60/90/120/180-degree angles and
  8/5/7/7/8-degree orbs; these are interpretive settings, not JPL measurements.

## Current Vedic sidereal mathematics

The app's JPL Vedic path uses the published Indian Astronomical Ephemeris
post-2021 polynomial and IAU 2000A/2006 nutation adjustment, independently
implemented in `sidereal.py`. The original constant and polynomial are factual
mathematical data, not copied Swiss implementation. [LAHIRI_RESEARCH.md](LAHIRI_RESEARCH.md)
records official publication URLs, exact pages, hashes, 458 accepted table
references and 25 inconsistent continuation cells retained as diagnostics.
The convention is named `iae-2021`; exact Lahiri identity is not asserted.
Mean Rahu still uses IERS equation 5.43 and has a separate documented PAC residual.

## Original experimental sidereal mathematics (diagnostic CLI only)

1. [IERS Conventions chapter 5, section 5.7.2, equation 5.43](https://iers-conventions.obspm.fr/content/chapter5/icc5.pdf)
   supplies the mean ascending lunar node. The constant is degrees, remaining
   coefficients arcseconds; time is Julian centuries from J2000. TT may replace
   TDB for this argument. No hard validity interval is established by that section.
   We rotate the mean node into the true equinox frame before subtracting the
   experimental sidereal offset. This is still a mean node, not an apparent
   observed body or an instantaneous osculating node. Ketu is opposite Rahu.
2. [India's Positional Astronomy Centre explanation](https://packolkata.imd.gov.in/panchang/en/explanation)
   gives an adopted origin of 23°15′ at 0h March 21, 1956. It does not fully
   specify time scale, frame realization or propagation. The pilot **chooses**
   00:00 TT, mean ecliptic/equinox, then propagates the fixed direction with
   Skyfield. Those choices are experimental and are not a claim of standard Lahiri.
3. [PAC mean-position table](https://packolkata.imd.gov.in/panchang/en/bija_corrections)
   gives mean ayanamsa 24°13′24″ and mean Rahu 313°42′25.31″ at March 22, 2026,
   05:30 IST. Report observed differences, not a manufactured Lahiri pass threshold.
4. [PAC star table](https://packolkata.imd.gov.in/panchang/en/nakshatra_division)
   gives Spica 179°58′54″ on July 1, 2026, 05:29 IST. Simply forcing Spica to
   180° is not equivalent to that published convention.

## Comparison data

`horizons_fixture.json` contains 30 factual numeric longitudes extracted from
previously cached official JPL Horizons responses: ten bodies on January 1, 2000,
April 15, 2024, and October 4, 2026, each at 12:00 UTC. Requests used observer
quantity 31, center `500@399`, extra precision, and planetary-center targets.
See [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html). The full
existing response cache remains in ignored `scratch/astrology-prototype/reference`.
This is an external implementation check sharing the JPL ephemeris family, not
validation against independent observational data. It is not a new live API test.
