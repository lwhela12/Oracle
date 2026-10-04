# Independent ephemeris release

Release candidate: 2026-10-04. Production engine: `astrology/jpl/` version 1.0.0.
The public features are Western/Vedic birth charts and daily horoscopes, using
the existing measured-facts → Gemini interpretation flow. A birth chart uses
date, local time and city. Western horoscope can use birthday alone; Vedic
horoscope requires all three inputs to derive the natal Moon sign and nakshatra.

## Calculation and product contract

- JPL DE440s, apparent geocentric true ecliptic/equinox of date, evaluated by
  pinned Skyfield 1.55 and jplephem 2.24. Original chart geometry and assembly.
- Western tropical zodiac; Whole Sign houses for birth charts; explicit product
  aspect angles/orbs. Planetary positions are not inferred by the language model.
- Vedic uses **Indian Astronomical Ephemeris (2021 convention)** (`iae-2021`),
  seven physical grahas plus IERS mean Rahu and opposite Ketu, nakshatras/padas,
  Whole Sign houses and sign-based Parashari drishti. No exact identity with all
  settings called Lahiri is promised. The older experimental anchor is not
  selectable by the application.
- Inputs cover 1850-01-01 through 2149-12-31 UTC. Historical civil times before
  1961 use a disclosed UT1 approximation; 1961–1971 uses USNO UTC drift data;
  modern UTC uses pinned leap seconds. Future rotation/leap seconds are uncertain.
- Mars through Pluto use the DE440s system barycenters. These are not labeled
  physical planet centers. Ascendant/MC use geodetic city-center coordinates
  without polar motion or refraction. Polar geometry carries a qualification.
- Finite-sample validation supports this symbolic chart product; no universal
  sub-arcsecond, surveying, navigation, or exact Swiss-compatibility claim.
- The LLM receives whitelisted derived chart facts, not raw birth details.
  Near-station uncertainty survives that projection. Historical natal time
  qualifications also survive a derived daily horoscope.
- Saved readings preserve their original facts and engine/convention. Opening
  a saved record does not recalculate it or rewrite a prior Swiss chart.

## Runtime and deployment

Install `requirements.txt` with Python 3.12. The default backend is `jpl`.
Set `ORACLE_ASTROLOGY_ENABLED=1` to expose the feature. The explicit
`ORACLE_ASTROLOGY_BACKEND=jpl` production setting documents that choice.
`ORACLE_JPL_KERNEL_PATH` is an optional local override; leave it unset in Vercel.

The unmodified 32 MB kernel is versioned under `astrology/jpl/data/de440s.bsp`.
SHA-256 `c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2`
is verified on initial load, once per process/path. There is no network fetch or
Swiss fallback. `.vercelignore` excludes experiments, scratch environments,
tests, the optional Swiss engine and its requirements file. The base dependency
graph contains no Swiss binding. Do not add `requirements-astrology.txt` to a
public deployment; it is only the separately licensed local comparison option.

Use a production-target Vercel deployment with `--skip-domain`, verify it, then
promote the verified deployment. This keeps production environment settings
(including scoped analytics/admin settings) intact while testing the candidate.
Record the prior deployment ID/URL before promotion for a rollback.

`GET /astrology/health` verifies actual kernel loading and returns only engine
and time-data metadata. It returns 404 when disabled, 503 for unavailable engine
or an expired Earth-rotation table, and 200 for healthy/refresh-due status.
Chart warnings remain visible in calculation details and in saved facts.

## Time-data maintenance

Run `python scripts/check_ephemeris_release.py` before each release. It verifies
the bundled kernel, records a hash of Skyfield's `iers.npz`, and fails if the
table has expired or has 45 or fewer days remaining. The initial table ends
2027-01-23 and includes predictions, not only finalized observations.

`.github/workflows/ephemeris-health.yml` runs this check on main pushes, pull
requests, manual dispatch and weekly on Monday. GitHub Actions failure status
is the maintenance signal; repository notification settings control delivery.
No personal birth details, API key or database credential are used by this job.

When the check flags a refresh:

1. Review the current official IERS/USNO data and Skyfield release/data notes.
   Prefer an updated pinned Skyfield distribution; never fetch changing time
   tables on a request. Verify the new table end date and published leap seconds.
2. Update the pin and third-party notices if necessary. Record the new data hash
   from the release check. Re-run historical UTC/drift/leap-second and chart
   reference tests, then compare before/after results on synthetic boundary cases.
3. Build and verify a new production candidate, then promote it. Existing saved
   readings keep their original provenance; only new calculations use new data.

If upstream data is not ready, the health check must stay visibly degraded;
do not manufacture a later expiry or silently remove the threshold. Current
sky results past the bundled table are explicitly extrapolated and must not be
marketed as finalized Earth-rotation measurements.

## Sources, license scope and validation

Original engine code is reserved to its rights holder under
`astrology/jpl/LICENSE`. This launch does not publish an open-source license for
the app. Third-party dependencies/data retain their own terms and notices in
`static/astrology/THIRD_PARTY_NOTICES.txt`, linked from the user-facing footer.
NASA/JPL allows unmodified NAIF kernel redistribution under its published rules:
https://naif.jpl.nasa.gov/naif/rules.html . No endorsement is implied.

The pilot source record and finite reference evidence remain under
`experiments/jpl_pilot/`: PHASE2.md, TIME_POLICY.md, LAHIRI_RESEARCH.md and the
numeric fixtures. They are excluded from deployment. Reference comparison is
a separate process; it is not part of production calculation or an output fit.

Release-specific test/deployment evidence is recorded in
`docs/JPL_RELEASE_VERIFICATION.md` after validation.
