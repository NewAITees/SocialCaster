import shutil
import subprocess
from pathlib import Path

from social_caster.newaitees import NewAITeesPublisher


def test_pages_url_is_generated_from_category() -> None:
    root = Path("tests/_runtime_newaitees")
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

        assert url.endswith("/assets/gallery/horror/image.png")
        assert (repository / "assets/gallery/horror/image.png").exists()
        assert [
            "git",
            "add",
            "--",
            "assets/gallery/horror/image.png",
            "assets/js/gallery-data.json",
            "assets/gallery-thumbnails",
        ] in calls
        assert ["git", "push", "origin", "main"] in calls
    finally:
        shutil.rmtree(root, ignore_errors=True)
