import pytest

from social_caster.database import (
    add_post,
    connect,
    due_posts,
    mark_failed,
    mark_success,
    stock_count,
)


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


def test_stock_count_only_includes_future_instagram_success() -> None:
    connection = connect(":memory:")
    future_id = add_post(
        connection,
        image_path="images/future.jpg",
        image_url="https://example.com/future.jpg",
        instagram_text="future",
        twitter_text="future",
        publish_at="2026-09-02T00:00:00+00:00",
    )
    past_id = add_post(
        connection,
        image_path="images/past.jpg",
        image_url="https://example.com/past.jpg",
        instagram_text="past",
        twitter_text="past",
        publish_at="2026-08-01T00:00:00+00:00",
    )
    failed_id = add_post(
        connection,
        image_path="images/failed.jpg",
        image_url="https://example.com/failed.jpg",
        instagram_text="failed",
        twitter_text="failed",
        publish_at="2026-09-03T00:00:00+00:00",
    )
    mark_success(connection, post_id=future_id, service="instagram", buffer_id="ig-future")
    mark_success(connection, post_id=past_id, service="instagram", buffer_id="ig-past")
    mark_failed(connection, post_id=failed_id, service="instagram", error="failed")

    assert stock_count(connection, now="2026-08-30T00:00:00+00:00") == 1


def test_stock_count_does_not_treat_past_jst_time_as_future() -> None:
    connection = connect(":memory:")
    post_id = add_post(
        connection,
        image_path="images/past-jst.jpg",
        image_url="https://example.com/past-jst.jpg",
        instagram_text="past JST",
        twitter_text="past JST",
        publish_at="2026-08-30T08:00:00+09:00",
    )
    mark_success(connection, post_id=post_id, service="instagram", buffer_id="ig-past-jst")

    assert stock_count(connection, now="2026-08-30T00:00:00+00:00") == 0
