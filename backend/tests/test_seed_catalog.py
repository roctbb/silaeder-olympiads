import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.extensions import db
from app.models import Olympiad, OlympiadEdition, RegistryStatus
from app.services.catalog import upsert_catalog_record
from app.services.directions import MAPPED_PROFILES

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "catalog.json"
MATERIAL_AUDIT_PATH = Path(__file__).resolve().parents[2] / "research" / "material_link_audit.json"
MOSH_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "official_mosh_asof_2026_08_25.json"
)
RESEARCH_PATH = Path(__file__).resolve().parents[2] / "research"
PRIORITY_COMPETITIONS_PATH = RESEARCH_PATH / "priority_competitions.json"
STRUCTURE_ENRICHMENT_PATHS = [
    RESEARCH_PATH / "catalog_structure_enrichment.json",
    *sorted(RESEARCH_PATH.glob("catalog_structure_batch_*.json")),
    RESEARCH_PATH / "unresolved_mgimo_mipt_itmo_enrichment.json",
    RESEARCH_PATH / "unresolved_vernadsky_music_enrichment.json",
]
CURRENT_DATE_ENRICHMENT_PATHS = sorted(RESEARCH_PATH.glob("current_dates_*_enrichment.json"))
CURRENT_REGISTRATION_ENRICHMENT_PATHS = sorted(RESEARCH_PATH.glob("current_registration_*.json"))
UNIVERSITY_BENEFITS_ENRICHMENT_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "university_benefits_2026_enrichment.json"
)
ADDITIONAL_UNIVERSITY_BENEFITS_PATHS = sorted(
    {
        *RESEARCH_PATH.glob("mosh_benefits_*_2026.json"),
        *RESEARCH_PATH.glob("level1_benefits_gap_*_2026.json"),
        *RESEARCH_PATH.glob("bmstu_benefits_2026.json"),
    }
)
LEVEL_ONE_BENEFIT_GAP_SLUGS = {
    "registry-2026-27-003-01",
    "registry-2026-27-004-01",
    "registry-2026-27-004-02",
    "registry-2026-27-014-02",
    "registry-2026-27-014-05",
    "registry-2026-27-016-01",
    "registry-2026-27-018-01",
    "registry-2026-27-023-01",
    "registry-2026-27-023-02",
    "registry-2026-27-023-03",
    "registry-2026-27-026-01",
    "registry-2026-27-028-01",
    "registry-2026-27-028-02",
    "registry-2026-27-028-03",
    "registry-2026-27-032-02",
    "registry-2026-27-032-08",
    "registry-2026-27-033-01",
    "registry-2026-27-033-03",
    "registry-2026-27-034-02",
    "registry-2026-27-036-01",
    "registry-2026-27-043-01",
    "registry-2026-27-043-02",
    "registry-2026-27-046-03",
    "registry-2026-27-070-01",
    "registry-2026-27-071-01",
    "registry-2026-27-071-03",
    "registry-2026-27-073-01",
    "lomonosov-tournament-physics",
}
LEVEL_ONE_REVIEWED_NO_MATCH_SLUGS: set[str] = set()
REVIEWED_NO_MATCH_NOTE = (
    "Официальные правила приёма-2026 проверены, но точная вузовская льгота "
    "для этого профиля не подтверждена."
)
DEPRECATED_VSOSH_ARCHIVE = "https://vos.olimpiada.ru/tasks"
ORGANIZER_PLACEHOLDER = "Полный состав организаторов указан в проекте приказа Минобрнауки России"


def test_seed_profiles_have_explicit_direction_taxonomy_coverage():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    seed_profiles = {record["profile"] for record in records}

    assert len(seed_profiles) == 134
    assert seed_profiles == MAPPED_PROFILES


