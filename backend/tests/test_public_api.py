from copy import deepcopy
from datetime import UTC, datetime

from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services import catalog as catalog_service


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

    live = client.get("/api/live")
    assert live.status_code == 200
    assert live.get_json() == {"status": "ok"}


def test_readiness_reports_database_and_redis_failures(app, client, monkeypatch):
    def database_unavailable(*_args, **_kwargs):
        raise SQLAlchemyError("database unavailable")

    with app.app_context():
        monkeypatch.setattr(db.session, "execute", database_unavailable)
        response = client.get("/api/health")
    assert response.status_code == 503
    assert response.get_json() == {
        "status": "unavailable",
        "checks": {"database": "error", "redis": "ok"},
    }

    class UnavailableRedis:
        def ping(self):
            raise RedisError("redis unavailable")

    monkeypatch.undo()
    app.config["SESSION_REDIS"] = UnavailableRedis()
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.get_json() == {
        "status": "unavailable",
        "checks": {"database": "ok", "redis": "error"},
    }


def test_catalog_filters_and_detail(admin_client, olympiad_payload):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201

    response = admin_client.get(
        "/api/v1/olympiads",
        query_string={"grade": 9, "profile": "Математика", "registry_level": 1},
    )
    assert response.status_code == 200
    document = response.get_json()
    assert document["pagination"]["total"] == 1
    assert document["items"][0]["slug"] == "test-math"
    assert document["items"][0]["directions"] == [
        {"slug": "mathematics", "name": "Математика"}
    ]
    assert document["items"][0]["next_stage"]["is_date_confirmed"] is False
    assert document["items"][0]["benefit_summary"] == [
        {
            "benefit_type": "bvi",
            "has_bvi": True,
            "has_hundred_points": False,
            "admission_year": 2027,
            "university": {
                "slug": "test-university",
                "name": "Тестовый университет",
                "short_name": "ТУ",
            },
        }
    ]

    detail = admin_client.get("/api/v1/olympiads/test-math")
    assert detail.status_code == 200
    payload = detail.get_json()
    assert payload["grades"] == [8, 9, 10, 11]
    assert payload["academic_year"] == "2026/27"
    assert payload["cycle_label"] == "Календарный цикл 2026"
    assert payload["eligibility_notes"] == "Учащиеся 8–11 классов."
    assert payload["materials"][0]["material_type"] == "archive"
    assert payload["benefits"][0]["university"]["short_name"] == "ТУ"
    assert payload["benefits"][0]["has_bvi"] is True
    assert payload["benefits"][0]["has_hundred_points"] is False
    assert "benefit_summary" not in payload
    assert payload["registry_status"] == "approved"


