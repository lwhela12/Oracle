# Independent JPL astrology pilot

**The qualified implementation has moved to `astrology/jpl/`.** Current production
packaging and maintenance are documented in
[JPL Ephemeris Release](../../docs/JPL_EPHEMERIS_RELEASE.md). The historical setup
and measurements below remain for reproducing the pilot; its three calculation
modules now forward to the independently authored production package.

This tests whether Quantum Oracle can replace its Swiss calculation dependency
with independently authored code plus JPL data and permissively licensed tools.
The app now has an opt-in local adapter. The default backend, production
dependencies and deployed feature flag remain unchanged.

Read [PHASE2.md](PHASE2.md) for current results, [RESULTS.md](RESULTS.md) for the
original pilot measurements, and
[SOURCES.md](SOURCES.md) for independent sources, conventions and licensing scope.
This is a new limited chart engine, not a complete reimplementation of Swiss
Ephemeris and not a production-ready replacement.

## Run

From the repository root, create an isolated Python environment (tested here with
Python 3.9 and 3.12 on macOS ARM64):

```sh
python3 -m venv scratch/jpl-venv
scratch/jpl-venv/bin/python -m pip install -r experiments/jpl_pilot/requirements.txt
scratch/jpl-venv/bin/python experiments/jpl_pilot/fetch_kernel.py
scratch/jpl-venv/bin/python experiments/jpl_pilot/run.py \
  --utc 2000-01-01T12:00:00Z --latitude 35 --longitude -110
scratch/jpl-venv/bin/python -m unittest discover -s experiments/jpl_pilot -p 'test_*.py'
```

Omit coordinates for global positions. Input must have an explicit UTC offset.
Raw local birth-time parsing, place lookup, and DST resolution remain in the
existing app and are not imported into this pilot. Western output includes
positions, speeds, signs, aspects, Ascendant, MC and Whole Sign houses.

`--tradition vedic` uses the explicitly named **Indian Astronomical Ephemeris
(2021 convention)**, with mean nodes, nakshatras/padas and graha drishti.
See [LAHIRI_RESEARCH.md](LAHIRI_RESEARCH.md) for published-source qualification
and why this is not labeled exact Lahiri. `--tradition sidereal-experimental`
retains the original 1956-anchor experiment for diagnostics only; the app cannot
select it. [TIME_POLICY.md](TIME_POLICY.md) defines historical/future time handling.

## Run the app locally without Swiss

Use Python 3.12 for the app (the standalone initial pilot also ran on Python 3.9):

```sh
python3.12 -m venv scratch/jpl312-venv
scratch/jpl312-venv/bin/python -m pip install -r requirements-astrology-jpl.txt
scratch/jpl312-venv/bin/python experiments/jpl_pilot/fetch_kernel.py
ORACLE_ASTROLOGY_ENABLED=1 ORACLE_ASTROLOGY_BACKEND=jpl \
  ORACLE_ANALYTICS_ENABLED=0 PYTHONDONTWRITEBYTECODE=1 \
  scratch/jpl312-venv/bin/python -m flask --app app run \
  --host 127.0.0.1 --port 8886
```

Open `http://127.0.0.1:8886/astrology/`. Existing `.env` Gemini configuration
enables interpretation; calculations themselves are offline. An optional
`ORACLE_JPL_KERNEL_PATH` overrides the kernel path, not its required hash.
The adapter supports Western/Vedic birth charts and horoscopes, shared input/DST
validation, prompts, exports and local saved readings. It does not convert old
saved Swiss charts or relabel their original convention.

```sh
PYTHONPATH=tests:. PYTHONDONTWRITEBYTECODE=1 \
  scratch/jpl312-venv/bin/python -m unittest discover -s tests
```

This is intentionally local-only: `.vercelignore` excludes `experiments/` and
`scratch/`. Production packaging, pinned time-data maintenance and final release
qualification remain separate work. Do not set the JPL backend on a deployment
whose bundle lacks the engine/kernel.

## Reproduce the Swiss comparison

These are two separate processes/environments. The independent engine never
imports Swiss Ephemeris. Reference exports use synthetic inputs, not birth records.

```sh
PYTHONDONTWRITEBYTECODE=1 scratch/astrology-venv/bin/python \
  experiments/jpl_pilot/export_baseline.py scratch/jpl-pilot/baseline.json
PYTHONDONTWRITEBYTECODE=1 scratch/jpl-venv/bin/python \
  experiments/jpl_pilot/compare.py
```

The first command requires the existing optional Swiss environment. The second
needs only its exported JSON. Full observations are written to
`scratch/jpl-pilot/report.json`; no fitting or calibration is performed.
The unit suite needs no Swiss installation and uses the bundled public Horizons
numeric fixture. After the initial package/kernel setup, calculation and testing
are offline. The test suite checks that `swisseph` cannot even be imported.

The 32 MB kernel and virtualenv are ignored and excluded from deployment uploads.
No source license for our original pilot code has been chosen or published yet.
