# Oracle usage and provider health

## Where to look

Vercel: https://vercel.com/lwhela12s-projects/oracle/logs

Search for `oracle.telemetry.v1`. `qrng_result` includes `source` (`quantum`,
`system`, `mixed`), `reason`, `http_status`, `requested`, `fallback_values`,
and request latency. `rate_limited` means HTTP 429; other provider errors are
kept distinct. `range_rejection` is a local unbiased-mapping fallback, not a
provider outage. All four traditions are instrumented.

`reading_started` and `reading_finished` share an `attempt_id`. Finished outcomes
are `completed`, `failed`, or `interrupted`. A hard process termination may leave
only a start event. HTTP 200 alone is not considered a successful streaming reading.
`reading_id` stays the same if the browser switches from streaming to synchronous
transport; a new user-initiated reading/retry gets a new ID. Count distinct completed
reading IDs for popularity; count all attempts for infrastructure usage.

`interpretation_usage` records model and reported token counters, including
thinking/cached tokens when supplied. Counters from streaming responses are taken
from the last reported usage object, not added once per chunk. No token prices are
hard-coded. Missing usage is unavailable, not zero.

## Anonymous user estimates

`app_opened` records an observed browser load. A random browser-local UUID groups
visits and readings across days. No login or fingerprinting. Multiple devices,
cleared storage, private browsing, opted-out visitors, bots and spoofed IDs mean
these are estimates of browsers, not verified counts of people. We do not infer
"first ever" from incomplete logs. Data collection starts after this deployment;
there is no historical backfill.

Analytics events exclude questions, prompts, interpretations, symbols, session
history, IP addresses, user agents, query strings and referrers. Hosting access
logs are separate. DNT, GPC and the in-app Learn → How the Oracle works → privacy
opt-out suppress visitor linkage. Operational health logs remain content-free.

`ORACLE_ANALYTICS_ENABLED=1` enables anonymous IDs in production logs and optional
forwarding; `0` disables linkage/forwarding. When unset it defaults on only when
`VERCEL_ENV=production`. Preview/local events carry their own environment and
must be filtered out of business metrics. Local tests should leave it off unless
explicitly testing analytics.

## Report without another service

Export the relevant Vercel runtime logs as JSON or NDJSON, then run:

```sh
.venv/bin/python scripts/usage_report.py /path/to/export.jsonl
```

The JSON report includes visitors/readers in the export, successful readings by
tradition/spread, daily reader counts, people with 2+ completed readings that day,
reading-frequency buckets (1, 2, 3, 4, 5+), provider fallback rates/reasons, and token
totals. Default day boundaries are America/Los_Angeles; change with `--timezone`.
Duplicate event IDs and duplicate completed reading IDs are excluded. Counts only
cover retained/exported logs; short log retention cannot establish lifetime users
or long-term retention. Missing days are missing evidence, not zero activity.

## Optional PostHog connection

PostHog is a hosted product analytics dashboard, not a QRNG provider. No account
or subscription is created by this code. Runtime logging works without it.

1. Create/select an Oracle project in PostHog.
2. In Vercel's Oracle project, set `POSTHOG_PROJECT_TOKEN` to its project token
   (not a personal/admin key). Set `POSTHOG_HOST` to `https://us.i.posthog.com` or
   `https://eu.i.posthog.com`, matching the project region.
3. Set `ORACLE_ANALYTICS_ENABLED=1` for Production and redeploy.
4. Complete a real reading and verify the events in PostHog before trusting reports.

The server sends one batch at reading completion (or failure/disconnect), and one
request per browser load. There is no autocapture, session replay or person-profile
creation. GeoIP enrichment is disabled. A batch uses short connection/read timeouts
and no retries. Delivery failure logs `telemetry_delivery_failed` but preserves the
reading. Events remain in runtime logs, but failed forwarding is not automatically
replayed. Hard kills before the final batch can be absent from PostHog; use Vercel
logs for that diagnosis. This is best-effort analytics, not billing-grade accounting.

### Suggested dashboard

Filter all insights to `environment=production`, and choose the same timezone.

- **Visitors:** unique `distinct_id` on `app_opened` within the selected period.
- **People who tried a reading:** unique `distinct_id` on `reading_started`.
- **Completed readings:** distinct `properties.reading_id` on `reading_finished`
  filtered to `outcome=completed`.
- **Most popular:** completed reading IDs, broken down by `mode` and `spread`.
- **Repeat use:** group completed reading IDs by `distinct_id` and local calendar
  date; count groups with 2+ and chart the 1/2/3/4/5+ distribution.
- **Returning readers:** retention insight on completed `reading_finished` events;
  compare day 1 and day 7 only after enough observation time has elapsed.
- **QRNG health:** fallback events / all `qrng_result` events, broken down by
  `reason`. Track provider failures separately from `range_rejection`.
- **Interpretation cost inputs:** token totals by model with coverage counts.

Use reader frequency and retention to evaluate subscription/credit limits. Use
persistent rate limits and failure rates to evaluate a paid QRNG source. No
monetization or automatic provider switching is enabled by this work.

References: https://posthog.com/docs/api/capture and https://vercel.com/docs/logs
