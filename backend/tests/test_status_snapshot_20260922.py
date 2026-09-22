"""Regression checks for the organizer-reviewed September 22 snapshot."""

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
    return {row["slug"]: row for row in json.loads(path.read_text())["records"]}


def test_expired_higher_test_and_vosh_are_closed_in_public_response(app, monkeypatch):
    from app.services import catalog

    monkeypatch.setattr(catalog, "_utcnow", lambda: datetime(2026, 9, 22, 18, tzinfo=UTC))
    rows = snapshot()
    for slug in ("vysshaya-proba-biology", "vosh-2026-27-01", "vosh-2026-27-16"):
        olympiad, edition = upsert_catalog_record(rows[slug])
        result = serialize_olympiad(olympiad, edition, hide_expired_registration=True)
        assert result["registration_status"] == "not_open"
        assert result["registration_url"] is None
    olympiad, edition = upsert_catalog_record(rows["vosh-2026-27-02"])
    assert serialize_olympiad(olympiad, edition, hide_expired_registration=True)[
        "registration_status"
    ] == "open"


def test_cancelled_profile_preserves_plan_and_stage_ids(app, user_id):
    row = snapshot()["shag-v-budushchee-biology"]
    previous = deepcopy(row)
    previous["status"] = "published"
    previous["data_status"] = "previous_year_estimate"
    previous["stages"][0].update(starts_on="2026-10-03", ends_on="2026-12-01")
    olympiad, edition = upsert_catalog_record(previous)
    db.session.commit()
    stage_ids = {stage.key: stage.id for stage in edition.stages}
    plan = UserOlympiadPlan(user_id=user_id, edition_id=edition.id)
    db.session.add(plan)
    db.session.commit()
    plan_id, edition_id = plan.id, edition.id
    _, updated = upsert_catalog_record(row)
    db.session.commit()
    assert updated.id == edition_id
    assert updated.status.value == "archived"
    assert db.session.get(UserOlympiadPlan, plan_id) is not None
    assert {stage.key: stage.id for stage in updated.stages} == stage_ids
    assert all(stage.starts_on is None and stage.ends_on is None for stage in updated.stages)


def test_new_open_registration_notifies_existing_subscriber_once(app, user_id):
    row = snapshot()["dano-data-analysis"]
    previous = deepcopy(row)
    previous.update(registration_status="not_open", registration_url=None)
    _, edition = upsert_catalog_record(previous)
    db.session.commit()
    plan = UserOlympiadPlan(user_id=user_id, edition_id=edition.id)
    db.session.add(plan)
    db.session.commit()
    upsert_catalog_record(row)
    db.session.commit()
    assert len(schedule_registration_notification_dispatches()) == 1
    upsert_catalog_record(row)
    db.session.commit()
    assert schedule_registration_notification_dispatches() == []


def test_snapshot_keeps_all_mkoshp_leagues_and_bmstu_exceptions():
    rows = snapshot()
    mkoshp = rows["mkoshp-programming"]
    stages = {stage["key"]: stage for stage in mkoshp["stages"]}
    assert stages["amateur-qualifying"]["starts_on"] == "2026-09-26"
    assert stages["amateur-final"]["starts_on"] == "2026-10-04"
    assert stages["qualifying-otborochnyi-kvalifikatsionnyi-tur"]["starts_on"] == "2026-10-11"
    assert stages["final-zaklyuchitelnyi-tur"]["starts_on"] == "2026-11-15"
    assert rows["registry-2026-27-052-04"]["registration_status"] == "announced"
    assert rows["registry-2026-27-052-05"]["registration_status"] == "open"
    assert rows["shag-v-budushchee-biology"]["status"] == "archived"
