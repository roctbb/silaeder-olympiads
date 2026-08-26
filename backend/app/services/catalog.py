from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from ..extensions import db
from ..models import (
    Benefit,
    BenefitType,
    DataStatus,
    DatePrecision,
    EditionGrade,
    EditionStatus,
    EventFormat,
    Geography,
    Material,
    MaterialType,
    Olympiad,
    OlympiadEdition,
    RegistrationStatus,
    RegistryStatus,
    SourceLink,
    Stage,
    University,
)
from .directions import directions_for_profile


class ValidationError(ValueError):
    pass


class ConflictError(ValueError):
    pass


def iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _utcnow() -> datetime:
    """Clock seam for deadline-sensitive public serialization."""

    return datetime.now(UTC)


def enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def parse_date(value: str | date | None, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Поле {field} должно быть датой в формате YYYY-MM-DD") from exc


def parse_aware_datetime(value: str | datetime | None, field: str) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(
                text[:-1] + "+00:00" if text.endswith("Z") else text
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Поле {field} должно быть ISO datetime с часовым поясом"
            ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(
            f"Поле {field} должно быть ISO datetime с часовым поясом"
        )
    return parsed.astimezone(UTC)


def parse_enum(enum_class, value: str | None, field: str, default=None):
    if value in (None, ""):
        return default
    try:
        return enum_class(value)
    except ValueError as exc:
        allowed = ", ".join(enum_class.values())
        raise ValidationError(f"Недопустимое значение {field}. Возможны: {allowed}") from exc


def serialize_stage(stage: Stage) -> dict[str, Any]:
    return {
        "id": stage.id,
        "key": stage.key,
        "name": stage.name,
        "stage_type": stage.stage_type,
        "position": stage.position,
        "is_active": stage.is_active,
        "starts_on": iso(stage.starts_on),
        "ends_on": iso(stage.ends_on),
        "registration_opens_on": iso(stage.registration_opens_on),
        "registration_closes_on": iso(stage.registration_closes_on),
        "date_precision": enum_value(stage.date_precision),
        "is_date_confirmed": stage.is_date_confirmed,
        "format": enum_value(stage.format),
        "location": stage.location,
        "details": stage.details,
        "source_url": stage.source_url,
    }


def serialize_material(material: Material) -> dict[str, Any]:
    return {
        "id": material.id,
        "title": material.title,
        "material_type": enum_value(material.material_type),
        "year": material.year,
        "url": material.url,
        "is_official": material.is_official,
    }


def serialize_benefit(benefit: Benefit) -> dict[str, Any]:
    university = benefit.university
    return {
        "id": benefit.id,
        "benefit_type": enum_value(benefit.benefit_type),
        "has_bvi": benefit.has_bvi,
        "has_hundred_points": benefit.has_hundred_points,
        "title": benefit.title,
        "description": benefit.description,
        "diploma_requirement": benefit.diploma_requirement,
        "ege_subject": benefit.ege_subject,
        "ege_min_score": benefit.ege_min_score,
        "admission_year": benefit.admission_year,
        "source_url": benefit.source_url,
        "university": (
            {
                "slug": university.slug,
                "name": university.name,
                "short_name": university.short_name,
                "website_url": university.website_url,
            }
            if university
            else None
        ),
    }


def serialize_benefit_summary(benefit: Benefit) -> dict[str, Any]:
    university = benefit.university
    return {
        "benefit_type": enum_value(benefit.benefit_type),
        "has_bvi": benefit.has_bvi,
        "has_hundred_points": benefit.has_hundred_points,
        "admission_year": benefit.admission_year,
        "university": (
            {
                "slug": university.slug,
                "name": university.name,
                "short_name": university.short_name,
            }
            if university
            else None
        ),
    }


def serialize_source(source: SourceLink) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "publisher": source.publisher,
        "source_type": source.source_type,
        "source_year": source.source_year,
        "accessed_on": iso(source.accessed_on),
    }


def _next_stage(edition: OlympiadEdition) -> Stage | None:
    today = date.today()
    future = [
        stage
        for stage in edition.stages
        if stage.is_active and (stage.ends_on or stage.starts_on or today) >= today
    ]
    return min(
        future,
        key=lambda stage: (stage.starts_on or stage.ends_on or date.max),
        default=None,
    )


def serialize_olympiad(
    olympiad: Olympiad,
    edition: OlympiadEdition,
    *,
    detailed: bool = False,
    hide_expired_registration: bool = False,
    include_benefit_summary: bool = False,
) -> dict[str, Any]:
    next_stage = _next_stage(edition)
    registration_url = edition.registration_url
    registration_status = edition.registration_status
    if hide_expired_registration and registration_status != RegistrationStatus.OPEN:
        registration_url = None
    if hide_expired_registration and edition.registration_closes_at:
        closes_at = edition.registration_closes_at
        if closes_at.tzinfo is None or closes_at.utcoffset() is None:
            closes_at = closes_at.replace(tzinfo=UTC)
        if _utcnow() >= closes_at.astimezone(UTC):
            registration_url = None
            registration_status = RegistrationStatus.NOT_OPEN
    result: dict[str, Any] = {
        "id": olympiad.id,
        "edition_id": edition.id,
        "slug": olympiad.slug,
        "name": olympiad.name,
        "family_name": olympiad.family_name,
        "profile": olympiad.profile,
        "directions": [
            direction.as_dict() for direction in directions_for_profile(olympiad.profile)
        ],
        "description": olympiad.description,
        "organizer": olympiad.organizer,
        "website_url": olympiad.website_url,
        "logo_url": olympiad.logo_url,
        "geography": enum_value(olympiad.geography),
        "is_team": olympiad.is_team,
        "academic_year": edition.academic_year,
        "cycle_label": edition.cycle_label,
        "status": enum_value(edition.status),
        "data_status": enum_value(edition.data_status),
        "is_in_registry": edition.is_in_registry,
        "registry_status": enum_value(edition.registry_status),
        "registry_level": edition.registry_level,
        "is_popular": edition.is_popular,
        "registration_status": enum_value(registration_status),
        "registration_checked_on": iso(edition.registration_checked_on),
        "registration_url": registration_url,
        "registration_closes_at": iso_datetime(edition.registration_closes_at),
        "previous_year_reference": edition.previous_year_reference,
        "eligibility_notes": edition.eligibility_notes,
        "notes": edition.notes,
        "grades": [item.grade for item in edition.grades],
        "next_stage": serialize_stage(next_stage) if next_stage else None,
        "stages_count": sum(stage.is_active for stage in edition.stages),
        "materials_count": len(olympiad.materials),
        "benefits_count": len(edition.benefits),
    }
    if include_benefit_summary:
        result["benefit_summary"] = [
            serialize_benefit_summary(item) for item in edition.benefits
        ]
    if detailed:
        result.update(
            stages=[serialize_stage(item) for item in edition.stages if item.is_active],
            materials=[serialize_material(item) for item in olympiad.materials],
            benefits=[serialize_benefit(item) for item in edition.benefits],
            sources=[serialize_source(item) for item in edition.sources],
            updated_at=edition.updated_at.isoformat() if edition.updated_at else None,
        )
    return result


def _required_text(
    payload: dict[str, Any], field: str, max_length: int | None = None
) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ValidationError(f"Поле {field} обязательно")
    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"Поле {field} длиннее {max_length} символов")
    return value


