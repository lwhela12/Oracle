"""Create the analytics boundary, append-only events, and scoped group roles."""

from alembic import op
import os
import sqlalchemy as sa


revision = "20260929_0001"
down_revision = None
branch_labels = None
depends_on = None


_ROLES = ("oracle_telemetry_writer", "oracle_report_reader", "oracle_maintenance")


def upgrade() -> None:
    for role in _ROLES:
        op.execute(f"""
        DO $block$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                CREATE ROLE {role} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;
        END
        $block$
        """)

    op.execute("CREATE SCHEMA analytics")
    op.execute("CREATE SCHEMA product")
    op.execute("REVOKE ALL ON SCHEMA analytics FROM PUBLIC")
    op.execute("REVOKE ALL ON SCHEMA product FROM PUBLIC")

    op.execute(r"""
    CREATE FUNCTION analytics.event_properties_valid(event_name text, p jsonb)
    RETURNS boolean
    LANGUAGE plpgsql
    IMMUTABLE
    STRICT
    AS $function$
    DECLARE
        key text;
        value_number numeric;
        allowed text[];
    BEGIN
        IF jsonb_typeof(p) <> 'object' OR pg_column_size(p) > 4096 THEN
            RETURN false;
        END IF;

        IF p ? 'mode' AND (
            jsonb_typeof(p->'mode') <> 'string' OR
            p->>'mode' <> ALL (ARRAY['tarot','runes','iching','number','oracle','unknown'])
        ) THEN RETURN false; END IF;
        IF p ? 'spread' AND (
            jsonb_typeof(p->'spread') <> 'string' OR
            p->>'spread' <> ALL (ARRAY['default','3-card','yes-no','5-card','celtic','norns',
                                        'single','five-cross','thor-hammer','nine-worlds'])
        ) THEN RETURN false; END IF;
        IF p ? 'transport' AND (
            jsonb_typeof(p->'transport') <> 'string' OR
            p->>'transport' <> ALL (ARRAY['sync','stream'])
        ) THEN RETURN false; END IF;

        FOREACH key IN ARRAY ARRAY['duration_ms','http_status','requested','fallback_values',
                                    'input_tokens','output_tokens','thinking_tokens','cached_tokens','total_tokens']
        LOOP
            IF p ? key THEN
                IF jsonb_typeof(p->key) <> 'number' OR (p->>key) !~ '^[0-9]+$' THEN
                    RETURN false;
                END IF;
                value_number := (p->>key)::numeric;
                IF value_number > 100000000 THEN RETURN false; END IF;
                IF key = 'duration_ms' AND value_number > 3600000 THEN RETURN false; END IF;
                IF key IN ('requested','fallback_values') AND value_number > 1024 THEN RETURN false; END IF;
                IF key = 'http_status' AND NOT value_number BETWEEN 100 AND 599 THEN RETURN false; END IF;
            END IF;
        END LOOP;

        IF p ? 'outcome' AND (jsonb_typeof(p->'outcome') <> 'string' OR
            p->>'outcome' <> ALL (ARRAY['completed','failed','interrupted']))
        THEN RETURN false; END IF;
        IF p ? 'source' AND (jsonb_typeof(p->'source') <> 'string' OR
            p->>'source' <> ALL (ARRAY['quantum','system','mixed']))
        THEN RETURN false; END IF;
        IF p ? 'reason' AND (jsonb_typeof(p->'reason') <> 'string' OR
            p->>'reason' <> ALL (ARRAY['none','no_provider','budget_exhausted','rate_limited',
                'http_error','invalid_response','timeout','network_error','range_rejection']))
        THEN RETURN false; END IF;
        IF p ? 'provider' AND (jsonb_typeof(p->'provider') <> 'string' OR
            p->>'provider' <> ALL (ARRAY['anu','lfdr.de','qrandom.io','anu-legacy']))
        THEN RETURN false; END IF;
        IF p ? 'model' AND (jsonb_typeof(p->'model') <> 'string' OR
            p->>'model' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$')
        THEN RETURN false; END IF;
        IF p ? 'failovers' AND (jsonb_typeof(p->'failovers') <> 'string' OR
            p->>'failovers' !~ '^(anu|lfdr[.]de|qrandom[.]io|anu-legacy):(no_provider|budget_exhausted|rate_limited|http_error|invalid_response|timeout|network_error)(,(anu|lfdr[.]de|qrandom[.]io|anu-legacy):(no_provider|budget_exhausted|rate_limited|http_error|invalid_response|timeout|network_error)){0,3}$')
        THEN RETURN false; END IF;

        IF event_name = 'app_opened' THEN
            allowed := ARRAY['mode','spread','transport'];
        ELSIF event_name = 'reading_started' THEN
            allowed := ARRAY['mode','spread','transport'];
            IF NOT p ?& ARRAY['mode','spread','transport'] THEN RETURN false; END IF;
        ELSIF event_name = 'reading_finished' THEN
            allowed := ARRAY['mode','spread','transport','outcome','duration_ms'];
            IF NOT p ?& allowed THEN RETURN false; END IF;
        ELSIF event_name = 'qrng_result' THEN
            allowed := ARRAY['mode','spread','transport','provider','source','reason','http_status',
                             'requested','fallback_values','duration_ms','failovers'];
            IF NOT p ?& ARRAY['source','reason','requested','fallback_values','duration_ms'] THEN RETURN false; END IF;
        ELSIF event_name = 'interpretation_usage' THEN
            allowed := ARRAY['mode','spread','transport','model','input_tokens','output_tokens',
                             'thinking_tokens','cached_tokens','total_tokens'];
            IF NOT p ? 'model' THEN RETURN false; END IF;
        ELSE
            RETURN false;
        END IF;
        FOR key IN SELECT jsonb_object_keys(p)
        LOOP
            IF NOT key = ANY (allowed) THEN RETURN false; END IF;
        END LOOP;
        RETURN true;
    EXCEPTION WHEN OTHERS THEN
        RETURN false;
    END
    $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION analytics.event_properties_valid(text, jsonb) FROM PUBLIC")

    environment = os.environ.get("ORACLE_DATABASE_ENVIRONMENT")
    if environment not in {"local", "development", "test", "preview", "staging", "production"}:
        raise ValueError("valid ORACLE_DATABASE_ENVIRONMENT is required for migration")
    op.execute("""
    CREATE TABLE analytics.database_identity (
        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
        environment text NOT NULL CHECK (environment IN (
            'local', 'development', 'test', 'preview', 'staging', 'production'
        ))
    )
    """)
    op.execute(sa.text(
        "INSERT INTO analytics.database_identity (singleton, environment) VALUES (true, :environment)"
    ).bindparams(environment=environment))
    op.execute("""
    CREATE FUNCTION analytics.environment_matches(expected text)
    RETURNS boolean
    LANGUAGE sql
    STABLE
    STRICT
    SECURITY DEFINER
    SET search_path = pg_catalog, analytics
    AS $function$
        SELECT EXISTS (
            SELECT 1 FROM analytics.database_identity
            WHERE singleton AND environment = expected
        )
    $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION analytics.environment_matches(text) FROM PUBLIC")

    op.execute("""
    CREATE TABLE analytics.events (
        event_id uuid PRIMARY KEY,
        schema_version smallint NOT NULL CHECK (schema_version IN (1, 2)),
        event_type text NOT NULL CHECK (event_type IN (
            'app_opened', 'reading_started', 'reading_finished', 'qrng_result', 'interpretation_usage'
        )),
        occurred_at timestamptz NOT NULL CHECK (
            occurred_at >= timestamptz '2020-01-01 00:00:00+00' AND
            occurred_at < timestamptz '2100-01-01 00:00:00+00'
        ),
        ingested_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        environment text NOT NULL CHECK (environment IN (
            'local', 'development', 'test', 'preview', 'staging', 'production'
        )),
        traffic_class text NOT NULL CHECK (traffic_class IN ('public', 'internal', 'test')),
        visitor_id uuid,
        reading_id uuid,
        attempt_id uuid,
        canonical_reading_id uuid,
        properties jsonb NOT NULL DEFAULT '{}'::jsonb,
        CONSTRAINT canonical_id_schema_version CHECK (
            schema_version = 2 OR canonical_reading_id IS NULL
        ),
        CONSTRAINT valid_event_properties CHECK (
            analytics.event_properties_valid(event_type, properties)
        )
    )
    """)
    op.execute("CREATE INDEX events_environment_occurred_idx ON analytics.events (environment, occurred_at)")
    op.execute("CREATE INDEX events_reading_attempt_idx ON analytics.events (reading_id, attempt_id)")
    op.execute("CREATE INDEX events_environment_visitor_occurred_idx ON analytics.events (environment, visitor_id, occurred_at)")

    op.execute("GRANT USAGE ON SCHEMA analytics TO oracle_telemetry_writer")
    op.execute("GRANT INSERT ON analytics.events TO oracle_telemetry_writer")
    op.execute("GRANT EXECUTE ON FUNCTION analytics.event_properties_valid(text, jsonb) TO oracle_telemetry_writer")
    op.execute("GRANT EXECUTE ON FUNCTION analytics.environment_matches(text) TO oracle_telemetry_writer")
    op.execute("GRANT USAGE ON SCHEMA analytics TO oracle_report_reader")
    op.execute("GRANT SELECT ON analytics.events TO oracle_report_reader")
    op.execute("GRANT USAGE ON SCHEMA analytics TO oracle_maintenance")
    op.execute("GRANT SELECT, DELETE ON analytics.events TO oracle_maintenance")

def downgrade() -> None:
    op.execute("DROP SCHEMA product")
    op.execute("DROP SCHEMA analytics CASCADE")
    # Roles are cluster-level and may have memberships provisioned outside this
    # database.  Downgrade intentionally preserves the empty NOLOGIN roles.