def test_seed_catalog_is_complete_and_importable(app):
    document = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records = document["records"]
    assert document["records_count"] == len(records)
    assert len(records) >= 357
    assert len({item["slug"] for item in records}) == len(records)

    required_slugs = {
        "dano-data-analysis",
        "prod-backend",
        "maxwell-physics",
        "moebius-mathematics",
        "mkoshp-programming",
        "vkoshp-programming",
        "lomonosov-tournament-mathematics",
    }
    assert required_slugs <= {item["slug"] for item in records}
    # The legal project contains 303 profile rows. Four МОШ rows expand into
    # nine independently selectable official directions, hence five extra
    # service cards carrying their shared registry level.
    assert sum(item["registry_status"] == "draft" for item in records) == 308
    assert all(item["sources"] for item in records)
    assert all(record["organizer"] != ORGANIZER_PLACEHOLDER for record in records)
    assert all(len(record["organizer"]) <= 255 for record in records)

    for record in records:
        long_note_sentences = [
            sentence.casefold()
            for sentence in re.split(r"(?<=\.)\s+", record.get("notes") or "")
            if len(sentence) >= 80
        ]
        assert len(long_note_sentences) == len(set(long_note_sentences))
        if record["grades"]:
            assert "grades=[]" not in (record.get("notes") or "")
        assert ".." not in (record.get("notes") or "")
        for stage in record["stages"]:
            if (
                stage["date_precision"] == "exact"
                and stage.get("starts_on")
                and stage.get("ends_on")
            ):
                assert stage["starts_on"] == stage["ends_on"]
        if record["data_status"] == "confirmed":
            assert "даты 2026/27 могут быть ещё не опубликованы" not in (record.get("notes") or "")
        if record["data_status"] == "previous_year_estimate":
            assert not any(stage["is_date_confirmed"] for stage in record["stages"])
            assert "эти даты не использовать" not in (record.get("notes") or "").casefold()
            for stage in record["stages"]:
                dated_values = [
                    date.fromisoformat(stage[field])
                    for field in ("starts_on", "ends_on")
                    if stage.get(field)
                ]
                assert all(date(2026, 8, 1) <= value <= date(2027, 7, 31) for value in dated_values)
                if dated_values:
                    assert "Прогноз на 2026/27" in (stage.get("details") or "")
        for benefit in record["benefits"]:
            description = (benefit.get("description") or "").casefold()
            if "льгот" in description and "нет" in description:
                assert benefit["benefit_type"] not in {"bvi", "hundred_points"}
        upsert_catalog_record(record)
    db.session.commit()

    assert db.session.scalar(select(func.count()).select_from(Olympiad)) == len(records)
    assert (
        db.session.scalar(
            select(func.count())
            .select_from(OlympiadEdition)
            .where(OlympiadEdition.registry_status == RegistryStatus.DRAFT)
        )
        == 308
    )

    prod = next(item for item in records if item["slug"] == "prod-mlops")
    assert prod["stages"][0]["starts_on"] == "2026-10-30"
    assert prod["stages"][-1]["ends_on"] == "2027-03-18"


