# Swiss Ephemeris integration plan

Status: local astrology experience implemented, October 4, 2026. Birth charts and global/local
Sky Now use the shared engine, a celestial particle reveal, and one streamed Gemini
interpretation. The feature remains disabled by default. A genuine Gemini global Sky Now reading completed locally on October 4, 2026 after
loading the Git-ignored local key. This is one integration check, not a broad quality evaluation. Combined readings remain later work.
Public launch requires a resolved license; an ordinary
public preview is also a public service, so pre-license testing stays local/private.

## First release

Add Astrology alongside the four existing reading choices, without an account requirement.
Two entry choices: **Birth chart** and **Horoscope**. Personal transits and Sky Now are no longer offered as new readings in the UI; their engine/API support and existing saved readings remain compatible. Each shows calculated placements and
then one streamed interpretation, with the current heart/full-depth reading experience.

- Birth chart: date, local birth time, and selected birthplace; no question field.
- Both forms show birth date, local time and birthplace. Birth charts require all three.
- Western horoscope: date required; time and birthplace optional, with an optional known-sign override. Complete birth details calculate the natal Sun sign; incomplete details use the stated calendar-range estimate. The result remains a general daily Sun-sign reading. Neither entry mode asks a reflection question.
- Vedic is available for both entry choices and requires all three birth details. It uses Lahiri sidereal positions, nine grahas, Whole Sign bhavas, nakshatras/padas, and directional full graha drishti. The horoscope is a general daily natal-Moon-sign reading, not a personal transit reading.
- The underlying current-sky calculation still supplies today’s positions for horoscopes.
- Sky now: server captures one UTC instant; city optional. Without a city, show global
  planets/aspects/lunar phase only. With a city, also calculate local angles/houses.
- Western uses the tropical zodiac, apparent geocentric planets, Whole Sign houses, Sun through Pluto,
  explicit aspect orbs, and retrograde motion are fixed conventions for v1.
- Describe Sky now as a chart of the moment, never as a natal chart or a personal transit.
- Unknown birth time requires a genuine partial-chart mode. Do not invent noon and display
  precise houses. Defer that mode initially and explain that accurate time is needed for
  this full-chart version. Later, calculate a daily range and omit uncertain features.
- Combined readings, daily forecast subscriptions, alternate
  house systems, dashas, divisional charts, and account-based birth profiles are later work.

Astrology calculations use no randomness. The quantum-provider pipeline continues to
serve the existing divination modes and, later, the drawn components of combined readings.

## Personal transits and daily horoscopes

The entry card now offers Birth chart and Horoscope only. The earlier transit entry
and post-birth-chart **Read my transits** action have been removed. The following
transit contracts describe retained backend and saved-reading compatibility. No account or payment is required.
Account-backed profiles and paid access remain future work; nothing syncs to a server.

Transit requests contain `chart_kind: transit`, a `natal_request` using the existing
natal contract, and optional `instant_utc` for replay. The server recalculates both
charts. The response retains current global planets and current `major_aspects`, adds
`natal_chart`, and records separate `transit_aspects` with `transit_body`, `natal_body`,
`aspect`, `angle` (actual separation), and `orb`. Cross-chart orbs are 3 degrees for
conjunction/opposition/square and 2 for trine/sextile. Current planets' `natal_house`
refers to natal Whole Sign houses, never houses at an invented current location.
The display uses glowing current symbols and small outer natal markers. Selecting a
current planet shows natal house context and expandable cross-chart aspects.

Western daily horoscope requests contain `chart_kind: horoscope`, `birthday: YYYY-MM-DD`, and
optional `sun_sign` (known-sign override) and `instant_utc` (replay). Optional complete
birth details use the natal `birth` object and `place_id`; both are required together,
and the local birth date must match `birthday`. The natal calculator derives the
Western Sun sign, with source `natal_calculation`. The known-sign override still takes
precedence. Without complete details, the date selects an explicitly approximate
conventional tropical Sun-sign range.

