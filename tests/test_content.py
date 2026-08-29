import pytest

from social_caster.content import (
    DEFAULT_HASHTAG_POOL,
    X_MAX_TEXT_LENGTH,
    diversify_hashtags,
    is_duplicate_text,
    strip_urls,
    validate_instagram_text,
    validate_x_text,
)


def test_instagram_allows_long_form_caption() -> None:
    validate_instagram_text("説明文\n" + "#tag " * 100)


def test_x_rejects_text_over_standard_limit() -> None:
    with pytest.raises(ValueError, match="280"):
        validate_x_text("x" * 281)


def test_near_identical_text_is_flagged_as_duplicate() -> None:
    existing = [
        "苔むした環の向こう、月光の時計仕掛け妖精都市。歯車がまわり冒険者が橋を渡る。 #aiart"
    ]
    candidate = (
        "苔むした輪の向こうに、時計仕掛けの妖精郷。歯車の塔がまわり冒険者が石段をのぼる。 #aiart"
    )
    assert is_duplicate_text(candidate, existing)


def test_distinct_text_is_not_duplicate() -> None:
    existing = ["白い霧の中、巨大な悪夢と向き合う一人のシルエット。 #aiart"]
    candidate = "宝石のように光るサイバー昆虫が、ミクロの世界をSFへ変える一枚。 #scifiart"
    assert not is_duplicate_text(candidate, existing)


def test_empty_history_is_never_duplicate() -> None:
    assert not is_duplicate_text("なんでもよい本文", [])


def _trailing_tags(text: str) -> list[str]:
    return [token for token in text.split() if token.startswith("#")]


def test_diversify_hashtags_preserves_body_text() -> None:
    body = "崩れた城に結晶の塔がそびえ、小さな旅人たちが石段を上っていく。"
    result = diversify_hashtags(f"{body} #aiart #newaitees", index=3)
    assert result.startswith(body)


def test_diversify_hashtags_varies_between_posts() -> None:
    text = "本文サンプル #aiart #newaitees"
    tag_sets = {tuple(_trailing_tags(diversify_hashtags(text, index=i))) for i in range(4)}
    # 連番の投稿で同一タグ集合ばかりにならない。
    assert len(tag_sets) >= 2


def test_diversify_hashtags_only_uses_allowed_tags() -> None:
    text = "本文 #aiart #newaitees"
    allowed = set(DEFAULT_HASHTAG_POOL) | {"#aiart", "#newaitees"}
    for i in range(6):
        for tag in _trailing_tags(diversify_hashtags(text, index=i)):
            assert tag in allowed


def test_diversify_hashtags_stays_within_x_limit() -> None:
    text = "あ" * 260 + " #aiart #newaitees"
    result = diversify_hashtags(text, index=1)
    assert len(result) <= X_MAX_TEXT_LENGTH


def test_strip_urls_removes_trailing_link_and_connector() -> None:
    text = "作品はInstagramにも→ https://www.instagram.com/new_ai_tees"
    assert strip_urls(text) == "作品はInstagramにも"


def test_strip_urls_removes_http_and_https() -> None:
    assert strip_urls("見てね http://example.com と https://example.org だよ") == "見てね と だよ"


def test_strip_urls_keeps_text_without_links() -> None:
    text = "リンクのない普通の本文 #aiart"
    assert strip_urls(text) == text
