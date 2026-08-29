"""Platform-specific post text validation for the MVP."""

import re
from collections.abc import Iterable
from difflib import SequenceMatcher

INSTAGRAM_MAX_TEXT_LENGTH = 2_200
X_MAX_TEXT_LENGTH = 280

# これ以上似た本文は「ほぼ重複」とみなしてX投稿をスキップする（凍結対策）。
# 実データ上、近重複は約0.57、別テーマは約0.12で明確に分離するため0.5に設定。
DUPLICATE_SIMILARITY_THRESHOLD = 0.5

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"[#＃]\S+")
# 空白・句読点・括弧・記号など、意味を持たない文字を比較前に取り除く。
_NON_WORD_RE = re.compile(r"[\s　。、，．！!？?・…—\-「」『』（）()\[\]'\"]+")


def _normalize_for_similarity(text: str) -> str:
    """URL・ハッシュタグ・記号・空白を除いた比較用の正規化文字列を返す。"""
    stripped = _URL_RE.sub("", text)
    stripped = _HASHTAG_RE.sub("", stripped)
    stripped = _NON_WORD_RE.sub("", stripped)
    return stripped.casefold()


# 各投稿に外部リンクが付くとスパム判定に加点されるため、X本文からURLを取り除く。
# URL直前の誘導記号（→ : など）と前後の空白もまとめて除去する。
_URL_WITH_LEAD_RE = re.compile(r"[\s　]*[→➡⇒:：—]*[\s　]*https?://\S+")


def strip_urls(text: str) -> str:
    """本文からURL（と直前の誘導記号・余分な空白）を取り除く。"""
    return _URL_WITH_LEAD_RE.sub("", text).rstrip()


def text_similarity(a: str, b: str) -> float:
    """2つの本文の類似度を0.0〜1.0で返す（正規化後の文字列比較）。"""
    left = _normalize_for_similarity(a)
    right = _normalize_for_similarity(b)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def is_duplicate_text(
    text: str,
    existing_texts: Iterable[str],
    *,
    threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> bool:
    """既存本文のいずれかと類似度がしきい値以上なら重複とみなす。"""
    return any(text_similarity(text, other) >= threshold for other in existing_texts)


# 毎回同じ #aiart #newaitees だけを付ける反復パターンを避けるためのタグ候補。
DEFAULT_HASHTAG_POOL = (
    "#aiart",
    "#newaitees",
    "#aiartwork",
    "#digitalart",
    "#fantasyart",
    "#conceptart",
    "#aiillustration",
    "#imaginativeart",
)

# 1投稿に付けるハッシュタグの本数（付けすぎ自体もスパム的なので控えめにする）。
HASHTAG_COUNT_PER_POST = 2

_TRAILING_HASHTAGS_RE = re.compile(r"(?:\s*[#＃]\S+)+\s*$")
_HASHTAG_TOKEN_RE = re.compile(r"[#＃]\S+")


def _split_trailing_hashtags(text: str) -> tuple[str, list[str]]:
    """本文末尾に連続するハッシュタグ群を切り離し、(本文, タグ列) を返す。"""
    match = _TRAILING_HASHTAGS_RE.search(text)
    if match is None:
        return text, []
    body = text[: match.start()]
    tags = _HASHTAG_TOKEN_RE.findall(match.group())
    return body, tags


def diversify_hashtags(
    text: str,
    *,
    index: int,
    pool: tuple[str, ...] = DEFAULT_HASHTAG_POOL,
    count: int = HASHTAG_COUNT_PER_POST,
    max_length: int = X_MAX_TEXT_LENGTH,
) -> str:
    """本文末尾のハッシュタグを、投稿ごとに変わる候補集合へ差し替える。

    元のタグも候補に含めたうえで index に応じて回転させるため、
    同じ組み合わせが毎回続くのを避けられる。本文部分は改変しない。
    """
    body, original = _split_trailing_hashtags(text)
    body = body.rstrip()
    candidates = list(dict.fromkeys([*original, *pool]))
    if not candidates:
        return text
    total = len(candidates)
    take = min(count, total)
    picked: list[str] = []
    for offset in range(take):
        tag = candidates[(index * take + offset) % total]
        if tag not in picked:
            picked.append(tag)
    while picked:
        tags_str = " ".join(picked)
        result = f"{body} {tags_str}".strip() if body else tags_str
        if len(result) <= max_length:
            return result
        picked.pop()
    return body[:max_length]


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
