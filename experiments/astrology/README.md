# Isolated astrology / synchronistic reading experiment

This CLI experiment is not imported by Flask. Its calculator now delegates to the shared
`astrology/engine.py`; the app has a separate default-off calculation endpoint documented
in `docs/SWISS_EPHEMERIS_INTEGRATION.md`. Deployment remains unchanged. Run locally only. Outputs,
credentials, and its virtual environment stay under the already ignored `scratch/` directory.

## Current result — 2026-10-04

- Three complete samples: public city-center coordinates for Los Angeles, London, and
  Tokyo, each using the same UTC moment and an invented question. No birth information.
- Actual Tarot (3 cards without replacement), Norns runes (3 unique runes plus reversal
  bits), three-coin I Ching (18 bits), and uniform 0–100 number draws. All 12 provider
  requests succeeded through LFDR, HTTP 200, zero fallback values. Provenance is in the bundle.
- Numerology adds explicit repeated decimal digit sums to the drawn number; it does not
  claim a birth-derived life path. Master numbers are not preserved; zero remains zero.
- Local calculations use Swiss Ephemeris 2.10.03 through `pysweph==2.10.3.6`, explicitly
  using the bundled **Moshier analytical ephemeris**, not downloaded Swiss/JPL files.
- Tropical apparent geocentric positions, longitude speeds and retrogrades, Whole Sign
  houses, Ascendant/MC, fixed-orb major aspects, eight-sector lunar phase. All conventions
  and engine flags are recorded. Phase sectors are not claims of an exact phase event.
- **28 focused tests pass.** Separately, a live NASA JPL Horizons comparison checked all
  ten planets at three reference epochs: 2000-01-01, 2024-04-15 (Mercury retrograde),
  and 2026-10-04, each at noon UTC. All 30 matched within the exploratory 0.01-degree
  threshold; largest observed difference was **0.487523 arcseconds**. This is a sample
  comparison of planetary longitudes, not certification of every date, houses, or astrology.
- Preview prose was authored by a Codex worker (`gpt-5.6-sol`) and reviewed/edited by
  the parent assistant against the saved evidence. **It is not a Gemini API response.**
- **Live AstroAPI.cloud comparison passed for all three cities.** All ten longitudes,
  speed signs/retrograde flags, Ascendant/MC, and twelve Whole Sign cusps were present
  and met the 0.01-degree threshold. Maximum planetary deviation: 0.455418 arcseconds;
  maximum angle deviation: 13.202439 arcseconds; all 36 house cusps matched exactly.
- Live validation revealed that `dateTime` rejects seconds and requires `YYYY-MM-DDTHH:mm`.
  Both comparison engines therefore use 2026-10-04T17:17:00Z. The original readings at
  17:17:36Z and their random draws remain unchanged. This checks three locations at one
  instant, not arbitrary dates or every house system.
- Approved calculation-only key is saved in ignored `scratch/astrology.env` with mode
  0600; dashboard expiry is October 11, 2026. Trial response headers report 200 total,
  192 remaining: five HTTP 400 attempts (including diagnosis), then three HTTP 200 calls.
  Successful calls took approximately 111–333 ms in this sample. No subscription purchased.
- Live Gemini generation is implemented but **not tested with credentials**. No local
  key was configured; an existing Vercel metadata request returned HTTP 403. Nothing
  was changed in Vercel and no credentials were exported.

## Reproduce

From the repository root:

```sh
.venv/bin/python -m venv scratch/astrology-venv
scratch/astrology-venv/bin/python -m pip install -r experiments/astrology/requirements.txt
scratch/astrology-venv/bin/python -m unittest discover -s experiments/astrology -p 'test_*.py' -v
scratch/astrology-venv/bin/python experiments/astrology/run.py --output scratch/astrology-new
```

