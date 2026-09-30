# Railway database deployment

## Dashboard preparation, September 30, 2026

Applied migration `20260930_0003` to staging and production. It grants the scoped
report-reader group execution of the boolean environment-check function only.
Live production checks confirmed event SELECT access, denied INSERT access, and
no product-schema access. All three reporting periods returned serializable
aggregate results through the production reader with verified TLS.

The dashboard source is locally verified but not deployed. Google OAuth setup and local
owner enrollment passed. The production dashboard credentials are installed as
sensitive Vercel variables; deployed authentication checks remain pending. See [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).
The production release record below describes the earlier foundation release.

## Production release, September 29, 2026

The user approved production deployment, scoped credential installation, and a
snapshot recovery rehearsal. The verified candidate was promoted to `qoracle.app`
and `www.qoracle.app`: `dpl_4g8cmceyUXeXfMNZRvGSKypdQkE1`,
https://oracle-nmdarpzlb-lwhela12s-projects.vercel.app (Vercel `iad1`).
The owner dashboard is still planned, not implemented. Analytics contain usage
metadata only; questions, draws, interpretations and journal text are excluded.

### Database and recovery

- Database service: `oracle-production-db`,
  `8b235d76-45f8-49b0-84f3-ece1453481e0`, environment
  `16c6e792-aaaf-4ad2-9b2a-113b8190c563`.
- PostgreSQL 18.6, Virginia, 1 vCPU / 500 MB caps. Alembic head
  `20260929_0002`, protected identity `production`. Separate writer, reader and
  maintenance logins have connection limits 12/4/2.
- TLS 1.3 verified; wrong hostname and wrong CA rejected. Public CA:
  `certs/oracle-production-root.crt`, SHA-256
  `FD:77:AB:B0:EC:12:1F:0D:B4:EA:2A:29:72:6D:8A:EE:89:F0:5D:CC:BA:AA:FA:EB:76:24:58:8D:6A:F6:CB:3D`.
  Host SAN `postgres--vkv.railway.internal`; external proxy
  `mainline.proxy.rlwy.net:28478`, resolved address `66.33.22.234`.
  Certificate expires December 28, 2028 at 03:36:18 UTC.
- Snapshot `d03ca465-0fc0-4768-b6c9-b6cd15dcd530`, created September 30
  03:43:40 UTC, was restored before public collection. Schema revision,
  production marker, existing logins and two pre-backup fixtures survived;
  the post-backup fixture was absent. TLS trust remained valid.
- Active restored volume: `eeb36906-3a29-4190-9cbb-190fae2bea40`, instance
  `2873ea65-e01b-46e2-8821-e9710eb6a09b`. Daily backups were explicitly enabled
  on this replacement volume. Active database deployment after restore:
  `f1c7640e-a23d-42f0-8c87-fb96e6280eaf`.
- Original detached volume `becda9aa-ec7c-40fc-a7f4-5840d1f17ff0` is retained
  as a rollback copy with synthetic data only. It incurs storage cost until
  deliberately removed. Point-in-time recovery is not enabled.

### Retention and credential separation

- Isolated service `oracle-analytics-retention`,
  `85efb477-5b96-4a4d-8994-cc7ef1975b0e`, deployment
  `284b91d3-2fa5-4e03-83da-150605388f61`, Virginia.
- Configured through the Railway API with `builder=RAILPACK` and
  `dockerfilePath=maintenance/Dockerfile`; the resulting manifest reports
  `DOCKERFILE`. Deprecated `railwayConfigFile` was rejected and removed from
  the repository. See `maintenance/README.md` for the direct settings.
- Runs daily at 08:00 UTC, restart policy `NEVER`. A manual deployed execution
  at 03:51:41 UTC September 30 finished in two seconds, status `ok`, TLS 1.3,
  database size 8,050,367 bytes, no expired backlog; job elapsed time 76 ms.
- A separate live fixture test deleted a 91-day-old event, preserved an
  89-day-old event, and respected the one-row batch cap. Default limits are
  5,000 deleted rows and approximately 20 seconds per run, fixed 90-day cutoff.
