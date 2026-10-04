# Explicit time policy, phase two

The first pilot extrapolated Skyfield's modern UTC leap-second table backward.
That is not an adequate model for historical civil birth times. The new policy
uses independent public time data instead of fitting Swiss outputs.

| Era | Meaning after the app resolves the IANA timezone | Conversion |
| --- | --- | --- |
| Before 1961 | Approximate historical UT1 | Skyfield `ut1()` and its historical Delta T reconstruction |
| 1961–1971 | Historical UTC, including frequency drift | USNO piecewise TAI−UTC table; TT = TAI + 32.184 seconds |
| 1972 onward | UTC with leap seconds | Pinned Skyfield leap-second table; UT1 from bundled Delta T data |

The pre-1961 choice is a documented engineering approximation. It cannot recover
the accuracy of an old recorded clock or resolve missing timezone history. We do
not claim UTC existed in 1850. The existing API's ISO timestamp remains the
timezone-normalized civil label; `provenance.time_policy.input_scale` explains
how that label is interpreted physically.

Source: [USNO TAI−UTC data](https://maia.usno.navy.mil/ser7/tai-utc.dat), checked
October 4, 2026. The 13 pre-1972 records provide effective dates, base offsets,
reference MJD and linear drift coefficients. Numeric coefficients are factual
data; the table-selection and two-part Julian-day arithmetic are original code.
No Swiss, SOFA or ERFA implementation was copied.

The offline tests check selected published offsets, all 12 internal drift-table
transitions, the 1972 modern UTC transition, and the 2016/2017 leap second. Python
datetime cannot represent the inserted `23:59:60` itself; surrounding instants
correctly span two physical seconds, and forms do not accept a leap-second label.

## New external reference evidence

Two sequential NASA Horizons requests fetched 24 apparent geocentric Sun/Moon
positions at public epochs spanning 1850–2026, including the drift era and leap
transition. The largest residual was 0.576 arcseconds; drift-era Moon residuals
for 1962–1971 were under 0.05 arcseconds. Exact samples and original query data
are retained in `historical_fixture.json` and ignored
`scratch/jpl-pilot/historical-reference/` respectively. These are sample
implementation checks, not a bound on every chart's physical accuracy.

[Horizons time conventions](https://ssd.jpl.nasa.gov/horizons/manual.html#time-scales)
use UT1 before 1962 and UTC afterward. Our 1961 sample intentionally compares
different input conventions (historical UTC versus Horizons UT1); its 0.195
arcsecond Moon residual is a diagnostic, not exact same-instant validation.

## Future times and maintenance

Skyfield 1.55's bundled Earth-rotation table ends January 23, 2027. Calculations
beyond it report `earth_rotation_extrapolated: true` and a warning. This last date
includes predictions and is not a claim that all preceding entries are final
observations. Future leap seconds cannot be known; the last known offset is
continued. Different forecasting policies can therefore disagree with the Swiss
baseline on future TT/UT1, even when their mathematics is correct.

[Skyfield's time documentation](https://rhodesmill.org/skyfield/time.html#ut1-and-downloading-iers-data)
explains the need to update IERS data. Before public activation, establish a
reviewed, pinned time-data update process and alert before predictions expire;
do not download changing tables during an individual reading. Re-run historical,
boundary and saved-reading tests on an update, record its version, and preserve
original facts/provenance in already saved readings. No automatic background
updater or monitoring service is created by this pilot.
