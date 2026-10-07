import inspect
import shutil
import subprocess
from pathlib import Path

import pytest

from social_caster.newaitees import NewAITeesError, NewAITeesPublisher


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
        publisher.flush()

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
            "-c",
            "core.longpaths=true",
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
            "-c",
            "core.longpaths=true",
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


def test_publish_rebases_and_retries_when_push_is_rejected() -> None:
    # NewAITeesはGitHub Actionsが Auto-update gallery data を push するため、
    # 画像を1枚公開するたびにリモートが先に進み、次のpushが fetch first で弾かれる。
    root = Path("tests/_runtime_newaitees_rejected")
    image = root / "image.png"
    repository = root / "NewAITees"
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        is_push = "push" in command
        if is_push and sum(1 for call in calls if "push" in call) == 1:
            return subprocess.CompletedProcess(
                command, 1, "", "! [rejected]        main -> main (fetch first)"
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        repository.mkdir(parents=True)
        image.write_bytes(b"png")
        publisher = NewAITeesPublisher(repository, runner=runner)

        publisher.publish(image, "horror")
        publisher.flush()

        git_arguments = [command[5:] for command in calls if command[0] == "git"]
        # 弾かれたあとに rebase で取り込み、同じブランチへ再pushする
        assert ["pull", "--rebase", "--autostash", "origin", "main"] in git_arguments
        pushes = [arguments for arguments in git_arguments if arguments[0] == "push"]
        assert pushes == [["push", "origin", "main"], ["push", "origin", "main"]]
        assert (
            git_arguments.index(["pull", "--rebase", "--autostash", "origin", "main"])
            < len(git_arguments) - 1
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_publish_raises_when_push_fails_even_after_rebase() -> None:
    root = Path("tests/_runtime_newaitees_push_dead")
    image = root / "image.png"
    repository = root / "NewAITees"

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "push" in command:
            return subprocess.CompletedProcess(command, 1, "", "! [rejected] main -> main")
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        repository.mkdir(parents=True)
        image.write_bytes(b"png")
        publisher = NewAITeesPublisher(repository, runner=runner)

        publisher.publish(image, "horror")
        with pytest.raises(NewAITeesError):
            publisher.flush()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_pages_wait_default_timeout_covers_observed_build_time() -> None:
    # 実測でPages反映に約9分かかったため、既定の300秒では足りない。
    default = (
        inspect.signature(NewAITeesPublisher.wait_until_available)
        .parameters["timeout_seconds"]
        .default
    )
    assert default == 900


def test_publish_commits_without_pushing() -> None:
    # Pagesはpushのたびにサイト全体を再ビルドするため、1枚ごとにpushすると
    # ビルド待ちが枚数ぶん積み上がる。pushはflushへ分離する。
    root = Path("tests/_runtime_newaitees_stage")
    image = root / "image.png"
    repository = root / "NewAITees"
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        repository.mkdir(parents=True)
        image.write_bytes(b"png")
        publisher = NewAITeesPublisher(repository, runner=runner)

        url = publisher.publish(image, "horror")

        assert url.endswith("/assets/gallery-social/horror/image.jpg")
        assert not any("push" in command for command in calls)
        assert any(command[5:6] == ["commit"] for command in calls if command[0] == "git")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_flush_pushes_once_for_the_whole_batch() -> None:
    root = Path("tests/_runtime_newaitees_flush")
    repository = root / "NewAITees"
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        repository.mkdir(parents=True)
        publisher = NewAITeesPublisher(repository, runner=runner)

        for _ in range(3):
            (root / "a.png").write_bytes(b"png")
            publisher.publish(root / "a.png", "horror")
        publisher.flush()

        pushes = [command for command in calls if "push" in command]
        assert len(pushes) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
