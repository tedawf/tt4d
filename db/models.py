from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from db.database import Base


class TotoResult(Base):
    __tablename__ = "toto_results"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, unique=True, nullable=False)
    winning_numbers = Column(postgresql.ARRAY(Integer), nullable=False)
    additional_number = Column(Integer, nullable=False)
    draw_date = Column(TIMESTAMP, nullable=False)
    jackpot = Column(DECIMAL, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class WinningShare(Base):
    __tablename__ = "winning_shares"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, ForeignKey("toto_results.draw_number"))
    group_number = Column(Integer, nullable=False)
    share_amount = Column(DECIMAL, nullable=True)
    winner_count = Column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("draw_number", "group_number"),)


class SnowballInfo(Base):
    __tablename__ = "snowball_info"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, ForeignKey("toto_results.draw_number"))
    group_number = Column(Integer, nullable=False)
    amount = Column(DECIMAL, nullable=False)

    __table_args__ = (UniqueConstraint("draw_number", "group_number"),)


class TotoPage(Base):
    __tablename__ = "toto_page"

    id = Column(Integer, primary_key=True, index=True)
    draw_number = Column(
        Integer,
        ForeignKey("toto_results.draw_number", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    html_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WinningTicket(Base):
    __tablename__ = "winning_tickets"

    id = Column(Integer, primary_key=True)
    draw_number = Column(
        Integer,
        ForeignKey("toto_results.draw_number", ondelete="CASCADE"),
        nullable=False,
    )
    group_number = Column(Integer, nullable=False)
    outlet_name = Column(String, nullable=False)
    outlet_address = Column(String, nullable=True)
    entry_type = Column(String, nullable=False)
    is_itoto = Column(Boolean, default=False)
    ticket_order = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("draw_number", "group_number", "ticket_order"),)


class ItotoLocation(Base):
    __tablename__ = "itoto_locations"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("winning_tickets.id"), nullable=False)
    outlet_name = Column(String, nullable=False)
    outlet_address = Column(String, nullable=True)
    share_count = Column(Integer, default=1)
    location_order = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("ticket_id", "location_order"),)