- Vercel holds only the insert-only writer secret. The maintenance service holds
  only its scoped maintenance secret. Reader/admin secrets are not deployed to
  either application. Vercel settings: production identity, public traffic class,
  analytics enabled. CA paths are `/var/task/certs/oracle-production-root.crt`
  for Vercel and `/app/certs/oracle-production-root.crt` for the job.
- Monitor Railway failed cron runs and backlog output. External alerting and
  larger capacity/load testing remain follow-up work.

### Production candidate checks

- Synchronous number reading: HTTP 200, 11.21 seconds, all four expected events;
  ANU quantum source with zero fallback values. Canonical reading ID matched.
- Streamed tarot reading with GPC: HTTP 200, 13.64 seconds, completed; all four
  operational events persisted with null visitor IDs. Canonical ID matched.
- GPC visit returned 204 and created no event. Four concurrent ordinary visits
  returned 204 and each persisted one event (HTTP 0.25–0.38 seconds).
- Event ingestion lag: cold first start 326 ms; subsequent reading events
  33–43 ms. The application's cumulative database budget remains 500 ms.
  Local Mac administrative role checks used a separate 3-second budget.
- The 12 known synthetic candidate events were classified as `test` traffic so
  they do not contribute to production business metrics. Role/deduplication and
  recovery fixtures also use test traffic.
- Regression suite: 81 Python tests discovered, 76 passed, 5 optional disposable
  PostgreSQL tests skipped; JavaScript analytics/journal checks passed. Live
  database, recovery and deployment checks above are additional evidence.
- Analytics remain best effort; database failure does not prevent a reading and
  can lose events. This release does not establish billing-grade completeness or
  larger-scale capacity. Privacy changes use a fresh Gemini chat per generation.

## Staging release record

September 29, 2026. Staging migrated and the protected Vercel Preview is collecting
test analytics. Database security, logical recovery, real reading reconciliation,
privacy opt-out, and a blocked-write resilience check passed. Production rollout
and the remaining operational checks below are separate work.

## Resources

- Workspace: `lwhela12's Projects`
- Project: `oracle` (`93406989-25d5-4534-ace0-0b2e7545abdd`), private
- Staging environment: `f964a706-4f11-416b-aab9-cc1cdb06503c`
- Empty production environment: `16c6e792-aaaf-4ad2-9b2a-113b8190c563`
- Staging service: `Postgres` (`7281907f-ae98-40a9-a046-db9a8d90b07c`)
- Initial volume: `1075c6d9-619a-41f2-a881-8a8ed51246e2` (region migration may replace it)
- Image: `ghcr.io/railwayapp-templates/postgres-ssl:18`, supplied by Railway
- Region: US East (Virginia); migration completed and service reports Online /
  Active. This matches existing Vercel `iad1` functions.
- Initial resource limits: 1 vCPU, 500 MB memory. These are caps, not reservations
  or a guaranteed bill; measure usage and increase memory if necessary.
- Daily volume backups enabled; Railway UI states six-day retention.
  Schedule was rechecked after region migration; the next backup is scheduled.
  First manual volume backup completed at 16:58 Pacific (UI reports 871 MB).
  Logical restore was verified separately; volume snapshot restore is not yet tested.
  Point-in-time recovery is off.
- Public TCP endpoint: `zephyr.proxy.rlwy.net:47023`; address resolved for this
  release: `66.33.22.227`. Certificate-verified connections are working.

The local foundation suite used PostgreSQL 17.9; migrations and logical recovery
were also verified against this deployed PostgreSQL 18.6 instance. Do not change
a populated cluster's major image tag as an in-place downgrade.

## Verified TLS configuration

