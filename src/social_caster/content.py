"""Platform-specific post text validation for the MVP."""

INSTAGRAM_MAX_TEXT_LENGTH = 2_200
X_MAX_TEXT_LENGTH = 280


def validate_instagram_text(text: str) -> None:
    if not text.strip():
        raise ValueError("Instagram本文は空にできません")
    if len(text) > INSTAGRAM_MAX_TEXT_LENGTH:
        raise ValueError(f"Instagram本文は{INSTAGRAM_MAX_TEXT_LENGTH}文字以内にしてください")


def validate_x_text(text: str) -> None:
    if not text.strip():
        raise ValueError("X本文は空にできません")
    if len(text) > X_MAX_TEXT_LENGTH:
        raise ValueError(f"X本文は{X_MAX_TEXT_LENGTH}文字以内にしてください")


def validate_platform_texts(*, instagram_text: str, twitter_text: str) -> None:
    validate_instagram_text(instagram_text)
    validate_x_text(twitter_text)
