# Independent PAC/IAE sidereal qualification

Research and checks: 4 October 2026. No production changes.

## Result

There is now an independently implementable, explicitly published **Indian
Astronomical Ephemeris ayanamsa convention adopted in 2021**. Use the identifier
`iae-2021` and name `Indian Astronomical Ephemeris (2021 convention)`.
`sidereal.py` implements that formula and its documented nutation adjustment.

This resolves the numerical implementation without reconstructing the ambiguous
1956 origin. It does **not** establish identity with every setting called Lahiri,
with the existing Oracle Swiss Lahiri implementation, or with True Chitrapaksha.
The complete extracted texts of the official 2024, 2026 and 2027 editions have no
matches for Lahiri, Chitrapaksha or Citrapaksha. An official statement equating
their current formula with that named application setting was not found. An
application that promises exact standard Lahiri must still fail closed until the
convention is explicitly selected/accepted or the missing equivalence is sourced.

The tests qualify the implementation against printed numerical references. They
do not validate astrological interpretation or prove a universal accuracy range.

## Primary sources, independently retrieved

The [official PAC download index](https://packolkata.imd.gov.in/indian-astronomical-ephemeris.php)
links these archives. The PDFs were downloaded directly from that government
host, extracted with pypdf/Poppler, and the formula and table pages visually
inspected. No Swiss source file was opened or used. Broad web search returned
unrequested Swiss snippets, which were excluded from the implementation basis;
subsequent source work used the official PAC publications.

| Official source | Formula: printed / PDF page | True table: printed / PDF page |
| --- | --- | --- |
| [IAE 2024](https://packolkata.imd.gov.in/download/IAE2024.zip) | 376 / 383 | 417 / 424 |
| [IAE 2026](https://packolkata.imd.gov.in/download/IAE2026.zip) | 378 / 384 | 419 / 425 |
| [IAE 2027](https://packolkata.imd.gov.in/download/IAE2027.zip) | 382 / 389 | 423 / 430 |

PDF pages above are one-based. Downloaded PDF hashes are recorded in
`iae_fixture.json`; they pin the checked artifacts, not an independently signed
publisher checksum. The 2027 archive's member is named
`IAE_2027_F_corrected_compressed.pdf`.

IAE 2026 printed p. 430 / PDF p. 436 specifies TT for fundamental geocentric
ephemerides. Printed pp. 441-442 / PDF pp. 447-448 describe nutation, its use in
ecliptic longitude, the IAU 2000A series and the IAU 2006 adjustment. These are
the direct mathematical sources used below. The introductory 1956 statement is
printed p. 377 / PDF p. 383, separate from the newer explicit formula.

## Published convention and implementation

Let `T = (JD_TT - 2451545.0) / 36525`. In **arcseconds**:

```text
A_mean = 23*3600 + 51*60 + 25.53
         + 5028.796195*T
         + 1.1054348*T^2
         + 0.00007964*T^3
         - 0.00023857*T^4
         - 0.0000000383*T^5

dpsi_2006 = dpsi_2000A * (1 + 0.4697e-6 - 2.7774e-6*T)
A_true = A_mean + dpsi_2006
```

The ephemerides attribute the precession polynomial to Capitaine, Wallace and
Chapront (2003), Astronomy & Astrophysics 412, 567-586, and say it was introduced
for their ayanamsa from 2021. The table footnotes independently identify the
J2000 mean constant and the mean-plus-nutation relationship. These are published
constants and equations, not a fit to chart output.

`mean_ayanamsa(tt_jd)` and `true_ayanamsa(t)` return degrees.
`nutation_longitude_degrees(t)` evaluates Skyfield's independent IAU 2000A series
and applies the adjustment above. Inputs are scalar TT Julian date or scalar
Skyfield Time respectively. These functions require no kernel or network call.
The mean-node convention remains separately identified as IERS equation 5.43.
Rotating that node to the true equinox does not turn it into an apparent body.

To combine apparent tropical longitudes with this convention, subtract the
true ayanamsa. With a mean-equinox node, subtract the mean ayanamsa directly, or
add the same nutation to both the node and offset before subtracting. Do not mix
mean and true offsets. A fully consistent frame realization matters at precision
far beyond the printed 0.1-arcsecond tables; the Skyfield frame and the IAE's
adjusted nutation must not be assumed bitwise identical.

## Published table checks

Table headings give true ayanamsa for `5h 29m` without repeating a time-zone label.
The calculation uses 00:00 TT, consistent with the publication's ephemeris time
argument and the rounded IST equivalent. The tests additionally evaluate literal
05:29 IST (23:59 UTC on the preceding civil date); its modern difference of
9.184 seconds from midnight TT does not change agreement at table precision.
No historical UTC realization is needed for these TT reference checks.

Each table has four columns on a three-day grid and repeats the endpoint between
adjacent columns. The fixture deduplicates those endpoints. Dates were assigned
from January 1 at successive three-day intervals, as described by the source;
this also resolves obvious printed month-label defects in the 2024 table such
as `Sept. 31`. Such label defects are not silently treated as valid calendar
dates. The numeric cells were extracted unchanged.

| Edition | Primary-year rows | Additional accepted continuation rows | Max absolute residual | RMS residual |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 122 | 39 (2025) | 0.051885 arcsec | 0.028940 arcsec |
| 2026 | 122 | 14 (2027) | 0.051588 arcsec | 0.029430 arcsec |
| 2027 | 122 | 39 (2028) | 0.051889 arcsec | 0.027891 arcsec |

The fixture retains **458 accepted references**, including all **244** requested
primary-year 2024/2026 entries, and another 122 primary-year 2027 entries. The
test threshold is 0.06 arcsecond, allowing the published 0.1-arcsecond rounding
plus the observed few-milliarcsecond differences. This threshold is a table
agreement criterion, not a claimed global error bound.

Selected residuals (computed minus published, at 00:00 TT):

| Date | Published true ayanamsa | Residual |
| --- | --- | ---: |
| 2024-01-01 | 24 deg 11 min 27.1 sec | -0.023179 arcsec |
| 2024-04-30 | 24 deg 11 min 43.7 sec | +0.012030 arcsec |
| 2024-08-28 | 24 deg 12 min 04.0 sec | -0.018148 arcsec |
| 2024-12-26 | 24 deg 12 min 21.4 sec | +0.025759 arcsec |
| 2026-01-01 | 24 deg 13 min 18.5 sec | +0.012288 arcsec |
| 2026-05-01 | 24 deg 13 min 35.2 sec | -0.019946 arcsec |
| 2026-08-29 | 24 deg 13 min 55.6 sec | -0.007743 arcsec |
| 2026-12-27 | 24 deg 14 min 13.4 sec | -0.037548 arcsec |

### Source inconsistency retained, not fitted away

The 2026 edition's continuation column from 2027-02-13 through 2027-04-26
contains **25 entries** differing from its own formula by +4.320961 to
+5.415665 arcseconds. They are preserved in `excluded_diagnostics`, with dates,
values and reason. For example, that table gives 24 deg 14 min 16.4 sec for
2027-02-13, while the formula gives 24 deg 14 min 21.028539 sec.

The separately downloaded 2027 primary-year table supports the formula across
all its entries, including the same season: February 12 and 15 give 20.9 and
21.4 arcseconds respectively after 24 deg 14 min. This strongly indicates a
publication/table inconsistency in the older continuation, but no official
erratum explaining its cause was obtained. Excluding it is a documented source
decision; it is not a widened tolerance or calibration of constants.

## Why changing the 1956 anchor alone is insufficient

The official narrative gives 23 deg 15 min at 0h on 1956-03-21 but does not
fully specify its historical time/frame realization. We tested two natural
interpretations without adjusting the angle: 23.25 degrees at 00:00 TT in the
mean frame, and 23.25 degrees in the true frame. Both propagate a fixed inertial
direction using Skyfield, exactly as the pilot's original experiment did.

Against the eight selected 2024/2026 true-table entries above:

- The original mean-anchor candidate differs by approximately +15.94 to
  +16.01 arcseconds.
- The true-anchor candidate differs by approximately -0.83 to -0.77 arcsecond.

The improvement supports investigating the true-frame interpretation, but does
not justify promoting it to the modern standard. At the 1956 epoch, extrapolating
the independently published post-2021 formula gives mean 23.24556033145643 deg
and true approximately 23.25022086077866 deg. Thus even that documented modern
polynomial does not force the historical true anchor to exactly 23.25 deg.
Use the published current formula; do not hide its difference with an invented
1956 correction or a correction fitted to Swiss outputs.

## Separate unresolved mean-node discrepancy

The [PAC mean-position table](https://packolkata.imd.gov.in/panchang/en/bija_corrections)
gives mean Rahu 313.70703055555555 deg at 2026-03-22 05:30 IST and rounded
mean ayanamsa 24 deg 13 min 24 sec. IERS mean node minus the new IAE mean
ayanamsa at that instant gives 313.7095628100936 deg: **+9.116116 arcseconds**.
This is retained as `mean_node_diagnostic`; no node constant was adjusted.
Qualification of ayanamsa does not qualify that distinct lunar-node convention.

## Reproduction, limits and handoff

Run from the repository root:

```sh
PYTHONPATH=experiments/jpl_pilot scratch/jpl312-venv/bin/python -m unittest experiments/jpl_pilot/test_sidereal.py -v
```

Five tests pass: the independent J2000 constant, all accepted table references,
the rounded IST time interpretation, preservation of rejected diagnostics, and
nonfinite input handling. Tests make no network calls and need no JPL kernel.

Validation is limited to the fixture dates: primary years 2024, 2026, 2027,
plus accepted continuation samples in 2025 and 2028. No primary reference
qualification for 1850-2023, the gaps between these samples, or 2029-2149 is
claimed. The formula can be evaluated there, but kernel coverage and algebraic
evaluation are not evidence of calendar convention or accuracy. The documented
2021 adoption date describes the publication's method change, not a promise
about valid birth years.

Changed only `sidereal.py`, `test_sidereal.py`, `iae_fixture.json` and this file.
The parent owns integration and any application naming decision. Exact standard
Lahiri equivalence and PAC mean-node equivalence remain bounded, explicit open
questions; no production switch or deployment is authorized by this research.
