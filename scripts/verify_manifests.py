"""Validate every post manifest currently present in input/inbox."""

import json
import re
from pathlib import Path

VALID_CATEGORIES = {
    "abstract_image",
    "botanical",
    "bottled_image",
    "horror",
    "joke",
    "monochrome",
    "other",
}
REQUIRED_HASHTAGS = {"#stablediffusion", "#sd", "#newaitees", "#aiart"}
X_PROFILE_URL = "https://x.com/New_AI_Tees"
HASHTAG_PATTERN = re.compile(r"#[^\s#]+")
BODY_PATTERN = re.compile(r"^日本語:\s*(.*?)\s*English:\s*(.*)$", re.DOTALL)


def validate_manifest(manifest_path: Path) -> list[str]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"JSONを解析できません: {exc}"]
    if not isinstance(payload, dict):
        return ["JSONのルートはオブジェクトである必要があります"]

    errors: list[str] = []
    image = payload.get("image")
    if not isinstance(image, str) or not image:
        errors.append("imageが存在し空でない文字列である必要があります")
    else:
        if not (manifest_path.parent / image).is_file():
            errors.append(f"imageで指定された画像が存在しません: {image}")
        if image != manifest_path.name.removesuffix(".json"):
            errors.append(f"imageがJSONファイル名と対応していません: {image}")

    category = payload.get("category")
    if category not in VALID_CATEGORIES:
        errors.append(f"categoryが有効ではありません: {category}")

    instagram_text = payload.get("instagram_text")
    if not isinstance(instagram_text, str) or not instagram_text:
        errors.append("instagram_textが存在し空でない文字列である必要があります")
    else:
        hashtags = HASHTAG_PATTERN.findall(instagram_text)
        body = HASHTAG_PATTERN.sub("", instagram_text).strip()
        body_match = BODY_PATTERN.fullmatch(body)
        if body_match is None:
            errors.append("instagram_textを日本語本文と英語本文に分割できません")
        else:
            japanese_text, english_text = body_match.groups()
            if len(japanese_text) > 250:
                errors.append(f"日本語本文が250文字を超えています: {len(japanese_text)}")
            if len(english_text) > 250:
                errors.append(f"英語本文が250文字を超えています: {len(english_text)}")
            if not english_text.rstrip().endswith(X_PROFILE_URL):
                errors.append(f"英語本文の末尾に{X_PROFILE_URL}がありません")
        if len(hashtags) != 20:
            errors.append(f"instagram_textのハッシュタグ数が20個ではありません: {len(hashtags)}")
        if any(hashtag != hashtag.lower() for hashtag in hashtags):
            errors.append("instagram_textに小文字ではないハッシュタグがあります")
        if len(set(hashtags)) != len(hashtags):
            errors.append("instagram_textに重複ハッシュタグがあります")
        missing_hashtags = REQUIRED_HASHTAGS - set(hashtags)
        if missing_hashtags:
            errors.append(f"必須ハッシュタグがありません: {' '.join(sorted(missing_hashtags))}")

    if "publish_at" in payload:
        errors.append("publish_atキーを付与してはいけません")

    twitter_text = payload.get("twitter_text")
    if not isinstance(twitter_text, str) or not twitter_text.strip():
        errors.append("twitter_textが存在し空でない文字列である必要があります")
    # ENABLE_TWITTER=falseでX投稿を凍結中のため、文字数・タグ・リンクは検証しない。
    # 凍結解除時には、運用仕様を確定してここへ検証を復活させる。

    return errors


def main(inbox: Path = Path("input/inbox")) -> int:
    failed = False
    for manifest_path in sorted(inbox.glob("*.json")):
        for error in validate_manifest(manifest_path):
            print(f"{manifest_path.name}: {error}")
            failed = True
    if failed:
        return 1
    print("All manifests are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