def test_public_registration_url_expires_at_timezone_aware_cutoff(
    admin_client, olympiad_payload, monkeypatch
):
    olympiad_payload["registration_closes_at"] = "2026-08-26T08:50:00Z"
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201

    monkeypatch.setattr(
        catalog_service,
        "_utcnow",
        lambda: datetime(2026, 8, 26, 8, 49, 59, tzinfo=UTC),
    )
    before = admin_client.get("/api/v1/olympiads/test-math").get_json()
    assert before["registration_url"] == "https://example.test/register"
    assert before["registration_status"] == "open"
    assert before["registration_checked_on"] == "2026-08-26"
    open_listing = admin_client.get(
        "/api/v1/olympiads", query_string={"registration_status": "open"}
    ).get_json()
    assert open_listing["pagination"]["total"] == 1
    open_metadata = admin_client.get(
        "/api/v1/metadata", query_string={"registration_status": "open"}
    ).get_json()
    assert open_metadata["counts"]["total"] == 1
    assert open_metadata["universities"][0]["slug"] == "test-university"
    assert before["registration_closes_at"] == "2026-08-26T08:50:00+00:00"

    monkeypatch.setattr(
        catalog_service,
        "_utcnow",
        lambda: datetime(2026, 8, 26, 8, 50, tzinfo=UTC),
    )
    at_cutoff = admin_client.get("/api/v1/olympiads/test-math").get_json()
    assert at_cutoff["registration_url"] is None
    assert at_cutoff["registration_status"] == "not_open"
    assert at_cutoff["registration_closes_at"] == "2026-08-26T08:50:00+00:00"
    listing = admin_client.get("/api/v1/olympiads").get_json()["items"][0]
    assert listing["registration_url"] is None
    assert listing["registration_closes_at"] == "2026-08-26T08:50:00+00:00"
    assert (
        admin_client.get(
            "/api/v1/olympiads", query_string={"registration_status": "open"}
        ).get_json()["pagination"]["total"]
        == 0
    )
    assert (
        admin_client.get(
            "/api/v1/olympiads", query_string={"registration_status": "not_open"}
        ).get_json()["pagination"]["total"]
        == 1
    )
    expired_metadata = admin_client.get(
        "/api/v1/metadata", query_string={"registration_status": "open"}
    ).get_json()
    assert expired_metadata["counts"]["total"] == 0
    assert expired_metadata["universities"] == []

    monkeypatch.setattr(
        catalog_service,
        "_utcnow",
        lambda: datetime(2026, 8, 26, 8, 50, 1, tzinfo=UTC),
    )
    after = admin_client.get("/api/v1/olympiads/test-math").get_json()
    assert after["registration_url"] is None

    admin_detail = admin_client.get("/api/admin/olympiads/test-math").get_json()
    assert admin_detail["registration_url"] == "https://example.test/register"
    assert admin_detail["registration_status"] == "open"
    assert admin_detail["registration_closes_at"] == (
        "2026-08-26T08:50:00+00:00"
    )

    invalid = admin_client.get(
        "/api/v1/olympiads", query_string={"registration_status": "mystery"}
    )
    assert invalid.status_code == 400
    assert "статус регистрации" in invalid.get_json()["error"]


def test_registration_available_excludes_only_confirmed_closed_windows(
    admin_client, olympiad_payload, monkeypatch
):
    monkeypatch.setattr(
        catalog_service,
        "_utcnow",
        lambda: datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )

    def record(slug, status, *, stage_start, stage_end, closes_at=None):
        payload = deepcopy(olympiad_payload)
        payload.update(
            slug=slug,
            name=f"Тестовая олимпиада — {slug}",
            registration_status=status,
            registration_url=(
                f"https://example.test/register/{slug}" if status == "open" else None
            ),
            registration_closes_at=closes_at,
        )
        payload["stages"] = [
            {
                **payload["stages"][0],
                "name": "Регистрация",
                "stage_type": "registration",
                "starts_on": stage_start,
                "ends_on": stage_end,
            }
        ]
        return payload

    records = [
        record(
            "open-current",
            "open",
            stage_start="2026-08-01",
            stage_end="2026-09-01",
            closes_at="2026-09-01T00:00:00Z",
        ),
        record(
            "announced-future",
            "announced",
            stage_start="2026-11-01",
            stage_end="2026-11-30",
        ),
        record(
            "not-open-future",
            "not_open",
            stage_start="2026-10-30",
            stage_end="2026-12-02",
        ),
        record(
            "not-open-past",
            "not_open",
            stage_start="2026-08-01",
            stage_end="2026-08-10",
        ),
        record(
            "not-found-future",
            "not_found",
            stage_start="2026-10-01",
            stage_end="2026-10-31",
        ),
        record(
            "open-expired",
            "open",
            stage_start="2026-08-01",
            stage_end="2026-08-10",
            closes_at="2026-08-25T00:00:00Z",
        ),
    ]
    for payload in records:
        assert admin_client.post("/api/admin/olympiads", json=payload).status_code == 201

    listing = admin_client.get(
        "/api/v1/olympiads",
        query_string={"registration_available": "true", "per_page": 100},
    ).get_json()
    assert {item["slug"] for item in listing["items"]} == {
        "open-current",
        "announced-future",
        "not-open-future",
        "not-open-past",
        "not-found-future",
    }

    metadata = admin_client.get(
        "/api/v1/metadata", query_string={"registration_available": "true"}
    ).get_json()
    assert metadata["counts"]["total"] == 5
    assert metadata["universities"] == [
        {
            "slug": "test-university",
            "name": "Тестовый университет",
            "short_name": "ТУ",
            "count": 5,
        }
    ]