def _optional_text(value: Any, field: str, max_length: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ValidationError(f"Поле {field} длиннее {max_length} символов")
    return text


def _url(
    value: Any, field: str, *, required: bool = False, max_length: int = 1000
) -> str | None:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValidationError(f"Поле {field} обязательно")
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"Поле {field} должно содержать абсолютный HTTP(S) URL")
    if len(text) > max_length:
        raise ValidationError(f"Поле {field} длиннее {max_length} символов")
    return text


def _integer(value: Any, field: str, minimum: int | None = None, maximum: int | None = None):
    if value in (None, ""):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Поле {field} должно быть целым числом") from exc
    if minimum is not None and result < minimum:
        raise ValidationError(f"Поле {field} должно быть не меньше {minimum}")
    if maximum is not None and result > maximum:
        raise ValidationError(f"Поле {field} должно быть не больше {maximum}")
    return result


def _boolean(value: Any, field: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError(f"Поле {field} должно быть логическим")
    return value


def _replace_grades(edition: OlympiadEdition, grades: list[Any]) -> None:
    parsed: list[int] = []
    for item in grades:
        grade = _integer(item, "grades", 5, 11)
        if grade is None:
            raise ValidationError("Класс не может быть пустым")
        parsed.append(grade)
    parsed = sorted(set(parsed))
    edition.grades = [EditionGrade(grade=grade) for grade in parsed]


def _replace_stages(edition: OlympiadEdition, items: list[dict[str, Any]]) -> None:
    existing_by_id = {stage.id: stage for stage in edition.stages if stage.id is not None}
    existing_by_key = {stage.key: stage for stage in edition.stages if stage.key}
    existing_by_position: dict[int, Stage] = {}
    for stage in edition.stages:
        existing_by_position.setdefault(stage.position, stage)

    stages: list[Stage] = []
    used_existing_ids: set[int] = set()
    used_keys: set[str] = set()
    legacy_key_transition = bool(edition.stages) and all(
        stage.key.startswith("legacy-") for stage in edition.stages
    )
    for index, item in enumerate(items):
        position = _integer(item.get("position", index), "position", 0) or 0
        requested_id = _integer(item.get("id"), "id", 1)
        explicit_key = str(item.get("key") or "").strip()
        requested_key = explicit_key or _generated_stage_key(item)
        if requested_key and not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,159}", requested_key):
            raise ValidationError(
                "Поле stages.key должно содержать только строчные латинские буквы, "
                "цифры, точку, дефис или подчёркивание"
            )

        if explicit_key and requested_id is not None:
            stage = existing_by_id.get(requested_id)
            if stage is None:
                raise ValidationError("Этап с указанным id не принадлежит этой олимпиаде")
            if stage.key != requested_key:
                raise ValidationError("Ключ этапа не соответствует указанному id")
        elif requested_id is not None:
            stage = existing_by_id.get(requested_id)
            if stage is None:
                raise ValidationError("Этап с указанным id не принадлежит этой олимпиаде")
            if explicit_key and stage.key != requested_key:
                raise ValidationError("Ключ этапа не соответствует указанному id")
            requested_key = explicit_key or stage.key
        elif requested_key in existing_by_key:
            stage = existing_by_key[requested_key]
        elif legacy_key_transition:
            candidate = existing_by_position.get(position)
            stage = (
                candidate
                if candidate is not None and candidate.id not in used_existing_ids
                else Stage()
            )
        else:
            stage = Stage()

        if stage.id is not None:
            if stage.id in used_existing_ids:
                raise ValidationError("Один этап нельзя указать в списке дважды")
            used_existing_ids.add(stage.id)

        if requested_key in used_keys:
            raise ValidationError("Ключ этапа должен быть уникальным в рамках олимпиады")
        used_keys.add(requested_key)

        stage.key = requested_key
        stage.is_active = True
        stage.name = _required_text(item, "name", 180)
        stage.stage_type = _optional_text(item.get("stage_type"), "stage_type", 80)
        stage.position = position
        stage.starts_on = parse_date(item.get("starts_on"), "starts_on")
        stage.ends_on = parse_date(item.get("ends_on"), "ends_on")
        stage.registration_opens_on = parse_date(
            item.get("registration_opens_on"), "registration_opens_on"
        )
        stage.registration_closes_on = parse_date(
            item.get("registration_closes_on"), "registration_closes_on"
        )
        stage.date_precision = parse_enum(
            DatePrecision,
            item.get("date_precision"),
            "date_precision",
            DatePrecision.TBA,
        )
        stage.is_date_confirmed = bool(item.get("is_date_confirmed", False))
        stage.format = parse_enum(
            EventFormat, item.get("format"), "format", EventFormat.UNKNOWN
        )
        stage.location = _optional_text(item.get("location"), "location", 500)
        stage.details = item.get("details") or None
        stage.source_url = _url(item.get("source_url"), "source_url")
        if stage.starts_on and stage.ends_on and stage.ends_on < stage.starts_on:
            raise ValidationError(f"У этапа «{stage.name}» дата окончания раньше начала")
        if (
            stage.registration_opens_on
            and stage.registration_closes_on
            and stage.registration_closes_on < stage.registration_opens_on
        ):
            raise ValidationError(
                f"У этапа «{stage.name}» регистрация закрывается раньше открытия"
            )
        stages.append(stage)

    active_ids = {stage.id for stage in stages if stage.id is not None}
    for existing in edition.stages:
        if existing.id is not None and existing.id not in active_ids:
            existing.is_active = False
    for stage in stages:
        if stage not in edition.stages:
            edition.stages.append(stage)


