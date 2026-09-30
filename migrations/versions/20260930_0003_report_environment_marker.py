"""Allow the aggregate reader to verify the database environment marker."""

from alembic import op


revision = "20260930_0003"
down_revision = "20260929_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "GRANT EXECUTE ON FUNCTION analytics.environment_matches(text) "
        "TO oracle_report_reader"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE EXECUTE ON FUNCTION analytics.environment_matches(text) "
        "FROM oracle_report_reader"
    )
