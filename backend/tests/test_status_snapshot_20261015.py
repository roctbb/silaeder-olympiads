"""October 15 organizer review: expired links, new openings, stable stage IDs."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.extensions import db
from app.models import UserOlympiadPlan
from app.services.catalog import serialize_olympiad, upsert_catalog_record
from app.services.registration_notifications import schedule_registration_notification_dispatches


def snapshot():
    path = Path(__file__).resolve().parents[2] / "data/seed/catalog.json"
    return {r["slug"]: r for r in json.loads(path.read_text())["records"]}


def test_october_expired_registrations_are_hidden(app, monkeypatch):
    from app.services import catalog

    now = datetime(2026, 10, 15, 20, tzinfo=UTC)
    monkeypatch.setattr(catalog, "_utcnow", lambda: now)
    rows = snapshot()
    for slug in (
        "dano-data-analysis", "masteryata-family-professional-skills",
        "vosh-2026-27-15", "vosh-2026-27-26", "vysshaya-proba-biology",
        "mkoshp-programming", "lomonosov-tournament-mathematics",
        "registry-2026-27-007-01",
    ):
        olympiad, edition = upsert_catalog_record(rows[slug])
        response = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
        assert response["registration_status"] == "not_open"
        assert response["registration_url"] is None
    for slug in (
        "euler-mathematics", "registry-2026-27-056-01",
        "registry-2026-27-018-01", "registry-2026-27-052-04",
        "registry-2026-27-078-01", "registry-2026-27-025-01",
        "vosh-2026-27-19", "vosh-2026-27-05", "vosh-2026-27-08",
    ):
        olympiad, edition = upsert_catalog_record(rows[slug])
        response = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
        assert response["registration_status"] == "open"
        assert response["registration_url"]


def test_expired_dano_does_not_send_opening_notification(app, user_id):
    row = snapshot()["dano-data-analysis"]
    previous = deepcopy(row)
    previous.update(
        registration_status="not_open", registration_url=None,
        registration_closes_at=None,
    )
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    db.session.add(UserOlympiadPlan(user_id=user_id, edition_id=edition.id))
    db.session.commit()
    upsert_catalog_record(row)
    db.session.commit()
    assert schedule_registration_notification_dispatches(
        now=datetime(2026, 10, 15, 20, tzinfo=UTC),
    ) == []


def test_replacing_euler_forecasts_keeps_plan_and_stage_ids(app, user_id):
    current = snapshot()["euler-mathematics"]
    previous = deepcopy(current)
    previous.update(registration_status="not_found", registration_url=None)
    previous["stages"][0].update(
        starts_on="2026-11-09", ends_on="2026-11-09",
        is_date_confirmed=False, date_precision="approximate",
    )
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    old_ids = {s.key: s.id for s in edition.stages}
    plan = UserOlympiadPlan(user_id=user_id, edition_id=edition.id)
    db.session.add(plan)
    db.session.commit()
    plan_id = plan.id
    _, updated = upsert_catalog_record(current)
    db.session.commit()
    assert {s.key: s.id for s in updated.stages} == old_ids
    assert db.session.get(UserOlympiadPlan, plan_id).edition_id == updated.id
