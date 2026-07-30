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
        social_name = f"{image_path.stem}.jpg"
        social_relative = f"assets/gallery-social/{category}/{social_name}"
        (self._repository_path / "assets" / "gallery-social" / category).mkdir(
            parents=True, exist_ok=True
        )
        self._make_social_variant(relative_image, social_relative)
        self._run("node", "gallery-generator.js", cwd=self._repository_path)
        self._run_git(
            "add",
            "--",
            relative_image,
            social_relative,
            "assets/js/gallery-data.json",
            "assets/gallery-thumbnails",
        )
        commit = self._run_git(
            "commit", "-m", f"chore: add gallery image {image_path.name}", allow_failure=True
        )
        if commit.returncode not in (0, 1):
            raise NewAITeesError(commit.stderr.strip() or "NewAITeesのcommitに失敗しました")
        self._run_git("push", "origin", self._branch)
        return (
            f"{self._pages_base_url}/assets/gallery-social/"
            f"{quote(category)}/{quote(social_name)}"
        )

    def _make_social_variant(self, source_relative: str, destination_relative: str) -> None:
        """SNS投稿用に幅2048pxのJPEGを sharp(node) で生成する（Xの5MB上限対策）。

        高精細な画像は品質85でも5MBを超えることがあるため、上限に収まるまで
        品質を段階的に下げてから書き出す。
        """
        script = (
            "const sharp=require('sharp');const fs=require('fs');"
            "const src=process.argv[1];const dest=process.argv[2];"
            "const LIMIT=5 * 1024 * 1024;const qualities=[85,75,65,55,45];"
            "(async()=>{"
            "const base=sharp(src).resize({width:2048,withoutEnlargement:true});"
            "let last=null;"
            "for(const q of qualities){"
            "const buf=await base.clone().jpeg({quality:q,mozjpeg:true}).toBuffer();"
            "last=buf;"
            "if(buf.length<=LIMIT){fs.writeFileSync(dest,buf);process.exit(0);}"
            "}"
            "fs.writeFileSync(dest,last);process.exit(0);"
            "})().catch(e=>{console.error(e&&e.message?e.message:e);process.exit(1);});"
        )
        self._run(
            "node",
            "-e",
            script,
            source_relative,
            destination_relative,
            cwd=self._repository_path,
        )

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
        return self._run(
            "git",
            "-c",
            f"safe.directory={self._repository_path.resolve()}",
            *arguments,
            cwd=self._repository_path,
            allow_failure=allow_failure,
        )

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
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 and not allow_failure:
            message = result.stderr.strip() or result.stdout.strip()
            raise NewAITeesError(f"{command}の実行に失敗しました: {message}")
        return result

    @staticmethod
    def _validate_component(value: str, label: str) -> None:
        if not value or value in {".", ".."} or Path(value).name != value:
            raise NewAITeesError(f"不正な{label}です: {value}")
