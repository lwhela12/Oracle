# Oracle owner dashboard plan

Prepared September 29, 2026; implementation status updated September 30.
The analytics foundation is live in production. The private dashboard is built
and locally verified; Google OAuth setup and owner enrollment remain before its
release. See [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md) for the implemented scope
and deployment checks. The sections below retain the original product plan.

For the concrete database schema, budget target, and implementation work order,
start with [DATABASE_PLAN.md](DATABASE_PLAN.md). This document retains the detailed
dashboard metric definitions and product contracts.

## Recommended outcome

Build a private, responsive owner dashboard at `qoracle.app/admin`, styled to fit
Oracle. Store the existing telemetry in a persistent PostgreSQL database and
build the metric queries, authenticated API, and dashboard ourselves. Keep Vercel
as the application host and AWS Marketplace as the
ANU billing source. An AWS subscription does not require moving the app to AWS.

We own the event schema, calculations, UI, and data lifecycle. The selected
hosting direction is **Railway PostgreSQL**, while Flask continues to run on
Vercel. Railway's database template is an unmanaged service: we operate its
security, backups, recovery, tuning, and maintenance. This plan records the
hosting decision; the staging database has since been provisioned and tested.
[Railway database responsibilities](https://docs.railway.com/databases)

Managed authentication is a separate decision. Select a maintained identity
service for owner login and later customer accounts; do not build password
storage, recovery, or session renewal ourselves. Railway PostgreSQL does not
supply that application identity service, and this plan adds no Supabase
subscription. PostHog is not a dependency.

Choose a database region close to the actual deployed Flask function region,
verify a serverless connection budget and pooling configuration, and isolate
production from test/preview data. Keep schema migrations and reporting queries
in the repository. The data model remains ordinary PostgreSQL, with identity
provider integration behind a verified-account boundary.

Design this database as the foundation for future accounts, saved readings, and
cloud journals. One PostgreSQL database can serve both product storage and
analytics initially, with separate schemas and narrowly scoped runtime roles.
The dashboard release establishes these boundaries; public accounts and journal
sync are a subsequent product feature, not a prerequisite for collecting usage.

The dashboard should answer three questions: Is usage growing? Do readers come
back? Is Oracle delivering readings reliably at an acceptable cost?

Assume one owner initially, America/Los_Angeles reporting days, and production-only
business metrics. Start with Today, 7 days, and 30 days, with visible source
freshness and a manual refresh. Indexed queries are sufficient until measurements
show a need for caching. Add custom ranges and previous-period comparisons later.
Clearly distinguish a partial current day from completed days.

The review changes the earlier plan in four ways: keep managed auth separate
from database hosting; ship one small dashboard first; establish a reading identity independent
of analytics; and explicitly give saved user data stronger write guarantees than
telemetry. A queue, a warehouse, and a complete sync engine are unnecessary for
the first release.

## Evidence and starting point

- `telemetry.py` already emits content-free, versioned events with event,
  reading, and attempt IDs; timestamps; environment; tradition/spread; completion
  outcome; QRNG source/latency; and reported model/token usage.
- Fresh production logs inspected during planning contain `app_opened`,
  `reading_started`, `qrng_result`, `interpretation_usage`, and
  `reading_finished`. Anonymous linkage and token reporting are present in this
  bounded sample. This is schema verification, not a traffic baseline.
- `static/analytics.js` supplies browser-local anonymous identifiers and respects
  DNT, GPC, and the existing opt-out. `static/ui.js` retains the reading ID across
  automatic transport fallback and creates a new ID for a user-requested retry.
- `scripts/usage_report.py` provides a useful reconciliation starting point;
  `tests/test_usage_report.py` covers some deduplication and timezone behavior.
- Optional PostHog forwarding already exists, but this design does not use it.
  Its live configuration has not been verified; check before retiring any active
  forwarding so the transition does not silently interrupt existing collection.
- No dashboard authentication or durable event database was found in the
  inspected application files. Runtime logs alone have limited retention.
- The current journal stores up to 25 readings in browser `localStorage`
  (`static/ui.js`). Records contain questions, interpretation text, draw metadata,
  a timestamp-based local ID, and a display-formatted date. They do not currently
  sync across devices, and their IDs/dates need deliberate import handling.

## Shared product database foundation

Use separate `product` and `analytics` schemas. A schema is organization, not an
automatic security boundary: enforce grants and use separate runtime credentials.
The dashboard's reporting role can read analytics aggregates and events but has
no access to private questions, interpretations, or journal notes. Migration and
backup privileges do not belong to the normal application roles.

Document the following product model now and add its tables as the corresponding
features ship; do not create speculative tables for every possible future feature.

| Data | Planned responsibility |
| --- | --- |
| Managed authentication | Separate maintained provider, selection pending; validate issuer and immutable subject, and map them to an internal account ID rather than using email as ownership |
| `product.profiles` | Application-specific preferences/account data keyed to the verified account; avoid duplicating the provider's credential/identity tables |
| `product.readings` | Owner, stable reading UUID, UTC time, tradition/spread, exact draw snapshot, question and interpretation, model/format version |
| `product.journal_entries` | Owner, associated reading, private notes/reflections, created/updated time, revision for future sync |
| `analytics.events` | Allowlisted content-free usage and operational records; independently retained and aggregated |

Keep customer identity separate from administrator privileges. When the owner
login is implemented, use explicit authorization; having a customer account must
never grant access to `/admin`. Anonymous browser IDs and current chat session IDs
are not trusted account ownership credentials. If account-linked analytics is
added later, respect analytics preferences; account creation does not imply
permission to attach identity to historical anonymous events.

Validate authentication on the Flask server. Derive database ownership from that
verified identity. With pooled SQL connections, scope any ownership context to
the transaction and prove it cannot leak into the next request. Do not use an
unrestricted service/admin credential for ordinary customer data access and
assume row-level policies still apply.

Before shipping cloud journals, enforce authenticated ownership on every read,
write, export, and delete. Use server checks and PostgreSQL row-level security as
defense in depth with appropriate non-owner runtime roles. A request must not
choose its effective owner merely by sending `user_id`. Test that account A cannot
read, edit, export, or delete account B's records, including by guessing IDs.

Preserve the exact completed reading so reopening a journal does not redraw or
regenerate it. Keep draw IDs and content-format versions stable. Reading text and
notes belong only in product storage, never in telemetry, aggregate exports, or
admin dashboards. Text-based journals can initially live in PostgreSQL; consider
object storage only if future image/file attachments warrant it.

Cloud save/sync should be an explicit user feature. Preserve local-only use and
existing journals during the dashboard build. Later offer an intentional import
after sign-in, deduplicate repeated imports, and keep the local copy until the
server confirms persistence. Legacy display dates may lack a year/timezone;
preserve the original label and mark uncertain dates rather than fabricating an
exact creation time. Assign stable IDs to imported entries before retrying upload.

Define edit conflicts and deletion propagation before enabling multiple-device
sync so a stale device cannot silently overwrite notes or restore a deleted entry.
Account export/deletion and backup retention need product-specific rules. Private
journals must not inherit the analytics event retention policy.

For dashboard v1, implement schema migrations, scoped roles, and a reusable
verified-owner identity boundary. Finalize the reading/journal contracts above.
Public registration, account recovery, cloud save, journal import, and sync remain
the next release unless explicitly added to the implementation scope.

### Reading identity, runtime state, and persistence

The current `reading_id` is browser-supplied telemetry correlation. It is created
in `static/analytics.js`, is absent from the returned reading metadata, and is
not retained by the local journal. The journal generates a separate timestamp ID.
Repeating a reading POST currently generates a new draw. Event deduplication does
not make reading generation idempotent.

Define three concepts explicitly: a client operation key for a requested action,
an execution attempt ID, and a server-generated canonical reading ID for a draw.
During the foundation build, return the canonical reading ID, UTC creation time,
and content-format version with each reading and preserve them in the local
journal. Generate these independently of optional analytics. Preserve existing
telemetry semantics through an explicit schema migration; do not silently change
the meaning of historical `reading_id` fields.

Later, cloud-save retries must refer to the same canonical reading and produce
one saved record under the authenticated owner. A deliberate new draw gets a new
ID. If generation retries are to return the same draw, implement a separate,
durable operation record with owner-scoped idempotency and concurrency tests;
do not claim that the initial dashboard release provides exactly-once generation.

Generation now creates a fresh chat for each reading and ignores session IDs for
history lookup. No reading history is retained across requests by the application.
The previous client-keyed in-memory conversation cache has been removed.

Analytics writes may fail without stopping a reading. Product writes have a
different contract: report "Saved to your account" only after the database commits;
otherwise report the save failure and retain the local copy for retry. Apply this
to new readings, edits, imports, and deletes. When cloud persistence ships, use the
product record as the authority for saved-reading counts; telemetry remains the
source for attempts and guest usage. Never reuse the telemetry swallow-error path
for product persistence.

## Dashboard layout

**First release: one overview page.** Show completed readings, linked active
browsers, completion/outcome counts, daily volume, tradition/spread popularity,
median/p95 reading time, quantum fallback, reported tokens, and estimated provider
cost when verified pricing is available. Show collection freshness and gaps.
Use counts alongside percentages. Do not turn immature retention into a headline
or invent growth targets before collecting a baseline.

The following are later expansions of the same dashboard, not four separate
views required for the first release:

**Audience:** visitors, readers, activation, readings per reader, repeat-use
distribution, and retention cohorts. Label these as anonymous browsers, not
verified people. Retention is available only for sufficiently mature cohorts.

**Reliability:** attempts, logical reading completion, failed/interrupted/unknown
attempts, median and p95 reading time, ANU latency, failovers, and system-random
fallback. Keep anonymous operational totals separate from opted-in audience
metrics so their denominators remain understandable.

**Costs:** estimated ANU and Gemini usage costs, cost per completed reading, token
coverage, and dated provider billing totals when available. Hosting and database
charges are separate expense lines. Include failed attempts in expense totals.

Each view shows source freshness, reporting coverage start, timezone, active
filters, and incomplete data warnings. Aggregate CSV export is a later addition.

## Metric definitions

| Metric | Definition and source | Decision supported |
| --- | --- | --- |
| Completed readings | Distinct `reading_id` with at least one completed `reading_finished`; count once across transports | Overall demand and successful delivery |
| Weekly active readers | Distinct linked browser IDs with a completed reading during the trailing seven local calendar days, explicitly including or excluding today in the label | Engaged audience growth |
| Day-7 return rate | Readers first observed completing a reading on cohort day D who complete another on D+7, divided by eligible readers in that cohort | Repeat value; subscription potential |
| Activation | Linked visitors who complete a reading within the selected period / linked `app_opened` visitors in that period; restrict numerator to the same visitor cohort | Whether visits turn into use |
| Readings per reader | Completed linked readings / distinct linked completing readers in the period | Usage intensity and possible credit limits |
| Same-day repeat use | Linked completing readers with 2+ readings that local day / linked completing readers that day | Depth of engagement |
| Popular traditions/spreads | Completed readings grouped by final normalized mode/spread | Product investment priorities |
| Reading completion rate | Started logical reading IDs with a completion / eligible started logical reading IDs in a bounded start cohort | End-to-end generation reliability |
| Attempt outcomes | Distinct attempt IDs, reconciled to completed, failed, interrupted, pending, or unresolved | Transport failures, retries, hard timeouts, collection gaps |
| Reading latency | Median and p95 completed attempt duration, split by tradition/spread and transport | Performance regressions |
| Quantum fallback rate | Distinct `qrng_result` events with `fallback_values > 0` / all distinct `qrng_result` events | Authenticity and source reliability |
| ANU service health | Actual provider attempts by status/reason, latency, and dispatch count | Provider outages, rate limits, and request consumption |
| Cost per completed reading | Estimated attributable provider expense across all attempts in the period / completed readings in that period | Unit economics; disclose timing and coverage limitations |
| Token reporting coverage | Interpretation calls with usable reported usage / all interpretation calls | Whether Gemini cost estimates are trustworthy |

Deduplicate by `event_id` before aggregation. Deduplicate successful readings by
`reading_id`, independently of visitor ID. A transport retry may add attempts
without adding a successful reading. Infer final tradition/spread from finalized
events rather than the early stdout start event, which may have an initial mode.

Stop treating a start as pending only after the deployed reading time limit plus
an ingestion grace period. An unmatched start is unresolved, not automatically
a failure. Right-censor starts near the selected window's end. Show a separate
client-visible completion measure once that event exists; server generation
completion does not prove the result appeared on screen or was read.

Returning readers means first observed in retained data, not first ever. Cohorts
from a partial collection day are excluded. Before seven complete days of
follow-up, display "Collecting baseline" rather than 0% retention.

## Data architecture

1. **Product events:** reuse existing anonymous browser and reading events. Add
   `reading_displayed` to distinguish server completion from client display.
   Defer journal-open, export, and other feature engagement events until the core
   dashboard works. No broad click tracking is needed.
2. **Operational events:** persist content-free backend events even when visitor
   linkage is disabled. Visitor identity stays null for opted-out requests.
   The existing visitor-gated forwarding queue must not gate database collection.
3. **Durable collection:** add a database sink to the existing telemetry module.
   Persist bounded batches at reading start, after the draw, and at terminal
   milestones; do not postpone every write until a streaming request ends.
   Persist visits and client actions through validated Flask endpoints. Use short
   connection/statement timeouts and serverless-compatible connection pooling.
   Keep operational stdout logs as a diagnostic fallback.
   Set one cumulative telemetry latency budget per reading, rather than allowing
   each milestone its own full retry budget. Use short transactions and release
   connections before waiting on ANU or Gemini; never hold a transaction or checked
   out database connection through the streaming response. Validate pool exhaustion
   and total added latency with actual deployed reads/writes before launch.
4. **Event store:** use an append-only `analytics.events` table with a unique
   `event_id`, schema version, event time, ingestion time, environment, nullable
   browser identity, reading/attempt IDs, and strictly allowlisted properties.
   Add indexes for time/environment, reading/attempt IDs, and linked browser/time.
   Insert idempotently so retries cannot inflate counts. Never persist raw
   request bodies, reading text, or arbitrary client properties.
5. **Delivery limits:** verify duplicates, out-of-order events, server hard kills,
   database outages, and connection exhaustion. A failed telemetry write must
   not fail a reading; it must emit a content-free delivery error and expose a
   coverage gap in monitoring. This first version can lose events during database
   outages. A persistent queue/recovery feed is a later addition if needed;
   neither a serverless background thread nor temporary disk is durable retry
   storage. Analytics is unsuitable for billing or enforcing credit balances.
6. **Query layer:** implement shared, parameterized SQL definitions in an analytics
   service module. Authenticated `/admin/api/*` endpoints return compact aggregate
   results. Use bounded date ranges and least-privilege database credentials;
   no browser credentials or arbitrary SQL endpoint. Start with indexed queries.
   Measure query latency before adding caches or scheduled rollups; display data
   freshness and stale/unavailable states explicitly.
7. **Billing:** event-derived costs are estimates; AWS/ANU, Google, Vercel, and
   database-host billing records are the authority for actual charges. Add imports or
   narrowly scoped billing access later; never substitute estimates for invoices.

The first version does not require a log drain or a separate event-processing
platform. Use migrations, production/preview database isolation, explicitly
configured backups, and a restore check. Start with a provisional 90-day event retention policy,
finalized against storage cost and privacy needs. Add longer-lived daily aggregates
before the first expiration only if required; a rollup service is not a v1
dependency. Audience counts and retention requiring raw identities are unavailable
outside their retained window. Do not sum daily unique readers to claim monthly
unique readers. Private saved readings have their own retention policy.

Daily backups provide recovery at backup boundaries, not zero data loss or
point-in-time recovery. Before cloud journals become the primary copy, agree the
acceptable recovery window and test restoration; price finer recovery separately
if needed. Database uptime and backups matter more here than raw storage volume.

## Instrumentation and cost gaps to close

- Add `provider_attempt` records for each actual ANU request dispatch, including
  failures and timeouts. The provider that ultimately serves a draw does not
  reveal all potentially billable calls.
- Add `interpretation_started` and sanitized completion/failure events so token
  coverage has a denominator, including calls that fail before usage is reported.
- Add server-validated internal/test classification so controlled tests can be
  excluded from audience metrics while remaining visible in operational spend.
  Label unidentified bot traffic as a limitation; do not fingerprint visitors.
- Use versioned, dated model prices. Verify the deployed model's pricing before
  calculating costs. Follow provider billing semantics for cached and thinking
  tokens; do not add counters that overlap or equate missing reports with zero.
- ANU publishes US$0.005/request. Show dispatch-based estimates and uncertainty
  for timeouts/failures until reconciled with the actual AWS agreement and bills.
  Number of random values requested is not number of paid API calls.
- Refine the existing report's definitions before reusing it: its visitor count
  currently includes IDs seen on any event, whereas activation uses an explicit
  `app_opened` cohort. Its completed-reading deduplication includes visitor ID;
  the dashboard should use reading ID. Preserve missing token fields as unknown.

## Access and privacy

**Product requirement: readings are private by default.** Collect content-free
usage events for aggregate reporting, never the question, interpretation, exact
draw, or journal notes. The owner dashboard must not offer individual reading
inspection or visitor profiles. Future cloud saving/import requires an explicit
user choice; signing in is not consent to upload a reading or local journal.
Readings are processed by the server and Gemini for generation, so privacy copy
must distinguish processing from analytics storage. See the privacy contract in
DATABASE_PLAN.md. Public sharing always requires a user action.

Select a managed identity provider supporting Google sign-in for the owner,
then use a fixed allowlist of verified account IDs for administrator authorization.
Provider selection and its pricing remain open; database work can proceed before
that choice, but the dashboard must remain inaccessible until login and access
checks are verified. Use the provider's maintained Flask-compatible integration.
Restrict initial enrollment to the owner until customer registration is
intentionally launched.
Protect both `/admin` and every `/admin/api/*` route server-side. An unlisted
URL or a hidden navigation link is not access control. Use secure, HttpOnly session
cookies, safe session expiry, and no public caching of dashboard responses.

Restrict CORS for admin endpoints separately from the public reading API. Return
aggregates only; do not expose visitor identifiers or individual reading content.
Preserve DNT, GPC, and opt-out behavior for audience and engagement analytics.
Operational collection is unlinked and must remain within the content-free
allowlist. Keep replay/autocapture off. Select the database region and explicit
retention/deletion policy during setup. Store connection and sign-in secrets on
the server, use encrypted database connections, and keep backups under the same
access and retention controls.

## Implementation sequence and completion checks

1. **Measurement foundation:** execute the staged Railway deployment below and
   separately select the owner sign-in configuration. Establish product/analytics
   schema boundaries, scoped roles, and stable account/reading identity contracts for later journals.
   Define collection start, timezone, canonical IDs,
   traffic classification, retention, and cost pricebook. Add schema migrations
   and run an ingestion spike. Deliver verified persisted events and documented
   limits, with no dependency on an analytics vendor.
2. **Collection and definitions:** implement minimal new events, the content-free
   operational feed, and shared aggregate definitions. Reconcile a controlled
   set of readings, retries, failures, and opt-outs. Verify duplicate delivery
   cannot inflate counts; database outages must not block a reading. Validate the
   shared SQL against a deterministic event fixture and the refined usage report.
3. **Private dashboard:** implement managed owner login, aggregate API, and one
   overview with the existing usage/health metrics and labeled cost estimates.
   Add the three preset date filters, freshness indicators, and empty states.
4. **Production verification:** test unauthorized HTML/API access, production
   isolation, timezone boundaries, missing data, incomplete cohorts, unpriced
   models, and real reading-to-dashboard updates. Check desktop and mobile.
   Preserve a minimal rollback path that disables collection/dashboard changes
   without affecting reading generation. Acceptance requires verified runtime
   behavior, not only passing builds.
5. **Accounts and saved journals:** reuse the chosen auth system, add private
   product tables and ownership policies, fix the session-state contract, and
   ship confirmed cloud saves plus a safe import of existing local journals.
   Begin with online save/load and simple conflict handling; full offline sync is
   a separate feature. Test account isolation and restore/export/delete behavior.
6. **After a baseline:** use two to four weeks of history to add useful retention
   views and choose alerts. Add comparisons, exports, and engagement events only
   as they answer concrete questions. In-dashboard warnings can ship first; configure email
   or other notifications only after the owner selects recipient and thresholds.
   Revenue, MRR, churn, and paid conversion become relevant after customer billing
   exists; the AWS supplier subscription alone does not supply those metrics.

Expected implementation touches: `telemetry.py`, `app.py`, `oracle_logic.py`,
`quantum_random.py`, `static/analytics.js`, `static/ui.js`, focused admin UI/API
modules, and the existing analytics/report tests. Keep query definitions shared
and instrumented events versioned. Add database migrations and focused persistence
and aggregation tests. No broad public reading UI rewrite is required.

## Railway deployment stages and operating ownership

These stages are planned, not completed. Keep application hosting on Vercel.

1. **Local preparation:** add reviewed PostgreSQL migrations and a Python driver,
   using synthetic events locally. Record the actual Vercel function region and
   select a nearby Railway region. Keep collection off by default without its
   explicit database configuration. Decide the initial resource ceiling and
   review the database, pooler, preview, backup, and egress estimate together.
2. **Isolated staging:** create an Oracle-specific Railway project with separate
   production and staging environments, database services, and volumes. Give each
   distinct credentials. Map Vercel Preview only to staging, Production only to production;
   local tests use disposable local PostgreSQL. Do not copy production journals
   or identifiers into staging. Avoid automatically spawning a paid database per
   preview. If staging is removed between tests, recreate it from migrations and
   synthetic fixtures before the next release.
3. **Connections and roles:** provision a single-node production PostgreSQL
   service with persistent storage. Vercel needs an external endpoint; Railway's
   private hostname is not reachable from the Vercel function. Enable only the
   public endpoint needed for application traffic. Railway documents a TLS-capable
   image and public TCP proxy, with egress charges; verify the selected endpoint
   rather than assuming these settings from a template.
   [PostgreSQL connectivity](https://docs.railway.com/databases/postgresql)
   Require encrypted connections and validate the certificate trust/hostname
   configuration before production. If the default certificate cannot support
   verified TLS, configure a trusted certificate/CA path before launch; do not
   silently disable verification. Verify TLS across both client-to-pooler and
   pooler-to-database hops if pooling is used. Keep credentials in scoped Vercel
   server variables, never browser bundles, logs, or repository files.
   Create separate telemetry insert, dashboard read, migration, and maintenance
   roles; add the product runtime role when cloud journals ship. Runtime roles
   must not own tables, bypass RLS, create schemas, or inherit the bootstrap
   superuser. Test denied operations as well as allowed ones.
4. **Serverless capacity:** the standard PostgreSQL template does not include
   pooling. Evaluate Railway's PgBouncer feature in transaction mode for ordinary
   application queries; migrations use a separate direct connection. Treat its
   resource use as part of the deployment cost.
   [Railway pooling guidance](https://docs.railway.com/guides/connection-pooling-pgbouncer)
   Before choosing limits, measure the actual `max_connections`, role limits,
   expected Vercel concurrency, and per-process driver pools. Reserve capacity
   for maintenance and recovery. Sum server connections across pooler replicas,
   users, and databases; per-role pools can multiply the apparent pool size.
   A driver pool inside each function instance is not a global limit. Load-test
   cold starts, concurrent requests, saturation, reconnects, and timeouts. Direct
   runtime access is acceptable only if a measured/enforced concurrency limit
   fits the database budget; otherwise require the tested pooler. Validate
   transaction-scoped identity and driver prepared-statement compatibility.
5. **Recovery before collection:** enable daily volume backups, verify the first
   successful backup, and rehearse recovery with synthetic data in staging.
   Railway currently retains daily snapshots for six days; snapshots restore
   only within the same project/environment, and wiping a volume removes its
   backups. Keep this limitation in the deletion runbook.
   [Railway volume backups](https://docs.railway.com/volumes/backups)
   Propose a 24-hour recovery-point target and four-hour restore target for v1
   analytics, and measure both in rehearsal. Test grants, migration version,
   event counts, application reconnection, and rollback after restore. Before
   journals become a primary copy, decide a stricter recovery target if needed,
   and evaluate independently retained encrypted exports for project-loss risk.
   Railway offers opt-in PITR with bucket storage and archive-upload costs; it
   requires configuration and verified archive health, not just a Pro plan.
   [Railway PITR](https://docs.railway.com/volumes/point-in-time-recovery)
6. **Production cutover:** apply reviewed migrations once through the migration
   role, then run a bounded deployed ingestion/query test. Confirm preview cannot
   access production and normal roles cannot read product text. Enable collection
   only after timeout, opt-out, duplicate, outage, TLS, and recovery checks pass.
   Reconcile a known event set and record collection start. Enable `/admin` only
   after the separately chosen auth provider passes authorization tests. Keep an
   application rollback that disables the sink without destroying stored data.
7. **Ongoing operation:** name the Oracle operator as owner of database health,
   disk headroom, connection saturation, backup failures, credential rotation,
   and cost review. Record PostgreSQL major version and image policy; test image
   updates and major upgrades in staging with a fresh recovery point and a
   rollback plan. Execute analytics retention with a maintenance role and bounded
   deletes, preserving separately agreed product retention. Rehearse restoration
   quarterly and after material database changes. Before retiring any service,
   identify consumers, settle export/retention needs, remove its credentials from
   deployments, and explicitly verify the intended volume/backup deletion scope.

## Budget and dependencies

Use the existing Railway Pro workspace. Pro's US$20/month minimum includes US$20
of resource usage; only usage above that amount adds resource overage. The
initial Oracle database may fit within existing included usage, but this is not a
fixed-price or zero-incremental-cost guarantee.
[Railway billing](https://docs.railway.com/pricing/understanding-your-bill)

Before provisioning, refresh the workspace forecast after the separately
requested idle-service cleanup. Include database and pooler RAM/CPU, volumes,
backup storage, Vercel-to-Railway traffic, and any staging or PITR resources.
Use the first 24–72 hours of measured usage to revise the monthly estimate and
review it again after a week. Set a billing alert below the agreed monthly ceiling;
review any hard-limit shutdown behavior before applying it to production.
Do not promise savings until the removed services and their retained storage are
verified. Keep private account/project cost inventories outside this repository.

The earlier 25-100 MB per 10,000 readings estimate covered only hypothetical raw
telemetry. It was not a benchmark and excluded private reading text, indexes,
database overhead, and backups. Measure representative records and actual query
load once the foundation exists. There is no current evidence requiring a
separate analytics database or warehouse.

We own database operation as well as migrations, authorization rules, metric
definitions, and application integration. Railway provides the infrastructure and
template; that does not transfer recovery, security, or upgrade decisions to a
fully managed database team. Measure load before adding rollups or a queue.

Implementation still needs the region/resource selection, tested TLS/pooling
configuration, recovery rehearsal, scoped server credentials, and managed owner
auth choice. Those are deployment gates, not completed setup. Actual billing
integrations can follow separately; the initial dashboard should clearly mark
those totals as unavailable until connected.

## External references checked during planning

- [Vercel runtime logs and retention](https://vercel.com/docs/logs/runtime)
- [ANU published pricing](https://quantumnumbers.anu.edu.au/pricing)
- [Gemini provider pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Railway database operating responsibilities](https://docs.railway.com/databases)
- [Railway PostgreSQL connectivity](https://docs.railway.com/databases/postgresql)
- [Railway connection pooling](https://docs.railway.com/guides/connection-pooling-pgbouncer)
- [Railway backups](https://docs.railway.com/volumes/backups)
- [Railway point-in-time recovery](https://docs.railway.com/volumes/point-in-time-recovery)
- [Railway billing](https://docs.railway.com/pricing/understanding-your-bill)
- [PostgreSQL schema privileges](https://www.postgresql.org/docs/current/ddl-schemas.html)
- [PostgreSQL row-level security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

These are current planning references, not a guarantee of future prices, data
retention, delivery semantics, or the terms of the user's particular agreement.
