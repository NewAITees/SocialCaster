"""Publish local images through the existing NewAITees GitHub Pages repository."""

import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


class NewAITeesError(RuntimeError):
    """Raised when the NewAITees repository or Pages deployment fails."""


class NewAITeesPublisher:
    def __init__(
        self,
        repository_path: Path,
        *,
        branch: str = "main",
        pages_base_url: str = "https://newaitees.github.io/NewAITees",
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._repository_path = repository_path
        self._branch = branch
        self._pages_base_url = pages_base_url.rstrip("/")
        self._runner = runner

    def publish(self, image_path: Path, category: str) -> str:
        self._validate_component(category, "category")
        self._validate_component(image_path.name, "image filename")
        if not image_path.is_file():
            raise NewAITeesError(f"画像が見つかりません: {image_path}")
        destination = self._repository_path / "assets" / "gallery" / category / image_path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, destination)
        relative_image = destination.relative_to(self._repository_path).as_posix()
        self._run_git("diff", "--cached", "--quiet")
        self._run("node", "gallery-generator.js", cwd=self._repository_path)
        self._run_git(
            "add",
            "--",
            relative_image,
            "assets/js/gallery-data.json",
            "assets/gallery-thumbnails",
        )
        commit = self._run_git(
            "commit", "-m", f"chore: add gallery image {image_path.name}", allow_failure=True
        )
        if commit.returncode not in (0, 1):
            raise NewAITeesError(commit.stderr.strip() or "NewAITeesのcommitに失敗しました")
        self._run_git("push", "origin", self._branch)
        return f"{self._pages_base_url}/assets/gallery/{quote(category)}/{quote(image_path.name)}"

    def wait_until_available(
        self,
        url: str,
        *,
        timeout_seconds: int = 300,
        interval_seconds: int = 10,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                request = Request(url, method="HEAD")
                with opener(request, timeout=10) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if getattr(response, "status", 200) == 200 and content_type.startswith(
                        "image/"
                    ):
                        return
            except OSError:
                pass
            sleep(interval_seconds)
        raise NewAITeesError(f"GitHub Pagesへの画像反映がタイムアウトしました: {url}")

    def _run_git(
        self, *arguments: str, allow_failure: bool = False
    ) -> subprocess.CompletedProcess[str]:
        return self._run("git", *arguments, cwd=self._repository_path, allow_failure=allow_failure)

    def _run(
        self,
        command: str,
        *arguments: str,
        cwd: Path,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        result = self._runner(
            [command, *arguments],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 and not allow_failure:
            message = result.stderr.strip() or result.stdout.strip()
            raise NewAITeesError(f"{command}の実行に失敗しました: {message}")
        return result

    @staticmethod
    def _validate_component(value: str, label: str) -> None:
        if not value or value in {".", ".."} or Path(value).name != value:
            raise NewAITeesError(f"不正な{label}です: {value}")
