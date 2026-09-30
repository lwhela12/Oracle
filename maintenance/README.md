# Railway retention service

Railway no longer accepts `railway.json` or `railway.toml` for this service.
Configure the retention worker directly on the isolated Railway service, using
the dashboard or the service-instance API, with these settings:

- `builder`: `RAILPACK` (the service-instance API enum; Railway reports the
  resulting deployment as `DOCKERFILE` because `dockerfilePath` is set)
- `dockerfilePath`: `maintenance/Dockerfile` (with the repository root as the
  build context)
- `multiRegionConfig`: Virginia region `us-east4-eqdc4a`
- `cronSchedule`: `0 8 * * *` (08:00 UTC daily)
- `startCommand`: `python scripts/maintain_analytics.py`
- `restartPolicyType`: `NEVER`

Set only these service variables:

- `ORACLE_MAINTENANCE_DATABASE_URL`: the secret connection URL for the
  production maintenance login. It must use `sslmode=verify-full`, the bundled
  CA at `/app/certs/oracle-production-root.crt`, and a numeric `hostaddr` when
  `host` is a DNS name.
- `ORACLE_DATABASE_ENVIRONMENT=production`
- `VERCEL_ENV=production`

Do not put the migration, writer, reader, or administrator credential on this
service. Apply migration `20260929_0002` before enabling the schedule.

The image installs the only non-standard Python dependency used by the job,
`psycopg[binary]`, and copies `database.py`, the maintenance script, and the
certificate bundle into `/app`. The job exits after each run; a nonzero exit is
a sanitized configuration or database failure.
