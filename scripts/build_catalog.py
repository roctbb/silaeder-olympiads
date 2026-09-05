#!/usr/bin/env python3
"""Build the importable catalog from reviewed research snapshots.

The script is intentionally not a scraper. It converts checked-in, source-linked
research files into the strict shape accepted by ``flask import-catalog``.
"""

from __future__ import annotations

import calendar
import json
import re
import unicodedata
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
OUTPUT = ROOT / "data" / "seed" / "catalog.json"
STRUCTURE_ENRICHMENT = RESEARCH / "catalog_structure_enrichment.json"
STRUCTURE_ENRICHMENT_GLOB = "catalog_structure_batch_*.json"
STRUCTURE_ENRICHMENT_EXTRAS = (
    "unresolved_mgimo_mipt_itmo_enrichment.json",
    "unresolved_vernadsky_music_enrichment.json",
)
CURRENT_DATES_ENRICHMENT_GLOB = "current_dates_*_enrichment.json"
CURRENT_REGISTRATION_ENRICHMENT_GLOB = "current_registration_*.json"
PROFILE_METADATA_ENRICHMENT_PATHS = (
    RESEARCH / "bmstu_step_profile_metadata.json",
)
UNIVERSITY_BENEFITS_ENRICHMENT = RESEARCH / "university_benefits_2026_enrichment.json"
EXTRA_COMPETITION_PATHS = (
    RESEARCH / "bmstu_biology_competition.json",
    RESEARCH / "bmstu_gazprom_competitions.json",
    RESEARCH / "euler_olympiad_competition.json",
    RESEARCH / "professional_skills_competitions.json",
)
ADDITIONAL_UNIVERSITY_BENEFITS_GLOBS = (
    "mosh_benefits_*_2026.json",
    "level1_benefits_gap_*_2026.json",
    "bmstu_benefits_2026.json",
)
REVIEWED_NO_MATCH_NOTE = (
    "Официальные правила приёма-2026 проверены, но точная вузовская льгота "
    "для этого профиля не подтверждена. Это не доказывает отсутствие льгот "
    "в других вузах и не является прогнозом приёма-2027."
)
SNAPSHOT_DATE = "2026-08-26"
TARGET_ACADEMIC_YEAR = "2026/27"
TARGET_ACADEMIC_START_YEAR = 2026

# A technically reachable landing page can still be a poor material link.  The
# generic Moscow archive is intentionally replaced with direct federal subject
# pages so a student lands on tasks for the selected ВсОШ profile.
DEPRECATED_MATERIAL_URLS = {"https://vos.olimpiada.ru/tasks"}

ALLOWED_DATA_STATUSES = {
    "confirmed",
    "partial",
    "previous_year_estimate",
    "announcement_pending",
}
ALLOWED_REGISTRATION_STATUSES = {"open", "announced", "not_open", "not_found"}
UNCONFIRMED_REGISTRATION_NOTE = (
    f"регистрация {TARGET_ACADEMIC_YEAR} не подтверждена."
)
DATA_STATUS_RANK = {
    "announcement_pending": 0,
    "previous_year_estimate": 1,
    "partial": 2,
    "confirmed": 3,
}
ALLOWED_REGISTRY_STATUSES = {"not_listed", "draft", "approved", "previous_year"}

TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

MONTHS = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "ма": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}

DRAFT_GAP_SENTENCE = (
    "Классы и даты в ежегодном проекте не указаны; "
    "grades=[] до проверки регламента организатора."
)
DRAFT_VERIFIED_STRUCTURE_PENDING_DATES_SENTENCE = (
    "Классы и структура этапов проверены по опубликованным материалам "
    "организатора; даты 2026/27 могут быть ещё не опубликованы."
)
ORGANIZER_PLACEHOLDER = (
    "Полный состав организаторов указан в проекте приказа Минобрнауки России"
)
OFFICIAL_ORGANIZER_DISPLAY_OVERRIDES = {
    21: (
        "Минобрнауки России, Росфинмониторинг России и Минпросвещения России "
        "(есть соорганизаторы)"
    ),
    58: (
        "Санкт-Петербургское отделение Математического института "
        "им. В. А. Стеклова РАН (есть соорганизаторы)"
    ),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower()).translate(TRANSLITERATION)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "olympiad"


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    result = re.sub(r"\s+", " ", str(value)).strip()
    return result or None