def test_catalog_excludes_wrong_grade(admin_client, olympiad_payload):
    admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    response = admin_client.get("/api/v1/olympiads", query_string={"grade": 5})
    assert response.get_json()["pagination"]["total"] == 0


def test_grade_filter_keeps_unknown_cards_but_orders_exact_matches_first(
    admin_client, olympiad_payload
):
    unknown = {
        **olympiad_payload,
        "slug": "unknown-grades",
        "name": "Олимпиада с уточняемыми классами",
        "grades": [],
        "is_popular": True,
        "website_url": "https://unknown.example.test",
    }
    exact = {
        **olympiad_payload,
        "slug": "exact-grades",
        "name": "Олимпиада для пятого класса",
        "grades": [5],
        "is_popular": False,
        "website_url": "https://exact.example.test",
    }
    assert admin_client.post("/api/admin/olympiads", json=unknown).status_code == 201
    assert admin_client.post("/api/admin/olympiads", json=exact).status_code == 201

    document = admin_client.get(
        "/api/v1/olympiads", query_string={"grade": 5}
    ).get_json()

    assert [item["slug"] for item in document["items"]] == [
        "exact-grades",
        "unknown-grades",
    ]
    assert [item["grade_match"] for item in document["items"]] == [
        "exact",
        "unknown",
    ]


def test_metadata(admin_client, olympiad_payload):
    admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    payload = admin_client.get("/api/v1/metadata").get_json()
    assert payload["profiles"] == ["Математика"]
    assert payload["categories"] == [
        {"slug": "mathematics", "name": "Математика", "count": 1}
    ]
    assert payload["benefit_types"] == ["bvi"]
    assert payload["universities"] == [
        {
            "slug": "test-university",
            "name": "Тестовый университет",
            "short_name": "ТУ",
            "count": 1,
        }
    ]
    assert payload["counts"] == {
        "total": 1,
        "popular": 1,
        "registry": 1,
        "registry_approved": 1,
        "registry_draft": 0,
        "registry_not_listed": 0,
        "registry_previous_year": 0,
    }


