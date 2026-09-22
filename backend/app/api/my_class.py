from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..auth import csrf_protected, current_user
from ..extensions import db
from ..models import ClassStudent, OlympiadEdition, User, UserOlympiadPlan
from .admin import current_admin
from .personal import _olympiad_summary

class_bp = Blueprint("my_class", __name__)


def class_owner():
    user = current_user()
    if user and (user.crm_role or "").strip().lower() in {"teacher", "admin"}:
        return ClassStudent.teacher_id == user.id, user
    admin = current_admin()
    if admin and admin.is_active:
        return ClassStudent.admin_id == admin.id, None
    return None


def class_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if class_owner() is None:
            status = 403 if current_user() else 401
            return jsonify(error="Раздел доступен учителям и администраторам"), status
        return view(*args, **kwargs)

    return wrapped


@class_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers.add("Vary", "Cookie")
    return response


def student_document(student):
    return {"id": student.id, "name": student.name, "grade": student.grade}


@class_bp.get("/my-class")
@class_required
def my_class():
    owner_filter, teacher = class_owner()
    members = db.session.scalars(
        select(ClassStudent)
        .options(joinedload(ClassStudent.student))
        .where(owner_filter)
        .join(User, ClassStudent.student_id == User.id)
        .order_by(User.name, User.id)
    ).all()
    year = request.args.get("academic_year", current_app.config["ACADEMIC_YEAR"])
    plans = db.session.scalars(
        select(UserOlympiadPlan)
        .join(OlympiadEdition)
        .where(
            UserOlympiadPlan.user_id.in_([m.student_id for m in members]),
            OlympiadEdition.academic_year == year,
        )
        .options(
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
        )
    ).all()
    by_student = {}
    for plan in plans:
        by_student.setdefault(plan.user_id, []).append(
            {
                "id": plan.id,
                "olympiad": _olympiad_summary(plan.edition),
                "academic_year": plan.edition.academic_year,
                "edition_status": plan.edition.status.value,
                "status": plan.status.value,
            }
        )
    return jsonify(
        items=[
            dict(student_document(m.student), plans=by_student.get(m.student_id, []))
            for m in members
        ],
        notifications_available=teacher is not None,
        csrf_token=session.get("csrf_token"),
    )


@class_bp.get("/my-class/candidates")
@class_required
def candidates():
    owner_filter, _ = class_owner()
    selected = select(ClassStudent.student_id).where(owner_filter)
    query = select(User).where(
        User.oidc_issuer == current_app.config["CRM_OIDC_ISSUER"],
        or_(User.object_type == "students", User.crm_role == "student"),
        User.id.not_in(selected),
    )
    search = request.args.get("q", "").strip()[:100]
    if search:
        query = query.where(User.name.icontains(search, autoescape=True))
    grade = request.args.get("grade", "")
    if grade:
        if not grade.isdigit() or not 5 <= int(grade) <= 11:
            return jsonify(error="Класс должен быть числом от 5 до 11"), 400
        query = query.where(User.grade == int(grade))
    students = db.session.scalars(query.order_by(User.name, User.id).limit(100)).all()
    return jsonify(items=[student_document(s) for s in students])


@class_bp.post("/my-class/students")
@class_required
@csrf_protected
def add_student():
    payload = request.get_json(silent=True)
    student_id = payload.get("student_id") if isinstance(payload, dict) else None
    if type(student_id) is not int:
        return jsonify(error="Укажите ученика"), 400
    student = db.session.get(User, student_id)
    if (
        student is None
        or student.oidc_issuer != current_app.config["CRM_OIDC_ISSUER"]
        or not (student.object_type == "students" or student.crm_role == "student")
    ):
        return jsonify(error="Ученик не найден"), 404
    owner_filter, teacher = class_owner()
    existing = db.session.scalar(
        select(ClassStudent).where(owner_filter, ClassStudent.student_id == student_id)
    )
    if existing:
        return jsonify(student_document(student)), 200
    member = ClassStudent(
        student_id=student_id,
        teacher_id=teacher.id if teacher else None,
        admin_id=None if teacher else current_admin().id,
    )
    db.session.add(member)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if (
            db.session.scalar(
                select(ClassStudent.id).where(owner_filter, ClassStudent.student_id == student_id)
            )
            is None
        ):
            raise
        return jsonify(student_document(student)), 200
    return jsonify(student_document(student)), 201


@class_bp.delete("/my-class/students/<int:student_id>")
@class_required
@csrf_protected
def remove_student(student_id):
    owner_filter, _ = class_owner()
    member = db.session.scalar(
        select(ClassStudent).where(owner_filter, ClassStudent.student_id == student_id)
    )
    if member:
        db.session.delete(member)
        db.session.commit()
    return "", 204
