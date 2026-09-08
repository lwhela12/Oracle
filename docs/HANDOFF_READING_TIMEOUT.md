# Handoff: "This reading is taking too long" on the deployed app

September 8, 2026. Written for whoever picks this up next. Everything below is committed and pushed to `main`; production is at https://www.qoracle.app (the bare domain redirects to www).

## Symptom reported

On iPhone Safari against production, a reading generates (sometimes slowly), the full interpretation appears, and then the error box at the bottom says "This reading is taking too long. Please try again for a new draw." The Share button stays disabled and the status line never shows "Saved to Journal". Lucas reports this on every reading as of the morning of September 8.

## What was wrong, and what has been fixed

Three separate defects stacked on top of each other. All three are fixed in `main`.

1. **The server never closed the stream.** `app.py` sent an explicit `Connection: keep-alive` header on the `/chat/stream` response. On Vercel this kept the HTTP response open indefinitely after the Flask generator finished, so the browser's reader waited on the socket until the client-side timeout fired. Removing the header makes Vercel close the response right after the `done` event. Verified with `curl` against production: the request now completes in about five seconds instead of running to the `--max-time` limit. Commit `f1c6015`.
2. **The client waited for the socket instead of the `done` event.** `static/ui.js` now stops reading and cancels the reader as soon as it parses `event: done`. Commit `0e609bb`. This is belt-and-braces now that the server closes the stream, but keep it: it protects against any other host that holds connections open.
3. **The client timeout was a fixed two minutes from the button press.** A long reading that was still streaming at 120 seconds was aborted just before the end. The timeout is now inactivity-based: up to 120 seconds for the first response, then abort only after 90 seconds with nothing arriving; the non-streaming fallback gets 240 seconds. If a stream does go quiet after text has arrived, the message now says so and offers a fresh draw instead of claiming the reading took too long. Commit `2d514eb`.

Static assets carry `?v=20260908a` in `static/index.html` so a phone cannot keep running the previous `ui.js`. Bump that string whenever `ui.js`, `oracle.js`, `learning.js`, `ui.css`, or `artwork.css` change.

## What was measured against production

All timings are for `/chat/stream` on www.qoracle.app, from this Mac.

| Check | Result |
|---|---|
| Node fetch, numerology, before the header fix | events complete at ~11 s, connection still open at 40 s |
| `curl`, numerology, before the header fix | ran to the 100 s limit with `event: done` already received |
| `curl`, numerology, after the header fix | closed at 5.3 s, `event: done` present |
| Node fetch, three-card tarot, fresh session | first token 4.8 s, done 10.0 s, ~5.7 KB |
| Node fetch, three tarot readings in one session | 7.8 s, 11.0 s, 10.3 s (history makes readings slightly longer, not slower) |
| Playwright WebKit (iPhone user agent), numerology | first text 6.1 s, complete with Share enabled at 11.2 s, no error |

Also ruled out: no service worker; Vercel does not compress the event stream; the deployed `ui.js` contained the client fixes at the time of testing; Vercel runtime logs show only 200s plus bot probes for WordPress paths in the last 24 hours.

## What has not been verified

- **A real iPhone.** Playwright's WebKit is close to Safari but uses a different network stack. The report of "every time" on the phone predates the server-side fix in `f1c6015`, so the first thing to do is retest on the device with a fresh page load.
- **The home-screen app.** `static/manifest.json` declares `display: standalone`. If the app was added to the home screen, iOS can hold an older copy of the page and scripts. Remove and re-add it, or open the site in Safari proper, before concluding anything.
- **Long readings at slow API moments.** Gemini latency varies a lot by time of day. A Celtic Cross at a slow moment can take well over a minute; the inactivity timeout should now let it finish, but this has only been checked with a simulated 135-second stream (`tests` have no such case; see the ad hoc `slowstream.js` approach below).

## If it still happens on the phone

Work through these in order. Each one takes a few minutes.

1. Confirm the phone is running the current build: in Safari, load `https://www.qoracle.app/static/ui.js?v=20260908a` and search the text for `armTimeout`. If it is missing, the phone is cached; clear website data for qoracle.app.
2. Attach Safari Web Inspector from a Mac (Settings → Safari → Advanced → Web Inspector) and watch the Network tab during a reading. Note when the first byte arrives, whether tokens arrive progressively or all at once, and whether the request finishes on its own. All-at-once delivery followed by the error means iOS is buffering the chunked response; in that case the fallback is to have iOS use the non-streaming `/chat` route, which returns one JSON document and closes.
3. Reproduce a slow reading locally without the API: a small Node proxy that serves `/chat/stream` with one token every three seconds for 135 seconds and proxies everything else to the Flask app on port 8876. With that in place the reading must finish with Share enabled and "Saved to Journal" shown.

## Optional improvement noted while investigating

Readings are independent, but the server keeps a chat per browser tab for two hours and feeds every earlier reading in as context. It does not make readings slower in any meaningful way, but it makes them a little longer and lets the model refer back to earlier questions. Sending a fresh `session_id` per reading from `static/ui.js`, or calling `POST /session/clear` before each reading, would remove that.

## Running the checks

```sh
.venv/bin/python -m flask --app app run --host 127.0.0.1 --port 8876
PLAYWRIGHT_MODULE=/path/to/node_modules/playwright node tests/verify-ui.cjs
PLAYWRIGHT_MODULE=/path/to/node_modules/playwright node tests/verify-learning.cjs
```

Both suites intercept the model calls with fixtures; neither makes live requests. `verify-ui.cjs` covers stream interruption, the non-streaming fallback, cancellation, and the timeout error path.
