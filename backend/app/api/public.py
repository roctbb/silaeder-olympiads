from calendar import monthrange
from datetime import date

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from ..extensions import db
from ..models import (
    Benefit,
    BenefitType,
    EditionGrade,
    EditionStatus,
    Olympiad,
    OlympiadEdition,
    RegistrationStatus,
    RegistryStatus,
    Stage,
    University,
    User,
    UserOlympiadPlan,
)
from ..services import catalog as catalog_service
from ..services import directions as direction_service
from ..services.catalog import serialize_olympiad, serialize_stage

public_bp = Blueprint("public", __name__)

PUBLIC_BENEFIT_TYPES = (
    BenefitType.BVI,
    BenefitType.HUNDRED_POINTS,
    BenefitType.OTHER,
    BenefitType.PRIZE,
)


def _benefit_type_criterion(benefit_type: BenefitType):
    if benefit_type == BenefitType.BVI:
        return Benefit.has_bvi.is_(True)
    if benefit_type == BenefitType.HUNDRED_POINTS:
        return Benefit.has_hundred_points.is_(True)
    return Benefit.benefit_type == benefit_type


def _base_query(*, calendar_only: bool = False):
    options = [
        joinedload(OlympiadEdition.olympiad),
        selectinload(OlympiadEdition.grades),
        selectinload(OlympiadEdition.stages),
    ]
    if not calendar_only:
        options.extend(
            [
                joinedload(OlympiadEdition.olympiad).selectinload(Olympiad.materials),
                selectinload(OlympiadEdition.benefits).selectinload(Benefit.university),
                selectinload(OlympiadEdition.sources),
            ]
        )
    return (
        select(OlympiadEdition)
        .join(Olympiad, OlympiadEdition.olympiad_id == Olympiad.id)
        .options(*options)
        .where(OlympiadEdition.status == EditionStatus.PUBLISHED)
    )


def _bool_arg(name: str) -> bool | None:
    value = request.args.get(name)
    if value is None or value == "":
        return None
    return value.lower() in {"1", "true", "yes", "on"}


def _registration_status_criteria(raw_status: str):
    if not raw_status:
        return ()
    try:
        requested_status = RegistrationStatus(raw_status)
    except ValueError as exc:
        raise ValueError("Неизвестный статус регистрации") from exc

    now = catalog_service._utcnow()
    if requested_status == RegistrationStatus.OPEN:
        return (
            OlympiadEdition.registration_status == RegistrationStatus.OPEN,
            or_(
                OlympiadEdition.registration_closes_at.is_(None),
                OlympiadEdition.registration_closes_at > now,
            ),
        )
    if requested_status == RegistrationStatus.NOT_OPEN:
        return (
            or_(
                OlympiadEdition.registration_status == RegistrationStatus.NOT_OPEN,
                and_(
                    OlympiadEdition.registration_status == RegistrationStatus.OPEN,
                    OlympiadEdition.registration_closes_at.is_not(None),
                    OlympiadEdition.registration_closes_at <= now,
                ),
            ),
        )
    return (OlympiadEdition.registration_status == requested_status,)


def _registration_available_criterion():
    now = catalog_service._utcnow()
    open_now = and_(
        OlympiadEdition.registration_status == RegistrationStatus.OPEN,
        or_(
            OlympiadEdition.registration_closes_at.is_(None),
            OlympiadEdition.registration_closes_at > now,
        ),
    )
    registration_announced = (
        OlympiadEdition.registration_status == RegistrationStatus.ANNOUNCED
    )
    registration_not_published_yet = (
        OlympiadEdition.registration_status == RegistrationStatus.NOT_FOUND
    )
    registration_not_open_yet = (
        OlympiadEdition.registration_status == RegistrationStatus.NOT_OPEN
    )
    return or_(
        open_now,
        registration_announced,
        registration_not_published_yet,
        registration_not_open_yet,
    )


