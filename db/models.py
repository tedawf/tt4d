from sqlalchemy import (
    DECIMAL,
    TEXT,
    TIMESTAMP,
    Column,
    DateTime,
    ForeignKey,
    Integer,
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


class WinningLocation(Base):
    __tablename__ = "winning_locations"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, ForeignKey("toto_results.draw_number"))
    group_number = Column(Integer, nullable=False)
    outlet_name = Column(TEXT, nullable=False)
    entry_type = Column(TEXT, nullable=False)

    __table_args__ = (
        UniqueConstraint("draw_number", "group_number", "outlet_name", "entry_type"),
    )


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
