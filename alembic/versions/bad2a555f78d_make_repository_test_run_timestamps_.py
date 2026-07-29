"""make repository test run timestamps timezone aware

Revision ID: bad2a555f78d
Revises: 77632c858823
Create Date: 2026-07-28 17:58:06.452045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bad2a555f78d'
down_revision: Union[str, Sequence[str], None] = '77632c858823'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "repository_test_runs",
        "created_at",
        existing_type=sa.DateTime(timezone=False),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        "repository_test_runs",
        "finished_at",
        existing_type=sa.DateTime(timezone=False),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="finished_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "repository_test_runs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        "repository_test_runs",
        "finished_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="finished_at AT TIME ZONE 'UTC'",
    )