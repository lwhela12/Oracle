# Quantum Oracle — UI redesign plan

September 6, 2026 · Planning record. The user subsequently chose direct implementation instead of mockups; see `UI_REDESIGN_IMPLEMENTATION.md`.

## Design direction

Create a quiet, atmospheric entrance where the first useful action is choosing a reading. Give learning its own clearly labeled place and offer short explanations beside relevant choices. Preserve the richness of the traditions, the artwork, and the readings; reduce the amount competing for attention at any one moment.

The intended feeling is a contemplative space: midnight colors, warm gold, a distinctive oracle emblem, beautiful objects, and room to breathe. Navigation and instructions should use familiar language. The depth should be apparent in the imagery and available in the content.

## Evidence reviewed

- Current local app: `static/index.html`, its reading configurations, journal behavior, and supporting Python code.
- Browser inspection at 390 × 844: entrance, Tarot learning dialog, built-in sample Tarot reading, and share preview. Sample data was used; no live reading or external share was requested.
- Full 14:52 attached voice memo, reviewed through a local automatic transcription. Feedback below is paraphrased; timestamps are approximate. Specialized terms were sometimes mistranscribed.

The entrance is 2,209 CSS pixels tall at the inspected phone size. The first tradition begins at approximately y=643; all four tradition cards occupy 925 pixels; the reading button begins at y=2,063. Users pass the banner, introduction, quantum quote, instructions, and four detailed cards before reaching spread selection and the question. Essential card descriptions are styled at 12px, origin badges at 9.5px, and learning buttons at 10px.

Natalie's comments are research input, including suggestions to evaluate. The requested scope is a redesign plan, not authorization to implement every suggestion in the recording.

| Memo | Feedback | Design response |
|---|---|---|
| 0:00–2:28 | Small identity mark; unclear first icon; quantum explanation is a wall of text and exposes implementation details. | Strengthen the existing emblem. Use a labeled “How readings work” topic in Learn, with a short introduction before detail. Remove source-code references from ordinary explanatory copy. |
| 1:25–2:12; 12:53–13:07 | Journal is appealing, but she initially expects somewhere to write. Later she notices the saved reading. | Keep Journal, with “Your saved readings” as its explanation and an explicit saved state after a reading. Treat personal notes as a separate possible feature. |
| 2:30–3:29 | Awkward heading wrap; likes light/dark mode; sound and music controls seem redundant or unclear. | Shorter headline; retain appearance choice. Put labeled effects/music settings together under Settings. |
| 3:51–5:29 | Too many words and choices; “Lore & Origins” is hard to locate and its purpose is unclear; tradition names change between views. | Four compact choices with consistent names. “About Tarot” means explanation; selecting Tarot means starting its setup. |
| 5:29–6:31 | Question helper text appears clipped; likes preset topics; main button wraps and decorative stars feel inconsistent. | Persistent question label and separate helper text. Keep suggested questions. Short, plain action label with a restrained visual treatment. |
| 6:31–8:23 | Quantum status is confusing; reading header feels poorly stacked; loves the cards; duplicate flip instructions; wants swiping and consistent branded icons. | Simplify reading header. Preserve artwork, add swipe browsing with button alternatives, and use one interaction hint. |
| 8:23–10:19 | Likes the reading and share artwork; reports being unable to scroll the share view or reach download controls; wants clearer return navigation. | Preserve output quality. Redesign mobile sharing with a reachable close/back action and reliable content scrolling. Add a contextual “Back to reading” or “Back to top” link where needed. |
| 10:20–12:53 | Rune controls communicate state inconsistently; action is too bright; unexplained green indicator; inconsistent “New inquiry” / “New consultation.” | Native, labeled settings with explicit state; muted gold primary action; remove decorative live indicator; standardize on “New reading.” |
| 13:18–14:34 | Prefers the oracle emblem to the women-in-a-circle banner; date badges add confusion and resemble buttons; suggests expandable explanations. | Lead with the emblem. Move dates and extended history into Learn. Offer a clearly labeled inline explanation rather than making the same tap both select and expand. |
| 14:34–14:50 | Suggests a subtle hum or heartbeat for the action. | Explore restrained feedback after interaction. Continuous pulsing or required sound should not be part of the core flow. |

## Proposed navigation and journey

