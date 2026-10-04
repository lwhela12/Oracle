# Astrology connection copy

The clickable connection panels use original, stored prose. There is no model call
on click. The chart calculator supplies the actual connection and its positions;
the browser selects a complete passage rather than assembling planet definitions,
an aspect definition, and a closing question.

## Coverage and source

- `static/astrology/aspects-sun-moon.js`: 17 pairs, 85 passages.
- `static/astrology/aspects-mercury-venus.js`: 13 pairs, 65 passages.
- `static/astrology/aspects-outer.js`: 15 pairs, 75 passages.
- `static/astrology/aspects-self.js`: 10 current-to-natal same-body pairs, 50 passages.

Each pair has conjunction, sextile, square, trine, and opposition entries. These are
lookup coverage counts, not claims that all combinations occur in a natal chart or
within a human lifespan. The calculator alone determines which connections appear.
In particular, the complete lookup matrix also serves cross-chart transits.

The 225 different-body passages describe symbolic relationships in neutral language,
so they can be used for natal connections, the current sky, and current-to-natal
connections. Reversing the lookup order returns the same essay. Transit panels separately
identify the current body, natal body, and both calculated positions before the essay;
the passage is not a personalized interpretation of those signs or houses. The 50
same-body essays are explicitly transit-only. Raw birth details are not stored in this
library. Planet, sign, house, and retrograde reference copy remains separate.

## Editorial approach

These are AI-drafted and editorially reviewed original passages, not quotations from
astrologers, a claim of professional astrological review, or evidence of scientific
validity. Each entry develops a relationship specific to its planet pair and aspect.
There are no automatic reflection questions. No entry should assert an event, a
diagnosis, a fixed personality, an exact station or future duration, or a compulsory
life milestone. Examples of possible expression should leave room for agency.

The main Gemini reading still provides whole-chart synthesis. Changes to these source
files apply when the page loads, including when saved readings are reopened. Their
stored generated reading text is not rewritten. This library is versioned with the
application rather than copied into each saved chart.

## Validation

Run `node tests/test_astrology_meanings.cjs` from the repository root. It checks all
275 entries, distinct complete paragraphs, reverse lookup, current/natal/transit
coverage, same-body restrictions, script load order, and safe missing-library behavior.
The three different-body files received a separate editorial review; the integration
review removed recycled phrasing and checked all same-body passages. Browser checks
cover saved natal/transit charts and the expandable connection panels.

For future edits, review adjacent passages together. Unique strings alone do not
establish good writing; check recurring sentence structures, interchangeable endings,
and whether the paragraph still says something specific about its named connection.
