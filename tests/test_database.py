import pytest

from social_caster.database import add_post, connect, due_posts, mark_failed, mark_success


def test_due_post_can_retry_one_failed_service() -> None:
    connection = connect(":memory:")
    post_id = add_post(
        connection,
        image_path="images/a.jpg",
        image_url="https://example.com/a.jpg",
        instagram_text="instagram",
        twitter_text="x",
        publish_at="2026-01-01T00:00:00+00:00",
    )
    mark_success(connection, post_id=post_id, service="instagram", buffer_id="ig-1")
    mark_failed(connection, post_id=post_id, service="twitter", error="temporary")

    posts = due_posts(connection, now="2026-01-01T00:01:00+00:00")

    assert len(posts) == 1
    assert posts[0].instagram_status == "SUCCESS"
    assert posts[0].twitter_status == "FAILED"


def test_local_image_url_is_rejected() -> None:
    connection = connect(":memory:")

    with pytest.raises(ValueError, match="https://"):
        add_post(
            connection,
            image_path="images/a.jpg",
            image_url="C:/images/a.jpg",
            instagram_text="instagram",
            twitter_text="x",
            publish_at="2026-01-01T00:00:00+00:00",
        )
