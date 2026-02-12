from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DdddDraw(Base):
    __tablename__ = "dddd_draws"

    draw_number = Column(BigInteger, primary_key=True)
    draw_date = Column(Date, nullable=False)
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

    prizes = relationship("DdddPrize", back_populates="draw", cascade="all, delete-orphan")


class DdddPrize(Base):
    __tablename__ = "dddd_prizes"

    draw_number = Column(
        BigInteger,
        ForeignKey("dddd_draws.draw_number", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tier = Column(Text, primary_key=True, nullable=False)
    tier_idx = Column(SmallInteger, primary_key=True, nullable=False)
    number = Column(CHAR(4), nullable=False)

    draw = relationship("DdddDraw", back_populates="prizes")

    __table_args__ = (
        CheckConstraint("tier IN ('1','2','3','S','C')", name="ck_dddd_prizes_tier"),
        CheckConstraint("number ~ '^[0-9]{4}$'", name="ck_dddd_prizes_number"),
    )


class DdddScrapeAttempt(Base):
    __tablename__ = "dddd_scrape_attempts"

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
    html_sha256 = Column(Text, nullable=True)
    response_html = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success','already_exists','fetch_error','parse_error','validation_error','db_error','sequence_mismatch')",
            name="ck_dddd_scrape_attempts_outcome",
        ),
    )
