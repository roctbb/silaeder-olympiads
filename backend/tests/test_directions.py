import pytest

from app.services.directions import direction_slugs_for_profile


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ("Естественные науки", {"natural-sciences"}),
        ("Гуманитарные и социальные науки", {"humanities"}),
        ("Медицина", {"biology-genetics", "medicine"}),
        (
            "Математическое моделирование и искусственный интеллект",
            {"mathematics", "programming", "ai-data"},
        ),
        (
            "Интеллектуальные робототехнические системы",
            {"programming", "ai-data", "robotics", "engineering"},
        ),
        (
            "Предпрофессиональная олимпиада: Исследования",
            {"mathematics", "programming", "engineering", "physics"},
        ),
        (
            "Финансовая безопасность",
            {"economics-finance", "safety"},
        ),
    ],
)
def test_multidirectional_profile_taxonomy(profile, expected):
    assert set(direction_slugs_for_profile(profile)) == expected


def test_unknown_profile_uses_runtime_fallback():
    assert direction_slugs_for_profile("Новый профиль организатора") == (
        "interdisciplinary",
    )
