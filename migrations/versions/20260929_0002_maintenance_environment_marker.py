"""Allow the bounded maintenance role to verify the database identity marker."""

from alembic import op


revision = "20260929_0002"
down_revision = "20260929_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "GRANT EXECUTE ON FUNCTION analytics.environment_matches(text) "
        "TO oracle_maintenance"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE EXECUTE ON FUNCTION analytics.environment_matches(text) "
        "FROM oracle_maintenance"
    )
