from __future__ import annotations

from datetime import date
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..auth import _serialize_user, csrf_protected, current_user, login_required
from ..extensions import db
from ..models import (
    EditionStatus,
    Olympiad,
    OlympiadEdition,
    PlanStatus,
    Stage,
    User,
    UserOlympiadPlan,
    UserStageProgress,
)

personal_bp = Blueprint("personal", __name__)


@personal_bp.after_request
def disable_personal_response_caching(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers.add("Vary", "Cookie")
    return response


class PayloadError(ValueError):
    pass


def _payload() -> dict[str, Any]:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise PayloadError("Ожидался JSON-объект")
    return value


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise PayloadError(f"Поле {field} должно быть логическим")
    return value


def _reminder_days(value: Any, *, allow_empty: bool = False) -> list[int]:
    minimum = 0 if allow_empty else 1
    if not isinstance(value, list) or not minimum <= len(value) <= 10:
        raise PayloadError(
            "reminder_days_before должен содержать от 1 до 10 дней "
            "(или быть пустым при выключенных напоминаниях)"
        )
    days: set[int] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 90:
            raise PayloadError("Дни напоминаний должны быть целыми числами от 0 до 90")
        days.add(item)
    return sorted(days, reverse=True)


def _academic_year() -> str:
    return request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])


def _edition(
    slug: str,
    *,
    statuses: tuple[EditionStatus, ...] = (EditionStatus.PUBLISHED,),
) -> OlympiadEdition | None:
    return db.session.scalar(
        select(OlympiadEdition)
        .join(Olympiad)
        .options(joinedload(OlympiadEdition.olympiad), selectinload(OlympiadEdition.stages))
        .where(
            Olympiad.slug == slug,
            OlympiadEdition.academic_year == _academic_year(),
            OlympiadEdition.status.in_(statuses),
        )
    )


def _plan_query(user_id: int, edition_id: int):
    return (
        select(UserOlympiadPlan)
        .options(
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
            joinedload(UserOlympiadPlan.edition).selectinload(OlympiadEdition.stages),
            selectinload(UserOlympiadPlan.stage_progress).joinedload(
                UserStageProgress.stage
            ),
        )
        .where(
            UserOlympiadPlan.user_id == user_id,
            UserOlympiadPlan.edition_id == edition_id,
        )
    )


def _plan(user_id: int, edition_id: int) -> UserOlympiadPlan | None:
    return db.session.scalar(_plan_query(user_id, edition_id))


def _olympiad_summary(edition: OlympiadEdition) -> dict[str, Any]:
    olympiad = edition.olympiad
    return {
        "slug": olympiad.slug,
        "name": olympiad.name,
        "family_name": olympiad.family_name,
        "profile": olympiad.profile,
    }


def _serialize_progress(progress: UserStageProgress) -> dict[str, Any]:
    return {
        "stage_id": progress.stage_id,
        "stage_key": progress.stage.key,
        "stage_name": progress.stage.name,
        "stage_is_active": progress.stage.is_active,
        "participated": progress.participated,
        "advanced": progress.advanced,
        "result": progress.result,
        "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,
    }


