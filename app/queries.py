import logging
from typing import List, Optional

from sqlalchemy import desc, select
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
from app.parsing_types import ParsedDrawResult, ParsedItotoLocation, ParsedWinningTicket

logger = logging.getLogger(__name__)


def get_latest_draw_number(db: Session) -> int:
    """Retrieves the highest draw_number from toto_results"""
    query = select(TotoResult.draw_number).order_by(desc(TotoResult.draw_number))
    latest_draw_number = db.execute(query).scalars().first()
    if latest_draw_number is None:
        logger.info(
            "No draws found in the database. Returning 0 as the latest draw number."
        )
        return 0
    return latest_draw_number


def _save_winning_tickets(
    db: Session, draw_number: int, group_number: int, tickets: List[ParsedWinningTicket]
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
        db.flush()  # Flush is necessary here to get db_winning_ticket.id for iTOTO locations

        # If it's an iTOTO ticket, save all the locations
        if ticket.is_itoto and ticket.itoto_locations:
            _save_itoto_locations(db, winning_ticket.id, ticket.itoto_locations)
    logger.debug(
        "Saved %s winning tickets for draw %s, group %s.",
        len(tickets),
        draw_number,
        group_number,
    )


def _save_itoto_locations(
    db: Session, winning_ticket_id: int, locations: List[ParsedItotoLocation]
):
    itoto_locations = []
    for location_order, loc_data in enumerate(locations, 1):
        itoto_locations.append(
            ItotoLocation(
                ticket_id=winning_ticket_id,
                outlet_name=loc_data.outlet_name,
                outlet_address=loc_data.outlet_address,
                share_count=loc_data.share_count,
                location_order=location_order,
            )
        )
    if itoto_locations:
        db.add_all(itoto_locations)
    logger.debug(
        "Saved %s iTOTO locations for ticket ID %s.", len(locations), winning_ticket_id
    )


def _save_snowball_info(
    db: Session, draw_number: int, group_number: int, amount: float
):
    snowball_info = SnowballInfo(
        draw_number=draw_number,
        group_number=group_number,
        amount=amount,
    )
    db.add(snowball_info)
    logger.debug(
        "Saved snowball info for draw %s, group %s, amount %s.",
        draw_number,
        group_number,
        amount,
    )


def get_draw(db: Session, draw_number: int) -> Optional[TotoResult]:
    query = select(TotoResult).where(TotoResult.draw_number == draw_number)
    result = db.execute(query).scalars().first()
    return result


def save_draw(db: Session, draw_result: ParsedDrawResult) -> bool:
    existing_draw = get_draw(db, draw_result.draw_number)
    if existing_draw:
        logger.warning(
            "Draw %s already exists in the database. Skipping save.",
            draw_result.draw_number,
        )
        return False

    try:
        logger.info("Saving new draw %s to database.", draw_result.draw_number)
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
            logger.debug(
                "Added %s winning share records for draw %s.",
                len(winning_shares),
                draw_result.draw_number,
            )

        # Process group results
        for group_num, group_result in [
            (1, draw_result.group1_result),
            (2, draw_result.group2_result),
        ]:
            if not group_result:
                logger.debug(
                    "No group %s result data to process for draw %s.",
                    group_num,
                    draw_result.draw_number,
                )
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
            else:
                logger.debug(
                    "Group %s for draw %s has no winners and no snowball amount.",
                    group_num,
                    draw_result.draw_number,
                )

        db.commit()
        logger.info(
            "Successfully saved draw %s and related data.", draw_result.draw_number
        )
        return True

    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error while saving draw %s: %s",
            draw_result.draw_number,
            e,
        )
        raise
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error saving draw %s: %s", draw_result.draw_number, e
        )
        raise


def save_html_content(db: Session, draw_number: int, html_content: str) -> bool:
    existing_query = select(TotoPage).where(TotoPage.draw_number == draw_number)
    existing_page = db.execute(existing_query).scalars().first()

    if existing_page:
        logger.info(
            "HTML content for draw %s already exists. Skipping save.", draw_number
        )
        return False

    try:
        toto_page = TotoPage(draw_number=draw_number, html_content=html_content)
        db.add(toto_page)
        db.commit()
        logger.info("Successfully saved HTML content for draw %s.", draw_number)
        return True
    except IntegrityError as e:
        db.rollback()
        logger.error("Integrity error saving HTML for draw %s: %s", draw_number, e)
        raise
    except Exception:
        db.rollback()
        logger.exception("Error saving HTML content for draw %s:", draw_number)
        return False


def get_html_content(db: Session, draw_number: int) -> Optional[str]:
    q = select(TotoPage.html_content).where(TotoPage.draw_number == draw_number)
    html_content = db.execute(q).scalars().first()
    if html_content:
        logger.debug("Found cached HTML for draw %s.", draw_number)
    else:
        logger.debug("No cached HTML found for draw %s.", draw_number)
    return html_content