def test_direction_taxonomy_filters_anonymous_list_calendar_and_metadata_without_duplicates(
    app, admin_client, olympiad_payload
):
    records = [
        olympiad_payload,
        {
            **deepcopy(olympiad_payload),
            "slug": "test-math-ai",
            "name": "Тестовая олимпиада — математическое моделирование и ИИ",
            "profile": "Математическое моделирование и искусственный интеллект",
            "website_url": "https://math-ai.example.test",
        },
        {
            **deepcopy(olympiad_payload),
            "slug": "test-ai",
            "name": "Тестовая олимпиада — искусственный интеллект",
            "profile": "Искусственный интеллект",
            "website_url": "https://ai.example.test",
        },
        {
            **deepcopy(olympiad_payload),
            "slug": "test-new-profile",
            "name": "Тестовая олимпиада — новый профиль",
            "profile": "Новый междисциплинарный профиль",
            "website_url": "https://new-profile.example.test",
        },
    ]
    for record in records:
        assert admin_client.post("/api/admin/olympiads", json=record).status_code == 201

    anonymous = app.test_client()
    metadata = anonymous.get("/api/v1/metadata").get_json()
    categories = {item["slug"]: item for item in metadata["categories"]}
    assert categories["mathematics"] == {
        "slug": "mathematics",
        "name": "Математика",
        "count": 2,
    }
    assert categories["ai-data"] == {
        "slug": "ai-data",
        "name": "Данные и искусственный интеллект",
        "count": 2,
    }
    assert categories["interdisciplinary"] == {
        "slug": "interdisciplinary",
        "name": "Междисциплинарные направления",
        "count": 1,
    }

    first_page = anonymous.get(
        "/api/v1/olympiads",
        query_string={"direction": "ai-data", "page": 1, "per_page": 1},
    ).get_json()
    second_page = anonymous.get(
        "/api/v1/olympiads",
        query_string={"direction": "ai-data", "page": 2, "per_page": 1},
    ).get_json()
    assert first_page["pagination"] == {
        "page": 1,
        "per_page": 1,
        "pages": 2,
        "total": 2,
    }
    assert second_page["pagination"]["total"] == 2
    assert {
        first_page["items"][0]["slug"],
        second_page["items"][0]["slug"],
    } == {"test-math-ai", "test-ai"}
    assert first_page["items"][0]["directions"]

    exact_profile = anonymous.get(
        "/api/v1/olympiads",
        query_string={
            "direction": "ai-data",
            "profile": "Математическое моделирование и искусственный интеллект",
        },
    ).get_json()
    assert exact_profile["pagination"]["total"] == 1
    assert exact_profile["items"][0]["slug"] == "test-math-ai"

    fallback = anonymous.get(
        "/api/v1/olympiads", query_string={"direction": "interdisciplinary"}
    ).get_json()
    assert fallback["pagination"]["total"] == 1
    assert fallback["items"][0]["slug"] == "test-new-profile"
    assert fallback["items"][0]["directions"] == [
        {
            "slug": "interdisciplinary",
            "name": "Междисциплинарные направления",
        }
    ]

    calendar = anonymous.get(
        "/api/v1/calendar",
        query_string={"direction": "ai-data", "month": "2026-10"},
    ).get_json()
    assert calendar["total"] == 2
    assert {event["olympiad"]["slug"] for event in calendar["events"]} == {
        "test-math-ai",
        "test-ai",
    }
    assert all(event["olympiad"]["directions"] for event in calendar["events"])

    fallback_calendar = anonymous.get(
        "/api/v1/calendar",
        query_string={"direction": "interdisciplinary", "month": "2026-10"},
    ).get_json()
    assert fallback_calendar["total"] == 1
    assert fallback_calendar["events"][0]["olympiad"]["slug"] == "test-new-profile"

    for endpoint, extra in (
        ("/api/v1/olympiads", {}),
        ("/api/v1/calendar", {"month": "2026-10"}),
    ):
        invalid = anonymous.get(
            endpoint,
            query_string={"direction": "unknown-direction", **extra},
        )
        assert invalid.status_code == 400
        assert invalid.get_json() == {"error": "Неизвестное направление"}


