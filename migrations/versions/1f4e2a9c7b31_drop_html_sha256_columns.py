"""drop html_sha256 columns

Revision ID: 1f4e2a9c7b31
Revises: 7d4df7ef5b7d
Create Date: 2026-02-14 03:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f4e2a9c7b31"
down_revision: Union[str, None] = "7d4df7ef5b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("toto_scrape_attempts", "html_sha256")
    op.drop_column("dddd_scrape_attempts", "html_sha256")


def downgrade() -> None:
    op.add_column("dddd_scrape_attempts", sa.Column("html_sha256", sa.Text(), nullable=True))
    op.add_column("toto_scrape_attempts", sa.Column("html_sha256", sa.Text(), nullable=True))
