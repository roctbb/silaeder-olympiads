from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

VR_PROFILE = (
    "Виртуальная реальность: разработка компьютерных игр, технологии "
    "виртуальной реальности, технологии дополненной реальности"
)


@dataclass(frozen=True, slots=True)
class Direction:
    slug: str
    name: str

    def as_dict(self) -> dict[str, str]:
        return {"slug": self.slug, "name": self.name}


# This taxonomy is deliberately independent from the database. ``profile`` remains
# the precise organizer/registry wording, while directions provide a stable public
# navigation layer. A profile may belong to several directions.
DIRECTIONS: tuple[Direction, ...] = (
    Direction("mathematics", "Математика"),
    Direction("programming", "Информатика и программирование"),
    Direction("ai-data", "Данные и искусственный интеллект"),
    Direction("infosec", "Информационная безопасность"),
    Direction("robotics", "Робототехника"),
    Direction("engineering", "Инженерия и технологии"),
    Direction("physics", "Физика"),
    Direction("astronomy-space", "Астрономия и космос"),
    Direction("chemistry", "Химия"),
    Direction("biology-genetics", "Биология и генетика"),
    Direction("medicine", "Медицина"),
    Direction("ecology", "Экология"),
    Direction("earth-sciences", "География и науки о Земле"),
    Direction("economics-finance", "Экономика и финансы"),
    Direction("entrepreneurship", "Предпринимательство и бизнес"),
    Direction("law", "Право"),
    Direction("social-sciences", "Обществознание и социология"),
    Direction("history", "История"),
    Direction("international-politics", "Политика и международные отношения"),
    Direction("russian-language", "Русский язык"),
    Direction("literature", "Литература и филология"),
    Direction("foreign-languages", "Иностранные и родные языки"),
    Direction("linguistics-oriental", "Лингвистика и востоковедение"),
    Direction("journalism", "Журналистика"),
    Direction("philosophy-culture", "Философия, религия и культура"),
    Direction("arts-design", "Искусство и дизайн"),
    Direction("music", "Музыка"),
    Direction("education-psychology", "Педагогика и психология"),
    Direction("safety", "Безопасность"),
    Direction("sport", "Физическая культура и спорт"),
    Direction("natural-sciences", "Естественные науки"),
    Direction("humanities", "Гуманитарные дисциплины"),
    Direction("interdisciplinary", "Междисциплинарные направления"),
)

FALLBACK_DIRECTION_SLUG = "interdisciplinary"