def test_mosh_official_directions_are_distinct_cards():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    snapshot = json.loads(MOSH_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    expected = {item["display_profile"]: item for item in snapshot["profiles"]}
    actual = {
        item["profile"]: item for item in records if item["family_name"] == snapshot["family_name"]
    }

    assert len(expected) == 32
    assert set(actual) == set(expected)

    registry_profile_counts: dict[str, int] = {}
    for item in snapshot["profiles"]:
        if item["registry_profile"]:
            registry_profile_counts[item["registry_profile"]] = (
                registry_profile_counts.get(item["registry_profile"], 0) + 1
            )

    for profile, source in expected.items():
        record = actual[profile]
        assert record["website_url"] == source["website_url"]
        assert record["grades"] == source["grades_estimate_2026_27"]
        assert source["materials_url"] in {material["url"] for material in record["materials"]}
        if source["registry_profile"]:
            assert record["registry_status"] == source["registry_status_2026_27"]
            assert record["registry_level"] == source["draft_level_2026_27"]
        if registry_profile_counts.get(source["registry_profile"], 0) > 1:
            assert record["slug"] == f"mosh-2026-27-{source['site_code']}"

    assert not {
        "Информатика",
        "Математика",
        "Предпрофессиональная",
        "Робототехника",
    } & set(actual)


def test_next_year_advancement_is_not_labeled_as_admission():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    advancements = [
        benefit
        for record in records
        for benefit in record["benefits"]
        if benefit["title"] == "Допуск в финал следующего сезона"
    ]

    assert len(advancements) == 26
    assert all(benefit["benefit_type"] == "other" for benefit in advancements)
    assert all(benefit["admission_year"] is None for benefit in advancements)
    assert all(
        "следующ" in (benefit.get("description") or "").casefold() for benefit in advancements
    )


def test_benefit_admission_cycles_and_explicit_right_flags_are_semantic():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    benefits = [benefit for record in records for benefit in record["benefits"]]

    assert all(isinstance(benefit["has_bvi"], bool) for benefit in benefits)
    assert all(isinstance(benefit["has_hundred_points"], bool) for benefit in benefits)
    assert all(benefit["has_bvi"] for benefit in benefits if benefit["benefit_type"] == "bvi")
    assert all(
        benefit["has_hundred_points"]
        for benefit in benefits
        if benefit["benefit_type"] == "hundred_points"
    )

    # A season label is not an admission campaign.  Awards, career bonuses and
    # next-season advancement must not create admission/filter rights.
    assert not any(benefit["admission_year"] == 2025 for benefit in benefits)
    prizes = [benefit for benefit in benefits if benefit["benefit_type"] == "prize"]
    assert prizes
    assert all(benefit["admission_year"] is None for benefit in prizes)
    assert all(not benefit["has_bvi"] and not benefit["has_hundred_points"] for benefit in prizes)

    advancements = [
        benefit for benefit in benefits if benefit["title"] == "Допуск в финал следующего сезона"
    ]
    assert advancements
    assert all(
        benefit["admission_year"] is None
        and not benefit["has_bvi"]
        and not benefit["has_hundred_points"]
        for benefit in advancements
    )

    dano = by_slug["dano-data-analysis"]
    dano_by_university = {
        (benefit.get("university") or {}).get("slug"): benefit
        for benefit in dano["benefits"]
        if benefit.get("university")
    }
    assert dano_by_university["niu-vshe"]["has_bvi"] is True
    assert dano_by_university["niu-vshe"]["has_hundred_points"] is True
    assert dano_by_university["universitet-itmo"]["has_bvi"] is True
    assert dano_by_university["universitet-itmo"]["has_hundred_points"] is False
    agu = dano_by_university["adygei-skii-gosudarstvennyi-universitet"]
    assert agu["title"] == "Баллы за индивидуальные достижения"
    assert agu["admission_year"] == 2026
    assert agu["has_bvi"] is False
    assert agu["has_hundred_points"] is False

    career = next(
        benefit for benefit in dano["benefits"] if "Т-Старт" in (benefit.get("description") or "")
    )
    assert career["admission_year"] is None
    assert career["has_bvi"] is False
    assert career["has_hundred_points"] is False

    # Reviewed mixed university rules remain type=other but expose both exact
    # rights to filters.  The helper also recognizes "максимальный балл".
    for slug in ("registry-2026-27-003-01", "registry-2026-27-004-02"):
        mixed = [
            benefit for benefit in by_slug[slug]["benefits"] if benefit["benefit_type"] == "other"
        ]
        assert mixed
        assert all(benefit["has_bvi"] and benefit["has_hundred_points"] for benefit in mixed)


def test_negative_registry_references_are_notes_and_sources_not_benefits():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    priority = json.loads(PRIORITY_COMPETITIONS_PATH.read_text(encoding="utf-8"))
    negative_references = [
        (record["slug"], benefit)
        for record in priority["records"]
        for benefit in record.get("benefits", [])
        if benefit.get("status") == "none_via_rsosh"
    ]

    assert len(negative_references) == 5
    for slug, reference in negative_references:
        record = by_slug[slug]
        assert reference["description"] in record["notes"]
        assert not any(
            benefit.get("description") == reference["description"] for benefit in record["benefits"]
        )
        assert any(
            source["source_type"] == "benefit_reference" and source["url"] == reference["url"]
            for source in record["sources"]
        )

    assert not any(
        benefit["title"] == "Вузовских льгот по перечню нет"
        for record in records
        for benefit in record["benefits"]
    )


def test_reviewed_structure_enrichment_fills_only_sourced_gaps():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    enrichments = [
        json.loads(path.read_text(encoding="utf-8")) for path in STRUCTURE_ENRICHMENT_PATHS
    ]

    for enrichment in enrichments:
        assert enrichment["target_academic_year"] == "2026/27"
        assert len({entry["family_name"] for entry in enrichment["families"]}) == len(
            enrichment["families"]
        )
        assert len({entry["slug"] for entry in enrichment["slugs"]}) == len(enrichment["slugs"])

    family_entries = [entry for item in enrichments for entry in item["families"]]
    slug_entries = [entry for item in enrichments for entry in item["slugs"]]

    stage_families = {entry["family_name"] for entry in family_entries if entry.get("stages")}
    stage_targets = {
        record["slug"] for record in records if record["family_name"] in stage_families
    } | {entry["slug"] for entry in slug_entries if entry.get("stages")}
    grade_families = {entry["family_name"] for entry in family_entries if entry.get("grades")}
    grade_targets = {
        record["slug"] for record in records if record["family_name"] in grade_families
    } | {entry["slug"] for entry in slug_entries if entry.get("grades")}

    assert len(stage_targets) >= 131
    assert len(grade_targets) >= 51
    assert all(by_slug[slug]["stages"] for slug in stage_targets)
    assert all(by_slug[slug]["grades"] for slug in grade_targets)

    assert sum(not record["grades"] for record in records) <= 5
    assert all(record["grades"] or record["eligibility_notes"] for record in records)
    assert all(record["stages"] for record in records)

    nto = [
        record
        for record in records
        if record["family_name"].startswith(
            "Всероссийская междисциплинарная олимпиада школьников 8–11"
        )
    ]
    assert len(nto) == 21
    assert all(record["grades"] == [8, 9, 10, 11] for record in nto)
    assert all(
        [stage["key"] for stage in record["stages"]]
        == ["first-qualifying", "second-qualifying", "final"]
        for record in nto
    )

    mosh = [
        record for record in records if record["family_name"] == "Московская олимпиада школьников"
    ]
    assert len(mosh) == 32
    assert all(record["data_status"] == "partial" for record in mosh)
    assert all(
        [stage["key"] for stage in record["stages"]] == ["qualifying", "final"] for record in mosh
    )
    assert all(
        not stage["starts_on"] and not stage["ends_on"] and stage["date_precision"] == "tba"
        for record in mosh
        for stage in record["stages"]
    )

    innopolis_math = by_slug["registry-2026-27-020-04"]
    assert innopolis_math["previous_year_reference"] == "2025/26"
    assert innopolis_math["stages"][0]["starts_on"] == "2026-11-03"
    assert all(
        stage["date_precision"] == "approximate"
        and not stage["is_date_confirmed"]
        and "Прогноз на 2026/27" in (stage["details"] or "")
        for stage in innopolis_math["stages"]
    )

    fiztekh_math = by_slug["registry-2026-27-051-04"]
    assert fiztekh_math["data_status"] == "partial"
    assert fiztekh_math["grades"] == [9, 10, 11]
    assert fiztekh_math["stages"][-1]["starts_on"] == "2027-02-14"
    assert not fiztekh_math["stages"][-1]["is_date_confirmed"]
    assert "Прогноз на 2026/27" not in (fiztekh_math["stages"][-1]["details"] or "")

    world_of_law = by_slug["registry-2026-27-057-01"]
    assert world_of_law["grades"] == [7, 8, 9, 10, 11]
    assert world_of_law["organizer"] == (
        "Всероссийский государственный университет юстиции (РПА Минюста России)"
    )
    assert world_of_law["website_url"] == "https://rpa-mu.wixsite.com/my-site"
    assert "grades=[]" not in (world_of_law["notes"] or "")

    nonnumeric_music_profiles = [
        by_slug[f"registry-2026-27-019-{profile:02d}"] for profile in (1, 3, 5, 6, 7)
    ]
    assert all(not record["grades"] for record in nonnumeric_music_profiles)
    assert all(record["eligibility_notes"] for record in nonnumeric_music_profiles)
    assert all(record["stages"] for record in nonnumeric_music_profiles)


def test_current_dates_are_confirmed_overlays_on_stable_stage_keys():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    targets = []

    for path in CURRENT_DATE_ENRICHMENT_PATHS:
        enrichment = json.loads(path.read_text(encoding="utf-8"))
        assert enrichment["target_academic_year"] == "2026/27"
        for entry in enrichment["slugs"]:
            stages_by_key = {stage["key"]: stage for stage in by_slug[entry["slug"]]["stages"]}
            for raw_stage in entry["stages"]:
                targets.append((entry["slug"], raw_stage["key"]))
                stage = stages_by_key[raw_stage["key"]]
                assert stage["is_date_confirmed"] is True
                assert stage["source_url"] == raw_stage["source_url"]
                for field in (
                    "starts_on",
                    "ends_on",
                    "registration_opens_on",
                    "registration_closes_on",
                ):
                    if field in raw_stage:
                        assert stage[field] == raw_stage[field]

    assert len(targets) >= 25
    assert len(targets) == len(set(targets))


def test_deadlines_and_regulatory_windows_are_not_rendered_as_event_ranges():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}

    sibiriada = by_slug["registry-2026-27-045-01"]
    expected_deadlines = {
        "qualifying-internet": "2026-12-31",
        "qualifying-offline": "2027-01-31",
        "final": "2027-03-31",
    }
    assert {stage["key"] for stage in sibiriada["stages"]} == set(expected_deadlines)
    assert sibiriada["data_status"] == "partial"
    for stage in sibiriada["stages"]:
        assert stage["starts_on"] is None
        assert stage["ends_on"] == expected_deadlines[stage["key"]]
        assert stage["date_precision"] == "exact"
        assert stage["is_date_confirmed"] is True
        assert "дедлайн" in (stage["details"] or "")

    innagrika = by_slug["registry-2026-27-006-01"]
    assert [stage["key"] for stage in innagrika["stages"]] == [
        "qualifying",
        "semifinal",
        "final",
    ]
    assert all(
        stage["starts_on"] is None
        and stage["ends_on"] is None
        and stage["date_precision"] == "tba"
        and stage["is_date_confirmed"] is False
        for stage in innagrika["stages"]
    )
    qualifying = innagrika["stages"][0]
    assert qualifying["registration_opens_on"] == "2026-09-01"
    assert qualifying["registration_closes_on"] == "2026-10-31"
    assert "1–31 октября 2026 года" in qualifying["details"]
    assert "1 ноября — 31 декабря 2026 года" in innagrika["stages"][1]["details"]
    assert "1 декабря 2026 года — 28 февраля 2027 года" in innagrika["stages"][2]["details"]


