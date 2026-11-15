"""November review: profile deadlines, real openings and non-destructive import."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.extensions import db
from app.models import UserOlympiadPlan, UserStageProgress
from app.services.catalog import serialize_olympiad, upsert_catalog_record
from app.services.registration_notifications import schedule_registration_notification_dispatches


def snapshot():
    path = Path(__file__).resolve().parents[2] / "data/seed/catalog.json"
    return {r["slug"]: r for r in json.loads(path.read_text())["records"]}


def test_november_profile_registration_states(app, monkeypatch):
    from app.services import catalog

    monkeypatch.setattr(catalog, "_utcnow", lambda: datetime(2026, 11, 3, 19, tzinfo=UTC))
    rows = snapshot()
    cases = {
        "registry-2026-27-005-01": "not_open",  # NTO senior, not juniors
        "registry-2026-27-014-01": "not_open",  # Vsesib biology already held
        "registry-2026-27-014-02": "not_open",  # latest review: November tour completed
        "registry-2026-27-020-04": "not_open",  # Innopolis math
        "registry-2026-27-020-05": "open",      # robotics has a later deadline
        "registry-2026-27-035-12": "announced", # MOSH law is in December
        "registry-2026-27-035-02": "open",      # MOSH probability/statistics
        "registry-2026-27-048-19": "open",      # Lomonosov law
        "registry-2026-27-054-01": "open",      # Technocup new season
        "moebius-mathematics": "open",
        "hse-team-programming": "not_open",
        "prod-backend": "open",               # November 15 browser check confirms form
        "vosh-2026-27-06": "not_open",
        "vosh-2026-27-28": "not_open",
    }
    for slug, expected in cases.items():
        olympiad, edition = upsert_catalog_record(rows[slug])
        result = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
        assert result["registration_status"] == expected, slug
        assert bool(result["registration_url"]) == (expected == "open"), slug


def test_innopolis_cutoff_closes_public_link_and_prevents_notification(app, user_id, monkeypatch):
    from app.services import catalog

    row = snapshot()["registry-2026-27-020-05"]
    previous = deepcopy(row)
    previous.update(registration_status="not_open", registration_url=None, registration_closes_at=None)
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    db.session.add(UserOlympiadPlan(user_id=user_id, edition_id=edition.id))
    db.session.commit()
    olympiad, edition = upsert_catalog_record(row)
    db.session.commit()
    before = datetime(2026, 11, 9, 11, 59, 59, tzinfo=UTC)
    monkeypatch.setattr(catalog, "_utcnow", lambda: before)
    assert serialize_olympiad(olympiad, edition, hide_expired_registration=True)["registration_status"] == "open"
    cutoff = datetime(2026, 11, 9, 12, tzinfo=UTC)  # 15:00 Moscow
    monkeypatch.setattr(catalog, "_utcnow", lambda: cutoff)
    result = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
    assert result["registration_status"] == "not_open"
    assert result["registration_url"] is None
    assert schedule_registration_notification_dispatches(now=cutoff) == []


def test_new_mosh_opening_preserves_progress_and_notifies_once(app, user_id):
    row = snapshot()["registry-2026-27-035-02"]
    previous = deepcopy(row)
    previous.update(registration_status="not_found", registration_url=None, registration_closes_at=None)
    previous["stages"][0].update(starts_on=None, ends_on=None, date_precision="tba", is_date_confirmed=False)
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    ids = {s.key: s.id for s in edition.stages}
    plan = UserOlympiadPlan(user_id=user_id, edition_id=edition.id)
    db.session.add(plan)
    db.session.flush()
    progress = UserStageProgress(plan_id=plan.id, stage_id=ids["qualifying"], participated=True, advanced=True, result="Сохранённый результат")
    db.session.add(progress)
    db.session.commit()
    plan_id, progress_id = plan.id, progress.id
    _, updated = upsert_catalog_record(row)
    db.session.commit()
    assert updated.id == edition.id
    assert {s.key: s.id for s in updated.stages} == ids
    assert db.session.get(UserOlympiadPlan, plan_id).edition_id == updated.id
    assert db.session.get(UserStageProgress, progress_id).result == "Сохранённый результат"
    now = datetime(2026, 11, 3, 20, tzinfo=UTC)
    assert len(schedule_registration_notification_dispatches(now=now)) == 1
    upsert_catalog_record(row)
    db.session.commit()
    assert schedule_registration_notification_dispatches(now=now) == []


def test_published_dates_replace_forecasts_but_conflicts_remain_unconfirmed():
    rows = snapshot()
    assert all(s["is_date_confirmed"] for s in rows["prod-backend"]["stages"])
    for slug in ("mosh-2026-27-iikt-10-11", "mosh-2026-27-iikt-6-9"):
        assert rows[slug]["stages"][0]["format"] == "offline"
    law = rows["registry-2026-27-035-12"]["stages"][0]
    assert (law["starts_on"], law["ends_on"]) == ("2026-12-03", "2026-12-18")
    for suffix in range(1, 6):
        final = rows[f"registry-2026-27-020-{suffix:02d}"]["stages"][-1]
        assert not final["is_date_confirmed"]
        assert "расхождение" in final["details"]