def _serialize_plan(plan: UserOlympiadPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "olympiad": _olympiad_summary(plan.edition),
        "academic_year": plan.edition.academic_year,
        "cycle_label": plan.edition.cycle_label,
        "edition_status": plan.edition.status.value,
        "status": plan.status.value,
        "is_name_public": plan.is_name_public,
        "reminders_enabled": plan.reminders_enabled,
        "reminder_days_before": list(plan.reminder_days_before),
        "stage_progress": [
            _serialize_progress(item)
            for item in sorted(
                plan.stage_progress,
                key=lambda progress: (progress.stage.position, progress.stage_id),
            )
        ],
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


def _apply_plan_payload(plan: UserOlympiadPlan, payload: dict[str, Any]) -> None:
    allowed = {
        "status",
        "is_name_public",
        "reminders_enabled",
        "reminder_days_before",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise PayloadError(f"Неизвестные поля: {', '.join(sorted(unknown))}")

    if "status" in payload:
        try:
            plan.status = PlanStatus(payload["status"])
        except (TypeError, ValueError) as exc:
            raise PayloadError(
                f"status должен быть одним из: {', '.join(PlanStatus.values())}"
            ) from exc
    if "is_name_public" in payload:
        plan.is_name_public = _strict_bool(payload["is_name_public"], "is_name_public")
    if "reminders_enabled" in payload:
        plan.reminders_enabled = _strict_bool(
            payload["reminders_enabled"], "reminders_enabled"
        )
    if "reminder_days_before" in payload:
        plan.reminder_days_before = _reminder_days(
            payload["reminder_days_before"], allow_empty=not plan.reminders_enabled
        )


def _participant_summary(edition_id: int) -> tuple[int, list[dict[str, str]]]:
    count = db.session.scalar(
        select(func.count())
        .select_from(UserOlympiadPlan)
        .where(UserOlympiadPlan.edition_id == edition_id)
    ) or 0
    names = db.session.scalars(
        select(User.name)
        .join(UserOlympiadPlan, UserOlympiadPlan.user_id == User.id)
        .where(
            UserOlympiadPlan.edition_id == edition_id,
            UserOlympiadPlan.is_name_public.is_(True),
        )
        .order_by(User.name, User.id)
    ).all()
    return count, [{"name": name} for name in names]


@personal_bp.get("/me")
@login_required
def me():
    return jsonify(user=_serialize_user(current_user()))


@personal_bp.patch("/me")
@login_required
@csrf_protected
def update_me():
    return jsonify(error="Класс синхронизируется из ЛК Силаэдр при входе"), 409


@personal_bp.get("/me/plan")
@login_required
def my_plan():
    user = current_user()
    plans = db.session.scalars(
        select(UserOlympiadPlan)
        .join(OlympiadEdition)
        .join(Olympiad)
        .options(
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
            joinedload(UserOlympiadPlan.edition).selectinload(OlympiadEdition.stages),
            selectinload(UserOlympiadPlan.stage_progress).joinedload(
                UserStageProgress.stage
            ),
        )
        .where(
            UserOlympiadPlan.user_id == user.id,
            OlympiadEdition.academic_year == _academic_year(),
            OlympiadEdition.status.in_(
                (EditionStatus.PUBLISHED, EditionStatus.ARCHIVED)
            ),
        )
        .order_by(Olympiad.family_name, Olympiad.profile)
    ).unique().all()

    today = date.today()
    upcoming = []
    for plan in plans:
        if plan.edition.status != EditionStatus.PUBLISHED:
            continue
        progress_by_stage = {item.stage_id: item for item in plan.stage_progress}
        for stage in plan.edition.stages:
            last_date = stage.ends_on or stage.starts_on
            if not stage.is_active or last_date is None or last_date < today:
                continue
            progress = progress_by_stage.get(stage.id)
            upcoming.append(
                {
                    "stage_id": stage.id,
                    "stage_key": stage.key,
                    "stage_name": stage.name,
                    "starts_on": stage.starts_on.isoformat() if stage.starts_on else None,
                    "ends_on": stage.ends_on.isoformat() if stage.ends_on else None,
                    "date_precision": stage.date_precision.value,
                    "is_date_confirmed": stage.is_date_confirmed,
                    "olympiad": _olympiad_summary(plan.edition),
                    "progress": _serialize_progress(progress) if progress else None,
                }
            )
    upcoming.sort(
        key=lambda item: (
            item["starts_on"] or item["ends_on"] or "9999-12-31",
            item["olympiad"]["name"],
        )
    )
    return jsonify(items=[_serialize_plan(plan) for plan in plans], upcoming_stages=upcoming)


@personal_bp.get("/olympiads/<slug>/planning")
def planning(slug: str):
    edition = _edition(slug)
    if edition is None:
        return jsonify(error="Олимпиада не найдена"), 404
    user = current_user()
    user_plan = _plan(user.id, edition.id) if user else None
    count, names = _participant_summary(edition.id)
    return jsonify(
        participant_count=count,
        public_participants=names,
        plan=_serialize_plan(user_plan) if user_plan else None,
    )


@personal_bp.post("/olympiads/<slug>/planning")
@login_required
@csrf_protected
def add_to_plan(slug: str):
    edition = _edition(slug)
    if edition is None:
        return jsonify(error="Олимпиада не найдена"), 404
    user = current_user()
    if _plan(user.id, edition.id) is not None:
        return jsonify(error="Олимпиада уже добавлена в план"), 409
    try:
        payload = _payload()
        plan = UserOlympiadPlan(user=user, edition=edition)
        _apply_plan_payload(plan, payload)
        db.session.add(plan)
        db.session.commit()
    except PayloadError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Олимпиада уже добавлена в план"), 409
    return jsonify(_serialize_plan(_plan(user.id, edition.id))), 201


@personal_bp.patch("/olympiads/<slug>/planning")
@login_required
@csrf_protected
def update_plan(slug: str):
    edition = _edition(
        slug, statuses=(EditionStatus.PUBLISHED, EditionStatus.ARCHIVED)
    )
    if edition is None:
        return jsonify(error="Олимпиада не найдена"), 404
    user = current_user()
    plan = _plan(user.id, edition.id)
    if plan is None:
        return jsonify(error="Олимпиада не добавлена в план"), 404
    try:
        payload = _payload()
        if not payload:
            raise PayloadError("Не указаны поля для изменения")
        _apply_plan_payload(plan, payload)
        db.session.commit()
    except PayloadError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400
    return jsonify(_serialize_plan(plan))


@personal_bp.delete("/olympiads/<slug>/planning")
@login_required
@csrf_protected
def remove_from_plan(slug: str):
    edition = _edition(
        slug, statuses=(EditionStatus.PUBLISHED, EditionStatus.ARCHIVED)
    )
    if edition is None:
        return jsonify(error="Олимпиада не найдена"), 404
    user = current_user()
    plan = _plan(user.id, edition.id)
    if plan is None:
        return jsonify(error="Олимпиада не добавлена в план"), 404
    db.session.delete(plan)
    db.session.commit()
    return "", 204


def _progress_target(slug: str, stage_id: int):
    edition = _edition(slug)
    if edition is None:
        return None, None, (jsonify(error="Олимпиада не найдена"), 404)
    user = current_user()
    plan = _plan(user.id, edition.id)
    if plan is None:
        return None, None, (jsonify(error="Сначала добавьте олимпиаду в план"), 409)
    stage = db.session.scalar(
        select(Stage).where(
            Stage.id == stage_id,
            Stage.edition_id == edition.id,
            Stage.is_active.is_(True),
        )
    )
    if stage is None:
        return None, None, (jsonify(error="Этап не найден"), 404)
    return plan, stage, None


@personal_bp.put("/olympiads/<slug>/stages/<int:stage_id>/progress")
@login_required
@csrf_protected
def put_progress(slug: str, stage_id: int):
    plan, stage, error = _progress_target(slug, stage_id)
    if error:
        return error
    try:
        payload = _payload()
        unknown = set(payload) - {"participated", "advanced", "result"}
        if unknown:
            raise PayloadError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
        if "participated" not in payload:
            raise PayloadError("Поле participated обязательно")
        participated = _strict_bool(payload["participated"], "participated")
        advanced = payload.get("advanced")
        if advanced is not None:
            advanced = _strict_bool(advanced, "advanced")
        result = payload.get("result")
        if result is not None and not isinstance(result, str):
            raise PayloadError("Поле result должно быть строкой или null")
        result = result.strip() if result else None
        if result and len(result) > 500:
            raise PayloadError("Поле result длиннее 500 символов")
    except PayloadError as exc:
        return jsonify(error=str(exc)), 400

    progress = db.session.scalar(
        select(UserStageProgress).where(
            UserStageProgress.plan_id == plan.id,
            UserStageProgress.stage_id == stage.id,
        )
    )
    if progress is None:
        progress = UserStageProgress(plan=plan, stage=stage)
        db.session.add(progress)
    progress.participated = participated
    progress.advanced = advanced if participated else None
    progress.result = result if participated else None
    db.session.commit()
    return jsonify(_serialize_progress(progress))


@personal_bp.delete("/olympiads/<slug>/stages/<int:stage_id>/progress")
@login_required
@csrf_protected
def delete_progress(slug: str, stage_id: int):
    plan, stage, error = _progress_target(slug, stage_id)
    if error:
        return error
    progress = db.session.scalar(
        select(UserStageProgress).where(
            UserStageProgress.plan_id == plan.id,
            UserStageProgress.stage_id == stage.id,
        )
    )
    if progress is not None:
        db.session.delete(progress)
        db.session.commit()
    return "", 204


__all__ = ["personal_bp", "_participant_summary"]