_DIRECTION_PROFILES: Mapping[str, tuple[str, ...]] = {
    "mathematics": (
        "Анализ данных",
        "Вероятность и статистика",
        "Математика",
        "Математика и криптография",
        "Математический праздник",
        "Математическое моделирование и искусственный интеллект",
        "Механика и математическое моделирование",
        "Московская математическая олимпиада",
        "Научно-технический",
        "Предпрофессиональная олимпиада: Исследования",
    ),
    "programming": (
        "MLOps-инжиниринг",
        "Автоматизация бизнес-процессов",
        "Анализ данных",
        "Бэкенд-разработка",
        VR_PROFILE,
        "Информатика",
        "Информатика (10–11 классы)",
        "Информатика (6–9 классы)",
        "Информатика и программирование",
        "Информационные и коммуникационные технологии",
        "Интеллектуальные робототехнические системы",
        "Инфохимия",
        "Информационная безопасность",
        "Командное программирование",
        "Компьютерная безопасность",
        "Математика и криптография",
        "Математическое моделирование и искусственный интеллект",
        "Мобильная разработка",
        "Программирование",
        "Программная инженерия в финансовых технологиях",
        "Предпрофессиональная олимпиада: Информационные технологии",
        "Предпрофессиональная олимпиада: Исследования",
        "Промышленное программирование",
        "Разработка мобильных приложений",
        "Фронтенд-разработка",
    ),
    "ai-data": (
        "MLOps-инжиниринг",
        "Анализ данных",
        "Анализ космических снимков и геопространственных данных",
        "Большие данные и машинное обучение",
        "Инфохимия",
        "Интеллектуальные робототехнические системы",
        "Интеллектуальные энергетические системы",
        "Искусственный интеллект",
        "Математическое моделирование и искусственный интеллект",
    ),
    "infosec": (
        "Информационная безопасность",
        "Компьютерная безопасность",
        "Математика и криптография",
    ),
    "physics": (
        "Квантовый инжиниринг",
        "Механика и математическое моделирование",
        "Научно-технический",
        "Предпрофессиональная олимпиада: Исследования",
        "Физика",
        "Ядерные технологии",
    ),
    "astronomy-space": (
        "Анализ космических снимков и геопространственных данных",
        "Астрономия",
        "Астрономия и науки о Земле",
        "Космонавтика",
        "Спутниковые и аэрокосмические системы",
    ),
    "chemistry": (
        "Инфохимия",
        "Наносистемы и химический инжиниринг",
        "Химия",
    ),
    "biology-genetics": (
        "Аграрная генетика",
        "Биология",
        "Биоэкономика",
        "Генетика",
        "Геномное редактирование",
        "Инженерные биологические системы",
        "Медицина",
        "Фундаментальная медицина",
    ),
    "medicine": (
        "Медицина",
        "Фундаментальная медицина",
    ),
    "ecology": (
        "Экология",
    ),
    "earth-sciences": (
        "Анализ космических снимков и геопространственных данных",
        "Астрономия и науки о Земле",
        "География",
        "Геология",
    ),
    "engineering": (
        "Автоматизация бизнес-процессов",
        "Автономные транспортные системы",
        "Беспилотные авиационные системы",
        VR_PROFILE,
        "Высокие технологии",
        "Графика",
        "Инженерное дело",
        "Инженерные биологические системы",
        "Инженерные науки",
        "Инженерные системы",
        "Интеллектуальные робототехнические системы",
        "Интеллектуальные энергетические системы",
        "Информационные и коммуникационные технологии",
        "Квантовый инжиниринг",
        "Компьютерное моделирование и графика",
        "Космонавтика",
        "Культура дома, дизайн и технологии",
        "Наносистемы и химический инжиниринг",
        "Предпрофессиональная олимпиада: Инженерия",
        "Предпрофессиональная олимпиада: Информационные технологии",
        "Предпрофессиональная олимпиада: Исследования",
        "Спутниковые и аэрокосмические системы",
        "Техника и технологии",
        "Техника, технологии и техническое творчество",
        "Технический рисунок и декоративная композиция",
        "Технологии беспроводной связи",
        "Технологическое предпринимательство",
        "Труд (технология): Культура дома, дизайн и технологии",
        "Труд (технология): Техника, технологии и техническое творчество",
        "Ядерные технологии",
    ),
    "robotics": (
        "Автономные транспортные системы",
        "Беспилотные авиационные системы",
        "Интеллектуальные робототехнические системы",
        "Летающая робототехника",
        "Робототехника",
        "Робототехника (5–8 классы)",
        "Робототехника (9–11 классы)",
    ),
    "economics-finance": (
        "Автоматизация бизнес-процессов",
        "Биоэкономика",
        "Программная инженерия в финансовых технологиях",
        "Финансовая безопасность",
        "Финансовая грамотность",
        "Экономика",
    ),
    "entrepreneurship": (
        "Автоматизация бизнес-процессов",
        "Основы бизнеса",
        "Технологическое предпринимательство",
    ),
    "law": (
        "Право",
    ),
    "safety": (
        "Комплексная безопасность",
        "Основы безопасности и защиты Родины (ОБЗР)",
        "Финансовая безопасность",
    ),
    "social-sciences": (
        "Обществознание",
        "Основы российской государственности",
        "Социология",
    ),
    "history": (
        "История",
        "История искусств",
        "Основы российской государственности",
    ),
    "international-politics": (
        "Востоковедение",
        "Восточные языки",
        "Международные отношения",
        "Международные отношения и глобалистика",
        "Основы российской государственности",
        "Политология",
    ),
    "foreign-languages": (
        "Английский язык",
        "Арабский язык",
        "Восточные языки",
        "Иностранные языки",
        "Иностранный язык",
        "Испанский язык",
        "Итальянский язык",
        "Китайский язык",
        "Немецкий язык",
        "Родные языки",
        "Французский язык",
    ),
    "linguistics-oriental": (
        "Востоковедение",
        "Восточные языки",
        "Лингвистика",
        "Филология",
    ),
    "russian-language": (
        "Русский язык",
    ),
    "literature": (
        "Литература",
        "Филология",
    ),
    "journalism": (
        "Журналистика",
    ),
    "philosophy-culture": (
        "Культурология",
        "Основы православной культуры",
        "Религиоведение",
        "Философия",
    ),
    "arts-design": (
        "Академический рисунок, живопись, композиция, история искусства и культуры",
        "Графика",
        "Графический дизайн",
        "Дизайн",
        VR_PROFILE,
        "Изобразительное искусство",
        "Искусство",
        "Искусство (мировая художественная культура)",
        "История искусств",
        "Композиция",
        "Компьютерное моделирование и графика",
        "Культура дома, дизайн и технологии",
        "Рисунок",
        "Рисунок, живопись, композиция, черчение",
        "Рисунок, живопись, скульптура, дизайн",
        "Технический рисунок и декоративная композиция",
        "Труд (технология): Культура дома, дизайн и технологии",
    ),
    "music": (
        "Духовые и ударные инструменты",
        "Инструменты народного оркестра",
        "Музыкальная педагогика и исполнительство",
        "Струнные инструменты",
        "Теория и история музыки",
        "Фортепиано",
        "Хоровое дирижирование",
    ),
    "education-psychology": (
        "Музыкальная педагогика и исполнительство",
        "Образование и педагогика",
        "Психология",
    ),
    "sport": (
        "Физическая культура",
    ),
    "natural-sciences": (
        "Естественные науки",
    ),
    "humanities": (
        "Гуманитарные и социальные науки",
    ),
    "interdisciplinary": (
        "Профессиональные компетенции",
    ),
}


