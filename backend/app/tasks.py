from celery import shared_task

from .services.registration_notifications import (
    deliver_registration_notification_once,
    due_registration_notification_ids,
    schedule_registration_notification_dispatches,
)
from .services.reminders import (
    deliver_reminder_once,
    due_dispatch_ids,
    schedule_reminder_dispatches,
)


@shared_task(name="catalog.health")
def catalog_health() -> dict[str, str]:
    """A lightweight worker wiring check."""
    return {"status": "ok"}


@shared_task(name="reminders.scan")
def scan_reminders() -> dict[str, int]:
    """Persist and enqueue stage reminders and registration notifications."""
    reminder_created_ids = schedule_reminder_dispatches()
    registration_created_ids = schedule_registration_notification_dispatches()
    reminder_due_ids = due_dispatch_ids()
    registration_due_ids = due_registration_notification_ids()
    for dispatch_id in reminder_due_ids:
        deliver_reminder.apply_async(args=(dispatch_id,))
    for dispatch_id in registration_due_ids:
        deliver_registration_notification.apply_async(args=(dispatch_id,))
    return {
        "created": len(reminder_created_ids) + len(registration_created_ids),
        "enqueued": len(reminder_due_ids) + len(registration_due_ids),
    }


@shared_task(bind=True, name="reminders.deliver", max_retries=None)
def deliver_reminder(self, dispatch_id: int) -> dict[str, str | int]:
    outcome = deliver_reminder_once(dispatch_id)
    if outcome.status == "retry":
        raise self.retry(countdown=outcome.retry_after or 1)
    result: dict[str, str | int] = {"status": outcome.status}
    if outcome.retry_after is not None:
        result["retry_after"] = outcome.retry_after
    return result


@shared_task(
    bind=True,
    name="registration_notifications.deliver",
    max_retries=None,
)
def deliver_registration_notification(
    self, dispatch_id: int
) -> dict[str, str | int]:
    outcome = deliver_registration_notification_once(dispatch_id)
    if outcome.status == "retry":
        raise self.retry(countdown=outcome.retry_after or 1)
    result: dict[str, str | int] = {"status": outcome.status}
    if outcome.retry_after is not None:
        result["retry_after"] = outcome.retry_after
    return result