The horoscope uses actual current planetary positions, the selected/calculated sign,
and the UTC date of the snapshot. It makes no claims about the user's natal Moon,
Ascendant, houses or personal transits. Raw birth inputs are excluded from chart facts
and model prompts. The client retains optional form drafts in `request.local_inputs`
for editing and explicit browser saves, strips that field before API submission, and
omits incomplete optional time/place pairs from the calculation request. Nothing is
saved automatically. Existing birthday-only saved requests remain compatible.

Both modes use one Gemini interpretation with whitelisted derived facts. Retrying
pins the original current instant. Existing browser saves remain readable; transit
saves can supply a natal request for a later new reading. Text/PDF exports distinguish
current versus natal aspects and omit raw input fields. Saved readings retain inputs.

## Vedic conventions and interpretation library

Send `tradition: vedic` for either natal or horoscope requests; omitted tradition retains
Western behavior. A Vedic horoscope also requires `birthday`, matching `birth.local_datetime`,
and `place_id`; a Sun-sign override is rejected. Its output separates the natal Moon sign
and nakshatra from the current sky and counts `moon_sign_house` inclusively from that sign.
It contains no natal angles or full natal record. Vedic personal-transit requests are rejected.

- Swiss Ephemeris `SIDM_LAHIRI` / `FLG_SIDEREAL`, explicit Moshier model.
- Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, mean Rahu and opposite Ketu.
- 27 equal nakshatras, each divided into four padas. Nakshatra rulers are not dasha periods.
- Whole Sign bhavas from sidereal Lagna; no bhava-chalit or divisional charts.
- Directional sign-based full Parashari drishti: seventh for the seven physical grahas,
  Mars fourth/eighth, Jupiter fifth/ninth, Saturn third/tenth. No node drishti,
  conjunction interpretation or Western degree-orb aspects in this convention.

`static/astrology/vedic-meanings.js` supplies 108 separately authored graha/rashi passages,
12 bhava descriptions, 27 nakshatra descriptions and nine graha introductions. Inspectors
use these local passages without additional model calls. A separate prompt contract
synthesizes calculated Vedic facts and forbids invented dashas, yogas, vargas or timing.
Pada text identifies the quarter only. These are reflective editorial interpretations,
not translations of classical verses or claims of scientific validation.

