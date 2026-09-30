# Database foundation: local setup and release checklist

The first implementation supports the five existing content-free telemetry event
types: app visits, reading starts and finishes, QRNG results, and interpretation
token usage. Database collection is disabled when `ORACLE_DATABASE_URL` is empty.
It does not create customer accounts, cloud journals, or an admin dashboard.

## Local setup

Use Python 3.12 and a disposable PostgreSQL database. Install the pinned database
dependencies alongside the application's existing dependencies:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Supply `ORACLE_MIGRATION_DATABASE_URL` through a local secret environment. It must
identify the intended database with an administrative role allowed to create
schemas and group roles. Set `ORACLE_DATABASE_ENVIRONMENT=local`; leave
`VERCEL_ENV` unset for local development. Then run:

```sh
.venv/bin/alembic upgrade head
```

Migrations are explicit commands. Importing Flask and serving requests never
modifies the schema. Alembic tracks the installed revision. The baseline creates
`analytics.events`, an environment identity marker, and an empty `product` schema
reserved for later account features.

Create separate, non-superuser login roles using the database administrator.
Give the application login membership in `oracle_telemetry_writer` and the future
reporting login membership in `oracle_report_reader`. Grant the retention-job
login only `oracle_maintenance`. These are NOLOGIN group roles; they do not supply
credentials. Use separate credentials for each environment. Set a measured
connection limit on login roles before deployment.

Set `ORACLE_DATABASE_URL` to the telemetry login connection, not the migration
connection. `ORACLE_TRAFFIC_CLASS` accepts `public`, `internal`, or `test`; use
`test` for synthetic runs. Keep administrative credentials out of the deployed
application environment.

The writer can insert events but cannot select, update, or delete them. The
reader can select events; the maintenance role can select and delete events.
None receives access to the reserved product schema. Future migrations must
explicitly grant access to any new objects.

## Verification

The ordinary suite includes configuration, validation, request integration, and
failure-path checks:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/test_analytics.cjs
node tests/test_journal_identity.cjs
```

To also run PostgreSQL integration tests, set
`ORACLE_TEST_ADMIN_DATABASE_URL` to a **disposable local test cluster** before
running the Python suite. The test creates and removes its own database and
temporary login roles. The three shared group roles may remain in that cluster.
Never point this test at production. Without the variable, PostgreSQL tests are
explicitly skipped; a passing ordinary suite alone does not verify migrations.

Local validation on September 29, 2026: 61 Python tests passed, including five
tests against PostgreSQL 17.9, plus the two JavaScript analytics/journal checks.
The PostgreSQL checks exercised migrations, event deduplication, constraints,
role isolation, the environment marker, lock timeout, and a Flask streaming
request with provider calls replaced by synthetic data. External providers and
the Vercel-to-Railway network were not part of these tests.

## Release connection check

For a configured release environment, set `ORACLE_REPORT_DATABASE_URL` to the
separate read-only login alongside the writer URL and explicit matching
`VERCEL_ENV` / `ORACLE_DATABASE_ENVIRONMENT`, then run:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_database_release.py
```

