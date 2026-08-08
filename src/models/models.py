from src.database import Base
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Organization(Base):
    __tablename__ = "reports_organization"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name_en: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Наименование организации анг"
    )
    name_ru: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Наименование организации"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name_ru='{self.name_ru}')>"


class Reports(Base):
    __tablename__ = "reports_report"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int | None]
    organization_id: Mapped[int | None]
    detection_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="Дата и время выявления угрозы")
    created_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Текстовые поля и CharField
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attack_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # GenericIPAddressField обычно хранится как VARCHAR(45) (для поддержки IPv6)
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    destination_ip: Mapped[str] = mapped_column(String(45), nullable=False)

    detection_tool: Mapped[str] = mapped_column(String(10), nullable=False)
    cve: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    host: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Поля с blank=True без null=True в Django в БД являются NOT NULL (сохраняют пустую строку "")
    methods: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    protocols_ports: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    potential_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_assessment: Mapped[str] = mapped_column(String(12), default="Низкая", nullable=False)
    data_or_payload: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_actions: Mapped[str] = mapped_column(Text, default="", nullable=False)