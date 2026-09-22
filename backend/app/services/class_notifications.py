"""One durable class digest per teacher, olympiad edition and calendar day."""

from datetime import timedelta

import requests
from flask import current_app
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    ClassNotificationDispatch as Dispatch,
)
from ..models import (
    ClassStudent,
    EditionStatus,
    OlympiadEdition,
    RegistrationStatus,
    ReminderStatus,
    UserOlympiadPlan,
)
from .reminders import (
    ACTIVE_PLAN_STATUSES,
    RETRYABLE_STATUSES,
    DeliveryOutcome,
    _aware_utc,
    _days_phrase,
    _deliver_claimed_dispatch,
    _event_date,
    _local_date,
    _now_utc,
    _olympiad_label,
    _payload_digest,
)


def _groups(today, now, *, teacher_id=None, edition_id=None):
    query = (
        select(ClassStudent, UserOlympiadPlan)
        .join(UserOlympiadPlan, ClassStudent.student_id == UserOlympiadPlan.user_id)
        .join(OlympiadEdition, UserOlympiadPlan.edition_id == OlympiadEdition.id)
        .where(
            ClassStudent.teacher_id.is_not(None),
            UserOlympiadPlan.status.in_(ACTIVE_PLAN_STATUSES),
            OlympiadEdition.status == EditionStatus.PUBLISHED,
        )
        .options(
            joinedload(ClassStudent.teacher),
            joinedload(ClassStudent.student),
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
            joinedload(UserOlympiadPlan.edition).selectinload(OlympiadEdition.stages),
        )
    )
    if teacher_id is not None:
        query = query.where(ClassStudent.teacher_id == teacher_id)
    if edition_id is not None:
        query = query.where(UserOlympiadPlan.edition_id == edition_id)
    rows = db.session.execute(query).all()
    groups = {}
    for member, plan in rows:
        teacher = member.teacher
        if (
            (teacher.crm_role or "").strip().lower() not in {"teacher", "admin"}
            or teacher.oidc_issuer != current_app.config["CRM_OIDC_ISSUER"]
            or member.student.oidc_issuer != teacher.oidc_issuer
        ):
            continue
        edition = plan.edition
        key = teacher.id, edition.id
        group = groups.setdefault(
            key, {"teacher": teacher, "plan": plan, "students": {}, "events": {}}
        )
        group["students"][member.student_id] = member.student.name
        for stage in edition.stages:
            event_on = _event_date(stage)
            if stage.is_active and stage.is_date_confirmed and event_on:
                days = (event_on - today).days
                if days in (7, 1):
                    event_key = f"stage:{stage.id}:{event_on}:{days}"
                    group["events"][event_key] = f"Этап «{stage.name}» — {_days_phrase(days)}."
        opened = edition.registration_opened_at
        if (
            edition.registration_status == RegistrationStatus.OPEN
            and edition.registration_url
            and opened
            and _local_date(opened) == today
            and _aware_utc(opened) <= now
            and _aware_utc(plan.created_at) <= _aware_utc(opened)
            and _aware_utc(member.created_at) <= _aware_utc(opened)
            and (
                edition.registration_closes_at is None
                or _aware_utc(edition.registration_closes_at) > now
            )
        ):
            group["events"][f"registration:{_aware_utc(opened).isoformat()}"] = (
                "Открылась регистрация."
            )
    return {key: group for key, group in groups.items() if group["events"]}


def _payload(group):
    label = _olympiad_label(group["plan"])
    names = [
        name for _, name in sorted(group["students"].items(), key=lambda pair: (pair[1], pair[0]))
    ]
    return {
        "recipient_sub": group["teacher"].oidc_subject,
        "title": f"Мой класс: {label}"[:200],
        "message": (
            f"Олимпиада «{label}». "
            + " ".join(group["events"][key] for key in sorted(group["events"]))
            + "\nУченики в плане участия:\n"
            + "\n".join(names)
        ),
        "url": current_app.config["FRONTEND_BASE_URL"].rstrip("/") + "/my-class",
    }


