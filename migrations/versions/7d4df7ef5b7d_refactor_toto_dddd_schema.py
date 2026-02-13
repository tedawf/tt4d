"""refactor toto dddd schema

Revision ID: 7d4df7ef5b7d
Revises: f0d4ad6ff2f6
Create Date: 2026-02-14 02:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7d4df7ef5b7d"
down_revision: Union[str, None] = "f0d4ad6ff2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old Toto tables.
    op.execute("DROP TABLE IF EXISTS itoto_locations CASCADE")
    op.execute("DROP TABLE IF EXISTS winning_tickets CASCADE")
    op.execute("DROP TABLE IF EXISTS winning_shares CASCADE")
    op.execute("DROP TABLE IF EXISTS snowball_info CASCADE")
    op.execute("DROP TABLE IF EXISTS toto_page CASCADE")
    op.execute("DROP TABLE IF EXISTS toto_results CASCADE")

    # Create new Toto tables.
    op.create_table(
        "toto_draws",
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column("winning_numbers", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("additional_number", sa.SmallInteger(), nullable=True),
        sa.Column("jackpot", sa.Numeric(14, 2), nullable=True),
        sa.Column("has_winning_shares", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_winning_outlets", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_jackpot", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("scrape_attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_scrape_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("draw_number"),
    )
    op.create_index("ix_toto_draws_draw_date", "toto_draws", ["draw_date"], unique=False)
    op.create_index("ix_toto_draws_is_complete", "toto_draws", ["is_complete"], unique=False)

    op.create_table(
        "toto_winning_shares",
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("group_number", sa.SmallInteger(), nullable=False),
        sa.Column("share_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("winner_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_draws.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("draw_number", "group_number"),
    )

    op.create_table(
        "toto_snowballs",
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("group_number", sa.SmallInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_draws.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("draw_number", "group_number"),
    )

    op.create_table(
        "toto_winning_tickets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("draw_number", sa.BigInteger(), nullable=False),
        sa.Column("group_number", sa.SmallInteger(), nullable=False),
        sa.Column("ticket_order", sa.Integer(), nullable=False),
        sa.Column("outlet_name", sa.Text(), nullable=False),
        sa.Column("outlet_address", sa.Text(), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("is_itoto", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_draws.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draw_number", "group_number", "ticket_order"),
    )
    op.create_index("ix_toto_winning_tickets_draw_number", "toto_winning_tickets", ["draw_number"], unique=False)

    op.create_table(
        "toto_itoto_locations",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("location_order", sa.Integer(), nullable=False),
        sa.Column("outlet_name", sa.Text(), nullable=False),
        sa.Column("outlet_address", sa.Text(), nullable=False),
        sa.Column("share_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["toto_winning_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ticket_id", "location_order"),
    )

    op.create_table(
        "toto_scrape_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("requested_draw_number", sa.BigInteger(), nullable=False),
        sa.Column("actual_draw_number", sa.BigInteger(), nullable=True),
        sa.Column("attempted_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("validation_mode", sa.Text(), nullable=False),
        sa.Column("result_sha256", sa.Text(), nullable=True),
        sa.Column("html_sha256", sa.Text(), nullable=True),
        sa.Column("response_html", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX ix_toto_scrape_attempts_requested_attempted "
        "ON toto_scrape_attempts (requested_draw_number, attempted_at DESC)"
    )

    # Update 4D tables.
    op.alter_column(
        "dddd_prizes",
        "tier",
        existing_type=sa.Text(),
        type_=sa.CHAR(length=1),
        nullable=False,
    )

    op.add_column(
        "dddd_scrape_attempts",
        sa.Column("validation_mode", sa.Text(), server_default=sa.text("'current'"), nullable=False),
    )
    op.add_column(
        "dddd_scrape_attempts",
        sa.Column("result_sha256", sa.Text(), nullable=True),
    )

    op.execute("ALTER TABLE dddd_scrape_attempts DROP CONSTRAINT IF EXISTS ck_dddd_scrape_attempts_outcome")
    op.create_check_constraint(
        "ck_dddd_scrape_attempts_outcome",
        "dddd_scrape_attempts",
        "outcome IN ('success','already_exists','fetch_error','parse_error','validation_error','db_error','sequence_mismatch','no_new_draw','skipped_locked','dry_run')",
    )

    op.create_index("ix_dddd_draws_draw_date", "dddd_draws", ["draw_date"], unique=False)
    op.execute(
        "CREATE INDEX ix_dddd_scrape_attempts_requested_attempted "
        "ON dddd_scrape_attempts (requested_draw_number, attempted_at DESC)"
    )

    op.alter_column("dddd_scrape_attempts", "validation_mode", server_default=None)

    # Analytics views.
    op.execute("DROP VIEW IF EXISTS v_toto_draws_analysis")
    op.execute("DROP VIEW IF EXISTS v_toto_draws_history")
    op.execute("DROP VIEW IF EXISTS v_dddd_draws_analysis")

    op.execute(
        """
        CREATE VIEW v_toto_draws_history AS
        SELECT
            draw_number,
            draw_date,
            winning_numbers,
            additional_number,
            jackpot,
            has_winning_shares,
            has_winning_outlets,
            has_jackpot,
            is_complete,
            scrape_attempt_count,
            last_scrape_attempt_at,
            created_at,
            updated_at
        FROM toto_draws
        """
    )

    op.execute(
        """
        CREATE VIEW v_toto_draws_analysis AS
        SELECT
            draw_number,
            draw_date,
            winning_numbers,
            additional_number,
            jackpot,
            created_at,
            updated_at
        FROM toto_draws
        WHERE
            is_complete = true
            AND winning_numbers IS NOT NULL
            AND cardinality(winning_numbers) = 6
            AND additional_number IS NOT NULL
            AND has_jackpot = true
        """
    )

    op.execute(
        """
        CREATE VIEW v_dddd_draws_analysis AS
        SELECT d.draw_number, d.draw_date, d.created_at, d.updated_at
        FROM dddd_draws d
        JOIN (
            SELECT
                draw_number,
                SUM(CASE WHEN tier IN ('1','2','3') THEN 1 ELSE 0 END) AS top_count,
                SUM(CASE WHEN tier = 'S' THEN 1 ELSE 0 END) AS starter_count,
                SUM(CASE WHEN tier = 'C' THEN 1 ELSE 0 END) AS consolation_count
            FROM dddd_prizes
            GROUP BY draw_number
        ) p ON p.draw_number = d.draw_number
        WHERE p.top_count = 3 AND p.starter_count = 10 AND p.consolation_count = 10
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_dddd_draws_analysis")
    op.execute("DROP VIEW IF EXISTS v_toto_draws_analysis")
    op.execute("DROP VIEW IF EXISTS v_toto_draws_history")

    op.drop_index("ix_dddd_scrape_attempts_requested_attempted", table_name="dddd_scrape_attempts")
    op.drop_index("ix_dddd_draws_draw_date", table_name="dddd_draws")

    op.execute("ALTER TABLE dddd_scrape_attempts DROP CONSTRAINT IF EXISTS ck_dddd_scrape_attempts_outcome")
    op.create_check_constraint(
        "ck_dddd_scrape_attempts_outcome",
        "dddd_scrape_attempts",
        "outcome IN ('success','already_exists','fetch_error','parse_error','validation_error','db_error','sequence_mismatch')",
    )

    op.drop_column("dddd_scrape_attempts", "result_sha256")
    op.drop_column("dddd_scrape_attempts", "validation_mode")

    op.alter_column(
        "dddd_prizes",
        "tier",
        existing_type=sa.CHAR(length=1),
        type_=sa.Text(),
        nullable=False,
    )

    op.drop_index("ix_toto_scrape_attempts_requested_attempted", table_name="toto_scrape_attempts")
    op.drop_table("toto_scrape_attempts")
    op.drop_table("toto_itoto_locations")
    op.drop_index("ix_toto_winning_tickets_draw_number", table_name="toto_winning_tickets")
    op.drop_table("toto_winning_tickets")
    op.drop_table("toto_snowballs")
    op.drop_table("toto_winning_shares")
    op.drop_index("ix_toto_draws_is_complete", table_name="toto_draws")
    op.drop_index("ix_toto_draws_draw_date", table_name="toto_draws")
    op.drop_table("toto_draws")

    # Recreate legacy Toto schema.
    op.create_table(
        "toto_page",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draw_number"),
    )

    op.create_table(
        "toto_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=False),
        sa.Column("winning_numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("additional_number", sa.Integer(), nullable=False),
        sa.Column("draw_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("jackpot", sa.DECIMAL(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_scrape_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("scrape_attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_toto_results_draw_date", "toto_results", ["draw_date"], unique=False)
    op.create_index("ix_toto_results_draw_number", "toto_results", ["draw_number"], unique=True)
    op.create_index("ix_toto_results_is_complete", "toto_results", ["is_complete"], unique=False)

    op.create_table(
        "snowball_info",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=False),
        sa.Column("group_number", sa.Integer(), nullable=False),
        sa.Column("amount", sa.DECIMAL(), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_results.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draw_number", "group_number"),
    )
    op.create_index("ix_snowball_info_draw_number", "snowball_info", ["draw_number"], unique=False)

    op.create_table(
        "winning_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=False),
        sa.Column("group_number", sa.Integer(), nullable=False),
        sa.Column("share_amount", sa.DECIMAL(), nullable=False),
        sa.Column("winner_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_results.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draw_number", "group_number"),
    )

    op.create_table(
        "winning_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=False),
        sa.Column("group_number", sa.Integer(), nullable=False),
        sa.Column("outlet_name", sa.Text(), nullable=False),
        sa.Column("outlet_address", sa.Text(), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("is_itoto", sa.Boolean(), nullable=True),
        sa.Column("ticket_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["draw_number"], ["toto_results.draw_number"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draw_number", "group_number", "ticket_order"),
    )
    op.create_index("ix_winning_tickets_draw_number", "winning_tickets", ["draw_number"], unique=False)

    op.create_table(
        "itoto_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("outlet_name", sa.Text(), nullable=False),
        sa.Column("outlet_address", sa.Text(), nullable=False),
        sa.Column("share_count", sa.Integer(), nullable=False),
        sa.Column("location_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["winning_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "location_order"),
    )
    op.create_index("ix_itoto_locations_ticket_id", "itoto_locations", ["ticket_id"], unique=False)
