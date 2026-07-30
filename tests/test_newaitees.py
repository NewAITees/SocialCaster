import shutil
import subprocess
from pathlib import Path

from social_caster.newaitees import NewAITeesPublisher


def test_publish_returns_social_variant_url() -> None:
    root = Path("tests/_runtime_newaitees")
    image = root / "image.png"
    repository = root / "NewAITees"
    calls: list[list[str]] = []
    run_options: list[dict[str, object]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        run_options.append(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        repository.mkdir(parents=True)
        image.write_bytes(b"png")
        publisher = NewAITeesPublisher(repository, runner=runner)

        url = publisher.publish(image, "horror")

        # X の 5MB 制限に収まる中間JPEGのURLを返す（IG/X共通で使う）
        assert url.endswith("/assets/gallery-social/horror/image.jpg")
        # 原寸画像はギャラリー表示用にこれまで通り配置する
        assert (repository / "assets/gallery/horror/image.png").exists()

        # 中間JPEGは sharp(node) で幅2048・JPEGに縮小して生成する
        social_calls = [
            command
            for command in calls
            if command[:2] == ["node", "-e"] and "gallery-social/horror/image.jpg" in command[-1]
        ]
        assert len(social_calls) == 1
        script = social_calls[0][2]
        assert "sharp" in script
        assert "2048" in script
        assert "jpeg" in script
        # 5MB上限を超える場合は品質を段階的に下げて確実に収める
        assert "5 * 1024 * 1024" in script
        assert "toBuffer" in script

        # 原寸・中間JPEG・ギャラリーデータ・サムネイルをまとめてコミット対象にする
        assert [
            "git",
            "-c",
            f"safe.directory={repository.resolve()}",
            "add",
            "--",
            "assets/gallery/horror/image.png",
            "assets/gallery-social/horror/image.jpg",
            "assets/js/gallery-data.json",
            "assets/gallery-thumbnails",
        ] in calls
        assert [
            "git",
            "-c",
            f"safe.directory={repository.resolve()}",
            "push",
            "origin",
            "main",
        ] in calls
        assert not any(
            command[3:5] == ["diff", "--cached"] for command in calls if len(command) >= 5
        )
        assert all(options["encoding"] == "utf-8" for options in run_options)
        assert all(options["errors"] == "replace" for options in run_options)
    finally:
        shutil.rmtree(root, ignore_errors=True)