def _filtered_editions_query(*, calendar_only: bool = False):
    query = _base_query(calendar_only=calendar_only)
    academic_year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    query = query.where(OlympiadEdition.academic_year == academic_year)

    search = request.args.get("q", "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Olympiad.name.ilike(pattern),
                Olympiad.family_name.ilike(pattern),
                Olympiad.profile.ilike(pattern),
                Olympiad.organizer.ilike(pattern),
            )
        )

    profile = request.args.get("profile", "").strip()
    if profile:
        query = query.where(Olympiad.profile.ilike(profile))

    direction_slug = request.args.get("direction", "").strip()
    if direction_slug:
        if direction_service.direction_by_slug(direction_slug) is None:
            raise ValueError("Неизвестное направление")
        profiles = direction_service.profile_names_for_direction(direction_slug)
        direction_criterion = Olympiad.profile.in_(profiles)
        if direction_slug == direction_service.FALLBACK_DIRECTION_SLUG:
            direction_criterion = or_(
                direction_criterion,
                Olympiad.profile.notin_(direction_service.MAPPED_PROFILES),
            )
        query = query.where(direction_criterion)

    grade = request.args.get("grade", type=int)
    if grade:
        query = query.where(
            or_(
                OlympiadEdition.grades.any(EditionGrade.grade == grade),
                ~OlympiadEdition.grades.any(),
            )
        )

    level = request.args.get("registry_level", type=int)
    if level:
        query = query.where(OlympiadEdition.registry_level == level)

    registry_status = request.args.get("registry_status", "").strip()
    if registry_status:
        try:
            query = query.where(
                OlympiadEdition.registry_status == RegistryStatus(registry_status)
            )
        except ValueError as exc:
            raise ValueError("Неизвестный статус перечня") from exc

    query = query.where(
        *_registration_status_criteria(
            request.args.get("registration_status", "").strip()
        )
    )
    registration_available = _bool_arg("registration_available")
    if registration_available is not None:
        criterion = _registration_available_criterion()
        query = query.where(
            criterion if registration_available else ~criterion
        )

    benefit_criteria = []
    benefit_type = request.args.get("benefit_type", "").strip()
    if benefit_type:
        try:
            requested_benefit_type = BenefitType(benefit_type)
        except ValueError as exc:
            raise ValueError("Неизвестный тип льготы") from exc
        if requested_benefit_type not in PUBLIC_BENEFIT_TYPES:
            raise ValueError("Неизвестный тип льготы")
        benefit_criteria.append(_benefit_type_criterion(requested_benefit_type))

    university_slug = request.args.get("university", "").strip()
    if university_slug:
        benefit_criteria.append(
            Benefit.university.has(University.slug == university_slug)
        )
        if not benefit_type:
            benefit_criteria.append(Benefit.benefit_type != BenefitType.PRIZE)

    if benefit_criteria:
        # Keep all conditions inside one EXISTS so a combined filter cannot be
        # satisfied by two different benefits of the same olympiad edition.
        query = query.where(
            OlympiadEdition.benefits.any(and_(*benefit_criteria))
        )

    for argument, column in (
        ("popular", OlympiadEdition.is_popular),
        ("in_registry", OlympiadEdition.is_in_registry),
        ("team", Olympiad.is_team),
    ):
        value = _bool_arg(argument)
        if value is not None:
            query = query.where(column.is_(value))

    if _bool_arg("upcoming"):
        query = query.where(
            OlympiadEdition.stages.any(
                and_(
                    Stage.is_active.is_(True),
                    or_(Stage.ends_on >= date.today(), Stage.starts_on >= date.today()),
                )
            )
        )

    return query


def _calendar_range() -> tuple[date, date]:
    month = request.args.get("month", "").strip()
    if not month:
        today = date.today()
        year, month_number = today.year, today.month
    else:
        try:
            year_text, month_text = month.split("-", maxsplit=1)
            year, month_number = int(year_text), int(month_text)
            if month != f"{year:04d}-{month_number:02d}":
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError("Месяц должен быть в формате YYYY-MM") from exc

    try:
        starts_on = date(year, month_number, 1)
        ends_on = date(year, month_number, monthrange(year, month_number)[1])
    except ValueError as exc:
        raise ValueError("Месяц должен быть в формате YYYY-MM") from exc
    return starts_on, ends_on


