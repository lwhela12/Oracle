# JPL phase two: working local birth charts and horoscopes

Historical local-integration checkpoint. The subsequent production packaging
and launch are documented in [JPL Ephemeris Release](../../docs/JPL_EPHEMERIS_RELEASE.md).

October 4, 2026. The independent engine now drives the existing app locally,
including Western and Vedic birth charts, daily horoscopes, interactive planet
descriptions and streamed Gemini interpretations. The runtime environment has
no Swiss Ephemeris installed. The default backend and deployed feature flag
remain unchanged; this work has not been committed, pushed or deployed.

## Changes and evidence

- Historical time is explicit: pre-1961 civil labels approximate UT1;
  1961–1971 uses USNO's published TAI–UTC drift segments; modern dates use
  Skyfield's pinned leap-second data. See [TIME_POLICY.md](TIME_POLICY.md).
- Vedic charts use the published **Indian Astronomical Ephemeris (2021
  convention)**, named `iae-2021` in facts, forms, prompts and exports.
  It is not silently labeled Lahiri. The old 1956-anchor method is retained
  only as a diagnostic CLI option.
- The official ayanamsa formula agrees with **458 accepted table entries**
  from the 2024/2026/2027 editions, including continuation dates, to a maximum
  residual of **0.05189 arcseconds**. Twenty-five inconsistent continuation
  cells remain explicitly documented and excluded; see
  [LAHIRI_RESEARCH.md](LAHIRI_RESEARCH.md).
- The adapter lazily loads and verifies one kernel per configured path,
  retains the existing chart contract, and keeps the stdlib timezone resolver
  independent of either native calculation backend. There is no Swiss fallback.

## Numerical results

These are measured differences on finite samples, not universal accuracy bounds.
Swiss is a black-box comparison in a separate environment; no output fitting
or Swiss implementation copying is used.

| Check | Result |
| --- | --- |
| Original 30 NASA Horizons longitudes | Maximum residual 0.09533 arcseconds |
| New 24 Sun/Moon Horizons references, 1850–2026 | Maximum residual 0.57571 arcseconds; 1961 has a declared time-convention difference |
| 56 modern nonpolar Swiss comparisons, 1972–2026 | Maximum Western longitude difference 1.37114 arcseconds; Vedic 1.37313 arcseconds |
| Modern Ascendant / MC | Maximum raw difference 6.58604 / 4.54624 arcseconds; with identical UT1, at most 0.00231 arcseconds |
| 12 pre-1972 Swiss comparisons | Maximum Western longitude difference 1.76903 arcseconds; angle difference 0.00124 arcseconds |
| All 86 comparisons | Zero Western sign, Whole Sign house, retrograde or aspect-membership differences; zero Vedic nakshatra/pada differences |
| Full 1850–2149 sample | Maximum raw longitude difference 32.1374 arcseconds and angle difference 0.34915 degrees; future time-model divergence remains |
| Warm Western chart calculation | About 17 ms median in the latest local run, excluding startup and LLM generation |

The previous pilot's one Vedic pada mismatch is absent with the published IAE
formula. Exact boundaries can still differ between engines. Matching sample
categories does not establish bitwise Lahiri compatibility. The separate IERS
mean-node convention still differs from the PAC mean Rahu reference by 9.11612
arcseconds; the node coefficients have not been fitted to remove this residual.

Machine-readable comparison summary: [observed-phase2.json](observed-phase2.json).
Full synthetic per-case data: `scratch/jpl-pilot/phase2-report.json` (ignored).

## Verification

Tests run on macOS ARM64, Python 3.12.11:

| Suite | Outcome |
| --- | --- |
| Independent engine/time/sidereal tests | 24 run, all passed |
| App discovery in Swiss-free JPL environment | 185 run, OK, 33 optional/Swiss-specific skips |
| Existing Swiss environment regression | 191 run, OK, 17 optional/JPL-specific skips |
| JavaScript syntax and both interpretation-library suites | Passed |

The JPL tests cover both chart/horoscope traditions, prompt privacy, streamed
response shape, DST folds, shared kernel initialization, missing-kernel errors
and subprocess proof that neither `swisseph` nor `astrology.engine` is imported.
Core checks cover published positions, drift-table boundaries, leap seconds,
angle geometry, station/sign boundaries, blocked-network operation and checksums.

Actual browser verification uses the new local origin
`http://127.0.0.1:8886/astrology/`, preserving the existing 8884 preview. Synthetic
inputs only: March 20, 1990, 15:30 in Los Angeles for natal and Vedic tests;
March 15, 1990 without time/place for the Western birthday-only horoscope.
Completed Western and Vedic birth-chart interpretations and both daily
horoscopes were verified through the real Gemini stream. Vedic chart nodes,
nakshatra/pada descriptions and IAE 2021 calculation labels rendered correctly.
All four synthetic readings were saved locally; the Vedic birth chart reopened
with its interpretation and the explicit “without recalculation” status. Its
downloaded text identified JPL DE440s and IAE 2021 and omitted the raw test birth
date and city. The browser download-event helper timed out, but the actual
newly downloaded file was found and inspected. No browser errors/warnings were
reported. Screenshot: `scratch/jpl-pilot/vedic-birth-chart.jpg` (ignored).

This pass did not reverify PDF/image exports, phone layout, social posting or
existing saved-chart migration across browser origins. Stored Swiss charts keep
their original convention; no stored record was recalculated or migrated.

## What remains before public activation

1. Move the qualified runtime out of the experimental directory and package the
   pinned kernel for the actual deployment platform. `.vercelignore` currently
   excludes both `experiments/` and `scratch/`; this local opt-in cannot simply
   be enabled on that production bundle. Test Linux startup, bundle size and load.
2. Establish a reviewed, pinned time-data refresh process. The current bundled
   Earth-rotation table ends January 23, 2027 and includes predictions; future
   UT1/leap seconds remain uncertain even before/after a routine refresh.
3. Finalize supported date/precision promises and the declared use of system
   barycenters for Mars–Pluto. Supplementary kernels are needed if exact physical
   planet centers become a requirement. Expand boundary/reference qualification
   for the chosen release range and mean-node convention.
4. Confirm the product's intentionally named Vedic convention. An official
   equivalence statement for every setting named Lahiri was not found.
5. Choose the license for our original engine code and assemble the actual
   third-party notices/data terms. [SOURCES.md](SOURCES.md) is the source record,
   not a completed distribution compliance review.

No account, payment, public release, or open-source publication was made here.
