from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from flask import current_app
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    EditionStatus,
    OlympiadEdition,
    PlanStatus,
    ReminderDispatch,
    ReminderStatus,
    Stage,
    UserOlympiadPlan,
)

ACTIVE_PLAN_STATUSES = (
    PlanStatus.PLANNED,
    PlanStatus.REGISTERED,
    PlanStatus.PARTICIPATING,
)
RETRYABLE_STATUSES = (ReminderStatus.PENDING, ReminderStatus.RETRY)
IDEMPOTENCY_KEY_RE = re.compile(r"[A-Za-z0-9._:-]{8,128}\Z")


@dataclass(frozen=True)
class DeliveryOutcome:
    status: str
    retry_after: int | None = None


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _local_date(now: datetime) -> date:
    timezone = ZoneInfo(current_app.config["REMINDER_TIMEZONE"])
    return _aware_utc(now).astimezone(timezone).date()


def _event_date(stage: Stage) -> date | None:
    return stage.starts_on or stage.ends_on


def _payload_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _days_phrase(days: int) -> str:
    if days == 0:
        return "сегодня"
    if days == 1:
        return "завтра"
    last_two = days % 100
    last = days % 10
    if 11 <= last_two <= 14:
        noun = "дней"
    elif last == 1:
        noun = "день"
    elif 2 <= last <= 4:
        noun = "дня"
    else:
        noun = "дней"
    return f"через {days} {noun}"


def _olympiad_label(plan: UserOlympiadPlan) -> str:
    olympiad = plan.edition.olympiad
    profile = olympiad.profile.strip()
    family = olympiad.family_name.strip()
    if profile and profile.casefold() not in family.casefold():
        return f"{family} — {profile}"
    return family or olympiad.name.strip()


def _notification_payload(
    plan: UserOlympiadPlan, stage: Stage, days_before: int
) -> dict[str, str]:
    label = _olympiad_label(plan)
    title = f"Скоро этап олимпиады: {label}"[:200]
    message = (
        f"Этап «{stage.name.strip()}» олимпиады «{label}» запланирован "
        f"{_days_phrase(days_before)}. Проверьте время и формат проведения на странице олимпиады."
    )
    base_url = current_app.config["FRONTEND_BASE_URL"].rstrip("/")
    slug = quote(plan.edition.olympiad.slug, safe="")
    academic_year = quote(plan.edition.academic_year, safe="")
    return {
        "recipient_sub": plan.user.oidc_subject,
        "title": title,
        "message": message,
        "url": f"{base_url}/olympiads/{slug}?academic_year={academic_year}",
    }


def _idempotency_key(
    plan: UserOlympiadPlan, stage: Stage, event_on: date, days_before: int
) -> str:
    key = (
        f"olympiads.reminder.{plan.id}.{stage.id}."
        f"{event_on.strftime('%Y%m%d')}.{days_before}"
    )
    if not IDEMPOTENCY_KEY_RE.fullmatch(key):
        raise ValueError("Generated an invalid reminder idempotency key")
    return key


