import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_manifests.py"
SCRIPT_GLOBALS = runpy.run_path(str(SCRIPT))
main = cast(Callable[[Path], int], SCRIPT_GLOBALS["main"])
validate_manifest = cast(Callable[[Path], list[str]], SCRIPT_GLOBALS["validate_manifest"])

HASHTAGS = [
    "#stablediffusion",
    "#sd",
    "#newaitees",
    "#aiart",
    "#aiartwork",
    "#digitalart",
    "#abstractart",
    "#generativeart",
    "#surrealart",
    "#conceptart",
    "#modernart",
    "#visualart",
    "#creativeart",
    "#artdaily",
    "#futureart",
    "#dreamscape",
    "#digitalpainting",
    "#artcollector",
    "#galleryart",
    "#newmediaart",
]


def _valid_payload() -> dict[str, object]:
    return {
        "image": "art.png",
        "category": "abstract_image",
        "instagram_text": (
            "日本語:\n光が折り重なる抽象作品です。\n\n"
            "English:\nLayers of light form an abstract landscape. "
            "https://x.com/New_AI_Tees\n\n"
            + " ".join(HASHTAGS)
        ),
        "twitter_text": "生成は維持しますが、X投稿は現在凍結中です。",
    }


def _write_manifest(root: Path, payload: object) -> Path:
    (root / "art.png").write_bytes(b"image")
    manifest = root / "art.png.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return manifest


def test_valid_manifest_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_manifest(tmp_path, _valid_payload())

    assert main(tmp_path) == 0
    assert capsys.readouterr().out == "All manifests are valid.\n"


Mutation = Callable[[dict[str, object], Path], None]


def _missing_image(payload: dict[str, object], root: Path) -> None:
    (root / "art.png").unlink()


def _wrong_image_name(payload: dict[str, object], root: Path) -> None:
    payload["image"] = "other.png"
    (root / "other.png").write_bytes(b"image")


def _invalid_category(payload: dict[str, object], root: Path) -> None:
    payload["category"] = "invalid"


def _long_japanese(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(
        "光が折り重なる抽象作品です。", "光" * 251
    )


def _long_english(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(
        "Layers of light form an abstract landscape. ", "A" * 251
    )


def _nineteen_hashtags(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(" #newmediaart", "")


def _uppercase_hashtag(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(
        "#aiartwork", "#AIartwork"
    )


def _duplicate_hashtag(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(
        "#newmediaart", "#stablediffusion"
    )


def _missing_required_hashtag(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace("#sd", "#scifiart")


def _missing_x_link(payload: dict[str, object], root: Path) -> None:
    payload["instagram_text"] = str(payload["instagram_text"]).replace(
        " https://x.com/New_AI_Tees", ""
    )


def _publish_at_present(payload: dict[str, object], root: Path) -> None:
    payload["publish_at"] = "2026-08-30T01:00:00+09:00"


def _empty_twitter_text(payload: dict[str, object], root: Path) -> None:
    payload["twitter_text"] = ""


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (_missing_image, "画像が存在しません"),
        (_wrong_image_name, "JSONファイル名と対応していません"),
        (_invalid_category, "categoryが有効ではありません"),
        (_long_japanese, "日本語本文が250文字を超えています"),
        (_long_english, "英語本文が250文字を超えています"),
        (_nineteen_hashtags, "ハッシュタグ数が20個ではありません"),
        (_uppercase_hashtag, "小文字ではないハッシュタグ"),
        (_duplicate_hashtag, "重複ハッシュタグ"),
        (_missing_required_hashtag, "必須ハッシュタグがありません"),
        (_missing_x_link, "英語本文の末尾"),
        (_publish_at_present, "publish_atキー"),
        (_empty_twitter_text, "twitter_textが存在し空でない"),
    ],
)
def test_manifest_violation_returns_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mutation: Mutation,
    message: str,
) -> None:
    payload = _valid_payload()
    manifest = _write_manifest(tmp_path, payload)
    mutation(payload, tmp_path)
    manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    assert main(tmp_path) == 1
    output = capsys.readouterr().out
    assert manifest.name in output
    assert message in output


def test_invalid_json_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "broken.png.json"
    manifest.write_text("{", encoding="utf-8")

    assert validate_manifest(manifest)
    assert main(tmp_path) == 1
    assert f"{manifest.name}: JSONを解析できません" in capsys.readouterr().out
