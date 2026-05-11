from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class Phenomenon(Base):
    __tablename__ = "phenomena"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    kind = Column(
        String(32),
        nullable=False,
        default="flowering",
    )
    category = Column(String(120))
    description = Column(Text)
    typical_season = Column(String(500))
    icon_emoji = Column(String(16), default="")
    icon_lucide = Column(String(64), nullable=True)
    main_photo_url = Column(String(500))
    website_url = Column(String(500))
    water_temp_c = Column(Float, nullable=True)

    events = relationship("Event", back_populates="phenomenon")


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    region = Column(String(120))
    subregion = Column(String(120))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    events = relationship("Event", back_populates="place")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    phenomenon_id = Column(Integer, ForeignKey("phenomena.id"), nullable=False)
    place_id = Column(Integer, ForeignKey("places.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    peak_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    intensity = Column(Integer, default=3)
    phase_history = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    phenomenon = relationship("Phenomenon", back_populates="events")
    place = relationship("Place", back_populates="events")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(254), nullable=False, index=True)
    phenomenon_id = Column(Integer, ForeignKey("phenomena.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    phenomenon = relationship("Phenomenon")


class TelegramWatch(Base):
    """Подписка чата Telegram на явление (задел под рассылку)."""

    __tablename__ = "telegram_watches"
    __table_args__ = (
        UniqueConstraint("chat_id", "phenomenon_id", name="uq_telegram_watch_chat_phenomenon"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    phenomenon_id = Column(Integer, ForeignKey("phenomena.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    phenomenon = relationship("Phenomenon")