def schedule_reminder_dispatches(*, today: date | None = None) -> list[int]:
    """Persist future reminders before delivery so restarts cannot lose them."""
    if today is None:
        today = _local_date(_now_utc())

    plans = db.session.scalars(
        select(UserOlympiadPlan)
        .join(OlympiadEdition)
        .options(
            joinedload(UserOlympiadPlan.user),
            joinedload(UserOlympiadPlan.edition).joinedload(OlympiadEdition.olympiad),
            joinedload(UserOlympiadPlan.edition).selectinload(OlympiadEdition.stages),
        )
        .where(
            UserOlympiadPlan.reminders_enabled.is_(True),
            UserOlympiadPlan.status.in_(ACTIVE_PLAN_STATUSES),
            OlympiadEdition.status == EditionStatus.PUBLISHED,
        )
    ).unique().all()

    plan_ids = [plan.id for plan in plans]
    existing: set[tuple[int, int, date, int]] = set()
    for offset in range(0, len(plan_ids), 500):
        chunk = plan_ids[offset : offset + 500]
        existing.update(
            db.session.execute(
                select(
                    ReminderDispatch.plan_id,
                    ReminderDispatch.stage_id,
                    ReminderDispatch.event_on,
                    ReminderDispatch.days_before,
                ).where(ReminderDispatch.plan_id.in_(chunk))
            ).all()
        )

    created_ids: list[int] = []
    for plan in plans:
        days_values = {
            value
            for value in plan.reminder_days_before
            if isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value <= 90
        }
        for stage in plan.edition.stages:
            event_on = _event_date(stage)
            if (
                not stage.is_active
                or not stage.is_date_confirmed
                or event_on is None
                or event_on < today
            ):
                continue
            for days_before in sorted(days_values, reverse=True):
                scheduled_for = event_on - timedelta(days=days_before)
                # Do not send a misleading reminder after its configured threshold.
                # Rows created before their due date remain durable and can be retried later.
                if scheduled_for < today:
                    continue
                identity = (plan.id, stage.id, event_on, days_before)
                if identity in existing:
                    continue
                payload = _notification_payload(plan, stage, days_before)
                dispatch = ReminderDispatch(
                    plan_id=plan.id,
                    stage_id=stage.id,
                    event_on=event_on,
                    scheduled_for=scheduled_for,
                    days_before=days_before,
                    idempotency_key=_idempotency_key(
                        plan, stage, event_on, days_before
                    ),
                    payload=payload,
                    payload_sha256=_payload_digest(payload),
                )
                try:
                    # The unique constraints are the final guard when two beat
                    # processes overlap during a rolling deployment.
                    with db.session.begin_nested():
                        db.session.add(dispatch)
                        db.session.flush()
                except IntegrityError:
                    duplicate = db.session.scalar(
                        select(ReminderDispatch.id).where(
                            ReminderDispatch.plan_id == plan.id,
                            ReminderDispatch.stage_id == stage.id,
                            ReminderDispatch.event_on == event_on,
                            ReminderDispatch.days_before == days_before,
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


def due_dispatch_ids(
    *, now: datetime | None = None, limit: int | None = None
) -> list[int]:
    now = _aware_utc(now or _now_utc())
    today = _local_date(now)
    lease_cutoff = now - timedelta(
        seconds=current_app.config["CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS"]
    )
    limit = limit or current_app.config["CRM_NOTIFICATION_SCAN_BATCH"]
    query = (
        select(ReminderDispatch.id)
        .where(
            ReminderDispatch.scheduled_for <= today,
            or_(
                and_(
                    ReminderDispatch.status.in_(RETRYABLE_STATUSES),
                    or_(
                        ReminderDispatch.next_attempt_at.is_(None),
                        ReminderDispatch.next_attempt_at <= now,
                    ),
                ),
                and_(
                    ReminderDispatch.status == ReminderStatus.PROCESSING,
                    or_(
                        ReminderDispatch.last_attempt_at.is_(None),
                        ReminderDispatch.last_attempt_at <= lease_cutoff,
                    ),
                ),
            ),
        )
        .order_by(ReminderDispatch.scheduled_for, ReminderDispatch.id)
        .limit(limit)
    )
    return list(db.session.scalars(query))


def _dispatch_is_current(dispatch: ReminderDispatch, today: date) -> bool:
    plan = dispatch.plan
    stage = dispatch.stage
    return bool(
        plan.reminders_enabled
        and plan.status in ACTIVE_PLAN_STATUSES
        and plan.edition.status == EditionStatus.PUBLISHED
        and dispatch.days_before in plan.reminder_days_before
        and plan.user.oidc_issuer.rstrip("/")
        == current_app.config["CRM_OIDC_ISSUER"]
        and dispatch.payload.get("recipient_sub") == plan.user.oidc_subject
        and stage.is_active
        and stage.is_date_confirmed
        and _event_date(stage) == dispatch.event_on
        and dispatch.event_on >= today
    )


def _parse_retry_after(value: str | None, now: datetime) -> int | None:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0, math.ceil((parsed.astimezone(UTC) - now).total_seconds()))


def _retry_delay(attempt_count: int, retry_after: str | None, now: datetime) -> int:
    base = current_app.config["CRM_NOTIFICATION_RETRY_BASE_SECONDS"]
    maximum = current_app.config["CRM_NOTIFICATION_RETRY_MAX_SECONDS"]
    exponential = min(maximum, base * (2 ** min(max(attempt_count - 1, 0), 16)))
    with_jitter = math.ceil(exponential + random.uniform(0, exponential * 0.25))
    server_delay = _parse_retry_after(retry_after, now)
    return max(with_jitter, server_delay or 0)


def _mark_retry(
    dispatch: Any,
    *,
    now: datetime,
    error: str,
    response_status: int | None = None,
    retry_after: str | None = None,
) -> DeliveryOutcome:
    if dispatch.attempt_count >= max(
        1, current_app.config["CRM_NOTIFICATION_MAX_ATTEMPTS"]
    ):
        dispatch.status = ReminderStatus.PERMANENT_FAILED
        dispatch.next_attempt_at = None
        dispatch.response_status = response_status
        dispatch.last_error = "retry_limit_exhausted"
        db.session.commit()
        return DeliveryOutcome("permanent_failed")
    delay = _retry_delay(dispatch.attempt_count, retry_after, now)
    dispatch.status = ReminderStatus.RETRY
    dispatch.next_attempt_at = now + timedelta(seconds=delay)
    dispatch.response_status = response_status
    dispatch.last_error = error[:100]
    db.session.commit()
    return DeliveryOutcome("retry", delay)


def _claim_dispatch(dispatch_id: int, now: datetime) -> tuple[ReminderDispatch | None, str]:
    dispatch = db.session.scalar(
        select(ReminderDispatch)
        .options(
            joinedload(ReminderDispatch.plan)
            .joinedload(UserOlympiadPlan.edition)
            .joinedload(OlympiadEdition.olympiad),
            joinedload(ReminderDispatch.plan).joinedload(UserOlympiadPlan.user),
            joinedload(ReminderDispatch.stage),
        )
        .where(ReminderDispatch.id == dispatch_id)
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
    today = _local_date(now)
    if today > dispatch.scheduled_for + timedelta(
        days=max(0, current_app.config["CRM_NOTIFICATION_MAX_AGE_DAYS"])
    ):
        dispatch.status = ReminderStatus.CANCELLED
        dispatch.next_attempt_at = None
        dispatch.last_error = "reminder_expired"
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
    if not _dispatch_is_current(dispatch, today):
        dispatch.status = ReminderStatus.CANCELLED
        dispatch.next_attempt_at = None
        dispatch.last_error = "reminder_no_longer_current"
        db.session.commit()
        return dispatch, "cancelled"
    dispatch.status = ReminderStatus.PROCESSING
    dispatch.attempt_count += 1
    dispatch.last_attempt_at = now
    dispatch.next_attempt_at = None
    dispatch.last_error = None
    db.session.commit()
    return dispatch, "claimed"


def _deliver_claimed_dispatch(
    dispatch: Any,
    *,
    http_post: Callable[..., Any],
    now: datetime,
) -> DeliveryOutcome:
    client_id = current_app.config["CRM_OIDC_CLIENT_ID"]
    client_secret = current_app.config["CRM_OIDC_CLIENT_SECRET"]
    if not client_id or not client_secret:
        return _mark_retry(
            dispatch,
            now=now,
            error="crm_credentials_unavailable",
        )

    try:
        response = http_post(
            current_app.config["CRM_NOTIFICATION_URL"],
            auth=(client_id, client_secret),
            headers={"Idempotency-Key": dispatch.idempotency_key},
            json=dict(dispatch.payload),
            timeout=current_app.config["CRM_NOTIFICATION_TIMEOUT_SECONDS"],
            verify=True,
            allow_redirects=False,
        )
    except requests.Timeout:
        return _mark_retry(dispatch, now=now, error="request_timeout")
    except requests.RequestException:
        return _mark_retry(dispatch, now=now, error="request_network_error")

    status_code = int(response.status_code)
    if status_code in (200, 202):
        dispatch.status = ReminderStatus.SENT
        dispatch.sent_at = now
        dispatch.next_attempt_at = None
        dispatch.response_status = status_code
        dispatch.last_error = None
        db.session.commit()
        return DeliveryOutcome("sent")

    if status_code == 429 or 500 <= status_code <= 599:
        return _mark_retry(
            dispatch,
            now=now,
            error=f"http_{status_code}",
            response_status=status_code,
            retry_after=response.headers.get("Retry-After"),
        )

    dispatch.status = ReminderStatus.PERMANENT_FAILED
    dispatch.next_attempt_at = None
    dispatch.response_status = status_code
    dispatch.last_error = f"http_{status_code}"
    db.session.commit()
    return DeliveryOutcome("permanent_failed")


def deliver_reminder_once(
    dispatch_id: int,
    *,
    http_post: Callable[..., Any] = requests.post,
    now: datetime | None = None,
) -> DeliveryOutcome:
    """Attempt one CRM POST and persist its outcome without exposing its body in logs."""
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
