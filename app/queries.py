from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ItotoLocation,
    SnowballInfo,
    TotoPage,
    TotoResult,
    WinningShare,
    WinningTicket,
)
from app.parsing_types import DrawResult


def get_latest_draw_number(db: Session) -> int:
    latest_draw = db.query(TotoResult).order_by(TotoResult.draw_number.desc()).first()
    return latest_draw.draw_number if latest_draw else 0


def _save_winning_tickets(
    db: Session, draw_number: int, group_number: int, tickets: list
):
    for ticket_order, ticket in enumerate(tickets, 1):
        winning_ticket = WinningTicket(
            draw_number=draw_number,
            group_number=group_number,
            outlet_name=ticket.outlet_name,
            outlet_address=ticket.outlet_address,
            entry_type=ticket.entry_type,
            is_itoto=ticket.is_itoto,
            ticket_order=ticket_order,
        )
        db.add(winning_ticket)
        db.flush()  # Get id

        # If it's an iTOTO ticket, save all the locations
        if ticket.is_itoto and ticket.itoto_locations:
            _save_itoto_locations(db, winning_ticket.id, ticket.itoto_locations)


def _save_itoto_locations(db: Session, ticket_id: int, locations: list):
    for location_order, location in enumerate(locations, 1):
        itoto_location = ItotoLocation(
            ticket_id=ticket_id,
            outlet_name=location.outlet_name,
            outlet_address=location.outlet_address,
            share_count=location.share_count,
            location_order=location_order,
        )
        db.add(itoto_location)


def _save_snowball_info(
    db: Session, draw_number: int, group_number: int, amount: float
):
    snowball_info = SnowballInfo(
        draw_number=draw_number,
        group_number=group_number,
        amount=amount,
    )
    db.add(snowball_info)


def save_draw(db: Session, draw_result: DrawResult) -> bool:
    try:
        # First, check if draw already exists
        existing_draw = (
            db.query(TotoResult)
            .filter(TotoResult.draw_number == draw_result.draw_number)
            .first()
        )
        if existing_draw:
            raise ValueError(f"Draw {draw_result.draw_number} already exists")

        # Save main result first
        toto_result = TotoResult(
            draw_number=draw_result.draw_number,
            winning_numbers=draw_result.winning_numbers,
            additional_number=draw_result.additional_number,
            draw_date=draw_result.draw_date,
            jackpot=draw_result.jackpot,
        )
        db.add(toto_result)
        db.flush()  # This ensures the main record exists before adding related records

        # Save winning shares
        if draw_result.winning_shares:
            winning_shares = [
                WinningShare(
                    draw_number=draw_result.draw_number,
                    group_number=share.group,
                    share_amount=share.amount,
                    winner_count=share.count,
                )
                for share in draw_result.winning_shares
            ]
            db.add_all(winning_shares)

        # Process group results
        for group_num, group_result in [
            (1, draw_result.group1_result),
            (2, draw_result.group2_result),
        ]:
            if not group_result:
                continue

            if group_result.has_winner:
                _save_winning_tickets(
                    db,
                    draw_result.draw_number,
                    group_num,
                    group_result.winning_tickets,
                )
            elif group_result.snowball_amount:
                _save_snowball_info(
                    db,
                    draw_result.draw_number,
                    group_num,
                    group_result.snowball_amount,
                )

        db.commit()
        return True

    except IntegrityError as e:
        db.rollback()
        if "violates foreign key constraint" in str(e):
            raise RuntimeError(
                f"Foreign key violation. Make sure parent record exists first: {str(e)}"
            ) from e
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Error saving draw: {str(e)}") from e


def save_html_content(db: Session, draw_number: int, html_content: str) -> bool:
    try:
        # Check if already exists
        existing = (
            db.query(TotoPage).filter(TotoPage.draw_number == draw_number).first()
        )

        if existing:
            raise ValueError(f"Html content for draw {draw_number} already exists")

        toto_page = TotoPage(draw_number=draw_number, html_content=html_content)
        db.add(toto_page)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error saving HTML content: {e}")
        return False


def get_html_content(db: Session, draw_number: int) -> str:
    toto_page = db.query(TotoPage).filter(TotoPage.draw_number == draw_number).first()
    return toto_page.html_content if toto_page else None
