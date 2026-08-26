from celery import shared_task

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
    """Persist new schedules, then enqueue every due or abandoned dispatch."""
    created_ids = schedule_reminder_dispatches()
    due_ids = due_dispatch_ids()
    for dispatch_id in due_ids:
        deliver_reminder.apply_async(args=(dispatch_id,))
    return {"created": len(created_ids), "enqueued": len(due_ids)}


@shared_task(bind=True, name="reminders.deliver", max_retries=None)
def deliver_reminder(self, dispatch_id: int) -> dict[str, str | int]:
    outcome = deliver_reminder_once(dispatch_id)
    if outcome.status == "retry":
        raise self.retry(countdown=outcome.retry_after or 1)
    result: dict[str, str | int] = {"status": outcome.status}
    if outcome.retry_after is not None:
        result["retry_after"] = outcome.retry_after
    return result
