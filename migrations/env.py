"""Alembic environment using the migration-only administrative connection."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from database import migration_database_url_from_env


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = None


def migration_url():
    url = make_url(migration_database_url_from_env())
    if url.get_backend_name() != "postgresql":
        raise ValueError("migration_database_must_be_postgresql")
    return url.set(drivername="postgresql+psycopg")


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url(), target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(migration_url(), poolclass=pool.NullPool, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