def test_current_registration_links_are_reviewed_for_the_target_season():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    seen = set()
    reviewed_open = set()
    status_counts = Counter()

    for path in CURRENT_REGISTRATION_ENRICHMENT_PATHS:
        enrichment = json.loads(path.read_text(encoding="utf-8"))
        assert enrichment["target_academic_year"] == "2026/27"
        assert enrichment["checked_on"] == "2026-08-26"
        for entry in enrichment["slugs"]:
            slug = entry["slug"]
            assert slug not in seen
            seen.add(slug)
            assert entry["registration_status"] in {
                "open",
                "announced",
                "not_open",
                "not_found",
            }
            status_counts[entry["registration_status"]] += 1
            assert by_slug[slug]["registration_status"] == entry["registration_status"]
            assert by_slug[slug]["registration_checked_on"] == enrichment["checked_on"]
            assert entry["source_url"] in {source["url"] for source in by_slug[slug]["sources"]}
            assert entry["source_url"].startswith(("http://", "https://"))
            assert entry["evidence"]
            if entry["registration_status"] == "open":
                reviewed_open.add(slug)
                assert entry["registration_url"].startswith(("http://", "https://"))
                assert by_slug[slug]["registration_url"] == entry["registration_url"]
                assert by_slug[slug]["registration_closes_at"] == entry.get(
                    "registration_closes_at"
                )
                if entry.get("registration_closes_at"):
                    closes_at = datetime.fromisoformat(
                        entry["registration_closes_at"].replace("Z", "+00:00")
                    )
                    assert closes_at.utcoffset() is not None
            elif entry["registration_status"] == "announced":
                assert entry["registration_url"].startswith(("http://", "https://"))
                assert entry.get("registration_closes_at") is None
                assert by_slug[slug]["registration_url"] is None
                assert by_slug[slug]["registration_closes_at"] is None
            else:
                assert entry["registration_url"] is None
                assert entry.get("registration_closes_at") is None
                assert by_slug[slug]["registration_url"] is None
                assert by_slug[slug]["registration_closes_at"] is None

    published_registration_links = {
        record["slug"] for record in records if record["registration_url"]
    }
    assert reviewed_open == published_registration_links
    assert seen == set(by_slug)
    assert status_counts == {
        "open": 50,
        "announced": 29,
        "not_open": 58,
        "not_found": 220,
    }
    assert by_slug["registry-2026-27-005-01"]["registration_url"] == (
        "https://talent.kruzhok.org/registration?event=10334"
    )
    nto_records = [
        record
        for record in records
        if record["registration_url"] == "https://talent.kruzhok.org/registration?event=10334"
    ]
    assert len(nto_records) == 21
    assert {record["registration_closes_at"] for record in nto_records} == {"2026-08-26T08:50:00Z"}
    assert by_slug["registry-2026-27-017-01"]["registration_url"] == (
        "https://distolymp.spbu.ru/phys/olymp/registration/user/"
    )
    ordinary_higher_test = [
        record
        for record in records
        if record["slug"].startswith("vysshaya-proba-")
        and record["slug"] != "vysshaya-proba-industrial-programming"
    ]
    assert len(ordinary_higher_test) == 24
    assert {record["registration_url"] for record in ordinary_higher_test} == {
        "https://myolymp.hse.ru/school.html"
    }
    assert all(
        "регистрация 2026/27 не подтверждена" not in (record["notes"] or "")
        for record in records
        if record["registration_url"]
    )


