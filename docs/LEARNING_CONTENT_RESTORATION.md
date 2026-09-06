# Learn content restoration

September 6, 2026. The first design pass incorrectly reduced learning depth. This follow-up keeps the new reading flow and restores the missing subject matter in expandable guides.

## Content accounting

| Original material | Current home |
| --- | --- |
| Tarot mechanics: Major/Minor Arcana and four elemental suits | Tarot → The 78 cards & their symbolism |
| Rune mechanics: three ættir and Merkstave | Runes → The Elder Futhark & three rune families; Reversals & the blank rune |
| I Ching mechanics: six lines, four line states, changing hexagrams | I Ching → Hexagrams, yin & yang; The eight trigrams; How to interpret your reading |
| Numerology mechanics: 1–999, digital roots, master numbers | Numerology → Number symbolism & digital roots; A guide to 1–9 & master numbers |
| Existing usage and history for all four traditions | Each guide → When to use it; History & origins |
| QUANTUM_PROTOCOLS and quantum tradition tab | Each guide → How the Oracle draws; How the Oracle works → How each tradition is drawn |
| PRNG/QRNG comparison and fallback explanation | How the Oracle works → Quantum & computer randomness |
| Synchronicity and Jung/Pauli material | How the Oracle works → Synchronicity, Jung & the meaningful moment |
| Integrity and privacy material | How the Oracle works → Draw integrity & the limits of the system; Your question, Journal & privacy |

Added practical instruction covers all 11 reading configurations, position meanings, examples, preparation, interpretation, and reflection. The tradition introductions still offer immediate access to reading setup.

## Presentation

- `static/learning.js` holds the recovered lore and expanded static editorial material. It loads after `oracle.js` and before `ui.js`.
- Native disclosure chapters have descriptive subtitles. The first chapter opens initially; a topic selector opens and focuses a selected chapter. Expand/collapse all supports continuous reading.
- Open chapters survive navigation within the current session. Learn-to-reading links retain the question and select the requested spread. Returning from a deeper learning page still returns to the original question or reading.
- Long text wraps at phone widths and follows the app's dark/light theme. There are no new model calls or content generation on page load.

## Editorial changes

Restored topics are not a verbatim republication of all original claims. The original guaranteed quantum resonance, described hardware details the app does not verify, asserted that quantum physics validated divination, and implied complete local privacy. Those explanations now distinguish symbolic philosophy from observable application behavior.

Selection and data flow were checked against `tarot.py`, `runes.py`, `iching.py`, `oracle_logic.py`, and the browser Journal implementation. The text acknowledges secure fallback, no per-draw source display, integer-sort ties, and the fact that AI interprets an already completed draw. Numerological reduction is described as an interpretive technique rather than an enforced computation.

Targeted historical edits distinguish esoteric interpretation from documented Tarot origins, Norse myth from a reconstruction of ancient casting, and traditional I Ching authorship from established authorship. This is not a comprehensive scholarly review of every inherited symbolic association.

References consulted, with user-facing links in the guides:

- [Tarot history, The Metropolitan Museum of Art](https://www.metmuseum.org/perspectives/tarot-2).
- [The Pictorial Key to the Tarot, A. E. Waite](https://en.wikisource.org/wiki/Pictorial_Key_to_the_Tarot).
- [Hávamál, University of Pittsburgh text collection](https://sites.pitt.edu/~dash/havamal.html).
- [Runes, National Museum of Denmark](https://natmus.dk/historisk-viden/temaer/runer/).
- [Book of Changes, Chinese Text Project](https://ctext.org/book-of-changes/ens).
- [Jung's Foreword to the I Ching, Princeton University Press](https://www.degruyterbrill.com/document/doi/10.1515/9780691213965-012/html?lang=en).
- [Pauli/Jung correspondence, CERN Pauli archive bibliography](https://sis.web.cern.ch/archives/Pauli_archive/committee/Pauli_books).
- [qrandom.io provider description](https://qrandom.io/) and [API documentation](https://qrandom.io/docs).
- [Python SystemRandom documentation](https://docs.python.org/3/library/random.html#random.SystemRandom).

## Verification

`tests/verify-learning.cjs` checks restoration of key topics on all five guides, disclosures, keyboard use, topic jumping, phone/tablet/desktop widths, all 11 spread links, retained question and open chapters, nested learning return, and both themes. It fails if a generation request occurs. The existing UI regression also checks reading, Journal, and sharing with intercepted fixtures.

Evidence is gitignored under `scratch/ui-verification/`, including `learning-result.json` and `learn-*.png`. No live model calls or external shares are made by these checks. Physical iPhone/Safari testing remains separate.