Three labeled destinations: **Read · Learn · Journal**. On mobile, use a compact bottom navigation; on desktop, place these links in the header. Put appearance, sound effects, and ambient music together in Settings. Use one small brand header on mobile instead of the current row of five utility icons.

**Read → select a tradition → review its setup → draw → explore the reading.**

Selecting a tradition opens its setup immediately. There is no separate welcome screen, required tutorial, or extra Continue step. With the existing default spread and an optional blank question, the target is two taps from arrival to starting a reading. This measures starting the request, not the time required for generation.

### 1. Entrance: make all four traditions visible

- One compact emblem and atmospheric treatment, replacing the separate illustration banner and repeated welcome block.
- Short heading, for example “Begin a reading.” One quiet supporting line, for example “Ancient symbols. Space for reflection.” These are proposed copy, not final brand language.
- Four generous, compact selectable rows. Each has a distinct tradition symbol, a familiar name, a one-line description, and a clear navigation affordance.
- Proposed labels: **Tarot** — perspectives through cards; **Runes** — guidance through symbols; **I Ching** — reflection on change; **Numerology** — meaning through numbers.
- Keep all four visible together at typical phone sizes. Avoid a horizontal carousel that conceals available traditions.
- Learn remains visible in the primary navigation. Long history, date badges, quantum quotations, and procedural instructions leave this screen.

This screen has one job: let the user choose. It does not need a second Start button beneath the choices.

### 2. Setup: only choices relevant to this reading

- Clear tradition title and a visible “Change tradition” action.
- Short selectable spread names, with one-line purpose descriptions. Preserve current defaults; do not silently replace a three-card reading with a single card in the name of speed.
- An “About this reading” disclosure for a short beginner explanation. Deeper material links to Learn and returns without losing the question or options.
- “Your question (optional)” as a persistent label. Place the general-guidance explanation outside the textarea so it cannot be clipped as placeholder text.
- Retain suggested questions under a small “Need inspiration?” disclosure. General guidance remains available without typing.
- For runes, put reversals and the blank rune under “Reading options.” Use a real on/off switch for reversals and a clearly labeled 24-rune / 25-rune choice for the set. State must not depend on gold color alone.
- Use one prominent, short action such as **Draw cards**, **Cast runes**, **Cast hexagram**, or **Draw a number**. A mobile action area stays reachable without covering content, the keyboard, or the navigation.
- I Ching and Numerology do not get a meaningless spread-selection step when only one option exists.

Preserve the complete current inventory:

| Tradition | Available readings |
|---|---|
| Tarot | Three cards; Single card / yes-no; Five-card cross; Celtic Cross — 10 cards |
| Runes | Three Norns; Single rune; Five-rune cross; Thor's Hammer — 5 runes; Nine Worlds — 9 runes; reversal and blank-rune settings |
| I Ching | Hexagram casting, including changing-line and transformed-hexagram results |
| Numerology | Number reading, using the existing 1–999 behavior |

### 3. Learn: an obvious destination with increasing depth

- Start with “Choose a tradition” and “How readings work,” using the same names and symbols as Read.
- Organize each tradition around **What it is → When to use it → Choose a spread → Symbols and meanings → History and origins**.
- Lead with a short explanation and examples. Put long essays and technical material behind clearly labeled sections.
- Include “Try a Tarot reading” or the corresponding tradition action, preserving any existing draft inquiry.
- From a completed reading, allow “About this card,” “About this rune,” or “About this hexagram” without losing the reading or scroll position. Specific symbol lessons beyond current content should be identified as a later content task.
- Natalie's expansion suggestion is useful for short explanations. Keep the explanation control distinct from the selection control so users can predict what a tap will do.

### 4. Reading: protect the strongest part of the app

- Keep the existing card and rune artwork and the full interpretation. Do not introduce an extra model call to summarize every reading as part of the UI pass.
- Order the page clearly: reading title and question, drawn objects, interpretation, then secondary actions.
- Show the spread arrangement, with a readable full-size inspection view. Support swipe between cards/runes and retain accessible previous/next buttons. Preserve spread positions and labels.
- Make portrait orientation fully usable; landscape can be an optional expanded view.
- Remove duplicate flip instructions and decorative emoji. Use a consistent icon family for controls and the existing custom artwork for tradition identity.
- Consolidate the footer to **Share**, **New reading**, and a clear **Saved to Journal** state. Put image-download variants inside Share.
- Use readable headings, paragraphs, and spacing for the existing streamed interpretation. Long readings can have a contextual Back to top control without adding another permanent floating button on arrival.