def test_calendar_year_cycles_are_not_presented_as_new_academic_seasons():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    financial_security = by_slug["registry-2026-27-021-01"]

    assert financial_security["cycle_label"] == "Календарный цикл 2026"
    assert "расписание календарного цикла 2026" in financial_security["notes"]
    assert "расписание 2026/27" not in financial_security["notes"]
    assert financial_security["registration_url"] is None
    assert {stage["starts_on"][:4] for stage in financial_security["stages"]} == {"2026"}
    assert any(
        source["url"] == "https://rosfinolymp.ru/stages" and source["source_year"] == "2026"
        for source in financial_security["sources"]
    )

    artificial_intelligence = by_slug["registry-2026-27-007-01"]
    assert artificial_intelligence["cycle_label"] == "Сезон 2026"
    assert "официальный календарный сезон" in artificial_intelligence["notes"]
    assert artificial_intelligence["stages"][0]["starts_on"] == "2026-07-01"
    assert artificial_intelligence["stages"][-1]["ends_on"] == "2026-11-21"
    assert all(stage["is_date_confirmed"] is True for stage in artificial_intelligence["stages"])
    assert any(
        source["url"] == "https://ai.edu.gov.ru/" and source["source_year"] == "2026"
        for source in artificial_intelligence["sources"]
    )


def test_bmstu_biology_is_a_separate_non_registry_profile():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    biology = by_slug["shag-v-budushchee-biology"]

    assert biology["family_name"] == "Олимпиада школьников «Шаг в будущее»"
    assert biology["profile"] == "Биология"
    assert biology["grades"] == list(range(5, 12))
    assert biology["is_in_registry"] is False
    assert biology["registry_status"] == "not_listed"
    assert biology["registry_level"] is None
    assert biology["registration_status"] == "announced"
    assert biology["registration_url"] is None
    assert [
        (stage["key"], stage["starts_on"], stage["is_date_confirmed"])
        for stage in biology["stages"]
    ] == [
        ("qualifying", "2026-10-03", False),
        ("final", "2027-02-01", False),
    ]
    assert {(material["material_type"], material["url"]) for material in biology["materials"]} == {
        ("archive", "https://olymp.bmstu.ru/ru/biology-olymp"),
        ("archive", "https://olymp.bmstu.ru/ru/variants"),
    }
    assert len(biology["benefits"]) == 1
    assert biology["benefits"][0]["admission_year"] == 2026
    assert biology["benefits"][0]["benefit_type"] == "other"
    assert biology["benefits"][0]["has_bvi"] is False
    assert biology["benefits"][0]["has_hundred_points"] is False
    assert {
        "https://olymp.bmstu.ru/ru/biology-olymp",
        "https://olymp.bmstu.ru/ru/profiles",
        "https://olymp.bmstu.ru/ru/calendar",
    } <= {source["url"] for source in biology["sources"]}

    expected_profile_urls = {
        "registry-2026-27-052-01": "https://olymp.bmstu.ru/ru/engeneering-olymp",
        "registry-2026-27-052-02": "https://olymp.bmstu.ru/ru/programming-olymp",
        "registry-2026-27-052-03": "https://olymp.bmstu.ru/ru/graphics-olymp",
        "registry-2026-27-052-04": "https://olymp.bmstu.ru/ru/mathematics-olymp",
        "registry-2026-27-052-05": "https://olymp.bmstu.ru/ru/physics-olymp",
        "registry-2026-27-052-06": "https://olymp.bmstu.ru/ru/khimiya",
    }
    for slug, website_url in expected_profile_urls.items():
        record = by_slug[slug]
        assert record["website_url"] == website_url
        assert "8–11 классы" in record["eligibility_notes"]
        assert "5 класса" in record["eligibility_notes"]


