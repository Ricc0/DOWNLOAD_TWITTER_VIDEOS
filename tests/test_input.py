import pytest

from twitter_video.input import read_url_file, validate_post_url


def test_validate_post_url_accepts_x_and_twitter_status_urls_with_suffixes():
    assert (
        validate_post_url(
            "https://x.com/jobecoffe/status/2108403966665199628?x=1#video"
        )
        == "https://x.com/jobecoffe/status/2108403966665199628?x=1#video"
    )
    assert (
        validate_post_url("https://twitter.com/user_name/status/42")
        == "https://twitter.com/user_name/status/42"
    )


def test_validate_post_url_rejects_non_post_url():
    with pytest.raises(ValueError, match="public X/Twitter post URL"):
        validate_post_url("https://x.com/jobecoffe")


def test_validate_post_url_rejects_single_media_index_url():
    with pytest.raises(ValueError, match="public X/Twitter post URL"):
        validate_post_url("https://x.com/jobecoffe/status/2108403966665199628/video/2")


def test_read_url_file_ignores_comments_and_collects_invalid_lines(tmp_path):
    source = tmp_path / "thread.txt"
    source.write_text(
        "# thread\n\nhttps://x.com/a/status/1\nnot-a-url\n"
        "https://twitter.com/b/status/2\n",
        encoding="utf-8",
    )

    batch = read_url_file(source)

    assert [request.url for request in batch.requests] == [
        "https://x.com/a/status/1",
        "https://twitter.com/b/status/2",
    ]
    assert [(problem.line_number, problem.value) for problem in batch.problems] == [
        (4, "not-a-url")
    ]
