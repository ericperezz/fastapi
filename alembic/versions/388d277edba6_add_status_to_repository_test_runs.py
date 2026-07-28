"""add status to repository test runs

Revision ID: 388d277edba6
Revises: bad2a555f78d
Create Date: 2026-07-28 18:49:26.701304

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '388d277edba6'
down_revision: Union[str, Sequence[str], None] = 'bad2a555f78d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "repository_test_runs",
        sa.Column("status", sa.String(length=50), nullable=True),
    )

    op.execute(
        """
        UPDATE repository_test_runs
        SET status = CASE
            WHEN tests_ran = false THEN 'skipped'
            WHEN success = true THEN 'passed'
            WHEN success = false AND exit_code IS NOT NULL THEN 'failed'
            WHEN success = false AND exit_code IS NULL THEN 'runner_error'
            ELSE 'runner_error'
        END
        """
    )

    op.alter_column(
        "repository_test_runs",
        "status",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.create_index(
        "ix_repository_test_runs_status",
        "repository_test_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_repository_test_runs_status",
        table_name="repository_test_runs",
    )

    op.drop_column(
        "repository_test_runs",
        "status",
    )