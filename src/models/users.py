from src.database import Base
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    func
)
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column



class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[bytes]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.timezone('Asia/Bishkek', func.now()))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone('Asia/Bishkek', func.now()),
        onupdate=func.timezone('Asia/Bishkek', func.now())
    )

    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="check_valid_email"
        ),
    )