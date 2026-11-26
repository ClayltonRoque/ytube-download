import pytest

from app.utils.validators import validate_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=AbC123_456-",
        "http://m.youtube.com/watch?v=AbC123_456-",
        "https://music.youtube.com/watch?v=AbC123_456-",
        "https://youtu.be/AbC123_456-?si=share-token",
        "https://www.youtube.com/shorts/AbC123_456-",
        "https://www.youtube.com/live/AbC123_456-",
        "https://www.youtube.com/embed/AbC123_456-",
        "https://www.youtube-nocookie.com/embed/AbC123_456-",
    ],
)
def test_accepts_supported_video_urls(url):
    assert validate_youtube_url(url) == url


def test_strips_surrounding_whitespace():
    assert validate_youtube_url("  https://youtu.be/AbC123_456-  ") == (
        "https://youtu.be/AbC123_456-"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        None,
        "https://example.com/watch?v=AbC123_456-",
        "https://youtube.com.evil.example/watch?v=AbC123_456-",
        "ftp://youtube.com/watch?v=AbC123_456-",
        "https://user@youtube.com/watch?v=AbC123_456-",
        "https://youtube.com:8443/watch?v=AbC123_456-",
        "https://youtube.com/watch",
        "https://youtube.com/watch?v=short",
        "https://youtube.com/playlist?list=PL123",
        "https://youtube.com/watch?v=AbC123_456-&list=PL123",
        "https://youtu.be/AbC123_456-?list=PL123",
        "https://youtube-nocookie.com/shorts/AbC123_456-",
    ],
)
def test_rejects_unsupported_or_malformed_urls(url):
    with pytest.raises(ValueError):
        validate_youtube_url(url)