def clean_url(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else None


def normalize_year_label(value: Any, default: str | None = None) -> str | None:
    text = clean_text(value)
    if not text:
        return default
    academic = re.search(r"(20\d{2})\s*[/_-]\s*(?:20)?(\d{2})", text)
    if academic:
        return f"{academic.group(1)}/{academic.group(2)}"
    single = re.search(r"20\d{2}", text)
    return single.group() if single else default


def join_notes(*values: Any) -> str | None:
    result: list[str] = []
    for value in values:
        text = clean_text(value)
        if text:
            text = re.sub(r"\.{2}(?=\s|$)", ".", text)
        if text and text not in result:
            result.append(text)
    combined = " ".join(result)
    if not combined:
        return None

    # Notes are assembled from independent reviewed overlays.  Two composite
    # blocks can share one long disclaimer even when the blocks themselves are
    # not equal.  Deduplicate only long, complete sentences: short fragments
    # may be abbreviations (for example, initials in a university name).
    sentences = re.split(r"(?<=\.)\s+", combined)
    seen_long: set[str] = set()
    unique_sentences: list[str] = []
    for sentence in sentences:
        identity = sentence.casefold()
        if len(sentence) >= 80 and identity in seen_long:
            continue
        unique_sentences.append(sentence)
        if len(sentence) >= 80:
            seen_long.add(identity)
    return " ".join(unique_sentences)


def reconcile_draft_gap_note(record: dict[str, Any]) -> None:
    """Remove a stale draft placeholder after organizer data was verified."""

    notes = record.get("notes")
    if not notes or DRAFT_GAP_SENTENCE not in notes:
        return

    has_grades = bool(record.get("grades"))
    has_eligibility = bool(record.get("eligibility_notes"))
    has_stages = bool(record.get("stages"))
    if has_grades and has_stages:
        replacement = DRAFT_VERIFIED_STRUCTURE_PENDING_DATES_SENTENCE
    elif has_grades:
        replacement = (
            "Классы проверены по опубликованным материалам организатора; "
            "структура этапов и даты 2026/27 пока уточняются."
        )
    elif has_eligibility and has_stages:
        replacement = (
            "Условия участия и структура этапов проверены по опубликованным "
            "материалам организатора; числовой диапазон общеобразовательных "
            "классов организатор не публикует."
        )
    elif has_eligibility:
        replacement = (
            "Условия участия проверены по опубликованным материалам организатора; "
            "числовой диапазон общеобразовательных классов организатор не публикует."
        )
    elif has_stages:
        replacement = (
            "Структура этапов проверена по опубликованным материалам организатора; "
            "классы и даты 2026/27 пока уточняются."
        )
    else:
        return

    record["notes"] = clean_text(notes.replace(DRAFT_GAP_SENTENCE, replacement))


def official_organizer_display(family: dict[str, Any]) -> str:
    """Return a truthful, import-safe organizer label from the official draft."""

    list_number = int(family["list_number"])
    override = OFFICIAL_ORGANIZER_DISPLAY_OVERRIDES.get(list_number)
    if override:
        return override

    full = clean_text(family.get("organizer"))
    if not full:
        raise ValueError(f"В проекте нет организатора для позиции {list_number}")
    if len(full) <= 255:
        return full

    closing_quote = full.find("»")
    if closing_quote < 0:
        raise ValueError(
            f"Нельзя безопасно сократить организатора позиции {list_number}"
        )
    first_organizer = full[: closing_quote + 1]
    suffix = " (есть соорганизаторы)"
    display = (
        first_organizer + suffix
        if len(first_organizer) + len(suffix) <= 255
        else first_organizer
    )
    if len(display) > 255:
        raise ValueError(f"Организатор позиции {list_number} длиннее 255 символов")
    return display


def normalize_identity(value: str) -> str:
    text = value.casefold().replace("ё", "е")
    text = re.sub(
        r"всероссийская|московская|олимпиада|школьников|межрегиональная", " ", text
    )
    return re.sub(r"[^a-zа-я0-9]+", " ", text).strip()


def normalize_profile_identity(value: str) -> str:
    normalized = normalize_identity(value)
    aliases = {
        "иностранные языки": "иностранный язык",
    }
    return aliases.get(normalized, normalized)


def title_profile(profile: str) -> str:
    return profile[:1].upper() + profile[1:] if profile else profile


def normalize_date(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


def normalize_aware_datetime(value: Any) -> str | None:
    """Return a canonical UTC ISO timestamp, rejecting naive datetimes."""

    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def shift_iso_date(value: str | None, years: int) -> str | None:
    if not value or years == 0:
        return value
    parsed = date.fromisoformat(value)
    try:
        return parsed.replace(year=parsed.year + years).isoformat()
    except ValueError:
        # 29 February is projected to the last valid February day.
        return parsed.replace(year=parsed.year + years, day=28).isoformat()


def project_stage_to_target_year(
    stage: dict[str, Any], source_reference: str | None
) -> dict[str, Any]:
    result = deepcopy(stage)
    date_fields = (
        "starts_on",
        "ends_on",
        "registration_opens_on",
        "registration_closes_on",
    )
    dated_values = [
        date.fromisoformat(result[field]) for field in date_fields if result.get(field)
    ]
    if not dated_values:
        return result

    anchor = min(dated_values)
    source_academic_start = anchor.year if anchor.month >= 8 else anchor.year - 1
    years = TARGET_ACADEMIC_START_YEAR - source_academic_start
    if years <= 0:
        return result

    for field in date_fields:
        result[field] = shift_iso_date(result.get(field), years)
    result["date_precision"] = "approximate"
    result["is_date_confirmed"] = False
    result["details"] = join_notes(
        result.get("details"),
        (
            f"Прогноз на {TARGET_ACADEMIC_YEAR}: дата сдвинута на {years} "
            f"{('учебный год' if years == 1 else 'учебных года')} по расписанию "
            f"{source_reference or 'предыдущего сезона'}; организатор её ещё не подтвердил."
        ),
    )
    return result


def dates_from_russian_month(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    lowered = text.casefold().replace("ё", "е")
    years = [int(item) for item in re.findall(r"\b(20\d{2})\b", lowered)]
    if not years:
        return None, None
    found: list[int] = []
    for stem, month in MONTHS.items():
        if re.search(rf"\b{stem}[а-я]*", lowered):
            found.append(month)
    if not found:
        return None, None
    start_month, end_month = min(found), max(found)
    start_year = years[0]
    end_year = years[-1]
    if end_month < start_month and end_year == start_year:
        end_year += 1
    last_day = calendar.monthrange(end_year, end_month)[1]
    return date(start_year, start_month, 1).isoformat(), date(
        end_year, end_month, last_day
    ).isoformat()


def normalize_format(value: Any) -> str:
    text = (clean_text(value) or "").casefold()
    online = "онлайн" in text or "дистанцион" in text
    offline = "очно" in text and "заочно" not in text
    if "гибрид" in text or (online and offline):
        return "hybrid"
    if online:
        return "online"
    if offline:
        return "offline"
    return value if value in {"online", "offline", "hybrid", "unknown"} else "unknown"


def stage_type(name: str) -> str:
    lowered = name.casefold()
    if "регистра" in lowered:
        return "registration"
    if "заключ" in lowered or "финал" in lowered:
        return "final"
    if "отбор" in lowered or "квалифика" in lowered:
        return "qualifying"
    if "муницип" in lowered:
        return "municipal"
    if "регион" in lowered:
        return "regional"
    if "школь" in lowered:
        return "school"
    return "stage"


def normalize_stage(
    raw: dict[str, Any], position: int, fallback_url: str | None
) -> dict[str, Any]:
    name = clean_text(raw.get("name")) or f"Этап {position + 1}"
    normalized_stage_type = clean_text(raw.get("stage_type")) or stage_type(name)
    explicit_key = clean_text(raw.get("key") or raw.get("stage_key"))
    stable_key = slugify(explicit_key or f"{normalized_stage_type}-{name}")[:160]
    starts_on = normalize_date(raw.get("starts_on") or raw.get("start_date"))
    ends_on = normalize_date(raw.get("ends_on") or raw.get("end_date"))
    date_text = clean_text(raw.get("date_text"))
    raw_date_status = (clean_text(raw.get("date_status")) or "").casefold()
    raw_precision = clean_text(raw.get("date_precision")) or "tba"

    if not starts_on and date_text:
        starts_on, inferred_end = dates_from_russian_month(date_text)
        ends_on = ends_on or inferred_end

    previous_year = "2025_26" in raw_date_status or "2025/26" in raw_date_status

    precision_map = {
        "event_window": "range",
        "window": "range",
        "day": "exact",
        "unknown": "tba",
    }
    precision = precision_map.get(raw_precision, raw_precision)
    if precision not in {"exact", "range", "month", "approximate", "tba"}:
        precision = "tba"
    if previous_year:
        precision = "approximate"
    elif not starts_on and not ends_on and precision not in {"month"}:
        precision = "tba"
    elif starts_on and ends_on and starts_on != ends_on and precision == "exact":
        precision = "range"

    confirmed = (
        "official_2026_27" in raw_date_status
        or "official 2026/27" in raw_date_status
        or bool(raw.get("is_date_confirmed"))
    ) and not previous_year
    raw_format = raw.get("format")
    format_note = (
        f"Указанный организатором формат: {raw_format}."
        if raw_format and raw_format not in {"online", "offline", "hybrid", "unknown"}
        else None
    )
    details = join_notes(
        date_text,
        raw.get("details"),
        raw.get("notes"),
        format_note,
        (
            "Исходная дата приведена из официального календаря 2025/26."
            if previous_year
            else None
        ),
    )
    return {
        "key": stable_key,
        "name": name,
        "stage_type": normalized_stage_type,
        "position": position,
        "starts_on": starts_on,
        "ends_on": ends_on,
        "registration_opens_on": normalize_date(raw.get("registration_opens_on")),
        "registration_closes_on": normalize_date(raw.get("registration_closes_on")),
        "date_precision": precision,
        "is_date_confirmed": confirmed,
        "format": normalize_format(raw_format),
        "location": clean_text(raw.get("location")),
        "details": details,
        "source_url": clean_url(raw.get("source_url")) or fallback_url,
    }


def ensure_unique_stage_keys(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Make generated keys unique without tying them to mutable list positions."""
    counts: dict[str, int] = {}
    for stage in stages:
        base = stage["key"]
        counts[base] = counts.get(base, 0) + 1
        if counts[base] > 1:
            suffix = f"-{counts[base]}"
            stage["key"] = f"{base[: 160 - len(suffix)]}{suffix}"
    return stages


def normalize_material_type(value: Any) -> str:
    text = (clean_text(value) or "other").casefold()
    if text in {"tasks", "solutions", "video", "course", "archive", "other"}:
        return text
    if "video" in text or "видео" in text:
        return "video"
    if "course" in text or "prepar" in text or "курс" in text or "подготов" in text:
        return "course"
    if "solution" in text or "решен" in text:
        return "solutions"
    if "task" in text or "задан" in text:
        return "tasks"
    if "archive" in text or "архив" in text:
        return "archive"
    return "other"


def normalize_material(raw: dict[str, Any]) -> dict[str, Any] | None:
    url = clean_url(raw.get("url"))
    if not url:
        return None
    year = raw.get("year")
    try:
        year = int(year) if year else None
    except (TypeError, ValueError):
        year = None
    return {
        "title": clean_text(raw.get("title")) or "Материалы для подготовки",
        "material_type": normalize_material_type(
            raw.get("material_type") or raw.get("type")
        ),
        "year": year,
        "url": url,
        "is_official": bool(raw.get("is_official", True)),
    }


def benefit_type(raw: dict[str, Any]) -> str:
    existing = raw.get("benefit_type")
    if existing in {"bvi", "hundred_points", "grant", "prize", "other"}:
        return existing
    text = " ".join(
        str(raw.get(field, "")) for field in ("kind", "title", "description")
    ).casefold()
    if "приз" in text or "наград" in text:
        return "prize"
    has_bvi = "бви" in text or "без вступительных" in text
    has_hundred = "100 бал" in text
    if has_bvi and not has_hundred:
        return "bvi"
    if has_hundred and not has_bvi:
        return "hundred_points"
    return "other"


def admission_year(raw: dict[str, Any]) -> int | None:
    """Return an admission campaign, never a competition season.

    Reviewed university matrices carry an explicit integer.  The older priority
    snapshot uses labels such as ``прием-2026`` for an actual campaign, while
    values such as ``2025/26`` describe the season in which a diploma or prize
    was awarded.  Parsing every first year made seasonal awards look like
    admission-2025 benefits.
    """

    if isinstance(raw.get("admission_year"), int):
        return raw["admission_year"]
    text = str(raw.get("academic_year") or "")
    if not re.search(r"при[её]м", text, re.IGNORECASE):
        return None
    match = re.search(r"20\d{2}", text)
    return int(match.group()) if match else None


NON_ADMISSION_BENEFIT_KINDS = {
    "award",
    "career",
    "individual_achievement",
    "next_year",
    "qualification",
}


def benefit_flags(raw: dict[str, Any], kind: str) -> tuple[bool, bool]:
    """Return explicit BVI/100-point semantics for a normalized benefit.

    The reviewed sources sometimes encode a mixed right as ``other`` because a
    single university rule grants BVI on one program and 100 points on another.
    Keep that distinction queryable without asking the API to interpret prose.
    Non-admission rows are guarded before text matching so words such as
    ``призер`` or a negative BVI reference cannot create a false right.
    """

    explicit_bvi = raw.get("has_bvi")
    explicit_hundred = raw.get("has_hundred_points")
    for field, value in (
        ("has_bvi", explicit_bvi),
        ("has_hundred_points", explicit_hundred),
    ):
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"{field} должен быть boolean")

    if kind == "bvi":
        if explicit_bvi is False:
            raise ValueError("Льгота benefit_type=bvi не может иметь has_bvi=false")
        return True, bool(explicit_hundred)
    if kind == "hundred_points":
        if explicit_hundred is False:
            raise ValueError(
                "Льгота benefit_type=hundred_points не может иметь "
                "has_hundred_points=false"
            )
        return bool(explicit_bvi), True
    if kind != "other":
        if explicit_bvi or explicit_hundred:
            raise ValueError("Не-приёмная льгота не может иметь BVI/100 flags")
        return False, False
    if (
        raw.get("status") == "none_via_rsosh"
        or raw.get("kind") in NON_ADMISSION_BENEFIT_KINDS
    ):
        if explicit_bvi or explicit_hundred:
            raise ValueError("Справочная не-приёмная запись не может иметь BVI/100 flags")
        return False, False

    text = " ".join(
        str(raw.get(field, ""))
        for field in ("title", "description", "diploma_requirement")
    ).casefold()
    inferred_bvi = "бви" in text or "без вступительн" in text
    inferred_hundred = bool(
        re.search(
            r"(?:100\s*бал|максимальн\w*\s+бал|максимум\s+(?:дви|егэ)|"
            r"наивысш\w*\s+результат)",
            text,
        )
    )
    return (
        explicit_bvi if explicit_bvi is not None else inferred_bvi,
        explicit_hundred if explicit_hundred is not None else inferred_hundred,
    )


def real_university_name(value: Any) -> str | None:
    name = clean_text(value)
    if not name:
        return None
    lowered = name.casefold()
    blocked = ("другие вуз", "вузы рф", "по правилам", "университеты-организаторы")
    return None if any(fragment in lowered for fragment in blocked) else name


def normalize_benefits(raw: dict[str, Any]) -> list[dict[str, Any]]:
    # This is a sourced statement that a competition has no list-based
    # admission right, not a Benefit.  ``normalize_record`` preserves it as a
    # note and source link instead.
    if raw.get("status") == "none_via_rsosh":
        return []

    source_url = clean_url(raw.get("source_url") or raw.get("url"))
    description = clean_text(raw.get("description"))
    kind = benefit_type(raw)
    has_bvi, has_hundred_points = benefit_flags(raw, kind)
    is_next_year_advance = raw.get("kind") == "next_year"
    if is_next_year_advance:
        default_title = "Допуск в финал следующего сезона"
    elif kind == "prize":
        default_title = "Призы и награды"
    else:
        default_title = "Льготы при поступлении"
    title = clean_text(raw.get("title")) or default_title
    base = {
        "benefit_type": kind,
        "title": title,
        "description": description,
        "has_bvi": has_bvi,
        "has_hundred_points": has_hundred_points,
        "diploma_requirement": clean_text(raw.get("diploma_requirement")),
        "ege_subject": clean_text(raw.get("ege_subject")),
        "ege_min_score": raw.get("ege_min_score"),
        "admission_year": admission_year(raw),
        "source_url": source_url,
    }
    if raw.get("university"):
        result = deepcopy(base)
        result["university"] = raw["university"]
        return [result]

    universities = [
        name
        for name in (real_university_name(item) for item in raw.get("universities", []))
        if name
    ]
    if not universities:
        result = deepcopy(base)
        result["university"] = None
        return [result]
    return [
        {
            **deepcopy(base),
            "university": {"slug": slugify(name), "name": name},
        }
        for name in universities
    ]


def normalize_source(
    raw: dict[str, Any], organizer: str | None, source_year: str | None
) -> dict[str, Any] | None:
    url = clean_url(raw.get("url"))
    if not url:
        return None
    return {
        "title": clean_text(raw.get("title")) or "Официальный источник",
        "url": url,
        "publisher": clean_text(raw.get("publisher")) or organizer,
        "source_type": clean_text(raw.get("source_type")) or "official",
        "source_year": normalize_year_label(raw.get("source_year"), source_year),
        "accessed_on": normalize_date(raw.get("accessed_on")) or SNAPSHOT_DATE,
    }


def infer_data_status(raw: dict[str, Any]) -> str:
    current = raw.get("data_status")
    if current in ALLOWED_DATA_STATUSES:
        return current
    text = str(current or "").casefold()
    if (
        "2025_26" in text
        or "last_official" in text
        or raw.get("status") == "last_published"
    ):
        return "previous_year_estimate"
    if "official" in text and "2026_27" in text:
        return "partial" if "pending" in text or "month" in text else "confirmed"
    return "announcement_pending"


def infer_registry_status(raw: dict[str, Any]) -> str:
    value = raw.get("registry_status")
    return value if value in ALLOWED_REGISTRY_STATUSES else "not_listed"


def infer_geography(raw: dict[str, Any]) -> str:
    value = raw.get("geography")
    if value in {"russia", "moscow", "russia_moscow"}:
        return value
    family = str(raw.get("family_name") or raw.get("name") or "").casefold()
    return "moscow" if "московск" in family else "russia"


def normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    family = (
        clean_text(raw.get("family_name")) or clean_text(raw.get("name")) or "Олимпиада"
    )
    profile = title_profile(clean_text(raw.get("profile")) or "Общий профиль")
    name = clean_text(raw.get("name")) or f"{family} — {title_profile(profile)}"
    organizer = clean_text(raw.get("organizer"))
    sources_raw = raw.get("sources") or []
    fallback_url = next(
        (clean_url(item.get("url")) for item in sources_raw if item), None
    )
    website_url = clean_url(raw.get("website_url")) or fallback_url
    if not website_url:
        raise ValueError(f"Нет официального URL: {family} / {profile}")

    data_status = infer_data_status(raw)
    previous_year_reference = normalize_year_label(raw.get("previous_year_reference"))
    if not previous_year_reference and (
        data_status == "previous_year_estimate"
        or infer_registry_status(raw) == "previous_year"
    ):
        previous_year_reference = "2025/26"

    materials = [
        item
        for item in (normalize_material(item) for item in raw.get("materials", []))
        if item
    ]
    raw_benefits = raw.get("benefits", [])
    negative_benefit_references = [
        item for item in raw_benefits if item.get("status") == "none_via_rsosh"
    ]
    benefits = [
        benefit
        for item in raw_benefits
        for benefit in normalize_benefits(item)
        if benefit.get("source_url") or benefit.get("description")
    ]
    source_year = (
        "2026/27" if infer_data_status(raw) in {"confirmed", "partial"} else "2025/26"
    )
    negative_benefit_sources = [
        {
            "title": "Справка об отсутствии перечневой льготы",
            "url": item.get("source_url") or item.get("url"),
            "publisher": organizer,
            "source_type": "benefit_reference",
            "source_year": normalize_year_label(item.get("academic_year"), source_year),
            "accessed_on": SNAPSHOT_DATE,
        }
        for item in negative_benefit_references
    ]
    sources = [
        item
        for item in (
            normalize_source(source, organizer, source_year)
            for source in [*sources_raw, *negative_benefit_sources]
        )
        if item
    ]
    if not sources:
        sources = [
            {
                "title": "Официальная страница олимпиады",
                "url": website_url,
                "publisher": organizer,
                "source_type": "official",
                "source_year": source_year,
                "accessed_on": SNAPSHOT_DATE,
            }
        ]
    stages = ensure_unique_stage_keys(
        [
            normalize_stage(item, position, sources[0]["url"])
            for position, item in enumerate(raw.get("stages", []), start=1)
        ]
    )
    if data_status == "previous_year_estimate":
        stages = [
            project_stage_to_target_year(stage, previous_year_reference)
            for stage in stages
        ]
    grades = sorted(
        {
            int(item)
            for item in (raw.get("grades") or [])
            if str(item).isdigit() and 5 <= int(item) <= 11
        }
    )
    geography_note = (
        clean_text(raw.get("geography"))
        if raw.get("geography") not in {"russia", "moscow", "russia_moscow"}
        else None
    )
    return {
        "slug": slugify(clean_text(raw.get("slug")) or f"{family}-{profile}"),
        "name": name,
        "family_name": family,
        "profile": profile,
        "description": clean_text(raw.get("description")),
        "organizer": organizer,
        "website_url": website_url,
        "logo_url": clean_url(raw.get("logo_url")),
        "geography": infer_geography(raw),
        "is_team": bool(raw.get("is_team", False)),
        "academic_year": TARGET_ACADEMIC_YEAR,
        "cycle_label": clean_text(raw.get("cycle_label")),
        "status": "published",
        "data_status": data_status,
        "is_in_registry": bool(raw.get("is_in_registry", False)),
        "registry_status": infer_registry_status(raw),
        "registry_level": raw.get("registry_level"),
        "is_popular": bool(raw.get("is_popular", False)),
        "registration_status": clean_text(raw.get("registration_status"))
        or "not_found",
        "registration_checked_on": normalize_date(
            raw.get("registration_checked_on")
        ),
        "registration_url": clean_url(raw.get("registration_url")),
        "registration_closes_at": normalize_aware_datetime(
            raw.get("registration_closes_at")
        ),
        "previous_year_reference": previous_year_reference,
        "eligibility_notes": clean_text(raw.get("eligibility_notes")),
        "notes": join_notes(
            raw.get("notes"),
            *(
                clean_text(item.get("description"))
                for item in negative_benefit_references
            ),
            f"География и формат по источнику: {geography_note}."
            if geography_note
            else None,
        ),
        "grades": grades,
        "stages": stages,
        "materials": materials,
        "benefits": benefits,
        "sources": sources,
    }


POPULAR_MARKERS = (
    "высшая проба",
    "ломонос",
    "физтех",
    "покори воробьевы горы",
    "спбгу",
    "иннополис",
    "бельчонок",
    "шаг в будущее",
)


def build_registry_records() -> list[dict[str, Any]]:
    draft = read_json(RESEARCH / "official_registry_2026_27_draft.json")
    approved_path = RESEARCH / "official_registry_2025_26_approved.json"
    approved = read_json(approved_path) if approved_path.exists() else {"olympiads": []}
    approved_urls = {
        normalize_identity(item["name"]): item.get("website_url")
        for item in approved["olympiads"]
        if item.get("website_url")
    }
    result: list[dict[str, Any]] = []
    for family in draft["olympiads"]:
        family_name = clean_text(family["name"])
        website = (
            approved_urls.get(normalize_identity(family_name)) or draft["project_url"]
        )
        for profile in family["profiles"]:
            profile_name = clean_text(profile["profile"])
            marker_text = f"{family_name} {profile_name}".casefold().replace("ё", "е")
            record_slug = (
                f"registry-{family['list_number']}-"
                f"{profile['profile_index']}-{profile_name}"
            )
            raw = {
                "slug": record_slug,
                "name": f"{family_name} — {title_profile(profile_name)}",
                "family_name": family_name,
                "profile": profile_name,
                "description": (
                    f"Профиль «{profile_name}» включён в официальный проект перечня олимпиад "
                    "школьников на 2026/27 учебный год."
                ),
                "organizer": family.get("organizer"),
                "website_url": website,
                "geography": "russia",
                "academic_year": "2026/27",
                "status": "published",
                "data_status": "announcement_pending",
                "is_in_registry": True,
                "registry_status": "draft",
                "registry_level": profile.get("level"),
                "is_popular": any(marker in marker_text for marker in POPULAR_MARKERS),
                "grades": [],
                "notes": (
                    "Это проект, а не вступивший в силу приказ. Классы, даты и правила приёма "
                    "нужно дополнить после публикации организатором и вузами. "
                    f"Соответствующие предметы или УГСН: {profile.get('subjects_or_ugsn')}."
                ),
                "stages": [],
                "materials": [],
                "benefits": [],
                "sources": [
                    {
                        "title": "Проект перечня олимпиад школьников на 2026/27",
                        "url": draft["project_url"],
                        "publisher": "Федеральный портал проектов нормативных правовых актов",
                        "source_type": "draft_regulation",
                        "source_year": "2026/27",
                        "accessed_on": draft.get("as_of") or SNAPSHOT_DATE,
                    }
                ],
            }
            result.append(normalize_record(raw))
    return result


def build_vosh_records() -> list[dict[str, Any]]:
    path = RESEARCH / "official_vosh_2026_27.json"
    if not path.exists():
        return []
    source = read_json(path)
    result: list[dict[str, Any]] = []
    for profile in source["profiles"]:
        profile_name = clean_text(profile["profile"])
        stages = []
        for rule in source["stage_rules"]:
            stages.append(
                {
                    "name": rule["name"],
                    "date_precision": "tba",
                    "is_date_confirmed": False,
                    "format": "unknown",
                    "details": f"Допустимые классы этапа: {rule['grades']}. Точные даты ожидаются.",
                    "source_url": rule["source_url"],
                }
            )
        raw = {
            "slug": f"vsosh-{profile_name}",
            "name": f"ВсОШ — {profile_name}",
            "family_name": "Всероссийская олимпиада школьников",
            "profile": profile_name,
            "description": (
                "Профиль Всероссийской олимпиады школьников с четырьмя этапами: "
                "школьным, муниципальным, региональным и заключительным."
            ),
            "organizer": "Министерство просвещения Российской Федерации",
            "website_url": "https://vserosolimp.edsoo.ru/",
            "geography": "russia",
            "academic_year": "2026/27",
            "status": "published",
            "data_status": "announcement_pending",
            "is_in_registry": False,
            "registry_status": "not_listed",
            "registry_level": None,
            "is_popular": True,
            "grades": profile.get("service_grades") or [],
            "notes": source.get("calendar_status"),
            "stages": stages,
            "materials": [
                {
                    "title": "Архив заданий ВсОШ прошлых лет",
                    "material_type": "archive",
                    "url": source["materials_archive_url"],
                    "is_official": False,
                }
            ],
            "benefits": [
                {
                    "benefit_type": "bvi",
                    "title": "Право на поступление без вступительных испытаний",
                    "description": source["benefit_policy"]["summary"],
                    "diploma_requirement": "Победитель или призёр заключительного этапа",
                    "admission_year": 2027,
                    "source_url": source["benefit_policy"]["source_url"],
                }
            ],
            "sources": [
                {
                    "title": "Официальный портал ВсОШ",
                    "url": "https://vserosolimp.edsoo.ru/",
                    "publisher": "Министерство просвещения Российской Федерации",
                    "source_type": "official",
                    "source_year": "2026/27",
                    "accessed_on": source.get("as_of") or SNAPSHOT_DATE,
                },
                {
                    "title": "Нормативные документы ВсОШ",
                    "url": source["normative_documents_url"],
                    "publisher": "Министерство просвещения Российской Федерации",
                    "source_type": "regulation",
                    "source_year": "2026/27",
                    "accessed_on": source.get("as_of") or SNAPSHOT_DATE,
                },
            ],
        }
        result.append(normalize_record(raw))
    return result


def source_key(source: dict[str, Any]) -> tuple[str, str]:
    return source.get("url", ""), source.get("title", "")


def merge_lists(
    left: list[dict[str, Any]], right: list[dict[str, Any]], key
) -> list[dict[str, Any]]:
    result = deepcopy(left)
    known = {key(item) for item in result}
    for item in right:
        if key(item) not in known:
            result.append(deepcopy(item))
            known.add(key(item))
    return result


def merge_materials(
    existing: list[dict[str, Any]], updates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Upsert reviewed material metadata by URL while preserving list order."""
    result = deepcopy(existing)
    positions = {item["url"]: index for index, item in enumerate(result)}
    for item in updates:
        current = positions.get(item["url"])
        if current is None:
            positions[item["url"]] = len(result)
            result.append(deepcopy(item))
        else:
            result[current] = {**result[current], **deepcopy(item)}
    return result


def record_match_score(base: dict[str, Any], overlay: dict[str, Any]) -> int:
    if base["slug"] == overlay["slug"]:
        return 1_000
    if normalize_profile_identity(base["profile"]) != normalize_profile_identity(
        overlay["profile"]
    ):
        return 0
    left = normalize_identity(base["family_name"])
    right = normalize_identity(overlay["family_name"])
    if left == right:
        return 100
    if {left, right} <= {"dano", "высшая проба"}:
        return 90
    if left and right and (left in right or right in left):
        return 50
    return 0


def record_matches(base: dict[str, Any], overlay: dict[str, Any]) -> bool:
    return record_match_score(base, overlay) > 0


def merge_record(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    registry_rank = {"not_listed": 0, "previous_year": 1, "draft": 2, "approved": 3}
    preserved_registry = (
        base
        if registry_rank[base["registry_status"]]
        >= registry_rank[overlay["registry_status"]]
        else overlay
    )
    for field in (
        "slug",
        "name",
        "family_name",
        "profile",
        "description",
        "organizer",
        "website_url",
        "logo_url",
        "geography",
        "registration_url",
        "registration_closes_at",
        "previous_year_reference",
        "cycle_label",
        "eligibility_notes",
    ):
        if overlay.get(field) not in (None, "", []):
            result[field] = deepcopy(overlay[field])
    result["is_team"] = bool(base["is_team"] or overlay["is_team"])
    result["is_popular"] = bool(base["is_popular"] or overlay["is_popular"])
    result["is_in_registry"] = bool(base["is_in_registry"] or overlay["is_in_registry"])
    result["registry_status"] = preserved_registry["registry_status"]
    result["registry_level"] = preserved_registry.get("registry_level")
    if overlay["data_status"] != "announcement_pending":
        result["data_status"] = overlay["data_status"]
    if overlay["grades"]:
        result["grades"] = overlay["grades"]
    if overlay["stages"]:
        result["stages"] = overlay["stages"]
    result["materials"] = merge_lists(
        base["materials"], overlay["materials"], lambda item: item["url"]
    )
    result["benefits"] = merge_lists(
        base["benefits"],
        overlay["benefits"],
        lambda item: (
            item.get("source_url"),
            (item.get("university") or {}).get("slug"),
            item.get("benefit_type"),
        ),
    )
    result["sources"] = merge_lists(base["sources"], overlay["sources"], source_key)
    result["notes"] = join_notes(base.get("notes"), overlay.get("notes"))
    return result


def merge_records(base_records: list[dict[str, Any]], overlays: list[dict[str, Any]]):
    result = deepcopy(base_records)
    for overlay in overlays:
        candidates = [
            (record_match_score(base, overlay), index)
            for index, base in enumerate(result)
            if record_matches(base, overlay)
        ]
        if not candidates:
            result.append(deepcopy(overlay))
        else:
            _, match_index = max(candidates)
            result[match_index] = merge_record(result[match_index], overlay)
    return result


def apply_material_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for record in result:
        by_family.setdefault(record["family_name"], []).append(record)
        record["materials"] = [
            item
            for item in record["materials"]
            if item["url"] not in DEPRECATED_MATERIAL_URLS
        ]

    enrichment_paths = sorted(
        {
            *RESEARCH.glob("*_materials_enrichment.json"),
            *RESEARCH.glob("materials_*_enrichment.json"),
            *RESEARCH.glob("*_material_recheck.json"),
        }
    )
    for path in enrichment_paths:
        document = read_json(path)
        remove_urls = set(document.get("remove_urls", []))
        if remove_urls:
            for record in result:
                record["materials"] = [
                    item
                    for item in record["materials"]
                    if item["url"] not in remove_urls
                ]

        for slug, raw_materials in document.get("materials_by_slug", {}).items():
            if slug not in by_slug:
                raise ValueError(f"Неизвестный slug в {path.name}: {slug}")
            materials = [
                item
                for item in (normalize_material(raw) for raw in raw_materials)
                if item and item["url"] not in DEPRECATED_MATERIAL_URLS
            ]
            by_slug[slug]["materials"] = merge_materials(
                by_slug[slug]["materials"], materials
            )

        for family, raw_materials in document.get("materials_by_family", {}).items():
            if family not in by_family:
                raise ValueError(f"Неизвестное семейство в {path.name}: {family}")
            materials = [
                item
                for item in (normalize_material(raw) for raw in raw_materials)
                if item and item["url"] not in DEPRECATED_MATERIAL_URLS
            ]
            for record in by_family[family]:
                record["materials"] = merge_materials(record["materials"], materials)

    return result


def apply_structure_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fill reviewed grade/stage gaps without overwriting richer records.

    The checked-in enrichment deliberately distinguishes a current-season
    publication from a previous-season reference.  Dates from the latter are
    projected by :func:`project_stage_to_target_year`, which makes them
    approximate and unconfirmed and adds the provenance warning shown in the
    UI.  Explicit stage keys in the research file remain stable across rebuilds.
    """
    enrichment_paths = [
        path
        for path in (
            STRUCTURE_ENRICHMENT,
            *sorted(RESEARCH.glob(STRUCTURE_ENRICHMENT_GLOB)),
            *(RESEARCH / name for name in STRUCTURE_ENRICHMENT_EXTRAS),
        )
        if path.exists()
    ]
    if not enrichment_paths:
        return deepcopy(records)

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for record in result:
        by_family.setdefault(record["family_name"], []).append(record)

    def apply_entry(
        record: dict[str, Any], entry: dict[str, Any], source_path: Path
    ) -> None:
        changed = False
        organizer = clean_text(entry.get("organizer"))
        if organizer:
            if len(organizer) > 255:
                raise ValueError(
                    f"Слишком длинный organizer в {source_path.name}: "
                    f"{record['slug']}"
                )
            if organizer != record.get("organizer"):
                record["organizer"] = organizer
                changed = True

        website_url = clean_url(entry.get("website_url"))
        if website_url and website_url != record.get("website_url"):
            record["website_url"] = website_url
            changed = True

        eligibility_notes = clean_text(entry.get("eligibility_notes"))
        if eligibility_notes and eligibility_notes != record.get("eligibility_notes"):
            record["eligibility_notes"] = eligibility_notes
            changed = True

        cycle_label = clean_text(entry.get("cycle_label"))
        if cycle_label:
            if len(cycle_label) > 120:
                raise ValueError(
                    f"Слишком длинный cycle_label в {source_path.name}: "
                    f"{record['slug']}"
                )
            if cycle_label != record.get("cycle_label"):
                record["cycle_label"] = cycle_label
                changed = True

        grades = sorted(
            {
                int(item)
                for item in entry.get("grades", [])
                if str(item).isdigit() and 5 <= int(item) <= 11
            }
        )
        if not record["grades"] and grades:
            record["grades"] = grades
            changed = True

        raw_stages = entry.get("stages", [])
        if not record["stages"] and raw_stages:
            fallback_url = next(
                (
                    clean_url(source.get("url"))
                    for source in entry.get("sources", [])
                    if source
                ),
                record.get("website_url"),
            )
            stages = ensure_unique_stage_keys(
                [
                    normalize_stage(raw, position, fallback_url)
                    for position, raw in enumerate(raw_stages, start=1)
                ]
            )
            status = entry.get("data_status")
            previous_reference = normalize_year_label(
                entry.get("previous_year_reference")
            )
            if status == "previous_year_estimate":
                stages = [
                    project_stage_to_target_year(stage, previous_reference)
                    for stage in stages
                ]
            record["stages"] = stages
            changed = True

        if not changed:
            return

        status = entry.get("data_status")
        if status not in ALLOWED_DATA_STATUSES:
            raise ValueError(
                f"Некорректный data_status в {source_path.name}: {status}"
            )
        if DATA_STATUS_RANK[status] > DATA_STATUS_RANK[record["data_status"]]:
            record["data_status"] = status
        previous_reference = normalize_year_label(entry.get("previous_year_reference"))
        if (
            record["data_status"] == "previous_year_estimate"
            and status == record["data_status"]
        ):
            record["previous_year_reference"] = previous_reference or "2025/26"
        record["notes"] = join_notes(record.get("notes"), entry.get("notes"))

        source_year = (
            record["previous_year_reference"]
            if status == "previous_year_estimate"
            else TARGET_ACADEMIC_YEAR
        )
        sources = [
            source
            for source in (
                normalize_source(raw, record.get("organizer"), source_year)
                for raw in entry.get("sources", [])
            )
            if source
        ]
        record["sources"] = merge_lists(record["sources"], sources, source_key)

    seen_family_fields: dict[str, dict[str, str]] = {}
    seen_slug_fields: dict[str, dict[str, str]] = {}
    for path in enrichment_paths:
        document = read_json(path)
        if document.get("target_academic_year") != TARGET_ACADEMIC_YEAR:
            raise ValueError(
                f"{path.name}: ожидался учебный год {TARGET_ACADEMIC_YEAR}"
            )
        family_entries = document.get("families", [])
        slug_entries = document.get("slugs", [])
        family_names = [clean_text(entry.get("family_name")) for entry in family_entries]
        slugs = [clean_text(entry.get("slug")) for entry in slug_entries]
        if len(family_names) != len(set(family_names)):
            raise ValueError(f"Повторяющиеся family_name в {path.name}")
        if len(slugs) != len(set(slugs)):
            raise ValueError(f"Повторяющиеся slug в {path.name}")

        def remember_fields(
            target: str,
            entry: dict[str, Any],
            seen: dict[str, dict[str, str]],
            label: str,
            source_name: str,
        ) -> None:
            fields = {
                field
                for field in ("grades", "stages", "cycle_label")
                if entry.get(field)
            }
            previous = seen.setdefault(target, {})
            for field in fields:
                previous_path = previous.get(field)
                if previous_path:
                    raise ValueError(
                        f"{label} {target}: поле {field} повторяется в "
                        f"{previous_path} и {source_name}"
                    )
                previous[field] = source_name

        for entry, family_name in zip(family_entries, family_names, strict=True):
            remember_fields(
                family_name, entry, seen_family_fields, "Семейство", path.name
            )
        for entry, slug in zip(slug_entries, slugs, strict=True):
            remember_fields(slug, entry, seen_slug_fields, "Slug", path.name)

        for entry in family_entries:
            family_name = clean_text(entry.get("family_name"))
            if not family_name or family_name not in by_family:
                raise ValueError(
                    f"Неизвестное семейство в {path.name}: {family_name}"
                )
            for record in by_family[family_name]:
                apply_entry(record, entry, path)

        for entry in slug_entries:
            slug = clean_text(entry.get("slug"))
            if not slug or slug not in by_slug:
                raise ValueError(f"Неизвестный slug в {path.name}: {slug}")
            apply_entry(by_slug[slug], entry, path)

    for record in result:
        reconcile_draft_gap_note(record)

    return result


def apply_current_date_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Overlay newly published 2026/27 dates onto existing stable stage keys."""

    paths = sorted(RESEARCH.glob(CURRENT_DATES_ENRICHMENT_GLOB))
    if not paths:
        return deepcopy(records)

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for record in result:
        by_family.setdefault(record["family_name"], []).append(record)
    seen: dict[tuple[str, str], str] = {}
    date_fields = (
        "starts_on",
        "ends_on",
        "registration_opens_on",
        "registration_closes_on",
    )

    for path in paths:
        document = read_json(path)
        if document.get("target_academic_year") != TARGET_ACADEMIC_YEAR:
            raise ValueError(
                f"{path.name}: ожидался учебный год {TARGET_ACADEMIC_YEAR}"
            )
        checked_on = normalize_date(document.get("checked_on")) or SNAPSHOT_DATE
        entries = list(document.get("slugs", []))
        for family_entry in document.get("families", []):
            family_name = clean_text(family_entry.get("family_name"))
            if not family_name or family_name not in by_family:
                raise ValueError(
                    f"Неизвестное семейство в {path.name}: {family_name}"
                )
            entries.extend(
                {**family_entry, "slug": record["slug"]}
                for record in by_family[family_name]
            )

        for entry in entries:
            slug = clean_text(entry.get("slug"))
            if not slug or slug not in by_slug:
                raise ValueError(f"Неизвестный slug в {path.name}: {slug}")
            record = by_slug[slug]
            stages_by_key = {stage["key"]: stage for stage in record["stages"]}
            updated = False
            for raw in entry.get("stages", []):
                key = clean_text(raw.get("key"))
                if not key or key not in stages_by_key:
                    raise ValueError(
                        f"Неизвестный stage key в {path.name}: {slug} / {key}"
                    )
                target = (slug, key)
                if target in seen:
                    raise ValueError(
                        f"Дата этапа {slug} / {key} повторяется в "
                        f"{seen[target]} и {path.name}"
                    )
                seen[target] = path.name

                stage = stages_by_key[key]
                source_url = clean_url(raw.get("source_url"))
                if not source_url:
                    raise ValueError(
                        f"У текущей даты нет официального источника: {slug} / {key}"
                    )
                is_date_confirmed = raw.get("is_date_confirmed")
                if not isinstance(is_date_confirmed, bool):
                    raise ValueError(
                        f"У current-date enrichment нет признака подтверждения: "
                        f"{slug} / {key}"
                    )

                parsed_dates: dict[str, str | None] = {}
                for field in date_fields:
                    value = raw.get(field)
                    parsed = normalize_date(value)
                    if value is not None and parsed is None:
                        raise ValueError(
                            f"Некорректная дата {field} в {path.name}: "
                            f"{slug} / {key}"
                        )
                    if value is not None:
                        parsed_dates[field] = parsed
                if not parsed_dates.get("starts_on") and not parsed_dates.get("ends_on"):
                    raise ValueError(
                        f"У current-date этапа нет даты: {slug} / {key}"
                    )

                if stage.get("is_date_confirmed"):
                    conflicting = [
                        field
                        for field, value in parsed_dates.items()
                        if stage.get(field) not in {None, value}
                    ]
                    if conflicting:
                        raise ValueError(
                            f"Конфликт подтверждённой даты {slug} / {key}: "
                            + ", ".join(conflicting)
                        )

                stage.update(parsed_dates)
                precision = clean_text(raw.get("date_precision")) or (
                    "range"
                    if stage.get("starts_on") != stage.get("ends_on")
                    else "exact"
                )
                if precision not in {"exact", "range", "month"}:
                    raise ValueError(
                        f"Некорректная точность текущей даты: {slug} / {key}"
                    )
                if (
                    stage.get("starts_on")
                    and stage.get("ends_on")
                    and stage["starts_on"] != stage["ends_on"]
                    and precision == "exact"
                ):
                    precision = "range"
                stage["date_precision"] = precision
                stage["is_date_confirmed"] = is_date_confirmed
                stage["source_url"] = source_url
                replace_details = raw.get(
                    "replace_details",
                    entry.get(
                        "replace_stage_details",
                        document.get("replace_stage_details", False),
                    ),
                )
                stage["details"] = (
                    clean_text(raw.get("details"))
                    if replace_details
                    else join_notes(stage.get("details"), raw.get("details"))
                )
                updated = True
                schedule_year = (
                    normalize_year_label(record.get("cycle_label"))
                    or TARGET_ACADEMIC_YEAR
                )

                record["sources"] = merge_lists(
                    record["sources"],
                    [
                        {
                            "title": clean_text(raw.get("source_title"))
                            or f"Расписание {schedule_year}: {stage['name']}",
                            "url": source_url,
                            "publisher": record.get("organizer"),
                            "source_type": "official_schedule",
                            "source_year": schedule_year,
                            "accessed_on": checked_on,
                        }
                    ],
                    source_key,
                )

            if updated:
                remove_note_fragments = [
                    *document.get("remove_note_fragments", []),
                    *entry.get("remove_note_fragments", []),
                ]
                for fragment in remove_note_fragments:
                    normalized_fragment = clean_text(fragment)
                    if normalized_fragment and record.get("notes"):
                        record["notes"] = clean_text(
                            record["notes"].replace(normalized_fragment, "")
                        )
                all_confirmed = all(
                    stage.get("starts_on") and stage.get("is_date_confirmed")
                    for stage in record["stages"]
                )
                record["data_status"] = "confirmed" if all_confirmed else "partial"
                schedule_year = (
                    normalize_year_label(record.get("cycle_label"))
                    or TARGET_ACADEMIC_YEAR
                )
                schedule_label = (
                    f"календарного цикла {schedule_year}"
                    if record.get("cycle_label")
                    else TARGET_ACADEMIC_YEAR
                )
                record["notes"] = join_notes(
                    record.get("notes"),
                    f"Опубликованные даты {schedule_label} проверены "
                    "на сайте организатора.",
                )

    for record in result:
        all_confirmed = bool(record["stages"]) and all(
            stage.get("starts_on") and stage.get("is_date_confirmed")
            for stage in record["stages"]
        )
        if all_confirmed and record.get("notes"):
            schedule_year = (
                normalize_year_label(record.get("cycle_label"))
                or TARGET_ACADEMIC_YEAR
            )
            schedule_label = (
                f"календарного цикла {schedule_year}"
                if record.get("cycle_label")
                else TARGET_ACADEMIC_YEAR
            )
            record["notes"] = clean_text(
                record["notes"].replace(
                    DRAFT_VERIFIED_STRUCTURE_PENDING_DATES_SENTENCE,
                    f"Классы, структура этапов и расписание {schedule_label} "
                    "проверены по опубликованным материалам организатора.",
                )
            )

    return result


def apply_current_registration_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply reviewed 2026/27 registration links without guessing future forms."""

    paths = sorted(RESEARCH.glob(CURRENT_REGISTRATION_ENRICHMENT_GLOB))
    if not paths:
        return deepcopy(records)

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    seen: dict[str, str] = {}

    for path in paths:
        document = read_json(path)
        if document.get("target_academic_year") != TARGET_ACADEMIC_YEAR:
            raise ValueError(
                f"{path.name}: ожидался учебный год {TARGET_ACADEMIC_YEAR}"
            )
        document_checked_on = normalize_date(document.get("checked_on"))
        if not document_checked_on:
            raise ValueError(f"{path.name}: отсутствует корректная дата проверки")

        entries = document.get("slugs", [])
        if not isinstance(entries, list):
            raise TypeError(f"{path.name}: slugs должен быть массивом")
        for entry in entries:
            checked_on = normalize_date(entry.get("checked_on")) or document_checked_on
            slug = clean_text(entry.get("slug"))
            if not slug or slug not in by_slug:
                raise ValueError(f"Неизвестный slug в {path.name}: {slug}")
            if slug in seen:
                raise ValueError(
                    f"Регистрация {slug} повторяется в {seen[slug]} и {path.name}"
                )
            seen[slug] = path.name

            status = clean_text(entry.get("registration_status"))
            if status not in ALLOWED_REGISTRATION_STATUSES:
                raise ValueError(
                    f"Некорректный registration_status в {path.name}: {slug} / {status}"
                )
            registration_url = clean_url(entry.get("registration_url"))
            raw_registration_closes_at = entry.get("registration_closes_at")
            registration_closes_at = normalize_aware_datetime(
                raw_registration_closes_at
            )
            source_url = clean_url(entry.get("source_url"))
            evidence = clean_text(entry.get("evidence"))
            if not source_url or not evidence:
                raise ValueError(
                    f"Нет источника или обоснования регистрации в {path.name}: {slug}"
                )
            if status in {"open", "announced"} and not registration_url:
                raise ValueError(
                    f"Для опубликованной регистрации нет URL в {path.name}: {slug}"
                )
            if status in {"not_open", "not_found"} and registration_url:
                raise ValueError(
                    f"У неопубликованной регистрации задан URL в {path.name}: {slug}"
                )
            if raw_registration_closes_at not in (None, "") and not registration_closes_at:
                raise ValueError(
                    "registration_closes_at должен быть timezone-aware ISO "
                    f"datetime в {path.name}: {slug}"
                )
            if status != "open" and registration_closes_at:
                raise ValueError(
                    "registration_closes_at допустим только для open в "
                    f"{path.name}: {slug}"
                )
            record = by_slug[slug]
            record["registration_status"] = status
            record["registration_checked_on"] = checked_on
            record["registration_url"] = None
            record["registration_closes_at"] = None
            record["sources"] = merge_lists(
                record["sources"],
                [
                    {
                        "title": f"Проверка регистрации {TARGET_ACADEMIC_YEAR}",
                        "url": source_url,
                        "publisher": record.get("organizer"),
                        "source_type": "registration",
                        "source_year": TARGET_ACADEMIC_YEAR,
                        "accessed_on": checked_on,
                    }
                ],
                source_key,
            )
            if status != "open":
                continue

            record["registration_url"] = registration_url
            record["registration_closes_at"] = registration_closes_at
            notes = (clean_text(record.get("notes")) or "").replace(
                UNCONFIRMED_REGISTRATION_NOTE,
                f"регистрация {TARGET_ACADEMIC_YEAR} подтверждена "
                f"по источнику организатора на {checked_on}."
            )
            record["notes"] = clean_text(notes)

    unreviewed = sorted(record["slug"] for record in result if record["slug"] not in seen)
    if unreviewed:
        raise ValueError(
            "Статус регистрации не проверен для карточек: " + ", ".join(unreviewed)
        )

    return result


def apply_profile_metadata_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply small, sourced card-level metadata corrections.

    This pass is intentionally limited to fields that do not alter the legal
    registry identity or schedule.  It lets a family-level seed point to the
    exact organizer page and explain age eligibility without hard-coding
    profile-specific facts in application code.
    """

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    seen: set[str] = set()

    for path in PROFILE_METADATA_ENRICHMENT_PATHS:
        if not path.exists():
            continue
        document = read_json(path)
        target_year = document.get("target_academic_year")
        if target_year not in (None, TARGET_ACADEMIC_YEAR):
            raise ValueError(
                f"{path.name}: ожидался учебный год {TARGET_ACADEMIC_YEAR}"
            )
        entries = document.get("records")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{path.name}: records должен быть непустым массивом")

        for entry in entries:
            slug = clean_text(entry.get("slug"))
            if not slug or slug not in by_slug:
                raise ValueError(f"{path.name}: неизвестный slug {slug}")
            if slug in seen:
                raise ValueError(f"{path.name}: повторяющийся slug {slug}")
            seen.add(slug)

            website_url = clean_url(entry.get("website_url"))
            eligibility_notes = clean_text(entry.get("eligibility_notes"))
            source_url = clean_url(entry.get("source_url") or website_url)
            if not website_url or not eligibility_notes or not source_url:
                raise ValueError(
                    f"{path.name}: для {slug} нужны website_url, "
                    "eligibility_notes и source_url"
                )

            record = by_slug[slug]
            record["website_url"] = website_url
            record["eligibility_notes"] = eligibility_notes
            record["sources"] = merge_lists(
                record["sources"],
                [
                    {
                        "title": "Официальная страница профиля и условия участия",
                        "url": source_url,
                        "publisher": record.get("organizer"),
                        "source_type": "official_profile",
                        "source_year": TARGET_ACADEMIC_YEAR,
                        "accessed_on": SNAPSHOT_DATE,
                    }
                ],
                source_key,
            )

    return result


def benefit_identity(item: dict[str, Any]) -> tuple[Any, ...]:
    """Identity used to replace a less precise benefit with reviewed data."""

    return (
        (item.get("university") or {}).get("slug"),
        item.get("admission_year"),
        item.get("benefit_type"),
        item.get("ege_subject"),
    )


def apply_university_benefit_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply reviewed university rules without projecting them to admission 2027.

    The catalog describes the 2026/27 competition season, while local admission
    rules for its graduates (the 2027 campaign) are not published yet.  The
    enrichment therefore carries the last fully published admission cycle as an
    explicitly labelled reference and never infers BVI merely from registry level.
    """

    if not UNIVERSITY_BENEFITS_ENRICHMENT.exists():
        return deepcopy(records)

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for record in result:
        by_family.setdefault(record["family_name"], []).append(record)

    document = read_json(UNIVERSITY_BENEFITS_ENRICHMENT)
    if document.get("target_catalog_year") != TARGET_ACADEMIC_YEAR:
        raise ValueError(
            f"{UNIVERSITY_BENEFITS_ENRICHMENT.name}: ожидался учебный год "
            f"{TARGET_ACADEMIC_YEAR}"
        )
    admission_cycle = document.get("admission_cycle")
    if admission_cycle != 2026:
        raise ValueError(
            f"{UNIVERSITY_BENEFITS_ENRICHMENT.name}: поддерживается только "
            "проверенный цикл приёма-2026"
        )

    universities = document.get("universities", {})
    seen_targets: set[tuple[str, tuple[Any, ...]]] = set()
    noted_records: set[str] = set()
    record_note = clean_text(document.get("record_note"))

    def reviewed_benefit(raw: dict[str, Any]) -> dict[str, Any]:
        university_ref = clean_text(raw.get("university_ref"))
        if not university_ref or university_ref not in universities:
            raise ValueError(
                f"Неизвестный university_ref в {UNIVERSITY_BENEFITS_ENRICHMENT.name}: "
                f"{university_ref}"
            )
        payload = deepcopy(raw)
        payload.pop("university_ref", None)
        payload["university"] = deepcopy(universities[university_ref])
        normalized = normalize_benefits(payload)
        if len(normalized) != 1:
            raise ValueError("Ожидалась ровно одна вузовская льгота")
        benefit = normalized[0]
        if benefit["admission_year"] != admission_cycle:
            raise ValueError(
                f"Льгота {university_ref} должна иметь admission_year={admission_cycle}"
            )
        if not benefit.get("source_url") or not benefit.get("description"):
            raise ValueError(
                "У проверенной вузовской льготы обязательны источник и описание"
            )
        return benefit

    def apply_to(record: dict[str, Any], benefit: dict[str, Any]) -> None:
        identity = benefit_identity(benefit)
        target = (record["slug"], identity)
        if target in seen_targets:
            raise ValueError(
                f"Повторяющаяся льгота в {UNIVERSITY_BENEFITS_ENRICHMENT.name}: "
                f"{record['slug']} / {identity}"
            )
        seen_targets.add(target)
        positions = {
            benefit_identity(existing): index
            for index, existing in enumerate(record["benefits"])
        }
        current = positions.get(identity)
        if current is None:
            record["benefits"].append(deepcopy(benefit))
        else:
            record["benefits"][current] = deepcopy(benefit)
        if record["slug"] not in noted_records:
            record["notes"] = join_notes(record.get("notes"), record_note)
            noted_records.add(record["slug"])

    for rule in document.get("family_rules", []):
        family_name = clean_text(rule.get("family_name"))
        if not family_name or family_name not in by_family:
            raise ValueError(
                f"Неизвестное семейство в {UNIVERSITY_BENEFITS_ENRICHMENT.name}: "
                f"{family_name}"
            )
        requested_profiles = {
            clean_text(profile)
            for profile in rule.get("profiles", [])
            if clean_text(profile)
        }
        available = {record["profile"] for record in by_family[family_name]}
        missing = sorted(requested_profiles - available)
        if missing:
            raise ValueError(f"Неизвестные профили {family_name}: {', '.join(missing)}")
        benefit = reviewed_benefit(rule["benefit"])
        for record in by_family[family_name]:
            if record["profile"] in requested_profiles:
                apply_to(record, benefit)

    for rule in document.get("slug_rules", []):
        slugs = [clean_text(slug) for slug in rule.get("slugs", [])]
        unknown = sorted(slug for slug in slugs if slug not in by_slug)
        if unknown:
            raise ValueError(
                f"Неизвестные slug в {UNIVERSITY_BENEFITS_ENRICHMENT.name}: "
                f"{', '.join(unknown)}"
            )
        benefit = reviewed_benefit(rule["benefit"])
        for slug in slugs:
            apply_to(by_slug[slug], benefit)

    return result


def apply_entry_university_benefit_enrichments(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply reviewed per-card benefit matrices from focused research passes.

    These documents intentionally keep at most one row for a catalog card and
    university.  If admission rights vary by programme, the row describes the
    variants as ``other`` instead of presenting one of them as universal BVI.
    """

    paths = sorted(
        {
            path
            for pattern in ADDITIONAL_UNIVERSITY_BENEFITS_GLOBS
            for path in RESEARCH.glob(pattern)
        }
    )
    if not paths:
        return deepcopy(records)

    result = deepcopy(records)
    by_slug = {record["slug"]: record for record in result}
    seen_targets: set[tuple[str, str]] = set()

    for path in paths:
        document = read_json(path)
        is_level_one_gap = path.match("level1_benefits_gap_*_2026.json") is not None
        if document.get("target_catalog_year") != TARGET_ACADEMIC_YEAR:
            raise ValueError(
                f"{path.name}: ожидался учебный год {TARGET_ACADEMIC_YEAR}"
            )
        admission_cycle = document.get("admission_cycle", document.get("admission_year"))
        if admission_cycle != 2026:
            raise ValueError(
                f"{path.name}: поддерживается только проверенный цикл приёма-2026"
            )
        universities = document.get("universities")
        if not isinstance(universities, dict) or not universities:
            raise ValueError(f"{path.name}: не задан справочник вузов")
        record_note = clean_text(document.get("record_note"))
        noted_records: set[str] = set()

        for entry in document.get("entries", []):
            slug = clean_text(entry.get("slug"))
            if not slug or slug not in by_slug:
                raise ValueError(f"{path.name}: неизвестный slug {slug}")
            record = by_slug[slug]
            profile = clean_text(entry.get("profile"))
            if profile and profile != record["profile"]:
                raise ValueError(
                    f"{path.name}: профиль {profile} не совпадает с {record['profile']} "
                    f"для {slug}"
                )

            raw_benefits = (
                [entry["benefit"]]
                if entry.get("benefit")
                else entry.get("benefits", [])
            )
            if is_level_one_gap:
                review_status = clean_text(entry.get("review_status")) or (
                    "confirmed" if raw_benefits else "reviewed_no_match"
                )
                if review_status not in {"confirmed", "reviewed_no_match"}:
                    raise ValueError(
                        f"{path.name}: неизвестный review_status {review_status} для {slug}"
                    )
                if review_status == "confirmed" and not raw_benefits:
                    raise ValueError(
                        f"{path.name}: подтверждённая карточка {slug} не содержит льгот"
                    )
                if review_status == "reviewed_no_match":
                    if raw_benefits:
                        raise ValueError(
                            f"{path.name}: reviewed_no_match {slug} содержит льготы"
                        )
                    if not entry.get("unresolved"):
                        raise ValueError(
                            f"{path.name}: для reviewed_no_match {slug} нужны детали проверки"
                        )
                    record["notes"] = join_notes(
                        record.get("notes"), REVIEWED_NO_MATCH_NOTE
                    )
                    continue
            for raw in raw_benefits:
                raw_benefit = deepcopy(raw)
                university_ref = clean_text(raw_benefit.pop("university_ref", None))
                if not university_ref or university_ref not in universities:
                    raise ValueError(
                        f"{path.name}: неизвестный university_ref {university_ref}"
                    )
                raw_benefit["university"] = deepcopy(universities[university_ref])
                subjects = [
                    clean_text(subject)
                    for subject in raw_benefit.pop("ege_subjects", [])
                    if clean_text(subject)
                ]
                if subjects and not raw_benefit.get("ege_subject"):
                    raw_benefit["ege_subject"] = " / ".join(subjects)
                if not isinstance(raw_benefit.get("ege_min_score"), int):
                    raw_benefit["ege_min_score"] = None
                normalized = normalize_benefits(raw_benefit)
                if len(normalized) != 1:
                    raise ValueError(f"{path.name}: ожидалась ровно одна льгота")
                benefit = normalized[0]
                if benefit["admission_year"] != admission_cycle:
                    raise ValueError(
                        f"{path.name}: льгота {slug}/{university_ref} должна иметь "
                        f"admission_year={admission_cycle}"
                    )
                if not benefit.get("source_url") or not benefit.get("description"):
                    raise ValueError(
                        f"{path.name}: у {slug}/{university_ref} нужны источник и описание"
                    )

                university_slug = benefit["university"].get("slug")
                target = (slug, university_slug)
                if not university_slug or target in seen_targets:
                    raise ValueError(
                        f"{path.name}: повторяющаяся связь карточки и вуза {target}"
                    )
                seen_targets.add(target)
                positions = [
                    index
                    for index, existing in enumerate(record["benefits"])
                    if (existing.get("university") or {}).get("slug")
                    == university_slug
                ]
                if len(positions) > 1:
                    raise ValueError(
                        f"{path.name}: в каталоге уже несколько льгот "
                        f"{slug}/{university_slug}"
                    )
                if positions:
                    record["benefits"][positions[0]] = deepcopy(benefit)
                else:
                    record["benefits"].append(deepcopy(benefit))
                if slug not in noted_records:
                    record["notes"] = join_notes(record.get("notes"), record_note)
                    noted_records.add(slug)

    return result


def expand_mosh_directions(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Split service-level МОШ directions that share one registry profile.

    The federal registry has one row for profiles such as mathematics or
    robotics, while the official Moscow site publishes separate competitions
    for age groups or tracks.  The product identity is the latter: every
    official terminal page must remain independently selectable, but it keeps
    the level and draft status of its shared registry profile.
    """

    snapshot = read_json(RESEARCH / "official_mosh_asof_2026_08_25.json")
    family_name = clean_text(snapshot.get("family_name"))
    if not family_name:
        raise ValueError("В срезе МОШ не указано семейство")

    directions_by_registry_profile: dict[str, list[dict[str, Any]]] = {}
    for direction in snapshot.get("profiles", []):
        registry_profile = clean_text(direction.get("registry_profile"))
        if not registry_profile:
            continue
        key = normalize_profile_identity(registry_profile)
        directions_by_registry_profile.setdefault(key, []).append(direction)

    split_groups = {
        key: directions
        for key, directions in directions_by_registry_profile.items()
        if len(directions) > 1
    }
    if not split_groups:
        raise ValueError("В срезе МОШ не найдены составные профили")

    result: list[dict[str, Any]] = []
    expanded_groups: set[str] = set()
    for record in records:
        key = normalize_profile_identity(record["profile"])
        if record["family_name"] != family_name or key not in split_groups:
            result.append(deepcopy(record))
            continue
        if key in expanded_groups:
            raise ValueError(
                f"Несколько базовых карточек МОШ соответствуют профилю {record['profile']}"
            )

        directions = split_groups[key]
        for direction in directions:
            expected_level = direction.get("draft_level_2026_27")
            expected_status = direction.get("registry_status_2026_27")
            if record.get("registry_level") != expected_level:
                raise ValueError(
                    f"Уровень МОШ не совпадает для {direction['display_profile']}"
                )
            if record.get("registry_status") != expected_status:
                raise ValueError(
                    f"Статус перечня МОШ не совпадает для {direction['display_profile']}"
                )

            display_profile = clean_text(direction.get("display_profile"))
            site_code = clean_text(direction.get("site_code"))
            website_url = clean_url(direction.get("website_url"))
            materials_url = clean_url(direction.get("materials_url"))
            if not all((display_profile, site_code, website_url, materials_url)):
                raise ValueError("В срезе МОШ неполное описание направления")

            split_record = deepcopy(record)
            split_record.update(
                {
                    "slug": f"mosh-2026-27-{site_code}",
                    "name": f"{family_name} — {display_profile}",
                    "profile": display_profile,
                    "description": (
                        f"Направление МОШ «{display_profile}». В проекте федерального "
                        f"перечня 2026/27 относится к общему профилю "
                        f"«{direction['registry_profile']}»."
                    ),
                    "website_url": website_url,
                    "grades": sorted(
                        int(grade)
                        for grade in direction.get("grades_estimate_2026_27", [])
                        if 5 <= int(grade) <= 11
                    ),
                    "materials": [
                        {
                            "title": f"Архив заданий МОШ: {display_profile}",
                            "material_type": "archive",
                            "year": None,
                            "url": materials_url,
                            "is_official": True,
                        }
                    ],
                    "notes": join_notes(
                        record.get("notes"),
                        (
                            f"Направление имеет отдельную карточку официального сайта, "
                            f"но использует уровень общего профиля "
                            f"«{direction['registry_profile']}» проекта перечня."
                        ),
                    ),
                }
            )
            split_record["sources"] = merge_lists(
                split_record["sources"],
                [
                    {
                        "title": f"Официальная страница МОШ: {display_profile}",
                        "url": website_url,
                        "publisher": "Городской оргкомитет МОШ",
                        "source_type": "official_profile",
                        "source_year": TARGET_ACADEMIC_YEAR,
                        "accessed_on": normalize_date(snapshot.get("as_of"))
                        or SNAPSHOT_DATE,
                    }
                ],
                source_key,
            )
            result.append(split_record)
        expanded_groups.add(key)

    missing_groups = sorted(set(split_groups) - expanded_groups)
    if missing_groups:
        raise ValueError(
            "Не найдены базовые карточки составных профилей МОШ: "
            + ", ".join(missing_groups)
        )
    return result


def load_base_records() -> list[dict[str, Any]]:
    prepared = RESEARCH / "official_seed_catalog.json"
    if prepared.exists():
        document = read_json(prepared)
        raw_records = deepcopy(document["records"])
        draft_path = RESEARCH / "official_registry_2026_27_draft.json"
        if draft_path.exists():
            draft = read_json(draft_path)
            organizers_by_family = {
                clean_text(family["name"]): official_organizer_display(family)
                for family in draft["olympiads"]
            }
            for record in raw_records:
                if clean_text(record.get("organizer")) != ORGANIZER_PLACEHOLDER:
                    continue
                family_name = clean_text(record.get("family_name"))
                organizer = organizers_by_family.get(family_name)
                if not organizer:
                    raise ValueError(
                        f"Не найден организатор проекта для {family_name}"
                    )
                record["organizer"] = organizer
        return [normalize_record(item) for item in raw_records]
    return build_registry_records() + build_vosh_records()


def assert_catalog(records: list[dict[str, Any]]) -> None:
    slugs = [item["slug"] for item in records]
    duplicate_slugs = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    if duplicate_slugs:
        raise ValueError(f"Повторяющиеся slug: {', '.join(duplicate_slugs[:10])}")
    for record in records:
        if record["data_status"] not in ALLOWED_DATA_STATUSES:
            raise ValueError(f"Некорректный data_status у {record['slug']}")
        if record["registry_status"] not in ALLOWED_REGISTRY_STATUSES:
            raise ValueError(f"Некорректный registry_status у {record['slug']}")
        if record.get("registration_status") not in ALLOWED_REGISTRATION_STATUSES:
            raise ValueError(f"Некорректный registration_status у {record['slug']}")
        if not normalize_date(record.get("registration_checked_on")):
            raise ValueError(f"Нет даты проверки регистрации у {record['slug']}")
        if record["registration_status"] == "open":
            if not record.get("registration_url"):
                raise ValueError(f"Открытая регистрация без URL у {record['slug']}")
        elif record.get("registration_url"):
            raise ValueError(
                f"URL регистрации задан для статуса {record['registration_status']} "
                f"у {record['slug']}"
            )
        if record.get("cycle_label") and len(record["cycle_label"]) > 120:
            raise ValueError(f"Слишком длинный cycle_label у {record['slug']}")
        if record.get("registration_closes_at"):
            if not record.get("registration_url"):
                raise ValueError(
                    f"Дедлайн регистрации без URL у {record['slug']}"
                )
            if not normalize_aware_datetime(record["registration_closes_at"]):
                raise ValueError(
                    f"Некорректный registration_closes_at у {record['slug']}"
                )
        if not record["sources"]:
            raise ValueError(f"Нет источников у {record['slug']}")
        stage_keys = [stage["key"] for stage in record["stages"]]
        if len(stage_keys) != len(set(stage_keys)):
            raise ValueError(f"Повторяющиеся key этапов у {record['slug']}")
        university_slugs = [
            benefit["university"]["slug"]
            for benefit in record["benefits"]
            if benefit.get("university")
        ]
        if len(university_slugs) != len(set(university_slugs)):
            raise ValueError(f"Повторяющиеся льготы вузов у {record['slug']}")
        for benefit in record["benefits"]:
            if not isinstance(benefit.get("has_bvi"), bool) or not isinstance(
                benefit.get("has_hundred_points"), bool
            ):
                raise TypeError(f"Нет явных флагов льготы у {record['slug']}")
            if benefit["benefit_type"] == "bvi" and not benefit["has_bvi"]:
                raise ValueError(f"BVI без has_bvi у {record['slug']}")
            if (
                benefit["benefit_type"] == "hundred_points"
                and not benefit["has_hundred_points"]
            ):
                raise ValueError(f"100 баллов без флага у {record['slug']}")


def main() -> None:
    records = load_base_records()
    priority_path = RESEARCH / "priority_competitions.json"
    if priority_path.exists():
        priority = read_json(priority_path)
        records = merge_records(
            records, [normalize_record(item) for item in priority["records"]]
        )
    for extra_path in EXTRA_COMPETITION_PATHS:
        if not extra_path.exists():
            continue
        document = read_json(extra_path)
        raw_records = document.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise ValueError(f"{extra_path.name}: records должен быть непустым массивом")
        records = merge_records(
            records, [normalize_record(item) for item in raw_records]
        )
    records = apply_material_enrichments(records)
    records = expand_mosh_directions(records)
    records = apply_structure_enrichments(records)
    records = apply_profile_metadata_enrichments(records)
    records = apply_current_date_enrichments(records)
    records = apply_current_registration_enrichments(records)
    records = apply_university_benefit_enrichments(records)
    records = apply_entry_university_benefit_enrichments(records)
    records.sort(
        key=lambda item: (item["family_name"].casefold(), item["profile"].casefold())
    )
    assert_catalog(records)
    document = {
        "academic_year": TARGET_ACADEMIC_YEAR,
        "generated_from_snapshot": SNAPSHOT_DATE,
        "records_count": len(records),
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(records)} records to {OUTPUT}")


if __name__ == "__main__":
    main()
