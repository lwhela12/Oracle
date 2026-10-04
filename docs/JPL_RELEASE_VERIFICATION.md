# JPL release verification — October 4, 2026

## Local and independent checks

- JPL environment: Python 3.12.11, macOS ARM64, no installed Swiss binding.
  Full application discovery: 196 tests run, OK, 33 optional/Swiss-specific skips.
- Independent numerical/time/sidereal suite: 24 tests, all passed.
- Release/JPL contracts/time-policy checks: 20 tests, all passed.
- Explicit Swiss compatibility environment: 202 tests run, OK, 25 optional/JPL
  skips after correcting the new tests' optional dependency guards.
- JavaScript syntax, Western/Vedic interpretation libraries, share-card renderer,
  analytics and saved-journal identity checks passed. `pip check` is clean.
- Kernel hash equals the pinned official unmodified DE440s file. Production
  import tests block `experiments`, `swisseph`, and `astrology.engine` and still
  complete calculations. Missing/incorrect kernels produce sanitized 503 errors.
- Numerical comparisons retained zero sampled sign/house/retrograde/aspect/
  nakshatra-pada differences; see the phase-two evidence and its finite-sample
  qualifications. There is no fitting to the Swiss output.
- Historical horoscope tests confirm retention of the pre-1961 natal UT1
  qualification without exposing raw birth inputs in the retained provenance
  or interpretation facts.

## Production-platform candidate

Candidate deployment: `dpl_25m5gkXUvGhSCnDhkDbr9eysshkD`,
`oracle-lbl45v5en-lwhela12s-projects.vercel.app`.
Created with the production target and `--skip-domain`, enabling JPL astrology
only on this candidate. It was uploaded from the working tree; its inherited
Git metadata still points to the previous commit and must not be mistaken for
the eventual committed release identity.

Vercel built with Python 3.12 and installed the runtime requirements. The build
reported a 373.46 MB pre-optimization bundle and completed dependency optimization
successfully. Actual `/astrology/health` returned HTTP 200 and:

- `Quantum Oracle Ephemeris`, `library_version` / `engine_version` = `1.0.0`.
- `JPL DE440s`, pinned kernel SHA-256
  `c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2`.
- Time status `healthy`, 111 days remaining, table endpoint 2027-01-23.
- Time-data SHA-256
  `c7d7536d898dfa9f8cd43e8044ff51e108cc8289675a13fee9822010a1c4935c`.
- `Cache-Control: no-store`.

The health probe actually loads/verifies the kernel and calculates a current
global sky. Build success alone was not treated as proof of runtime operation.

Prior production rollback baseline: `dpl_5d51zJsvahAwnYX1NnN8iwf1CwAi`,
`oracle-glw9xhrd7-lwhela12s-projects.vercel.app`, commit
`63bd563080f7ccdb9f601e2bcaaf7256a3cbdde6`. Its astrology feature is disabled.

## Public release checks

The user authorized temporary candidate browser access. The candidate completed
Western and Vedic birth charts, including generated interpretations, saved
readings and a sharing preview. The UI identifies JPL DE440s and IAE 2021.

Commit `10f8dd2` passed GitHub's Ubuntu/Python 3.12 release workflow (11 tests)
and was deployed as `dpl_G415hTTVXMhiBsdh7thhEZ15wRCn`, then promoted to
`https://www.qoracle.app`. Production now explicitly configures
`ORACLE_ASTROLOGY_ENABLED=1` and `ORACLE_ASTROLOGY_BACKEND=jpl`.

On the public domain, the homepage exposes Astrology. A birthday-only Western
horoscope, Vedic birth chart and Vedic Moon-sign horoscope completed with real
generated interpretations. Synthetic inputs were used throughout. A Vedic PDF
download completed. The planet detail view works at a 390 x 844 viewport, with
document width and scroll width both 390 pixels. Saved reading controls and the
existing Tarot entry were also checked. No browser errors were observed; the
deployment's error/fatal runtime-log query returned no entries during the test.

Export review found one remaining hardcoded Lahiri label in chart images; the
follow-up correction uses the chart's actual ayanamsa convention for both image
and embedded PDF graphics. Final deployment identity and screenshots are recorded
in the release conversation and `scratch/jpl-release/`.