The last command makes real randomness-provider requests and records fallback honestly.
For an offline run use `--randomness system`; it labels that source as system randomness.
Each new output directory captures one timestamp and three independent casts. Existing
output is never silently overwritten. `--resume` reuses the saved timestamp, calculations,
and casts, rather than drawing again. The report is static HTML; opening it makes no
network requests and never generates readings.

For public NASA reference validation (10 sequential requests; cached responses reused):

```sh
scratch/astrology-venv/bin/python experiments/astrology/check_reference.py
```

## Credentials and further checks

The existing `scratch/astrology.env` already contains the approved AstroAPI key; do not
overwrite it. For a fresh checkout, copy `.env.example` to that path, restrict permissions
to the owner, and enter credentials locally. Never commit it or paste keys into chat.
For AstroAPI.cloud use the narrow calculation permission `calc:use` and the natal
calculation module `natal:calc`; no interpretation text or chart-rendering module is needed.
This trial/module combination has been verified by successful live calculation calls.

```sh
scratch/astrology-venv/bin/python experiments/astrology/run.py --resume --compare-hosted
scratch/astrology-venv/bin/python experiments/astrology/run.py --resume --generate
```

The comparison command makes one call per untested saved sample, using a whole UTC minute,
`houseSystem: whole`, `moonCenter: geocentric`, and `includeText: false`. It has bounded
timeouts, no redirects or automatic retry, and records only real returned usage headers.
It explicitly recalculates a separate local comparison chart at that same minute; it never
silently rounds a hosted request or rewrites the original reading. It compares all ten
longitudes, speed signs/retrograde flags, both local angles, and all
twelve cusps. Missing fields fail closed. Raw response and calculation settings remain
inspectable; a completed HTTP request is not a passed comparison. Vendor aspect orbs are
not compared; the prototype deliberately owns its explicit aspect policy.

The generation command uses one fresh Gemini call per saved sample. It replaces a Codex
preview but skips an already completed Gemini result. The entire five-system record goes
into a single prompt. JSON shape, evidence references, and five-system coverage are checked;
these checks cannot prove the prose is factually grounded. Inspect the result manually.
Failures retain their status and return a nonzero exit; no production fallback is used.
Completed hosted calls are not repeated by `--resume`. To investigate a failed hosted call,
first inspect its safe error type and provider dashboard; there is no automatic retry loop.

## Review files

- `scratch/astrology-prototype/index.html`: three readings with expandable evidence.
- `scratch/astrology-prototype/bundle.json`: original inputs, casts, provider receipts,
  chart facts, generation origin, and reference results.
- `scratch/astrology-prototype/*-prompt.txt`: exact synthesis prompts.
- `scratch/astrology-prototype/reference/report.json`: numeric comparison and scope.
- `scratch/astrology-prototype/reference/horizons-*.json`: original reference responses.

## Decisions still open

The private prototype does not establish permission to publish Swiss Ephemeris-dependent
code under the repository's existing terms. Before distribution/public service, choose the
applicable Swiss Ephemeris license and check the Python binding's terms.

Provider clarification to resolve before relying on a hosted service for production:
“For our app, may we retain raw calculation results alongside saved user readings and pass
those results to our own LLM solely for interpretation, without reselling API access? What
quota and modules apply to the trial and calculation-only plan?” No message has been sent.

Birth charts, personal transits, geocoding, a user-facing input form, account/profile
storage, paid usage limits, and integration with the production journal are out of scope.

## Sources

- https://www.astro.com/swisseph/swephprg.htm
- https://www.astro.com/swisseph/swephprice_e.htm
- https://github.com/sailorfe/pysweph
- https://docs.astroapi.cloud/guide/natal-charts
- https://docs.astroapi.cloud/api/operations/postApiCalcNatal
- https://docs.astroapi.cloud/guide/rate-limits
- https://ssd-api.jpl.nasa.gov/doc/horizons.html
- https://ssd.jpl.nasa.gov/horizons/manual.html (observer quantity 31)
- https://aa.usno.navy.mil/faq/sun_approx