def test_bmstu_gazprom_has_all_six_profiles_and_hybrid_finals():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    family = [
        record
        for record in records
        if record["family_name"] == "Отраслевая олимпиада школьников «Газпром»"
    ]

    assert {record["profile"] for record in family} == {
        "Инженерное дело",
        "Информационные и коммуникационные технологии",
        "Физика",
        "Математика",
        "Химия",
        "Экономика",
    }
    assert len(family) == 6
    assert all(record["grades"] == [8, 9, 10, 11] for record in family)
    assert all(record["stages"][-1]["format"] == "hybrid" for record in family)

    expected_new_profiles = {
        "gazprom-mathematics": (
            "Математика",
            "2027-02-22",
            "mathematics.zip",
        ),
        "gazprom-chemistry": ("Химия", "2027-02-07", "chemistry.zip"),
        "gazprom-economics": ("Экономика", "2027-01-31", "economics.zip"),
    }
    for slug, (profile, final_date, archive_name) in expected_new_profiles.items():
        record = by_slug[slug]
        assert record["profile"] == profile
        assert record["registry_status"] == "not_listed"
        assert record["registry_level"] is None
        assert record["data_status"] == "previous_year_estimate"
        assert record["registration_status"] == "not_found"
        assert record["registration_url"] is None
        assert record["stages"][-1]["starts_on"] == final_date
        assert record["stages"][-1]["is_date_confirmed"] is False
        assert any(material["url"].endswith(archive_name) for material in record["materials"])

    for record in family:
        bmstu_benefits = [
            benefit
            for benefit in record["benefits"]
            if (benefit.get("university") or {}).get("slug")
            == "mgtu-imeni-n-e-baumana"
        ]
        assert len(bmstu_benefits) == 1
        assert bmstu_benefits[0]["admission_year"] == 2026
    ict_benefit = by_slug["registry-2026-27-065-02"]["benefits"][0]
    assert ict_benefit["has_bvi"] is True
    assert ict_benefit["has_hundred_points"] is True