def test_benefit_filters_match_one_benefit_without_duplicates_or_auth(
    app, admin_client, olympiad_payload
):
    bvi = olympiad_payload["benefits"][0]
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201
    olympiad_payload["updated_at"] = created.get_json()["updated_at"]
    olympiad_payload["benefits"] = [
        bvi,
        {
            "title": "Денежный приз",
            "benefit_type": "prize",
            "admission_year": 2027,
            "university": {
                "slug": "second-university",
                "name": "Второй университет",
                "short_name": "ВУ",
            },
        },
        {
            "title": "Особое право",
            "benefit_type": "other",
            "admission_year": 2027,
            "university": {
                "slug": "test-university",
                "name": "Тестовый университет",
                "short_name": "ТУ",
            },
        },
        {
            "title": "Смешанное право",
            "benefit_type": "other",
            "has_bvi": True,
            "has_hundred_points": True,
            "admission_year": 2027,
            "university": {
                "slug": "mixed-university",
                "name": "Смешанный университет",
                "short_name": "СУ",
            },
        },
    ]
    assert (
        admin_client.put(
            "/api/admin/olympiads/test-math", json=olympiad_payload
        ).status_code
        == 200
    )

    previous_year = deepcopy(olympiad_payload)
    previous_year.update(
        slug="previous-benefit",
        name="Прошлогодняя олимпиада",
        family_name="Прошлогодняя олимпиада",
        academic_year="2025/26",
    )
    previous_year["benefits"] = [
        {
            "title": "Прошлогодняя льгота",
            "benefit_type": "hundred_points",
            "university": {
                "slug": "old-university",
                "name": "Старый университет",
                "short_name": "СУ",
            },
        }
    ]
    assert (
        admin_client.post("/api/admin/olympiads", json=previous_year).status_code
        == 201
    )

    draft = deepcopy(previous_year)
    draft.update(
        slug="draft-benefit",
        name="Черновик олимпиады",
        family_name="Черновик олимпиады",
        academic_year="2026/27",
        status="draft",
    )
    draft["benefits"][0]["university"] = {
        "slug": "draft-university",
        "name": "Университет из черновика",
        "short_name": None,
    }
    assert admin_client.post("/api/admin/olympiads", json=draft).status_code == 201

    anonymous_client = app.test_client()
    bvi_listing = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={"benefit_type": "bvi", "per_page": 1},
    ).get_json()
    assert bvi_listing["pagination"] == {
        "page": 1,
        "per_page": 1,
        "pages": 1,
        "total": 1,
    }
    assert [item["slug"] for item in bvi_listing["items"]] == ["test-math"]

    university_listing = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={"university": "test-university"},
    ).get_json()
    assert university_listing["pagination"]["total"] == 1

    prize_only_university = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={"university": "second-university"},
    ).get_json()
    assert prize_only_university["pagination"]["total"] == 0

    matching = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={
            "benefit_type": "prize",
            "university": "second-university",
        },
    ).get_json()
    assert matching["pagination"]["total"] == 1

    # The edition has BVI and a benefit from second-university, but not in the
    # same Benefit row, so these two conditions must not cross-match.
    mismatched = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={
            "benefit_type": "bvi",
            "university": "second-university",
        },
    ).get_json()
    assert mismatched["pagination"]["total"] == 0

    for benefit_type, flag in (
        ("bvi", "has_bvi"),
        ("hundred_points", "has_hundred_points"),
    ):
        mixed = anonymous_client.get(
            "/api/v1/olympiads",
            query_string={
                "benefit_type": benefit_type,
                "university": "mixed-university",
            },
        ).get_json()
        assert mixed["pagination"]["total"] == 1
        mixed_summary = next(
            benefit
            for benefit in mixed["items"][0]["benefit_summary"]
            if benefit["university"]["slug"] == "mixed-university"
        )
        assert mixed_summary["benefit_type"] == "other"
        assert mixed_summary[flag] is True

    mixed_other = anonymous_client.get(
        "/api/v1/olympiads",
        query_string={
            "benefit_type": "other",
            "university": "mixed-university",
        },
    ).get_json()
    assert mixed_other["pagination"]["total"] == 1

    matching_calendar = anonymous_client.get(
        "/api/v1/calendar",
        query_string={
            "month": "2026-10",
            "benefit_type": "prize",
            "university": "second-university",
        },
    ).get_json()
    assert matching_calendar["total"] == 1
    assert matching_calendar["events"][0]["olympiad"]["slug"] == "test-math"

    mismatched_calendar = anonymous_client.get(
        "/api/v1/calendar",
        query_string={
            "month": "2026-10",
            "benefit_type": "bvi",
            "university": "second-university",
        },
    ).get_json()
    assert mismatched_calendar["total"] == 0
    assert mismatched_calendar["events"] == []

    mixed_calendar = anonymous_client.get(
        "/api/v1/calendar",
        query_string={
            "month": "2026-10",
            "benefit_type": "hundred_points",
            "university": "mixed-university",
        },
    ).get_json()
    assert mixed_calendar["total"] == 1

    metadata = anonymous_client.get("/api/v1/metadata").get_json()
    assert metadata["benefit_types"] == [
        "bvi",
        "hundred_points",
        "other",
        "prize",
    ]
    assert metadata["universities"] == [
        {
            "slug": "mixed-university",
            "name": "Смешанный университет",
            "short_name": "СУ",
            "count": 1,
        },
        {
            "slug": "test-university",
            "name": "Тестовый университет",
            "short_name": "ТУ",
            "count": 1,
        },
    ]

    for invalid_type in ("grant", "imaginary"):
        invalid = anonymous_client.get(
            "/api/v1/olympiads",
            query_string={"benefit_type": invalid_type},
        )
        assert invalid.status_code == 400
        assert invalid.get_json() == {"error": "Неизвестный тип льготы"}