This command checks TLS sessions and scoped privileges, inserts one synthetic
`traffic_class=test` event twice, verifies only one row exists, and prints a
sanitized JSON result. It retains that fixture for audit. It also rejects
unexpected transitive role memberships and product-schema access. Live Railway
security and deduplication checks passed, but the local network exceeded the
500 ms budget. Real same-region Vercel Preview readings subsequently persisted
all expected events under the unchanged budget, and a blocked-write reading
continued successfully. See
[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for measurements and recovery evidence.

## Collection behavior

Events are validated against event-specific property names, types, enums, and
size limits, with a second constraint in PostgreSQL. Delivery deduplicates only
identical event IDs. No question, generated interpretation, journal text, email,
IP address, or raw request body belongs in the event payload.

DNT, GPC, and analytics opt-out suppress visitor linkage and app-visit collection.
Operational events can still be written without a visitor ID. Existing optional
PostHog forwarding remains independently configured.

Requests flush after the route resolves mode/spread (before the draw), after the
draw, and at completion. Pre-routing errors flush start and failure together.
Each request has a
cumulative 500 ms database delivery budget and batches are capped at 50 events.
Connections close between writes, before provider calls. Delivery failure logs
only sanitized metadata, disables further database attempts for that request,
and lets the reading continue. There is no durable retry queue: an outage or
process termination can lose events. This is measurement, not a billing ledger.

New readings return a server-issued canonical UUID, UTC creation time, and
content-format version in both response transports, even with analytics disabled.
The browser journal retains this metadata and avoids duplicate saves of the same
canonical ID. Existing browser entries remain readable. A new draw gets a new
ID; generation retries are not durable idempotent operations.

## Before Railway rollout

1. Create isolated staging and production databases with separate volumes and
   credentials. The configured environment, Vercel runtime environment, and
   database identity marker must agree. A Vercel Preview deployment uses
   `preview` in all three places, even if the Railway environment is named
   `staging`. Local rehearsal of preview migrations must explicitly set
   `VERCEL_ENV=preview`.
2. Verify external endpoint TLS and certificate trust. Production and Preview
   connections require `sslmode=verify-full`; do not weaken this requirement to
   work around a certificate or hostname mismatch. The runtime connection must
   also supply a numeric `hostaddr` when `host` is a DNS name. Retain `host` for
   certificate hostname verification. Resolve the address during deployment and
   refresh it when the endpoint changes; a stale address disables collection
   rather than delaying a reading for DNS. Psycopg's threaded DNS resolver cannot
   be bounded by the request timeout, so runtime configuration rejects that path.
   Local Unix sockets and literal IP hosts do not need this extra parameter.
   Administrative migration connections can resolve DNS outside a request.
3. Measure actual Vercel-to-Railway latency, connection saturation, and the
   cumulative timeout under healthy and stalled connections. The local tests do
   not prove deployed latency or capacity. Add a pooler only if measurement
   requires it, and verify TLS on each hop.
4. Enable backups and perform a restore rehearsal. Record the collection start,
   recovery results, and expected coverage gaps. Add the bounded 90-day retention
   job and disk/connection/cost monitoring.
5. Reconcile synthetic and real reading events in staging, including opt-out,
   retries, streaming interruption, and database outage, before enabling the
   production writer secret.

Disable collection by removing `ORACLE_DATABASE_URL`. Preserve the database and
its history during rollback; do not downgrade a live database to turn analytics
off. Provider-dispatch/display events, reporting queries, owner authentication,
the dashboard, and cloud journal persistence remain later work.

## Production retention job

Deploy the separate image in `maintenance/Dockerfile`. Railway's former Config
as Code files are deprecated, so configure the isolated retention service
directly through Railway's dashboard or service-instance API:

- `builder=RAILPACK`, `dockerfilePath=maintenance/Dockerfile`, repository root
  as the build context. `RAILPACK` is the service-instance API enum; with this
  Dockerfile path, Railway reports the resulting deployment as `DOCKERFILE`.
- `multiRegionConfig` set to Virginia region `us-east4-eqdc4a`
- `cronSchedule=0 8 * * *` (08:00 UTC daily)
- `startCommand=python scripts/maintain_analytics.py`
- `restartPolicyType=NEVER`

The complete service checklist is in `maintenance/README.md`. Give this service
only the secret `ORACLE_MAINTENANCE_DATABASE_URL`, plus
`ORACLE_DATABASE_ENVIRONMENT=production` and `VERCEL_ENV=production`. The
connection must use the maintenance login, certificate verification, and the
certificate path `/app/certs/oracle-production-root.crt`. Do not give the
service a migration, writer, reader, or administrator credential. Keep the
maintenance credential out of the public application. Apply migration
`20260929_0002` before enabling the schedule. The job exits after each run.

The job deletes events older than 90 days, at most 5,000 rows and approximately
20 seconds per invocation by default, and reports bounded backlog counts,
database size, TLS state, and deleted counts without event contents. Review
failed cron runs and persistent backlogs; no external alert integration is
configured yet. A nonzero exit indicates a sanitized configuration or database
failure. This job does not delete database backups.
