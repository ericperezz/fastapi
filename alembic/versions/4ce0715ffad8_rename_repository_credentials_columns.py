"""rename repository credentials columns

Revision ID: 4ce0715ffad8
Revises: 537da30f9fd4
Create Date: 2026-07-27 17:14:35.359211
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4ce0715ffad8"
down_revision = "537da30f9fd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "repositories",
        "username",
        new_column_name="git_username",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )

    op.alter_column(
        "repositories",
        "encrypted_token",
        new_column_name="encrypted_git_password",
        existing_type=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "repositories",
        "git_username",
        new_column_name="username",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )

    op.alter_column(
        "repositories",
        "encrypted_git_password",
        new_column_name="encrypted_token",
        existing_type=sa.Text(),
        existing_nullable=False,
    )