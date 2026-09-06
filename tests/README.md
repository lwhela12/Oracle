# UI browser verification

`verify-ui.cjs` checks the redesigned app in Chrome using Playwright. It intercepts **every `/chat` and `/chat/stream` request** and supplies deterministic fixtures. It makes no live model calls and sends no external shares. The native-share cancellation case replaces the browser share API with a local test function.

Start the Flask app in one terminal:

```sh
.venv/bin/python -m flask --app app run --host 127.0.0.1 --port 8876
```

With Node.js, Chrome, and the `playwright` package available:

```sh
node tests/verify-ui.cjs
```

To use a Playwright installation outside this repository:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/node_modules/playwright node tests/verify-ui.cjs
```

`ORACLE_TEST_URL` can override `http://127.0.0.1:8876`.

The script covers all 11 reading configurations; rune flags; changing and unchanging I Ching; draft and navigation preservation; saving and reopening journal entries; card keyboard/swipe inspection; share controls at short viewport heights; a simulated software-keyboard viewport; PNG export; native-share cancellation; light appearance; request errors, retry, stream interruption, compatibility fallback, cancellation, and reduced motion.

Screenshots, a result file, and a clearly labeled mock API log are written to **gitignored** `scratch/ui-verification/`. This is a fixture log, not an LLM output log. If future tests make real model calls, the repository's development-only exact-context/output logging requirement applies separately. No test logging runs in production.

Viewport and synthetic-touch checks do not replace a physical iPhone/Safari check.

## Learning restoration checks

Run `node tests/verify-learning.cjs` (with the same optional `PLAYWRIGHT_MODULE` and `ORACLE_TEST_URL` settings). This checks key restored topics in all five guides, expand/collapse and keyboard controls, topic navigation, widths from 320 to 1365 pixels, all 11 reading links, draft and chapter preservation, and both themes. It intercepts and rejects generation requests; no model calls are made. Evidence is saved as `scratch/ui-verification/learning-result.json` and `learn-*.png`.