def _build_taxonomy() -> tuple[
    Mapping[str, Direction], Mapping[str, tuple[str, ...]], frozenset[str]
]:
    by_slug = {direction.slug: direction for direction in DIRECTIONS}
    if len(by_slug) != len(DIRECTIONS):
        raise RuntimeError("Direction slugs must be unique")
    if set(_DIRECTION_PROFILES) != set(by_slug):
        raise RuntimeError("Every direction must have an explicit profile group")

    profile_directions: dict[str, list[str]] = {}
    for direction in DIRECTIONS:
        profiles = _DIRECTION_PROFILES[direction.slug]
        if len(profiles) != len(set(profiles)):
            raise RuntimeError(f"Duplicate profile in direction {direction.slug}")
        for profile in profiles:
            profile_directions.setdefault(profile, []).append(direction.slug)

    return (
        MappingProxyType(by_slug),
        MappingProxyType(
            {profile: tuple(slugs) for profile, slugs in profile_directions.items()}
        ),
        frozenset(profile_directions),
    )


DIRECTION_BY_SLUG, PROFILE_DIRECTIONS, MAPPED_PROFILES = _build_taxonomy()


def direction_by_slug(slug: str) -> Direction | None:
    return DIRECTION_BY_SLUG.get(slug)


def profile_names_for_direction(slug: str) -> tuple[str, ...]:
    if slug not in DIRECTION_BY_SLUG:
        raise KeyError(slug)
    return _DIRECTION_PROFILES[slug]


def direction_slugs_for_profile(profile: str) -> tuple[str, ...]:
    return PROFILE_DIRECTIONS.get(profile, (FALLBACK_DIRECTION_SLUG,))


def directions_for_profile(profile: str) -> tuple[Direction, ...]:
    return tuple(DIRECTION_BY_SLUG[slug] for slug in direction_slugs_for_profile(profile))


def aggregate_direction_counts(
    profile_counts: Iterable[tuple[str, int]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for profile, count in profile_counts:
        for slug in direction_slugs_for_profile(profile):
            counts[slug] += count
    return dict(counts)
