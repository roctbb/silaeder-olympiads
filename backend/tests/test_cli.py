import json
from datetime import UTC, datetime

from app.extensions import db
from app.models import Admin, EditionStatus, Olympiad, OlympiadEdition


def _write_catalog(tmp_path, records):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"records": records}), encoding="utf-8")
    return path


def test_create_admin_rejects_weak_password_for_new_and_existing_account(app):
    runner = app.test_cli_runner()

    for password in ("", "            ", "too-short"):
        result = runner.invoke(
            args=["create-admin", "--username", "new-editor", "--password", password]
        )
        assert result.exit_code != 0
        assert "не менее 12 символов" in result.output

    created = runner.invoke(
        args=[
            "create-admin",
            "--username",
            "new-editor",
            "--password",
            "long-safe-password",
        ]
    )
    assert created.exit_code == 0, created.output

    rejected_update = runner.invoke(
        args=["create-admin", "--username", "new-editor", "--password", "short"]
    )
    assert rejected_update.exit_code != 0
    with app.app_context():
        admin = db.session.scalar(db.select(Admin).where(Admin.username == "new-editor"))
        assert admin is not None
        assert admin.check_password("long-safe-password")
        assert not admin.check_password("short")


def test_import_catalog_sync_archives_only_missing_editions(
    app, admin_client, olympiad_payload, tmp_path
):
    second = {
        **olympiad_payload,
        "slug": "second-math",
        "name": "Вторая олимпиада",
        "website_url": "https://second.example.test",
    }
    previous_year = {
        **olympiad_payload,
        "slug": "previous-math",
        "name": "Прошлый сезон",
        "academic_year": "2025/26",
        "website_url": "https://previous.example.test",
    }
    for payload in (olympiad_payload, second, previous_year):
        assert admin_client.post("/api/admin/olympiads", json=payload).status_code == 201

    runner = app.test_cli_runner()
    source = _write_catalog(tmp_path, [olympiad_payload])
    result = runner.invoke(args=["import-catalog", str(source), "--sync"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        current = {
            (edition.olympiad.slug, edition.academic_year): edition.status
            for edition in db.session.scalars(
                db.select(OlympiadEdition).join(Olympiad)
            ).all()
        }
    assert current[("test-math", "2026/27")] == EditionStatus.PUBLISHED
    assert current[("second-math", "2026/27")] == EditionStatus.ARCHIVED
    assert current[("previous-math", "2025/26")] == EditionStatus.PUBLISHED
    assert "архивировано отсутствующих сезонов: 1" in result.output


def test_import_catalog_rejects_duplicate_slug_and_year(app, olympiad_payload, tmp_path):
    source = _write_catalog(tmp_path, [olympiad_payload, olympiad_payload])

    result = app.test_cli_runner().invoke(args=["import-catalog", str(source)])

    assert result.exit_code != 0
    assert "Повторная запись" in result.output


def test_import_catalog_persists_and_validates_cycle_label(
    app, olympiad_payload, tmp_path
):
    olympiad_payload["cycle_label"] = "  Календарный цикл 2026  "
    source = _write_catalog(tmp_path, [olympiad_payload])

    imported = app.test_cli_runner().invoke(args=["import-catalog", str(source)])

    assert imported.exit_code == 0, imported.output
    with app.app_context():
        edition = db.session.scalar(db.select(OlympiadEdition))
        assert edition is not None
        assert edition.cycle_label == "Календарный цикл 2026"

    olympiad_payload["cycle_label"] = "x" * 121
    rejected_source = _write_catalog(tmp_path, [olympiad_payload])
    rejected = app.test_cli_runner().invoke(
        args=["import-catalog", str(rejected_source)]
    )

    assert rejected.exit_code != 0
    assert "cycle_label" in rejected.output


def test_import_catalog_persists_timezone_aware_registration_close(
    app, olympiad_payload, tmp_path
):
    olympiad_payload["registration_closes_at"] = "2026-08-26T11:50:00+03:00"
    source = _write_catalog(tmp_path, [olympiad_payload])

    imported = app.test_cli_runner().invoke(args=["import-catalog", str(source)])

    assert imported.exit_code == 0, imported.output
    with app.app_context():
        edition = db.session.scalar(db.select(OlympiadEdition))
        assert edition is not None
        closes_at = edition.registration_closes_at
        assert closes_at is not None
        if closes_at.tzinfo is None:
            closes_at = closes_at.replace(tzinfo=UTC)
        assert closes_at.astimezone(UTC) == datetime(
            2026, 8, 26, 8, 50, tzinfo=UTC
        )

    olympiad_payload["registration_closes_at"] = "2026-08-26T08:50:00"
    rejected_source = _write_catalog(tmp_path, [olympiad_payload])
    rejected = app.test_cli_runner().invoke(
        args=["import-catalog", str(rejected_source)]
    )

    assert rejected.exit_code != 0
    assert "registration_closes_at" in rejected.output
