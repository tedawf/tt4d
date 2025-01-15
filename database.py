import os
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import DictCursor

from toto_models import DrawResult, GroupResult

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}


def save_group_result(result: GroupResult, cur, draw_number, group_number):
    if result.has_winner:
        for location in result.winning_locations:
            cur.execute(
                """INSERT INTO winning_locations (draw_number, group_number, outlet_name, entry_type) 
                VALUES (%s, %s, %s, %s) ON CONFLICT (draw_number, group_number) DO NOTHING""",
                (draw_number, group_number, location.outlet_name, location.entry_type),
            )
    elif result.snowball_amount:
        cur.execute(
            """INSERT INTO snowball_info (draw_number, group_number, amount)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (draw_number, group_number) DO NOTHING""",
            (draw_number, group_number, result.snowball_amount),
        )


def save_draw(result: DrawResult) -> bool:

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=DictCursor)

        # Insert draw results
        cur.execute(
            """INSERT INTO toto_results (draw_number, draw_date, winning_numbers, additional_number, jackpot) 
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (draw_number) DO NOTHING""",
            (
                result.draw_number,
                result.draw_date,
                result.winning_numbers,
                result.additional_number,
                result.jackpot,
            ),
        )

        # Insert winning shares
        if result.winning_shares:
            for share in result.winning_shares:
                cur.execute(
                    """INSERT INTO winning_shares (draw_number, group_number, share_amount, winner_count)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (draw_number, group_number) DO NOTHING""",
                    (
                        result.draw_number,
                        share.group,
                        share.amount,
                        share.count,
                    ),
                )

        # Insert group results
        if result.group1_result and result.group2_result:
            save_group_result(result.group1_result, cur, result.draw_number, 1)
            save_group_result(result.group2_result, cur, result.draw_number, 2)

        conn.commit()
        return True

    except Exception as e:
        print(f"Error saving draw {result.draw_number}: {e}")
        import traceback

        traceback.print_exc()  # This will print the full error trace
        if conn:
            conn.rollback()
        return False

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_latest_draw_number() -> Optional[int]:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT MAX(draw_number) FROM toto_results")
        result = cur.fetchone()
        return result[0] if result[0] is not None else 0

    except Exception as e:
        print(f"Error getting latest draw number: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    print(f"Latest draw number: {get_latest_draw_number()}")
