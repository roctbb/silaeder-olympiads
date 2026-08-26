import secrets
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..auth import _rotate_session_id, csrf_protected
from ..extensions import db
from ..models import Admin, Benefit, Olympiad, OlympiadEdition, UserOlympiadPlan
from ..services.catalog import (
    ConflictError,
    ValidationError,
    create_catalog_record,
    serialize_olympiad,
    upsert_catalog_record,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.after_request
def disable_admin_response_caching(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers.add("Vary", "Cookie")
    return response


def _is_olympiad_slug_conflict(exc: IntegrityError) -> bool:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name in {"ix_olympiads_slug", "olympiads_slug_key"}:
        return True
    return "olympiads.slug" in str(exc.orig).casefold()


def current_admin() -> Admin | None:
    admin_id = session.get("admin_id")
    return db.session.get(Admin, admin_id) if admin_id else None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        admin = current_admin()
        if admin is None or not admin.is_active:
            session.pop("admin_id", None)
            return jsonify(error="Требуется вход администратора"), 401
        return view(*args, **kwargs)

    return wrapped


def _loaded_olympiad(slug: str) -> Olympiad | None:
    return db.session.scalar(
        select(Olympiad)
        .options(
            selectinload(Olympiad.materials),
            selectinload(Olympiad.editions).selectinload(OlympiadEdition.grades),
            selectinload(Olympiad.editions).selectinload(OlympiadEdition.stages),
            selectinload(Olympiad.editions).selectinload(OlympiadEdition.benefits),
            selectinload(Olympiad.editions).selectinload(OlympiadEdition.sources),
        )
        .where(Olympiad.slug == slug)
    )


def _admin_session_document(admin: Admin) -> dict[str, str | bool]:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return {
        "authenticated": True,
        "username": admin.username,
        "csrf_token": token,
    }


@admin_bp.get("/session")
def admin_session():
    admin = current_admin()
    if admin is None or not admin.is_active:
        return jsonify(authenticated=False), 401
    return jsonify(_admin_session_document(admin))


@admin_bp.post("/session")
def admin_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    admin = db.session.scalar(select(Admin).where(Admin.username == username))
    if admin is None or not admin.is_active or not admin.check_password(password):
        return jsonify(error="Неверный логин или пароль"), 401
    session.clear()
    session["admin_id"] = admin.id
    _rotate_session_id()
    return jsonify(_admin_session_document(admin))


@admin_bp.delete("/session")
@admin_required
@csrf_protected
def admin_logout():
    session.clear()
    return "", 204


@admin_bp.get("/olympiads")
@admin_required
def admin_olympiad_list():
    academic_year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    editions = db.session.scalars(
        select(OlympiadEdition)
        .join(Olympiad)
        .options(
            joinedload(OlympiadEdition.olympiad).selectinload(Olympiad.materials),
            selectinload(OlympiadEdition.grades),
            selectinload(OlympiadEdition.stages),
            selectinload(OlympiadEdition.benefits).selectinload(Benefit.university),
            selectinload(OlympiadEdition.sources),
        )
        .where(OlympiadEdition.academic_year == academic_year)
        .order_by(Olympiad.family_name, Olympiad.profile)
    ).all()
    return jsonify(
        items=[serialize_olympiad(edition.olympiad, edition, detailed=True) for edition in editions]
    )


@admin_bp.get("/olympiads/<slug>")
@admin_required
def admin_olympiad_detail(slug: str):
    academic_year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    olympiad = _loaded_olympiad(slug)
    if olympiad is None:
        return jsonify(error="Олимпиада не найдена"), 404
    edition = next(
        (item for item in olympiad.editions if item.academic_year == academic_year), None
    )
    if edition is None:
        return jsonify(error="Версия олимпиады за этот учебный год не найдена"), 404
    return jsonify(serialize_olympiad(olympiad, edition, detailed=True))


@admin_bp.post("/olympiads")
@admin_required
@csrf_protected
def admin_olympiad_create():
    payload = request.get_json(silent=True) or {}
    try:
        olympiad, edition = create_catalog_record(payload)
        db.session.commit()
    except ConflictError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409
    except IntegrityError as exc:
        db.session.rollback()
        if _is_olympiad_slug_conflict(exc):
            return jsonify(error="Олимпиада с таким slug уже существует"), 409
        return jsonify(error="Нарушены ограничения целостности данных"), 400
    except (ValidationError, DataError) as exc:
        db.session.rollback()
        return jsonify(error=str(getattr(exc, "orig", exc))), 400
    return jsonify(serialize_olympiad(olympiad, edition, detailed=True)), 201


@admin_bp.put("/olympiads/<slug>")
@admin_required
@csrf_protected
def admin_olympiad_update(slug: str):
    payload = request.get_json(silent=True) or {}
    academic_year = payload.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    edition = db.session.scalar(
        select(OlympiadEdition)
        .join(Olympiad)
        .where(
            Olympiad.slug == slug,
            OlympiadEdition.academic_year == academic_year,
        )
        .with_for_update()
    )
    if edition is None:
        return jsonify(error="Версия олимпиады за этот учебный год не найдена"), 404
    olympiad = edition.olympiad
    expected_updated_at = payload.get("updated_at")
    if not expected_updated_at:
        return jsonify(error="Для обновления требуется поле updated_at"), 428
    current_updated_at = edition.updated_at.isoformat()
    if expected_updated_at != current_updated_at:
        return (
            jsonify(
                error="Карточка уже изменена другим редактором. Обновите данные.",
                current_updated_at=current_updated_at,
            ),
            409,
        )
    try:
        olympiad, edition = upsert_catalog_record(payload, olympiad)
        db.session.commit()
    except (ValidationError, DataError, IntegrityError) as exc:
        db.session.rollback()
        return jsonify(error=str(getattr(exc, "orig", exc))), 400
    return jsonify(serialize_olympiad(olympiad, edition, detailed=True))


@admin_bp.delete("/olympiads/<slug>")
@admin_required
@csrf_protected
def admin_olympiad_delete(slug: str):
    olympiad = _loaded_olympiad(slug)
    if olympiad is None:
        return jsonify(error="Олимпиада не найдена"), 404
    plan_count = db.session.scalar(
        select(func.count())
        .select_from(UserOlympiadPlan)
        .join(OlympiadEdition)
        .where(OlympiadEdition.olympiad_id == olympiad.id)
    ) or 0
    if plan_count:
        return (
            jsonify(
                error=(
                    "Олимпиаду нельзя удалить, пока она есть в личных планах. "
                    "Переведите выпуск в архивный статус."
                )
            ),
            409,
        )
    db.session.delete(olympiad)
    db.session.commit()
    return "", 204
