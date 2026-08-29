from social_caster.batch import DailyBatch
from social_caster.cli import _build_parser


def test_publish_media_count_argument_defaults_and_overrides() -> None:
    parser = _build_parser()

    assert parser.parse_args(["publish-media"]).count == DailyBatch.MEDIA_PER_RUN
    assert parser.parse_args(["publish-media", "--count", "7"]).count == 7


def test_publish_social_count_argument_defaults_and_overrides() -> None:
    parser = _build_parser()

    assert parser.parse_args(["publish-social"]).count == DailyBatch.SOCIAL_POSTS_PER_RUN
    assert parser.parse_args(["publish-social", "--count", "5"]).count == 5