def test_registry_status_filter(admin_client, olympiad_payload):
    admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    approved = admin_client.get(
        "/api/v1/olympiads", query_string={"registry_status": "approved"}
    )
    assert approved.get_json()["pagination"]["total"] == 1
    invalid = admin_client.get(
        "/api/v1/olympiads", query_string={"registry_status": "imaginary"}
    )
    assert invalid.status_code == 400


def test_calendar_returns_overlapping_stages(admin_client, olympiad_payload):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201

    response = admin_client.get(
        "/api/v1/calendar",
        query_string={
            "academic_year": "2026/27",
            "month": "2026-10",
            "grade": 9,
            "profile": "Математика",
        },
    )

    assert response.status_code == 200
    document = response.get_json()
    assert document["range"] == {
        "starts_on": "2026-10-01",
        "ends_on": "2026-10-31",
    }
    assert document["total"] == 1
    assert document["events"][0]["olympiad"] == {
        "slug": "test-math",
        "name": "Тестовая олимпиада — Математика",
        "family_name": "Тестовая олимпиада",
            "profile": "Математика",
            "directions": [{"slug": "mathematics", "name": "Математика"}],
            "is_team": False,
        "is_popular": True,
        "cycle_label": "Календарный цикл 2026",
        "data_status": "previous_year_estimate",
        "registry_status": "approved",
        "registry_level": 1,
        "grades": [8, 9, 10, 11],
        "grade_match": "exact",
    }
    assert document["events"][0]["stage"]["date_precision"] == "approximate"
    assert document["events"][0]["stage"]["starts_on"] == "2026-10-01"
    assert document["events"][0]["stage"]["ends_on"] == "2026-10-31"


def test_calendar_keeps_an_ends_only_deadline_anonymous(
    admin_client, client, olympiad_payload
):
    olympiad_payload["data_status"] = "partial"
    olympiad_payload["stages"] = [
        {
            "name": "Крайний срок первого тура",
            "position": 1,
            "starts_on": None,
            "ends_on": "2026-12-31",
            "date_precision": "exact",
            "is_date_confirmed": True,
            "format": "online",
            "source_url": "https://example.test/deadline",
        }
    ]
    assert admin_client.post("/api/admin/olympiads", json=olympiad_payload).status_code == 201

    response = client.get("/api/v1/calendar", query_string={"month": "2026-12"})
    assert response.status_code == 200
    stage = response.get_json()["events"][0]["stage"]
    assert stage["starts_on"] is None
    assert stage["ends_on"] == "2026-12-31"


def test_calendar_applies_filters_and_validates_month(admin_client, olympiad_payload):
    admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    empty = admin_client.get(
        "/api/v1/calendar", query_string={"month": "2026-10", "grade": 5}
    )
    assert empty.status_code == 200
    assert empty.get_json()["events"] == []

    outside_range = admin_client.get(
        "/api/v1/calendar", query_string={"month": "2026-09"}
    )
    assert outside_range.status_code == 200
    assert outside_range.get_json()["total"] == 0

    invalid = admin_client.get(
        "/api/v1/calendar", query_string={"month": "2026-13"}
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "Месяц должен быть в формате YYYY-MM"
