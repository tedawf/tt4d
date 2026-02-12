"""add dddd tables

Revision ID: f0d4ad6ff2f6
Revises: a9005cfc79ec
Create Date: 2026-02-13 01:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0d4ad6ff2f6"
down_revision: Union[str, None] = "a9005cfc79ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dddd_draws",
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("draw_number"),
    )

    op.create_table(
        "dddd_prizes",
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("tier_idx", sa.SmallInteger(), nullable=False),
        sa.Column("number", sa.CHAR(length=4), nullable=False),
        sa.CheckConstraint("tier IN ('1','2','3','S','C')", name="ck_dddd_prizes_tier"),
        sa.CheckConstraint("number ~ '^[0-9]{4}$'", name="ck_dddd_prizes_number"),
        sa.ForeignKeyConstraint(
            ["draw_number"],
            ["dddd_draws.draw_number"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("draw_number", "tier", "tier_idx"),
    )

    op.create_table(
        "dddd_scrape_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requested_draw_number", sa.BigInteger(), nullable=False),
        sa.Column("actual_draw_number", sa.BigInteger(), nullable=True),
        sa.Column(
            "attempted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("html_sha256", sa.Text(), nullable=True),
        sa.Column("response_html", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('success','already_exists','fetch_error','parse_error','validation_error','db_error','sequence_mismatch')",
            name="ck_dddd_scrape_attempts_outcome",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("dddd_scrape_attempts")
    op.drop_table("dddd_prizes")
    op.drop_table("dddd_draws")
