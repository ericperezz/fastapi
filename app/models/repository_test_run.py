import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RepositoryTestRun(Base):
    __tablename__ = "repository_test_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    repository = relationship("Repository", back_populates="test_runs")

    triggered_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    docker_image: Mapped[str] = mapped_column(String(255), nullable=False)

    command: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    tests_ran: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    has_local_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    has_remote_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)

    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )