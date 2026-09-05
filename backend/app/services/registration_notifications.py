from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import requests
from flask import current_app
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    EditionStatus,
    OlympiadEdition,
    RegistrationNotificationDispatch,
    RegistrationStatus,
    ReminderStatus,
    UserOlympiadPlan,
)
from .reminders import (
    ACTIVE_PLAN_STATUSES,
    IDEMPOTENCY_KEY_RE,
    RETRYABLE_STATUSES,
    DeliveryOutcome,
    _aware_utc,
    _deliver_claimed_dispatch,
    _local_date,
    _now_utc,
    _payload_digest,
)


def _url_digest(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _olympiad_label(plan: UserOlympiadPlan) -> str:
    olympiad = plan.edition.olympiad
    profile = olympiad.profile.strip()
    family = olympiad.family_name.strip()
    if profile and profile.casefold() not in family.casefold():
        return f"{family} — {profile}"
    return family or olympiad.name.strip()


def _notification_payload(plan: UserOlympiadPlan) -> dict[str, str]:
    label = _olympiad_label(plan)
    base_url = current_app.config["FRONTEND_BASE_URL"].rstrip("/")
    slug = quote(plan.edition.olympiad.slug, safe="")
    academic_year = quote(plan.edition.academic_year, safe="")
    return {
        "recipient_sub": plan.user.oidc_subject,
        "title": f"Открылась регистрация: {label}"[:200],
        "message": (
            f"На олимпиаду «{label}» открылась регистрация. "
            "Проверьте сроки и перейдите к официальной форме со страницы олимпиады."
        ),
        "url": f"{base_url}/olympiads/{slug}?academic_year={academic_year}",
    }


def _idempotency_key(
    plan: UserOlympiadPlan, opened_at: datetime, registration_url: str
) -> str:
    event_digest = hashlib.sha256(
        f"{opened_at.isoformat()}\0{registration_url}".encode()
    ).hexdigest()[:20]
    key = f"olympiads.registration.{plan.id}.{event_digest}"
    if not IDEMPOTENCY_KEY_RE.fullmatch(key):
        raise ValueError("Generated an invalid registration idempotency key")
    return key


def schedule_registration_notification_dispatches(
    *, now: datetime | None = None
) -> list[int]:
    """Persist one notification for plans that existed when registration opened."""
    now = _aware_utc(now or _now_utc())
    today = _local_date(now)
    plans = db.session.scalars(
        select(UserOlympiadPlan)
        .join(OlympiadEdition)
        .options(
            joinedload(UserOlympiadPlan.user),
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
        )
        .where(
            UserOlympiadPlan.reminders_enabled.is_(True),
            UserOlympiadPlan.status.in_(ACTIVE_PLAN_STATUSES),
            OlympiadEdition.status == EditionStatus.PUBLISHED,
            OlympiadEdition.registration_status == RegistrationStatus.OPEN,
            OlympiadEdition.registration_url.is_not(None),
            OlympiadEdition.registration_opened_at.is_not(None),
            UserOlympiadPlan.created_at <= OlympiadEdition.registration_opened_at,
            or_(
                OlympiadEdition.registration_closes_at.is_(None),
                OlympiadEdition.registration_closes_at > now,
            ),
        )
    ).unique().all()

    plan_ids = [plan.id for plan in plans]
    existing: set[tuple[int, datetime]] = set()
    for offset in range(0, len(plan_ids), 500):
        chunk = plan_ids[offset : offset + 500]
        for plan_id, opened_at in db.session.execute(
            select(
                RegistrationNotificationDispatch.plan_id,
                RegistrationNotificationDispatch.registration_opened_at,
            ).where(RegistrationNotificationDispatch.plan_id.in_(chunk))
        ).all():
            existing.add((plan_id, _aware_utc(opened_at)))

    created_ids: list[int] = []
    for plan in plans:
        edition = plan.edition
        opened_at = _aware_utc(edition.registration_opened_at)
        registration_url = edition.registration_url
        if not registration_url:
            continue
        identity = (plan.id, opened_at)
        if identity in existing:
            continue
        payload = _notification_payload(plan)
        dispatch = RegistrationNotificationDispatch(
            plan_id=plan.id,
            registration_opened_at=opened_at,
            registration_url_sha256=_url_digest(registration_url),
            scheduled_for=today,
            idempotency_key=_idempotency_key(plan, opened_at, registration_url),
            payload=payload,
            payload_sha256=_payload_digest(payload),
        )
        try:
            with db.session.begin_nested():
                db.session.add(dispatch)
                db.session.flush()
        except IntegrityError:
            duplicate = db.session.scalar(
                select(RegistrationNotificationDispatch.id).where(
                    RegistrationNotificationDispatch.plan_id == plan.id,
                    RegistrationNotificationDispatch.registration_opened_at
                    == opened_at,
                )
            )
            if duplicate is None:
                raise
            existing.add(identity)
            continue
        created_ids.append(dispatch.id)
        existing.add(identity)

    db.session.commit()
    return created_ids


def due_registration_notification_ids(
    *, now: datetime | None = None, limit: int | None = None
) -> list[int]:
    now = _aware_utc(now or _now_utc())
    today = _local_date(now)
    lease_cutoff = now - timedelta(
        seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
    )
    limit = limit or current_app.config["CRM_NOTIFICATION_SCAN_BATCH"]
    query = (
        select(RegistrationNotificationDispatch.id)
        .where(
            RegistrationNotificationDispatch.scheduled_for <= today,
            or_(
                and_(
                    RegistrationNotificationDispatch.status.in_(RETRYABLE_STATUSES),
                    or_(
                        RegistrationNotificationDispatch.next_attempt_at.is_(None),
                        RegistrationNotificationDispatch.next_attempt_at <= now,
                    ),
                ),
                and_(
                    RegistrationNotificationDispatch.status
                    == ReminderStatus.PROCESSING,
                    or_(
                        RegistrationNotificationDispatch.last_attempt_at.is_(None),
                        RegistrationNotificationDispatch.last_attempt_at <= lease_cutoff,
                    ),
                ),
            ),
        )
        .order_by(
            RegistrationNotificationDispatch.scheduled_for,
            RegistrationNotificationDispatch.id,
        )
        .limit(limit)
    )
    return list(db.session.scalars(query))


def _dispatch_is_current(
    dispatch: RegistrationNotificationDispatch, now: datetime
) -> bool:
    plan = dispatch.plan
    edition = plan.edition
    opened_at = edition.registration_opened_at
    registration_url = edition.registration_url
    return bool(
        plan.reminders_enabled
        and plan.status in ACTIVE_PLAN_STATUSES
        and edition.status == EditionStatus.PUBLISHED
        and edition.registration_status == RegistrationStatus.OPEN
        and opened_at is not None
        and _aware_utc(opened_at) == _aware_utc(dispatch.registration_opened_at)
        and registration_url
        and _url_digest(registration_url) == dispatch.registration_url_sha256
        and (
            edition.registration_closes_at is None
            or _aware_utc(edition.registration_closes_at) > now
        )
        and plan.user.oidc_issuer.rstrip("/")
        == current_app.config["CRM_OIDC_ISSUER"]
        and dispatch.payload.get("recipient_sub") == plan.user.oidc_subject
    )


def _claim_dispatch(
    dispatch_id: int, now: datetime
) -> tuple[RegistrationNotificationDispatch | None, str]:
    dispatch = db.session.scalar(
        select(RegistrationNotificationDispatch)
        .where(RegistrationNotificationDispatch.id == dispatch_id)
        .with_for_update()
    )
    if dispatch is None:
        return None, "missing"

    lease_cutoff = now - timedelta(
        seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
    )
    can_reclaim = dispatch.status == ReminderStatus.PROCESSING and (
        dispatch.last_attempt_at is None
        or _aware_utc(dispatch.last_attempt_at) <= lease_cutoff
    )
    if dispatch.status not in RETRYABLE_STATUSES and not can_reclaim:
        return dispatch, "finished"
    if dispatch.next_attempt_at and _aware_utc(dispatch.next_attempt_at) > now:
        return dispatch, "deferred"
    if dispatch.scheduled_for > _local_date(now):
        return dispatch, "deferred"
    if _local_date(now) > dispatch.scheduled_for + timedelta(
        days=max(0, current_app.config["CRM_NOTIFICATION_MAX_AGE_DAYS"])
    ):
        dispatch.status = ReminderStatus.CANCELLED
        dispatch.next_attempt_at = None
        dispatch.last_error = "registration_notification_expired"
        db.session.commit()
        return dispatch, "cancelled"
    if dispatch.attempt_count >= max(
        1, current_app.config["CRM_NOTIFICATION_MAX_ATTEMPTS"]
    ):
        dispatch.status = ReminderStatus.PERMANENT_FAILED
        dispatch.next_attempt_at = None
        dispatch.last_error = "retry_limit_exhausted"
        db.session.commit()
        return dispatch, "permanent_failed"
    if (
        not IDEMPOTENCY_KEY_RE.fullmatch(dispatch.idempotency_key)
        or not isinstance(dispatch.payload, dict)
        or _payload_digest(dispatch.payload) != dispatch.payload_sha256
    ):
        dispatch.status = ReminderStatus.PERMANENT_FAILED
        dispatch.next_attempt_at = None
        dispatch.last_error = "invalid_persisted_dispatch"
        db.session.commit()
        return dispatch, "permanent_failed"
    if not _dispatch_is_current(dispatch, now):
        dispatch.status = ReminderStatus.CANCELLED
        dispatch.next_attempt_at = None
        dispatch.last_error = "registration_no_longer_open"
        db.session.commit()
        return dispatch, "cancelled"

    dispatch.status = ReminderStatus.PROCESSING
    dispatch.attempt_count += 1
    dispatch.last_attempt_at = now
    dispatch.next_attempt_at = None
    dispatch.last_error = None
    db.session.commit()
    return dispatch, "claimed"


def deliver_registration_notification_once(
    dispatch_id: int,
    *,
    http_post: Callable[..., Any] = requests.post,
    now: datetime | None = None,
) -> DeliveryOutcome:
    now = _aware_utc(now or _now_utc())
    dispatch, claim_status = _claim_dispatch(dispatch_id, now)
    if dispatch is None:
        return DeliveryOutcome("missing")
    if claim_status == "finished" and dispatch.status == ReminderStatus.PROCESSING:
        lease_until = _aware_utc(dispatch.last_attempt_at or now) + timedelta(
            seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
        )
        return DeliveryOutcome(
            "retry", max(1, math.ceil((lease_until - now).total_seconds()))
        )
    if claim_status != "claimed":
        return DeliveryOutcome(claim_status)
    return _deliver_claimed_dispatch(dispatch, http_post=http_post, now=now)