### 5. Sharing and Journal: complete the experience

- Preserve the talisman artwork. Use a smaller initial preview with a way to enlarge it, a single content-scrolling region, and a persistent reachable close/back action.
- Keep Share and Download reachable at small screen heights and when editing the quote with the keyboard open. Do not bury actions under a fixed-height preview.
- Return to the same reading and scroll position after closing Share or Learn.
- Explain Journal as saved readings on this device. Current storage is local and limited to 25 entries; the wording should reflect that behavior rather than implying permanent cross-device storage.

## Visual system

- **Palette:** midnight/ink foundations, warm ivory text, restrained antique gold, and subtle violet atmosphere. Preserve a legible light mode.
- **Typography:** a distinctive serif for the brand and short headings; a highly readable text face for controls and explanations. Target 16px controls/body copy and 18px reading prose, with comfortable line spacing. Avoid tiny uppercase instructions.
- **Surfaces:** reduce the nested panels, outlines, pills, and glows. Use spacing and type hierarchy to group content. Reserve strong emphasis for the active choice and main action.
- **Identity:** develop the existing oracle emblem as the arrival focal point. Keep ornament intentional and separate from functional labels.
- **Motion:** brief transitions and a subtle reveal can create ritual. Do not delay the request or hide available content behind a timed animation. Honor reduced-motion preferences; keep audio under user control.

## Delivery sequence after this plan

1. **Review the proposed direction in phone mockups.** Show entrance, Tarot setup, rune options, Learn, completed reading, and Share as one connected journey. Include a desktop adaptation and both appearance modes. This is the next reviewable deliverable.
2. **Implement entrance, setup, and navigation.** Apply the type/spacing system and plain labels, preserving every tradition and spread. Extract deterministic view/state handling from the large HTML file only as needed for these changes.
3. **Implement reading, learning, and utility improvements.** Resolve share-panel scrolling, preserve return state, improve inspection controls, and clarify the Journal. Keep generation behavior stable unless a specific UI requirement demands a change.
4. **Verify the complete phone journey and refine with Natalie.** Test both first-time and returning-user tasks. Use her original reported problems as the review checklist.

The interaction and configuration logic should remain deterministic. The UI redesign does not require new agent loops or JSON-only model responses. If live model calls are used in implementation testing, follow the repository's requirement for gitignored development-only logs containing each exact context payload, output, and invocation location; do not enable that logging in production.

## Acceptance criteria

- At 390 × 844, all four traditions and Learn are visible on arrival without scrolling. At 375 × 667, target the same; at narrower widths or enlarged text, allow natural scrolling rather than shrinking or clipping essential content.
- With defaults, a user can start any tradition in two taps without typing. Every existing spread and rune option remains discoverable in that tradition's setup.
- In a first-impression review, a new user can identify how to get a reading and where to learn within five seconds. This is a validation target, not a measured result yet.
- Controls have generous touch targets, visible labels/focus states, explicit selected states, and adequate contrast. Check 200% text scaling, reduced motion, keyboard navigation, and screen-reader names.
- Learn, Journal, and Share always provide a reachable exit and preserve the relevant draft or reading on return.
- Share and Download are reachable at 320px, 375px, 390px, and 430px widths, short landscape heights, and with the software keyboard open. Verify on a real iPhone/Safari in addition to browser viewport checks.
- All Tarot and rune spread layouts, I Ching changing and unchanging results, and Numerology render correctly. Verify loading, failure/retry, saved readings, native-share cancellation, and download fallback.

## Review boundaries and follow-up notes

The local UI review does not establish behavior in every mobile browser or verify live generation. The inspected share preview places its actions below the initial viewport, but mouse-wheel scrolling did bring Download into view. Natalie's exact scroll lock was therefore not reproduced in desktop Chromium at a phone viewport; it remains a priority to reproduce and resolve on her device.

The current UI repeatedly labels entropy as a live quantum state, while supporting code contains a random-number fallback. In the redesign, “How readings work” should be explanatory; any live provenance/status badge should reflect actual response data. The long-form historical quotations and scientific claims should receive a separate editorial check before being reused in revised learning copy.

New journaling notes, accounts, cross-device sync, a new lesson catalog, and changes to interpretation style are possible later additions, not dependencies for simplifying this UI.
