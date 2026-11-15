"""Current openings must expire in the public API and notification scheduler together."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.extensions import db
from app.models import UserOlympiadPlan
from app.services.catalog import serialize_olympiad, upsert_catalog_record
from app.services.registration_notifications import schedule_registration_notification_dispatches


def test_extended_arabic_registration_expires_without_late_notification(app, user_id, monkeypatch):
    from app.services import catalog

    rows = json.loads((Path(__file__).resolve().parents[2] / "data/seed/catalog.json").read_text())["records"]
    row = next(r for r in rows if r["slug"] == "mosh-2026-27-arab")
    previous = deepcopy(row)
    previous.update(registration_status="announced", registration_url=None, registration_closes_at=None)
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    db.session.add(UserOlympiadPlan(user_id=user_id, edition_id=edition.id))
    db.session.commit()
    olympiad, edition = upsert_catalog_record(row)
    db.session.commit()
    monkeypatch.setattr(catalog, "_utcnow", lambda: datetime(2026, 11, 15, 19, tzinfo=UTC))
    assert serialize_olympiad(olympiad, edition, hide_expired_registration=True)["registration_status"] == "open"
    cutoff = datetime(2026, 11, 16, 20, 59, tzinfo=UTC)
    monkeypatch.setattr(catalog, "_utcnow", lambda: cutoff)
    public = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
    assert public["registration_status"] == "not_open"
    assert public["registration_url"] is None
    assert schedule_registration_notification_dispatches(now=cutoff) == []


def test_review_closes_profiles_without_closing_the_whole_family(app, monkeypatch):
    from app.services import catalog

    monkeypatch.setattr(catalog, "_utcnow", lambda: datetime(2026, 11, 15, 19, tzinfo=UTC))
    rows = {r["slug"]: r for r in json.loads((Path(__file__).resolve().parents[2] / "data/seed/catalog.json").read_text())["records"]}
    for slug, expected in {
        "registry-2026-27-048-01": "not_open",  # MSU biology
        "registry-2026-27-048-13": "open",      # MSU mathematics
        "registry-2026-27-052-04": "not_open",  # BMSTU mathematics
        "registry-2026-27-052-06": "open",      # BMSTU chemistry
        "registry-2026-27-035-07": "open",      # MOSH history
        "registry-2026-27-035-12": "announced", # MOSH law
        "prod-backend": "open",
        "registry-2026-27-055-01": "open",
    }.items():
        olympiad, edition = upsert_catalog_record(rows[slug])
        assert serialize_olympiad(olympiad, edition, hide_expired_registration=True)["registration_status"] == expected, slug
