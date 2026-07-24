import pytest

from social_caster.content import validate_instagram_text, validate_x_text


def test_instagram_allows_long_form_caption() -> None:
    validate_instagram_text("説明文\n" + "#tag " * 100)


def test_x_rejects_text_over_standard_limit() -> None:
    with pytest.raises(ValueError, match="280"):
        validate_x_text("x" * 281)
