# Quantum Oracle UI redesign

Implemented September 6, 2026. The user chose direct implementation instead of a separate mockup phase.

## What changed

- A compact entrance presents Tarot, Runes, I Ching, and Numerology together. The oracle emblem, midnight palette, warm gold, and serif display typography establish the atmosphere.
- Read, Learn, and Journal are labeled navigation. Settings groups appearance, sound effects, and ambient music; sound is opt-in for a new visitor.
- Each tradition has its own setup. Every existing spread and rune flag retains its API identifier and behavior. With defaults, selection and drawing take two taps; a question remains optional.
- Learn contains full expandable guides to symbolism, every spread, interpretation, practice, history, and draw mechanics, plus a substantial explanation of quantum randomness and synchronicity. A topic selector, expand/collapse controls, and remembered open chapters support deeper reading. Draft questions, spread selections, and completed readings remain available when returning. See `LEARNING_CONTENT_RESTORATION.md` for the content audit.
- The reading view retains the artwork and full interpretation. It has consistent labels, accessible card/rune inspection, swipe navigation, a saved state, and a consolidated share action.
- Sharing keeps close, share, and download controls outside a single scrolling body. A compact preview can expand. Sizing accounts for viewport rotation and the on-screen keyboard's visual viewport.
- Journal clearly describes browser-local storage and its 25-reading limit. Entries are keyboard-accessible; reopening one restores the correct tradition and artwork.
- Streaming shows loading and error states, blocks duplicate submissions, supports explicit retry, and cancels the local request when starting over. An interrupted stream does not silently trigger another random draw.

## File organization

- `static/index.html`: semantic app structure.
- `static/ui.css`: navigation, responsive layout, typography, controls, learning, journal, and dialog sizing.
- `static/ui.js`: deterministic navigation, setup, learning presentation, preferences, request lifecycle, and journal handling.
- `static/artwork.css`: retained artwork, spread geometry, inspection, and export styling.
- `static/oracle.js`: spread configuration, artwork rendering, audio, and canvas export, extracted from the original HTML.
- `static/learning.js`: restored tradition lore, practical guides, and how-the-Oracle-works chapters.

Obsolete entrance/dossier styles and dialog controllers were removed. The Python generation code, model prompts, reading IDs, card/rune assets, and storage key are unchanged. External scripts are deferred so the initial content can paint while they load.

## Verification and limits

The browser regression script uses intercepted responses; it does not call a model. See `tests/README.md` for coverage and execution. Screenshots and fixture logs are stored in gitignored `scratch/ui-verification/`.

The checks cover the redesigned interface and its existing API contract. Live provider availability and behavior on a physical iPhone/Safari are not established by these tests. The learning restoration includes targeted corrections and source links; it is not a comprehensive scholarly review of every inherited symbolic association.

The redesign is local and has not been deployed.