@public_bp.get("/olympiads")
def olympiad_list():
    try:
        query = _filtered_editions_query()
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    requested_grade = request.args.get("grade", type=int)
    ordering = []
    if requested_grade:
        ordering.append(
            case(
                (
                    OlympiadEdition.grades.any(
                        EditionGrade.grade == requested_grade
                    ),
                    0,
                ),
                else_=1,
            )
        )
    query = query.order_by(
        *ordering,
        OlympiadEdition.is_popular.desc(),
        Olympiad.family_name,
        Olympiad.profile,
    )
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 24, type=int), 1), 100)
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    edition_ids = [item.id for item in pagination.items]
    participant_counts = dict(
        db.session.execute(
            select(UserOlympiadPlan.edition_id, func.count(UserOlympiadPlan.id))
            .where(UserOlympiadPlan.edition_id.in_(edition_ids))
            .group_by(UserOlympiadPlan.edition_id)
        ).all()
    ) if edition_ids else {}
    items = []
    for edition in pagination.items:
        payload = serialize_olympiad(
            edition.olympiad,
            edition,
            hide_expired_registration=True,
            include_benefit_summary=True,
        )
        payload["participant_count"] = participant_counts.get(edition.id, 0)
        if requested_grade:
            payload["grade_match"] = (
                "exact"
                if any(item.grade == requested_grade for item in edition.grades)
                else "unknown"
            )
        items.append(payload)
    return jsonify(
        items=items,
        pagination={
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
            "total": pagination.total,
        },
    )


@public_bp.get("/calendar")
def calendar_events():
    try:
        starts_on, ends_on = _calendar_range()
        query = _filtered_editions_query(calendar_only=True)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    stage_starts_on = func.coalesce(Stage.starts_on, Stage.ends_on)
    stage_ends_on = func.coalesce(Stage.ends_on, Stage.starts_on)
    query = query.where(
        OlympiadEdition.stages.any(
            and_(
                Stage.is_active.is_(True),
                stage_starts_on <= ends_on,
                stage_ends_on >= starts_on,
            )
        )
    ).order_by(
        OlympiadEdition.is_popular.desc(), Olympiad.family_name, Olympiad.profile
    )
    editions = db.session.scalars(query).unique().all()

    events = []
    requested_grade = request.args.get("grade", type=int)
    for edition in editions:
        olympiad = edition.olympiad
        olympiad_summary = {
            "slug": olympiad.slug,
            "name": olympiad.name,
            "family_name": olympiad.family_name,
            "profile": olympiad.profile,
            "directions": [
                direction.as_dict()
                for direction in direction_service.directions_for_profile(
                    olympiad.profile
                )
            ],
            "is_team": olympiad.is_team,
            "is_popular": edition.is_popular,
            "cycle_label": edition.cycle_label,
            "data_status": edition.data_status.value,
            "registry_status": edition.registry_status.value,
            "registry_level": edition.registry_level,
            "grades": sorted(item.grade for item in edition.grades),
        }
        if requested_grade:
            olympiad_summary["grade_match"] = (
                "exact"
                if any(item.grade == requested_grade for item in edition.grades)
                else "unknown"
            )
        for stage in edition.stages:
            if not stage.is_active:
                continue
            stage_start = stage.starts_on or stage.ends_on
            stage_end = stage.ends_on or stage.starts_on
            if not stage_start or not stage_end:
                continue
            if stage_start <= ends_on and stage_end >= starts_on:
                events.append(
                    {
                        "id": stage.id,
                        "olympiad": olympiad_summary,
                        "stage": serialize_stage(stage),
                    }
                )

    events.sort(
        key=lambda event: (
            event["stage"]["starts_on"] or event["stage"]["ends_on"],
            event["stage"]["ends_on"] or event["stage"]["starts_on"],
            event["olympiad"]["name"],
            event["stage"]["position"],
        )
    )
    return jsonify(
        events=events,
        range={"starts_on": starts_on.isoformat(), "ends_on": ends_on.isoformat()},
        total=len(events),
    )