def test_university_benefits_use_only_published_2026_rules():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    by_family_profile = {(record["family_name"], record["profile"]): record for record in records}
    enrichment = json.loads(UNIVERSITY_BENEFITS_ENRICHMENT_PATH.read_text(encoding="utf-8"))

    assert enrichment["target_catalog_year"] == "2026/27"
    assert enrichment["admission_cycle"] == 2026
    assert len(enrichment["universities"]) == 8

    all_benefits = [benefit for record in records for benefit in record["benefits"]]
    assert len(all_benefits) == 359
    assert Counter(benefit["benefit_type"] for benefit in all_benefits) == {
        "bvi": 92,
        "hundred_points": 46,
        "other": 203,
        "prize": 18,
    }

    concrete_benefits = [benefit for benefit in all_benefits if benefit.get("university")]
    assert len(concrete_benefits) == 276
    priority_university_slugs = {
        university["slug"] for university in enrichment["universities"].values()
    }
    assert priority_university_slugs <= {
        benefit["university"]["slug"] for benefit in concrete_benefits
    }
    assert (
        sum(
            any(
                benefit.get("university") and benefit["admission_year"] == 2026
                for benefit in record["benefits"]
            )
            for record in records
        )
        == 155
    )

    reviewed_benefits = []

    def assert_reviewed_rule(record, raw_benefit):
        university = enrichment["universities"][raw_benefit["university_ref"]]
        matches = [
            benefit
            for benefit in record["benefits"]
            if (benefit.get("university") or {}).get("slug") == university["slug"]
            and benefit["benefit_type"] == raw_benefit["benefit_type"]
            and benefit["admission_year"] == raw_benefit["admission_year"]
            and benefit.get("ege_subject") == raw_benefit.get("ege_subject")
        ]
        assert len(matches) == 1
        benefit = matches[0]
        assert benefit["title"] == raw_benefit["title"]
        assert benefit["source_url"] == raw_benefit["source_url"]
        assert "не прогноз на приём-2027" in benefit["description"].casefold()
        reviewed_benefits.append(benefit)

    for rule in enrichment["family_rules"]:
        for profile in rule["profiles"]:
            assert_reviewed_rule(by_family_profile[(rule["family_name"], profile)], rule["benefit"])
    for rule in enrichment["slug_rules"]:
        for slug in rule["slugs"]:
            assert_reviewed_rule(by_slug[slug], rule["benefit"])

    assert len(reviewed_benefits) == 128
    reviewed_source_urls = {benefit["source_url"] for benefit in reviewed_benefits}
    assert all(
        benefit["admission_year"] == 2026
        for benefit in all_benefits
        if benefit.get("source_url") in reviewed_source_urls
    )

    mipt_math = next(
        benefit
        for benefit in by_slug["registry-2026-27-051-04"]["benefits"]
        if (benefit.get("university") or {}).get("slug") == "mfti"
    )
    assert mipt_math["benefit_type"] == "hundred_points"
    assert mipt_math["ege_subject"] == "Математика"
    assert mipt_math["ege_min_score"] == 75

    bmstu_informatics = next(
        benefit
        for benefit in by_slug["registry-2026-27-052-02"]["benefits"]
        if (benefit.get("university") or {}).get("slug") == "mgtu-imeni-n-e-baumana"
    )
    assert bmstu_informatics["benefit_type"] == "bvi"
    assert all(
        program_code in bmstu_informatics["description"]
        for program_code in ("01.03.02", "09.03.04", "10.05.01", "10.05.03")
    )

    mephi_physics = next(
        benefit
        for benefit in by_slug["registry-2026-27-066-03"]["benefits"]
        if (benefit.get("university") or {}).get("slug") == "niyau-mifi"
    )
    assert mephi_physics["benefit_type"] == "bvi"
    assert mephi_physics["ege_subject"] == "Физика"
    assert mephi_physics["ege_min_score"] == 75

    itmo_lomonosov_math = next(
        benefit
        for benefit in by_slug["registry-2026-27-048-13"]["benefits"]
        if (benefit.get("university") or {}).get("slug") == "universitet-itmo"
    )
    assert itmo_lomonosov_math["benefit_type"] == "bvi"
    assert itmo_lomonosov_math["diploma_requirement"].startswith("Победитель;")

    world_of_law = next(
        benefit
        for benefit in by_slug["registry-2026-27-057-01"]["benefits"]
        if (benefit.get("university") or {}).get("slug")
        == "vserossiyskiy-gosudarstvennyy-universitet-yustitsii"
    )
    assert world_of_law["benefit_type"] == "other"
    assert world_of_law["admission_year"] == 2026
    assert "11 класса" in world_of_law["description"]
    assert world_of_law["source_url"] == "https://rpa-mu.wixsite.com/my-site"

    for new_profile_slug in (
        "registry-2026-27-048-02",
        "registry-2026-27-048-22",
    ):
        assert not any(
            (benefit.get("university") or {}).get("slug") == "mgu-imeni-m-v-lomonosova"
            for benefit in by_slug[new_profile_slug]["benefits"]
        )


def test_additional_benefits_match_reviewed_university_matrices():
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["records"]
    by_slug = {record["slug"]: record for record in records}
    assert len(ADDITIONAL_UNIVERSITY_BENEFITS_PATHS) >= 2

    reviewed_targets = set()
    reviewed_count = 0
    expected_reviewed_count = 0
    level_one_checked = set()
    level_one_reviewed_no_match = set()
    for path in ADDITIONAL_UNIVERSITY_BENEFITS_PATHS:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["target_catalog_year"] == "2026/27"
        assert document.get("admission_cycle", document.get("admission_year")) == 2026
        universities = document["universities"]
        is_mosh_matrix = path.name.startswith("mosh_benefits_")
        is_level_one_gap = path.name.startswith("level1_benefits_gap_")
        is_bmstu_matrix = path.name == "bmstu_benefits_2026.json"
        assert is_mosh_matrix or is_level_one_gap or is_bmstu_matrix
        for entry in document["entries"]:
            record = by_slug[entry["slug"]]
            assert record["profile"] == entry["profile"]
            raw_benefits = [entry["benefit"]] if entry.get("benefit") else entry.get("benefits", [])
            if is_mosh_matrix:
                assert record["family_name"] == "Московская олимпиада школьников"
            elif is_level_one_gap:
                assert record["registry_level"] == 1
                assert 11 in record["grades"]
                assert entry["slug"] in LEVEL_ONE_BENEFIT_GAP_SLUGS
                assert entry["slug"] not in level_one_checked
                level_one_checked.add(entry["slug"])
                review_status = entry.get("review_status") or (
                    "confirmed" if raw_benefits else "reviewed_no_match"
                )
                assert review_status in {"confirmed", "reviewed_no_match"}
                if review_status == "reviewed_no_match":
                    assert not raw_benefits
                    assert entry.get("unresolved")
                    assert REVIEWED_NO_MATCH_NOTE in record["notes"]
                    level_one_reviewed_no_match.add(entry["slug"])
                    continue
                assert raw_benefits
            else:
                assert record["family_name"] == "Отраслевая олимпиада школьников «Газпром»"
                assert raw_benefits
            expected_reviewed_count += len(raw_benefits)
            for raw in raw_benefits:
                university = universities[raw["university_ref"]]
                target = (entry["slug"], university["slug"])
                assert target not in reviewed_targets
                reviewed_targets.add(target)
                matches = [
                    benefit
                    for benefit in record["benefits"]
                    if (benefit.get("university") or {}).get("slug") == university["slug"]
                ]
                assert len(matches) == 1
                benefit = matches[0]
                assert benefit["benefit_type"] == raw["benefit_type"]
                assert benefit["admission_year"] == 2026
                assert benefit["title"] == raw["title"]
                assert benefit["source_url"] == raw["source_url"]
                assert "прогноз" in benefit["description"].casefold()
                assert "2027" in benefit["description"]
                reviewed_count += 1

    assert reviewed_count == expected_reviewed_count
    assert len(reviewed_targets) == expected_reviewed_count
    level_one_paths = [
        path
        for path in ADDITIONAL_UNIVERSITY_BENEFITS_PATHS
        if path.name.startswith("level1_benefits_gap_")
    ]
    if len(level_one_paths) == 2:
        assert level_one_checked == LEVEL_ONE_BENEFIT_GAP_SLUGS
        assert level_one_reviewed_no_match == LEVEL_ONE_REVIEWED_NO_MATCH_SLUGS
    mosh_records = [
        record for record in records if record["family_name"] == "Московская олимпиада школьников"
    ]
    assert sum(bool(record["benefits"]) for record in mosh_records) == 19
    assert sum(len(record["benefits"]) for record in mosh_records) == 67


