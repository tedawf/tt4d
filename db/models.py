from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class TotoResult(Base):
    __tablename__ = "toto_results"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, unique=True, nullable=False, index=True)
    winning_numbers = Column(postgresql.ARRAY(Integer), nullable=False)
    additional_number = Column(Integer, nullable=False)
    draw_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    jackpot = Column(DECIMAL, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.current_timestamp()
    )

    winning_shares = relationship(
        "WinningShare", back_populates="toto_result", cascade="all, delete-orphan"
    )
    snowball_info = relationship(
        "SnowballInfo", back_populates="toto_result", cascade="all, delete-orphan"
    )
    winning_tickets = relationship(
        "WinningTicket", back_populates="toto_result", cascade="all, delete-orphan"
    )


class WinningShare(Base):
    __tablename__ = "winning_shares"

    id = Column(Integer, primary_key=True)
    draw_number = Column(
        Integer,
        ForeignKey("toto_results.draw_number", ondelete="CASCADE"),
        nullable=False,
    )
    group_number = Column(Integer, nullable=False)
    share_amount = Column(DECIMAL, nullable=False)
    winner_count = Column(Integer, nullable=False)

    toto_result = relationship("TotoResult", back_populates="winning_shares")

    __table_args__ = (UniqueConstraint("draw_number", "group_number"),)


class SnowballInfo(Base):
    __tablename__ = "snowball_info"

    id = Column(Integer, primary_key=True)
    draw_number = Column(
        Integer,
        ForeignKey("toto_results.draw_number", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    group_number = Column(Integer, nullable=False)
    amount = Column(DECIMAL, nullable=False)

    toto_result = relationship("TotoResult", back_populates="snowball_info")

    __table_args__ = (UniqueConstraint("draw_number", "group_number"),)


class TotoPage(Base):
    __tablename__ = "toto_page"

    id = Column(Integer, primary_key=True)
    draw_number = Column(
        Integer,
        unique=True,
        nullable=False,
    )
    html_content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


class WinningTicket(Base):
    __tablename__ = "winning_tickets"

    id = Column(Integer, primary_key=True)
    draw_number = Column(
        Integer,
        ForeignKey("toto_results.draw_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_number = Column(Integer, nullable=False)
    outlet_name = Column(Text, nullable=False)
    outlet_address = Column(Text, nullable=False)
    entry_type = Column(Text, nullable=False)
    is_itoto = Column(Boolean, default=False)
    ticket_order = Column(Integer, nullable=False)

    itoto_locations = relationship("ItotoLocation", back_populates="winning_ticket")
    toto_result = relationship("TotoResult", back_populates="winning_tickets")

    __table_args__ = (UniqueConstraint("draw_number", "group_number", "ticket_order"),)


class ItotoLocation(Base):
    __tablename__ = "itoto_locations"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(
        Integer,
        ForeignKey("winning_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outlet_name = Column(Text, nullable=False)
    outlet_address = Column(Text, nullable=False)
    share_count = Column(Integer, nullable=False)
    location_order = Column(Integer, nullable=False)

    winning_ticket = relationship("WinningTicket", back_populates="itoto_locations")

    __table_args__ = (UniqueConstraint("ticket_id", "location_order"),)