@public_bp.get("/olympiads/<slug>")
def olympiad_detail(slug: str):
    academic_year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    edition = db.session.scalar(
        _base_query().where(
            Olympiad.slug == slug,
            OlympiadEdition.academic_year == academic_year,
        )
    )
    if edition is None:
        return jsonify(error="Олимпиада не найдена"), 404
    payload = serialize_olympiad(
        edition.olympiad,
        edition,
        detailed=True,
        hide_expired_registration=True,
    )
    participant_count = db.session.scalar(
        select(func.count())
        .select_from(UserOlympiadPlan)
        .where(UserOlympiadPlan.edition_id == edition.id)
    ) or 0
    public_names = db.session.scalars(
        select(User.name)
        .join(UserOlympiadPlan, UserOlympiadPlan.user_id == User.id)
        .where(
            UserOlympiadPlan.edition_id == edition.id,
            UserOlympiadPlan.is_name_public.is_(True),
        )
        .order_by(User.name, User.id)
    ).all()
    payload["participant_count"] = participant_count
    payload["public_participants"] = [{"name": name} for name in public_names]
    return jsonify(payload)


@public_bp.get("/metadata")
def metadata():
    academic_year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    try:
        registration_criteria = _registration_status_criteria(
            request.args.get("registration_status", "").strip()
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    availability_criteria = ()
    registration_available = _bool_arg("registration_available")
    if registration_available is not None:
        criterion = _registration_available_criterion()
        availability_criteria = (
            criterion if registration_available else ~criterion,
        )
    published = (
        OlympiadEdition.academic_year == academic_year,
        OlympiadEdition.status == EditionStatus.PUBLISHED,
        *registration_criteria,
        *availability_criteria,
    )
    profile_counts = db.session.execute(
        select(
            Olympiad.profile,
            func.count(func.distinct(OlympiadEdition.id)),
        )
        .join(OlympiadEdition)
        .where(*published)
        .group_by(Olympiad.profile)
        .order_by(Olympiad.profile)
    ).all()
    profiles = [profile for profile, _count in profile_counts]
    direction_counts = direction_service.aggregate_direction_counts(profile_counts)
    total = db.session.scalar(select(func.count()).select_from(OlympiadEdition).where(*published))
    popular = db.session.scalar(
        select(func.count())
        .select_from(OlympiadEdition)
        .where(*published, OlympiadEdition.is_popular.is_(True))
    )
    registry = db.session.scalar(
        select(func.count())
        .select_from(OlympiadEdition)
        .where(*published, OlympiadEdition.is_in_registry.is_(True))
    )
    registry_counts = {
        status.value: db.session.scalar(
            select(func.count())
            .select_from(OlympiadEdition)
            .where(*published, OlympiadEdition.registry_status == status)
        )
        or 0
        for status in RegistryStatus
    }
    available_benefit_types = {
        benefit_type
        for benefit_type in PUBLIC_BENEFIT_TYPES
        if db.session.scalar(
            select(Benefit.id)
            .join(
                OlympiadEdition,
                Benefit.edition_id == OlympiadEdition.id,
            )
            .where(*published, _benefit_type_criterion(benefit_type))
            .limit(1)
        )
        is not None
    }
    universities = [
        {
            "slug": slug,
            "name": name,
            "short_name": short_name,
            "count": count,
        }
        for slug, name, short_name, count in db.session.execute(
            select(
                University.slug,
                University.name,
                University.short_name,
                func.count(func.distinct(Benefit.edition_id)),
            )
            .join(Benefit, Benefit.university_id == University.id)
            .join(
                OlympiadEdition,
                Benefit.edition_id == OlympiadEdition.id,
            )
            .where(*published, Benefit.benefit_type != BenefitType.PRIZE)
            .group_by(
                University.slug,
                University.name,
                University.short_name,
            )
            .order_by(University.name, University.slug)
        ).all()
    ]
    return jsonify(
        academic_year=academic_year,
        profiles=profiles,
        categories=[
            {
                **direction.as_dict(),
                "count": direction_counts[direction.slug],
            }
            for direction in direction_service.DIRECTIONS
            if direction_counts.get(direction.slug, 0) > 0
        ],
        grades=list(range(5, 12)),
        benefit_types=[
            benefit_type.value
            for benefit_type in PUBLIC_BENEFIT_TYPES
            if benefit_type in available_benefit_types
        ],
        universities=universities,
        registry_levels=[1, 2, 3],
        registry_statuses=RegistryStatus.values(),
        registration_statuses=RegistrationStatus.values(),
        counts={
            "total": total or 0,
            "popular": popular or 0,
            "registry": registry or 0,
            **{f"registry_{key}": value for key, value in registry_counts.items()},
        },
    )
