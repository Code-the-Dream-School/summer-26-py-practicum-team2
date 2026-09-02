from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class City(Base):
    """Target locations from the city input contract (`cities.csv`)."""

    __tablename__ = "cities"

    city_id: Mapped[str] = mapped_column(Text, primary_key=True)
    city_name: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class GoldAirQuality(Base):
    """One hourly air-quality row per city for the dashboard gold table."""

    __tablename__ = "gold_air_quality"
    __table_args__ = (
        UniqueConstraint("city_id", "observed_at", name="uq_gold_city_hour"),
        CheckConstraint("aqi >= 1 AND aqi <= 5", name="ck_gold_aqi"),
    )

    gold_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.city_id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aqi: Mapped[int] = mapped_column(Integer, nullable=False)
    co: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    no2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    o3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    so2: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm2_5: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    pm10: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    nh3: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