def test_seed_materials_are_profile_specific_and_audited():
    catalog_bytes = CATALOG_PATH.read_bytes()
    document = json.loads(catalog_bytes)
    records = document["records"]

    material_urls = {
        material["url"] for record in records for material in record.get("materials", [])
    }
    material_occurrences = sum(len(record.get("materials", [])) for record in records)
    records_with_materials = sum(bool(record.get("materials")) for record in records)
    records_with_past_tasks = {
        record["slug"]
        for record in records
        if any(
            material["material_type"] in {"tasks", "solutions", "archive"}
            for material in record.get("materials", [])
        )
    }
    records_without_materials = {
        record["slug"] for record in records if not record.get("materials")
    }

    assert records_with_materials == 357
    assert len(records_with_past_tasks) == 356
    assert records_without_materials == set()
    assert len(material_urls) >= 286
    assert DEPRECATED_VSOSH_ARCHIVE not in material_urls
    assert all(record["materials"] for record in records if record["is_popular"])

    by_slug = {record["slug"]: record for record in records}
    expected_gap_materials = {
        "registry-2026-27-006-01": {
            (
                "archive",
                "https://innagrika.ru/olimpiada/zadanija-i-pobediteli-proshlyh-let/",
            ),
            (
                "tasks",
                "https://innagrika.ru/wp-content/uploads/2026/05/"
                "7.materialy_zadanij_i_kriterii_ocenki_profil_agrogenetika_2025-26.pdf",
            ),
        },
        "registry-2026-27-039-01": {
            (
                "archive",
                "https://opk.pravolimp.ru/pages/6361009f53bb56318d003c08",
            ),
        },
        "registry-2026-27-054-01": {
            ("archive", "https://techno-cup.ru/archive"),
        },
        "registry-2026-27-079-01": {
            ("tasks", "https://disk.360.yandex.ru/d/bP7LfOrVlE3khg"),
        },
    }
    for slug, expected_materials in expected_gap_materials.items():
        actual_materials = {
            (material["material_type"], material["url"]) for material in by_slug[slug]["materials"]
        }
        assert expected_materials <= actual_materials

    biology_materials = by_slug["registry-2026-27-030-02"]["materials"]
    assert {(material["material_type"], material["url"]) for material in biology_materials} == {
        (
            "other",
            "http://academy.fsb.ru/upload/iblock/a77/pb6cpyv2bnrln4f8dfaqgsuu0l9r723u.pdf",
        )
    }

    vsosh_records = [
        record
        for record in records
        if record["family_name"] == "Всероссийская олимпиада школьников"
    ]
    assert len(vsosh_records) == 28
    for record in vsosh_records:
        assert any(
            material["material_type"] == "archive"
            and material["url"].startswith("https://vserosolimp.edsoo.ru/")
            for material in record["materials"]
        )

    audit = json.loads(MATERIAL_AUDIT_PATH.read_text(encoding="utf-8"))
    assert audit["catalog_sha256"] == hashlib.sha256(catalog_bytes).hexdigest()
    assert audit["catalog_records"] == len(records)
    assert audit["material_occurrences"] == material_occurrences
    assert audit["unique_urls"] == len(material_urls)
    assert audit["olympiads_with_materials"] == records_with_materials
    assert audit["summary"]["status_unique_urls"] == {"ok": len(material_urls)}
    assert {row["url"] for row in audit["results"]} == material_urls
