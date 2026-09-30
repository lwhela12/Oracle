# Owner dashboard

Implemented locally September 30, 2026; not yet deployed. The dashboard route is `/admin`; its only data
endpoint is `/admin/api/report?period=today|7d|30d`. It is a live aggregate view of
Railway analytics, not a reading browser. Google login configuration and a
verified owner subject are required before anyone can access it.

## Google sign-in

Google Cloud project `quantum-oracle-510213` (Quantum Oracle) was created under
`whelanpartners.com` on September 30 with the user's explicit approval to link
the existing My Billing Account. The authentication branding form is prepared
as Quantum Oracle Owner Dashboard with an Internal audience and the designated
owner email for support/contact. The user accepted Google's API Services User Data Policy. The Web application
client Oracle Owner Dashboard is created, with the production callback below
and `http://127.0.0.1:5059/admin/auth/callback` for local verification. Real Google
sign-in verified the designated account; an empty allowlist denied access, then
the explicitly pinned verified subject allowed access. Production-only Vercel
variables are installed as sensitive values; preview has no dashboard credentials.

Use a Google OAuth **Web application** in the intended Google Cloud project.
Register the exact production redirect URI:

```
https://www.qoracle.app/admin/auth/callback
```

Use the canonical `www` host because `qoracle.app` redirects there. This is a
server-side authorization-code flow using Authlib, OIDC state/nonce checks and
PKCE. Only `openid email` scopes are requested. No Drive, Gmail, or other account
data is requested. Google stores the account credentials; Oracle does not build
password storage or recovery.

Set these Vercel server variables, separately for production and any preview:

| Variable | Purpose |
| --- | --- |
| `ORACLE_ADMIN_ORIGIN` | Exact `https://www.qoracle.app` for production; a fixed protected preview URL for preview |
| `ORACLE_ADMIN_GOOGLE_CLIENT_ID` | Google OAuth Web client ID |
| `ORACLE_ADMIN_GOOGLE_CLIENT_SECRET` | Google OAuth client secret; sensitive |
| `ORACLE_ADMIN_SESSION_SECRET` | Independent random secret of at least 32 characters; sensitive |
| `ORACLE_ADMIN_EXPECTED_EMAIL` | Owner's verified email; restricts enrollment display only |
| `ORACLE_ADMIN_GOOGLE_SUBJECTS` | Comma-separated immutable Google account IDs explicitly authorized as owner |
| `ORACLE_REPORT_DATABASE_URL` | The reporting-only login, using verified TLS and the environment's bundled CA |
| `ORACLE_DATABASE_ENVIRONMENT` | Must match `VERCEL_ENV` and the protected database identity |

Leave the subject allowlist empty during the first owner sign-in. Successful
Google verification shows the user's account ID to that browser, but denies the
dashboard. For the designated verified owner account, explicitly set that ID in
`ORACLE_ADMIN_GOOGLE_SUBJECTS`, redeploy, and sign in again. Email alone never
grants dashboard access. Removing a subject revokes its existing sessions on the
next request. Do not paste secrets into source code, chat, or log output.

Apply Alembic migration `20260930_0003` with the separate migration connection.
It grants the existing report-reader group access only to the protected boolean
environment-check function; it does not grant writes or product-schema access.
Deploy only the reporting login to the dashboard server, never the administrative
or maintenance login. Production and preview must keep separate credentials.

Sessions are signed, HttpOnly, Secure, SameSite=Lax cookies scoped to `/admin`.
They expire after at most one hour, capped by Google's token expiry. Provider
tokens are not stored in cookies. Admin HTML/API/errors are not cacheable, cannot
be framed, and have no cross-origin API access. Logout requires a CSRF-protected
POST. Missing configuration fails closed.

## Metrics and limits

The report uses public traffic only, in the configured database environment.
Today, 7 days, and 30 days are Pacific calendar windows through the current time,
including the partial current day. Tests/internal traffic are excluded.

- Completed requests deduplicate reading IDs across transport retries. Browser
  counts refer to linked anonymous browsers with a completion, not people.
- Completion rate uses starts at least 15 minutes old, with a completion by the
  report time. Recent starts are excluded rather than treated as failures.
- Attempt outcomes reconcile terminal events. Unfinished starts are pending for
  15 minutes, then unresolved. Missing telemetry is not proof of failure.
- Duration percentiles cover completed attempts with reported duration.
- Quantum fallback counts recorded draw batches, not billed provider requests.
- Token totals preserve unknown and partially reported fields. They are not a
  billing ledger. Dollar estimates remain unavailable until pricing and request
  instrumentation support them; hosting bills are not inferred from tokens.
- Collection is best effort and raw events have a 90-day retention policy. The
  earliest retained event is not necessarily a user's first-ever visit. No
  retention-cohort, revenue, or customer-subscription claim is made.

Queries are parameterized and aggregate inside PostgreSQL; no raw event,
reading, attempt, or visitor identifiers are sent to the browser. The report
runs in a read-only repeatable-read transaction with database timeouts and fixed
periods. A database failure shows an unavailable state, never fabricated zeros.

## Local validation and release

Use the existing unittest suite plus the optional disposable-PostgreSQL tests.
`ORACLE_TEST_ADMIN_DATABASE_URL` must point only to a local test cluster: those
tests create/drop their own databases and roles. Never use production for them.

For local Google testing only, use an explicit `http://127.0.0.1:<port>` origin
and `ORACLE_ADMIN_LOCAL_HTTP=1`, off Vercel. This permits a local OAuth redirect;
it does not bypass authentication. Register the local callback in Google first.

Before release, verify unauthorized HTML/API access, a real owner Google login,
a different Google account's denial, logout and session expiry, source totals,
all period controls, desktop/mobile layout, and database-unavailable behavior.
Protect the preview deployment using Vercel's existing controls. Test production
with its reporting role after promotion and record the deployment separately.

### Validation record, September 30, 2026

- All 104 Python tests passed, including eight integration tests against a
  disposable UTF-8 PostgreSQL 17 cluster. Authentication tests validate signed
  synthetic Google tokens through Authlib with mocked provider transport.
- Production reporting-role queries succeeded for Today, 7 days, and 30 days.
  The retained public snapshot reconciled to three completed readings and one
  linked browser; no reading content or row identifiers were returned.
- Local browser verification used those aggregate snapshots and a temporary
  harness outside the repository. Date controls, refresh, unavailable-state
  recovery, logout, desktop layout, and a 390-pixel mobile viewport passed.
  This does not establish a real Google login or a deployed dashboard.
- Real Google sign-in and owner enrollment passed locally, and production Vercel
  credentials are installed. Deployed authentication checks remain pending. The chosen owner account is
  `lucas@whelanpartners.com`; its email alone grants no access.

References: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
and [Authlib Flask integration](https://docs.authlib.org/en/latest/oauth2/client/web/flask.html).