def schedule_class_notifications(*, now=None):
    now = _aware_utc(now or _now_utc())
    today = _local_date(now)
    created = []
    for (teacher_id, edition_id), group in _groups(today, now).items():
        key = f"olympiads.class.{teacher_id}.{edition_id}.{today:%Y%m%d}"
        if db.session.scalar(select(Dispatch.id).where(Dispatch.idempotency_key == key)):
            continue
        payload = _payload(group)
        item = Dispatch(
            teacher_id=teacher_id,
            edition_id=edition_id,
            scheduled_for=today,
            events=sorted(group["events"]),
            idempotency_key=key,
            payload=payload,
            payload_sha256=_payload_digest(payload),
        )
        try:
            with db.session.begin_nested():
                db.session.add(item)
                db.session.flush()
        except IntegrityError:
            if not db.session.scalar(select(Dispatch.id).where(Dispatch.idempotency_key == key)):
                raise
            continue
        created.append(item.id)
    db.session.commit()
    return created


def due_class_notification_ids(*, now=None):
    now = _aware_utc(now or _now_utc())
    cutoff = now - timedelta(
        seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
    )
    return list(
        db.session.scalars(
            select(Dispatch.id)
            .where(
                Dispatch.scheduled_for <= _local_date(now),
                or_(
                    and_(
                        Dispatch.status.in_(RETRYABLE_STATUSES),
                        or_(Dispatch.next_attempt_at.is_(None), Dispatch.next_attempt_at <= now),
                    ),
                    and_(
                        Dispatch.status == ReminderStatus.PROCESSING,
                        or_(Dispatch.last_attempt_at.is_(None), Dispatch.last_attempt_at <= cutoff),
                    ),
                ),
            )
            .order_by(Dispatch.scheduled_for, Dispatch.id)
            .limit(current_app.config["CRM_NOTIFICATION_SCAN_BATCH"])
        )
    )


def deliver_class_notification_once(dispatch_id, *, http_post=requests.post, now=None):
    now = _aware_utc(now or _now_utc())
    item = db.session.scalar(select(Dispatch).where(Dispatch.id == dispatch_id).with_for_update())
    if item is None:
        return DeliveryOutcome("missing")
    if item.status == ReminderStatus.PROCESSING:
        lease_end = _aware_utc(item.last_attempt_at or now) + timedelta(
            seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
        )
        if lease_end > now:
            return DeliveryOutcome("retry", max(1, int((lease_end - now).total_seconds())))
    elif item.status not in RETRYABLE_STATUSES:
        return DeliveryOutcome("finished")
    if (
        item.scheduled_for > _local_date(now)
        or item.next_attempt_at
        and _aware_utc(item.next_attempt_at) > now
    ):
        return DeliveryOutcome("deferred")

    error = None
    status = ReminderStatus.CANCELLED
    if _local_date(now) > item.scheduled_for + timedelta(
        days=current_app.config["CRM_NOTIFICATION_MAX_AGE_DAYS"]
    ):
        error = "class_notification_expired"
    elif item.attempt_count >= current_app.config["CRM_NOTIFICATION_MAX_ATTEMPTS"]:
        error, status = "retry_limit_exhausted", ReminderStatus.PERMANENT_FAILED
    elif _payload_digest(item.payload) != item.payload_sha256:
        error, status = "invalid_persisted_dispatch", ReminderStatus.PERMANENT_FAILED
    else:
        group = _groups(
            item.scheduled_for, now, teacher_id=item.teacher_id, edition_id=item.edition_id
        ).get((item.teacher_id, item.edition_id))
        if not group:
            error = "class_notification_no_longer_current"
        else:
            payload = _payload(group)
            if item.attempt_count == 0:
                # Include everyone added before the first delivery, then freeze the payload
                # for CRM's idempotency contract. Never resend a changed body with this key.
                item.payload = payload
                item.payload_sha256 = _payload_digest(payload)
                item.events = sorted(group["events"])
            elif item.payload_sha256 != _payload_digest(payload):
                error = "class_notification_no_longer_current"
    if error:
        item.status, item.last_error, item.next_attempt_at = status, error, None
        db.session.commit()
        return DeliveryOutcome(status.value)
    item.status = ReminderStatus.PROCESSING
    item.attempt_count += 1
    item.last_attempt_at = now
    item.next_attempt_at = None
    db.session.commit()
    return _deliver_claimed_dispatch(item, http_post=http_post, now=now)
