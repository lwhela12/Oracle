# JPL pilot: feasible foundation, not yet a production replacement

**Historical first-pass report.** Subsequent historical-time fixes, Vedic
qualification and local app integration are documented in [PHASE2.md](PHASE2.md).
The measurements and limitations below describe the original pilot snapshot.

October 4, 2026. **The independent planetary/Western-chart approach works.**
The prototype runs without Swiss Ephemeris installed and does not need network
access during startup or a reading. Its original implementation can have its own
licensing decision, subject to retaining the separate terms of its dependencies
and data. No production code, deployment, or public license was changed.

The pilot is deliberately narrower than Swiss Ephemeris. It evaluates JPL's
existing ephemeris through Skyfield and adds our chart mathematics; it does not
recreate the Solar System integration or all Swiss functions.

## Measured results

| Check | Observation |
| --- | --- |
| NASA Horizons reference | 30 longitudes across ten bodies and three epochs; largest residual **0.09533 arcseconds** |
| Existing Swiss/Moshier comparison | 86 synthetic charts, including six high-latitude cases; 860 Western planetary positions |
| Modern nonpolar subset | 56 charts dated 1972–2026; maximum longitude difference **1.37114 arcseconds** |
| Modern local angles | Maximum Ascendant difference **6.58603 arcseconds**, MC **4.54624 arcseconds** |
| Same UT1 diagnostic, modern subset | Angle difference shrinks to **0.00231 arcseconds or less**; time-model differences explain most raw angle residuals |
| Western categories across all 86 charts | **Zero** sign, Whole Sign house assignment, retrograde-label, or aspect-membership differences |
| Experimental sidereal comparison | One nakshatra/pada mismatch; **not qualified as Lahiri** |
| Warm Western chart calculation | About **18 ms median** on this Mac, excluding interpreter startup, kernel verification, network, and LLM work |
| Kernel size | About 32 MB, pinned and verified once on initialization |

One arcsecond is 1/3600 of a degree. Small residuals can still change a sign,
house or pada at an exact boundary. Categorical agreement in a sample is not
a guarantee at every date or boundary. The Horizons comparison uses cached
official responses and shares the JPL ephemeris family, so it is not independent
observational verification or a newly performed live NASA API check.

Machine-readable measured summary: [observed-results.json](observed-results.json).
Full per-case observations are in ignored `scratch/jpl-pilot/report.json`.

## What the pilot uncovered

### Time handling needs deliberate qualification

Across the wider 1850–2149 sample, raw differences reach **32.14 arcseconds**
for planetary longitude and **0.35 degrees** for local angles. These must not
be hidden by reporting only the modern subset.

Before 1972, the pilot's bundled UTC/leap-second extrapolation differs from the
existing engine's historical time treatment. Far-future time conventions and
Earth rotation predictions also differ. A separate diagnostic feeds both engines
the same numerical TT for planets and UT1 for angles: maxima fall to **2.95
arcseconds** for positions and **2.69 arcseconds** for angles across the full
sample. This isolates the issue; it does not resolve which historical/future
civil-time policy the product should use. The actual new engine never consumes
Swiss timing outputs or uses Swiss as a fallback.

Before migration, select and document pre-1972 civil-time handling, the supported
date range, future-time uncertainty, and an update policy for leap seconds and
Earth-rotation data. Then validate against independent time/angle references.

### Vedic remains experimental

Rahu uses the published IERS mean-node formula, with Ketu opposite. The sidereal
origin uses PAC's published 1956 anchor but declares its own TT and mean-frame
realization because the public description does not settle those details.

At the PAC March 22, 2026 reference, the pilot's mean offset differs by **16.09
arcseconds** and mean Rahu by **−6.87 arcseconds**. Across modern comparison
cases, experimental sidereal positions differ by up to **17.31 arcseconds**.
For synthetic case `modern-9` (March 28, 1985), Jupiter falls in a different pada
than the current Lahiri implementation. This is a material product difference,
not just harmless numerical noise. Exact Lahiri must be resolved independently
or the product must intentionally offer a differently named convention.

### Planet centers and coverage are explicit

DE440s supplies system barycenters for Mars through Pluto. It does not supply
all physical planet centers. The observed differences are small in these tests,
but the pilot labels its targets honestly; supplemental kernels or a documented
barycenter policy are needed before promising equivalence. The accepted interval
1850–2149 describes available input coverage, not a blanket accuracy guarantee.

## Verification

The 12-test offline suite passes on macOS ARM64 with Python 3.9 and Python 3.12
in separate environments containing no Swiss Ephemeris. It covers 30 external longitudes, 45 angle-geometry
combinations, published mean-node arithmetic, date/coordinate validation, kernel
checksum rejection, explicit experimental labels, global/local separation,
the Sun's 0/360-degree crossing, a Mercury retrograde station, finite-difference
step stability, concurrent repeatability, and blocked-network operation.
It also checks that Swiss Ephemeris is absent from the test environment.

A separate read-only mathematical review checked 105 horizon/meridian cases:
maximum plane residual was 7.6e−16. It also checked that the mean-to-true node
conversion agrees with nutation in longitude. This supports implementation
consistency; it is not an independent astronomical accuracy guarantee.

This pass does not establish Linux/Vercel bundle behavior, production concurrency,
long-term time-data maintenance, exhaustive boundary correctness, or a complete
third-party distribution/license audit. Existing forms, charts, LLM synthesis,
and saved readings have not been connected to this pilot.

## Recommended next step

Proceed with this architecture if avoiding Swiss dependence is the priority.
First resolve historical time policy and exact sidereal conventions; add boundary
fixtures wherever either changes a user-visible label. Then complete the existing
app's output contract and test it on the actual deployment runtime. Keep the
new engine isolated until those checks pass. Most of the existing interface and
interpretation work can remain, but this pilot is not yet a drop-in replacement.

For original-code licensing and source provenance, see [SOURCES.md](SOURCES.md).
No Swiss code was copied or translated into this pilot; no paid Swiss license
was acquired or represented as necessary for its independent runtime.
