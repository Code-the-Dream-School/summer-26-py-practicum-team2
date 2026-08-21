from __future__ import annotations

from sqlalchemy import Boolean, Text
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
