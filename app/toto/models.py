from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TotoDraw(Base):
    __tablename__ = "toto_draws"

    draw_number = Column(BigInteger, primary_key=True)
    draw_date = Column(Date, nullable=False, index=True)
    winning_numbers = Column(ARRAY(Integer), nullable=True)
    additional_number = Column(SmallInteger, nullable=True)
    jackpot = Column(DECIMAL(14, 2), nullable=True)

    has_winning_shares = Column(Boolean, nullable=False, server_default=text("false"))
    has_winning_outlets = Column(Boolean, nullable=False, server_default=text("false"))
    has_jackpot = Column(Boolean, nullable=False, server_default=text("false"))

    is_complete = Column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )
    scrape_attempt_count = Column(Integer, nullable=False, server_default=text("0"))
    last_scrape_attempt_at = Column(TIMESTAMP(timezone=True), nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    winning_shares = relationship(
        "TotoWinningShare", back_populates="draw", cascade="all, delete-orphan"
    )
    snowballs = relationship(
        "TotoSnowball", back_populates="draw", cascade="all, delete-orphan"
    )
    winning_tickets = relationship(
        "TotoWinningTicket", back_populates="draw", cascade="all, delete-orphan"
    )


class TotoWinningShare(Base):
    __tablename__ = "toto_winning_shares"

    draw_number = Column(
        BigInteger,
        ForeignKey("toto_draws.draw_number", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_number = Column(SmallInteger, primary_key=True, nullable=False)
    share_amount = Column(DECIMAL(14, 2), nullable=False)
    winner_count = Column(Integer, nullable=False)

    draw = relationship("TotoDraw", back_populates="winning_shares")


class TotoSnowball(Base):
    __tablename__ = "toto_snowballs"

    draw_number = Column(
        BigInteger,
        ForeignKey("toto_draws.draw_number", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_number = Column(SmallInteger, primary_key=True, nullable=False)
    amount = Column(DECIMAL(14, 2), nullable=False)

    draw = relationship("TotoDraw", back_populates="snowballs")


class TotoWinningTicket(Base):
    __tablename__ = "toto_winning_tickets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    draw_number = Column(
        BigInteger,
        ForeignKey("toto_draws.draw_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_number = Column(SmallInteger, nullable=False)
    ticket_order = Column(Integer, nullable=False)
    outlet_name = Column(Text, nullable=False)
    outlet_address = Column(Text, nullable=False)
    entry_type = Column(Text, nullable=False)
    is_itoto = Column(Boolean, nullable=False, server_default=text("false"))

    draw = relationship("TotoDraw", back_populates="winning_tickets")
    itoto_locations = relationship(
        "TotoItotoLocation",
        back_populates="winning_ticket",
        cascade="all, delete-orphan",
    )


class TotoItotoLocation(Base):
    __tablename__ = "toto_itoto_locations"

    ticket_id = Column(
        BigInteger,
        ForeignKey("toto_winning_tickets.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    location_order = Column(Integer, primary_key=True, nullable=False)
    outlet_name = Column(Text, nullable=False)
    outlet_address = Column(Text, nullable=False)
    share_count = Column(Integer, nullable=False)

    winning_ticket = relationship("TotoWinningTicket", back_populates="itoto_locations")


class TotoScrapeAttempt(Base):
    __tablename__ = "toto_scrape_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    requested_draw_number = Column(BigInteger, nullable=False)
    actual_draw_number = Column(BigInteger, nullable=True)
    attempted_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    source_url = Column(Text, nullable=False)
    http_status = Column(Integer, nullable=True)
    outcome = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    validation_mode = Column(Text, nullable=False)
    result_sha256 = Column(Text, nullable=True)
    response_html = Column(Text, nullable=True)