def _generated_stage_key(item: dict[str, Any]) -> str:
    """Compatibility fallback; catalog builders should always provide an explicit key."""
    identity = "\x1f".join(
        str(item.get(field) or "").strip().casefold()
        for field in ("stage_type", "name")
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"stage-{digest}"


def _replace_materials(olympiad: Olympiad, items: list[dict[str, Any]]) -> None:
    olympiad.materials = [
        Material(
            title=_required_text(item, "title", 255),
            material_type=parse_enum(
                MaterialType, item.get("material_type"), "material_type", MaterialType.OTHER
            ),
            year=_integer(item.get("year"), "year", 1990, 2100),
            url=_url(item.get("url"), "url", required=True),
            is_official=bool(item.get("is_official", True)),
        )
        for item in items
    ]


def _university_from_payload(item: dict[str, Any]) -> University | None:
    data = item.get("university")
    if not data:
        return None
    if isinstance(data, str):
        data = {"name": data, "slug": data.lower().replace(" ", "-")}
    slug = _required_text(data, "slug", 180)
    university = db.session.scalar(select(University).where(University.slug == slug))
    if university is None:
        university = University(
            slug=slug,
            name=_required_text(data, "name", 255),
            short_name=_optional_text(data.get("short_name"), "university.short_name", 100),
            website_url=_url(data.get("website_url"), "university.website_url"),
        )
        db.session.add(university)
    else:
        # A benefit payload references a shared university; it is not the university editor.
        # Only fill missing metadata so saving a stale olympiad cannot overwrite newer data.
        if not university.short_name and data.get("short_name"):
            university.short_name = _optional_text(
                data["short_name"], "university.short_name", 100
            )
        if not university.website_url and data.get("website_url"):
            university.website_url = _url(
                data.get("website_url"), "university.website_url"
            )
    return university


def _replace_benefits(edition: OlympiadEdition, items: list[dict[str, Any]]) -> None:
    benefits: list[Benefit] = []
    with db.session.no_autoflush:
        for item in items:
            parsed_type = parse_enum(
                BenefitType,
                item.get("benefit_type"),
                "benefit_type",
                BenefitType.OTHER,
            )
            has_bvi = _boolean(
                item.get("has_bvi"),
                "benefits.has_bvi",
                default=parsed_type == BenefitType.BVI,
            )
            has_hundred_points = _boolean(
                item.get("has_hundred_points"),
                "benefits.has_hundred_points",
                default=parsed_type == BenefitType.HUNDRED_POINTS,
            )
            if parsed_type == BenefitType.BVI and not has_bvi:
                raise ValidationError(
                    "Льгота типа bvi должна иметь benefits.has_bvi=true"
                )
            if parsed_type == BenefitType.HUNDRED_POINTS and not has_hundred_points:
                raise ValidationError(
                    "Льгота типа hundred_points должна иметь "
                    "benefits.has_hundred_points=true"
                )
            benefits.append(
                Benefit(
                    university=_university_from_payload(item),
                    benefit_type=parsed_type,
                    has_bvi=has_bvi,
                    has_hundred_points=has_hundred_points,
                    title=_required_text(item, "title", 255),
                    description=item.get("description") or None,
                    diploma_requirement=_optional_text(
                        item.get("diploma_requirement"), "diploma_requirement", 255
                    ),
                    ege_subject=_optional_text(item.get("ege_subject"), "ege_subject", 160),
                    ege_min_score=_integer(item.get("ege_min_score"), "ege_min_score", 0, 100),
                    admission_year=_integer(
                        item.get("admission_year"), "admission_year", 2000, 2100
                    ),
                    source_url=_url(item.get("source_url"), "source_url"),
                )
            )
        edition.benefits = benefits


def _replace_sources(edition: OlympiadEdition, items: list[dict[str, Any]]) -> None:
    edition.sources = [
        SourceLink(
            title=_required_text(item, "title", 255),
            url=_url(item.get("url"), "url", required=True),
            publisher=_optional_text(item.get("publisher"), "publisher", 255),
            source_type=_optional_text(item.get("source_type"), "source_type", 80),
            source_year=_optional_text(item.get("source_year"), "source_year", 9),
            accessed_on=parse_date(item.get("accessed_on"), "accessed_on"),
        )
        for item in items
    ]


def upsert_catalog_record(
    payload: dict[str, Any],
    olympiad: Olympiad | None = None,
) -> tuple[Olympiad, OlympiadEdition]:
    slug = _required_text(payload, "slug", 180)
    academic_year = _required_text(payload, "academic_year", 9)
    if olympiad is None:
        olympiad = db.session.scalar(select(Olympiad).where(Olympiad.slug == slug))
    if olympiad is None:
        olympiad = Olympiad(slug=slug)
        db.session.add(olympiad)
    elif olympiad.slug != slug:
        duplicate = db.session.scalar(select(Olympiad).where(Olympiad.slug == slug))
        if duplicate and duplicate.id != olympiad.id:
            raise ValidationError("Олимпиада с таким slug уже существует")

    olympiad.slug = slug
    olympiad.name = _required_text(payload, "name", 255)
    olympiad.family_name = _required_text(payload, "family_name", 255)
    olympiad.profile = _required_text(payload, "profile", 160)
    olympiad.description = payload.get("description") or None
    olympiad.organizer = _optional_text(payload.get("organizer"), "organizer", 255)
    olympiad.website_url = _url(payload.get("website_url"), "website_url", required=True)
    olympiad.logo_url = _url(payload.get("logo_url"), "logo_url")
    olympiad.geography = parse_enum(
        Geography, payload.get("geography"), "geography", Geography.RUSSIA
    )
    olympiad.is_team = bool(payload.get("is_team", False))

    edition = next(
        (item for item in olympiad.editions if item.academic_year == academic_year), None
    )
    if edition is None:
        edition = OlympiadEdition(academic_year=academic_year)
        olympiad.editions.append(edition)

    edition.cycle_label = _optional_text(
        payload.get("cycle_label"), "cycle_label", 120
    )
    edition.status = parse_enum(
        EditionStatus, payload.get("status"), "status", EditionStatus.DRAFT
    )
    edition.data_status = parse_enum(
        DataStatus,
        payload.get("data_status"),
        "data_status",
        DataStatus.ANNOUNCEMENT_PENDING,
    )
    edition.registry_level = _integer(payload.get("registry_level"), "registry_level", 1, 3)
    requested_registry_flag = bool(payload.get("is_in_registry", False))
    default_registry_status = edition.registry_status or (
        RegistryStatus.APPROVED
        if requested_registry_flag or edition.registry_level is not None
        else RegistryStatus.NOT_LISTED
    )
    edition.registry_status = parse_enum(
        RegistryStatus,
        payload.get("registry_status"),
        "registry_status",
        default_registry_status,
    )
    edition.is_in_registry = edition.registry_status != RegistryStatus.NOT_LISTED
    if "is_in_registry" in payload and requested_registry_flag != edition.is_in_registry:
        raise ValidationError(
            "Поля registry_status и is_in_registry противоречат друг другу"
        )
    if not edition.is_in_registry and edition.registry_level is not None:
        raise ValidationError(
            "У олимпиады вне перечня не может быть уровня перечня"
        )
    edition.is_popular = bool(payload.get("is_popular", False))
    edition.registration_url = _url(payload.get("registration_url"), "registration_url")
    default_registration_status = edition.registration_status or (
        RegistrationStatus.OPEN
        if edition.registration_url
        else RegistrationStatus.NOT_FOUND
    )
    edition.registration_status = parse_enum(
        RegistrationStatus,
        payload.get("registration_status"),
        "registration_status",
        default_registration_status,
    )
    edition.registration_checked_on = parse_date(
        payload.get("registration_checked_on"), "registration_checked_on"
    )
    edition.registration_closes_at = parse_aware_datetime(
        payload.get("registration_closes_at"), "registration_closes_at"
    )
    if edition.registration_closes_at and not edition.registration_url:
        raise ValidationError(
            "Поле registration_closes_at нельзя задать без registration_url"
        )
    if (
        edition.registration_status == RegistrationStatus.OPEN
        and not edition.registration_url
    ):
        raise ValidationError(
            "Для открытой регистрации обязательно поле registration_url"
        )
    if (
        edition.registration_status != RegistrationStatus.OPEN
        and edition.registration_url
    ):
        raise ValidationError(
            "registration_url допустим только для открытой регистрации"
        )
    edition.previous_year_reference = _optional_text(
        payload.get("previous_year_reference"), "previous_year_reference", 9
    )
    edition.eligibility_notes = _optional_text(
        payload.get("eligibility_notes"), "eligibility_notes", 4000
    )
    edition.notes = payload.get("notes") or None

    _replace_grades(edition, payload.get("grades", []))
    _replace_stages(edition, payload.get("stages", []))
    _replace_materials(olympiad, payload.get("materials", []))
    _replace_benefits(edition, payload.get("benefits", []))
    _replace_sources(edition, payload.get("sources", []))
    edition.updated_at = datetime.now(UTC)
    olympiad.updated_at = datetime.now(UTC)
    return olympiad, edition


def create_catalog_record(
    payload: dict[str, Any],
) -> tuple[Olympiad, OlympiadEdition]:
    """Create a new stable olympiad identity without falling back to upsert semantics."""
    slug = _required_text(payload, "slug", 180)
    if db.session.scalar(select(Olympiad.id).where(Olympiad.slug == slug)) is not None:
        raise ConflictError("Олимпиада с таким slug уже существует")
    olympiad = Olympiad(slug=slug)
    db.session.add(olympiad)
    return upsert_catalog_record(payload, olympiad)