References: [Swiss programmer documentation](https://www.astro.com/swisseph/swephprg.htm),
[BPHS 26.4, full planetary aspects](https://vedicpupil.in/library/books/brihat-parashara-hora-shastra/chapter-26/verse-4),
[Garuda Purana 1.59, nakshatra associations](https://eternalraga.com/en/scriptures/puranas/garuda-purana/1/59).
Seven positions at 2000-01-01 00:00 UTC were compared to the
[published MyHora Lahiri table](https://www.myhora.com/ephemeris/january-2000.aspx?p=1&sid=lahiri&sys=sidereal&tz=utc+00%3A00).
Residuals are about 13–15 arcseconds, within the explicit 0.01-degree sample tolerance;
the apparent/mean ayanamsa convention may account for the common offset. This is an
external published-table check, not validation against an independent physical model.

## Running the local experience

`astrology/engine.py` is the shared calculator; the experiment imports a compatibility
shim. `astrology/service.py` validates requests and records time/location provenance.
`astrology/routes.py` registers the calculation API without loading the native binding.
The base app still starts without Swiss Ephemeris installed. Native calculations are
serialized within each process and explicitly request the bundled Moshier model.

Install the optional dependencies in a private environment and run locally:

```sh
python3.12 -m venv scratch/astrology-venv
scratch/astrology-venv/bin/python -m pip install -r requirements-astrology.txt
ORACLE_ASTROLOGY_ENABLED=1 scratch/astrology-venv/bin/python -m flask --app app run --host 127.0.0.1 --port 8884
```

Open `http://127.0.0.1:8884/astrology/`. The homepage adds an Astrology choice when the flag
is enabled. The host must provide IANA timezone data for Python's `zoneinfo`. Calculations
need no hosted astrology key. Set the existing `GEMINI_API_KEY` securely in the local runtime
for genuine interpretations. The root `.env` is Git-ignored and loaded by `python-dotenv`;
add `GEMINI_API_KEY=...` there and restart the local server. Never paste keys into chat. Without it, the chart still appears with a retryable message.
`GET /astrology/capabilities` reports `enabled`, `configured`, `interpretation_available`,
`chart_kinds` and `schema_version`; configuration is not proof of provider/runtime health.

`POST /astrology/chart` accepts a JSON object of at most 8192 bytes. For a birth chart:

```json
{
  "chart_kind": "natal",
  "birth": {"local_datetime": "2000-01-01T03:00:00", "timezone": "America/Phoenix"},
  "location": {"latitude": 33.45, "longitude": -112.07}
}
```

For a global current sky, send `{"chart_kind":"current"}`. Add `location` for local
angles and houses; add `instant_utc`, such as `2000-01-01T12:00:00Z`, to reproduce a
specific snapshot. Birth requests require a known time and caller-supplied IANA timezone.
Repeated wall times require `birth.fold` of 0 or 1; nonexistent wall times are rejected.
The user interface uses `place_id` instead of manual location/timezone fields: POST
`/astrology/places` with `{"query":"Sierra Vista, AZ"}`, then send the selected `geonames:ID`
as `place_id`. The server resolves coordinates and the historical IANA timezone. Mixing
a place ID with manual coordinates or birth timezone is rejected.

The response contains `type`, `chart_kind`, a unique `chart_id`, `created_at`, and a
schema-v1 `chart`. This calculation ID is not a completed reading ID. Within `chart`,
`inputs.utc` identifies the calculated instant; `engine` and `provenance` identify the
model, conventions, requested/returned flags and limitations. `planets`, `major_aspects`
and `lunar_phase` always appear. Local charts additionally contain `ascendant`,
`midheaven`, `whole_sign_cusps`, input coordinates and per-planet `whole_sign_house`.
Global charts omit all of those local fields. `input_resolution` distinguishes supplied
times from the server clock and records caller-supplied location/timezone provenance.

Responses use `Cache-Control: no-store`; the endpoint writes no chart to a database,
analytics or a model prompt. Disabling the flag returns 404; invalid inputs return safe
4xx errors; missing or failed native calculations return 503 without exception details.
Explicit astrology requests to `/chat` and `/chat/stream` return a directing error, preventing
a silent numerology fallback. The dedicated POST `/astrology/read/stream` accepts
`{"chart_request": {...}, "question": "optional"}`. It validates/calculates before streaming,
emits metadata before model initialization, then token/done events or a safe error.
The model receives only a whitelisted chart projection and the question, not the raw
date, time, coordinates or place ID. No chart data is written to analytics or a database.

Run the foundation and compatibility checks from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 scratch/astrology-venv/bin/python -m unittest discover -s tests -p 'test_astrology*.py' -v
PYTHONDONTWRITEBYTECODE=1 scratch/astrology-venv/bin/python -m unittest discover -s experiments/astrology -p 'test_*.py' -v
```

## Implemented boundaries

- `astrology/engine.py`: deterministic, versioned calculation record; no model or randomness.
- `astrology/service.py`: shared input validation, time resolution and place provenance.
- `astrology/places.py`, `place_routes.py`: local GeoNames lookup, lazy optional dependency.
- `astrology/reading.py`, `routes.py`: bounded prompt projection and metadata-first SSE.
- `static/astrology/`: dedicated form, starfield, planet inspectors, accessible placements,
  chart details, heart/depth prose, cancellation, retry and explicit local save/reopen.
  Planet nodes are the primary click/tap/keyboard controls; the full list is inside details.
  A compact entry card transitions into a full chart, with edit/return preserving the inputs.
  Particle masks form planetary glyphs at calculated longitude anchors; illustrative radial
  lanes reduce overlap. Selecting a planet shows instant reference meanings tied to its
  calculated sign and house. Aspect disclosures isolate the corresponding line and endpoints.
  `meanings.js` supplies original reference prose; these panels make no extra model calls.
  The existing single Gemini call still provides the overall personal synthesis.
- `static/astrology/entry.js`: capability-gated homepage entry; no existing-mode routing changes.
- `static/reading-layers.js` and `static/reading-pdf-worker.js`: existing parser/PDF code reused.
- `requirements-astrology.txt`: optional dependencies; the base app starts without them.

Saved charts use a separate browser key, `oracle_astrology_journal_v1`, with at most 20 entries.
Saving explicitly includes chart inputs, the question and available prose; reopening performs
no calculation/model call. Retries preserve the captured UTC instant and the saved-entry ID.
Text/PDF exports include calculated placements and prose; the PNG contains the chart image.
Completed readings also offer **Share reading**, matching the other traditions: Story
(1080×1920) and Post (1080×1080) PNG cards, up to three quotes from `ReadingLayers`,
enlarged preview, native file sharing with download fallback, Copy reading, and PDF export.
`static/share-card.js` is the shared compositor used by both the main readings and astrology.
Astrology renders a separate chart snapshot for sharing, preserving live selection and motion;
the card includes the chart, reading title and selected quote, never the raw birth-input fields.
No upload occurs when opening or rendering the dialog. Native share destinations depend on
the user's browser and installed apps; sending remains a user action.
Local browser verification (October 4, 2026) covered saved-reading reopening, both image
dimensions, quote switching, enlarged preview/Escape, Copy reading, a downloaded PNG
and four-page PDF, the 390px layout, light/dark themes, and the existing Tarot demo preview.
Both pages reported no browser console errors. Native delivery to a social app was not
performed; these checks do not establish delivery or native iOS share-sheet behavior.
Exports omit raw input fields and the question, but derived positions/prose remain personal.
The particle arrangement and radial distances are illustrative; longitude anchors are calculated.
Reduced-motion, pause, keyboard controls, mobile layout and light/dark themes are supported.

GeoNames lookup uses the pinned `geonamescache==3.0.2` cities1000 catalogue and vendored
administrative region names, with CC BY 4.0 attribution. See `astrology/data/admin1.SOURCE.md`.
Only the city query is sent to the local server; no geocoding provider sees birth details.
City centres are approximate and small settlements may require selecting a nearby city.
The local catalogue contains 170,391 cities. A local cold-load check took approximately
0.63 seconds with approximately 360 MB peak process RSS; qualify memory/startup on the
actual hosting runtime before release. The dataset is loaded only on first place use.

Runtime recommendation: pin Python 3.12 and `pysweph==2.10.3.6` for the first candidate.
Vercel currently documents Python 3.12 as its default, Flask/WSGI support, streaming, and
a 500 MB standard uncompressed Python bundle limit. PyPI publishes
`pysweph-2.10.3.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`.
That supports a plausible deployment path, not a successful deployment claim. Avoid
combining a Vercel routing/config migration with this feature unless necessary.

- https://vercel.com/docs/functions/runtimes/python
- https://pypi.org/project/pysweph/2.10.3.6/#files

The engine sets `SIDM_LAHIRI` on every Vedic calculation inside the native lock.
The lock covers planet, house and ayanamsa calculation; Western requests omit the sidereal
flag. It avoids per-request `set_topo`, `set_ephe_path` and `close` calls. Mixed-tradition
threaded regression checks compare complete outputs against sequential calculations.
Any cache is an optimization, never a required warm-instance source of truth. Explicitly
exclude scratch files, private birth-chart artifacts, credentials, and experiments from
deployment bundles; Git ignore alone is not proof of the final bundle's contents.

## Calculation and reading flow

1. User chooses astrology type and enters the required fields.
2. Server validates input and resolves the selected place and historical timezone.
3. Capture/resolve one instant, then compute a versioned chart record.
4. SSE emits the chart metadata before any Gemini call. The wheel and table can render
   even if interpretation credentials, quota or generation subsequently fail.
5. Build a bounded prompt from chart facts and the optional question, then stream one
   Gemini interpretation using the existing heart/depth/quote contract.
6. Save the completed natal reading only through an explicit local save action. Existing
   traditions retain their current journal behavior. A saved reading reopens from its
   stored chart and prose, without another calculation or model request.

Both `/astrology/chart` and `/astrology/read/stream` call the same preparation function.
The calculation-only endpoint needs no Gemini key. An ordinary reading uses one SSE
request that prepares then interprets the chart.
Validate before committing the stream response, with consistent safe 4xx errors.

Retrying an interpretation preserves the original normalized input and captured instant.
The server recalculates those inputs rather than trusting client-supplied planet positions;
a retry must not silently change a Sky now chart to a newer moment. New interpretation
attempts can have distinct reading/attempt IDs while the calculated snapshot is unchanged.
Do not introduce a durable server-side cache of birth details just to support retry.

The current default `else` in the routes falls back to numerology. An unsupported or
disabled explicit astrology request must return a clear error instead of entering it.

## Data contract

Keep the existing outer metadata fields (`type`, `canonical_reading_id`, `created_at`,
`content_format_version`) and add `type: astrology`, `chart_kind: natal|current|transit|horoscope`, and a
versioned `chart` object. `created_at` means reading creation, not the birth date.

Suggested chart fields:

- `schema_version`, `engine` (library, binding and data/model versions).
- `conventions` (tropical, geocentric, Whole Sign, orb policy).
- `instant_utc`, input precision, local offset/timezone provenance.
- `location_precision` and optional location; global charts have no local house fields.
- `planets`, `aspects`, `lunar_phase`; optional `angles` and `houses`.
- `warnings` for calculated limitations, rather than a misleading blanket accuracy claim.

Use separate internal calculation inputs, browser display data and LLM prompt projections.
Do not serialize the whole internal record into prompts, operational logs or shared cards.
Send Gemini the placements/aspects needed for interpretation; exact date/time, coordinates,
and place identifiers normally add no value to a natal interpretation and can be omitted.
Derived chart data is still personal information, not anonymized by that omission.

V1 uses no per-planet LLM calls. Placement inspectors show deterministic data; one full
interpretation covers the chart. Connection panels use 225 original pair/aspect passages
and 50 same-body transit passages, with no stock closing questions. See
[the connection library guide](ASTROLOGY_ASPECT_LIBRARY.md) for scope and validation. Later personal passages may use stable placement IDs,
without conflating them with Tarot/Rune symbol indices.

## Time, location and engine correctness

The engine separates global-sky and local-angle calculation functions. A global reading
has no arbitrary location, rising sign or houses.

Keep the prototype's strict aware-datetime validation and `resolve_local_datetime` behavior.
Use IANA timezone history, not the browser's present UTC offset. Reject nonexistent DST
wall times; ask the user which occurrence applies for an ambiguous time. Preserve seconds
for local calculations: AstroAPI's minute-only limitation is not a Swiss limitation.

A city search must return a specific city/region/country with verified coordinates and a
server-resolved IANA timezone. Never ask Gemini to guess them. The geocoding dataset/service
is now the offline GeoNames catalogue described above. Search sends only the place query,
not the birth date or question. Manual coordinates/timezone remain available for API tests.

Initially retain the explicitly configured Moshier model already exercised in the prototype.
Do not let presence/absence of data files silently change calculation models. If switching
to bundled Swiss ephemeris files before launch, treat it as an engine version change: pin
files and checksums, verify actual returned flags, and rerun reference fixtures. Confirm
supported date ranges and clear errors at extreme latitudes; do not claim universal precision.

## Delivery sequence and acceptance

### 1. Engine and server integration, local/private

- Refactor the calculator into a reusable module and define chart schema v1.
- Add calculation-only endpoint, shared reading preparation, safe validation and a default-off
  server capability flag. Hide the UI option when unavailable; reject its API requests too.
- Keep the native import lazy so a missing optional dependency cannot break Tarot/Runes.
- Check known historical charts, sign boundaries, retrograde stations, UTC conversion,
  DST gaps/folds, global-vs-local separation and supported latitude/date limits.
- Confirm equal inputs reproduce the same facts and that Gemini failure leaves a usable chart.

### 2. Complete astrology experience, local/private

- Add birthplace/time input, city selection, wheel, accessible table, heart/depth reading,
  explicit natal journal save, safe sharing and full export.
- Test natal and global/local Sky now end-to-end with fixture streams; verify cancellation,
  interpretation retry, journal reopening, exports, keyboard use, mobile sizes and both themes.
- Run existing reading, layered-output, journal, telemetry and export regressions.
- Run a genuine Gemini interpretation with authorized test inputs and review its claims
  against the chart. Fixture success alone does not establish generated-prose quality.
  Development exact-context logging must use synthetic/test inputs and remain disabled in production.

### 3. Release qualification

- Resolve Swiss/binding licensing for the intended public product before public activation.
- Verify a Linux artifact on the actual target Python/platform: import, calculate, stream,
  native state isolation, bundle contents/size, startup behavior and request concurrency.
- Verify no birth fields reach analytics, URLs, exception responses or ordinary share assets.
- Confirm an existing-mode reading still works when astrology is disabled or unavailable.
- Public deployment is a separate action; this plan does not activate a feature or buy a license.

### 4. Combined readings afterward

Reuse the same chart record as one component beside immutable Tarot/Runes/I Ching/number
artifacts. Capture one current instant for the whole reading, draw each component once,
and perform one deliberate LLM synthesis. Add combined rendering and prompt contracts
at that stage, without changing how natal charts are calculated.

## Current evidence and limits

Commit qualification, October 4: the complete Python suite in the isolated astrology
environment passes 182 tests (8 skipped), plus all 28 experiment tests. The Western
and Vedic meaning-library checks and all eight shared-card canvas traces pass.
Static review found no blockers in lazy dependency loading, prompt projections, or
share/export input exclusion. These checks do not establish a deployed Linux runtime.
Astrology stays disabled by default and its native dependencies remain optional while
the public license decision is open. Non-monetized public use still needs an applicable
license. `.vercelignore` excludes private environments, scratch output and experiments
from deployment uploads.

Vedic integration check, October 4: all 78 astrology Python tests and both JavaScript
meaning-library checks passed. The Vedic-specific suite has 12 checks, including all
108 pada boundaries, Moon-sign privacy, API/SSE validation, published-table comparison,
and 120 mixed-tradition calculations across eight threads. The 28 experiment tests also pass.

Browser fixture flows completed for Vedic natal and horoscope plus Western natal and
birthday-only horoscope. Required Vedic time validation blocked submission; saved Vedic
natal data reopened with the same tradition and details. Moon/Rahu/Ketu inspectors and
directional Jupiter-to-Moon drishti were checked. A downloaded Vedic text export includes
nakshatras, padas and directional glances without raw birth inputs. The download-event
observer timed out, but the completed file was found and its contents inspected.

Genuine Gemini Vedic horoscope and natal streams completed using synthetic 1990-03-20
15:30 Los Angeles test details. Inspected astronomical references matched their supplied
charts; no invented dashas or divisional charts appeared in these samples. The first
horoscope used overly certain personality wording, so the prompt was tightened. The
natal sample still uses confident poetic phrasing; these two runs establish integration,
not comprehensive interpretive quality or guaranteed prompt compliance. Phone-width
form and inspector checks at 390px showed no horizontal overflow. Native iOS behavior
and Vedic PNG/PDF downloads were not requalified in this pass. Screenshots are in
`scratch/astrology-ui-verification/vedic-*.png`. Main local preview remains on port 8884.


Current local checks: 78 astrology engine/API/place/reading/mode tests pass with the optional
dependencies; the base app suite passes 159 tests (25 skipped without optional dependencies).
All 28 experiment checks pass. JavaScript syntax and `git diff --check` pass. A full-suite
attempt in the small experimental virtualenv failed on missing legacy `psycopg` dependencies;
the normal app virtualenv was used for the full regression suite instead.

The shared birth-information form was checked after simplifying entry to Birth chart
and Horoscope. Both display date, time and birthplace. Fixture streams (real calculation,
labelled synthetic prose) completed for a full-details horoscope, birthday-only fallback,
and birth chart. A March 20 boundary example returned calculated Aries versus the
calendar-range Pisces estimate, with correct source labels. Editing retained the entered
details, birth-chart submission blocked a missing time, and the form fit a 390px browser
viewport without horizontal overflow. The restarted 8884 preview calculation API also
returned both expected Sun-sign sources. This pass did not repeat native iOS or live
Gemini quality testing.

An actual iPhone simulator Safari check on October 4 found overlapping native date/time
inputs that the Chromium 390px check missed. The mobile form now stacks those fields,
constrains their intrinsic width, and uses 16px input text. The corrected form was visually
verified on iPhone 17 Pro / iOS 26.2 and an isolated iOS 27 simulator; scrolling to the
submit button was checked on iOS 26.2. Screenshots are in the ignored
`scratch/astrology-ui-verification/` directory.

This is not a completed mobile end-to-end pass. iOS 26.2 Safari repeatedly crashed and
reloaded, including during a live Sky Now stream. Native crash reports include Canvas
fill-style string conversion, JavaScriptCore JIT compilation, and a separate simulator
startup crash before WebCore loaded. App causality is unresolved. The iOS 27 form loaded,
but Device Hub capture/control problems prevented completing the reading interaction.
Verify reveal, planet/aspect selection, long-text scrolling, and pause/resume on reliable
mobile Safari before considering the phone flow qualified. No animation mitigation was
applied based solely on these crash reports.

The added modes were checked through birth chart → transit, explicit saved-natal selection,
transit save/reopen, interrupted transit retry preserving UTC, birthday-only horoscope,
and a known-sign override. Mobile forms and the transit inspector fit 390px without
horizontal overflow. Genuine Gemini horoscope and synthetic-natal transit streams completed.
The first horoscope sample overstated a nonzero orb as exact and implied a station; prompts
were tightened to forbid these unsupported timing claims. This remains a sample check,
not a broad generated-text quality evaluation.

Browser checks exercised global Sky Now, synthetic natal chart with Sierra Vista lookup,
metadata surviving missing Gemini credentials, interrupted-stream retry preserving the instant,
save/reopen without duplicate entries, cancellation and repeated New York DST time resolution.
The staged form/chart flow, glyph reveal, per-planet meanings, aspect highlighting, replay,
edit/return and saved reopening were checked at desktop and 390px widths. A live global
Gemini stream also completed in the new flow. Text, PNG and PDF downloads were inspected
in the preceding integration pass. Fixture prose is prominently labelled as test data.
For reproducible UI stream testing without a key, run:

```sh
PYTHONDONTWRITEBYTECODE=1 scratch/astrology-venv/bin/python experiments/astrology/serve_ui_fixture.py
```

This binds only `127.0.0.1:8885`, calculates real charts and substitutes labelled synthetic
prose. The question `fixture:interrupt` interrupts its first attempt, allowing retry testing.
Never use fixture success as evidence of genuine Gemini quality. No native Linux or
publicly deployed runtime check is claimed. Licensing and release qualification remain open.

The private prototype has 28 passing tests. Previous live checks compared 30 planetary
positions with NASA JPL over three epochs; the largest discrepancy was 0.488 arcseconds.
Three AstroAPI comparisons passed the prototype threshold after both engines were aligned
to the same whole minute. These are sample checks, not full production or historical coverage.
A live global Sky Now Gemini stream completed in the integrated local UI, including HEART
and DEPTH rendering. No personal birth inputs were used in this provider check. The local source now includes
the default-off astrology experience; no deployment or production environment was changed.
An additional macOS ARM check compared complete chart JSON for 500 varied UTC/location
cases calculated sequentially and through 16 Python threads, with zero differences. This
does not establish Linux behavior or prove native calls actually overlapped under the GIL.

Official license references, checked October 4, 2026:

- https://www.astro.com/swisseph/swephinfo_e.htm
- https://www.astro.com/swisseph/swephprice_e.htm
- https://www.astro.com/swisseph/secont_e_2609.pdf

Current professional terms list CHF 700 for unlimited projects with a six-year duration;
AGPL is the alternative. Confirm applicable binding terms and the executed agreement.
