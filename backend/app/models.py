from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class ValueEnum(StrEnum):
    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class Geography(ValueEnum):
    RUSSIA = "russia"
    MOSCOW = "moscow"
    BOTH = "russia_moscow"


class EditionStatus(ValueEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DataStatus(ValueEnum):
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    PREVIOUS_YEAR_ESTIMATE = "previous_year_estimate"
    ANNOUNCEMENT_PENDING = "announcement_pending"


class RegistryStatus(ValueEnum):
    NOT_LISTED = "not_listed"
    DRAFT = "draft"
    APPROVED = "approved"
    PREVIOUS_YEAR = "previous_year"


class RegistrationStatus(ValueEnum):
    OPEN = "open"
    ANNOUNCED = "announced"
    NOT_OPEN = "not_open"
    NOT_FOUND = "not_found"


class DatePrecision(ValueEnum):
    EXACT = "exact"
    RANGE = "range"
    MONTH = "month"
    APPROXIMATE = "approximate"
    TBA = "tba"


class EventFormat(ValueEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class MaterialType(ValueEnum):
    TASKS = "tasks"
    SOLUTIONS = "solutions"
    VIDEO = "video"
    COURSE = "course"
    ARCHIVE = "archive"
    OTHER = "other"


class BenefitType(ValueEnum):
    BVI = "bvi"
    HUNDRED_POINTS = "hundred_points"
    GRANT = "grant"
    PRIZE = "prize"
    OTHER = "other"


class PlanStatus(ValueEnum):
    PLANNED = "planned"
    REGISTERED = "registered"
    PARTICIPATING = "participating"
    COMPLETED = "completed"


class ReminderStatus(ValueEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY = "retry"
    SENT = "sent"
    PERMANENT_FAILED = "permanent_failed"
    CANCELLED = "cancelled"


def enum_type(enum: type[ValueEnum], length: int = 40):
    return db.Enum(
        enum,
        values_callable=lambda items: items.values(),
        native_enum=False,
        validate_strings=True,
        length=length,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Admin(TimestampMixin, db.Model):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Olympiad(TimestampMixin, db.Model):
    __tablename__ = "olympiads"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    family_name: Mapped[str] = mapped_column(String(255), index=True)
    profile: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    organizer: Mapped[str | None] = mapped_column(String(255))
    website_url: Mapped[str] = mapped_column(String(1000))
    logo_url: Mapped[str | None] = mapped_column(String(1000))
    geography: Mapped[Geography] = mapped_column(
        enum_type(Geography), default=Geography.RUSSIA, nullable=False
    )
    is_team: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    editions: Mapped[list[OlympiadEdition]] = relationship(
        back_populates="olympiad", cascade="all, delete-orphan"
    )
    materials: Mapped[list[Material]] = relationship(
        back_populates="olympiad", cascade="all, delete-orphan"
    )


class OlympiadEdition(TimestampMixin, db.Model):
    __tablename__ = "olympiad_editions"
    __table_args__ = (
        UniqueConstraint("olympiad_id", "academic_year", name="edition_olympiad_year"),
        CheckConstraint(
            "registry_level IS NULL OR registry_level BETWEEN 1 AND 3",
            name="valid_registry_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    olympiad_id: Mapped[int] = mapped_column(ForeignKey("olympiads.id", ondelete="CASCADE"))
    academic_year: Mapped[str] = mapped_column(String(9), index=True)
    cycle_label: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[EditionStatus] = mapped_column(
        enum_type(EditionStatus), default=EditionStatus.DRAFT, nullable=False, index=True
    )
    data_status: Mapped[DataStatus] = mapped_column(
        enum_type(DataStatus), default=DataStatus.ANNOUNCEMENT_PENDING, nullable=False
    )
    is_in_registry: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    registry_status: Mapped[RegistryStatus] = mapped_column(
        enum_type(RegistryStatus), default=RegistryStatus.NOT_LISTED, nullable=False, index=True
    )
    registry_level: Mapped[int | None] = mapped_column(db.SmallInteger, index=True)
    is_popular: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    registration_status: Mapped[RegistrationStatus] = mapped_column(
        enum_type(RegistrationStatus),
        default=RegistrationStatus.NOT_FOUND,
        nullable=False,
        index=True,
    )
    registration_checked_on: Mapped[date | None] = mapped_column(db.Date)
    registration_url: Mapped[str | None] = mapped_column(String(1000))
    registration_closes_at: Mapped[datetime | None] = mapped_column(
        db.DateTime(timezone=True)
    )
    previous_year_reference: Mapped[str | None] = mapped_column(String(9))
    eligibility_notes: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    olympiad: Mapped[Olympiad] = relationship(back_populates="editions")
    grades: Mapped[list[EditionGrade]] = relationship(
        back_populates="edition", cascade="all, delete-orphan", order_by="EditionGrade.grade"
    )
    stages: Mapped[list[Stage]] = relationship(
        back_populates="edition", cascade="all, delete-orphan", order_by="Stage.position"
    )
    benefits: Mapped[list[Benefit]] = relationship(
        back_populates="edition", cascade="all, delete-orphan"
    )
    sources: Mapped[list[SourceLink]] = relationship(
        back_populates="edition", cascade="all, delete-orphan"
    )
    plans: Mapped[list[UserOlympiadPlan]] = relationship(
        back_populates="edition", cascade="all, delete-orphan"
    )


class EditionGrade(db.Model):
    __tablename__ = "edition_grades"
    __table_args__ = (CheckConstraint("grade BETWEEN 5 AND 11", name="valid_grade"),)

    edition_id: Mapped[int] = mapped_column(
        ForeignKey("olympiad_editions.id", ondelete="CASCADE"), primary_key=True
    )
    grade: Mapped[int] = mapped_column(db.SmallInteger, primary_key=True)

    edition: Mapped[OlympiadEdition] = relationship(back_populates="grades")


class Stage(TimestampMixin, db.Model):
    __tablename__ = "stages"
    __table_args__ = (
        CheckConstraint("position >= 0", name="nonnegative_position"),
        UniqueConstraint("edition_id", "key", name="stage_edition_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("olympiad_editions.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(180))
    stage_type: Mapped[str | None] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    starts_on: Mapped[date | None] = mapped_column(db.Date)
    ends_on: Mapped[date | None] = mapped_column(db.Date)
    registration_opens_on: Mapped[date | None] = mapped_column(db.Date)
    registration_closes_on: Mapped[date | None] = mapped_column(db.Date)
    date_precision: Mapped[DatePrecision] = mapped_column(
        enum_type(DatePrecision), default=DatePrecision.TBA, nullable=False
    )
    is_date_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    format: Mapped[EventFormat] = mapped_column(
        enum_type(EventFormat), default=EventFormat.UNKNOWN, nullable=False
    )
    location: Mapped[str | None] = mapped_column(String(500))
    details: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(1000))

    edition: Mapped[OlympiadEdition] = relationship(back_populates="stages")
    user_progress: Mapped[list[UserStageProgress]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    reminder_dispatches: Mapped[list[ReminderDispatch]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class Material(TimestampMixin, db.Model):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    olympiad_id: Mapped[int] = mapped_column(
        ForeignKey("olympiads.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    material_type: Mapped[MaterialType] = mapped_column(enum_type(MaterialType), nullable=False)
    year: Mapped[int | None] = mapped_column(db.SmallInteger)
    url: Mapped[str] = mapped_column(String(1000))
    is_official: Mapped[bool] = mapped_column(default=True, nullable=False)

    olympiad: Mapped[Olympiad] = relationship(back_populates="materials")


class University(TimestampMixin, db.Model):
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    short_name: Mapped[str | None] = mapped_column(String(100))
    website_url: Mapped[str | None] = mapped_column(String(1000))

    benefits: Mapped[list[Benefit]] = relationship(back_populates="university")


class Benefit(TimestampMixin, db.Model):
    __tablename__ = "benefits"

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("olympiad_editions.id", ondelete="CASCADE"), index=True
    )
    university_id: Mapped[int | None] = mapped_column(
        ForeignKey("universities.id", ondelete="SET NULL"), index=True
    )
    benefit_type: Mapped[BenefitType] = mapped_column(enum_type(BenefitType), nullable=False)
    has_bvi: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_hundred_points: Mapped[bool] = mapped_column(default=False, nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    diploma_requirement: Mapped[str | None] = mapped_column(String(255))
    ege_subject: Mapped[str | None] = mapped_column(String(160))
    ege_min_score: Mapped[int | None] = mapped_column(db.SmallInteger)
    admission_year: Mapped[int | None] = mapped_column(db.SmallInteger)
    source_url: Mapped[str | None] = mapped_column(String(1000))

    edition: Mapped[OlympiadEdition] = relationship(back_populates="benefits")
    university: Mapped[University | None] = relationship(back_populates="benefits")


class SourceLink(TimestampMixin, db.Model):
    __tablename__ = "source_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("olympiad_editions.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000))
    publisher: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str | None] = mapped_column(String(80))
    source_year: Mapped[str | None] = mapped_column(String(9))
    accessed_on: Mapped[date | None] = mapped_column(db.Date)

    edition: Mapped[OlympiadEdition] = relationship(back_populates="sources")


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("oidc_issuer", "oidc_subject", name="user_oidc_identity"),
        CheckConstraint("grade IS NULL OR grade BETWEEN 5 AND 11", name="valid_grade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    oidc_issuer: Mapped[str] = mapped_column(String(255))
    oidc_subject: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    preferred_username: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    crm_role: Mapped[str | None] = mapped_column(String(80))
    object_type: Mapped[str | None] = mapped_column(String(80))
    grade: Mapped[int | None] = mapped_column(db.SmallInteger)
    last_login_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)

    plans: Mapped[list[UserOlympiadPlan]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserOlympiadPlan(TimestampMixin, db.Model):
    __tablename__ = "user_olympiad_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "edition_id", name="user_edition_plan"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("olympiad_editions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[PlanStatus] = mapped_column(
        enum_type(PlanStatus), default=PlanStatus.PLANNED, nullable=False, index=True
    )
    is_name_public: Mapped[bool] = mapped_column(default=True, nullable=False)
    reminders_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    reminder_days_before: Mapped[list[int]] = mapped_column(
        db.JSON, default=lambda: [7, 1], nullable=False
    )

    user: Mapped[User] = relationship(back_populates="plans")
    edition: Mapped[OlympiadEdition] = relationship(back_populates="plans")
    stage_progress: Mapped[list[UserStageProgress]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    reminder_dispatches: Mapped[list[ReminderDispatch]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class UserStageProgress(TimestampMixin, db.Model):
    __tablename__ = "user_stage_progress"
    __table_args__ = (
        UniqueConstraint("plan_id", "stage_id", name="plan_stage_progress"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("user_olympiad_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participated: Mapped[bool] = mapped_column(default=False, nullable=False)
    advanced: Mapped[bool | None] = mapped_column(nullable=True)
    result: Mapped[str | None] = mapped_column(String(500))

    plan: Mapped[UserOlympiadPlan] = relationship(back_populates="stage_progress")
    stage: Mapped[Stage] = relationship(back_populates="user_progress")


class ReminderDispatch(TimestampMixin, db.Model):
    __tablename__ = "reminder_dispatches"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "stage_id",
            "event_on",
            "days_before",
            name="reminder_plan_stage_event_day",
        ),
        CheckConstraint(
            "days_before BETWEEN 0 AND 90", name="valid_reminder_days_before"
        ),
        CheckConstraint("attempt_count >= 0", name="nonnegative_attempt_count"),
        CheckConstraint(
            "length(idempotency_key) BETWEEN 8 AND 128",
            name="valid_idempotency_key_length",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("user_olympiad_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_on: Mapped[date] = mapped_column(db.Date, nullable=False)
    scheduled_for: Mapped[date] = mapped_column(db.Date, nullable=False, index=True)
    days_before: Mapped[int] = mapped_column(db.SmallInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    payload: Mapped[dict] = mapped_column(db.JSON, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        enum_type(ReminderStatus),
        default=ReminderStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        db.DateTime(timezone=True), index=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True))
    response_status: Mapped[int | None] = mapped_column(db.SmallInteger)
    last_error: Mapped[str | None] = mapped_column(String(100))

    plan: Mapped[UserOlympiadPlan] = relationship(back_populates="reminder_dispatches")
    stage: Mapped[Stage] = relationship(back_populates="reminder_dispatches")