The official image currently issues its own CA and server certificate. Its
server SANs include `localhost` and the private Railway domain, rather than the
external TCP proxy hostname. Inspect the actual deployed certificate before
using these assumptions. Sources:
[certificate initialization](https://raw.githubusercontent.com/railwayapp-templates/postgres-ssl/main/init-ssl.sh),
[startup and renewal](https://raw.githubusercontent.com/railwayapp-templates/postgres-ssl/main/wrapper.sh).

Export only the public CA over the authenticated Railway HTTPS Console. Never
export the server or CA private keys. The deployed public certificate was read
from this confirmed path:

```sh
cat /var/lib/postgresql/data/certs/root.crt
```

Saved public CA: `certs/oracle-staging-root.crt`. SHA-256 fingerprint:
`18:99:37:B6:19:72:3A:07:91:3D:BC:A1:2B:07:AF:87:25:8B:36:60:B4:AA:E1:DF:55:18:7A:AB:6E:69:A0:2B`.
Actual server SANs: `localhost`, `postgres.railway.internal`. CA and server
certificate validity: September 29, 2026 to December 27, 2028 (23:42:30 UTC).
CLI authorization is verified. SSH's unknown host key was not accepted; the
temporary Railway SSH key was removed and its isolated agent stopped.

Configure `host` as the actual certificate DNS SAN, `hostaddr` as the resolved
public TCP proxy IP, `port` as the proxy port, `sslmode=verify-full`, and
`sslrootcert` as the bundled public CA path. Libpq connects to `hostaddr` while
authenticating `host`; the private DNS name does not need external resolution.
[PostgreSQL connection parameters](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS).

Use `preview` for the database identity marker and both runtime environment
settings because this staging database will serve Vercel Preview. Keep separate
admin, writer, reporting, and maintenance credentials. Only the scoped writer
belongs in the public application's server environment.

Before enabling collection, prove positive TLS connection and query results,
verify `pg_stat_ssl`, and test that a wrong hostname and wrong CA both fail.
Then measure actual preview requests against the cumulative 500 ms write budget.

The official image currently regenerates its CA during certificate renewal.
Coordinate client trust replacement before renewal; record certificate expiry
and fingerprint after export. Resolve and refresh the public proxy address at
deployment and after endpoint changes. Do not weaken certificate verification
to recover from either mismatch.

## Completed staging checks

- PostgreSQL 18.6, Alembic revision `20260929_0001`, identity `preview`.
- TLS 1.3 verified with `verify-full`; wrong hostname and wrong CA rejected.
- Separate writer/reader/maintenance logins created with connection limits
  12/4/2. Writer cannot read/delete events or access product; reader cannot
  delete events. Transitive role memberships contain only each intended group.
- Environment mismatch rejected. Same event inserted twice yields counts 1/0.
- Local Mac-to-Virginia 500 ms write check **failed by timeout**. A separate
  administrative 3-second-budget check passed (two writes took 2411 ms).
  The application budget remains 500 ms. This does not establish Vercel latency.
- PostgreSQL 18 `pg_dump -Fc` and `pg_restore --exit-on-error` restored a single
  synthetic test event to `oracle_restore_fixture`. Source and restored event
  hashes, event count, table grants, and migration revision matched.
  Event hash: `c38a5d3d7d68cde08f943f4d1ce892822ec715a5218c2c49bc6c6924ba53e43d`.
  Dump SHA-256: `d1803dd3ae1df45e2e1f4077dfaa521201898daed95549f513b02d68152ab7f3`.
  Independent downloaded copy: `~/Downloads/oracle-staging-fixture.dump` (13,897
  bytes). It contains synthetic data only and no login passwords. This rehearsal
  restores into the same cluster; separate-cluster role bootstrap remains untested.
- Source database size at check: 8,050,367 bytes; server max_connections 500;
  9 sessions observed. Load capacity and memory under load are not yet measured.
- Final local regression run: 64 Python tests passed, 5 local PostgreSQL tests
  skipped (69 discovered); JavaScript analytics and journal checks passed.
  Live staging checks listed above were separate from that unit-test run.

The first empty-schema restore database `oracle_restore_rehearsal` and the
fixture restore database are retained in staging for audit. Neither is used by
the application. Remote `/tmp` dump files are ephemeral; the downloaded copy is
independent of the container.

## Remaining acceptance checks

- Measure PostgreSQL health and memory under load; platform Online is verified.
- Broaden concurrency/connection-capacity measurements beyond four visits.
- Exercise deployed client interruption and provider retries; the local suite
  covers interrupted streams, but deployed interruption behavior is not established.
- Exercise volume-snapshot recovery separately before relying on it operationally.
- Record measured usage, connection capacity, and recovery results before production.
- Add the 90-day retention job, monitoring, and production database before enabling
  public collection. The owner dashboard and cloud journals are later slices.

## Protected Preview release

User explicitly approved the staging writer credential transfer. It is stored as
a sensitive Vercel Preview environment variable in project `oracle`; administrative,
reporting, and maintenance credentials were not deployed. Preview-wide settings:
`ORACLE_DATABASE_ENVIRONMENT=preview`, `ORACLE_TRAFFIC_CLASS=test`, and
`ORACLE_ANALYTICS_ENABLED=1`. The writer's CA path is
`/var/task/certs/oracle-staging-root.crt`. All future Preview deployments inherit
these staging settings until removed; production settings were not changed.

- Deployment: `dpl_2qWYeaXenS9e5fn7g1jyJZpUntrd`, Ready, function region `iad1`.
- URL: https://oracle-imak8yihz-lwhela12s-projects.vercel.app
- Unauthenticated requests redirect to `vercel.com` (302); protected calls used
  the signed-in `vercel curl` workflow. Deployment protection remains enabled.
- Source uploaded directly from the local working tree. No commit or push was
  performed, so a Git deployment must include these new files before replacing it.
- Synchronous number reading: HTTP 200 in 10.06 s; four expected database events
  (`reading_started`, `qrng_result`, `interpretation_usage`, `reading_finished`).
  Canonical ID matched the response. Reading ID:
  `2298c854-75a2-49ff-9698-af6342073c72`.
- Streamed tarot reading with `Sec-GPC: 1`: HTTP 200 with done event in 12.65 s;
  all four operational events persisted with null visitor IDs. Canonical ID
  matched stream metadata. Reading ID: `98127694-5f73-464c-b611-807cb9f48670`.
- Event timestamp-to-ingestion latency: first start 376 ms; remaining sync events
  33–43 ms; streamed events 34–39 ms. These are ingestion-lag observations, not
  isolated transaction timing. The cumulative 500 ms application write budget was
  unchanged and all expected events arrived for both tested readings.
- Ordinary visit returned 204 and inserted one event; subsequent GPC visit returned
  204 without inserting another event for that visitor.
- Four concurrent visits all returned 204 and persisted one event each. Ingestion
  lag was 32–246 ms; total HTTP time was 0.24–2.77 s, including a slower invocation.
  This is a small smoke test, not a capacity or latency-percentile guarantee.
- Resilience: held an exclusive lock on staging `analytics.events`, then issued
  one number reading. It returned HTTP 200 with a canonical ID in 12.02 s while
  no analytics rows persisted for its reading ID. Logs show one sanitized delivery
  failure, then normal provider work and completion. The start-to-QRNG interval
  minus logged QRNG duration was approximately 502 ms, consistent with the 500 ms
  database deadline plus small overhead. The lock was released after the request.
  Reading ID: `181f4e02-7d11-441f-af0c-544ae65a3157`.

Database delivery is best effort. The blocked-write test deliberately lost analytics;
it does not establish durable retry or billing-grade completeness.

## Privacy follow-up after Preview acceptance

User confirmed the Preview showed no regressions and required private readings
by default, with usage/aggregate collection only. The local source now removes
the process-local Gemini conversation cache; each generation uses a fresh chat
even if a session ID is reused. The analytics allowlist is unchanged and excludes
reading content; regression coverage now explicitly checks questions, prompts,
interpretations, journal text, exact draws, and response text are rejected.
Database/dashboard plans require explicit opt-in for any future cloud saving.

These follow-up changes have not been redeployed to the Preview URL above or to
production. Local validation: 66 Python tests passed, 5 PostgreSQL tests skipped
(71 discovered); JavaScript analytics and journal tests passed.

Daily backup scheduling alone does not prove a usable restore. See Railway's
[backup and restore guide](https://docs.railway.com/guides/postgres-backups-restores).
